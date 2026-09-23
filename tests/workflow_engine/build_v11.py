"""Generate GridResolveAIWorkflow v11 from the v10 definition.

v11 is v10 plus bounded correction routes. v10 collapses every compliance
decision other than APPROVE into one fail-closed escalation. v11 routes two of
those decisions back into the workflow, each at most twice per case in total:

    ROUTE_DECISION::GRIDRESOLVE_REJECT_REWRITE   redraft the customer message
    ROUTE_DECISION::GRIDRESOLVE_REJECT_REPLAN    re-plan, then redraft

Every correction is re-reviewed by EvidenceComplianceAgent and re-gated. The
bound is structural: the tree below is unrolled to depth two, so no counter an
agent writes can extend it. A third non-approval, a malformed token, or a
missing decision object takes the fail-closed branch, exactly as in v10.
Nothing is ever sent to the customer on that branch.

The generator reads the v10 YAML and its reviewed invocation messages, keeps
every attempt-0 action id and expression byte for byte, and emits:

    workflows/GridResolveAIWorkflow_v11.yaml
    invocation_messages_v11.json

Run: python tests/workflow_engine/build_v11.py
Check: python tests/workflow_engine/build_v11.py --check   (exit 1 on drift)
No network, no model, no cost.
"""
from __future__ import annotations

import json
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
V10_YAML = os.path.join(HERE, "workflows", "GridResolveAIWorkflow_v10.yaml")
V10_MESSAGES = os.path.join(HERE, "invocation_messages_v10.json")
V11_YAML = os.path.join(HERE, "workflows", "GridResolveAIWorkflow_v11.yaml")
V11_MESSAGES = os.path.join(HERE, "invocation_messages_v11.json")

MAX_CORRECTIONS = 2

APPROVED = "ROUTE_DECISION::GRIDRESOLVE_APPROVED"
REWRITE = "ROUTE_DECISION::GRIDRESOLVE_REJECT_REWRITE"
REPLAN = "ROUTE_DECISION::GRIDRESOLVE_REJECT_REPLAN"
ESCALATE = "ROUTE_DECISION::GRIDRESOLVE_ESCALATE"

# v10 action ids, kept for attempt 0 so run analysis and the live-config
# checks that know them keep working.
V10 = {
    "triage": "node-1789696603365", "evidence": "node-1789696645054",
    "usage": "node-1789696697430", "policy": "node-1789696718717",
    "planner": "node-1789696778418", "comms": "node-1789696813306",
    "compliance": "node-1789696841174", "gate": "node-1789696874113",
    "approve_branch": "if-node-approved-release",
    "release": "node-release-approved-message",
    "followup_gate": "node-case-followup-gate",
    "no_followup_branch": "if-node-no-human-followup",
    "no_followup": "node-record-no-followup",
    "followup_branch": "if-node-human-followup",
    "followup_handoff": "node-followup-handoff",
    "escalate_branch": "if-node-failclosed-escalate",
    "escalate": "node-1789697115060", "audit": "node-1789697069548",
}

AGENT = {"planner": "ResolutionPlannerAgent", "comms": "CustomerCommunicationAgent",
         "compliance": "EvidenceComplianceAgent",
         "escalation": "EscalationCoordinatorAgent", "audit": "CaseAuditAgent"}


# ---- ids and variables, one naming rule for the whole tree ------------------

def prefix(path: tuple[str, ...]) -> str:
    """('rewrite', 'replan') -> 'a1-rewrite-a2-replan'."""
    return "-".join("a%d-%s" % (n + 1, kind) for n, kind in enumerate(path))


def suffix(path: tuple[str, ...]) -> str:
    """('rewrite', 'replan') -> 'A1RwA2Rp', the variable name suffix."""
    return "".join("A%d%s" % (n + 1, {"rewrite": "Rw", "replan": "Rp"}[kind])
                   for n, kind in enumerate(path))


def ids(path: tuple[str, ...]) -> dict[str, str]:
    if not path:
        return dict(V10)
    p = prefix(path)
    return {
        "planner": "node-%s-planner" % p, "comms": "node-%s-comms" % p,
        "compliance": "node-%s-compliance" % p, "gate": "node-%s-gate" % p,
        "approve_branch": "if-node-%s-approved-release" % p,
        "release": "node-%s-release-approved-message" % p,
        "followup_gate": "node-%s-case-followup-gate" % p,
        "no_followup_branch": "if-node-%s-no-human-followup" % p,
        "no_followup": "node-%s-record-no-followup" % p,
        "followup_branch": "if-node-%s-human-followup" % p,
        "followup_handoff": "node-%s-followup-handoff" % p,
        "escalate_branch": "if-node-%s-failclosed-escalate" % p,
        "escalate": "node-%s-escalate" % p,
    }


def reject_branch(path: tuple[str, ...], kind: str) -> str:
    """The branch id, under the gate at `path`, that starts correction attempt len(path)+1."""
    n = len(path) + 1
    return "if-node-%sa%d-reject-%s" % (prefix(path) + "-" if path else "", n, kind)


def variables(path: tuple[str, ...], plan_path: tuple[str, ...]) -> dict[str, str]:
    """Variable names at `path`. The plan is the one written at `plan_path`."""
    s = suffix(path)
    return {
        "plan": "Local.VarPlan" + suffix(plan_path) if plan_path else "Local.VarPlan",
        "draft": "Local.VarCustomerDraft" + s if path else "Local.VarCustomerDraft",
        "message": "Local.VarCustomerMessage" + s if path else "Local.VarCustomerMessage",
        "compliance": "Local.VarCompliance" + s if path else "Local.Var1497",
    }


# ---- Power Fx, derived from the reviewed v10 expressions --------------------

def _v10() -> tuple[dict, dict[str, str]]:
    with open(V10_YAML, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    with open(V10_MESSAGES, encoding="utf-8") as fh:
        messages = {k: v for k, v in json.load(fh).items() if not k.startswith("_")}
    return doc, messages


def _find(actions: list, action_id: str) -> dict:
    for act in actions:
        if act.get("id") == action_id:
            return act
        for cond in act.get("conditions", []):
            if cond.get("id") == action_id:
                return cond
            found = _find(cond.get("actions", []), action_id)
            if found:
                return found
    return {}


def approve_condition(v10_expr: str, var: dict[str, str]) -> str:
    """The v10 approve expression, on this attempt's variables, refusing REJECT tokens."""
    marker = '!("GRIDRESOLVE_ESCALATE" in t)'
    assert v10_expr.count(marker) == 1
    expr = v10_expr.replace(marker, marker + ' && !("GRIDRESOLVE_REJECT" in t)')
    return (expr.replace("Local.Var1497", var["compliance"])
                .replace("Local.VarCustomerMessage", var["message"]))


def reject_condition(token: str, other: str, compliance_var: str) -> str:
    """Exactly one occurrence of `token`, as the last non-blank line, no other
    route token anywhere, and a decision object to correct from."""
    return (
        '=With({t: Last(%s).Text}, With({l: Trim(Last(Filter(Split(Substitute(t, '
        'Char(13), ""), Char(10)), !IsBlank(Trim(Value)))).Value)}, !IsBlank(t) && '
        '!("GRIDRESOLVE_ESCALATE" in t) && !("GRIDRESOLVE_APPROVED" in t) && '
        '!("%s" in t) && (Len(t) - Len(Substitute(t, "%s", "")) = Len("%s")) && '
        '("%s" exactin l) && (Len(l) = Len("%s")))) && With({s: Trim(Substitute('
        'Substitute(Substitute(Last(%s).Text, Char(10), ""), Char(13), ""), Char(9), '
        '""))}, StartsWith(s, "{") && ("""decision""" in s))'
        % (compliance_var, other, token, token, token, token, compliance_var))


def followup_condition(v10_expr: str, plan_var: str) -> str:
    return v10_expr.replace("Local.VarPlan", plan_var)


def release_activity(v10_activity: str, message_var: str) -> str:
    return v10_activity.replace("Local.VarCustomerMessage.", message_var + ".")


# ---- invocation messages ----------------------------------------------------

COMMON = ("Every assistant message above was written by a different specialist "
          "agent, not by you. ")
UNATTENDED = "No operator is present and no confirmation will be given. "


def correction_messages(n: int, kind: str) -> dict[str, str]:
    """Plain literals for correction attempt n. They name the step, the attempt,
    what to read and what to return. They state no finding and no verdict."""
    attempt = "CORRECTION ATTEMPT %d of %d" % (n, MAX_CORRECTIONS)
    out = {}
    if kind == "replan":
        out["planner"] = (
            "WORKFLOW STEP 5 of 9, %s: ResolutionPlannerAgent. %sWorkflow state: the "
            "most recent EvidenceComplianceAgent output above did not accept the plan "
            "and asked for a replan. Nothing has been sent to the customer. Task: read "
            "the correction_instructions, unsupported_claim_ids, failed_checks and "
            "reason_codes in that output, then propose a corrected resolution "
            "supported only by the step 2 evidence, step 3 usage and step 4 policy "
            "outputs above, with the evidence and policy basis for every claim. Drop "
            "or mark UNSUPPORTED any claim the evidence does not support. Do not fill "
            "an evidence gap yourself; if evidence is missing, say so in the plan. "
            "%sRespond now, in this single reply, with the JSON object your OUTPUT "
            "contract requires, starting with an opening brace, followed by the single "
            "CASE_FOLLOWUP token line your instructions define."
            % (attempt, COMMON, UNATTENDED))
        out["comms"] = (
            "WORKFLOW STEP 6 of 9, %s: CustomerCommunicationAgent. %sWorkflow state: "
            "the plan was corrected after the most recent EvidenceComplianceAgent "
            "review above. Nothing has been sent to the customer. Task: write a new "
            "customer message from the claims the most recent ResolutionPlannerAgent "
            "plan above supports, and do not carry over wording from the earlier "
            "draft that the review identified. Complete all six customer-facing "
            "fields in plain language that stands on its own. %sRespond now, in this "
            "single reply, with the JSON object your output schema requires."
            % (attempt, COMMON, UNATTENDED))
    else:
        out["comms"] = (
            "WORKFLOW STEP 6 of 9, %s: CustomerCommunicationAgent. %sWorkflow state: "
            "the most recent EvidenceComplianceAgent output above did not accept the "
            "customer message and asked for a rewrite. Nothing has been sent to the "
            "customer. Task: read the correction_instructions, failed_checks and "
            "reason_codes in that output and change only the wording it identified. "
            "Keep every claim, fact and policy interpretation of the most recent "
            "ResolutionPlannerAgent plan above unchanged. Complete all six "
            "customer-facing fields in plain language that stands on its own. "
            "%sRespond now, in this single reply, with the JSON object your output "
            "schema requires." % (attempt, COMMON, UNATTENDED))
    out["compliance"] = (
        "WORKFLOW STEP 7 of 9, %s: EvidenceComplianceAgent. %sWorkflow state: an "
        "earlier review did not accept the customer message, and the most recent "
        "CustomerCommunicationAgent output above is the corrected draft. Task: review "
        "that corrected message against the step 2 evidence, step 3 usage, step 4 "
        "policy and the most recent ResolutionPlannerAgent plan above. Run your checks "
        "and record which failed, with reasons and reason codes. Decide only whether "
        "that message is safe to release; whether the case still needs a person is "
        "routed separately by the workflow and is not by itself a reason to reject. If "
        "an output you need is missing or is not a JSON object, record that as a failed "
        "check and do not repair it. %sRespond now, in this single reply, with the JSON "
        "decision object your OUTPUT contract requires, starting with an opening brace, "
        "followed by the single ROUTE_DECISION token line your instructions define. The "
        "token line alone is not a complete response." % (attempt, COMMON, UNATTENDED))
    return out


def escalate_message(n: int) -> str:
    return (
        "WORKFLOW STEP 8 of 9: EscalationCoordinatorAgent. %sWorkflow state: the "
        "customer message was not released. The step 7 review did not accept it after "
        "%d automated correction attempt(s), the workflow permits at most %d, or a "
        "required specialist output or customer field was incomplete. Nothing has been "
        "sent to the customer. Task: prepare the human review package. List every "
        "decision, failed check, reason code and correction instruction in the "
        "EvidenceComplianceAgent outputs above, in order, and list any specialist "
        "output above that is missing or is not a JSON object. %sDo not describe what "
        "you will do. Respond now, in this single reply, with only the JSON object "
        "your OUTPUT contract requires, starting with an opening brace."
        % (COMMON, n, MAX_CORRECTIONS, UNATTENDED))


def handoff_message(n: int) -> str:
    return (
        "WORKFLOW STEP 8 of 9: EscalationCoordinatorAgent. %sWorkflow state: the "
        "customer message drafted in the most recent CustomerCommunicationAgent output "
        "above was accepted by the step 7 review and released, after %d automated "
        "correction attempt(s), and the most recent step 5 follow-up line did not clear "
        "the case of further human work. Task: prepare the human review package for the "
        "open case work, and include every earlier review decision and reason code "
        "above. %sDo not describe what you will do. Respond now, in this single reply, "
        "with only the JSON object your OUTPUT contract requires, starting with an "
        "opening brace." % (COMMON, n, UNATTENDED))


def audit_message(v10_text: str) -> str:
    marker = ("Copy the compliance decision from the step 7 output and its final "
              "ROUTE_DECISION line, never from the wording of the customer message.")
    assert marker in v10_text
    return v10_text.replace(marker, (
        "Copy the compliance decision from the most recent step 7 output and its "
        "final ROUTE_DECISION line, never from the wording of the customer message. "
        "Record correction_count as the number of CORRECTION ATTEMPT messages above, "
        "and every earlier step 7 decision with its failed checks and reason codes, "
        "in order."))


# ---- the tree ----------------------------------------------------------------

def invoke(action_id: str, agent: str, message: str, out_var: str,
           response_object: str | None = None, auto_send: bool = False) -> dict:
    node = {"kind": "InvokeAzureAgent", "id": action_id, "agent": agent,
            "message": message, "autoSend": auto_send, "messages": out_var}
    if response_object:
        node["responseObject"] = response_object
    return node


def build(v10: dict, v10_messages: dict[str, str]) -> tuple[list, dict[str, str]]:
    top = v10["trigger"]["actions"]
    gate0 = _find(top, V10["gate"])
    approve0 = gate0["conditions"][0]["condition"]
    release0 = _find(top, V10["release"])["activity"]
    followup0 = _find(top, V10["followup_gate"])["conditions"][0]["condition"]
    messages: dict[str, str] = {}

    def agent_node(path, plan_path, key, msg):
        i, var = ids(path), variables(path, plan_path)
        messages[i[key]] = msg
        if key == "planner":
            return invoke(i["planner"], AGENT["planner"], msg, var["plan"])
        if key == "comms":
            return invoke(i["comms"], AGENT["comms"], msg, var["draft"], var["message"])
        if key == "compliance":
            return invoke(i["compliance"], AGENT["compliance"], msg, var["compliance"])
        raise KeyError(key)

    def approve_branch(path, plan_path):
        i, var = ids(path), variables(path, plan_path)
        n = len(path)
        handoff = v10_messages[V10["followup_handoff"]] if not path else handoff_message(n)
        messages[i["followup_handoff"]] = handoff
        return {
            "condition": approve_condition(approve0, var), "id": i["approve_branch"],
            "actions": [
                {"kind": "SendActivity", "id": i["release"],
                 "activity": release_activity(release0, var["message"])},
                {"kind": "ConditionGroup", "id": i["followup_gate"], "conditions": [
                    {"condition": followup_condition(followup0, var["plan"]),
                     "id": i["no_followup_branch"], "actions": [
                         {"kind": "SetVariable", "id": i["no_followup"],
                          "variable": "Local.VarCaseFollowUp",
                          "value": '="NONE_REQUIRED"'}]},
                    {"condition": "true", "id": i["followup_branch"], "actions": [
                        invoke(i["followup_handoff"], AGENT["escalation"], handoff,
                               "Local.VarFollowUpHandoff", auto_send=True)]}]}]}

    def escalate_branch(path):
        i = ids(path)
        msg = v10_messages[V10["escalate"]] if not path else escalate_message(len(path))
        messages[i["escalate"]] = msg
        return {"condition": "true", "id": i["escalate_branch"], "actions": [
            invoke(i["escalate"], AGENT["escalation"], msg, "Local.VarEscalation",
                   auto_send=True)]}

    def correction_branch(parent, plan_path, kind):
        """Attempt len(parent)+1 of `kind`, then its own gate."""
        path = parent + (kind,)
        n = len(path)
        msgs = correction_messages(n, kind)
        new_plan_path = path if kind == "replan" else plan_path
        var = variables(parent, plan_path)
        actions = []
        if kind == "replan":
            actions.append(agent_node(path, new_plan_path, "planner", msgs["planner"]))
        actions.append(agent_node(path, new_plan_path, "comms", msgs["comms"]))
        actions.append(agent_node(path, new_plan_path, "compliance", msgs["compliance"]))
        actions.append(gate(path, new_plan_path))
        other = REPLAN if kind == "rewrite" else REWRITE
        token = REWRITE if kind == "rewrite" else REPLAN
        return {"condition": reject_condition(token, other, var["compliance"]),
                "id": reject_branch(parent, kind), "actions": actions}

    def gate(path, plan_path):
        i = ids(path)
        conditions = [approve_branch(path, plan_path)]
        if len(path) < MAX_CORRECTIONS:
            conditions.append(correction_branch(path, plan_path, "rewrite"))
            conditions.append(correction_branch(path, plan_path, "replan"))
        conditions.append(escalate_branch(path))
        return {"kind": "ConditionGroup", "id": i["gate"], "conditions": conditions}

    actions = []
    for key, out_var, response_object in (
            ("triage", "Local.VarTriage", None), ("evidence", "Local.VarEvidence", None),
            ("usage", "Local.VarUsage", None), ("policy", "Local.VarPolicy", None),
            ("planner", "Local.VarPlan", None),
            ("comms", "Local.VarCustomerDraft", "Local.VarCustomerMessage"),
            ("compliance", "Local.Var1497", None)):
        src = _find(top, V10[key])
        messages[V10[key]] = v10_messages[V10[key]]
        actions.append(invoke(V10[key], src["agent"]["name"], v10_messages[V10[key]],
                              out_var, response_object))
    actions.append(gate((), ()))
    audit = audit_message(v10_messages[V10["audit"]])
    messages[V10["audit"]] = audit
    actions.append(invoke(V10["audit"], AGENT["audit"], audit, "Local.VarAudit",
                          auto_send=True))
    return actions, messages


# ---- emitter, in the style of the v10 file -----------------------------------

def _q(text: str) -> str:
    """A YAML double-quoted scalar. JSON escapes are valid YAML escapes."""
    return json.dumps(text, ensure_ascii=False)


def emit(actions: list, indent: int) -> list[str]:
    pad = " " * indent
    lines: list[str] = []
    for act in actions:
        kind = act["kind"]
        lines.append(pad + "- kind: " + kind)
        lines.append(pad + "  id: " + act["id"])
        if kind == "InvokeAzureAgent":
            lines += [pad + "  agent:", pad + "    name: " + act["agent"],
                      pad + "  conversationId: =System.ConversationId",
                      pad + "  input:", pad + "    messages: " + _q(act["message"]),
                      pad + "  output:",
                      pad + "    autoSend: " + ("true" if act["autoSend"] else "false"),
                      pad + "    messages: " + act["messages"]]
            if act.get("responseObject"):
                lines.append(pad + "    responseObject: " + act["responseObject"])
        elif kind == "ConditionGroup":
            lines.append(pad + "  conditions:")
            for cond in act["conditions"]:
                c = cond["condition"]
                assert "'" not in c
                quoted = '"true"' if c == "true" else "'%s'" % c
                lines.append(pad + "    - condition: " + quoted)
                lines.append(pad + "      id: " + cond["id"])
                lines.append(pad + "      actions:")
                lines += emit(cond["actions"], indent + 8)
        elif kind == "SendActivity":
            lines.append(pad + "  activity: |-")
            for line in act["activity"].split("\n"):
                lines.append((pad + "    " + line) if line else "")
        elif kind == "SetVariable":
            lines.append(pad + "  variable: " + act["variable"])
            lines.append(pad + "  value: " + act["value"])
        else:
            raise ValueError(kind)
    return lines


def render() -> tuple[str, str]:
    v10, v10_messages = _v10()
    actions, messages = build(v10, v10_messages)
    lines = (["kind: workflow", "trigger:", "  kind: OnConversationStart",
              "  id: trigger_wf", "  actions:"] + emit(actions, 4)
             + ['id: ""', "name: GridResolveAIWorkflow"])
    text = "\n".join(lines) + "\n"
    ordered = {"_about": (
        "The explicit input message each agent node of GridResolveAIWorkflow v11 "
        "passes to its agent, generated by build_v11.py. Attempt-0 messages are the "
        "reviewed v10 messages. Correction messages name the step and the attempt, "
        "say what to read and what to return, and state no finding, no verdict and "
        "no expected outcome. Keyed by workflow action id.")}
    ordered.update(messages)
    return text, json.dumps(ordered, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    text, messages = render()
    if "--check" in argv:
        drift = []
        for path, expected in ((V11_YAML, text), (V11_MESSAGES, messages)):
            current = None
            if os.path.exists(path):
                with open(path, encoding="utf-8") as fh:
                    current = fh.read().replace("\r\n", "\n")
            if current != expected:
                drift.append(os.path.relpath(path, HERE))
        print("v11 in sync" if not drift else "v11 DRIFT: " + ", ".join(drift))
        return 1 if drift else 0
    for path, content in ((V11_YAML, text), (V11_MESSAGES, messages)):
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        print("wrote", os.path.relpath(path, HERE), "%d lines" % content.count("\n"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
