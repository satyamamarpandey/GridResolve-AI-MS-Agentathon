"""What a finished run actually did, read from the items the service returned.

Pure functions over captured data: no network, no model, no cost. They work on
the live result of a run and equally on the evidence files of an earlier one.

Every conversation item carries `created_by.agent`, the name and version of the
agent the platform actually invoked. That is the authoritative record of who
took part. An audit written by a language model cannot see it, which is why the
first real run's audit listed four agents and invented their versions. Items in
a response's `output` carry the same fact as `agent_reference`.
"""
from __future__ import annotations

import json
import os
import re
from typing import Final

from . import workflow_map

RELEASE_NOT_RELEASED = "NOT_RELEASED"
RELEASE_CUSTOMER_MESSAGE = "DELIVERED_CUSTOMER_MESSAGE"
RELEASE_DELIVERED_DRAFT = "DELIVERED_WHOLE_DRAFT"
RELEASE_UNEVALUATED = "UNEVALUATED_EXPRESSION"
RELEASE_OTHER_TEXT = "DELIVERED_OTHER_TEXT"
RELEASE_EMPTY = "DELIVERED_EMPTY_TEXT"

NOT_OBSERVED = "NOT_OBSERVED"
NOT_INVOKED = "NOT_INVOKED"

# Identifiers that belong in the case record, not in a customer message.
_INTERNAL_ID = re.compile(
    r"\b(?:SYN|POL|ADJ|MTR)-[A-Z0-9][A-Z0-9-]*|\bCL?-\d{2,}\b|\binternal_\w+")

# A workflow variable reference such as Local.VarCustomerDraft. Ordinary prose
# that happens to contain "Local." followed by a space does not match.
_VARIABLE_REFERENCE = re.compile(r"\b(?:Local|System|Global)\.[A-Za-z_]")


def items_of(payload: object) -> list[dict]:
    """Items from a conversation listing, a response, or a bare list."""
    if isinstance(payload, dict):
        payload = payload.get("data", payload.get("output", []))
    return [i for i in payload if isinstance(i, dict)] \
        if isinstance(payload, list) else []


def _agent_of(item: dict) -> dict:
    created_by = item.get("created_by")
    agent = created_by.get("agent") if isinstance(created_by, dict) else None
    if not isinstance(agent, dict):
        agent = item.get("agent_reference")
    return agent if isinstance(agent, dict) else {}


def _inner_response_id(item: dict) -> str:
    created_by = item.get("created_by")
    found = created_by.get("response_id") if isinstance(created_by, dict) else None
    found = found or item.get("response_id")
    return found if isinstance(found, str) else ""


def text_of(item: dict) -> str:
    parts = [b.get("text") for b in item.get("content", []) or []
             if isinstance(b, dict) and isinstance(b.get("text"), str)]
    return "".join(parts)


def _assistant_messages(items: list[dict]) -> list[dict]:
    return [i for i in items if i.get("type") == "message"
            and i.get("role") == "assistant"]


def participation(items: list[dict], workflow_name: str) -> list[dict]:
    """One entry per agent message, in order, as the platform recorded it."""
    found = []
    for item in _assistant_messages(items):
        agent = _agent_of(item)
        name = agent.get("name")
        if not isinstance(name, str) or name == workflow_name:
            continue
        found.append({
            "agent": name,
            "version": str(agent.get("version") or NOT_OBSERVED),
            "inner_response_id": _inner_response_id(item) or NOT_OBSERVED,
            "output_chars": len(text_of(item)),
        })
    return found


# An agent that stops to ask instead of working. Seen once for real: in the first
# run AccountEvidenceAgent replied "If you want, I will now produce ... Please
# confirm to proceed" and produced no evidence ledger.
_ASKS_INSTEAD_OF_WORKING = re.compile(
    r"please confirm|confirm to proceed|if you want,? i (?:will|can)|"
    r"would you like me to|shall i (?:proceed|continue|produce)|"
    r"let me know (?:if|when|whether)", re.IGNORECASE)


# Both real runs contained a reply of this kind: one sentence promising the work,
# then the end of the turn. It is not a completed investigation.
_ANNOUNCES_FUTURE_WORK = re.compile(
    r"\bi(?:'ll| will| shall| am going to)\s+(?:now\s+)?(?:produce|provide|generate|"
    r"prepare|create|build|return|output|compile)\b|\bnow i will\b|"
    r"\bthis will be the final\b", re.IGNORECASE)

# The least an investigation stage must return for its work to count as done. A
# key in REQUIRED_LISTS must hold at least one entry carrying the named id.
STAGE_AGENTS: Final = ("AccountEvidenceAgent", "UsageAnomalyAgent", "PolicyKnowledgeAgent")
REQUIRED_LISTS: Final = {
    "AccountEvidenceAgent": (("evidence_ledger", "evidence_id"),),
    "PolicyKnowledgeAgent": (("policy_ledger", "policy_id"),),
}
REQUIRED_TEXT: Final = {
    "UsageAnomalyAgent": ("usage_summary",),
    "EvidenceComplianceAgent": ("decision",),
}


def _contract_problems(name: str, output: dict) -> list[str]:
    problems = []
    for key, entry_id in REQUIRED_LISTS.get(name, ()):
        value = output.get(key)
        if not isinstance(value, list):
            problems.append("MISSING:" + key)
        elif not any(isinstance(e, dict) and str(e.get(entry_id) or "").strip()
                     for e in value):
            problems.append("EMPTY:" + key)
    for key in REQUIRED_TEXT.get(name, ()):
        if not str(output.get(key) or "").strip():
            problems.append("MISSING:" + key)
    if name == "EvidenceComplianceAgent" \
            and not str(output.get("compliance_summary") or "").strip() \
            and not output.get("failed_checks"):
        problems.append("NO_REASONS")
    return problems


def output_health(items: list[dict], workflow_name: str) -> list[dict]:
    """Agents whose output is not the work their contract requires."""
    unhealthy = []
    for item in _assistant_messages(items):
        name = _agent_of(item).get("name")
        if not isinstance(name, str) or name == workflow_name:
            continue
        text = text_of(item)
        problems = []
        output = _json_object_in(text)
        if output is None:
            problems.append("NO_JSON_OBJECT")
        if _ASKS_INSTEAD_OF_WORKING.search(text):
            problems.append("ASKS_FOR_CONFIRMATION")
        if output is None and _ANNOUNCES_FUTURE_WORK.search(text):
            problems.append("ANNOUNCES_FUTURE_WORK")
        problems += _contract_problems(name, output or {})
        if problems:
            unhealthy.append({"agent": name, "problems": problems,
                              "output_chars": len(text),
                              "preview": text[:120]})
    return unhealthy


def investigation(observed: list[dict], unhealthy: list[dict]) -> dict:
    """Did every investigation stage the platform ran return its work?"""
    ran = {p["agent"] for p in observed}
    bad = {u["agent"] for u in unhealthy}
    incomplete = [name for name in STAGE_AGENTS if name in ran and name in bad]
    not_run = [name for name in STAGE_AGENTS if name not in ran]
    return {"complete": not incomplete and not not_run,
            "incomplete_stages": incomplete, "stages_not_run": not_run}


def _last_text_by(items: list[dict], agent_name: str) -> str | None:
    texts = [text_of(i) for i in _assistant_messages(items)
             if _agent_of(i).get("name") == agent_name]
    return texts[-1] if texts else None


def compliance_decision(items: list[dict]) -> dict:
    """The route token on the compliance agent's final non-blank line."""
    text = _last_text_by(items, "EvidenceComplianceAgent")
    if text is None:
        return {"token": NOT_OBSERVED, "final_line": NOT_OBSERVED}
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    final = lines[-1] if lines else ""
    if final == workflow_map.APPROVED_TOKEN:
        token = "APPROVED"
    elif final == workflow_map.ESCALATE_TOKEN:
        token = "ESCALATE"
    else:
        token = "NO_VALID_TOKEN"
    return {"token": token, "final_line": final[:120]}


def release_check(items: list[dict], workflow_name: str) -> dict:
    """Did the release step deliver the drafted message, or something else?

    A message authored by the workflow itself is the output of SendActivity.
    """
    sent = [text_of(i) for i in _assistant_messages(items)
            if _agent_of(i).get("name") == workflow_name]
    draft = _last_text_by(items, "CustomerCommunicationAgent")
    if not sent:
        return {"outcome": RELEASE_NOT_RELEASED, "released_chars": 0,
                "draft_chars": len(draft or ""), "released_preview": "",
                "customer_ready": False, "identifiers_in_release": []}
    released = sent[-1]
    draft_object = _json_object_in(draft) if draft else None
    expected = workflow_map.compose_customer_message(draft_object) \
        if draft_object else None
    if expected is not None and _same_text(released, expected):
        outcome = RELEASE_CUSTOMER_MESSAGE
    elif draft is not None and released == draft:
        outcome = RELEASE_DELIVERED_DRAFT
    elif not released.strip():
        outcome = RELEASE_EMPTY
    elif released.lstrip().startswith("=") \
            or _VARIABLE_REFERENCE.search(released):
        outcome = RELEASE_UNEVALUATED
    else:
        outcome = RELEASE_OTHER_TEXT
    return {"outcome": outcome, "released_chars": len(released),
            "draft_chars": len(draft or ""),
            "released_preview": released[:160],
            # Customer-ready means exactly the six customer-facing fields, and
            # never the JSON object. Identifiers found in that prose are listed
            # rather than judged: a bill number may be fine, a policy id is not.
            "customer_ready": outcome == RELEASE_CUSTOMER_MESSAGE,
            "identifiers_in_release": sorted(set(_INTERNAL_ID.findall(released)))}


def _same_text(a: str, b: str) -> bool:
    def norm(text: str) -> str:
        return "\n".join(line.rstrip() for line in
                         text.replace("\r\n", "\n").strip().split("\n"))
    return norm(a) == norm(b)


def case_follow_up(items: list[dict]) -> dict:
    """Question B: does the case itself still need a person?

    Read from the planner, never from the compliance decision on the message.
    """
    text = _last_text_by(items, "ResolutionPlannerAgent")
    if text is None:
        return {"planner_token": NOT_OBSERVED,
                "planner_states_human_review_reason": NOT_OBSERVED}
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    final = lines[-1] if lines else ""
    if final == workflow_map.FOLLOWUP_HUMAN_TOKEN:
        token = "HUMAN_REQUIRED"
    elif final == workflow_map.FOLLOWUP_NONE_TOKEN \
            and text.count(workflow_map.FOLLOWUP_NONE_TOKEN) == 1 \
            and workflow_map.FOLLOWUP_HUMAN_TOKEN.casefold() not in text.casefold():
        token = "NONE_REQUIRED"
    else:
        token = "NO_VALID_TOKEN"
    plan = _json_object_in(text) or {}
    reason = plan.get("human_review_reason")
    return {"planner_token": token,
            "planner_states_human_review_reason":
                bool(isinstance(reason, str) and reason.strip()),
            "planner_resolution_status": plan.get("resolution_status",
                                                  NOT_OBSERVED)}


def _json_object_in(text: str) -> dict | None:
    """The first JSON object in the text. Anything after it is ignored, so a
    trailing route token or prose containing braces cannot hide the object."""
    start = text.find("{")
    if start < 0:
        return None
    try:
        parsed, _end = json.JSONDecoder().raw_decode(text[start:])
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


_NO_HUMAN = ("NO_HUMAN_REVIEW_REQUIRED", "NONE_REQUIRED", "NOT_REQUIRED", "NONE")


def _audit_compliance_decision(audit: dict) -> str | None:
    """The compliance decision as the audit states it, under any name it has used."""
    for key in ("message_compliance_decision", "compliance_decision", "compliance_status",
                "compliance_result"):
        value = audit.get(key)
        if isinstance(value, dict):
            value = value.get("compliance_decision") or value.get("decision")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def audit_check(items: list[dict], workflow_label: str,
                observed: list[dict], follow_up: dict | None = None,
                route: dict | None = None, compliance: dict | None = None,
                unhealthy: list[dict] | None = None) -> dict:
    """Compare the audit agent's record with what the platform recorded.

    The audit is a model-produced statement. `observed`, `route` and the
    planner's own output are the facts it is checked against.
    """
    text = _last_text_by(items, "CaseAuditAgent")
    audit = _json_object_in(text) if text else None
    if audit is None:
        return {"audit_parsed": False, "findings": ["No audit JSON was observed."]}
    findings: list[str] = []
    if audit.get("workflow_version") != workflow_label:
        findings.append("workflow_version is %r, the run used %r."
                        % (audit.get("workflow_version"), workflow_label))
    # The audit's own rule is RUNTIME_FAILED when a required upstream output is
    # missing or malformed, so that value is right exactly when one was.
    status = audit.get("execution_status")
    if status == "RUNTIME_FAILED" and not unhealthy:
        findings.append("execution_status is 'RUNTIME_FAILED', but every output the "
                        "platform recorded was usable.")
    elif status not in ("RUNTIME_EXECUTED", "RUNTIME_FAILED"):
        findings.append("execution_status is %r for a real execution." % status)
    # Approving the customer message must never erase a human review that the
    # case itself still needs.
    needs_human = bool(follow_up) and (
        follow_up.get("planner_token") == "HUMAN_REQUIRED"
        or follow_up.get("planner_states_human_review_reason") is True)
    handed_off = bool(route) and route.get("case_follow_up") == "HANDED_TO_HUMAN"
    for field_name in ("case_human_review_status", "human_review_status"):
        stated = audit.get(field_name)
        if isinstance(stated, str) and stated.upper() in _NO_HUMAN \
                and (needs_human or handed_off):
            findings.append(
                "%s is %r, but %s." % (
                    field_name, stated,
                    "the platform ran a human handoff" if handed_off
                    else "the planner stated that the case needs human review"))
    # The route token is what the workflow acted on. The audit's account of the
    # compliance decision must agree with it.
    if compliance is not None and compliance.get("token") != NOT_OBSERVED:
        stated = _audit_compliance_decision(audit)
        approved = compliance["token"] == "APPROVED"
        if stated is None:
            findings.append("The audit records no compliance decision. The platform "
                            "observed the token %s." % compliance["token"])
        elif (stated.upper() in ("APPROVE", "APPROVED")) != approved:
            findings.append("The audit records the compliance decision as %r, but the "
                            "token the platform observed was %s."
                            % (stated, compliance["token"]))
    # The disposition must agree with the branch the platform actually ran.
    disposition = audit.get("final_disposition")
    if isinstance(disposition, str) and route:
        pending = "HUMAN" in disposition.upper()
        to_human = route.get("route") == "ESCALATED_TO_HUMAN" \
            or route.get("case_follow_up") == "HANDED_TO_HUMAN"
        released_only = route.get("route") == "APPROVED_AND_RELEASED" \
            and route.get("case_follow_up") == "NONE_REQUIRED"
        if to_human and not pending:
            findings.append("final_disposition is %r, but the platform handed the "
                            "case to a human." % disposition)
        if released_only and pending:
            findings.append("final_disposition is %r, but the platform released the "
                            "message and ran no human handoff." % disposition)
    unusable = {u["agent"]: u["problems"] for u in (unhealthy or [])}
    truth = {p["agent"]: p["version"] for p in observed}
    listed = audit.get("participating_agents")
    # Every entry is judged on its own. A dict keyed by name would let a later
    # correct entry for the same agent hide an earlier false one.
    entries = [e for e in (listed if isinstance(listed, list) else [])
               if isinstance(e, dict) and isinstance(e.get("agent_name"), str)]
    named = {e["agent_name"] for e in entries}
    missing = sorted(set(truth) - named)
    if missing:
        findings.append("Agents that ran but are absent from the audit: %s."
                        % ", ".join(missing))
    for entry in entries:
        name = entry["agent_name"]
        claimed = str(entry.get("agent_version"))
        actual = truth.get(name)
        not_invoked = entry.get("output_status") == NOT_INVOKED
        if actual is None:
            if not not_invoked:
                findings.append("%s is listed as a participant, but the "
                                "platform recorded no output from it." % name)
            continue
        if not_invoked:
            findings.append("%s is recorded as NOT_INVOKED, but the platform "
                            "ran version %s." % (name, actual))
        elif name in unusable and entry.get("output_status") == "RECEIVED":
            findings.append("%s is recorded as 'RECEIVED', but its output was not "
                            "usable: %s." % (name, ", ".join(unusable[name])))
        if claimed in (NOT_OBSERVED, "None"):
            continue
        if claimed.lstrip("v") != actual:
            findings.append("%s is recorded as version %r, the platform ran "
                            "version %s." % (name, claimed, actual))
    return {"audit_parsed": True,
            "audit_execution_status": audit.get("execution_status"),
            "audit_workflow_version": audit.get("workflow_version"),
            "audit_agents_listed": len(named),
            "audit_entries": len(entries),
            "platform_agents_observed": len(truth),
            "accurate": not findings, "findings": findings}


def analyze(items: list[dict], actions: list[dict], workflow_name: str,
            workflow_label: str) -> dict:
    """Everything derived from one run's captured items and action events."""
    observed = participation(items, workflow_name)
    route = workflow_map.describe_route(
        [a["action_id"] for a in actions if isinstance(a.get("action_id"), str)],
        [a["previous_action_id"] for a in actions
         if isinstance(a.get("previous_action_id"), str)])
    follow_up = case_follow_up(items)
    unhealthy = output_health(items, workflow_name)
    compliance = compliance_decision(items)
    findings: list[str] = []
    needs_human = follow_up.get("planner_token") == "HUMAN_REQUIRED" \
        or follow_up.get("planner_states_human_review_reason") is True
    if needs_human and route["case_follow_up"] not in ("HANDED_TO_HUMAN",):
        findings.append(
            "The planner stated that the case needs human review, but no human "
            "handoff was observed. Follow-up observed: %s."
            % route["case_follow_up"])
    return {
        "basis": {
            "platform_observed": ["route", "participation", "distinct_agents",
                                  "release", "unhealthy_outputs", "investigation"],
            "model_produced": ["compliance", "case_follow_up.planner_*",
                               "audit.audit_*"],
            "note": "Platform-observed fields come from service metadata and "
                    "delivered text. Model-produced fields are what an agent "
                    "wrote. Where they disagree the platform fields win.",
        },
        "route": route,
        "participation": observed,
        "distinct_agents": len({p["agent"] for p in observed}),
        "unhealthy_outputs": unhealthy,
        "investigation": investigation(observed, unhealthy),
        "compliance": compliance,
        "release": release_check(items, workflow_name),
        "case_follow_up": {**follow_up, "observed": route["case_follow_up"],
                           "findings": findings},
        "audit": audit_check(items, workflow_label, observed, follow_up, route,
                             compliance, unhealthy),
    }


def analyze_run_dir(run_dir: str) -> dict:
    """Re-derive the analysis of an earlier run from its evidence files.

    Read-only. The run's own preflight record says which workflow version it
    used, so an old run is judged against its version and not today's pin.
    """
    def load(name: str) -> object:
        with open(os.path.join(run_dir, name), encoding="utf-8") as handle:
            return json.load(handle)

    preflight = load("00_preflight.json")
    name = str(preflight.get("workflow"))
    label = "%s v%s" % (name, preflight.get("workflow_version"))
    actions = load("04_workflow_actions.json")
    result = analyze(items_of(load("07_conversation_items.json")),
                     actions if isinstance(actions, list) else [], name, label)
    events = 0
    with open(os.path.join(run_dir, "02_events.jsonl"), encoding="utf-8") as handle:
        events = sum(1 for line in handle if line.strip())
    return {"derived_offline_from": os.path.basename(os.path.normpath(run_dir)),
            "workflow": label, "case_sha256": preflight.get("case_sha256"),
            "stream_events": events, **result}
