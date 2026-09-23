"""Tests for the escalation reason-code check (evaluation/deterministic_checks.py).

Offline. Hand-built runs only, plus a read-only pass over the three genuine
evidence folders. Kept in its own file so the frozen count of
tests/test_evaluation_package.py (198) is unchanged.

Run: python tests/test_escalation_reason_codes.py
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from evaluation import deterministic_checks as dc  # noqa: E402
from evaluation import run_record  # noqa: E402
from evaluation.run_checks import compute_escalation  # noqa: E402

WORKFLOW = "GridResolveAIWorkflow"
COMPLIANCE = "EvidenceComplianceAgent"
REFERENCE = dc.Reference(governed_policy_ids=frozenset(), expected_root_cause="")
ESCALATED = {"route": {"route": "ESCALATED_TO_HUMAN", "gate_evaluated": True}}
APPROVED = {"route": {"route": "APPROVED_AND_RELEASED", "gate_evaluated": True}}
ESCALATE_TAIL = "\nROUTE_DECISION::GRIDRESOLVE_ESCALATE"

RUN_1 = "20260920T205607Z_SYN-CASE-4003_80391bf2"
RUN_2 = "20260920T225342Z_SYN-CASE-4003_5e6f1114"
RUN_3 = "20260921T000142Z_SYN-CASE-4003_c2be2b51"

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        print("FAIL: %s %s" % (name, detail))


def message(role: str, text: str, agent: str | None = None) -> dict:
    item: dict = {"type": "message", "role": role,
                  "content": [{"type": "text", "text": text}]}
    if agent:
        item["created_by"] = {"agent": {"name": agent, "version": "1"},
                              "response_id": "resp_" + agent}
    return item


def make_run(compliance: dict | str | None,
             analysis: dict) -> run_record.RunRecord:
    items = [message("user", json.dumps({"case_id": "SYN-CASE-4003"}))]
    if compliance is not None:
        text = compliance if isinstance(compliance, str) \
            else json.dumps(compliance) + ESCALATE_TAIL
        items += [message("user", "WORKFLOW STEP: " + COMPLIANCE),
                  message("assistant", text, COMPLIANCE)]
    return run_record.build_run("TEST-RUN", WORKFLOW, "10", items, analysis)


def verdict(run: run_record.RunRecord) -> str:
    return dc.check_escalation_reason_codes(run, REFERENCE).verdict


def code(name: str, **cites: str) -> dict:
    return {"code": name, "cites": cites, "note": "test"}


reject = {"decision": "REJECT", "compliance_summary": "Unsupported claim."}

check("escalation with cited codes passes",
      verdict(make_run({**reject, "reason_codes": [
          code("UNSUPPORTED_CLAIM", claim_id="CLM-1"),
          code("POLICY_RULE_VIOLATED", policy_id="POL-MTR-003")]},
          ESCALATED)) == "PASS")
check("escalation with codes nested under escalation passes",
      verdict(make_run({**reject, "escalation": {"reason_codes": [
          code("EVIDENCE_GAP", evidence_id="EVID-BILL-0003-07-KWH")]}},
          ESCALATED)) == "PASS")
check("escalation with no codes fails",
      verdict(make_run(reject, ESCALATED)) == "FAIL")
check("escalation with an empty code list fails",
      verdict(make_run({**reject, "reason_codes": []}, ESCALATED)) == "FAIL")
check("bare token with no JSON object fails",
      verdict(make_run("ROUTE_DECISION::GRIDRESOLVE_ESCALATE", ESCALATED))
      == "FAIL")
check("compliance never ran but route escalated fails",
      verdict(make_run(None, ESCALATED)) == "FAIL")
check("code without a citation fails",
      verdict(make_run({**reject, "reason_codes": [
          {"code": "EVIDENCE_GAP", "cites": {}}]}, ESCALATED)) == "FAIL")
check("code with a blank citation fails",
      verdict(make_run({**reject, "reason_codes": [
          code("EVIDENCE_GAP", evidence_id="  ")]}, ESCALATED)) == "FAIL")
check("code citing an unknown key fails",
      verdict(make_run({**reject, "reason_codes": [
          {"code": "EVIDENCE_GAP", "cites": {"vibe": "bad"}}]}, ESCALATED))
      == "FAIL")
check("unknown code fails even with a citation",
      verdict(make_run({**reject, "reason_codes": [
          code("BECAUSE", claim_id="CLM-1")]}, ESCALATED)) == "FAIL")
check("one good and one bad code fails",
      verdict(make_run({**reject, "reason_codes": [
          code("UNSUPPORTED_CLAIM", claim_id="CLM-1"),
          {"code": "TOOL_FAILURE", "cites": {}}]}, ESCALATED)) == "FAIL")
check("a non-object entry fails",
      verdict(make_run({**reject, "reason_codes": ["EVIDENCE_GAP"]},
                       ESCALATED)) == "FAIL")
check("an approved release is not required to carry codes",
      verdict(make_run({"decision": "APPROVE", "compliance_summary": "ok"},
                       APPROVED)) == "NOT_APPLICABLE")
check("every enum value is accepted",
      all(verdict(make_run({**reject, "reason_codes": [
          code(name, rule="human authorization required")]}, ESCALATED))
          == "PASS" for name in sorted(dc.REASON_CODES)))
check("the schema enum and the check enum agree",
      set(json.load(open(os.path.join(ROOT, "gridresolve_case_state.schema.json"),
                         encoding="utf-8"))["properties"]["escalation"]
          ["properties"]["reason_codes"]["items"]["properties"]["code"]["enum"])
      == set(dc.REASON_CODES))
check("the check is not in the frozen ALL_CHECKS tuple",
      dc.check_escalation_reason_codes not in dc.ALL_CHECKS)
check("the check is in ESCALATION_CHECKS",
      dc.ESCALATION_CHECKS == (dc.check_escalation_reason_codes,))

# ------------------------------------------------- genuine evidence, read only
results = {r.run: r.verdict for r in compute_escalation()}
check("three genuine runs were examined", len(results) == 3, str(results))
check("run 2 (v9, escalated with no reasons) fails the new check",
      results.get(RUN_2) == "FAIL")
check("run 1 and run 3 (released) are not applicable",
      results.get(RUN_1) == "NOT_APPLICABLE"
      and results.get(RUN_3) == "NOT_APPLICABLE")

print("RESULT: %d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
