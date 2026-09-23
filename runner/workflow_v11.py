"""Action identifiers of GridResolveAIWorkflow v11, the bounded-correction design.

v11 is v10 plus two correction routes out of the compliance gate. Every attempt-0
action id, expression and invocation message of v10 is kept unchanged. The gate
now distinguishes four route tokens on the last line of the compliance output:

    ROUTE_DECISION::GRIDRESOLVE_APPROVED         release, as in v10
    ROUTE_DECISION::GRIDRESOLVE_REJECT_REWRITE   CustomerCommunicationAgent again,
                                                 then EvidenceComplianceAgent, then gate
    ROUTE_DECISION::GRIDRESOLVE_REJECT_REPLAN    ResolutionPlannerAgent, then the two
                                                 above, then gate
    anything else                                fail closed, as in v10

At most two correction attempts per case, of either kind. The bound is in the
shape of the definition (the tree is unrolled to depth two), not in a counter an
agent controls. After the second correction the gate has only two outcomes,
release or escalate. Nothing is ever sent to the customer on an escalation.

The definition and this map are generated from one naming rule, see
tests/workflow_engine/build_v11.py. A test asserts the two agree.

STATUS: local design, tested on Microsoft's open-source declarative engine with
scripted agents. Not published to Foundry. No hosted run has exercised v11.
"""
from __future__ import annotations

from itertools import product
from typing import Final

from . import workflow_map as v10

WORKFLOW_VERSION: Final = "11"
MAX_CORRECTIONS: Final = 2
KINDS: Final = ("rewrite", "replan")

APPROVED_TOKEN: Final = v10.APPROVED_TOKEN
ESCALATE_TOKEN: Final = v10.ESCALATE_TOKEN
REJECT_REWRITE_TOKEN: Final = "ROUTE_DECISION::GRIDRESOLVE_REJECT_REWRITE"
REJECT_REPLAN_TOKEN: Final = "ROUTE_DECISION::GRIDRESOLVE_REJECT_REPLAN"
FOLLOWUP_HUMAN_TOKEN: Final = v10.FOLLOWUP_HUMAN_TOKEN
FOLLOWUP_NONE_TOKEN: Final = v10.FOLLOWUP_NONE_TOKEN

RELEASE_FIELDS: Final = v10.RELEASE_FIELDS
release_template = v10.release_template
compose_customer_message = v10.compose_customer_message

# Every correction path: () is attempt 0, ("rewrite",) attempt 1, and so on.
PATHS: Final = tuple(p for n in range(MAX_CORRECTIONS + 1) for p in product(KINDS, repeat=n))


def _prefix(path: tuple[str, ...]) -> str:
    return "-".join("a%d-%s" % (n + 1, kind) for n, kind in enumerate(path))


def ids(path: tuple[str, ...]) -> dict[str, str]:
    """The action ids at one point of the tree. Attempt 0 is v10's ids."""
    if not path:
        return {"gate": v10.GATE_ACTION, "approve_branch": v10.APPROVE_BRANCH,
                "release": v10.RELEASE_ACTION, "followup_gate": v10.FOLLOWUP_GATE,
                "no_followup_branch": v10.NO_FOLLOWUP_BRANCH,
                "no_followup": v10.NO_FOLLOWUP_ACTION,
                "followup_branch": v10.FOLLOWUP_BRANCH,
                "followup_handoff": v10.FOLLOWUP_HANDOFF_ACTION,
                "escalate_branch": v10.ESCALATE_BRANCH, "escalate": v10.ESCALATION_ACTION}
    p = _prefix(path)
    return {"planner": "node-%s-planner" % p, "comms": "node-%s-comms" % p,
            "compliance": "node-%s-compliance" % p, "gate": "node-%s-gate" % p,
            "approve_branch": "if-node-%s-approved-release" % p,
            "release": "node-%s-release-approved-message" % p,
            "followup_gate": "node-%s-case-followup-gate" % p,
            "no_followup_branch": "if-node-%s-no-human-followup" % p,
            "no_followup": "node-%s-record-no-followup" % p,
            "followup_branch": "if-node-%s-human-followup" % p,
            "followup_handoff": "node-%s-followup-handoff" % p,
            "escalate_branch": "if-node-%s-failclosed-escalate" % p,
            "escalate": "node-%s-escalate" % p}


def reject_branch(path: tuple[str, ...], kind: str) -> str:
    return "if-node-%sa%d-reject-%s" % (_prefix(path) + "-" if path else "",
                                         len(path) + 1, kind)


def _collect(key: str) -> tuple[str, ...]:
    return tuple(ids(p)[key] for p in PATHS if key in ids(p))


AGENT_ACTIONS: Final = {
    **v10.AGENT_ACTIONS,
    **{ids(p)["planner"]: "ResolutionPlannerAgent" for p in PATHS if p and p[-1] == "replan"},
    **{ids(p)["comms"]: "CustomerCommunicationAgent" for p in PATHS if p},
    **{ids(p)["compliance"]: "EvidenceComplianceAgent" for p in PATHS if p},
    **{ids(p)["followup_handoff"]: "EscalationCoordinatorAgent" for p in PATHS if p},
    **{ids(p)["escalate"]: "EscalationCoordinatorAgent" for p in PATHS if p},
}

GATE_ACTION: Final = v10.GATE_ACTION
GATE_ACTIONS: Final = _collect("gate")
APPROVE_BRANCHES: Final = _collect("approve_branch")
RELEASE_ACTIONS: Final = _collect("release")
ESCALATE_BRANCHES: Final = _collect("escalate_branch")
ESCALATION_ACTIONS: Final = _collect("escalate")
FOLLOWUP_GATES: Final = _collect("followup_gate")
NO_FOLLOWUP_BRANCHES: Final = _collect("no_followup_branch")
NO_FOLLOWUP_ACTIONS: Final = _collect("no_followup")
FOLLOWUP_BRANCHES: Final = _collect("followup_branch")
FOLLOWUP_HANDOFF_ACTIONS: Final = _collect("followup_handoff")
CORRECTION_COMPLIANCE_ACTIONS: Final = tuple(ids(p)["compliance"] for p in PATHS if p)
REJECT_BRANCHES: Final = {
    reject_branch(p, kind): kind for p in PATHS if len(p) < MAX_CORRECTIONS for kind in KINDS}
# The first agent node of each correction attempt, which names its kind.
CORRECTION_STARTS: Final = {
    **{ids(p)["comms"]: "REWRITE" for p in PATHS if p and p[-1] == "rewrite"},
    **{ids(p)["planner"]: "REPLAN" for p in PATHS if p and p[-1] == "replan"}}

# Kept so callers written against v10 keep working on the attempt-0 names.
APPROVE_BRANCH: Final = v10.APPROVE_BRANCH
ESCALATE_BRANCH: Final = v10.ESCALATE_BRANCH
RELEASE_ACTION: Final = v10.RELEASE_ACTION
ESCALATION_ACTION: Final = v10.ESCALATION_ACTION
AUDIT_ACTION: Final = v10.AUDIT_ACTION
FOLLOWUP_GATE: Final = v10.FOLLOWUP_GATE
NO_FOLLOWUP_BRANCH: Final = v10.NO_FOLLOWUP_BRANCH
FOLLOWUP_BRANCH: Final = v10.FOLLOWUP_BRANCH
NO_FOLLOWUP_ACTION: Final = v10.NO_FOLLOWUP_ACTION
FOLLOWUP_HANDOFF_ACTION: Final = v10.FOLLOWUP_HANDOFF_ACTION


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    return [v for v in values if not (v in seen or seen.add(v))]


def describe_route(observed_action_ids: list[str],
                   previous_action_ids: list[str] | tuple[str, ...] = ()) -> dict:
    """Classify what happened, from action ids the service actually emitted.

    Same rules as v10: nothing is inferred from absence, each agent is listed
    once in first-seen order, and a branch counts as evaluated when the service
    names it as a predecessor. Adds the correction record: how many correction
    attempts ran, of which kinds, in order.
    """
    ordered = list(observed_action_ids)
    seen = set(ordered)
    gate_refs = GATE_ACTIONS + APPROVE_BRANCHES + ESCALATE_BRANCHES + tuple(REJECT_BRANCHES)
    gate_referenced = any(p.startswith(gate_refs) for p in previous_action_ids)
    followup_refs = FOLLOWUP_GATES + NO_FOLLOWUP_BRANCHES + FOLLOWUP_BRANCHES
    followup_referenced = any(p.startswith(followup_refs) for p in previous_action_ids)
    handed_off = bool(seen & set(FOLLOWUP_HANDOFF_ACTIONS + FOLLOWUP_BRANCHES))
    no_followup = bool(seen & set(NO_FOLLOWUP_ACTIONS + NO_FOLLOWUP_BRANCHES))
    released = bool(seen & set(RELEASE_ACTIONS + APPROVE_BRANCHES))
    escalated = bool(seen & set(ESCALATION_ACTIONS + ESCALATE_BRANCHES))
    if released and escalated:
        route = "CONFLICTING_BOTH_BRANCHES_OBSERVED"
    elif escalated:
        route = "ESCALATED_TO_HUMAN"
    elif released:
        route = "APPROVED_AND_RELEASED"
    else:
        route = "NOT_OBSERVED"
    if handed_off and no_followup:
        follow_up = "CONFLICTING_BOTH_BRANCHES_OBSERVED"
    elif handed_off or escalated:
        follow_up = "HANDED_TO_HUMAN"
    elif no_followup:
        follow_up = "NONE_REQUIRED"
    else:
        follow_up = "NOT_OBSERVED"
    # One entry per correction attempt that started, in order, by the first
    # agent node of that attempt. Branch ids are not counted: the hosted service
    # names them only as predecessors, and they carry no agent.
    kinds = [CORRECTION_STARTS[a] for a in _dedupe(ordered) if a in CORRECTION_STARTS]
    corrections = len([a for a in _dedupe(ordered) if a in CORRECTION_COMPLIANCE_ACTIONS])
    observed_agents = _dedupe([AGENT_ACTIONS[a] for a in ordered if a in AGENT_ACTIONS])
    return {
        "route": route,
        "gate_evaluated": bool(seen & set(GATE_ACTIONS)) or gate_referenced,
        "case_follow_up": follow_up,
        "follow_up_gate_evaluated": (bool(seen & set(FOLLOWUP_GATES)) or followup_referenced
                                     or handed_off or no_followup),
        "audit_ran": AUDIT_ACTION in seen,
        "agents_observed": observed_agents,
        "agents_not_observed": [n for n in _dedupe(list(v10.AGENT_ACTIONS.values()))
                                if n not in observed_agents],
        "correction_attempts": corrections,
        "rejections_observed": kinds,
        "correction_bound": MAX_CORRECTIONS,
    }
