"""
Foundry workflow runner tests. Every API response here is mocked.

No network call, no Azure CLI call, no model request, no cost. These simulate
complete execution lifecycles end to end, and the fake transport records every
request, so each scenario asserts how many billable requests were attempted as
well as what the runner reported.

Nothing in this file is Foundry execution evidence. It proves the runner's
behaviour, not the workflow's.

Run: python tests/test_foundry_runner.py
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from runner import case as case_mod  # noqa: E402
from runner import (analysis, cli, evidence as ev, execute as ex,  # noqa: E402
                    foundry, pricing, workflow_map as wm)
from runner.config import ConfigError, RunnerConfig, from_env  # noqa: E402
from runner.redaction import Redactor  # noqa: E402
from runner.transport import (ApiError, AuthError, HttpResponse,  # noqa: E402
                              StreamInterrupted, ThrottledError,
                              TimeoutExceeded, TransportError, parse_sse)

checks, fails = [], []

FAKE_TOKEN = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJmYWtlLXRlc3QtdG9rZW4ifQ.c2lnbmF0dXJl"
CONFIG = RunnerConfig(resource="secret-resource-name",
                      project="secret-project-name")
PHRASE = ex.CONFIRM_PHRASE
RESP = "resp_mock_0001"
CONV = "conv_mock_0001"


def check(name, cond, detail=""):
    (checks if cond else fails).append((name, detail))
    print("  [%s] %-62s %s" % ("PASS" if cond else "FAIL", name, detail))


def j(payload, status=200, headers=None):
    return HttpResponse(status, json.dumps(payload).encode("utf-8"), headers or {})


def live_agent(version=wm.WORKFLOW_VERSION, state="enabled", draft=False,
               yaml_text=None):
    if yaml_text is None:
        yaml_text = "\n".join(list(wm.AGENT_ACTIONS) + [wm.APPROVED_TOKEN])
    return {"name": "GridResolveAIWorkflow", "state": state,
            "versions": {"latest": {"version": version, "draft": draft,
                                    "definition": {"kind": "workflow",
                                                   "workflow": yaml_text}}}}


def final(status="completed", usage=True, text="Audit complete."):
    out = {"id": RESP, "object": "response", "status": status,
           "output_text": text}
    if usage:
        out["usage"] = {"input_tokens": 100_000, "output_tokens": 30_000,
                        "total_tokens": 130_000,
                        "input_tokens_details": {"cached_tokens": 20_000}}
    return out


def action(action_id, status="completed", kind="InvokeAzureAgent", prev=None):
    return {"type": "response.output_item.done",
            "item": {"type": "workflow_action", "action_id": action_id,
                     "kind": kind, "status": status, "previous_action_id": prev}}


CHAIN = ["node-1789696603365", "node-1789696645054", "node-1789696697430",
         "node-1789696718717", "node-1789696778418", "node-1789696813306",
         "node-1789696841174", wm.GATE_ACTION]


def events(branch="escalate", end="response.completed", created=True):
    out = []
    if created:
        out.append({"type": "response.created",
                    "response": {"id": RESP, "status": "in_progress"}})
    out += [action(a) for a in CHAIN]
    if branch == "escalate":
        out += [action(wm.ESCALATE_BRANCH, kind="ConditionItem"),
                action(wm.ESCALATION_ACTION)]
    elif branch == "approve":
        out += [action(wm.APPROVE_BRANCH, kind="ConditionItem"),
                action(wm.RELEASE_ACTION, kind="SendActivity")]
    elif branch == "both":
        out += [action(wm.RELEASE_ACTION), action(wm.ESCALATION_ACTION)]
    if branch != "no_audit":
        out.append(action(wm.AUDIT_ACTION))
    if end:
        out.append({"type": end, "response": {"id": RESP,
                                              "status": end.split(".")[1]}})
    return out


class FakeTransport:
    """Scripted responses and one scripted stream. Records every request."""

    def __init__(self, sends, stream=None, stream_error=None, on_stream=None):
        self.sends = list(sends)
        self.stream_events = stream
        self.stream_error = stream_error
        self.on_stream = on_stream
        self.requests = []

    def send(self, method, url, headers, body=None, timeout=120.0):
        self.requests.append({"method": method, "url": url,
                              "headers": dict(headers), "body": body})
        if not self.sends:
            raise AssertionError("unexpected extra request: %s %s" % (method, url))
        return self.sends.pop(0)

    def stream(self, method, url, headers, body=None, timeout=300.0):
        self.requests.append({"method": method, "url": url, "stream": True,
                              "headers": dict(headers), "body": body})
        if self.on_stream:
            self.on_stream()
        if isinstance(self.stream_error, Exception) and self.stream_events is None:
            raise self.stream_error
        return self._gen()

    def _gen(self):
        for e in self.stream_events or []:
            yield e
        if self.stream_error:
            raise self.stream_error

    @property
    def model_requests(self):
        """Billable requests: POSTs to the responses route."""
        return [r for r in self.requests if r["method"] == "POST"
                and r["url"].endswith("/openai/v1/responses")]

    @property
    def writes(self):
        return [r for r in self.requests if r["method"] == "POST"]


def happy_sends(final_payload=None, items=None):
    return [j(live_agent()), j({"id": CONV, "object": "conversation"}),
            j(final_payload or final()),
            j(items if items is not None else {"object": "list", "data": []})]


def make_root():
    root = tempfile.mkdtemp(prefix="gridresolve_runner_")
    os.makedirs(os.path.join(root, "submission"))
    shutil.copy(os.path.join(ROOT, "submission", "SYN-CASE-4003_input.json"),
                os.path.join(root, "submission", "SYN-CASE-4003_input.json"))
    return root


def client_for(transport, token_provider=None):
    return foundry.FoundryAgentClient(
        CONFIG, transport=transport,
        token_provider=token_provider or (lambda _c: FAKE_TOKEN))


def run(transport, root, **kw):
    ticks = iter(range(0, 10_000_000, kw.pop("tick", 1)))
    return ex.execute_once(
        CONFIG, "SYN-CASE-4003", cap_usd=kw.pop("cap", 1.00),
        confirm_phrase=kw.pop("phrase", PHRASE), root=root,
        accept_known_defects=kw.pop("accept", True),
        client=client_for(transport, kw.pop("token_provider", None)),
        sleep=lambda _s: None, clock=lambda: next(ticks), **kw)


def attempt(transport, root, **kw):
    """Run and return (result, exception). Exactly one of them is None."""
    try:
        return run(transport, root, **kw), None
    except Exception as exc:  # noqa: BLE001 - the test inspects the type
        return None, exc


def ledger_outcome(root):
    entries = ev.read_ledger(root)
    return entries[-1]["outcome"] if entries else None


def evidence_text(root):
    chunks = []
    for folder, _d, files in os.walk(os.path.join(root, "evidence")):
        for name in files:
            with open(os.path.join(folder, name), encoding="utf-8") as fh:
                chunks.append(fh.read())
    return "\n".join(chunks)


def main():
    print("\n1. DEFAULT BEHAVIOUR MAKES NO REQUEST AT ALL")
    root = make_root()
    t = FakeTransport([])
    pf = ex.preflight(CONFIG, "SYN-CASE-4003", 1.00, root=root, client=client_for(t))
    check("preflight sends zero requests of any kind", len(t.requests) == 0)
    check("preflight reports ready with an adequate cap", pf.can_execute)
    check("preflight output hides the tenant identifiers",
          "secret-" not in pf.endpoint and "secret-" not in pf.request_preview)
    check("preflight blocks when no cap is given",
          not ex.preflight(CONFIG, "SYN-CASE-4003", None, root=root,
                           client=client_for(t)).can_execute)
    check("preflight blocks a cap below the modelled worst case",
          not ex.preflight(CONFIG, "SYN-CASE-4003", 0.10, root=root,
                           client=client_for(t)).can_execute)
    check("a preflight creates no evidence directory",
          not os.path.exists(os.path.join(root, "evidence")))

    print("\n2. REQUEST CONTRACT MATCHES MICROSOFT'S WORKFLOW SAMPLE")
    root = make_root()
    t = FakeTransport(happy_sends(), stream=events())
    result, exc = attempt(t, root)
    check("the happy path completes", exc is None and result.status == "completed",
          repr(exc) if exc else "")
    conv_req, model_req = t.writes[0], t.model_requests[0]
    body = json.loads(model_req["body"].decode("utf-8"))
    check("a conversation is created before the run",
          conv_req["url"].endswith("/openai/v1/conversations")
          and t.requests.index(conv_req) < t.requests.index(model_req))
    check("the run targets /openai/v1/responses with no api-version",
          model_req["url"].endswith("/openai/v1/responses")
          and "api-version" not in model_req["url"])
    check("the workflow is selected by agent_reference",
          body.get("agent_reference") == {"type": "agent_reference",
                                          "name": "GridResolveAIWorkflow"})
    check("the run is bound to the created conversation",
          body.get("conversation") == CONV)
    check("the run is streamed", body.get("stream") is True)
    check("no model field is sent, as in every official agent sample",
          "model" not in body)
    check("no background field is sent", "background" not in body)
    check("the body has exactly the four documented keys",
          sorted(body) == ["agent_reference", "conversation", "input", "stream"],
          str(sorted(body)))
    original = open(os.path.join(root, "submission", "SYN-CASE-4003_input.json"),
                    encoding="utf-8").read()
    check("the canonical case is sent verbatim", body["input"] == original)
    check("every request sends Accept: application/json, as the official client does",
          all(r["headers"].get("Accept") == "application/json" for r in t.requests),
          model_req["headers"].get("Accept"))
    check("no header beyond Authorization, Accept and Content-Type on the model request",
          sorted(model_req["headers"]) == ["Accept", "Authorization", "Content-Type"],
          str(sorted(model_req["headers"])))
    check("the model request carries no preview feature header",
          "Foundry-Features" not in model_req["headers"])
    check("the agent read carries the workflow preview header",
          t.requests[0]["headers"].get("Foundry-Features")
          == "WorkflowAgents=V1Preview")
    check("a token is fetched per request, so a long run cannot outlive one",
          all(r["headers"]["Authorization"] == "Bearer " + FAKE_TOKEN
              for r in t.requests))

    print("\n3. SUCCESSFUL EXECUTION, ESCALATION ROUTE")
    check("exactly one billable model request was sent",
          len(t.model_requests) == 1, "count=%d" % len(t.model_requests))
    check("route observed from workflow_action events is escalation",
          result.route["route"] == "ESCALATED_TO_HUMAN")
    check("gate evaluation observed", result.route["gate_evaluated"])
    check("audit completion observed", result.route["audit_ran"])
    check("all nine agents observed on the escalation path",
          len(result.route["agents_observed"]) == 9
          and result.route["agents_not_observed"] == [],
          "%d agents" % len(result.route["agents_observed"]))
    check("measured usage captured", result.usage.reported
          and result.usage.input_tokens == 100_000)
    check("cost computed from measured tokens, cached input at the cached rate",
          abs(result.usd - pricing.cost_usd(100_000, 30_000, 20_000)) < 1e-9,
          "$%.4f" % result.usd)
    check("the run is within the approved cap", not result.over_cap)
    for name in ("00_preflight.json", "01_conversation.json", "02_events.jsonl",
                 "03_response_id.json", "04_workflow_actions.json",
                 "05_poll_log.jsonl", "06_final_response.json",
                 "07_conversation_items.json", "08_output.txt",
                 "09_route.json", "10_usage_report.md"):
        check("evidence written: " + name,
              os.path.isfile(os.path.join(result.run_dir, name)))
    check("ledger closed with the real outcome",
          ledger_outcome(root) == "COMPLETED_STATUS_COMPLETED")

    print("\n4. ROUTES: APPROVAL, NEITHER, BOTH, MISSING AUDIT")
    for branch, want in (("approve", "APPROVED_AND_RELEASED"),
                         ("none", "NOT_OBSERVED"),
                         ("both", "CONFLICTING_BOTH_BRANCHES_OBSERVED")):
        root = make_root()
        r, exc = attempt(FakeTransport(happy_sends(), stream=events(branch)), root)
        check("branch %-8s is reported as %s" % (branch, want),
              exc is None and r.route["route"] == want,
              r.route["route"] if r else repr(exc))
    check("an unobserved route is never reported as an escalation",
          wm.describe_route([])["route"] == "NOT_OBSERVED")
    root = make_root()
    r, _ = attempt(FakeTransport(happy_sends(), stream=events("no_audit")), root)
    check("an audit that never ran is reported as not observed",
          r is not None and r.route["audit_ran"] is False)
    check("the report says so in words",
          r is not None and "| Audit ran | not observed |" in ex.usage_report(r))
    root = make_root()
    plain = [{"type": "response.created", "response": {"id": RESP}},
             {"type": "response.output_text.delta", "delta": "hello"},
             {"type": "response.completed", "response": {"id": RESP,
                                                         "status": "completed"}}]
    r, _ = attempt(FakeTransport(happy_sends(), stream=plain), root)
    check("hidden intermediate outputs leave the route NOT_OBSERVED",
          r is not None and r.route["route"] == "NOT_OBSERVED"
          and len(r.route["agents_not_observed"]) == 9)
    check("and the run notes say the branch cannot be established",
          r is not None and any("cannot be established" in n for n in r.notes))
    items = {"object": "list", "data": [
        {"type": "message", "role": "user"},
        {"type": "message", "role": "assistant", "content": [
            {"type": "output_text", "text": "draft"}]}] * 5}
    root = make_root()
    r, _ = attempt(FakeTransport(happy_sends(items=items), stream=events()), root)
    saved = json.load(open(os.path.join(r.run_dir, "07_conversation_items.json"),
                           encoding="utf-8"))
    check("multiple conversation items are all captured",
          len(saved["data"]) == 10, "items=%d" % len(saved["data"]))

    print("\n5. RESPONSE AND USAGE EDGE CASES")
    root = make_root()
    r, exc = attempt(FakeTransport(happy_sends(), stream=events(created=False)),
                     root)
    check("a run that streams without a response.created still resolves its id",
          exc is None and r.response_id == RESP)
    root = make_root()
    no_id = [e for e in events() if "response" not in e]
    t = FakeTransport([j(live_agent()), j({"id": CONV})], stream=no_id)
    r, exc = attempt(t, root)
    check("a stream that never reveals a response id is an explicit failure",
          isinstance(exc, TransportError) and "cannot be retrieved" in str(exc))
    check("that state is recorded as unknown, not as success",
          ledger_outcome(root) == "NO_RESPONSE_ID_STATE_UNKNOWN")
    check("and it did not send a second model request",
          len(t.model_requests) == 1)
    root = make_root()
    t = FakeTransport([j(live_agent()), j({"object": "conversation"})])
    r, exc = attempt(t, root)
    check("a missing conversation id stops before any model request",
          isinstance(exc, TransportError) and len(t.model_requests) == 0)
    check("and is recorded as failed before the model request",
          ledger_outcome(root) == "FAILED_BEFORE_MODEL_REQUEST")
    root = make_root()
    r, _ = attempt(FakeTransport(happy_sends(final(usage=False)),
                                 stream=events()), root)
    report = ex.usage_report(r)
    check("missing usage is reported as unmeasured, not zero",
          not r.usage.reported and "unmeasured" in report
          and "It is not zero" in report and "$0.0000" not in report)
    check("an unmeasured run is never called within or over cap", not r.over_cap)
    check("a partial usage block is treated as unreported",
          not pricing.usage_from_response({"usage": {"input_tokens": 5}}).reported)
    check("usage of the wrong type is treated as unreported",
          not pricing.usage_from_response({"usage": "n/a"}).reported)
    root = make_root()
    big = final()
    big["usage"] = {"input_tokens": 2_000_000, "output_tokens": 900_000,
                    "total_tokens": 2_900_000}
    r, _ = attempt(FakeTransport(happy_sends(big), stream=events()), root)
    check("a run that exceeds the cap is flagged plainly",
          r.over_cap and "| Within cap | no |" in ex.usage_report(r),
          "$%.2f against $%.2f" % (r.usd, r.cap_usd))
    for status in ("failed", "incomplete", "cancelled"):
        root = make_root()
        t = FakeTransport(happy_sends(final(status=status)),
                          stream=events(end="response." + status))
        r, exc = attempt(t, root)
        check("status %-10s is reported as such, never as completed" % status,
              exc is None and r.status == status and len(t.model_requests) == 1)
    root = make_root()
    sends = [j(live_agent()), j({"id": CONV}), j({"id": RESP, "status": "weird"})]
    sends += [j({"id": RESP, "status": "weird"})] * 400
    r, exc = attempt(FakeTransport(sends, stream=events()), root,
                     deadline_seconds=60, tick=10)
    check("an unexpected status is never treated as terminal success",
          isinstance(exc, TimeoutExceeded))

    print("\n6. INTERRUPTED RUNS RECOVER THE SAME RESPONSE, NEVER A NEW ONE")
    root = make_root()
    partial = events()[:4]
    sends = [j(live_agent()), j({"id": CONV}),
             j({"id": RESP, "status": "in_progress"}),
             j({"id": RESP, "status": "in_progress"}), j(final()), j({"data": []})]
    t = FakeTransport(sends, stream=partial,
                      stream_error=StreamInterrupted("connection reset"))
    r, exc = attempt(t, root)
    check("a broken stream falls back to polling the same response",
          exc is None and r.status == "completed" and r.stream_interrupted,
          repr(exc) if exc else "")
    check("recovery polled the original response id",
          all(RESP in q["url"] for q in t.requests
              if q["method"] == "GET" and "/responses/" in q["url"]))
    check("recovery sent no second model request", len(t.model_requests) == 1,
          "count=%d" % len(t.model_requests))
    check("the partial route is reported honestly, not completed by guesswork",
          r.route["route"] == "NOT_OBSERVED"
          and len(r.route["agents_observed"]) == 3)
    root = make_root()
    sends = [j(live_agent()), j({"id": CONV})] + [
        j({"id": RESP, "status": "in_progress"})] * 400
    t = FakeTransport(sends, stream=events()[:2],
                      stream_error=StreamInterrupted("dropped"))
    r, exc = attempt(t, root, deadline_seconds=120, tick=10)
    check("a run that never finishes raises TimeoutExceeded",
          isinstance(exc, TimeoutExceeded))
    check("the timeout carries the response id and warns it may still bill",
          isinstance(exc, TimeoutExceeded) and exc.response_id == RESP
          and "may still bill" in str(exc))
    check("the timeout names the recovery command, not a re-run",
          "report --response-id " + RESP in str(exc))
    check("the timeout is recorded as still running",
          ledger_outcome(root) == "TIMED_OUT_STILL_RUNNING")
    check("the timeout sent no second model request", len(t.model_requests) == 1)
    saved_id = json.load(open(os.path.join(
        root, ev.read_ledger(root)[0]["run_dir"], "03_response_id.json"),
        encoding="utf-8"))
    check("the response id was on disk before the failure",
          saved_id["response_id"] == RESP and saved_id["conversation_id"] == CONV)
    t2 = FakeTransport([])
    r, exc = attempt(t2, root)
    check("an ambiguous run cannot be silently re-run",
          isinstance(exc, ev.SafetyError) and len(t2.requests) == 0)

    # A crash after the POST: the process dies mid-stream with a non-runner error.
    root = make_root()
    t = FakeTransport([j(live_agent()), j({"id": CONV})], stream=events()[:3],
                      stream_error=KeyboardInterrupt())
    try:
        run(t, root)
        crashed = False
    except KeyboardInterrupt:
        crashed = True
    check("a hard crash mid-stream propagates", crashed)
    check("the ledger still shows the attempt after the crash",
          ledger_outcome(root) == "ATTEMPT_RECORDED_BEFORE_REQUEST")
    t2 = FakeTransport([])
    r, exc = attempt(t2, root)
    check("after a crash the next start is refused with zero requests",
          isinstance(exc, ev.SafetyError) and len(t2.requests) == 0)
    rec = FakeTransport([j(final()), j({"data": [{"type": "message"}]})])
    got = client_for(rec).get_response(RESP)
    client_for(rec).get_conversation_items(CONV)
    check("recovery by original response id is read-only",
          got["status"] == "completed" and not rec.writes)
    root = make_root()
    sends = [j(live_agent()), j({"id": CONV}), j({"error": {"message": "x"}}, 503)]
    t = FakeTransport(sends, stream=events())
    r, exc = attempt(t, root)
    check("a polling failure is recorded as possibly still running",
          isinstance(exc, ApiError)
          and ledger_outcome(root) == "POLLING_FAILED_RUN_MAY_CONTINUE")
    check("the response id survives in the ledger for recovery",
          RESP in ev.read_ledger(root)[0]["detail"])

    print("\n7. HTTP FAILURES: ONE ATTEMPT, NO RETRY")
    for status, err, outcome in (
            (400, ApiError, "FAILED_BEFORE_COMPLETION"),
            (404, ApiError, "FAILED_BEFORE_COMPLETION"),
            (500, ApiError, "FAILED_BEFORE_COMPLETION"),
            (503, ApiError, "FAILED_BEFORE_COMPLETION"),
            (401, AuthError, "FAILED_BEFORE_COMPLETION"),
            (403, AuthError, "FAILED_BEFORE_COMPLETION"),
            (429, ThrottledError, "THROTTLED")):
        root = make_root()
        failure = None
        try:
            from runner.transport import raise_for_status
            raise_for_status(j({"error": {"code": "c", "message": "svc said no"}},
                               status, {"Retry-After": "42"}), "Starting")
        except TransportError as e:
            failure = e
        t = FakeTransport([j(live_agent()), j({"id": CONV})], stream_error=failure)
        r, exc = attempt(t, root)
        check("HTTP %d on the model request raises %s" % (status, err.__name__),
              isinstance(exc, err), type(exc).__name__)
        check("HTTP %d is attempted exactly once" % status,
              len(t.model_requests) == 1, "count=%d" % len(t.model_requests))
        check("HTTP %d is recorded as %s" % (status, outcome),
              ledger_outcome(root) == outcome, str(ledger_outcome(root)))
    check("a throttle surfaces Retry-After and says nothing retries",
          isinstance(exc, ThrottledError) and exc.retry_after == "42"
          and "does not retry" in str(exc))
    root = make_root()
    t = FakeTransport([j(live_agent()), j({"error": {"message": "no"}}, 500)])
    r, exc = attempt(t, root)
    check("a failed conversation create never reaches the model",
          isinstance(exc, ApiError) and len(t.model_requests) == 0)
    root = make_root()
    t = FakeTransport([j(live_agent()), j({"id": CONV})],
                      stream_error=TransportError("Request timed out"))
    r, exc = attempt(t, root)
    check("a network timeout on the model request is not retried",
          isinstance(exc, TransportError) and len(t.model_requests) == 1)

    print("\n8. AUTHENTICATION")
    root = make_root()

    def no_login(_c):
        raise AuthError("Azure CLI could not issue a token. Run `az login`")

    t = FakeTransport([])
    r, exc = attempt(t, root, token_provider=no_login)
    check("no az session: AuthError, zero requests, no ledger entry",
          isinstance(exc, AuthError) and "az login" in str(exc)
          and not t.requests and ev.read_ledger(root) == [])
    root = make_root()
    calls = {"n": 0}

    def expiring(_c):
        calls["n"] += 1
        if calls["n"] > 2:
            raise AuthError("token expired. Run `az login`")
        return FAKE_TOKEN

    t = FakeTransport([j(live_agent()), j({"id": CONV})])
    r, exc = attempt(t, root, token_provider=expiring)
    check("a token that expires before the model request stops the run",
          isinstance(exc, AuthError) and len(t.model_requests) == 0)
    check("an expired token is recorded, not retried",
          ledger_outcome(root) == "FAILED_BEFORE_COMPLETION")
    check("auth errors never echo the token", FAKE_TOKEN not in str(exc))

    print("\n9. SAFEGUARDS: PHRASE, CAP, LIVE VERSION")
    for label, phrase in (("empty", ""), ("lowercase", PHRASE.lower()),
                          ("trailing space", PHRASE + " "), ("yes", "yes")):
        root = make_root()
        t = FakeTransport([])
        r, exc = attempt(t, root, phrase=phrase)
        check("refuses the %s confirmation phrase, zero requests" % label,
              isinstance(exc, ev.SafetyError) and not t.requests)
    root = make_root()
    t = FakeTransport([])
    r, exc = attempt(t, root, cap=0.05)
    check("refuses a cap below worst case, zero requests",
          isinstance(exc, ev.SafetyError) and not t.requests)
    republished = str(int(wm.WORKFLOW_VERSION) + 1)
    for label, agent in (("a republished later version",
                          live_agent(version=republished)),
                         ("the superseded v6", live_agent(version="6")),
                         ("the superseded v8", live_agent(version="8")),
                         ("the superseded v9, one version back",
                          live_agent(version="9")),
                         ("a draft version", live_agent(draft=True)),
                         ("a disabled agent", live_agent(state="disabled")),
                         ("a definition missing the sentinel",
                          live_agent(yaml_text="\n".join(wm.AGENT_ACTIONS))),
                         ("a definition with other node ids",
                          live_agent(yaml_text=wm.APPROVED_TOKEN))):
        root = make_root()
        t = FakeTransport([j(agent)])
        r, exc = attempt(t, root)
        check("refuses %s before any write" % label,
              isinstance(exc, ev.SafetyError) and not t.writes
              and ev.read_ledger(root) == [])

    print("\n9a. THE AUDIT RECORD MUST NAME THE VERSION THAT ACTUALLY RUNS")
    real = case_mod.load("SYN-CASE-4003")
    check("the canonical case input names the targeted workflow version",
          real.document["workflow_version"]
          == "GridResolveAIWorkflow v" + wm.WORKFLOW_VERSION,
          real.document["workflow_version"])
    from runner import config as config_module
    check("this runner targets workflow v10", wm.WORKFLOW_VERSION == "10"
          and config_module.EXPECTED_WORKFLOW_VERSION == "10")
    for old in ("5", "8", "9"):
        root = make_root()
        stale_path = os.path.join(root, "submission", "SYN-CASE-4003_input.json")
        stale = open(stale_path, encoding="utf-8").read().replace(
            "GridResolveAIWorkflow v" + wm.WORKFLOW_VERSION,
            "GridResolveAIWorkflow v" + old)
        with open(stale_path, "w", encoding="utf-8") as fh:
            fh.write(stale)
        pf = ex.preflight(CONFIG, "SYN-CASE-4003", 1.00, root=root,
                          client=client_for(FakeTransport([])))
        check("a stale v%s label in the case input blocks the preflight" % old,
              not pf.can_execute and any("workflow_version" in b for b in pf.blockers))
        t = FakeTransport([])
        r, exc = attempt(t, root)
        check("and execute refuses the v%s payload with zero requests of any kind" % old,
              isinstance(exc, ev.SafetyError) and not t.requests
              and ev.read_ledger(root) == [])

    print("\n9b. KNOWN LIVE CONFIGURATION DEFECTS BLOCK THE RUN BY DEFAULT")
    nodes = "\n".join(list(wm.AGENT_ACTIONS))
    bad_gate = nodes + ('\n        - condition: =("%s" in Local.Var1497)\n'
                        % wm.APPROVED_TOKEN)
    good_gate = nodes + ('\n        - condition: =("%s" exactin '
                         'Last(Local.Var1497).Text)\n' % wm.APPROVED_TOKEN)

    def agents_with(text):
        return {"data": [{"name": "AccountEvidenceAgent", "versions": {"latest": {
            "definition": {"instructions": text}}}}]}

    told = agents_with("SYN-CASE-4003 maps to SYN-2002, unsupported "
                       "meter-fault claim.")
    clean = agents_with("SYN-CASE-4001 maps to SYN-1001, seasonal.\n"
                        "SYN-CASE-4011: unsupported credit request.")
    found = ex.configuration_defects(client_for(FakeTransport(
        [j(live_agent(yaml_text=bad_gate)), j(told)])), "SYN-CASE-4003")
    check("a bare `in` against a messages table is detected",
          any(d.startswith("GATE") for d in found))
    check("an agent told the verdict for this case is detected",
          any(d.startswith("CONTAMINATION") for d in found))
    found = ex.configuration_defects(client_for(FakeTransport(
        [j(live_agent(yaml_text=good_gate)), j(clean)])), "SYN-CASE-4003")
    check("a Last(...).Text gate and other cases' notes are not flagged",
          found == (), str(found)[:80])
    root = make_root()
    t = FakeTransport([j(live_agent(yaml_text=bad_gate)),
                       j(live_agent(yaml_text=bad_gate)), j(told)])
    r, exc = attempt(t, root, accept=False)
    check("execute refuses by default against known defects, zero writes",
          isinstance(exc, ev.SafetyError)
          and "known configuration defects" in str(exc)
          and not t.writes and ev.read_ledger(root) == [])
    check("the detector performs only reads",
          all(q["method"] == "GET" for q in t.requests))
    root = make_root()
    t = FakeTransport([j(live_agent(yaml_text=bad_gate)),
                       j({"id": CONV}), j(final()), j({"data": []})],
                      stream=events())
    r, exc = attempt(t, root, accept=True)
    check("an explicit acceptance lets the operator run anyway",
          exc is None and len(t.model_requests) == 1)

    print("\n9c. THE RELEASE ACTIVITY MUST BE A TEMPLATE, NOT AN =EXPRESSION")
    v6_release = nodes + "\n              activity: '=Last(Local.VarCustomerDraft).Text'\n"
    v5_release = nodes + "\n              activity: =Local.VarCustomerDraft\n"
    v7_release = nodes + '\n              activity: "{Last(Local.VarCustomerDraft).Text}"\n'
    plain_text = nodes + "\n              activity: Routing to the billing team\n"
    for label, text, expect in (("the v6 quoted =expression", v6_release, True),
                                ("the v5 bare =expression", v5_release, True),
                                ("the v7 {...} template", v7_release, False),
                                ("plain message text", plain_text, False)):
        found = ex.configuration_defects(client_for(FakeTransport(
            [j(live_agent(yaml_text=text)), j(clean)])), "SYN-CASE-4003")
        check("%s is %s" % (label, "flagged" if expect else "not flagged"),
              any(d.startswith("RELEASE") for d in found) == expect)
    shipped = open(os.path.join(ROOT, "tests", "powerfx_gate", "release_v7.txt"),
                   encoding="utf-8").read().strip()
    check("the shipped release template is a single {...} segment",
          shipped.startswith("{") and shipped.endswith("}")
          and not shipped.startswith("="), shipped)

    print("\n9d. EVIDENCE EXTRACTION, REPLAYED AGAINST THE REAL RUN OF 2026-09-20")
    # These files are the untouched artifacts of the one real execution. They
    # are read, never written. This proves the extraction code against what the
    # hosted service actually returns. It is not a new execution.
    real_run = os.path.join(ROOT, "evidence", "runtime",
                            "20260920T205607Z_SYN-CASE-4003_80391bf2")
    before = {n: os.path.getmtime(os.path.join(real_run, n))
              for n in os.listdir(real_run)}
    got = analysis.analyze_run_dir(real_run)
    check("all 1303 captured stream events are read", got["stream_events"] == 1303,
          str(got["stream_events"]))
    with open(os.path.join(real_run, "07_conversation_items.json"),
              encoding="utf-8") as handle:
        real_items = analysis.items_of(json.load(handle))
    check("all 22 captured conversation items are read", len(real_items) == 22,
          str(len(real_items)))
    check("the run is judged against its own workflow version, v6",
          got["workflow"] == "GridResolveAIWorkflow v6", got["workflow"])
    route = got["route"]
    check("the approve route is reported", route["route"] == "APPROVED_AND_RELEASED")
    check("the gate is reported as evaluated, from previous_action_id references",
          route["gate_evaluated"] is True)
    check("each observed agent is listed once, in pipeline order",
          route["agents_observed"] == [
              "CaseTriageAgent", "AccountEvidenceAgent", "UsageAnomalyAgent",
              "PolicyKnowledgeAgent", "ResolutionPlannerAgent",
              "CustomerCommunicationAgent", "EvidenceComplianceAgent",
              "CaseAuditAgent"], str(route["agents_observed"]))
    check("the escalation agent is reported as not observed",
          route["agents_not_observed"] == ["EscalationCoordinatorAgent"])
    part = got["participation"]
    check("eight agents took part, per platform metadata",
          got["distinct_agents"] == 8 and len(part) == 8)
    check("agent versions come from the platform, not from the audit prose",
          {p["agent"]: p["version"] for p in part} == {
              "CaseTriageAgent": "5", "AccountEvidenceAgent": "7",
              "UsageAnomalyAgent": "4", "PolicyKnowledgeAgent": "5",
              "ResolutionPlannerAgent": "5", "CustomerCommunicationAgent": "4",
              "EvidenceComplianceAgent": "5", "CaseAuditAgent": "4"})
    check("every agent's inner response id is captured",
          all(p["inner_response_id"].startswith("resp_") for p in part))
    check("the compliance token is read from the final line",
          got["compliance"]["token"] == "APPROVED")
    check("D1 is detected: the release delivered an unevaluated expression",
          got["release"]["outcome"] == analysis.RELEASE_UNEVALUATED
          and got["release"]["released_preview"]
          == "=Last(Local.VarCustomerDraft).Text")
    check("the 4036-character draft that should have been sent is identified",
          got["release"]["draft_chars"] == 4036)
    check("D2 is visible: the evidence agent returned 363 characters",
          part[1]["agent"] == "AccountEvidenceAgent"
          and part[1]["output_chars"] == 363)
    audit = got["audit"]
    check("D3 is detected: the audit is marked inaccurate",
          audit["audit_parsed"] and audit["accurate"] is False)
    check("D3: execution_status CONFIGURED is flagged for a real execution",
          any("CONFIGURED" in f for f in audit["findings"]))
    check("D3: four listed against eight observed",
          audit["audit_agents_listed"] == 4
          and audit["platform_agents_observed"] == 8)
    check("D3: the four agents the audit omitted are named",
          any("absent from the audit" in f and "CaseTriageAgent" in f
              and "UsageAnomalyAgent" in f for f in audit["findings"]))
    check("D3: the invented version v1.0 is flagged against the real one",
          any("'v1.0'" in f and "version 7" in f for f in audit["findings"]))
    check("the audit's workflow version label was correct and is not flagged",
          not any("workflow_version" in f for f in audit["findings"]))
    check("replaying the evidence modified none of the original artifacts",
          before == {n: os.path.getmtime(os.path.join(real_run, n))
                     for n in os.listdir(real_run)})
    with contextlib.redirect_stdout(io.StringIO()) as out:
        code = cli.main(["analyze", "--run-dir", real_run])
    check("`analyze` runs offline with no configuration and prints the result",
          code == 0 and '"UNEVALUATED_EXPRESSION"' in out.getvalue())

    print("\n9e. ROUTE AND RELEASE REPORTING ON SERVICE-SHAPED DATA")

    def msg(agent_name, version, text, response_id="resp_x"):
        return {"type": "message", "role": "assistant", "status": "completed",
                "created_by": {"response_id": response_id,
                               "agent": {"type": "agent_id", "name": agent_name,
                                         "version": version}},
                "content": [{"type": "output_text", "text": text}]}

    def act(action_id, prev, kind="InvokeAzureAgent"):
        return [{"event": e, "action_id": action_id, "kind": kind,
                 "status": "completed", "previous_action_id": prev}
                for e in ("response.output_item.added",
                          "response.output_item.done")]

    wf = "GridResolveAIWorkflow"
    label = "%s v%s" % (wf, wm.WORKFLOW_VERSION)
    good_audit = json.dumps({
        "workflow_version": label, "execution_status": "RUNTIME_EXECUTED",
        "message_compliance_decision": "APPROVE",
        "participating_agents": [
            {"agent_name": "CustomerCommunicationAgent",
             "agent_version": "NOT_OBSERVED", "output_status": "RECEIVED"},
            {"agent_name": "EvidenceComplianceAgent",
             "agent_version": "NOT_OBSERVED", "output_status": "RECEIVED"},
            {"agent_name": "EscalationCoordinatorAgent",
             "agent_version": "NOT_OBSERVED", "output_status": "NOT_INVOKED"},
            {"agent_name": "CaseAuditAgent", "agent_version": "NOT_OBSERVED",
             "output_status": "RECEIVED"}]})
    draft = '{"customer_summary": "We cannot confirm the meter is broken."}'
    approve_items = [
        msg("CustomerCommunicationAgent", "4", draft),
        msg("EvidenceComplianceAgent", "5", '{"decision":"APPROVE","failed_checks":[],"compliance_summary":"All checks passed."}\n'
            + wm.APPROVED_TOKEN),
        msg(wf, wm.WORKFLOW_VERSION, draft),
        msg("CaseAuditAgent", "5", good_audit)]
    approve_actions = (act("node-1789696841174", "node-1789696813306_Post")
                       + act(wm.RELEASE_ACTION, wm.APPROVE_BRANCH + "Actions",
                             "SendActivity")
                       + act(wm.AUDIT_ACTION, wm.GATE_ACTION + "_Post"))
    got = analysis.analyze(approve_items, approve_actions, wf, label)
    check("approval route: the released message equals the draft",
          got["release"]["outcome"] == analysis.RELEASE_DELIVERED_DRAFT)
    check("approval route: reported with the gate evaluated",
          got["route"]["route"] == "APPROVED_AND_RELEASED"
          and got["route"]["gate_evaluated"])
    check("an audit that reports NOT_OBSERVED versions and RUNTIME_EXECUTED "
          "is accepted as accurate", got["audit"]["accurate"],
          str(got["audit"]["findings"]))

    escalate_items = [
        msg("CustomerCommunicationAgent", "4", draft),
        msg("EvidenceComplianceAgent", "5",
            '{"decision":"HUMAN_REVIEW_REQUIRED"}\n' + wm.ESCALATE_TOKEN),
        msg("EscalationCoordinatorAgent", "5", '{"escalation":"PACKET"}'),
        msg("CaseAuditAgent", "5", good_audit)]
    escalate_actions = (act("node-1789696841174", "node-1789696813306_Post")
                        + act(wm.ESCALATION_ACTION, wm.ESCALATE_BRANCH + "Actions")
                        + act(wm.AUDIT_ACTION, wm.GATE_ACTION + "_Post"))
    got = analysis.analyze(escalate_items, escalate_actions, wf, label)
    check("rejection route: reported as escalated to a human",
          got["route"]["route"] == "ESCALATED_TO_HUMAN"
          and got["route"]["gate_evaluated"]
          and "EscalationCoordinatorAgent" in got["route"]["agents_observed"])
    check("rejection route: the draft is reported as not released",
          got["release"]["outcome"] == analysis.RELEASE_NOT_RELEASED)
    check("rejection route: the escalate token is read",
          got["compliance"]["token"] == "ESCALATE")
    leaked = escalate_items + [msg(wf, wm.WORKFLOW_VERSION, draft)]
    got = analysis.analyze(leaked, escalate_actions
                           + act(wm.RELEASE_ACTION, "x", "SendActivity"), wf, label)
    check("a release on an escalated run is reported as a conflict",
          got["route"]["route"] == "CONFLICTING_BOTH_BRANCHES_OBSERVED")
    got = analysis.analyze([msg("EvidenceComplianceAgent", "5", "Looks fine.")],
                           [], wf, label)
    check("with no action events the route and gate stay NOT observed",
          got["route"]["route"] == "NOT_OBSERVED"
          and got["route"]["gate_evaluated"] is False)
    check("compliance prose without a token is NO_VALID_TOKEN, never APPROVED",
          got["compliance"]["token"] == "NO_VALID_TOKEN")
    quoted = "I will not emit %s for this draft." % wm.APPROVED_TOKEN
    got = analysis.analyze([msg("EvidenceComplianceAgent", "5", quoted)],
                           [], wf, label)
    check("an approved token merely quoted in a refusal is never APPROVED",
          got["compliance"]["token"] == "NO_VALID_TOKEN")
    got = analysis.analyze([msg("EvidenceComplianceAgent", "5",
                                quoted + "\n" + wm.ESCALATE_TOKEN)],
                           [], wf, label)
    check("a quoted approved token followed by the escalate line is ESCALATE",
          got["compliance"]["token"] == "ESCALATE")
    got = analysis.analyze([], [], wf, label)
    check("an empty run reports nothing as observed and no audit",
          got["participation"] == [] and not got["audit"]["audit_parsed"]
          and got["compliance"]["token"] == analysis.NOT_OBSERVED)
    output_shaped = [{"type": "message", "role": "assistant",
                      "agent_reference": {"name": "CaseTriageAgent", "version": "5"},
                      "response_id": "resp_y",
                      "content": [{"type": "output_text", "text": "{}"}]}]
    check("participation is also read from a response's agent_reference form",
          analysis.participation(output_shaped, wf) == [
              {"agent": "CaseTriageAgent", "version": "5",
               "inner_response_id": "resp_y", "output_chars": 2}])

    root = make_root()
    t = FakeTransport(happy_sends(items={"object": "list", "data": approve_items}),
                      stream=events(branch="approve"))
    r = run(t, root)
    written = os.path.join(r.run_dir, "11_run_analysis.json")
    check("a run writes 11_run_analysis.json with platform participation",
          os.path.exists(written) and json.load(open(written, encoding="utf-8"))[
              "release"]["outcome"] == analysis.RELEASE_DELIVERED_DRAFT)
    report = ex.usage_report(r)
    check("the run report lists agents with platform versions",
          "| 1 | CustomerCommunicationAgent | 4 |" in report
          and "| Release step | DELIVERED_WHOLE_DRAFT |" in report
          and "| Customer-ready message | no |" in report
          and "| Case follow-up, observed |" in report)
    bad_items = [dict(i) for i in approve_items]
    bad_items[2] = msg(wf, wm.WORKFLOW_VERSION, "=Last(Local.VarCustomerDraft).Text")
    root = make_root()
    t = FakeTransport(happy_sends(items={"object": "list", "data": bad_items}),
                      stream=events(branch="approve"))
    r = run(t, root)
    check("a run whose release step sends an expression says so in its notes",
          any("did not deliver the drafted message" in n for n in r.notes))

    print("\n9f. PREPARED ESCALATION TESTS: VALID, UNREGISTERED, AND NOT TOLD THE ANSWER")
    prep = os.path.join(ROOT, "tests", "escalation_validation")
    with open(os.path.join(prep, "SYN-CASE-4021_input.json"), encoding="utf-8") as fh:
        raw = fh.read()
    doc = json.loads(raw)
    prepared = case_mod.CaseInput(case_id="SYN-CASE-4021", path="prepared",
                                  raw_text=raw, document=doc)
    try:
        case_mod._validate(prepared)
        valid = True
    except case_mod.CaseError as exc:
        valid = str(exc)
    check("the prepared case passes the runner's synthetic-only validator",
          valid is True, str(valid)[:80])
    check("the prepared case is NOT registered, so it cannot be run by accident",
          "SYN-CASE-4021" not in case_mod.available_cases())
    rec = doc["synthetic_account_records"]
    rate = rec["rate_components"]
    check("its billing arithmetic is internally consistent",
          all(round(b["kwh_billed"] * rate["energy_charge_usd_per_kwh"]
                    + rate["fixed_charge_usd_per_period"], 2) == b["amount_usd"]
              for b in rec["billing_history"]))
    check("its register delta matches the billed kWh",
          rec["meter_reads"][1]["register_kwh"] - rec["meter_reads"][0]["register_kwh"]
          == rec["billing_history"][1]["kwh_billed"])
    check("its records genuinely conflict: bill says actual, read says estimated",
          rec["billing_history"][1]["read_type_end"] == "actual"
          and rec["meter_reads"][1]["read_type"] == "estimated"
          and rec["meter_reads"][1]["read_date"]
          == rec["billing_history"][1]["period_end"])
    folded = raw.casefold()
    check("the input states no conclusion",
          not any(w in folded for w in ("conflict", "escalat", "human review",
                                        "reject", "unsupported", "expected")))
    check("it shares no account, meter or record id with SYN-CASE-4003",
          "0003" not in raw and "SYN-CASE-4003" not in raw)
    with open(os.path.join(prep, "gate_harness.yaml"), encoding="utf-8") as fh:
        harness = fh.read()
    gate = open(os.path.join(ROOT, "tests", "powerfx_gate", "gate_v6.txt"),
                encoding="utf-8").read().strip()
    body = harness.split("kind: workflow", 1)[1]
    check("the gate harness invokes no agent, so it makes no model request",
          "InvokeAzureAgent" not in body and "agent:" not in body)
    check("the gate harness uses the production gate, byte for byte",
          "condition: '=" + gate + "'" in body)
    check("the gate harness keeps the fail-closed default branch",
          'condition: "true"' in body and wm.ESCALATE_BRANCH in body
          and wm.GATE_ACTION in body)
    check("the gate harness labels itself as injected input, not a model decision",
          "INJECTED" in harness and "never a model decision" in harness)

    print("\n9g. THE AUDIT AND RELEASE CHECKS CANNOT BE FOOLED (code review, 2026-09-20)")

    def audit_with(entries, status="RUNTIME_EXECUTED", tail=""):
        body = json.dumps({"workflow_version": label, "execution_status": status,
                           "participating_agents": entries}) + tail
        ran = [msg("CustomerCommunicationAgent", "4", draft),
               msg("CaseAuditAgent", "5", body)]
        return analysis.analyze(ran, [], wf, label)["audit"]

    honest = [{"agent_name": "CustomerCommunicationAgent",
               "agent_version": "NOT_OBSERVED", "output_status": "RECEIVED"},
              {"agent_name": "CaseAuditAgent", "agent_version": "NOT_OBSERVED",
               "output_status": "RECEIVED"}]
    check("an honest audit is accepted", audit_with(honest)["accurate"])
    ghost = honest + [{"agent_name": "GhostAgent", "agent_version": "3",
                       "output_status": "RECEIVED"}]
    got = audit_with(ghost)
    check("an agent the audit lists but the platform never ran is flagged",
          not got["accurate"] and any("GhostAgent" in f for f in got["findings"]))
    skipped = honest + [{"agent_name": "EscalationCoordinatorAgent",
                         "agent_version": "NOT_OBSERVED",
                         "output_status": "NOT_INVOKED"}]
    check("an agent honestly listed as NOT_INVOKED is not flagged",
          audit_with(skipped)["accurate"], str(audit_with(skipped)["findings"]))
    lied = [dict(honest[0], output_status="NOT_INVOKED"), honest[1]]
    got = audit_with(lied)
    check("an agent recorded NOT_INVOKED that the platform did run is flagged",
          not got["accurate"] and any("NOT_INVOKED" in f for f in got["findings"]))
    twice = [dict(honest[0], agent_version="v1.0"),
             dict(honest[0], agent_version="4"), honest[1]]
    got = audit_with(twice)
    check("a false version is flagged even when a later entry for the same "
          "agent is correct",
          not got["accurate"] and any("'v1.0'" in f for f in got["findings"]))
    got = audit_with(honest, tail="\nNote: use {} for placeholders.")
    check("audit JSON followed by prose containing braces is still parsed",
          got["audit_parsed"] and got["accurate"])
    got = audit_with(honest, tail="\n" + wm.APPROVED_TOKEN)
    check("audit JSON followed by a trailing token line is still parsed",
          got["audit_parsed"])

    def released_as(text, with_draft=True):
        sent = ([msg("CustomerCommunicationAgent", "4", draft)] if with_draft
                else []) + [msg(wf, wm.WORKFLOW_VERSION, text)]
        return analysis.release_check(sent, wf)["outcome"]

    check("ordinary prose containing 'Local.' is not called an expression",
          released_as("Please contact your Local. Utility office.",
                      with_draft=False) == analysis.RELEASE_OTHER_TEXT)
    check("a leaked variable reference is called an unevaluated expression",
          released_as("{Last(Local.VarCustomerDraft).Text}")
          == analysis.RELEASE_UNEVALUATED)
    check("a leading = is called an unevaluated expression",
          released_as("  =Upper(x)") == analysis.RELEASE_UNEVALUATED)
    check("text that differs from the draft is never DELIVERED_DRAFT",
          released_as(draft + " ") == analysis.RELEASE_OTHER_TEXT)

    block = nodes + "\n              activity: |-\n                =Last(Local.VarCustomerDraft).Text\n"
    folded = nodes + "\n              activity: >\n                =Local.VarCustomerDraft\n"
    block_ok = nodes + "\n              activity: |-\n                Hello {Local.Name},\n                = is fine mid-text\n"
    for label_, text, expect in (("a block-scalar =expression", block, True),
                                 ("a folded-scalar =expression", folded, True),
                                 ("a block-scalar template", block_ok, False)):
        found = ex.configuration_defects(client_for(FakeTransport(
            [j(live_agent(yaml_text=text)), j(clean)])), "SYN-CASE-4003")
        check("%s is %s" % (label_, "flagged" if expect else "not flagged"),
              any(d.startswith("RELEASE") for d in found) == expect)

    print("\n9h. WORKFLOW v8: CUSTOMER-READY RELEASE")
    full_draft = {"case_id": "SYN-CASE-4003", "workflow_version": label,
                  "case_state": "DRAFTING",
                  "customer_summary": "We cannot confirm the meter is broken.",
                  "what_we_reviewed": "Your June and July bills and meter reads.",
                  "what_we_found": "The register moved 870 kWh.",
                  "why_bill_changed": "Measured use rose from 640 to 870 kWh.",
                  "what_happens_next": "A specialist will review your case.",
                  "customer_action_needed": "Tell us about any changes at home.",
                  "internal_claim_ids": ["C-001"], "internal_evidence_ids": [],
                  "internal_policy_ids": ["POL-MTR-003"],
                  "communication_risk_flags": {"privacy": False},
                  "required_disclosures_included": True}
    composed = wm.compose_customer_message(full_draft)
    check("the composed message carries all six customer fields and headings",
          composed is not None and composed.startswith("We cannot confirm")
          and all(h in composed for h, _f in wm.RELEASE_FIELDS if h)
          and composed.endswith("Tell us about any changes at home."))
    check("the composed message carries no internal field or identifier",
          "internal_" not in composed and "POL-MTR-003" not in composed
          and "C-001" not in composed and "{" not in composed)
    check("a draft with a blank customer field composes to nothing, so it is withheld",
          wm.compose_customer_message(dict(full_draft, what_we_found=" ")) is None
          and wm.compose_customer_message({"customer_summary": "x"}) is None)
    shipped = open(os.path.join(ROOT, "tests", "powerfx_gate", "release_v8.txt"),
                   encoding="utf-8").read().strip()
    check("the runner's release template equals the shipped release_v8.txt",
          wm.release_template() == shipped)
    v8_yaml = open(os.path.join(ROOT, "tests", "workflow_engine", "workflows",
                                "GridResolveAIWorkflow_v%s.yaml" % wm.WORKFLOW_VERSION),
                   encoding="utf-8").read()
    check("the release template in the live definition is the v8 template, unchanged",
          all(line.strip() in v8_yaml for line in shipped.splitlines() if line.strip()))
    check("every action id the runner interprets exists in the live definition",
          all(a in v8_yaml for a in wm.AGENT_ACTIONS)
          and all(a in v8_yaml for a in (
              wm.GATE_ACTION, wm.APPROVE_BRANCH, wm.ESCALATE_BRANCH,
              wm.RELEASE_ACTION, wm.FOLLOWUP_GATE, wm.NO_FOLLOWUP_BRANCH,
              wm.FOLLOWUP_BRANCH, wm.NO_FOLLOWUP_ACTION,
              wm.FOLLOWUP_HANDOFF_ACTION)))

    def released_with(draft_text, released_text):
        return analysis.release_check(
            [msg("CustomerCommunicationAgent", "5", draft_text),
             msg(wf, wm.WORKFLOW_VERSION, released_text)], wf)

    got = released_with(json.dumps(full_draft), composed)
    check("the six-field message is DELIVERED_CUSTOMER_MESSAGE and customer-ready",
          got["outcome"] == analysis.RELEASE_CUSTOMER_MESSAGE
          and got["customer_ready"] is True and got["identifiers_in_release"] == [])
    got = released_with(json.dumps(full_draft), composed.replace("\n", "\r\n") + "\n")
    check("line-ending differences do not change that verdict",
          got["customer_ready"] is True)
    got = released_with(json.dumps(full_draft), json.dumps(full_draft))
    check("releasing the whole JSON object is never customer-ready",
          got["outcome"] == analysis.RELEASE_DELIVERED_DRAFT
          and got["customer_ready"] is False
          and "internal_claim_ids" in got["identifiers_in_release"])
    got = released_with(json.dumps(full_draft),
                        composed.replace("870 kWh", "870 kWh (SYN-BILL-0003-07)"))
    check("a message altered after composition is not customer-ready",
          got["customer_ready"] is False)
    leaky = dict(full_draft, what_we_reviewed="Bills SYN-BILL-0003-06 and POL-MTR-003.")
    got = released_with(json.dumps(leaky), wm.compose_customer_message(leaky))
    check("identifiers written into customer prose are listed, not hidden",
          got["identifiers_in_release"] == ["POL-MTR-003", "SYN-BILL-0003-06"])

    print("\n9i. WORKFLOW v8: MESSAGE APPROVAL AND HUMAN REVIEW ARE SEPARATE")
    plan_json = json.dumps({"resolution_status": "NEED_MORE_INFORMATION",
                            "human_review_reason": "On-site meter test required."})
    clear_json = json.dumps({"resolution_status": "RESOLVED", "human_review_reason": ""})

    def follow(text):
        return analysis.case_follow_up([msg("ResolutionPlannerAgent", "6", text)])

    check("the planner's HUMAN_REQUIRED final line is read",
          follow(plan_json + "\n" + wm.FOLLOWUP_HUMAN_TOKEN)["planner_token"]
          == "HUMAN_REQUIRED")
    check("the planner's NONE_REQUIRED final line is read",
          follow(clear_json + "\n" + wm.FOLLOWUP_NONE_TOKEN)["planner_token"]
          == "NONE_REQUIRED")
    check("no token is NO_VALID_TOKEN, never NONE_REQUIRED",
          follow(plan_json)["planner_token"] == "NO_VALID_TOKEN")
    check("both tokens is NO_VALID_TOKEN",
          follow(plan_json + "\n" + wm.FOLLOWUP_HUMAN_TOKEN + "\n"
                 + wm.FOLLOWUP_NONE_TOKEN)["planner_token"] == "NO_VALID_TOKEN")
    check("a NONE token merely quoted in prose is NO_VALID_TOKEN",
          follow("I will not write %s here." % wm.FOLLOWUP_NONE_TOKEN)[
              "planner_token"] == "NO_VALID_TOKEN")
    check("a NONE token written twice is NO_VALID_TOKEN, as in the workflow gate",
          follow("Decision recorded as %s.\n%s" % (wm.FOLLOWUP_NONE_TOKEN,
                                                    wm.FOLLOWUP_NONE_TOKEN))[
              "planner_token"] == "NO_VALID_TOKEN")
    check("a human_review_reason in the plan is reported on its own",
          follow(plan_json)["planner_states_human_review_reason"] is True
          and follow(clear_json + "\n" + wm.FOLLOWUP_NONE_TOKEN)[
              "planner_states_human_review_reason"] is False)
    check("with no planner output nothing is claimed",
          analysis.case_follow_up([])["planner_token"] == analysis.NOT_OBSERVED)

    release_acts = (act("node-1789696841174", "node-1789696813306_Post")
                    + act(wm.RELEASE_ACTION, wm.APPROVE_BRANCH + "Actions",
                          "SendActivity"))
    handoff_acts = release_acts + act(wm.FOLLOWUP_HANDOFF_ACTION,
                                      wm.FOLLOWUP_BRANCH + "Actions") \
        + act(wm.AUDIT_ACTION, wm.GATE_ACTION + "_Post")
    none_acts = release_acts + act(wm.NO_FOLLOWUP_ACTION,
                                   wm.NO_FOLLOWUP_BRANCH + "Actions", "SetVariable") \
        + act(wm.AUDIT_ACTION, wm.GATE_ACTION + "_Post")

    def route_of(actions):
        return wm.describe_route([a["action_id"] for a in actions],
                                 [a["previous_action_id"] for a in actions])

    got = route_of(handoff_acts)
    check("approved AND handed to a human are reported together, not as a conflict",
          got["route"] == "APPROVED_AND_RELEASED"
          and got["case_follow_up"] == "HANDED_TO_HUMAN"
          and got["follow_up_gate_evaluated"]
          and "EscalationCoordinatorAgent" in got["agents_observed"]
          and got["agents_not_observed"] == [
              n for n in ("CaseTriageAgent", "AccountEvidenceAgent",
                          "UsageAnomalyAgent", "PolicyKnowledgeAgent",
                          "ResolutionPlannerAgent", "CustomerCommunicationAgent")])
    got = route_of(none_acts)
    check("approved with no follow-up needed is reported as NONE_REQUIRED",
          got["case_follow_up"] == "NONE_REQUIRED"
          and "EscalationCoordinatorAgent" in got["agents_not_observed"])
    got = route_of(release_acts)
    check("a release with no follow-up evidence stays NOT_OBSERVED",
          got["case_follow_up"] == "NOT_OBSERVED"
          and got["follow_up_gate_evaluated"] is False)
    got = route_of(escalate_actions)
    check("an escalated message counts as handed to a human",
          got["route"] == "ESCALATED_TO_HUMAN"
          and got["case_follow_up"] == "HANDED_TO_HUMAN")
    got = route_of(handoff_acts + none_acts)
    check("both follow-up branches observed is reported as a conflict",
          got["case_follow_up"] == "CONFLICTING_BOTH_BRANCHES_OBSERVED")
    check("the escalation agent is never listed twice",
          route_of(handoff_acts + escalate_actions)["agents_observed"].count(
              "EscalationCoordinatorAgent") == 1)

    def audit_json(**fields):
        body = {"workflow_version": label, "execution_status": "RUNTIME_EXECUTED",
                "message_compliance_decision": "APPROVE",
                "participating_agents": [
                    {"agent_name": n, "agent_version": "NOT_OBSERVED",
                     "output_status": "RECEIVED"}
                    for n in ("ResolutionPlannerAgent", "CustomerCommunicationAgent",
                              "EvidenceComplianceAgent", "EscalationCoordinatorAgent",
                              "CaseAuditAgent")]}
        body.update(fields)
        return json.dumps(body)

    def whole_run(plan_text, audit_text, actions, handoff=True):
        run_items = [msg("ResolutionPlannerAgent", "6", plan_text),
                     msg("CustomerCommunicationAgent", "5", json.dumps(full_draft)),
                     msg("EvidenceComplianceAgent", "5", '{"decision":"APPROVE","failed_checks":[],"compliance_summary":"All checks passed."}\n'
                         + wm.APPROVED_TOKEN),
                     msg(wf, wm.WORKFLOW_VERSION, composed)]
        if handoff:
            run_items.append(msg("EscalationCoordinatorAgent", "5", '{"p":1}'))
        run_items.append(msg("CaseAuditAgent", "6", audit_text))
        return analysis.analyze(run_items, actions, wf, label)

    needs = plan_json + "\n" + wm.FOLLOWUP_HUMAN_TOKEN
    got = whole_run(needs, audit_json(case_human_review_status="HUMAN_REVIEW_REQUIRED",
                                      human_review_status="HUMAN_REVIEW_REQUIRED",
                                      message_compliance_decision="APPROVE"),
                    handoff_acts)
    check("approved message plus human handoff plus honest audit: no findings",
          got["audit"]["accurate"] and got["case_follow_up"]["findings"] == []
          and got["release"]["customer_ready"], str(got["audit"]["findings"]))
    got = whole_run(needs, audit_json(human_review_status="NO_HUMAN_REVIEW_REQUIRED"),
                    handoff_acts)
    check("an audit that lets approval erase the human review is flagged",
          not got["audit"]["accurate"]
          and any("human_review_status" in f for f in got["audit"]["findings"]))
    got = whole_run(needs, audit_json(case_human_review_status="NONE_REQUIRED"),
                    handoff_acts)
    check("the same erasure under case_human_review_status is flagged",
          any("case_human_review_status" in f for f in got["audit"]["findings"]))
    got = whole_run(needs, audit_json(human_review_status="HUMAN_REVIEW_REQUIRED"),
                    release_acts + act(wm.AUDIT_ACTION, wm.GATE_ACTION + "_Post"),
                    handoff=False)
    check("a case that needs a person with no handoff observed is a finding",
          any("no human handoff was observed" in f
              for f in got["case_follow_up"]["findings"]))
    none_audit = audit_json(human_review_status="NONE_REQUIRED")
    none_audit = json.dumps({**json.loads(none_audit), "participating_agents": [
        e for e in json.loads(none_audit)["participating_agents"]
        if e["agent_name"] != "EscalationCoordinatorAgent"]})
    got = whole_run(clear_json + "\n" + wm.FOLLOWUP_NONE_TOKEN, none_audit,
                    none_acts, handoff=False)
    check("a resolved case with no follow-up and an honest audit has no findings",
          got["audit"]["accurate"] and got["case_follow_up"]["findings"] == [],
          str(got["audit"]["findings"]))
    check("the analysis labels which fields are platform facts and which are model output",
          "route" in got["basis"]["platform_observed"]
          and "participation" in got["basis"]["platform_observed"]
          and any(x.startswith("audit") for x in got["basis"]["model_produced"]))

    real = analysis.analyze_run_dir(real_run)
    check("replayed run 1: the planner asked for human review and none happened",
          real["case_follow_up"]["planner_states_human_review_reason"] is True
          and real["case_follow_up"]["observed"] == "NOT_OBSERVED"
          and len(real["case_follow_up"]["findings"]) == 1)
    check("replayed run 1: the audit's NO_HUMAN_REVIEW_REQUIRED is flagged",
          any("NO_HUMAN_REVIEW_REQUIRED" in f for f in real["audit"]["findings"]))
    check("replayed run 1: the release is not customer-ready",
          real["release"]["customer_ready"] is False)

    print("\n9j. THE RELEASE CONTRACT IS CHECKED BEFORE ANY MONEY IS SPENT")
    v8_def = nodes + "\n        responseObject: Local.VarCustomerMessage\n" \
        "              activity: |-\n                {Local.VarCustomerMessage.customer_summary}\n"
    customer_fields = [f for _h, f in wm.RELEASE_FIELDS]

    def comm_agent(fmt):
        definition = {"instructions": "x"}
        if fmt is not None:
            definition["text"] = {"format": fmt}
        return {"data": [{"name": "CustomerCommunicationAgent",
                          "versions": {"latest": {"definition": definition}}}]}

    strict = {"type": "json_schema", "strict": True,
              "schema": {"required": customer_fields + ["case_id"]}}
    for label_, fmt, expect in (
            ("a strict schema requiring all six fields", strict, False),
            ("no output format at all", None, True),
            ("a schema that is not strict", dict(strict, strict=False), True),
            ("a schema missing one customer field",
             dict(strict, schema={"required": customer_fields[:-1]}), True),
            ("a json_object format", {"type": "json_object"}, True)):
        found = ex.configuration_defects(client_for(FakeTransport(
            [j(live_agent(yaml_text=v8_def)), j(comm_agent(fmt))])), "SYN-CASE-4003")
        check("%s is %s" % (label_, "refused" if expect else "accepted"),
              any(d.startswith("RELEASE-SCHEMA") for d in found) == expect,
              str(found)[:90])
    found = ex.configuration_defects(client_for(FakeTransport(
        [j(live_agent(yaml_text=v8_def.replace(
            "responseObject: Local.VarCustomerMessage", "messages: Local.Other"))),
         j(comm_agent(strict))])), "SYN-CASE-4003")
    check("a template reading a variable nothing fills is refused",
          any("no agent output is saved" in d for d in found))
    schema_path = os.path.join(ROOT, "tests", "workflow_engine",
                               "customer_message.schema.json")
    schema = json.load(open(schema_path, encoding="utf-8"))
    check("the shipped schema requires every field the release template reads",
          all(f in schema["required"] for f in customer_fields)
          and schema["additionalProperties"] is False)
    real_draft = json.loads(analysis._last_text_by(real_items,
                                                   "CustomerCommunicationAgent"))
    check("the real run-1 draft already has exactly the schema's fields",
          set(real_draft) == set(schema["properties"]))
    real_message = wm.compose_customer_message(real_draft)
    check("the real run-1 draft composes to a customer message with no JSON",
          real_message is not None and "{" not in real_message
          and "internal_" not in real_message and "POL-" not in real_message
          and real_message.startswith("You reported a large increase"))

    print("\n9j2. NO SPEND UNLESS THE v10 INVOCATION DESIGN AND OUTPUT CONTRACTS ARE LIVE")
    live_yaml = open(os.path.join(ROOT, "tests", "workflow_engine", "workflows",
                                  "GridResolveAIWorkflow_v%s.yaml" % wm.WORKFLOW_VERSION),
                     encoding="utf-8").read()

    def schema_file(name):
        with open(os.path.join(ROOT, "tests", "workflow_engine", name), encoding="utf-8") as fh:
            return {"type": "json_schema", "strict": True, "schema": json.load(fh)}

    formats = {"CustomerCommunicationAgent": schema_file("customer_message.schema.json"),
               "AccountEvidenceAgent": schema_file("evidence_ledger.schema.json"),
               "PolicyKnowledgeAgent": schema_file("policy_mapping.schema.json"),
               "CaseAuditAgent": schema_file("case_audit.schema.json")}

    def agents_listing(overrides=None):
        chosen = dict(formats, **(overrides or {}))
        return {"data": [{"name": n, "versions": {"latest": {"definition": dict(
            {"instructions": "x"}, **({"text": {"format": f}} if f else {}))}}}
            for n, f in chosen.items()]}

    def defects(yaml_text, listing):
        return ex.configuration_defects(client_for(FakeTransport(
            [j(live_agent(yaml_text=yaml_text)), j(listing)])), "SYN-CASE-4003")

    check("the shipped v10 definition with all four schemas live has no defect",
          not defects(live_yaml, agents_listing()), str(defects(live_yaml, agents_listing()))[:90])
    one_empty = live_yaml.replace(
        'messages: "WORKFLOW STEP 4 of 9', 'messages: ""\n        x: "WORKFLOW STEP 4 of 9', 1)
    check("one agent node with an empty input message is refused",
          any(d.startswith("INVOCATION-INPUT") for d in defects(one_empty, agents_listing())))
    v9_yaml = open(os.path.join(ROOT, "tests", "workflow_engine", "workflows",
                                "GridResolveAIWorkflow_v9.yaml"), encoding="utf-8").read()
    check("the v9 definition, every input empty, is refused on that ground too",
          any(d.startswith("INVOCATION-INPUT") for d in defects(v9_yaml, agents_listing())))
    no_guard = live_yaml.replace('"""evidence_id"""', '"""x"""')
    check("a definition without the investigation guard is refused",
          any(d.startswith("INVESTIGATION-GUARD") for d in defects(no_guard, agents_listing())))
    for agent_name, key in (("AccountEvidenceAgent", "evidence_ledger"),
                            ("PolicyKnowledgeAgent", "policy_ledger"),
                            ("CaseAuditAgent", "message_compliance_decision")):
        check("%s with no output schema is refused" % agent_name,
              any(d.startswith("OUTPUT-SCHEMA") and agent_name in d
                  for d in defects(live_yaml, agents_listing({agent_name: None}))))
        loose = dict(formats[agent_name], strict=False)
        check("%s with a schema that is not strict is refused" % agent_name,
              any(d.startswith("OUTPUT-SCHEMA") and agent_name in d
                  for d in defects(live_yaml, agents_listing({agent_name: loose}))))
        lacking = json.loads(json.dumps(formats[agent_name]))
        lacking["schema"]["required"].remove(key)
        check("%s with a schema that does not require %s is refused" % (agent_name, key),
              any(d.startswith("OUTPUT-SCHEMA") and agent_name in d
                  for d in defects(live_yaml, agents_listing({agent_name: lacking}))))

    print("\n9k. THE PAYLOAD HASH DOES NOT DEPEND ON LINE ENDINGS")
    canonical = case_mod.load("SYN-CASE-4003")
    for label_, transform in (
            ("CRLF line endings", lambda b: b.replace(b"\n", b"\r\n")),
            ("a UTF-8 byte-order mark", lambda b: b"\xef\xbb\xbf" + b),
            ("CRLF and a byte-order mark",
             lambda b: b"\xef\xbb\xbf" + b.replace(b"\n", b"\r\n"))):
        root = make_root()
        target = os.path.join(root, "submission", "SYN-CASE-4003_input.json")
        with open(target, "rb") as fh:
            original = fh.read().replace(b"\r\n", b"\n")
        with open(target, "wb") as fh:
            fh.write(transform(original))
        loaded = case_mod.load("SYN-CASE-4003", root=root)
        check("a checkout with %s has the same sha256 and payload" % label_,
              loaded.sha256 == canonical.sha256
              and case_mod.build_input(loaded) == case_mod.build_input(canonical)
              and "\r" not in case_mod.build_input(loaded))
    check("the transmitted payload contains no carriage return or BOM",
          "\r" not in canonical.raw_text and not canonical.raw_text.startswith("﻿"))
    attrs = open(os.path.join(ROOT, ".gitattributes"), encoding="utf-8").read()
    check(".gitattributes pins the case input to LF and leaves evidence untouched",
          "submission/*_input.json" in attrs and "eol=lf" in attrs
          and "evidence/runtime/**" in attrs and "-text" in attrs)

    print("\n9l. AN AGENT THAT ASKS INSTEAD OF WORKING IS FLAGGED IN ANY POSITION")
    real = analysis.analyze_run_dir(real_run)
    check("replayed run 1: exactly one agent is flagged, AccountEvidenceAgent",
          [u["agent"] for u in real["unhealthy_outputs"]] == ["AccountEvidenceAgent"]
          and set(real["unhealthy_outputs"][0]["problems"])
          == {"NO_JSON_OBJECT", "ASKS_FOR_CONFIRMATION", "ANNOUNCES_FUTURE_WORK",
              "MISSING:evidence_ledger"})
    check("replayed run 1: the seven agents that did their work are not flagged",
          not any(u["agent"] != "AccountEvidenceAgent"
                  for u in real["unhealthy_outputs"]))
    for name in ("UsageAnomalyAgent", "PolicyKnowledgeAgent",
                 "EvidenceComplianceAgent", "EscalationCoordinatorAgent"):
        got = analysis.output_health(
            [msg(name, "4", "I can prepare that. Would you like me to continue?")], wf)
        check("%s asking for confirmation would be flagged" % name,
              len(got) == 1 and got[0]["agent"] == name
              and "ASKS_FOR_CONFIRMATION" in got[0]["problems"])
    check("JSON followed by a route token line is healthy",
          analysis.output_health([msg("EvidenceComplianceAgent", "5",
                                      '{"decision":"APPROVE","failed_checks":[],"compliance_summary":"All checks passed."}\n' + wm.APPROVED_TOKEN)],
                                 wf) == [])
    check("the workflow's own released message is never judged as an agent output",
          analysis.output_health([msg(wf, wm.WORKFLOW_VERSION, "Plain text.")], wf) == [])
    root = make_root()
    stalled = [msg("UsageAnomalyAgent", "4", "Please confirm to proceed.")]
    t = FakeTransport(happy_sends(items={"object": "list", "data": stalled}),
                      stream=events(branch="approve"))
    r = run(t, root)
    check("a run in which an agent stalls says so in its notes",
          any("UsageAnomalyAgent did not return its required output" in n
              for n in r.notes))

    print("\n9m. BOTH REAL RUNS REPLAYED: EVERY AUDIT INCONSISTENCY IS REPORTED")
    second_run = os.path.join(ROOT, "evidence", "runtime",
                              "20260920T225342Z_SYN-CASE-4003_5e6f1114")
    before_2 = {n: os.path.getmtime(os.path.join(second_run, n))
                for n in os.listdir(second_run)}
    two = analysis.analyze_run_dir(second_run)
    found = " | ".join(two["audit"]["findings"])
    check("run 2: the audit says APPROVE, the platform token was ESCALATE, and that is reported",
          two["compliance"]["token"] == "ESCALATE"
          and "compliance decision" in found and "'APPROVE'" in found and "ESCALATE" in found,
          found[:90])
    check("run 2: the escalation agent recorded as NOT_INVOKED although it ran is reported",
          "EscalationCoordinatorAgent is recorded as NOT_INVOKED" in found)
    for name in ("AccountEvidenceAgent", "PolicyKnowledgeAgent", "EvidenceComplianceAgent"):
        check("run 2: %s recorded as RECEIVED although its output was not usable is reported"
              % name, ("%s is recorded as 'RECEIVED'" % name) in found)
    check("run 2: agents whose output was usable are not reported for output_status",
          not any(("%s is recorded as 'RECEIVED'" % n) in found
                  for n in ("CaseTriageAgent", "UsageAnomalyAgent", "ResolutionPlannerAgent",
                            "CustomerCommunicationAgent", "CaseAuditAgent")))
    check("run 2: the audit's invented version for itself is reported",
          "CaseAuditAgent is recorded as version 'GRIDRESOLVE-AGENTS-3.0'" in found)
    check("run 2: a disposition that matches the observed route is not reported",
          "final_disposition" not in found and two["route"]["route"] == "ESCALATED_TO_HUMAN")
    check("run 2: six inconsistencies in all, none invented",
          len(two["audit"]["findings"]) == 6 and two["audit"]["accurate"] is False,
          str(len(two["audit"]["findings"])))
    health = {u["agent"]: set(u["problems"]) for u in two["unhealthy_outputs"]}
    check("run 2: the two announcements of future work are named as such",
          "ANNOUNCES_FUTURE_WORK" in health.get("AccountEvidenceAgent", set())
          and "ANNOUNCES_FUTURE_WORK" in health.get("PolicyKnowledgeAgent", set()),
          str(health)[:90])
    check("run 2: the missing ledger and the missing policy mapping are named",
          "MISSING:evidence_ledger" in health.get("AccountEvidenceAgent", set())
          and "MISSING:policy_ledger" in health.get("PolicyKnowledgeAgent", set()))
    check("run 2: a verdict with no decision and no reasons is named",
          {"MISSING:decision", "NO_REASONS"} <= health.get("EvidenceComplianceAgent", set()))
    check("run 2: exactly those three agents are unhealthy",
          set(health) == {"AccountEvidenceAgent", "PolicyKnowledgeAgent",
                          "EvidenceComplianceAgent"})
    check("run 2: the investigation is reported as incomplete",
          two["investigation"]["complete"] is False
          and set(two["investigation"]["incomplete_stages"])
          == {"AccountEvidenceAgent", "PolicyKnowledgeAgent"})
    check("run 2: its evidence files were not modified by the replay",
          before_2 == {n: os.path.getmtime(os.path.join(second_run, n))
                       for n in os.listdir(second_run)})

    one = analysis.analyze_run_dir(real_run)
    found_1 = " | ".join(one["audit"]["findings"])
    check("run 1: the seven findings reported before are all still reported",
          all(s in found_1 for s in (
              "execution_status is 'CONFIGURED'", "human_review_status is",
              "Agents that ran but are absent", "AccountEvidenceAgent is recorded as version",
              "ResolutionPlannerAgent is recorded as version",
              "EvidenceComplianceAgent is recorded as version",
              "CaseAuditAgent is recorded as version")), found_1[:90])
    check("run 1: the audit's compliance decision agreed with the token, so it is not reported",
          one["compliance"]["token"] == "APPROVED" and "compliance decision" not in found_1)
    check("run 1: AccountEvidenceAgent listed as a participant with no usable output is reported",
          "AccountEvidenceAgent is recorded as" in found_1)
    check("run 1: the investigation is reported as incomplete, evidence stage only",
          one["investigation"]["incomplete_stages"] == ["AccountEvidenceAgent"])
    health_1 = {u["agent"]: set(u["problems"]) for u in one["unhealthy_outputs"]}
    check("run 1: only AccountEvidenceAgent is unhealthy, the other seven pass their contracts",
          set(health_1) == {"AccountEvidenceAgent"}, str(health_1)[:90])

    good_compliance = ('{"decision":"APPROVE","failed_checks":[],"compliance_summary":'
                       '"All twenty checks passed."}\n' + wm.APPROVED_TOKEN)

    def audit_with(decision, disposition="CLOSED", review="NONE_REQUIRED"):
        return json.dumps({
            "workflow_version": label, "execution_status": "RUNTIME_EXECUTED",
            "message_compliance_decision": decision, "case_human_review_status": review,
            "human_review_status": review, "final_disposition": disposition,
            "participating_agents": [
                {"agent_name": "EvidenceComplianceAgent", "agent_version": "NOT_OBSERVED",
                 "output_status": "RECEIVED"},
                {"agent_name": "CaseAuditAgent", "agent_version": "NOT_OBSERVED",
                 "output_status": "RECEIVED"}]})

    def audited(compliance_text, audit_text, actions=()):
        return analysis.analyze(
            [msg("EvidenceComplianceAgent", "6", compliance_text),
             msg("CaseAuditAgent", "7", audit_text)], list(actions), wf, label)["audit"]

    check("an audit that agrees with an APPROVED token is accurate",
          audited(good_compliance, audit_with("APPROVE"))["findings"] == [])
    for token_text, stated in ((good_compliance, "HUMAN_REVIEW_REQUIRED"),
                               ('{"decision":"REJECT_AND_REWRITE","compliance_summary":"x"}\n'
                                + wm.ESCALATE_TOKEN, "APPROVE"),
                               ('{"decision":"APPROVE","compliance_summary":"x"}', "APPROVE")):
        got = audited(token_text, audit_with(stated))
        check("audit decision %s against token %s is reported"
              % (stated, analysis.compliance_decision(
                  [msg("EvidenceComplianceAgent", "6", token_text)])["token"]),
              any("compliance decision" in f for f in got["findings"]), str(got["findings"])[:80])
    got = audited(good_compliance, json.dumps({
        "workflow_version": label, "execution_status": "RUNTIME_EXECUTED",
        "participating_agents": []}))
    check("an audit that records no compliance decision at all is reported",
          any("records no compliance decision" in f for f in got["findings"]))
    escalated = act(wm.ESCALATION_ACTION, wm.ESCALATE_BRANCH + "Actions")
    got = audited('{"decision":"HUMAN_REVIEW_REQUIRED","compliance_summary":"x"}\n'
                  + wm.ESCALATE_TOKEN,
                  audit_with("HUMAN_REVIEW_REQUIRED", disposition="RESOLVED",
                             review="HUMAN_REVIEW_REQUIRED"), escalated)
    check("a closed disposition on a run the platform escalated is reported",
          any("final_disposition" in f for f in got["findings"]), str(got["findings"])[:80])
    got = audited(good_compliance, audit_with("APPROVE", disposition="PENDING_HUMAN_REVIEW",
                                              review="HUMAN_REVIEW_REQUIRED"), none_acts)
    check("a pending-human disposition when the platform ran no handoff is reported",
          any("final_disposition" in f for f in got["findings"]), str(got["findings"])[:80])

    def failed_audit(status):
        record = json.loads(audit_with("APPROVE"))
        record["execution_status"] = status
        record["participating_agents"].insert(0, {
            "agent_name": "PolicyKnowledgeAgent", "agent_version": "NOT_OBSERVED",
            "output_status": "MISSING_OR_MALFORMED"})
        return json.dumps(record)

    def with_policy(policy_text, audit_text):
        return analysis.analyze(
            [msg("PolicyKnowledgeAgent", "6", policy_text),
             msg("EvidenceComplianceAgent", "6", good_compliance),
             msg("CaseAuditAgent", "7", audit_text)], [], wf, label)["audit"]["findings"]

    stalled_policy = "Now I will produce the mandated policy mapping."
    good_policy = json.dumps({"policy_ledger": [{"policy_id": "POL-HB-001"}]})
    check("RUNTIME_FAILED is accepted when a stage the platform ran produced no usable output",
          with_policy(stalled_policy, failed_audit("RUNTIME_FAILED")) == [],
          str(with_policy(stalled_policy, failed_audit("RUNTIME_FAILED")))[:80])
    check("RUNTIME_FAILED is reported when every output the platform recorded was usable",
          any("execution_status" in f
              for f in with_policy(good_policy, failed_audit("RUNTIME_FAILED"))))
    check("CONFIGURED is still reported for a real execution",
          any("execution_status" in f
              for f in with_policy(stalled_policy, failed_audit("CONFIGURED"))))
    with open(os.path.join(ROOT, "tests", "workflow_engine", "case_audit.schema.json"),
              encoding="utf-8") as fh:
        audit_schema = json.load(fh)
    entry = audit_schema["properties"]["participating_agents"]["items"]["properties"]
    check("the audit schema leaves the agent no way to state a version",
          entry["agent_version"]["enum"] == ["NOT_OBSERVED"]
          and audit_schema["additionalProperties"] is False
          and sorted(audit_schema["required"]) == sorted(audit_schema["properties"]))
    check("the audit schema names all nine agents and the three output states",
          len(entry["agent_name"]["enum"]) == 9
          and entry["output_status"]["enum"] == ["RECEIVED", "MISSING_OR_MALFORMED",
                                                 "NOT_INVOKED"])
    order = list(audit_schema["properties"])
    check("the audit must transcribe the route token before it states the decision",
          order.index("compliance_route_token") < order.index("message_compliance_decision"))

    print("\n10. DUPLICATE AND CONCURRENT RUNS CANNOT BOTH BILL")
    root = make_root()
    attempt(FakeTransport(happy_sends(), stream=events()), root)
    t2 = FakeTransport([])
    r, exc = attempt(t2, root)
    check("a second run of the same case is refused with zero requests",
          isinstance(exc, ev.SafetyError) and not t2.requests)
    t3 = FakeTransport(happy_sends(), stream=events())
    r, exc = attempt(t3, root, allow_additional=True)
    check("an explicit opt-in permits one further run",
          exc is None and len(t3.model_requests) == 1)
    check("the ledger records both attempts", len(ev.read_ledger(root)) == 2)
    try:
        ev.claim_run_slot(root, "SYN-CASE-4003",
                          ev.new_run_dir(root, "SYN-CASE-4003"), False)
        refused = False
    except ev.SafetyError:
        refused = True
    check("the ledger itself refuses a repeat, independent of preflight",
          refused and len(ev.read_ledger(root)) == 2)
    root = make_root()
    lock = os.path.join(root, ev.RUNTIME_DIR, ev.LOCK_NAME)
    os.makedirs(os.path.dirname(lock))
    open(lock, "w").close()
    t = FakeTransport([j(live_agent())])
    r, exc = attempt(t, root)
    check("a concurrent start is refused while the ledger lock is held",
          isinstance(exc, ev.SafetyError) and "ledger lock" in str(exc))
    check("the locked-out start made no write to the service", not t.writes)
    os.remove(lock)
    attempt(FakeTransport(happy_sends(), stream=events()), root)
    check("the lock is released after a normal run", not os.path.exists(lock))
    with open(ev.ledger_path(root), "w", encoding="utf-8") as fh:
        fh.write("{ not json")
    try:
        ev.prior_attempts(root, "SYN-CASE-4003")
        refused = False
    except ev.SafetyError:
        refused = True
    check("an unreadable ledger blocks a run rather than reading as empty",
          refused)
    dirs = {ev.new_run_dir(root, "SYN-CASE-4003", stamp="20260920T000000Z")
            for _ in range(200)}
    check("run directories in the same second never collide", len(dirs) == 200)
    root = make_root()
    seen = {}
    t = FakeTransport(happy_sends(), stream=events(),
                      on_stream=lambda: seen.update(e=ev.read_ledger(root)))
    attempt(t, root)
    check("the ledger entry exists at the moment of the model request",
          len(seen.get("e", [])) == 1
          and seen["e"][0]["outcome"].startswith("ATTEMPT_RECORDED"))

    print("\n11. NO SECRET REACHES EVIDENCE OR THE TERMINAL")
    root = make_root()
    leaky = final(text="see https://secret-resource-name.services.ai.azure.com/"
                       "api/projects/secret-project-name Bearer " + FAKE_TOKEN)
    attempt(FakeTransport(happy_sends(leaky), stream=events()), root)
    blob = evidence_text(root)
    check("access token absent from every saved artifact", FAKE_TOKEN not in blob)
    check("resource and project names absent from every saved artifact",
          "secret-resource-name" not in blob and "secret-project-name" not in blob)
    check("the redaction markers are present, so the test is not vacuous",
          "<foundry-resource>" in blob and "<redacted-token>" in blob)
    check("config and client reprs hide the tenant identifiers",
          "secret-" not in repr(CONFIG)
          and "secret-" not in repr(client_for(FakeTransport([]))))
    os.environ["GRIDRESOLVE_FOUNDRY_RESOURCE"] = "secret-resource-name"
    os.environ["GRIDRESOLVE_FOUNDRY_PROJECT"] = "secret-project-name"
    err = ApiError(404, "Not found: https://secret-resource-name.services.ai."
                        "azure.com/api/projects/secret-project-name "
                        "Authorization: Bearer " + FAKE_TOKEN)
    shown = cli._safe(err)
    check("terminal errors are redacted",
          "secret-" not in shown and FAKE_TOKEN not in shown)
    del os.environ["GRIDRESOLVE_FOUNDRY_RESOURCE"]
    del os.environ["GRIDRESOLVE_FOUNDRY_PROJECT"]
    check("terminal errors are token-scrubbed even with no config",
          FAKE_TOKEN not in cli._safe(err))
    red = Redactor("secret-resource-name", "secret-project-name")
    check("the redactor walks nested structures",
          "secret" not in json.dumps(red.data(
              {"a": ["https://secret-resource-name.x/secret-project-name"]})))
    for short in ("ai", "demo", "id"):
        try:
            from_env({"GRIDRESOLVE_FOUNDRY_RESOURCE": short,
                      "GRIDRESOLVE_FOUNDRY_PROJECT": "long-enough-name"})
            refused = False
        except ConfigError:
            refused = True
        check("an identifier short enough to corrupt evidence is refused: %r"
              % short, refused)

    print("\n12. SERVER-SENT EVENT PARSING")
    raw = [b": keepalive\n", b"event: response.created\n",
           b'data: {"type":"response.created","response":{"id":"r1"}}\n', b"\n",
           b'data: {"type":"x",\n', b'data: "k":1}\n', b"\r\n",
           b"data: not json\n", b"\n", b"data: [DONE]\n", b"\n",
           b'data: {"type":"tail"}\n']
    parsed = list(parse_sse(raw))
    check("comments and the [DONE] sentinel are skipped",
          [e["type"] for e in parsed] == ["response.created", "x",
                                          "runner.unparsed", "tail"],
          str([e["type"] for e in parsed]))
    check("multi-line data fields are joined", parsed[1].get("k") == 1)
    check("an unparseable payload is kept as evidence, not dropped",
          parsed[2]["raw"] == "not json")
    check("a final event without a trailing blank line is not lost",
          parsed[-1]["type"] == "tail")
    check("a non-object JSON payload cannot crash the runner",
          list(parse_sse([b"data: [1,2]\n", b"\n"]))[0]["type"]
          == "runner.unparsed")

    print("\n13. PRICING ARITHMETIC")
    check("expected scenario matches the documented $0.09",
          round(pricing.SCENARIOS[0].usd, 2) == 0.09)
    check("conservative scenario matches the documented $0.26",
          round(pricing.SCENARIOS[1].usd, 2) == 0.26)
    check("worst case matches the documented $0.33",
          round(pricing.worst_case_usd(), 2) == 0.33)
    check("one million input tokens cost $0.25",
          pricing.cost_usd(1_000_000, 0) == 0.25)
    check("one million output tokens cost $2.00",
          pricing.cost_usd(0, 1_000_000) == 2.00)
    for bad in ((-1, 0, 0), (0, -1, 0), (10, 0, 11)):
        try:
            pricing.cost_usd(*bad)
            rejected = False
        except ValueError:
            rejected = True
        check("rejects invalid token counts %s" % (bad,), rejected)
    check("the price source is stated, not implied live",
          "not a live quote" in pricing.PRICE_SOURCE)

    print("\n14. ONLY SYNTHETIC DATA, AND NEVER THE ANSWER")
    root = make_root()
    path = os.path.join(root, "submission", "SYN-CASE-4003_input.json")
    original_doc = json.load(open(path, encoding="utf-8"))

    def rewrite(mutator):
        doc = json.loads(json.dumps(original_doc))
        mutator(doc)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh)

    def refused_with(fragment):
        try:
            case_mod.load("SYN-CASE-4003", root=root)
            return False
        except case_mod.CaseError as e:
            return fragment in str(e)

    rewrite(lambda d: d.update(data_classification="PRODUCTION"))
    check("a case not marked SYNTHETIC_ONLY is refused",
          refused_with("SYNTHETIC_ONLY"))
    rewrite(lambda d: d["synthetic_account_records"].update(account_id="ACCT-9912"))
    check("a non synthetic account identifier is refused", refused_with("SYN-"))
    rewrite(lambda d: d.update(answer_key="GRIDRESOLVE_ESCALATE"))
    check("an answer under an unlisted top-level key is refused",
          refused_with("unexpected top level"))
    rewrite(lambda d: d["synthetic_account_records"].update(gold_label="X"))
    check("an answer under an unlisted record key is refused",
          refused_with("unexpected synthetic_account_records"))
    rewrite(lambda d: d.update(customer_request="Bill up. ground_truth: fine."))
    check("a marker inside an allowed field is still refused",
          refused_with("ground_truth"))
    rewrite(lambda d: d.update(case_id="SYN-CASE-9999"))
    check("a mismatched case id is refused", refused_with("case_id"))
    try:
        case_mod.load("REAL-CUSTOMER-1", root=root)
        refused = False
    except case_mod.CaseError:
        refused = True
    check("an unknown case id is refused", refused)
    real = case_mod.load("SYN-CASE-4003")
    check("the committed canonical case passes every guard",
          real.case_id == "SYN-CASE-4003" and len(real.sha256) == 64)

    print("\n15. COMMAND LINE AND STRUCTURE")
    try:
        from_env({})
        refused = False
    except ConfigError:
        refused = True
    check("missing environment is refused with a clear message", refused)
    parser = cli._build_parser()
    for label, argv in (("--confirm", ["execute", "--max-usd", "1"]),
                        ("--max-usd", ["execute", "--confirm", PHRASE])):
        try:
            with contextlib.redirect_stderr(io.StringIO()):  # argparse usage text
                parser.parse_args(argv)
            accepted = True
        except SystemExit:
            accepted = False
        check("execute without %s is rejected by the parser" % label, not accepted)
    check("the bare command resolves to the free preflight",
          parser.parse_args([]).command is None)
    narrow = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
    real_stdout = sys.stdout
    sys.stdout = narrow
    try:
        cli._harden_console()
        print("model text with an unencodable character: ☃ 中")
        narrow.flush()
        survived = True
    except UnicodeEncodeError:
        survived = False
    finally:
        sys.stdout = real_stdout
    check("unencodable model output cannot crash the console after a run",
          survived)
    source = ""
    for name in sorted(os.listdir(os.path.join(ROOT, "runner"))):
        if name.endswith(".py"):
            source += open(os.path.join(ROOT, "runner", name),
                           encoding="utf-8").read()
    check("the model request is issued from exactly one call site",
          source.count(".stream_response(") == 1,
          "count=%d" % source.count(".stream_response("))
    check("no retry or backoff library is imported",
          not any(lib in source for lib in ("import tenacity", "import backoff",
                                            "urllib3.util.retry", "Retry(")))

    print("\n" + "=" * 72)
    print("RESULT: %d passed, %d failed" % (len(checks), len(fails)))
    print("=" * 72)
    if fails:
        for n, d in fails:
            print("  - %s %s" % (n, d))
        return 1
    print("\nEvery API response above was mocked. No model was called.")
    print("These results are not Foundry execution evidence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
