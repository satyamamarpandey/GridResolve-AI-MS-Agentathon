"""HTTP transport for the Foundry runner.

Deliberately small and injectable, so every failure path in the tests is driven
by a fake transport rather than by a real request.

There is no retry logic anywhere in this module, and none anywhere above it. A
throttled or failed call raises and the run stops. Automatic retries against a
nine-agent workflow are how a small budget becomes a large one, and a retry
after a partial run would be billed twice.
"""
from __future__ import annotations

import http.client
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Mapping, Protocol


class TransportError(RuntimeError):
    """Base class for every failure the runner can report."""


class AuthError(TransportError):
    """No usable credential, or the credential was rejected."""


class ThrottledError(TransportError):
    """429 from the service. Never retried automatically."""

    def __init__(self, message: str, retry_after: str | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class ApiError(TransportError):
    """Any other non-success status."""

    def __init__(self, status: int, message: str, code: str = "",
                 request_id: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.request_id = request_id


class TimeoutExceeded(TransportError):
    """The polling deadline passed before the run reached a terminal status."""

    def __init__(self, message: str, response_id: str = "") -> None:
        super().__init__(message)
        self.response_id = response_id


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: bytes
    headers: Mapping[str, str] = field(default_factory=dict)

    def json(self) -> Any:
        if not self.body:
            return {}
        try:
            return json.loads(self.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApiError(self.status,
                           "Response body was not valid JSON: %s" % exc) from exc


class StreamInterrupted(TransportError):
    """The event stream ended before the run reported a terminal state.

    The request was accepted, so the run may still be executing and billing.
    Recovery is to retrieve the same response, never to send another request.
    """


class Transport(Protocol):
    """Minimal surface, so tests can substitute a fake."""

    def send(self, method: str, url: str, headers: Mapping[str, str],
             body: bytes | None = None, timeout: float = 120.0) -> HttpResponse:
        ...

    def stream(self, method: str, url: str, headers: Mapping[str, str],
               body: bytes | None = None,
               timeout: float = 300.0) -> Iterator[dict]:
        ...


def parse_sse(lines: Iterable[bytes]) -> Iterator[dict]:
    """Decode a server-sent event stream into JSON event payloads.

    Events are separated by a blank line. `data:` lines within one event are
    joined with newlines, per the SSE specification. The `[DONE]` sentinel and
    comment lines are skipped. A payload that is not JSON is surfaced as a
    `runner.unparsed` event instead of being dropped, so nothing the service
    sent can vanish from the evidence.
    """
    data: list[str] = []
    for raw in lines:
        line = raw.decode("utf-8", "replace").rstrip("\r\n")
        if line.startswith(":"):
            continue
        if line.startswith("data:"):
            data.append(line[5:].lstrip(" "))
            continue
        if line == "" and data:
            payload = "\n".join(data)
            data = []
            if payload.strip() == "[DONE]":
                continue
            try:
                event = json.loads(payload)
            except json.JSONDecodeError:
                event = {"type": "runner.unparsed", "raw": payload[:2000]}
            yield event if isinstance(event, dict) else {
                "type": "runner.unparsed", "raw": payload[:2000]}
    if data:  # stream closed without the trailing blank line
        payload = "\n".join(data)
        if payload.strip() != "[DONE]":
            try:
                event = json.loads(payload)
                if isinstance(event, dict):
                    yield event
            except json.JSONDecodeError:
                yield {"type": "runner.unparsed", "raw": payload[:2000]}


class UrllibTransport:
    """The real transport. One request, no retry, explicit timeout."""

    def stream(self, method: str, url: str, headers: Mapping[str, str],
               body: bytes | None = None,
               timeout: float = 300.0) -> Iterator[dict]:
        """Open one streaming request and yield its events as they arrive.

        `timeout` bounds the wait between reads, not the whole run. A non-success
        status is raised before any event is yielded.
        """
        request = urllib.request.Request(url, data=body, method=method,
                                         headers=dict(headers))
        try:
            resp = urllib.request.urlopen(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            raise_for_status(HttpResponse(status=exc.code, body=exc.read(),
                                          headers=dict(exc.headers or {})),
                             "Starting the workflow run")
            raise  # unreachable: raise_for_status always raises on an error status
        except urllib.error.URLError as exc:
            raise TransportError("Network call failed: %s" % exc.reason) from exc
        except TimeoutError as exc:
            raise TransportError(
                "No response within %ss when opening the stream" % timeout) from exc
        try:
            with resp:
                yield from parse_sse(resp)
        except (TimeoutError, OSError, http.client.HTTPException) as exc:
            raise StreamInterrupted(
                "The event stream broke mid-run: %s" % exc) from exc

    def send(self, method: str, url: str, headers: Mapping[str, str],
             body: bytes | None = None, timeout: float = 120.0) -> HttpResponse:
        request = urllib.request.Request(url, data=body, method=method,
                                         headers=dict(headers))
        try:
            with urllib.request.urlopen(request, timeout=timeout) as resp:
                return HttpResponse(status=resp.status, body=resp.read(),
                                    headers=dict(resp.headers))
        except urllib.error.HTTPError as exc:
            return HttpResponse(status=exc.code, body=exc.read(),
                                headers=dict(exc.headers or {}))
        except urllib.error.URLError as exc:
            raise TransportError("Network call failed: %s" % exc.reason) from exc
        except TimeoutError as exc:
            raise TransportError(
                "Request timed out after %ss with no response" % timeout) from exc


def raise_for_status(response: HttpResponse, context: str) -> Any:
    """Turn a non-success status into a specific, actionable error."""
    if 200 <= response.status < 300:
        return response.json()

    code, message, request_id = "", "", ""
    try:
        payload = json.loads(response.body.decode("utf-8"))
        error = payload.get("error", payload) if isinstance(payload, dict) else {}
        if isinstance(error, dict):
            code = str(error.get("code", ""))
            message = str(error.get("message", ""))
            request_id = str(error.get("request_id", ""))
    except Exception:  # noqa: BLE001 - a malformed error body must not mask the status
        message = response.body.decode("utf-8", "replace")[:400]

    detail = message or response.body.decode("utf-8", "replace")[:400] or "no detail"

    if response.status in (401, 403):
        raise AuthError(
            "%s was rejected with HTTP %d: %s. Sign in with `az login` and "
            "confirm the account has access to this Foundry project."
            % (context, response.status, detail))
    if response.status == 429:
        retry_after = response.headers.get("Retry-After") or response.headers.get(
            "retry-after")
        raise ThrottledError(
            "%s was throttled (HTTP 429): %s. The runner does not retry "
            "automatically. A throttled call is not billed, but a partially "
            "completed workflow may already have been." % (context, detail),
            retry_after=retry_after)
    raise ApiError(response.status,
                   "%s failed with HTTP %d: %s" % (context, response.status, detail),
                   code=code, request_id=request_id)
