"""
Runs the real GridResolveAIWorkflow YAML definitions through Microsoft's
open-source declarative workflow engine, with every agent replaced by a scripted
reply. No network, no Azure call, no model request, no cost.

The scripted replies are the genuine agent outputs captured in the two real runs
(evidence/runtime/20260920T205607Z_SYN-CASE-4003_80391bf2 and
evidence/runtime/20260920T225342Z_SYN-CASE-4003_5e6f1114), edited only where a
scenario says so, plus one offline fixture labelled as such. Those evidence files
are read, never written.

CALIBRATION. The v6 definition is run first and must reproduce what the hosted
Foundry service actually did with it on 2026-09-20: the same agents, the same
branch, and the literal text "=Last(Local.VarCustomerDraft).Text" delivered to
the customer. That is the evidence that this engine is a fair stand-in.

What this establishes: how Microsoft's open-source engine runs these definitions.
What it does not: that the closed-source hosted service behaves identically for
v10. Nothing here is Foundry execution evidence.

Needs the .NET SDK. Run: python tests/test_workflow_engine.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests", "workflow_engine"))

import offline_fixtures  # noqa: E402
from runner import analysis, workflow_map as wm  # noqa: E402

PROJECT = os.path.join(ROOT, "tests", "workflow_engine")
WORKFLOWS = os.path.join(PROJECT, "workflows")
REAL_RUN = os.path.join(ROOT, "evidence", "runtime",
                        "20260920T205607Z_SYN-CASE-4003_80391bf2")
SECOND_RUN = os.path.join(ROOT, "evidence", "runtime",
                          "20260920T225342Z_SYN-CASE-4003_5e6f1114")
WORKFLOW_NAME = "GridResolveAIWorkflow"
A, E = wm.APPROVED_TOKEN, wm.ESCALATE_TOKEN
HUMAN, NONE = wm.FOLLOWUP_HUMAN_TOKEN, wm.FOLLOWUP_NONE_TOKEN
# The definition the runner expects to be live. v10 is v9 plus an explicit input message on
# every agent node and a third gate term that requires a completed investigation.
LIVE = "v" + wm.WORKFLOW_VERSION

checks, fails = [], []


def check(name, cond, detail=""):
    (checks if cond else fails).append((name, detail))
    print("  [%s] %-66s %s" % ("PASS" if cond else "FAIL", name, detail))


def real_run_scenario(run_dir=None):
    """The genuine input and agent outputs of a real run, keyed by agent name. Run 1 by default."""
    with open(os.path.join(run_dir or REAL_RUN, "07_conversation_items.json"),
              encoding="utf-8") as fh:
        items = analysis.items_of(json.load(fh))
    agents = {}
    for item in items:
        if item.get("type") == "message" and item.get("role") == "assistant":
            name = item["created_by"]["agent"]["name"]
            if name != WORKFLOW_NAME:
                agents[name] = analysis.text_of(item)
    user = [analysis.text_of(i) for i in items if i.get("role") == "user"][0]
    # EscalationCoordinatorAgent did not run in run 1, so a labelled placeholder stands in there.
    agents.setdefault("EscalationCoordinatorAgent", json.dumps(
        {"case_state": "HUMAN_REVIEW", "scripted": "placeholder, not a real output"}))
    return {"input": user, "agents": agents}


def build():
    done = subprocess.run(["dotnet", "build", PROJECT, "-c", "Release", "-v", "q",
                           "--nologo"], capture_output=True, text=True)
    if done.returncode != 0:
        print(done.stdout[-1500:], done.stderr[-500:])
        sys.exit("The workflow engine harness did not build. Is the .NET SDK installed?")
    out = os.path.join(PROJECT, "bin", "Release", "net9.0")
    return os.path.join(out, "workflow_engine.dll")


def run_engine(dll, workdir, version, scenario, overrides=None):
    data = json.loads(json.dumps(scenario))
    data["agents"].update(overrides or {})
    path = os.path.join(workdir, "scenario.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    yaml_path = os.path.join(WORKFLOWS, "%s_%s.yaml" % (WORKFLOW_NAME, version))
    done = subprocess.run(["dotnet", dll, yaml_path, path], capture_output=True,
                          text=True, encoding="utf-8", timeout=180)
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("{")]
    if not lines:
        return {"executed": [], "invoked": [], "sent": [],
                "failed": ["no summary: " + (done.stderr or done.stdout)[-300:]]}
    return json.loads(lines[-1])


def main():
    dll = build()
    base = real_run_scenario()
    draft_text = base["agents"]["CustomerCommunicationAgent"]
    plan_text = base["agents"]["ResolutionPlannerAgent"]
    draft = json.loads(draft_text)
    before = {n: os.path.getmtime(os.path.join(REAL_RUN, n)) for n in os.listdir(REAL_RUN)}
    work = tempfile.mkdtemp(prefix="gridresolve_engine_")
    eight = ["CaseTriageAgent", "AccountEvidenceAgent", "UsageAnomalyAgent",
             "PolicyKnowledgeAgent", "ResolutionPlannerAgent",
             "CustomerCommunicationAgent", "EvidenceComplianceAgent", "CaseAuditAgent"]
    through_compliance = eight[:7]
    with open(os.path.join(ROOT, "submission", "SYN-CASE-4003_input.json"), encoding="utf-8") as fh:
        case = json.load(fh)
    # No real run has produced an evidence ledger. The healthy path uses one built from the
    # case records by plain copying, labelled OFFLINE_FIXTURE. Everything else in `healthy`
    # is the genuine run-1 output of the agent concerned.
    ledger_fixture = offline_fixtures.evidence_ledger_text(case)
    healthy = json.loads(json.dumps(base))
    healthy["agents"]["AccountEvidenceAgent"] = ledger_fixture

    print("\n1. CALIBRATION: v6 IN THIS ENGINE AGAINST v6 IN THE HOSTED SERVICE")
    got = run_engine(dll, work, "v6", base)
    check("the engine ran v6 without failure", got["failed"] == [], str(got["failed"])[:80])
    check("it delivered the same literal text the hosted service delivered",
          got["sent"] == ["=Last(Local.VarCustomerDraft).Text"], str(got["sent"])[:80])
    check("it invoked the same eight agents in the same order", got["invoked"] == eight)
    with open(os.path.join(REAL_RUN, "04_workflow_actions.json"), encoding="utf-8") as fh:
        hosted = json.load(fh)
    hosted_ids = {a["action_id"] for a in hosted}
    hosted_prev = {a["previous_action_id"] for a in hosted}
    check("every action id the hosted service emitted was executed here",
          hosted_ids <= set(got["executed"]), str(hosted_ids - set(got["executed"])))
    check("every predecessor id the hosted service named exists in this engine",
          hosted_prev <= set(got["executed"]), str(hosted_prev - set(got["executed"])))
    check("the escalation agent did not run, as in the hosted run",
          "EscalationCoordinatorAgent" not in got["invoked"])

    print("\n2. v7 EVALUATES ITS TEMPLATE, BUT SENDS THE WHOLE INTERNAL JSON")
    got = run_engine(dll, work, "v7", base)
    check("v7 delivers the draft text rather than an expression",
          got["failed"] == [] and got["sent"] == [draft_text])
    check("which exposes internal fields to the customer, the reason for v8",
          "internal_claim_ids" in got["sent"][0] and got["sent"][0].lstrip().startswith("{"))

    print("\n3. v10 RELEASES A CUSTOMER-READY MESSAGE FROM THE REAL RUN-1 DRAFT")
    needs_human = {"ResolutionPlannerAgent": plan_text + "\n" + HUMAN}
    got = run_engine(dll, work, LIVE, healthy, needs_human)
    check("v10 ran without failure", got["failed"] == [], str(got["failed"])[:80])
    check("exactly one message was sent to the customer", len(got["sent"]) == 1)
    message = got["sent"][0] if got["sent"] else ""
    expected = wm.compose_customer_message(draft)
    check("it equals the six customer-facing fields of the real draft, in order",
          analysis._same_text(message, expected))
    check("it opens with the real customer summary, not with JSON",
          message.startswith(draft["customer_summary"]) and not message.lstrip().startswith("{"))
    check("it carries every heading and every customer field",
          all(h in message for h, _f in wm.RELEASE_FIELDS if h)
          and all(draft[f] in message for _h, f in wm.RELEASE_FIELDS))
    check("it carries no JSON syntax and no internal field name",
          '"' + "customer_summary" + '"' not in message and "internal_" not in message
          and "communication_risk_flags" not in message and "case_state" not in message)
    check("it carries no claim id and no policy id from the internal lists",
          not any(i in message for i in draft["internal_claim_ids"])
          and not any(i in message for i in draft["internal_policy_ids"]))
    verdict = analysis.release_check(
        [{"type": "message", "role": "assistant",
          "created_by": {"agent": {"name": "CustomerCommunicationAgent", "version": "5"}},
          "content": [{"type": "output_text", "text": draft_text}]},
         {"type": "message", "role": "assistant",
          "created_by": {"agent": {"name": WORKFLOW_NAME, "version": "8"}},
          "content": [{"type": "output_text", "text": message}]}], WORKFLOW_NAME)
    check("the runner's own check calls that delivery customer-ready",
          verdict["outcome"] == analysis.RELEASE_CUSTOMER_MESSAGE
          and verdict["customer_ready"] is True)
    print("      identifiers the agent itself wrote into that prose: %s"
          % (", ".join(verdict["identifiers_in_release"]) or "none"))

    print("\n4. v10: MESSAGE APPROVAL AND HUMAN REVIEW ARE ROUTED SEPARATELY")
    check("approved message AND case needs a person: released, then handed off, then audited",
          got["invoked"] == through_compliance + ["EscalationCoordinatorAgent", "CaseAuditAgent"]
          and wm.FOLLOWUP_HANDOFF_ACTION in got["executed"]
          and wm.ESCALATION_ACTION not in got["executed"])
    got = run_engine(dll, work, LIVE, healthy, {"ResolutionPlannerAgent": plan_text + "\n" + NONE})
    check("approved message and no follow-up needed: released, no handoff, audited",
          got["failed"] == [] and len(got["sent"]) == 1 and got["invoked"] == eight
          and wm.NO_FOLLOWUP_ACTION in got["executed"])
    for label, text in (
            ("the genuine run-1 plan, which has no token", plan_text),
            ("both follow-up tokens", plan_text + "\n" + HUMAN + "\n" + NONE),
            ("the NONE token only quoted in prose", plan_text + "\nI will not write " + NONE + " here."),
            ("the NONE token in lower case", plan_text + "\n" + NONE.lower()),
            ("an empty plan", "")):
        got = run_engine(dll, work, LIVE, healthy, {"ResolutionPlannerAgent": text})
        check("fail closed on %s: handed to a human" % label,
              got["failed"] == [] and "EscalationCoordinatorAgent" in got["invoked"]
              and got["invoked"][-1] == "CaseAuditAgent", str(got["failed"])[:60])

    print("\n5. v10: A MESSAGE COMPLIANCE DOES NOT APPROVE IS NEVER RELEASED")
    for label, text in (
            ("an escalate decision", '{"decision":"HUMAN_REVIEW_REQUIRED"}\n' + E),
            ("a rejection that quotes the approved token",
             "I am not emitting " + A + " for this draft.\n" + E),
            ("prose with no token", "The draft looks reasonable to me."),
            ("both tokens", A + "\n" + E),
            ("an empty compliance output", "")):
        got = run_engine(dll, work, LIVE, healthy,
                         dict(needs_human, EvidenceComplianceAgent=text))
        check("%s: nothing sent, escalated once, audited" % label,
              got["failed"] == [] and got["sent"] == []
              and got["invoked"].count("EscalationCoordinatorAgent") == 1
              and wm.ESCALATION_ACTION in got["executed"]
              and wm.FOLLOWUP_HANDOFF_ACTION not in got["executed"]
              and got["invoked"][-1] == "CaseAuditAgent", str(got)[:80])

    print("\n6. v10: AN APPROVED DRAFT THAT CANNOT BE READ IS WITHHELD AND ESCALATED")
    for label, text in (
            ("a draft that is not JSON", "Dear customer, we cannot confirm the meter is broken."),
            ("a draft wrapped in a code fence", "```json\n" + draft_text + "\n```"),
            ("a draft with a blank customer summary",
             json.dumps(dict(draft, customer_summary=""))),
            ("a draft with a blank later field",
             json.dumps(dict(draft, what_happens_next="")))):
        got = run_engine(dll, work, LIVE, healthy,
                         dict(needs_human, CustomerCommunicationAgent=text))
        check("%s: nothing sent, escalated, audited" % label,
              got["failed"] == [] and got["sent"] == []
              and "EscalationCoordinatorAgent" in got["invoked"]
              and got["invoked"][-1] == "CaseAuditAgent", str(got)[:80])
    got = run_engine(dll, work, LIVE, healthy, dict(
        needs_human, CustomerCommunicationAgent=json.dumps({"customer_summary": "Only this."})))
    check("KNOWN LIMIT: a draft missing a field stops the run at the gate, before any release",
          got["sent"] == [] and any(wm.GATE_ACTION in f for f in got["failed"])
          and "CaseAuditAgent" not in got["invoked"], str(got["failed"])[:80])
    print("      That path cannot be caught in Power Fx, it is a binding error. It is closed")
    print("      off at the source: CustomerCommunicationAgent v5 has a strict JSON schema that")
    print("      requires all six fields, and the runner refuses to run unless that is live.")
    release_fields = [name for _, name in wm.RELEASE_FIELDS]
    missing = [run_engine(dll, work, LIVE, healthy, dict(needs_human, CustomerCommunicationAgent=(
        json.dumps({k: v for k, v in draft.items() if k != name})))) for name in release_fields]
    check("whichever of the six fields is missing, nothing is sent to the customer",
          all(got["sent"] == [] for got in missing))
    check("KNOWN LIMIT: and in each of those six runs no terminal audit is written",
          all(got["failed"] and "CaseAuditAgent" not in got["invoked"] for got in missing))
    nulls = [run_engine(dll, work, LIVE, healthy, dict(needs_human, CustomerCommunicationAgent=(
        json.dumps(dict(draft, **{name: None}))))) for name in release_fields]
    check("whichever of the six fields is null: nothing sent, escalated, audited",
          all(got["failed"] == [] and got["sent"] == []
              and "EscalationCoordinatorAgent" in got["invoked"]
              and got["invoked"][-1] == "CaseAuditAgent" for got in nulls))

    print("\n7. v10: A FIELD HOLDING ONLY WHITESPACE IS WITHHELD. v8 RELEASED IT")
    spaces = dict(draft, what_we_found="   ")
    got = run_engine(dll, work, "v8", base, dict(
        needs_human, CustomerCommunicationAgent=json.dumps(spaces)))
    check("the defect is real: v8 released a message with a field holding only spaces",
          len(got["sent"]) == 1 and wm.compose_customer_message(spaces) is None)
    v8_release = (got["sent"] or [""])[0]
    for label, value in (("spaces", "   "), ("a tab", "\t"), ("a line feed", "\n"),
                         ("a carriage return", "\r"), ("CRLF", "\r\n"),
                         ("spaces, tabs and line breaks mixed", " \t \r\n\t  \n")):
        runs = [run_engine(dll, work, LIVE, healthy, dict(needs_human, CustomerCommunicationAgent=(
            json.dumps(dict(draft, **{name: value}))))) for name in release_fields]
        check("only %s, in any of the six fields: nothing sent, escalated, audited" % label,
              all(g["failed"] == [] and g["sent"] == []
                  and g["invoked"].count("EscalationCoordinatorAgent") == 1
                  and wm.ESCALATION_ACTION in g["executed"]
                  and g["invoked"][-1] == "CaseAuditAgent" for g in runs))
    padded = dict(draft, customer_summary="  \n" + draft["customer_summary"] + " \r\n",
                  what_we_found=draft["what_we_found"] + "\n\n\tSecond paragraph.")
    got = run_engine(dll, work, LIVE, healthy, dict(
        needs_human, CustomerCommunicationAgent=json.dumps(padded)))
    check("prose that merely contains tabs and line breaks is still released, unaltered",
          got["failed"] == [] and len(got["sent"]) == 1
          and analysis._same_text(got["sent"][0], wm.compose_customer_message(padded)))
    same = run_engine(dll, work, "v8", base, needs_human)["sent"] \
        == run_engine(dll, work, LIVE, healthy, needs_human)["sent"]
    check("for the genuine draft, v10 sends exactly what v8 sent", same)
    released = [{"type": "message", "role": "assistant",
                 "created_by": {"agent": {"name": name, "version": version}},
                 "content": [{"type": "output_text", "text": text}]}
                for name, version, text in (
                    ("CustomerCommunicationAgent", "5", json.dumps(spaces)),
                    (WORKFLOW_NAME, "8", v8_release))]
    verdict = analysis.release_check(released, WORKFLOW_NAME)
    check("had v8 done that in a real run, the runner would have reported it",
          verdict["customer_ready"] is False
          and verdict["outcome"] != "DELIVERED_CUSTOMER_MESSAGE", str(verdict)[:80])

    print("\n8. THE ESCALATION AGENT IS INVOKED UNATTENDED, AND A STALL WOULD BE REPORTED")
    print("      A language model cannot be run locally. This tests the workflow around the")
    print("      agent and the runner's detector, not how EscalationCoordinatorAgent v5 behaves.")
    stall = ("Per the instructions this is the handoff step. If you want, I will now prepare "
             "the escalation package. Please confirm to proceed.")
    package = json.dumps({"case_state": "HUMAN_REVIEW", "decision_card": {"decision_needed": "x"}})

    def as_items(name, text):
        return [{"type": "message", "role": "assistant",
                 "created_by": {"agent": {"name": name, "version": "5"}},
                 "content": [{"type": "output_text", "text": text}]}]

    for label, overrides, action in (
            ("after an approved message", needs_human, wm.FOLLOWUP_HANDOFF_ACTION),
            ("on the fail-closed route", dict(needs_human, EvidenceComplianceAgent=(
                '{"decision":"HUMAN_REVIEW_REQUIRED"}\n' + E)), wm.ESCALATION_ACTION)):
        got = run_engine(dll, work, LIVE, healthy,
                         dict(overrides, EscalationCoordinatorAgent=stall))
        check("%s it is invoked once, with no input step before it" % label,
              got["failed"] == [] and action in got["executed"]
              and got["invoked"].count("EscalationCoordinatorAgent") == 1
              and not any("question" in e.lower() or "input" in e.lower()
                          for e in got["executed"]), str(got["executed"])[-80:])
        check("%s a stalled reply does not stop the terminal audit" % label,
              got["invoked"][-1] == "CaseAuditAgent")
    flagged = analysis.output_health(as_items("EscalationCoordinatorAgent", stall), WORKFLOW_NAME)
    check("the runner flags an escalation agent that asks instead of working",
          [f["agent"] for f in flagged] == ["EscalationCoordinatorAgent"]
          and "ASKS_FOR_CONFIRMATION" in flagged[0]["problems"]
          and "NO_JSON_OBJECT" in flagged[0]["problems"])
    check("and does not flag a complete escalation package",
          analysis.output_health(as_items("EscalationCoordinatorAgent", package),
                                 WORKFLOW_NAME) == [])

    print("\n9. BOTH HISTORICAL FAILURES, REPRODUCED ON THE OLD DESIGN, THEN RUN ON v10")
    run2 = real_run_scenario(SECOND_RUN)
    before_2 = {n: os.path.getmtime(os.path.join(SECOND_RUN, n)) for n in os.listdir(SECOND_RUN)}
    nine = eight[:7] + ["EscalationCoordinatorAgent", "CaseAuditAgent"]
    got = run_engine(dll, work, "v9", run2)
    check("v9 with the genuine run-2 outputs takes the route the hosted service took",
          got["failed"] == [] and got["sent"] == [] and got["invoked"] == nine
          and wm.ESCALATION_ACTION in got["executed"])
    with open(os.path.join(SECOND_RUN, "04_workflow_actions.json"), encoding="utf-8") as fh:
        hosted_2 = {a["action_id"] for a in json.load(fh)}
    check("every action id the hosted service emitted in run 2 was executed here",
          hosted_2 <= set(got["executed"]), str(hosted_2 - set(got["executed"])))
    check("the old design hands no agent any message",
          all(i["Given"] == [] for i in got["inputs"]))
    check("so every agent after the first sees another agent's assistant turn last",
          [i["LastVisibleRole"] for i in got["inputs"]] == ["user"] + ["assistant"] * 8,
          "the shape the platform recorded for both real runs")
    got = run_engine(dll, work, "v9", base, needs_human)
    check("v9 with the genuine run-1 outputs releases a message although no ledger exists",
          got["failed"] == [] and len(got["sent"]) == 1,
          "the defect: an incomplete investigation passed")
    got = run_engine(dll, work, LIVE, base, needs_human)
    check("v10 with the same run-1 outputs: nothing sent, escalated once, audited",
          got["failed"] == [] and got["sent"] == []
          and got["invoked"].count("EscalationCoordinatorAgent") == 1
          and wm.ESCALATION_ACTION in got["executed"]
          and got["invoked"][-1] == "CaseAuditAgent")
    got = run_engine(dll, work, LIVE, run2)
    check("v10 with the genuine run-2 outputs: nothing sent, escalated once, audited",
          got["failed"] == [] and got["sent"] == []
          and got["invoked"].count("EscalationCoordinatorAgent") == 1
          and got["invoked"][-1] == "CaseAuditAgent")

    print("\n10. v10: EVERY AGENT IS HANDED AN EXPLICIT, ROLE-SPECIFIC, NEUTRAL MESSAGE")
    with open(os.path.join(PROJECT, "invocation_messages_v10.json"), encoding="utf-8") as fh:
        node_messages = {k: v for k, v in json.load(fh).items() if not k.startswith("_")}
    node_of = {agent: node for node, agent in wm.AGENT_ACTIONS.items()
               if agent != "EscalationCoordinatorAgent"}
    for label, overrides, escalation_node in (
            ("approved message with a human handoff", needs_human, wm.FOLLOWUP_HANDOFF_ACTION),
            ("fail-closed escalation", dict(needs_human, EvidenceComplianceAgent=(
                '{"decision":"HUMAN_REVIEW_REQUIRED","compliance_summary":"x"}\n' + E)),
             wm.ESCALATION_ACTION)):
        got = run_engine(dll, work, LIVE, healthy, overrides)
        expected = [node_messages[escalation_node if agent == "EscalationCoordinatorAgent"
                                  else node_of[agent]] for agent in got["invoked"]]
        check("%s: all nine invocations receive exactly their own message, as a user turn" % label,
              got["invoked"] == nine
              and [[m["Text"] for m in i["Given"]] for i in got["inputs"]] == [[t] for t in expected]
              and all(m["Role"] == "user" for i in got["inputs"] for m in i["Given"]))
        check("%s: no agent sees another agent's turn last" % label,
              [i["LastVisibleRole"] for i in got["inputs"]] == ["user"] * 9)
    check("each message names the agent it is for and says nobody will confirm",
          all(wm.AGENT_ACTIONS[node] in text and "no confirmation will be given" in text
              for node, text in node_messages.items()))
    check("the two escalation messages state the branch the workflow took, and differ",
          "was approved and released" in node_messages[wm.FOLLOWUP_HANDOFF_ACTION]
          and "was not released" in node_messages[wm.ESCALATION_ACTION])
    records = case["synthetic_account_records"]
    figures = [str(v) for bill in records["billing_history"]
               for v in (bill["kwh_billed"], bill["amount_usd"])] \
        + [str(r["register_kwh"]) for r in records["meter_reads"]]
    told = [w for w in figures + [A, E, HUMAN, NONE, "broken", "unsupported", "PASS",
                                  "APPROVE", "REJECT"]
            if any(w in text for text in node_messages.values())]
    check("no message states a case figure, a finding, a verdict or a route token",
          told == [], str(told))
    check("no message repeats the case: the longest is under 1000 characters",
          max(len(t) for t in node_messages.values()) < 1000)

    print("\n11. SEVEN END-TO-END SCENARIOS, JUDGED BY THE ENGINE AND BY THE RUNNER")
    print("      Agent replies are offline fixtures or genuine earlier outputs, scripted.")
    print("      None of this is a Foundry model execution.")

    def judged(overrides):
        """Run v10, then hand what happened to the runner's own analysis."""
        result = run_engine(dll, work, LIVE, healthy, overrides)
        replies = dict(healthy["agents"], **overrides)
        run_items = []
        for agent in result["invoked"]:
            run_items.append({"type": "message", "role": "assistant",
                              "created_by": {"agent": {"name": agent, "version": "0"}},
                              "content": [{"type": "output_text", "text": replies[agent]}]})
            if agent == "EvidenceComplianceAgent":
                run_items += [{"type": "message", "role": "assistant",
                               "created_by": {"agent": {"name": WORKFLOW_NAME,
                                                        "version": wm.WORKFLOW_VERSION}},
                               "content": [{"type": "output_text", "text": text}]}
                              for text in result["sent"]]
        actions = [{"action_id": e, "previous_action_id": e} for e in result["executed"]]
        return result, analysis.analyze(run_items, actions, WORKFLOW_NAME,
                                        "%s v%s" % (WORKFLOW_NAME, wm.WORKFLOW_VERSION))

    approved = healthy["agents"]["EvidenceComplianceAgent"]
    rejected = ('{"decision":"REJECT_AND_REWRITE","failed_checks":["6"],'
                '"compliance_summary":"OFFLINE_FIXTURE: a claim lacks evidence."}\n' + E)
    scenarios = (
        ("1 safe draft, no human follow-up needed",
         {"ResolutionPlannerAgent": plan_text + "\n" + NONE}, True, False, "NONE_REQUIRED"),
        ("2 safe draft, human follow-up required", needs_human, True, True, "HANDED_TO_HUMAN"),
        ("3 unsafe draft, compliance does not approve",
         dict(needs_human, EvidenceComplianceAgent=rejected), False, True, "HANDED_TO_HUMAN"),
        ("4 missing compliance decision, empty output",
         dict(needs_human, EvidenceComplianceAgent=""), False, True, "HANDED_TO_HUMAN"),
        ("5a malformed compliance: approve token with no decision object",
         dict(needs_human, EvidenceComplianceAgent=A), False, True, "HANDED_TO_HUMAN"),
        ("5b malformed compliance: both tokens",
         dict(needs_human, EvidenceComplianceAgent=approved + "\n" + E), False, True,
         "HANDED_TO_HUMAN"),
        ("6 incomplete customer message, a field of spaces",
         dict(needs_human, CustomerCommunicationAgent=json.dumps(
             dict(draft, what_happens_next="   "))), False, True, "HANDED_TO_HUMAN"),
        ("7a incomplete investigation: policy stage stalls, run-2 wording",
         dict(needs_human, PolicyKnowledgeAgent=run2["agents"]["PolicyKnowledgeAgent"]),
         False, True, "HANDED_TO_HUMAN"),
        ("7b incomplete investigation: evidence stage stalls, run-2 wording",
         dict(needs_human, AccountEvidenceAgent=run2["agents"]["AccountEvidenceAgent"]),
         False, True, "HANDED_TO_HUMAN"),
        ("7c incomplete investigation: usage stage announces future work",
         dict(needs_human, UsageAnomalyAgent="I will now produce the usage analysis."),
         False, True, "HANDED_TO_HUMAN"))
    for label, overrides, released, to_human, follow in scenarios:
        result, seen = judged(overrides)
        check("%s: engine" % label,
              result["failed"] == [] and (len(result["sent"]) == 1) == released
              and (result["invoked"].count("EscalationCoordinatorAgent") == 1) == to_human
              and result["invoked"][-1] == "CaseAuditAgent", str(result["invoked"][-3:]))
        check("%s: runner" % label,
              seen["route"]["route"] == ("APPROVED_AND_RELEASED" if released
                                         else "ESCALATED_TO_HUMAN")
              and seen["route"]["case_follow_up"] == follow
              and seen["route"]["audit_ran"]
              and seen["release"]["customer_ready"] is released,
              "%s / %s" % (seen["route"]["route"], seen["route"]["case_follow_up"]))
    _result, seen = judged(scenarios[7][1])
    check("the runner names the stalled policy stage and calls the investigation incomplete",
          seen["investigation"]["incomplete_stages"] == ["PolicyKnowledgeAgent"]
          and "ANNOUNCES_FUTURE_WORK" in seen["unhealthy_outputs"][0]["problems"])
    _result, seen = judged(needs_human)
    check("on the healthy path the runner finds every investigation stage complete",
          seen["investigation"]["complete"] is True and seen["unhealthy_outputs"] == [],
          str(seen["unhealthy_outputs"])[:80])
    check("the second run's evidence files were not modified by any of this",
          before_2 == {n: os.path.getmtime(os.path.join(SECOND_RUN, n))
                       for n in os.listdir(SECOND_RUN)})

    check("the real evidence files were not modified by any of this",
          before == {n: os.path.getmtime(os.path.join(REAL_RUN, n))
                     for n in os.listdir(REAL_RUN)})
    shutil.rmtree(work, ignore_errors=True)

    print("\n" + "=" * 68)
    print("RESULT: %d passed, %d failed" % (len(checks), len(fails)))
    print("=" * 68)
    print("Open-source engine, scripted agents. Not Foundry execution evidence.")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
