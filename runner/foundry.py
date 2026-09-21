"""Foundry workflow client.

The request contract follows Microsoft's own workflow sample,
azure-sdk-for-python/sdk/ai/azure-ai-projects/samples/agents/
sample_workflow_multi_agent.py, which invokes a workflow agent as:

    conversation = openai_client.conversations.create()
    openai_client.responses.create(
        conversation=conversation.id,
        extra_body={"agent_reference": {"name": <workflow>,
                                        "type": "agent_reference"}},
        input=<text>,
        stream=True)

Three details of that sample correct an earlier version of this runner, which
was built from the generic Responses reference and would likely have failed:

  * A conversation is created first. The live workflow passes
    `=System.ConversationId` to all nine agents, so without one they would have
    no shared history to read.
  * No `model` is sent. The workflow agent definition has no model of its own,
    and none of the three official agent samples pass one alongside an agent.
  * The run is streamed. Streaming is the only invocation Microsoft
    demonstrates for workflows, and its `workflow_action` events are the only
    direct record of which branch the workflow actually took.

`background` is not sent: no official workflow sample uses it.

Verified read-only against the live project on 2026-09-20. A deliberately wrong
identifier returns 400 "Malformed identifier" on each of these, which shows the
route exists and validates its parameter. None of these calls can bill:

    GET {project}/openai/v1/responses                     200
    GET {project}/openai/v1/responses/{id}                400 invalid_parameters
    GET {project}/openai/v1/conversations/{id}            400 invalid_parameters
    GET {project}/openai/v1/conversations/{id}/items      400 invalid_parameters

Not verifiable without a billable request: whether the service accepts this
exact body for this workflow, and the precise shape of the streamed events.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any, Callable, Iterator

from . import config as cfg
from .transport import (AuthError, HttpResponse, Transport, UrllibTransport,
                        raise_for_status)

TERMINAL_STATUSES = ("completed", "failed", "cancelled", "incomplete")
PENDING_STATUSES = ("queued", "in_progress")


def az_cli_token(config: cfg.RunnerConfig) -> str:
    """Borrow a token from the operator's existing Azure CLI session.

    The token is returned to the caller for the lifetime of one request and is
    never written to disk, logged, or placed in captured evidence. It is fetched
    again for every request, so a long run cannot outlive a token obtained at
    the start: the Azure CLI refreshes it when it is close to expiry.
    """
    try:
        result = subprocess.run(
            [config.az_path, "account", "get-access-token",
             "--resource", cfg.TOKEN_SCOPE, "--query", "accessToken", "-o", "tsv"],
            capture_output=True, text=True, timeout=60)
    except FileNotFoundError as exc:
        raise AuthError(
            "Azure CLI not found at %s. Install it, or set GRIDRESOLVE_AZ_PATH "
            "to its location." % config.az_path) from exc
    except subprocess.TimeoutExpired as exc:
        raise AuthError("Azure CLI did not return a token within 60s") from exc
    if result.returncode != 0:
        raise AuthError(
            "Azure CLI could not issue a token. Run `az login` and try again. "
            "Detail: %s" % (result.stderr or "").strip()[:300])
    token = result.stdout.strip()
    if not token:
        raise AuthError("Azure CLI returned an empty token")
    return token


@dataclass(frozen=True)
class FoundryAgentClient:
    """Read and, only when asked, write against one Foundry project."""

    config: cfg.RunnerConfig
    transport: Transport = UrllibTransport()
    token_provider: Callable[[cfg.RunnerConfig], str] = az_cli_token

    def _headers(self, with_body: bool = False, control_plane: bool = False,
                 stream: bool = False) -> dict[str, str]:
        # The official OpenAI client, which Microsoft's workflow sample uses, sends
        # Accept: application/json on every request, streamed ones included, and
        # never text/event-stream. The runner sends exactly what that client
        # sends, so a strict gateway has no reason to treat it differently.
        del stream
        headers = {
            "Authorization": "Bearer " + self.token_provider(self.config),
            "Accept": "application/json",
        }
        if control_plane:
            headers["Foundry-Features"] = cfg.CONTROL_PLANE_FEATURES
        if with_body:
            headers["Content-Type"] = "application/json"
        return headers

    def _get(self, url: str, context: str, control_plane: bool = False,
             timeout: float = 90.0) -> Any:
        response: HttpResponse = self.transport.send(
            "GET", url, self._headers(control_plane=control_plane),
            timeout=timeout)
        return raise_for_status(response, context)

    # Read-only calls. None of these can bill.

    def get_agent(self) -> Any:
        return self._get(self.config.agent_url(), "Reading the workflow agent",
                         control_plane=True)

    def list_agents(self) -> Any:
        return self._get(self.config.agents_url(), "Listing agents",
                         control_plane=True)

    def list_responses(self) -> Any:
        return self._get(self.config.responses_url(), "Listing responses")

    def get_response(self, response_id: str) -> Any:
        return self._get(self.config.responses_url(response_id),
                         "Retrieving response %s" % response_id)

    def get_conversation_items(self, conversation_id: str) -> Any:
        return self._get(self.config.conversation_items_url(conversation_id),
                         "Retrieving conversation items")

    # Writes. Creating a conversation stores an empty container and invokes no
    # model. Only `stream_response` reaches a model.

    def create_conversation(self) -> Any:
        response = self.transport.send(
            "POST", self.config.conversations_url(),
            self._headers(with_body=True), body=b"{}", timeout=90.0)
        return raise_for_status(response, "Creating the conversation")

    def build_request(self, input_text: str,
                      conversation_id: str) -> dict[str, Any]:
        """The exact payload that `stream_response` sends."""
        return {
            "conversation": conversation_id,
            "agent_reference": {"type": "agent_reference",
                                "name": self.config.agent_name},
            "input": input_text,
            "stream": True,
        }

    def describe_request(self, input_text: str) -> str:
        """Human-readable preview of the billable request, for the preflight."""
        payload = self.build_request(input_text, "<conversation id, created "
                                                 "immediately before this call>")
        payload["input"] = ("<%d characters: the canonical case file, verbatim>"
                            % len(input_text))
        return ("POST %s\n{}\n\nPOST %s\n%s" % (
            self.config.conversations_url(), self.config.responses_url(),
            json.dumps(payload, indent=2)))

    def stream_response(self, input_text: str, conversation_id: str,
                        read_timeout: float = 300.0) -> Iterator[dict]:
        """Start one workflow run. This is billable. Called once, never retried."""
        body = json.dumps(
            self.build_request(input_text, conversation_id)).encode("utf-8")
        return self.transport.stream(
            "POST", self.config.responses_url(),
            self._headers(with_body=True, stream=True), body=body,
            timeout=read_timeout)


def status_of(response: Any) -> str:
    if isinstance(response, dict) and isinstance(response.get("status"), str):
        return response["status"]
    return "unknown"


def is_terminal(status: str) -> bool:
    return status in TERMINAL_STATUSES
