"""Action identifiers of GridResolveAIWorkflow v10, read from the live definition.

v10 is v9 with two changes. Every agent node now passes a short literal input
message, so each agent is given a user turn naming its step instead of being
left to continue a conversation whose last speaker looks like itself, which is
what stalled three invocations in the first two real runs. The gate gains a
third term: the evidence, usage, policy and compliance outputs must each begin
a JSON object holding their key field, or the case escalates. Every action id,
branch and template is unchanged from v9.

v9 is v8 with one change: the release guard also withholds the message when any
of the six customer fields holds only spaces, tabs, carriage returns or line
feeds. Every action id, branch and template is unchanged from v8.

v8 keeps every earlier action id and adds a second, separate gate inside the
approve branch. The first gate answers "is this customer message safe to send".
The second answers "does the case itself still need a person", from the
planner's follow-up token, and defaults to a human handoff. v8 also releases the
six customer-facing fields of the draft instead of the whole JSON object.

History:

v6 kept every action id of v5 and changed the compliance gate condition and the
release activity. v7 keeps every action id again and changes the release
activity only, from an `=expression`, which the hosted service sent as literal
text in the first real run, to a `{...}` template. See tests/powerfx_gate.

Used only to interpret the `workflow_action` events of a real run. If the
workflow is republished these change, which is why the runner refuses to run
against any version other than the one recorded here.
"""
from __future__ import annotations

from typing import Final

WORKFLOW_VERSION: Final = "10"

AGENT_ACTIONS: Final = {
    "node-1789696603365": "CaseTriageAgent",
    "node-1789696645054": "AccountEvidenceAgent",
    "node-1789696697430": "UsageAnomalyAgent",
    "node-1789696718717": "PolicyKnowledgeAgent",
    "node-1789696778418": "ResolutionPlannerAgent",
    "node-1789696813306": "CustomerCommunicationAgent",
    "node-1789696841174": "EvidenceComplianceAgent",
    "node-1789697115060": "EscalationCoordinatorAgent",
    "node-followup-handoff": "EscalationCoordinatorAgent",
    "node-1789697069548": "CaseAuditAgent",
}

GATE_ACTION: Final = "node-1789696874113"
APPROVE_BRANCH: Final = "if-node-approved-release"
ESCALATE_BRANCH: Final = "if-node-failclosed-escalate"
RELEASE_ACTION: Final = "node-release-approved-message"
ESCALATION_ACTION: Final = "node-1789697115060"
AUDIT_ACTION: Final = "node-1789697069548"

FOLLOWUP_GATE: Final = "node-case-followup-gate"
NO_FOLLOWUP_BRANCH: Final = "if-node-no-human-followup"
FOLLOWUP_BRANCH: Final = "if-node-human-followup"
NO_FOLLOWUP_ACTION: Final = "node-record-no-followup"
FOLLOWUP_HANDOFF_ACTION: Final = "node-followup-handoff"

APPROVED_TOKEN: Final = "ROUTE_DECISION::GRIDRESOLVE_APPROVED"
ESCALATE_TOKEN: Final = "ROUTE_DECISION::GRIDRESOLVE_ESCALATE"
FOLLOWUP_HUMAN_TOKEN: Final = "CASE_FOLLOWUP::HUMAN_REQUIRED"
FOLLOWUP_NONE_TOKEN: Final = "CASE_FOLLOWUP::NONE_REQUIRED"

# The customer-facing fields of CustomerCommunicationAgent's output, in the order
# the v8 release template sends them, each with the heading printed above it.
# tests assert this equals tests/powerfx_gate/release_v8.txt and the live YAML.
RELEASE_FIELDS: Final = (
    ("", "customer_summary"),
    ("What we reviewed", "what_we_reviewed"),
    ("What we found", "what_we_found"),
    ("Why your bill changed", "why_bill_changed"),
    ("What happens next", "what_happens_next"),
    ("What we need from you", "customer_action_needed"),
)


def release_template() -> str:
    lines: list[str] = []
    for heading, field_name in RELEASE_FIELDS:
        if heading:
            lines += ["", heading]
        lines.append("{Local.VarCustomerMessage.%s}" % field_name)
    return "\n".join(lines)


def compose_customer_message(draft: dict) -> str | None:
    """What the v8 release template sends for this draft, or None when the
    workflow would withhold it because a customer-facing field is blank."""
    lines: list[str] = []
    for heading, field_name in RELEASE_FIELDS:
        value = draft.get(field_name)
        if not isinstance(value, str) or not value.strip():
            return None
        if heading:
            lines += ["", heading]
        lines.append(value)
    return "\n".join(lines)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    return [v for v in values if not (v in seen or seen.add(v))]


def describe_route(observed_action_ids: list[str],
                   previous_action_ids: list[str] | tuple[str, ...] = ()) -> dict:
    """Classify the branch taken, from action ids the service actually emitted.

    Anything not directly observed is reported as not observed. It is never
    inferred from the absence of the other branch.

    The hosted service emits no workflow_action item for the ConditionGroup
    itself. The first real run showed the gate only as the predecessor of later
    actions: `if-node-approved-releaseActions` before the release step and
    `node-1789696874113_Post` before the audit. Those references are service
    output too, so the gate counts as evaluated when any of them is present.

    Each action arrives twice, as `added` then `done`, and one agent can sit
    behind two nodes, so agents are listed once each, in first-seen order.
    """
    ordered = list(observed_action_ids)
    seen = set(ordered)
    gate_refs = (GATE_ACTION, APPROVE_BRANCH, ESCALATE_BRANCH)
    gate_referenced = any(p.startswith(gate_refs) for p in previous_action_ids)
    followup_refs = (FOLLOWUP_GATE, NO_FOLLOWUP_BRANCH, FOLLOWUP_BRANCH)
    followup_referenced = any(p.startswith(followup_refs)
                              for p in previous_action_ids)
    handed_off = FOLLOWUP_HANDOFF_ACTION in seen or FOLLOWUP_BRANCH in seen
    no_followup = NO_FOLLOWUP_ACTION in seen or NO_FOLLOWUP_BRANCH in seen
    released = RELEASE_ACTION in seen or APPROVE_BRANCH in seen
    escalated = ESCALATION_ACTION in seen or ESCALATE_BRANCH in seen
    if released and escalated:
        route = "CONFLICTING_BOTH_BRANCHES_OBSERVED"
    elif escalated:
        route = "ESCALATED_TO_HUMAN"
    elif released:
        route = "APPROVED_AND_RELEASED"
    else:
        route = "NOT_OBSERVED"
    # Question B, separate from the message route above. An escalated message
    # is itself a human handoff. Nothing here is inferred from absence.
    if handed_off and no_followup:
        follow_up = "CONFLICTING_BOTH_BRANCHES_OBSERVED"
    elif handed_off or ESCALATION_ACTION in seen or ESCALATE_BRANCH in seen:
        follow_up = "HANDED_TO_HUMAN"
    elif no_followup:
        follow_up = "NONE_REQUIRED"
    else:
        follow_up = "NOT_OBSERVED"
    observed_agents = _dedupe([AGENT_ACTIONS[a] for a in ordered
                               if a in AGENT_ACTIONS])
    return {
        "route": route,
        "gate_evaluated": GATE_ACTION in seen or gate_referenced,
        "case_follow_up": follow_up,
        "follow_up_gate_evaluated": (FOLLOWUP_GATE in seen or followup_referenced
                                     or handed_off or no_followup),
        "audit_ran": AUDIT_ACTION in seen,
        "agents_observed": observed_agents,
        "agents_not_observed": [n for n in _dedupe(list(AGENT_ACTIONS.values()))
                                if n not in observed_agents],
    }
