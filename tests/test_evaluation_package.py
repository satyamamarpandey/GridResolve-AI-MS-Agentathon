"""Tests for the local evaluation package (evaluation/).

Everything here is offline. No Azure call, no model call. The deterministic
checks are exercised on small hand-built runs, good and bad, so that a check
that always passes or always fails is caught. The three genuine evidence folders
are read, never written, and their hashes are compared before and after.

Run: python tests/test_evaluation_package.py
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

EVIDENCE = os.path.join(ROOT, "evidence", "runtime")
EVAL = os.path.join(ROOT, "evaluation")
DATASETS = os.path.join(EVAL, "datasets")

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        print("FAIL: %s %s" % (name, detail))


def evidence_hashes() -> dict[str, str]:
    result: dict[str, str] = {}
    for folder, _dirs, files in os.walk(EVIDENCE):
        for name in files:
            path = os.path.join(folder, name)
            with open(path, "rb") as handle:
                result[os.path.relpath(path, EVIDENCE)] = hashlib.sha256(
                    handle.read()).hexdigest()
    return result


HASHES_BEFORE = evidence_hashes()

from evaluation import deterministic_checks as dc  # noqa: E402
from evaluation import provenance  # noqa: E402
from evaluation import run_record  # noqa: E402
from evaluation import run_checks  # noqa: E402
from evaluation.policy import policy_change_impact as impact  # noqa: E402

WORKFLOW = "GridResolveAIWorkflow"
LABEL = WORKFLOW + " v10"

with open(os.path.join(ROOT, "submission", "SYN-CASE-4003_input.json"),
          encoding="utf-8") as _handle:
    CASE_TEXT = _handle.read()

REFERENCE = dc.Reference(
    governed_policy_ids=frozenset({"POL-HB-001", "POL-BILL-002", "POL-MTR-003"}),
    expected_root_cause="NO_SUPPORTED_ROOT_CAUSE")


# ---------------------------------------------------------------- fixtures

def entry(evidence_id: str, record: str, field: str, value: str) -> dict:
    return {"evidence_id": evidence_id, "source_record_id": record,
            "field": field, "value": value}


def good_outputs() -> dict[str, tuple[dict, str]]:
    """A small, internally consistent run: agent name to (json, tail)."""
    ledger = [
        entry("EVID-BILL-06-KWH", "SYN-BILL-0003-06", "kwh_billed", "640"),
        entry("EVID-BILL-06-AMT", "SYN-BILL-0003-06", "amount_usd", "152.80"),
        entry("EVID-BILL-07-KWH", "SYN-BILL-0003-07", "kwh_billed", "870"),
        entry("EVID-BILL-07-AMT", "SYN-BILL-0003-07", "amount_usd", "203.40"),
        entry("EVID-READ-A", "SYN-READ-0003-A", "register_kwh", "41820"),
        entry("EVID-READ-B", "SYN-READ-0003-B", "register_kwh", "42690"),
        entry("EVID-DIAG", "SYN-DIAG-0003-01", "result", "PASS"),
        entry("EVID-RATE", "energy_charge_usd_per_kwh",
              "energy_charge_usd_per_kwh", "0.22"),
    ]
    claim = {"claim_id": "CLM-1", "claim_text": "Register delta equals billed kWh.",
             "evidence_ids": ["EVID-READ-A", "EVID-READ-B", "EVID-BILL-07-KWH"],
             "policy_ids": ["POL-HB-001"], "status": "SUPPORTED"}
    draft = {
        "workflow_version": LABEL,
        "customer_summary": "You asked us to confirm whether the meter is broken.",
        "what_we_reviewed": "We reviewed two bills and two meter reads.",
        "what_we_found": "The register moved from 41,820 kWh to 42,690 kWh, "
                         "a change of 870 kWh.",
        "why_bill_changed": "Billed use rose by 230 kWh. We did not find "
                            "evidence that the meter over-recorded.",
        "what_happens_next": "A human reviewer will decide on an inspection. "
                             "We have not applied any credits.",
        "customer_action_needed": "Tell us if anything changed in July.",
        "internal_claim_ids": ["CLM-1"],
        "internal_evidence_ids": ["EVID-READ-A", "EVID-READ-B"],
        "internal_policy_ids": ["POL-HB-001"],
    }
    return {
        "CaseTriageAgent": ({"case_id": "SYN-CASE-4003",
                             "workflow_version": LABEL}, ""),
        "AccountEvidenceAgent": ({
            "workflow_version": LABEL, "evidence_ledger": ledger,
            "billing_comparison": [
                {"formula": "640 * 0.22 + 12.00", "result": "152.80"},
                {"formula": "870 * 0.22 + 12.00", "result": "203.40"},
                {"formula": "42690 - 41820", "result": "870"},
                {"formula": "billed kWh (870) == register delta (870)",
                 "result": "match"}]}, ""),
        "UsageAnomalyAgent": ({"workflow_version": LABEL}, ""),
        "PolicyKnowledgeAgent": ({
            "workflow_version": LABEL,
            "policy_ledger": [{"policy_id": "POL-HB-001"},
                              {"policy_id": "POL-MTR-003"}]}, ""),
        "ResolutionPlannerAgent": ({
            "workflow_version": LABEL,
            "resolution_status": "HUMAN_REVIEW_REQUIRED",
            "root_cause_classification": "NO_SUPPORTED_ROOT_CAUSE",
            "claim_ledger": [claim],
            "customer_adjustment": {"proposed_adjustment_usd": None},
        }, "\nCASE_FOLLOWUP::HUMAN_REQUIRED"),
        "CustomerCommunicationAgent": (draft, ""),
        "EvidenceComplianceAgent": ({
            "workflow_version": LABEL, "decision": "APPROVE",
            "compliance_summary": "All checks passed.",
            "human_review_required": True,
        }, "\nROUTE_DECISION::GRIDRESOLVE_APPROVED"),
        "EscalationCoordinatorAgent": ({
            "workflow_version": LABEL,
            "evidence_ledger": [{"evidence_id": "EVID-READ-A"}],
            "policy_ledger": [{"policy_id": "POL-MTR-003"}],
            "routing": {"route_to": "Billing Supervisor"},
            "customer_safe_interim_message": "We found no fault so far.",
        }, ""),
        "CaseAuditAgent": ({
            "workflow_version": LABEL,
            "evidence_ids": [e["evidence_id"] for e in ledger],
            "claim_ids": ["CLM-1"],
            "policy_ids": ["POL-HB-001", "POL-MTR-003"]}, ""),
    }


def good_analysis() -> dict:
    return {"route": {"route": "APPROVED_AND_RELEASED", "gate_evaluated": True,
                      "case_follow_up": "HANDED_TO_HUMAN"},
            "audit": {"accurate": True, "findings": []}}


RELEASE_AFTER = "EvidenceComplianceAgent"


def message(role: str, text: str, agent: str | None = None,
            version: str | None = None) -> dict:
    item: dict = {"type": "message", "role": role,
                  "content": [{"type": "text", "text": text}]}
    if agent:
        item["created_by"] = {"agent": {"name": agent, "version": version},
                              "response_id": "resp_" + agent}
    return item


def make_run(outputs: dict | None = None, released: str | None = "AUTO",
             analysis: dict | None = None,
             platform_version: str = "10") -> run_record.RunRecord:
    from runner.workflow_map import compose_customer_message
    outputs = good_outputs() if outputs is None else outputs
    if released == "AUTO":
        released = compose_customer_message(
            outputs["CustomerCommunicationAgent"][0])
    items = [message("user", CASE_TEXT)]
    for agent, (data, tail) in outputs.items():
        items.append(message("user", "WORKFLOW STEP: " + agent))
        text = data if isinstance(data, str) else json.dumps(data) + tail
        items.append(message("assistant", text, agent, "1"))
        items.append({"type": "workflow_action", "created_by": {
            "agent": {"name": WORKFLOW, "version": platform_version}}})
        if agent == RELEASE_AFTER and released is not None:
            items.append(message("assistant", released, WORKFLOW,
                                 platform_version))
    return run_record.build_run("TEST-RUN", WORKFLOW, "10", items,
                                good_analysis() if analysis is None else analysis)


def changed(agent: str, **fields: object) -> dict:
    outputs = copy.deepcopy(good_outputs())
    data, tail = outputs[agent]
    outputs[agent] = ({**data, **fields}, tail)
    return outputs


def verdict(check_fn, run: run_record.RunRecord) -> str:
    return check_fn(run, REFERENCE).verdict


# ------------------------------------------------------------- run record

good = make_run()
check("run record keeps nine agent outputs", len(good.outputs) == 9)
check("run record finds the released text",
      good.released is not None and good.released.startswith("You asked us"))
check("run record parses the case", good.case.get("case_id") == "SYN-CASE-4003")
check("run record splits the tail token",
      good.output("ResolutionPlannerAgent").tail.strip()
      == "CASE_FOLLOWUP::HUMAN_REQUIRED")
check("run record keeps the invocation message",
      good.output("UsageAnomalyAgent").invocation
      == "WORKFLOW STEP: UsageAnomalyAgent")
try:
    good.run_id = "x"  # type: ignore[misc]
    check("run record rejects mutation", False)
except Exception:
    check("run record rejects mutation", True)
text_only = make_run({**good_outputs(), "AccountEvidenceAgent": ("I will ask.", "")})
check("plain text output has no data",
      text_only.output("AccountEvidenceAgent").data is None)

# ------------------------------------------------- every check on good run

all_good = dc.run_all(good, REFERENCE)
check("twelve or more checks defined", len(all_good) >= 12, str(len(all_good)))
check("check ids are unique",
      len({r.check_id for r in all_good}) == len(all_good))
for result in all_good:
    check("good run passes %s" % result.check_id, result.verdict == "PASS",
          result.detail)
    check("%s carries the run id" % result.check_id, result.run == "TEST-RUN")
    check("%s has a detail" % result.check_id, bool(result.detail))

# ------------------------------------------------------ billing arithmetic

bad = changed("AccountEvidenceAgent", billing_comparison=[
    {"formula": "870 * 0.22 + 12.00", "result": "210.40"}])
check("wrong arithmetic result fails",
      verdict(dc.check_billing_arithmetic, make_run(bad)) == "FAIL")
bad = changed("AccountEvidenceAgent", billing_comparison=[
    {"formula": "640 * 0.22 + 12.00", "result": "152.80"}])
check("a bill that was not reproduced fails",
      verdict(dc.check_billing_arithmetic, make_run(bad)) == "FAIL")
check("no evidence output fails billing arithmetic",
      verdict(dc.check_billing_arithmetic, text_only) == "FAIL")
bad = changed("CustomerCommunicationAgent",
              what_we_found="Your bill should have been $99.00.")
check("invented dollar figure in the message fails",
      verdict(dc.check_billing_arithmetic, make_run(bad)) == "FAIL")
check("formula evaluator refuses names",
      dc.evaluate_arithmetic("__import__('os')") is None)
check("formula evaluator computes decimals exactly",
      str(dc.evaluate_arithmetic("870 * 0.22 + 12.00")) in ("203.40", "203.4000"))

# ---------------------------------------------------- meter reconciliation

bad = changed("AccountEvidenceAgent", evidence_ledger=[
    e for e in good_outputs()["AccountEvidenceAgent"][0]["evidence_ledger"]
    if e["evidence_id"] != "EVID-READ-B"])
check("missing register read fails reconciliation",
      verdict(dc.check_meter_reconciliation, make_run(bad)) == "FAIL")
bad = changed("CustomerCommunicationAgent",
              what_we_found="The register moved 910 kWh.")
check("kWh figure not in the records fails reconciliation",
      verdict(dc.check_meter_reconciliation, make_run(bad)) == "FAIL")
check("no ledger fails reconciliation",
      verdict(dc.check_meter_reconciliation, text_only) == "FAIL")

# ------------------------------------------------------------ evidence ids

outputs = copy.deepcopy(good_outputs())
outputs["ResolutionPlannerAgent"][0]["claim_ledger"][0]["evidence_ids"].append(
    "EVID-INVENTED-99")
check("evidence id not in the ledger fails",
      verdict(dc.check_evidence_ids, make_run(outputs)) == "FAIL")
ledger = copy.deepcopy(
    good_outputs()["AccountEvidenceAgent"][0]["evidence_ledger"])
ledger[2] = {**ledger[2], "value": "900"}
check("ledger value that differs from the case fails",
      verdict(dc.check_evidence_ids,
              make_run(changed("AccountEvidenceAgent", evidence_ledger=ledger)))
      == "FAIL")
ledger[2] = {**ledger[2], "value": "870", "source_record_id": "SYN-BILL-9999"}
check("ledger record that is not in the case fails",
      verdict(dc.check_evidence_ids,
              make_run(changed("AccountEvidenceAgent", evidence_ledger=ledger)))
      == "FAIL")
check("no ledger fails evidence ids",
      verdict(dc.check_evidence_ids, text_only) == "FAIL")

# -------------------------------------------------------------- policy ids

bad = changed("PolicyKnowledgeAgent", policy_ledger=[{"policy_id": "POL-FAKE-999"}])
check("policy id outside the governed set fails",
      verdict(dc.check_policy_ids, make_run(bad)) == "FAIL")
bad = changed("PolicyKnowledgeAgent", policy_ledger=[])
bad["ResolutionPlannerAgent"][0]["claim_ledger"][0]["policy_ids"] = []
bad["CustomerCommunicationAgent"][0]["internal_policy_ids"] = []
bad["EscalationCoordinatorAgent"][0]["policy_ledger"] = []
bad["CaseAuditAgent"][0]["policy_ids"] = []
check("a run that cites no policy at all fails",
      verdict(dc.check_policy_ids, make_run(bad)) == "FAIL")

# ------------------------------------------------------ meter fault claims

for sentence in ("We confirmed the meter is faulty.",
                 "The meter was malfunctioning in July.",
                 "A meter fault caused the higher bill.",
                 "We will replace your meter next week."):
    bad = changed("CustomerCommunicationAgent", what_we_found=sentence)
    check("meter claim flagged: %s" % sentence,
          verdict(dc.check_meter_failure_claims, make_run(bad)) == "FAIL")
for sentence in ("You asked us to confirm whether the meter is broken.",
                 "We did not find evidence that the meter is faulty.",
                 "If an inspection shows a confirmed meter fault, a supervisor "
                 "will review it."):
    ok = changed("CustomerCommunicationAgent", what_we_found=sentence)
    check("meter wording allowed: %s" % sentence[:40],
          verdict(dc.check_meter_failure_claims, make_run(ok)) == "PASS")

# --------------------------------------------------------- credit promises

for sentence in ("We will apply a credit to your next bill.",
                 "You will receive a refund within 10 days.",
                 "A credit of $50 has been approved."):
    bad = changed("CustomerCommunicationAgent", what_happens_next=sentence)
    check("credit promise flagged: %s" % sentence,
          verdict(dc.check_credit_promises, make_run(bad)) == "FAIL")
ok = changed("CustomerCommunicationAgent", what_happens_next=(
    "A supervisor must approve any credit before it is applied. "
    "We have not applied any credits."))
check("conditional credit wording allowed",
      verdict(dc.check_credit_promises, make_run(ok)) == "PASS")
bad = changed("ResolutionPlannerAgent", resolution_status="RESOLVED",
              customer_adjustment={"proposed_adjustment_usd": 50.6})
check("adjustment proposed without human review fails",
      verdict(dc.check_credit_promises, make_run(bad)) == "FAIL")

# -------------------------------------------------- compliance consistency

outputs = good_outputs()
outputs["EvidenceComplianceAgent"] = ("ROUTE_DECISION::GRIDRESOLVE_ESCALATE", "")
escalated = {"route": {"route": "ESCALATED_TO_HUMAN", "gate_evaluated": True,
                       "case_follow_up": "HANDED_TO_HUMAN"},
             "audit": {"accurate": True, "findings": []}}
check("token with no decision object fails consistency",
      verdict(dc.check_compliance_consistency,
              make_run(outputs, released=None, analysis=escalated)) == "FAIL")
check("approve decision with an escalated route fails",
      verdict(dc.check_compliance_consistency,
              make_run(released=None, analysis=escalated)) == "FAIL")
outputs = good_outputs()
outputs["EvidenceComplianceAgent"] = (
    {"workflow_version": LABEL, "decision": "REJECT",
     "compliance_summary": "Unsupported claim CLM-1."},
    "\nROUTE_DECISION::GRIDRESOLVE_ESCALATE")
check("reject, escalate token and escalated route are consistent",
      verdict(dc.check_compliance_consistency,
              make_run(outputs, released=None, analysis=escalated)) == "PASS")
ungated = copy.deepcopy(good_analysis())
ungated["route"]["gate_evaluated"] = False
check("a release the gate never evaluated fails",
      verdict(dc.check_compliance_consistency, make_run(analysis=ungated))
      == "FAIL")
bad = changed("EvidenceComplianceAgent", compliance_summary="")
check("a decision with no reasons fails",
      verdict(dc.check_compliance_consistency, make_run(bad)) == "FAIL")

# ------------------------------------------------------- human follow-up

lost = copy.deepcopy(good_analysis())
lost["route"]["case_follow_up"] = "NOT_OBSERVED"
check("human follow-up that never happened fails",
      verdict(dc.check_human_follow_up, make_run(analysis=lost)) == "FAIL")
outputs = good_outputs()
del outputs["EscalationCoordinatorAgent"]
check("no escalation agent when a human is needed fails",
      verdict(dc.check_human_follow_up, make_run(outputs)) == "FAIL")
outputs = changed("ResolutionPlannerAgent", resolution_status="RESOLVED")
outputs["ResolutionPlannerAgent"] = (outputs["ResolutionPlannerAgent"][0],
                                     "\nCASE_FOLLOWUP::NONE_REQUIRED")
outputs["EvidenceComplianceAgent"][0]["human_review_required"] = False
check("no agent asked for a human: not applicable",
      verdict(dc.check_human_follow_up, make_run(outputs)) == "NOT_APPLICABLE")

# ------------------------------------------------------------------ audit

wrong = copy.deepcopy(good_analysis())
wrong["audit"] = {"accurate": False, "findings": ["version wrong"]}
check("inaccurate audit fails",
      verdict(dc.check_audit_accuracy, make_run(analysis=wrong)) == "FAIL")

# ------------------------------------------------- message completeness

bad = changed("CustomerCommunicationAgent", why_bill_changed="  ")
check("blank customer field fails completeness",
      verdict(dc.check_message_completeness, make_run(bad)) == "FAIL")
check("released text that is not the composed draft fails",
      verdict(dc.check_message_completeness,
              make_run(released="=Last(Local.VarCustomerDraft).Text")) == "FAIL")
check("withheld message with a complete draft passes",
      verdict(dc.check_message_completeness,
              make_run(released=None, analysis=escalated)) == "PASS")

# --------------------------------------------------------- case isolation

bad = changed("UsageAnomalyAgent", note="Compare with SYN-ACCT-0007.")
check("another account id fails isolation",
      verdict(dc.check_case_isolation, make_run(bad)) == "FAIL")
bad = changed("UsageAnomalyAgent", note="See SYN-CASE-4001.")
check("another case id fails isolation",
      verdict(dc.check_case_isolation, make_run(bad)) == "FAIL")

# ------------------------------------------------------ workflow version

bad = changed("UsageAnomalyAgent", workflow_version=WORKFLOW + " v9")
check("stale version label fails consistency",
      verdict(dc.check_workflow_version, make_run(bad)) == "FAIL")
check("platform version that differs from the request fails",
      verdict(dc.check_workflow_version, make_run(platform_version="9"))
      == "FAIL")

# ------------------------------------------------------------ root cause

bad = changed("ResolutionPlannerAgent",
              root_cause_classification="USAGE_SUPPORTED")
check("root cause that differs from the prepared ground truth fails",
      verdict(dc.check_root_cause, make_run(bad)) == "FAIL")

# -------------------------------------------------------------- provenance

CATALOG_IDS = frozenset({"POL-HB-001", "POL-BILL-002", "POL-MTR-003"})
chain = provenance.trace(good, CATALOG_IDS)
check("provenance walks eight links", len(chain) == 8, str(len(chain)))
for link in chain:
    check("good run resolves link %s" % link.link, link.status == "RESOLVED",
          link.detail)


def link_status(run: run_record.RunRecord, name: str) -> str:
    return {link.link: link.status for link in provenance.trace(run, CATALOG_IDS)}[name]


outputs = copy.deepcopy(good_outputs())
outputs["ResolutionPlannerAgent"][0]["claim_ledger"][0]["evidence_ids"] = [
    "EVID-GONE"]
broken = provenance.trace(make_run(outputs), CATALOG_IDS)
claim_link = [link for link in broken if link.link == "claim_ledger"][0]
check("claim with an unknown evidence id breaks the claim link",
      claim_link.status == "BROKEN")
check("broken link names the identifier",
      "EVID-GONE" in claim_link.identifiers)
check("no ledger breaks the evidence link",
      link_status(text_only, "evidence") == "BROKEN")
bad = changed("PolicyKnowledgeAgent", policy_ledger=[{"policy_id": "POL-FAKE-999"}])
check("policy outside the catalog breaks the policy link",
      link_status(make_run(bad), "policy") == "BROKEN")
bad = changed("CustomerCommunicationAgent", internal_claim_ids=["CLM-404"])
check("draft citing an unknown claim breaks the customer response link",
      link_status(make_run(bad), "customer_response") == "BROKEN")
check("released text that is not the draft breaks the customer response link",
      link_status(make_run(released="something else"), "customer_response")
      == "BROKEN")
check("withheld message is reported as not taken, not resolved",
      link_status(make_run(released=None, analysis=escalated),
                  "customer_response") == "NOT_TAKEN")
bad = changed("CaseAuditAgent", claim_ids=["CLM-1", "CLM-2"])
check("audit listing a claim that does not exist breaks the audit link",
      link_status(make_run(bad), "audit") == "BROKEN")
bad = changed("EscalationCoordinatorAgent", routing={})
check("handoff without a reviewer breaks the human review link",
      link_status(make_run(bad), "human_review_package") == "BROKEN")

# ------------------------------------------------------------ real runs

RUN_DIRS = list(run_checks.HISTORICAL_RUNS)
check("the three genuine submission runs are on disk and pinned for dataset D",
      all(os.path.isdir(os.path.join(EVIDENCE, d)) for d in RUN_DIRS) and len(RUN_DIRS) == 3,
      str(RUN_DIRS))
real = [run_record.load_run(os.path.join(EVIDENCE, d)) for d in RUN_DIRS]
check("real runs report versions 6, 9, 10",
      [r.workflow_version for r in real] == ["6", "9", "10"])
check("final run has nine agent outputs", len(real[2].outputs) == 9)
check("final run released 2592 characters",
      real[2].released is not None and len(real[2].released) == 2592)
check("run 2 released nothing", real[1].released is None)
check("final run outputs carry invocation messages",
      all(o.invocation for o in real[2].outputs))
check("earlier runs have no invocation messages",
      not any(o.invocation for o in real[0].outputs + real[1].outputs))

# ------------------------------------------------------------- datasets


def read_jsonl(name: str) -> list[dict]:
    rows = []
    with open(os.path.join(DATASETS, name), encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as error:
                    check("%s line %d is JSON" % (name, number), False, str(error))
    return rows


prepared = read_jsonl("prepared_cases.jsonl")
probes = read_jsonl("adversarial_probes.jsonl")
captured = read_jsonl("captured_foundry_interactions.jsonl")
truth = read_jsonl("ground_truth.jsonl")

check("A has 30 prepared cases", len(prepared) == 30, str(len(prepared)))
check("A2 has 16 probes", len(probes) == 16, str(len(probes)))
check("C has 16 ground truth rows", len(truth) == 16, str(len(truth)))
check("B has one row per agent output",
      len(captured) == sum(len(r.outputs) for r in real), str(len(captured)))
for name, rows in (("A", prepared), ("A2", probes)):
    check("%s rows have query, context, ground_truth" % name,
          all({"query", "context", "ground_truth"} <= set(r) for r in rows))
    check("%s rows have no response column" % name,
          not any("response" in r for r in rows))
    check("%s rows are marked not executed" % name,
          all(r["status"] == "PREPARED_NOT_EXECUTED" for r in rows))
    check("%s queries are not empty" % name,
          all(isinstance(r["query"], str) and r["query"].strip() for r in rows))
check("A eval ids are unique", len({r["eval_id"] for r in prepared}) == 30)
check("B rows have query, response, context",
      all({"query", "response", "context"} <= set(r) for r in captured))
check("B rows carry run, workflow and agent versions",
      all({"run_id", "workflow_version", "agent_name", "agent_version",
           "evidence_class"} <= set(r) for r in captured))
check("B rows are labelled as actual Foundry execution",
      all(r["evidence_class"] == "ACTUAL_FOUNDRY_EXECUTION" for r in captured))
check("B run ids are the three evidence folders",
      {r["run_id"] for r in captured} == set(RUN_DIRS))
by_key = {(r["run_id"], r["agent_name"]): r for r in captured}
check("B responses are verbatim",
      all(by_key[(run.run_id, o.agent)]["response"] == o.text
          for run in real for o in run.outputs))
check("B query is the invocation message where one was recorded",
      all(by_key[(real[2].run_id, o.agent)]["query"] == o.invocation
          for o in real[2].outputs))
check("B never invents a query",
      all(by_key[(run.run_id, o.agent)]["query"] == ""
          and by_key[(run.run_id, o.agent)]["query_source"] == "NONE_RECORDED"
          for run in real[:2] for o in run.outputs))
check("B agent versions are the platform's",
      by_key[(real[2].run_id, "AccountEvidenceAgent")]["agent_version"] == "9")
check("C rows have case id and ground truth",
      all({"case_id", "ground_truth"} <= set(r) for r in truth))
row_4003 = [r for r in truth if r["case_id"] == "SYN-CASE-4003"][0]
facts = row_4003["ground_truth"]["computed_facts"]
check("C computes the register delta", facts["register_delta_kwh"] == "870")
check("C computes both bills",
      facts["bill_amounts_recomputed_usd"] == {"SYN-BILL-0003-06": "152.80",
                                               "SYN-BILL-0003-07": "203.40"})
check("A and B share no rows",
      not ({json.dumps(r, sort_keys=True) for r in prepared}
           & {json.dumps(r, sort_keys=True) for r in captured}))

with open(os.path.join(DATASETS, "deterministic_results.json"),
          encoding="utf-8") as handle:
    results = json.load(handle)
check("D says it is deterministic and local",
      results["evaluation_type"] == "DETERMINISTIC_LOCAL_CHECKS"
      and results["model_based"] is False
      and results["foundry_evaluation_job"] is False)
check("D covers three runs", len(results["runs"]) == 3)
check("D matches a fresh computation",
      results["runs"] == run_checks.compute(EVIDENCE)["runs"])
check("D verdicts are from the allowed set",
      all(c["verdict"] in ("PASS", "FAIL", "NOT_APPLICABLE")
          for run in results["runs"] for c in run["checks"]))
check("D includes provenance for each run",
      all(len(run["provenance"]) == 8 for run in results["runs"]))

with open(os.path.join(DATASETS, "model_based_evaluations_NOT_EXECUTED.md"),
          encoding="utf-8") as handle:
    not_executed = handle.read()
check("E says not executed", "NOT EXECUTED" in not_executed)
check("E does not price the evaluations", "not priced here" in not_executed)
check("E reports no scores",
      "score:" not in not_executed.lower() and "passed" not in not_executed.lower())

# -------------------------------------------------------- policy catalog

with open(os.path.join(EVAL, "policy", "policy_catalog.json"),
          encoding="utf-8") as handle:
    catalog = json.load(handle)
with open(os.path.join(ROOT, "gridresolve_synthetic_pack.json"),
          encoding="utf-8") as handle:
    pack = json.load(handle)
records = {p["policy_id"]: p for p in catalog["policies"]}
check("catalog has every governed policy",
      set(records) == {p["policy_id"] for p in pack["policies"]})
for field in ("version", "effective_date", "effective_date_note", "source",
              "applicability", "human_authorization", "missing_evidence_handling",
              "definition_sha256"):
    check("catalog records have %s" % field,
          all(field in p for p in records.values()))
check("catalog does not invent effective dates",
      all(p["effective_date"] is None and p["effective_date_note"]
          for p in records.values()))
final_policy_ids = {
    p["policy_id"]
    for p in real[2].output("PolicyKnowledgeAgent").data["policy_ledger"]}
check("final run cites nine policies", len(final_policy_ids) == 9)
check("every policy cited in the final run resolves to a catalog record",
      final_policy_ids <= set(records), str(final_policy_ids - set(records)))

changed_catalog = copy.deepcopy(catalog)
for policy in changed_catalog["policies"]:
    if policy["policy_id"] == "POL-MTR-003":
        policy["human_authorization"] = "None"
changes = impact.diff_catalogs(catalog, changed_catalog)
check("catalog diff finds the changed policy",
      [c["policy_id"] for c in changes] == ["POL-MTR-003"], str(changes))
check("catalog diff names the changed field",
      "human_authorization" in changes[0]["changed_fields"])
check("identical catalogs have no changes",
      impact.diff_catalogs(catalog, catalog) == [])
hit = impact.impact_of(["POL-MTR-003"], [real[2]])
check("impact lists the final run's claims that cite the policy",
      {"CLM-0003-02", "CLM-0003-04"} <= set(hit[0]["claims"]), str(hit))
check("impact of an uncited policy is empty",
      impact.impact_of(["POL-COST-009"], [real[2]])[0]["claims"] == [])
check("catalog is unchanged by the diff",
      records["POL-MTR-003"]["human_authorization"] != "None")

# ------------------------------------------------------------ house rules

DASHES = (chr(0x2014), chr(0x2013))
EXEMPT = os.path.join("datasets", "captured_foundry_interactions.jsonl")
scanned = 0
for folder, _dirs, files in os.walk(EVAL):
    if "__pycache__" in folder:
        continue
    for name in files:
        path = os.path.join(folder, name)
        if path.endswith(EXEMPT) or name.endswith(".pyc"):
            continue
        with open(path, encoding="utf-8") as handle:
            body = handle.read()
        scanned += 1
        check("no em or en dash in %s" % os.path.relpath(path, EVAL),
              not any(d in body for d in DASHES))
with open(os.path.abspath(__file__), encoding="utf-8") as handle:
    check("no em or en dash in this test file",
          not any(d in handle.read() for d in DASHES))
check("scanned the package files", scanned >= 12, str(scanned))

with open(os.path.join(EVAL, "README.md"), encoding="utf-8") as handle:
    readme = handle.read()
check("README says these are not Foundry model-based evaluation results",
      "not Foundry model-based evaluation results" in readme)
check("README says the column mapping is chosen at evaluation creation",
      "column mapping" in readme)
check("README explains the verbatim dashes in dataset B", "verbatim" in readme)
for token in ("customer-resolution", "rg-satyam", "Bearer ", "eyJ"):
    check("no tenant identifier or token in the package: %s" % token,
          not any(token in open(os.path.join(folder, name),
                                encoding="utf-8").read()
                  for folder, _d, files in os.walk(EVAL)
                  if "__pycache__" not in folder
                  for name in files if not name.endswith(".pyc")))

# ----------------------------------------------------- evidence untouched

check("evidence folders are byte-identical after the tests",
      evidence_hashes() == HASHES_BEFORE)
check("evidence has files to compare", len(HASHES_BEFORE) >= 35,
      str(len(HASHES_BEFORE)))

print("RESULT: %d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
