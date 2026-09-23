"""Preflight and execution of one workflow run.

The default path through this module makes no model request. `preflight` is
offline and free. `live_blockers` is a read-only GET. `execute_once` is the only
function that can bill, it sends exactly one model request, and it never retries.

If anything goes wrong after that request is accepted, recovery means observing
the SAME response by its id. No code path here sends a second one.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Final

from . import analysis as analysis_mod
from . import case as case_mod
from . import config as cfg
from . import evidence as ev
from . import foundry, pricing, workflow_map
from . import workflow_versions as wv
from .redaction import for_config
from .transport import (StreamInterrupted, ThrottledError, TimeoutExceeded,
                        TransportError)

CONFIRM_PHRASE = "APPROVE ONE SYNTHETIC DEMO RUN"
DEFAULT_POLL_SECONDS = 10.0
DEFAULT_DEADLINE_SECONDS = 1500.0
STREAM_END_EVENTS = ("response.completed", "response.failed",
                     "response.incomplete", "response.cancelled")


@dataclass(frozen=True)
class Preflight:
    """Everything the operator needs to decide, computed without spending."""

    case_id: str
    case_sha256: str
    case_path: str
    endpoint: str
    request_preview: str
    scenarios: tuple[pricing.Scenario, ...]
    cap_usd: float | None
    prior_attempt_count: int
    blockers: tuple[str, ...]

    @property
    def worst_case_usd(self) -> float:
        return max(s.usd for s in self.scenarios)

    @property
    def can_execute(self) -> bool:
        return not self.blockers


def preflight(config: cfg.RunnerConfig, case_id: str, cap_usd: float | None,
              root: str = case_mod.ROOT,
              client: foundry.FoundryAgentClient | None = None,
              allow_additional: bool = False) -> Preflight:
    """Validate everything that can be validated with no network call at all."""
    loaded = case_mod.load(case_id, root=root)
    agent = client or foundry.FoundryAgentClient(config)
    redactor = for_config(config)

    blockers: list[str] = []
    prior = ev.prior_attempts(root, case_id)
    if prior and not allow_additional:
        blockers.append(
            "%d previous run attempt(s) are recorded for %s. A further billable "
            "run needs --allow-additional-run." % (len(prior), case_id))

    # Every agent is told to preserve workflow_version from shared state, so the
    # label in the case input is what the terminal audit record will carry. It
    # has to name the version this runner targets, which live_blockers in turn
    # ties to the version actually deployed.
    expected_label = "%s v%s" % (config.agent_name, wv.active_version())
    declared_label = loaded.document.get("workflow_version")
    if declared_label != expected_label:
        blockers.append(
            "The case input declares workflow_version %r, but this run targets "
            "%r. The audit record would name the wrong version."
            % (declared_label, expected_label))

    worst = pricing.worst_case_usd()
    if cap_usd is None:
        blockers.append("No spending cap was given. Pass --max-usd.")
    elif cap_usd <= 0:
        blockers.append("The spending cap must be greater than zero.")
    elif cap_usd < worst:
        blockers.append(
            "The cap of $%.2f is below the modelled worst case of $%.2f. Raise "
            "the cap or decline the run." % (cap_usd, worst))

    return Preflight(
        case_id=loaded.case_id,
        case_sha256=loaded.sha256,
        case_path=loaded.path,
        endpoint=redactor.text(config.responses_url()),
        request_preview=redactor.text(
            agent.describe_request(case_mod.build_input(loaded))),
        scenarios=pricing.SCENARIOS,
        cap_usd=cap_usd,
        prior_attempt_count=len(prior),
        blockers=tuple(blockers),
    )


def live_blockers(client: foundry.FoundryAgentClient) -> tuple[str, ...]:
    """One read-only GET confirming the run would hit the intended workflow.

    Guards against the workflow having been republished, disabled or re-routed
    between the readiness review and the run. The action identifiers used to
    interpret the run belong to one specific version.
    """
    agent = client.get_agent()
    found: list[str] = []
    if not isinstance(agent, dict):
        return ("The workflow agent could not be read.",)
    latest = (agent.get("versions") or {}).get("latest") or {}
    version = str(latest.get("version", ""))
    wm = wv.active()
    if version != wm.WORKFLOW_VERSION:
        found.append("The live workflow is v%s, but this runner interprets v%s."
                     % (version or "unknown", wm.WORKFLOW_VERSION))
    if latest.get("draft") is not False:
        found.append("The latest workflow version is a draft.")
    if agent.get("state") != "enabled":
        found.append("The workflow agent state is %r, not enabled."
                     % agent.get("state"))
    definition = (latest.get("definition") or {}).get("workflow") or ""
    missing = [a for a in wm.AGENT_ACTIONS if a not in definition]
    if missing:
        found.append("The live definition lacks %d expected action id(s), so "
                     "its events could not be interpreted." % len(missing))
    if wm.APPROVED_TOKEN not in definition:
        found.append("The live definition no longer contains the approval "
                     "sentinel.")
    return tuple(found)


_BARE_TABLE_GATE = re.compile(r'condition:\s*=?\(?\s*"[^"]+"\s+in\s+Local\.\w+\s*\)?\s*$',
                              re.MULTILINE)
_CASE_VERDICT = re.compile(r"(SYN-CASE-\d{4})[^\n]*unsupported", re.IGNORECASE)
# Plain, quoted, and block-scalar (`activity: |-` then `=...` on the next line).
_EXPRESSION_ACTIVITY = re.compile(
    r"""^\s*activity:\s*(?:[|>][-+0-9]*[ \t]*\r?\n\s*)?['"]?=""", re.MULTILINE)


def configuration_defects(client: foundry.FoundryAgentClient,
                          case_id: str) -> tuple[str, ...]:
    """Known defects in the live configuration that would undermine a run.

    Read-only. Both were found by reading the deployed configuration on
    2026-09-20, and the runner refuses to spend money against them unless the
    operator explicitly accepts them.
    """
    found: list[str] = []
    agent = client.get_agent()
    latest = ((agent or {}).get("versions") or {}).get("latest") or {}
    definition = (latest.get("definition") or {}).get("workflow") or ""
    if _BARE_TABLE_GATE.search(definition):
        found.append(
            "GATE: the compliance gate applies `in` directly to a variable "
            "filled by `output.messages`, which is a table of message records, "
            "not text. Power Fx rejects that expression (\"Invalid schema, "
            "expected a one-column table\"), and the open-source workflow "
            "engine throws when a condition is not boolean. Microsoft's samples "
            "use Last(<var>).Text or MessageText(<var>). Reproduce with "
            "`dotnet run --project tests/powerfx_gate`.")
    if _EXPRESSION_ACTIVITY.search(definition):
        found.append(
            "RELEASE: a SendActivity `activity` starts with `=`. That field is a "
            "template, not an expression, so the hosted service sends the text "
            "literally. The first real run delivered "
            "\"=Last(Local.VarCustomerDraft).Text\" to the customer instead of "
            "the draft. Microsoft's documentation and samples embed formulas as "
            "{...}. Reproduce with `dotnet run --project tests/powerfx_gate`.")
    listed = client.list_agents()
    found.extend(_release_contract_defects(definition, listed))
    found.extend(_invocation_contract_defects(definition, listed))
    for entry in (listed or {}).get("data", []) if isinstance(listed, dict) else []:
        definition = ((entry.get("versions") or {}).get("latest") or {}).get(
            "definition") or {}
        instructions = str(definition.get("instructions") or "")
        for match in _CASE_VERDICT.finditer(instructions):
            if match.group(1) == case_id:
                found.append(
                    "CONTAMINATION: %s's instructions state the expected "
                    "conclusion for %s (\"%s\"), so a run cannot show the "
                    "workflow reached it from the records alone."
                    % (entry.get("name"), case_id, match.group(0)[:90]))
    return tuple(found)


CUSTOMER_FIELDS: Final = tuple(f for _h, f in workflow_map.RELEASE_FIELDS)


def _release_contract_defects(definition: str, listed: object) -> list[str]:
    """The release template reads fields of the communication agent's JSON.

    The open-source engine fails the run when a referenced field is absent, and
    that cannot be caught in Power Fx because it is a binding error. A strict
    JSON schema on the agent is what guarantees every field, so the runner
    refuses to spend money unless it is in place.
    """
    if "Local.VarCustomerMessage." not in definition:
        return []
    found: list[str] = []
    if "responseObject: Local.VarCustomerMessage" not in definition:
        found.append("RELEASE-SCHEMA: the release template reads "
                     "Local.VarCustomerMessage, but no agent output is saved to "
                     "it with responseObject.")
    entries = (listed or {}).get("data", []) if isinstance(listed, dict) else []
    agent = next((e for e in entries
                  if e.get("name") == "CustomerCommunicationAgent"), None)
    latest = ((agent or {}).get("versions") or {}).get("latest") or {}
    fmt = (((latest.get("definition") or {}).get("text") or {}).get("format")
           or {})
    schema = fmt.get("schema") if isinstance(fmt.get("schema"), dict) else {}
    required = set(schema.get("required") or [])
    missing = [f for f in CUSTOMER_FIELDS if f not in required]
    if fmt.get("type") != "json_schema" or fmt.get("strict") is not True \
            or missing:
        found.append(
            "RELEASE-SCHEMA: CustomerCommunicationAgent must return a strict "
            "json_schema output that requires every customer-facing field the "
            "release template reads. Found type=%r strict=%r, not required: %s."
            % (fmt.get("type"), fmt.get("strict"), ", ".join(missing) or "none"))
    return found


# Agents whose work is only usable downstream as a JSON object, and the key whose
# absence made an earlier real run useless. A strict schema makes a reply that
# only announces the work impossible, which is what both real runs suffered.
SCHEMA_AGENTS: Final = (
    ("AccountEvidenceAgent", "evidence_ledger"),
    ("PolicyKnowledgeAgent", "policy_ledger"),
    ("CaseAuditAgent", "message_compliance_decision"),
)
_EMPTY_INPUT = re.compile(r"""^\s*messages:\s*(?:""|'')\s*$""", re.MULTILINE)


def _format_of(listed: object, agent_name: str) -> dict:
    entries = (listed or {}).get("data", []) if isinstance(listed, dict) else []
    agent = next((e for e in entries if e.get("name") == agent_name), None)
    latest = ((agent or {}).get("versions") or {}).get("latest") or {}
    return (((latest.get("definition") or {}).get("text") or {}).get("format") or {})


def _invocation_contract_defects(definition: str, listed: object) -> list[str]:
    """Both real runs lost agents that were invoked with an empty input on a
    shared conversation ending in another agent's turn. The runner will not
    spend money on that design again."""
    found: list[str] = []
    empty = len(_EMPTY_INPUT.findall(definition))
    if empty:
        found.append(
            "INVOCATION-INPUT: %d agent node(s) pass an empty input message. In "
            "both real runs an agent invoked that way mistook the previous "
            "agent's output for its own turn and produced no work." % empty)
    if "WORKFLOW STEP" not in definition:
        return found
    if '"""evidence_id"""' not in definition or '"""policy_id"""' not in definition:
        found.append(
            "INVESTIGATION-GUARD: the release gate does not require the evidence "
            "and policy stages to have produced structured output, so an "
            "incomplete investigation could still be released.")
    for agent_name, key in SCHEMA_AGENTS:
        fmt = _format_of(listed, agent_name)
        schema = fmt.get("schema") if isinstance(fmt.get("schema"), dict) else {}
        if fmt.get("type") != "json_schema" or fmt.get("strict") is not True \
                or key not in (schema.get("required") or []):
            found.append(
                "OUTPUT-SCHEMA: %s must return a strict json_schema output that "
                "requires %s. Found type=%r strict=%r."
                % (agent_name, key, fmt.get("type"), fmt.get("strict")))
    return found


@dataclass(frozen=True)
class RunResult:
    """What actually happened. Nothing here is inferred."""

    case_id: str
    run_dir: str
    response_id: str
    conversation_id: str
    status: str
    usage: pricing.Usage
    event_count: int
    elapsed_seconds: float
    output_text: str
    cap_usd: float
    route: dict = field(default_factory=dict)
    analysis: dict = field(default_factory=dict)
    stream_interrupted: bool = False
    polls: int = 0
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def usd(self) -> float:
        return self.usage.usd if self.usage.reported else 0.0

    @property
    def over_cap(self) -> bool:
        return self.usage.reported and self.usd > self.cap_usd


def extract_output_text(response: dict) -> str:
    """Prefer the convenience field, fall back to walking the output items."""
    direct = response.get("output_text")
    if isinstance(direct, str) and direct:
        return direct
    parts: list[str] = []
    for item in response.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        for block in item.get("content", []) or []:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
    return "\n".join(parts)


def _workflow_action(event: dict) -> dict | None:
    """The workflow_action item carried by an output_item event, if any."""
    if event.get("type") not in ("response.output_item.added",
                                 "response.output_item.done"):
        return None
    item = event.get("item")
    if isinstance(item, dict) and item.get("type") == "workflow_action":
        return item
    return None


def _response_id_of(event: dict) -> str:
    response = event.get("response")
    if isinstance(response, dict) and isinstance(response.get("id"), str):
        return response["id"]
    return ""


def execute_once(config: cfg.RunnerConfig, case_id: str, cap_usd: float,
                 confirm_phrase: str, root: str = case_mod.ROOT,
                 client: foundry.FoundryAgentClient | None = None,
                 allow_additional: bool = False,
                 accept_known_defects: bool = False,
                 poll_seconds: float = DEFAULT_POLL_SECONDS,
                 deadline_seconds: float = DEFAULT_DEADLINE_SECONDS,
                 sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic) -> RunResult:
    """Run the workflow once. The only billable path in this package."""
    if confirm_phrase != CONFIRM_PHRASE:
        raise ev.SafetyError(
            "Refusing to run. The confirmation phrase must be exactly %r."
            % CONFIRM_PHRASE)

    agent = client or foundry.FoundryAgentClient(config)
    checks = preflight(config, case_id, cap_usd, root=root, client=agent,
                       allow_additional=allow_additional)
    if not checks.can_execute:
        raise ev.SafetyError("Refusing to run:\n  - "
                             + "\n  - ".join(checks.blockers))
    live = live_blockers(agent)
    if live:
        raise ev.SafetyError("Refusing to run, the live workflow is not as "
                             "reviewed:\n  - " + "\n  - ".join(live))
    if not accept_known_defects:
        defects = configuration_defects(agent, case_id)
        if defects:
            raise ev.SafetyError(
                "Refusing to run against known configuration defects:\n  - "
                + "\n  - ".join(defects) + "\nFix them, or pass "
                "--accept-known-defects to run anyway with that on the record.")

    loaded = case_mod.load(case_id, root=root)
    redactor = for_config(config)
    run_dir = ev.new_run_dir(root, case_id)
    writer = ev.EvidenceWriter(run_dir, redactor)

    # Recorded before any write to the service, so a crash cannot hide a run.
    ev.claim_run_slot(root, case_id, run_dir, allow_additional)
    writer.write_json("00_preflight.json", {
        "case_id": checks.case_id,
        "case_sha256": checks.case_sha256,
        "workflow": config.agent_name,
        "workflow_version": wv.active_version(),
        "request_preview": checks.request_preview,
        "cap_usd": cap_usd,
        "price_source": pricing.PRICE_SOURCE,
        "estimates_usd": {s.name: s.usd for s in checks.scenarios},
        "retries_enabled": False,
        "started_at": ev.utc_iso(),
    })

    def abort(outcome: str, exc: BaseException) -> None:
        ev.close_run_slot(root, run_dir, outcome, str(exc))
        writer.write_text("99_error.txt", str(exc))

    try:
        conversation = agent.create_conversation()
    except TransportError as exc:
        abort("FAILED_BEFORE_MODEL_REQUEST", exc)
        raise
    conversation_id = str(conversation.get("id", "")) if isinstance(
        conversation, dict) else ""
    if not conversation_id:
        exc = TransportError("The service created no conversation id, so the "
                             "workflow was not started. Nothing was billed.")
        abort("FAILED_BEFORE_MODEL_REQUEST", exc)
        raise exc
    writer.write_json("01_conversation.json", {"conversation_id": conversation_id})

    started = clock()
    response_id = ""
    status = "unknown"
    event_count = 0
    actions: list[dict] = []
    interrupted = False
    notes: list[str] = []

    try:
        events = agent.stream_response(case_mod.build_input(loaded),
                                       conversation_id)
        for event in events:
            event_count += 1
            writer.append_jsonl("02_events.jsonl", event)
            if not response_id:
                response_id = _response_id_of(event)
                if response_id:
                    # Written the moment it is known: this id is the only handle
                    # on a run that may outlive this process.
                    writer.write_json("03_response_id.json", {
                        "response_id": response_id,
                        "conversation_id": conversation_id,
                        "recover_with": "python -m runner report --response-id "
                                        "%s --conversation-id %s"
                                        % (response_id, conversation_id)})
            action = _workflow_action(event)
            if action is not None:
                actions.append({"event": event.get("type"),
                                "action_id": action.get("action_id"),
                                "kind": action.get("kind"),
                                "status": action.get("status"),
                                "previous_action_id":
                                    action.get("previous_action_id")})
            if event.get("type") in STREAM_END_EVENTS:
                status = foundry.status_of(event.get("response")) \
                    if isinstance(event.get("response"), dict) else status
                break
            if event.get("type") == "error":
                notes.append("The stream carried an error event: %s"
                             % str(event)[:300])
            if clock() - started > deadline_seconds:
                interrupted = True
                notes.append("The overall deadline passed while streaming.")
                break
        else:
            if not foundry.is_terminal(status):
                interrupted = True
    except StreamInterrupted as exc:
        interrupted = True
        notes.append(str(exc))
    except ThrottledError as exc:
        abort("THROTTLED" if not response_id
              else "THROTTLED_AFTER_START_RUN_MAY_CONTINUE", exc)
        raise
    except TransportError as exc:
        abort("FAILED_BEFORE_COMPLETION" if not response_id
              else "FAILED_AFTER_START_RUN_MAY_CONTINUE", exc)
        raise

    writer.write_json("04_workflow_actions.json", actions)

    if not response_id:
        exc = TransportError(
            "The stream ended without ever reporting a response id, so the run "
            "cannot be retrieved. It may or may not have started. Check the "
            "Foundry portal and Azure Cost Management before any further run. "
            "Conversation id: %s" % conversation_id)
        abort("NO_RESPONSE_ID_STATE_UNKNOWN", exc)
        raise exc

    # Observe the same response until it is terminal. Never a new request.
    polls = 0
    latest: dict = {}
    while True:
        try:
            fetched = agent.get_response(response_id)
        except TransportError as exc:
            abort("POLLING_FAILED_RUN_MAY_CONTINUE",
                  RuntimeError("response %s: %s" % (response_id, exc)))
            raise
        latest = fetched if isinstance(fetched, dict) else {}
        status = foundry.status_of(latest)
        writer.append_jsonl("05_poll_log.jsonl", {
            "at": ev.utc_iso(), "poll": polls, "status": status})
        if foundry.is_terminal(status):
            break
        if clock() - started > deadline_seconds:
            ev.close_run_slot(root, run_dir, "TIMED_OUT_STILL_RUNNING",
                              "response %s last seen %s" % (response_id, status))
            raise TimeoutExceeded(
                "The run did not reach a terminal status within %.0fs. Last "
                "status was %r. It may still be running and may still bill. Do "
                "not start another run: retrieve this one with `python -m "
                "runner report --response-id %s --conversation-id %s`."
                % (deadline_seconds, status, response_id, conversation_id),
                response_id=response_id)
        sleep(poll_seconds)
        polls += 1

    elapsed = clock() - started
    writer.write_json("06_final_response.json", latest)

    usage = pricing.usage_from_response(latest)
    if not usage.reported:
        notes.append(
            "The API returned no usable usage block, so the token count and "
            "cost of this run are unmeasured. Read them from Azure Cost "
            "Management before running again.")
    conversation_items: object = None
    try:
        conversation_items = agent.get_conversation_items(conversation_id)
        writer.write_json("07_conversation_items.json", conversation_items)
    except TransportError as exc:
        notes.append("Conversation items could not be read: %s" % exc)

    # Platform metadata first. The response's own output is the fallback.
    items = analysis_mod.items_of(conversation_items) \
        or analysis_mod.items_of(latest)
    analysis = analysis_mod.analyze(
        items, actions, config.agent_name,
        "%s v%s" % (config.agent_name, wv.active_version()),
        route_map=wv.active())
    route = analysis["route"]
    release = analysis["release"]
    if release["outcome"] != analysis_mod.RELEASE_NOT_RELEASED \
            and not release["customer_ready"]:
        notes.append("The release step did not deliver the drafted message: %s."
                     % release["outcome"])
    if release["identifiers_in_release"]:
        notes.append("Identifiers appear in the released customer message: %s."
                     % ", ".join(release["identifiers_in_release"]))
    for bad in analysis["unhealthy_outputs"]:
        notes.append("%s did not return its required output: %s."
                     % (bad["agent"], ", ".join(bad["problems"])))
    for finding in analysis["case_follow_up"]["findings"]:
        notes.append("Case follow-up: " + finding)
    for finding in analysis["audit"].get("findings", []):
        notes.append("Audit record: " + finding)
    if not actions:
        notes.append("No workflow_action events were observed, so the branch "
                     "taken cannot be established from the stream.")
    output_text = extract_output_text(latest)
    writer.write_text("08_output.txt", output_text or "(no output text returned)")

    result = RunResult(
        case_id=case_id, run_dir=run_dir, response_id=response_id,
        conversation_id=conversation_id, status=status, usage=usage,
        event_count=event_count, elapsed_seconds=elapsed,
        output_text=output_text, cap_usd=cap_usd, route=route,
        analysis=analysis, stream_interrupted=interrupted, polls=polls,
        notes=tuple(notes))

    writer.write_json("09_route.json", route)
    writer.write_json("11_run_analysis.json", analysis)
    writer.write_text("10_usage_report.md", usage_report(result))
    ev.close_run_slot(root, run_dir, "COMPLETED_STATUS_" + status.upper(),
                      "response %s" % response_id)
    return result


def _analysis_lines(analysis: dict) -> list[str]:
    """Rows and a table built from platform metadata, never from agent prose."""
    if not analysis:
        return []
    release = analysis.get("release", {})
    audit = analysis.get("audit", {})
    lines = [
        "| Compliance token | %s |" % analysis.get("compliance", {}).get(
            "token", analysis_mod.NOT_OBSERVED),
        "| Release step | %s |" % release.get("outcome",
                                              analysis_mod.NOT_OBSERVED),
        "| Customer-ready message | %s |" % (
            "yes" if release.get("customer_ready") else "no"),
        "| Case follow-up, planner token | %s |" % analysis.get(
            "case_follow_up", {}).get("planner_token", analysis_mod.NOT_OBSERVED),
        "| Case follow-up, observed | %s |" % analysis.get(
            "case_follow_up", {}).get("observed", analysis_mod.NOT_OBSERVED),
        "| Audit record accurate | %s |" % (
            "not observed" if not audit.get("audit_parsed")
            else "yes" if audit.get("accurate") else "NO, see notes"),
        "",
        "## Agents the platform invoked",
        "",
        "From `created_by.agent` on each conversation item, not from any "
        "agent's own account of the run.",
        "",
        "| # | Agent | Version | Output chars |",
        "| --- | --- | --- | --- |",
    ]
    for index, entry in enumerate(analysis.get("participation", []), 1):
        lines.append("| %d | %s | %s | %d |" % (
            index, entry["agent"], entry["version"], entry["output_chars"]))
    return lines


def usage_report(result: RunResult) -> str:
    """Post-execution report. Measured values only, or an explicit absence."""
    route = result.route or {}
    lines = [
        "# Run report: %s" % result.case_id,
        "",
        "| Field | Value |",
        "| --- | --- |",
        "| Response id | `%s` |" % (result.response_id or "none returned"),
        "| Conversation id | `%s` |" % (result.conversation_id or "none"),
        "| Final status | **%s** |" % result.status,
        "| Stream events | %d |" % result.event_count,
        "| Stream interrupted | %s |" % ("yes" if result.stream_interrupted
                                         else "no"),
        "| Elapsed | %.1fs |" % result.elapsed_seconds,
        "| Route observed | **%s** |" % route.get("route", "NOT_OBSERVED"),
        "| Gate evaluated | %s |" % ("observed" if route.get("gate_evaluated")
                                     else "not observed"),
        "| Audit ran | %s |" % ("observed" if route.get("audit_ran")
                                else "not observed"),
        "| Agents observed | %s |" % (", ".join(route.get("agents_observed", []))
                                      or "none"),
    ]
    lines += _analysis_lines(result.analysis)
    lines += [
        "",
        "## Token usage and cost",
        "",
    ]
    if result.usage.reported:
        lines += [
            "| Measure | Value |",
            "| --- | --- |",
            "| Input tokens | %d |" % result.usage.input_tokens,
            "| Cached input tokens | %d |" % result.usage.cached_input_tokens,
            "| Output tokens | %d |" % result.usage.output_tokens,
            "| Total tokens | %d |" % result.usage.total_tokens,
            "| **Cost** | **$%.4f** |" % result.usd,
            "| Approved cap | $%.2f |" % result.cap_usd,
            "| Within cap | %s |" % ("no" if result.over_cap else "yes"),
            "",
            "Prices: %s" % pricing.PRICE_SOURCE,
            "",
            "Whether this usage block covers all nine inner agent calls or only "
            "part of the run is not documented. Reconcile it against Azure Cost "
            "Management before treating it as the full cost.",
        ]
    else:
        lines += [
            "The API returned no usable usage block for this run, so the cost "
            "is **unmeasured**. It is not zero. Read the actual amount from "
            "Azure Cost Management before approving another run.",
        ]
    if result.notes:
        lines += ["", "## Notes", ""] + ["- " + n for n in result.notes]
    return "\n".join(lines) + "\n"
