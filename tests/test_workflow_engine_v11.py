"""
GridResolveAIWorkflow v11, the bounded-correction design, run through
Microsoft's open-source declarative workflow engine with scripted agents.
No network, no Azure call, no model request, no cost.

The scripted replies are the genuine agent outputs of the final hosted run
(evidence/runtime/20260921T000142Z_SYN-CASE-4003_c2be2b51, workflow v10),
read and never written, plus hand-built compliance decisions and edited drafts
labelled OFFLINE_FIXTURE. A reply given as a list is consumed one per
invocation, which is how a rejected draft is followed by a corrected one.

What this establishes: how Microsoft's open-source engine runs the v11 YAML,
and that the runner's v11 map reads what it did. What it does not: that the
hosted Foundry service behaves the same. v11 is not published. Nothing here is
Foundry execution evidence.

Needs the .NET SDK. Run: python tests/test_workflow_engine_v11.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tests", "workflow_engine"))

import build_v11  # noqa: E402
import test_workflow_engine as v10t  # noqa: E402
from runner import analysis, workflow_map as v10, workflow_v11 as v11  # noqa: E402
from runner import workflow_versions as wv  # noqa: E402

FINAL_RUN = os.path.join(ROOT, "evidence", "runtime",
                         "20260921T000142Z_SYN-CASE-4003_c2be2b51")
WORKFLOW_NAME = "GridResolveAIWorkflow"
A, E = v11.APPROVED_TOKEN, v11.ESCALATE_TOKEN
RW, RP = v11.REJECT_REWRITE_TOKEN, v11.REJECT_REPLAN_TOKEN
HUMAN, NONE = v11.FOLLOWUP_HUMAN_TOKEN, v11.FOLLOWUP_NONE_TOKEN
FIX = "OFFLINE_FIXTURE"

checks, fails = [], []


def check(name, cond, detail=""):
    (checks if cond else fails).append((name, detail))
    print("  [%s] %-66s %s" % ("PASS" if cond else "FAIL", name, detail))


def decision(kind, token, reason_codes=True):
    body = {"case_id": "SYN-CASE-4003", "decision": kind, "failed_checks": ["11"],
            "correction_target": "CustomerCommunicationAgent",
            "correction_instructions": FIX + ": soften the sentence about the meter.",
            "compliance_summary": FIX + ": wording goes beyond the supported claim.",
            "human_review_required": False}
    if reason_codes:
        body["reason_codes"] = [{"code": "UNSUPPORTED_CLAIM", "cites": {"claim_id": "CLM-3"},
                                 "note": FIX}]
    return json.dumps(body) + "\n" + token


def strip_token(text):
    """A planner output without its follow-up line."""
    lines = text.rstrip().splitlines()
    return "\n".join(lines[:-1]) if lines and lines[-1].strip() in (HUMAN, NONE) else text


def walk(actions, depth=0, out=None):
    """Every action and branch of the YAML, with the correction depth it sits at."""
    out = [] if out is None else out
    for act in actions:
        out.append((act, depth))
        for cond in act.get("conditions", []):
            out.append((cond, depth))
            deeper = depth + 1 if cond["id"] in v11.REJECT_BRANCHES else depth
            walk(cond["actions"], deeper, out)
    return out


def main():
    dll = v10t.build()
    work = tempfile.mkdtemp(prefix="gridresolve_engine_v11_")
    base = v10t.real_run_scenario(FINAL_RUN)
    before = {n: os.path.getmtime(os.path.join(FINAL_RUN, n)) for n in os.listdir(FINAL_RUN)}
    draft_text = base["agents"]["CustomerCommunicationAgent"]
    plan_text = base["agents"]["ResolutionPlannerAgent"]
    approved = base["agents"]["EvidenceComplianceAgent"]
    draft = json.loads(draft_text)
    fixed = dict(draft, what_we_found=draft["what_we_found"] + " " + FIX + ": corrected wording.")
    fixed_text = json.dumps(fixed)
    fixed2 = dict(fixed, why_bill_changed=fixed["why_bill_changed"] + " " + FIX + ": second.")
    plan_body = strip_token(plan_text)
    plan_none = plan_body + "\n" + NONE
    plan_human = plan_body + "\n" + HUMAN
    replanned = json.dumps(dict(json.loads(plan_body), reasoning_summary=FIX + ": replanned."))
    seven = ["CaseTriageAgent", "AccountEvidenceAgent", "UsageAnomalyAgent",
             "PolicyKnowledgeAgent", "ResolutionPlannerAgent",
             "CustomerCommunicationAgent", "EvidenceComplianceAgent"]

    def run(overrides=None, version="v11"):
        return v10t.run_engine(dll, work, version, base, overrides)

    def judged(result, overrides):
        """Hand what the engine did to the runner's own analysis with the v11 map."""
        replies = dict(base["agents"], **(overrides or {}))
        cursor = {}
        items = []
        for agent in result["invoked"]:
            reply = replies[agent]
            if isinstance(reply, list):
                reply = reply[cursor.get(agent, 0)]
                cursor[agent] = cursor.get(agent, 0) + 1
            items.append({"type": "message", "role": "assistant",
                          "created_by": {"agent": {"name": agent, "version": "0"}},
                          "content": [{"type": "output_text", "text": reply}]})
            if agent == "EvidenceComplianceAgent":
                items += [{"type": "message", "role": "assistant",
                           "created_by": {"agent": {"name": WORKFLOW_NAME, "version": "11"}},
                           "content": [{"type": "output_text", "text": text}]}
                          for text in result["sent"]]
        actions = [{"action_id": e, "previous_action_id": e} for e in result["executed"]]
        return analysis.analyze(items, actions, WORKFLOW_NAME, WORKFLOW_NAME + " v11",
                                route_map=v11)

    print("\n1. THE v11 DEFINITION IS GENERATED, IN SYNC, AND WELL FORMED")
    sync = subprocess.run([sys.executable, os.path.join(ROOT, "tests", "workflow_engine",
                                                        "build_v11.py"), "--check"],
                          capture_output=True, text=True)
    check("regenerating v11 gives the committed YAML and messages, byte for byte",
          sync.returncode == 0, sync.stdout.strip())
    with open(build_v11.V11_YAML, encoding="utf-8") as fh:
        y = fh.read()
    doc = yaml.safe_load(y)
    nodes = walk(doc["trigger"]["actions"])
    ids = [n["id"] for n, _d in nodes]
    invokes = {n["id"]: n for n, _d in nodes if n.get("kind") == "InvokeAzureAgent"}
    check("every action and branch id is unique", len(ids) == len(set(ids)),
          "%d ids" % len(ids))
    check("every agent node is handed a plain literal message, never an expression",
          all(isinstance(n["input"]["messages"], str)
              and not n["input"]["messages"].startswith("=") for n in invokes.values()))
    check("no SendActivity activity is written as an =expression, the v6 defect",
          not re.search(r"""^\s*activity:\s*['"]?=""", y, re.MULTILINE))
    check("every agent node still shares the one conversation",
          all(n.get("conversationId") == "=System.ConversationId" for n in invokes.values()))
    check("every v10 action id is present in v11",
          all(i in ids for i in v10.AGENT_ACTIONS) and v10.GATE_ACTION in ids
          and v10.RELEASE_ACTION in ids and v10.ESCALATION_ACTION in ids)
    with open(v10t.os.path.join(v10t.WORKFLOWS, "GridResolveAIWorkflow_v10.yaml"),
              encoding="utf-8") as fh:
        y10 = fh.read()
    v10_doc = yaml.safe_load(y10)
    v10_gate = build_v11._find(v10_doc["trigger"]["actions"], v10.GATE_ACTION)
    v11_gate = build_v11._find(doc["trigger"]["actions"], v10.GATE_ACTION)
    check("the attempt-0 approve expression is v10's, plus the REJECT exclusion",
          v11_gate["conditions"][0]["condition"]
          == v10_gate["conditions"][0]["condition"].replace(
              '!("GRIDRESOLVE_ESCALATE" in t)',
              '!("GRIDRESOLVE_ESCALATE" in t) && !("GRIDRESOLVE_REJECT" in t)'))
    check("the attempt-0 gate offers approve, rewrite, replan, then fail closed, in that order",
          [c["id"] for c in v11_gate["conditions"]]
          == [v10.APPROVE_BRANCH, "if-node-a1-reject-rewrite", "if-node-a1-reject-replan",
              v10.ESCALATE_BRANCH])
    deepest = max(d for _n, d in nodes)
    depth2_gates = [n for n, d in nodes if n.get("kind") == "ConditionGroup"
                    and n["id"] in v11.GATE_ACTIONS and d == 2]
    check("the tree is unrolled to exactly two correction attempts",
          deepest == 2 and len(depth2_gates) == 4)
    check("after the second correction a gate can only release or fail closed",
          all(len(g["conditions"]) == 2 and g["conditions"][-1]["condition"] == "true"
              for g in depth2_gates))
    compliance_nodes = [n["id"] for n, _d in nodes if n.get("kind") == "InvokeAzureAgent"
                        and n["agent"]["name"] == "EvidenceComplianceAgent"]
    check("seven compliance reviews exist in the tree: one initial, six corrections",
          len(compliance_nodes) == 7 and len(v11.CORRECTION_COMPLIANCE_ACTIONS) == 6)
    releases = [n for n, _d in nodes if n.get("kind") == "SendActivity"]
    check("every release sends the six customer fields of its own attempt's draft",
          len(releases) == 7 and all(
              r["activity"].count("{" + var + ".") == 6 for r, var in
              ((r, re.search(r"\{(Local\.VarCustomerMessage\w*)\.", r["activity"]).group(1))
               for r in releases)))
    check("each correction attempt reviews a fresh draft variable, never the rejected one",
          len({re.search(r"\{(Local\.VarCustomerMessage\w*)\.", r["activity"]).group(1)
               for r in releases}) == 7)

    print("\n2. THE RUNNER'S v11 MAP DESCRIBES THE SAME DEFINITION")
    check("the map's agent nodes are exactly the YAML's, with the same agent names",
          {i: n["agent"]["name"] for i, n in invokes.items()} == dict(v11.AGENT_ACTIONS))
    check("every gate, release, escalation and follow-up id in the map exists in the YAML",
          all(i in ids for i in v11.GATE_ACTIONS + v11.RELEASE_ACTIONS
              + v11.ESCALATION_ACTIONS + v11.FOLLOWUP_HANDOFF_ACTIONS
              + v11.NO_FOLLOWUP_ACTIONS + tuple(v11.REJECT_BRANCHES)))
    check("the runner selects v10 by default and v11 only when asked",
          wv.active({}) is v10 and wv.active({wv.ENV_VAR: "11"}) is v11
          and wv.active_version({}) == "10")
    refused = False
    try:
        wv.active({wv.ENV_VAR: "12"})
    except Exception:
        refused = True
    check("an unknown version is refused", refused)
    check("old evidence is still read with the v10 map",
          all(wv.for_version(v) is v10 for v in ("6", "9", "10")))
    with open(build_v11.V11_MESSAGES, encoding="utf-8") as fh:
        messages = {k: v for k, v in json.load(fh).items() if not k.startswith("_")}
    check("one invocation message per agent node, and none is empty",
          set(messages) == set(invokes) and all(messages.values()))
    check("each message names the agent its node invokes and says nobody will confirm",
          all(invokes[i]["agent"]["name"] in t and "no confirmation will be given" in t
              for i, t in messages.items()))
    check("attempt-0 messages are the reviewed v10 messages, unchanged, except the audit",
          all(messages[i] == v10t.json.load(open(os.path.join(
              v10t.PROJECT, "invocation_messages_v10.json"), encoding="utf-8"))[i]
              for i in v10.AGENT_ACTIONS if i != v10.AUDIT_ACTION))
    correction_ids = [i for i in invokes if i in v11.CORRECTION_STARTS
                      or i in v11.CORRECTION_COMPLIANCE_ACTIONS
                      or (i.startswith("node-a") and i.endswith("-comms"))]
    check("every correction message states the attempt number and the bound of 2",
          all(re.search(r"CORRECTION ATTEMPT [12] of 2", messages[i]) for i in correction_ids))
    check("the audit is asked to record correction_count and every rejection reason",
          "correction_count" in messages[v10.AUDIT_ACTION]
          and "reason codes" in messages[v10.AUDIT_ACTION])
    with open(os.path.join(ROOT, "submission", "SYN-CASE-4003_input.json"), encoding="utf-8") as fh:
        records = json.load(fh)["synthetic_account_records"]
    figures = [str(v) for bill in records["billing_history"]
               for v in (bill["kwh_billed"], bill["amount_usd"])] \
        + [str(r["register_kwh"]) for r in records["meter_reads"]]
    told = [w for w in figures + [A, E, RW, RP, HUMAN, NONE, "broken", "PASS", "APPROVE",
                                  "REJECT"]
            if any(w in text for text in messages.values())]
    check("no message states a case figure, a finding, a verdict or a route token",
          told == [], str(told))
    check("no message repeats the case: the longest is under 1200 characters",
          max(len(t) for t in messages.values()) < 1200)

    print("\n3. ATTEMPT 0: v11 RELEASES EXACTLY WHAT v10 RELEASED, ON THE FINAL RUN'S OUTPUTS")
    got10 = run(version="v10")
    got11 = run()
    check("v10 with the genuine final-run outputs releases one message",
          got10["failed"] == [] and len(got10["sent"]) == 1, str(got10["failed"])[:80])
    check("v11 takes the same actions in the same order",
          got11["failed"] == [] and got11["executed"] == got10["executed"])
    check("v11 invokes the same nine agents in the same order",
          got11["invoked"] == got10["invoked"] and got11["invoked"][-1] == "CaseAuditAgent")
    check("v11 releases the identical text, character for character",
          got11["sent"] == got10["sent"]
          and got11["sent"] == [v11.compose_customer_message(draft)])
    check("v11 hands the case to a human afterwards, as the final run did",
          v10.FOLLOWUP_HANDOFF_ACTION in got11["executed"])
    seen = judged(got11, None)
    check("the runner reads it as released, zero corrections, audited",
          seen["route"]["route"] == "APPROVED_AND_RELEASED"
          and seen["route"]["correction_attempts"] == 0
          and seen["route"]["rejections_observed"] == []
          and seen["route"]["audit_ran"] and seen["release"]["customer_ready"] is True)

    print("\n4. REWRITE, THEN APPROVE: THE CORRECTED DRAFT IS RELEASED, THE REJECTED ONE IS NOT")
    ov = {"EvidenceComplianceAgent": [decision("REJECT_AND_REWRITE", RW), approved],
          "CustomerCommunicationAgent": [draft_text, fixed_text]}
    got = run(ov)
    check("the engine ran without failure", got["failed"] == [], str(got["failed"])[:80])
    check("the communication agent was invoked twice and compliance twice, planner once",
          got["invoked"] == seven + ["CustomerCommunicationAgent", "EvidenceComplianceAgent",
                                     "EscalationCoordinatorAgent", "CaseAuditAgent"])
    expected_nodes = ["node-a1-rewrite-comms", "node-a1-rewrite-compliance",
                      "node-a1-rewrite-release-approved-message"]
    check("the correction nodes ran, in order",
          [e for e in got["executed"] if e in expected_nodes] == expected_nodes)
    check("exactly one message was sent, and it is the corrected draft",
          got["sent"] == [v11.compose_customer_message(fixed)])
    check("the rejected draft was not sent",
          got["sent"] != [v11.compose_customer_message(draft)]
          and FIX in got["sent"][0])
    check("the rewrite invocation received its own correction message as a user turn",
          [m["Text"] for m in got["inputs"][7]["Given"]] == [messages["node-a1-rewrite-comms"]]
          and got["inputs"][7]["Agent"] == "CustomerCommunicationAgent")
    check("the case was then handed to a human, from the original plan's token",
          "node-a1-rewrite-followup-handoff" in got["executed"])
    seen = judged(got, ov)
    check("the runner reads it as released after one REWRITE correction",
          seen["route"]["route"] == "APPROVED_AND_RELEASED"
          and seen["route"]["correction_attempts"] == 1
          and seen["route"]["rejections_observed"] == ["REWRITE"]
          and seen["release"]["customer_ready"] is True, str(seen["route"])[:100])
    check("the runner's release check compares against the latest draft",
          seen["release"]["outcome"] == analysis.RELEASE_CUSTOMER_MESSAGE)
    check("the runner reads the final compliance token, the approval, not the rejection",
          seen["compliance"]["token"] == "APPROVED")

    print("\n5. REPLAN, THEN APPROVE: THE FOLLOW-UP GATE READS THE NEW PLAN")
    ov = {"EvidenceComplianceAgent": [decision("REJECT_AND_REPLAN", RP), approved],
          "ResolutionPlannerAgent": [plan_human, replanned + "\n" + NONE],
          "CustomerCommunicationAgent": [draft_text, fixed_text]}
    got = run(ov)
    check("planner, communication and compliance each ran twice",
          got["failed"] == [] and got["invoked"]
          == seven + ["ResolutionPlannerAgent", "CustomerCommunicationAgent",
                      "EvidenceComplianceAgent", "CaseAuditAgent"])
    check("the corrected draft was released, once",
          got["sent"] == [v11.compose_customer_message(fixed)])
    check("the new plan cleared the case, so no human handoff was created",
          "node-a1-replan-record-no-followup" in got["executed"]
          and "EscalationCoordinatorAgent" not in got["invoked"])
    seen = judged(got, ov)
    check("the runner reads it as released after one REPLAN, follow-up NONE_REQUIRED",
          seen["route"]["route"] == "APPROVED_AND_RELEASED"
          and seen["route"]["rejections_observed"] == ["REPLAN"]
          and seen["route"]["case_follow_up"] == "NONE_REQUIRED")
    ov["ResolutionPlannerAgent"] = [plan_none, replanned + "\n" + HUMAN]
    got = run(ov)
    check("and the reverse: the original plan cleared the case but the new plan does not, "
          "so a handoff is created", got["failed"] == []
          and "node-a1-replan-followup-handoff" in got["executed"]
          and got["invoked"][-2:] == ["EscalationCoordinatorAgent", "CaseAuditAgent"])

    print("\n6. THE BOUND: A THIRD NON-APPROVAL FAILS CLOSED, NOTHING IS SENT")
    bound_cases = (
        ("rewrite, rewrite, then reject",
         {"EvidenceComplianceAgent": [decision("REJECT_AND_REWRITE", RW)] * 2
          + [decision("HUMAN_REVIEW_REQUIRED", E)],
          "CustomerCommunicationAgent": [draft_text, fixed_text, json.dumps(fixed2)]},
         "node-a1-rewrite-a2-rewrite-escalate", ["REWRITE", "REWRITE"]),
        ("replan, rewrite, then reject",
         {"EvidenceComplianceAgent": [decision("REJECT_AND_REPLAN", RP),
                                      decision("REJECT_AND_REWRITE", RW),
                                      decision("HUMAN_REVIEW_REQUIRED", E)],
          "ResolutionPlannerAgent": [plan_human, replanned + "\n" + HUMAN],
          "CustomerCommunicationAgent": [draft_text, fixed_text, json.dumps(fixed2)]},
         "node-a1-replan-a2-rewrite-escalate", ["REPLAN", "REWRITE"]),
        ("rewrite, rewrite, then a third rewrite request, which the shape cannot grant",
         {"EvidenceComplianceAgent": [decision("REJECT_AND_REWRITE", RW)] * 3,
          "CustomerCommunicationAgent": [draft_text, fixed_text, json.dumps(fixed2)]},
         "node-a1-rewrite-a2-rewrite-escalate", ["REWRITE", "REWRITE"]),
        ("replan, replan, then a third replan request",
         {"EvidenceComplianceAgent": [decision("REJECT_AND_REPLAN", RP)] * 3,
          "ResolutionPlannerAgent": [plan_human, replanned + "\n" + HUMAN,
                                     replanned + "\n" + HUMAN],
          "CustomerCommunicationAgent": [draft_text, fixed_text, json.dumps(fixed2)]},
         "node-a1-replan-a2-replan-escalate", ["REPLAN", "REPLAN"]))
    for label, ov, escalate_node, kinds in bound_cases:
        got = run(ov)
        check("%s: nothing sent, escalated once, audited last" % label,
              got["failed"] == [] and got["sent"] == []
              and got["invoked"].count("EscalationCoordinatorAgent") == 1
              and escalate_node in got["executed"]
              and got["invoked"][-1] == "CaseAuditAgent", str(got["failed"] or got["invoked"][-3:])[:90])
        check("%s: compliance ran exactly three times" % label,
              got["invoked"].count("EvidenceComplianceAgent") == 3)
        seen = judged(got, ov)
        check("%s: the runner reads two corrections, then escalation" % label,
              seen["route"]["route"] == "ESCALATED_TO_HUMAN"
              and seen["route"]["correction_attempts"] == 2
              and seen["route"]["rejections_observed"] == kinds
              and seen["route"]["case_follow_up"] == "HANDED_TO_HUMAN"
              and seen["release"]["customer_ready"] is False, str(seen["route"])[:100])

    print("\n7. ROUTING IS THE TOKEN AND THE DECISION OBJECT, NOTHING ELSE")
    ov = {"EvidenceComplianceAgent": [approved] * 3}
    got = run(ov)
    check("three scripted approvals: one release, compliance consulted once",
          got["failed"] == [] and len(got["sent"]) == 1
          and got["invoked"].count("EvidenceComplianceAgent") == 1)
    for label, second in (
            ("a malformed token at attempt 1", '{"decision":"APPROVE"}\nROUTE_DECISION::GRIDRESOLVE_APROVED'),
            ("both approve and rewrite tokens at attempt 1", '{"decision":"APPROVE"}\n' + A + "\n" + RW),
            ("prose only at attempt 1", "The corrected draft reads well now."),
            ("an empty output at attempt 1", "")):
        ov = {"EvidenceComplianceAgent": [decision("REJECT_AND_REWRITE", RW), second],
              "CustomerCommunicationAgent": [draft_text, fixed_text]}
        got = run(ov)
        check("%s: nothing sent, escalated once, audited" % label,
              got["failed"] == [] and got["sent"] == []
              and got["invoked"].count("EscalationCoordinatorAgent") == 1
              and "node-a1-rewrite-escalate" in got["executed"]
              and got["invoked"][-1] == "CaseAuditAgent", str(got["failed"])[:80])
    ov = {"EvidenceComplianceAgent": decision("REJECT_AND_REWRITE", RW) + "\n" + A}
    got = run(ov)
    check("approved token present but the decision rejects and the text holds a REJECT token: "
          "not released, not corrected, escalated",
          got["failed"] == [] and got["sent"] == []
          and got["invoked"].count("EvidenceComplianceAgent") == 1
          and v10.ESCALATION_ACTION in got["executed"])
    for label, text in (("the rewrite token alone, no decision object", RW),
                        ("the replan token alone", RP),
                        ("a rewrite token after prose, no JSON", "Please soften it.\n" + RW),
                        ("a rewrite token quoted inside the JSON only",
                         json.dumps({"decision": "REJECT_AND_REWRITE", "note": RW}))):
        got = run({"EvidenceComplianceAgent": text})
        check("%s: no correction is attempted, escalated, audited" % label,
              got["failed"] == [] and got["sent"] == []
              and got["invoked"].count("EvidenceComplianceAgent") == 1
              and v10.ESCALATION_ACTION in got["executed"]
              and got["invoked"][-1] == "CaseAuditAgent", str(got["failed"])[:80])
    with_codes = run({"EvidenceComplianceAgent": [decision("REJECT_AND_REWRITE", RW, True), approved],
                      "CustomerCommunicationAgent": [draft_text, fixed_text]})
    without = run({"EvidenceComplianceAgent": [decision("REJECT_AND_REWRITE", RW, False), approved],
                   "CustomerCommunicationAgent": [draft_text, fixed_text]})
    check("reason codes present or absent, the route is the same: they are for people and checks",
          with_codes["executed"] == without["executed"] and with_codes["sent"] == without["sent"])
    got = run({"EvidenceComplianceAgent": [decision("REJECT_AND_REWRITE", RW), approved],
               "CustomerCommunicationAgent": [draft_text, json.dumps(dict(fixed, what_we_found="  "))]})
    check("a corrected draft with a blank field is withheld and escalated, as in v10",
          got["failed"] == [] and got["sent"] == []
          and "node-a1-rewrite-escalate" in got["executed"])
    got = run({"EvidenceComplianceAgent": [decision("REJECT_AND_REWRITE", RW), approved],
               "CustomerCommunicationAgent": [draft_text, "Dear customer, all fixed."]})
    check("a corrected draft that is not JSON is withheld and escalated",
          got["failed"] == [] and got["sent"] == []
          and "node-a1-rewrite-escalate" in got["executed"])

    print("\n8. THE AUDIT AGENT RUNS LAST ON EVERY PATH, AND v10 IS UNCHANGED")
    paths = [run(o) for o in (
        None,
        {"EvidenceComplianceAgent": [decision("REJECT_AND_REWRITE", RW), approved],
         "CustomerCommunicationAgent": [draft_text, fixed_text]},
        {"EvidenceComplianceAgent": [decision("REJECT_AND_REPLAN", RP), approved],
         "ResolutionPlannerAgent": [plan_human, replanned + "\n" + NONE],
         "CustomerCommunicationAgent": [draft_text, fixed_text]},
        {"EvidenceComplianceAgent": decision("HUMAN_REVIEW_REQUIRED", E)},
        {"EvidenceComplianceAgent": [decision("REJECT_AND_REWRITE", RW),
                                     decision("REJECT_AND_REPLAN", RP), approved],
         "ResolutionPlannerAgent": [plan_human, replanned + "\n" + HUMAN],
         "CustomerCommunicationAgent": [draft_text, fixed_text, json.dumps(fixed2)]})]
    check("on every path the terminal audit runs last and exactly once",
          all(p["failed"] == [] and p["invoked"][-1] == "CaseAuditAgent"
              and p["invoked"].count("CaseAuditAgent") == 1 for p in paths))
    check("on every path at most one message reaches the customer",
          all(len(p["sent"]) <= 1 for p in paths))
    check("rewrite then replan then approve releases the third draft",
          paths[4]["sent"] == [v11.compose_customer_message(fixed2)]
          and "node-a1-rewrite-a2-replan-release-approved-message" in paths[4]["executed"])
    check("the v10 definition file is unchanged by all of this",
          y10 == open(os.path.join(v10t.WORKFLOWS, "GridResolveAIWorkflow_v10.yaml"),
                      encoding="utf-8").read())
    check("the final run's evidence files were not modified by any of this",
          before == {n: os.path.getmtime(os.path.join(FINAL_RUN, n))
                     for n in os.listdir(FINAL_RUN)})
    shutil.rmtree(work, ignore_errors=True)

    print("\n" + "=" * 68)
    print("RESULT: %d passed, %d failed" % (len(checks), len(fails)))
    print("=" * 68)
    print("Open-source engine, scripted agents, v11 unpublished. Not Foundry execution evidence.")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
