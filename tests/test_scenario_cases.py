"""
The two synthetic scenario cases prepared on 2026-09-23 for post-review hosted
validation: SYN-CASE-4001 (no-follow-up candidate) and SYN-CASE-4007
(conflicting-records escalation candidate). No model call, no Azure call, no
cost. Nothing here is Foundry execution evidence; neither case has been sent.

What is checked: each case loads through runner.case (the synthetic-only
validator, the field allowlist and the leak-marker scan), its money arithmetic
is internally consistent, its identifiers follow the SYN- convention, its
workflow label names v11, and its designed property holds (4001: register
movement equals billed kWh and no allegation or credit request in the text;
4007: register movement does NOT equal billed kWh, no diagnostic record, one
meter event). The canonical SYN-CASE-4003 file is read and must be unchanged.

Run: python tests/test_scenario_cases.py
"""
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from runner import case as case_mod  # noqa: E402

CANONICAL_4003_SHA256 = "baddf1f8febd366f40898998ccd27abd29dac452ec59c1bd45dfb5f722cb8520"

checks, fails = [], []


def check(name, cond, detail=""):
    (checks if cond else fails).append((name, detail))
    print("  [%s] %-70s %s" % ("PASS" if cond else "FAIL", name, detail))


def money_consistent(records):
    rate = records["rate_components"]
    return all(round(b["kwh_billed"] * rate["energy_charge_usd_per_kwh"]
                     + rate["fixed_charge_usd_per_period"], 2) == b["amount_usd"]
               for b in records["billing_history"])


def register_delta(records):
    reads = records["meter_reads"]
    return reads[-1]["register_kwh"] - reads[0]["register_kwh"]


def syn_ids(records):
    ids = [records["account_id"], records["meter_id"]]
    for group in ("billing_history", "meter_reads", "meter_events", "diagnostic_records"):
        ids += [r["record_id"] for r in records[group]]
    return ids


def common(case_id, expected_delta_matches):
    print("\n%s" % case_id)
    try:
        loaded = case_mod.load(case_id)
    except case_mod.CaseError as exc:
        check("%s loads through runner.case" % case_id, False, str(exc)[:100])
        return None
    check("%s loads through runner.case" % case_id, True)
    doc = loaded.document
    rec = doc["synthetic_account_records"]
    check("declares SYNTHETIC_ONLY", doc["data_classification"] == "SYNTHETIC_ONLY")
    check("workflow label names v11", doc["workflow_version"] == "GridResolveAIWorkflow v11",
          doc["workflow_version"])
    check("top-level fields are exactly the canonical allowlist",
          set(doc) == set(case_mod.ALLOWED_TOP_LEVEL))
    check("record fields are exactly the canonical allowlist",
          set(rec) == set(case_mod.ALLOWED_RECORD_FIELDS))
    check("no leak marker in the payload", case_mod.leak_markers(loaded.raw_text) == ())
    check("every identifier starts with SYN-", all(i.startswith("SYN-") for i in syn_ids(rec)))
    check("amount = kWh x energy charge + fixed charge on every bill", money_consistent(rec))
    check("two meter reads, both dated", len(rec["meter_reads"]) == 2
          and all(r["read_date"] for r in rec["meter_reads"]))
    delta = register_delta(rec)
    billed = rec["billing_history"][-1]["kwh_billed"]
    if expected_delta_matches:
        check("register movement equals the latest billed kWh (%d)" % billed,
              delta == billed, "delta %d" % delta)
    else:
        check("register movement does NOT equal the latest billed kWh (%d)" % billed,
              delta != billed, "delta %d" % delta)
    check("usage history ends with the latest billed kWh",
          rec["usage_history_kwh"][-1]["kwh"] == billed)
    check("file uses LF line endings and no BOM",
          b"\r" not in open(loaded.path, "rb").read()
          and not open(loaded.path, "rb").read().startswith(b"\xef\xbb\xbf"))
    print("  sha256 %s" % loaded.sha256)
    return doc


def main():
    print("Scenario case validation. No model call. No workflow execution. Azure cost: $0.00")

    print("\nCANONICAL CASE UNCHANGED")
    raw = open(os.path.join(ROOT, "submission", "SYN-CASE-4003_input.json"), "rb").read()
    check("SYN-CASE-4003_input.json sha256 is the final-run payload",
          hashlib.sha256(case_mod.canonical_text(raw).encode("utf-8")).hexdigest()
          == CANONICAL_4003_SHA256)
    check("the three cases are registered, 4003 among them",
          set(case_mod.available_cases()) == {"SYN-CASE-4001", "SYN-CASE-4003", "SYN-CASE-4007"},
          str(case_mod.available_cases()))

    doc = common("SYN-CASE-4001", expected_delta_matches=True)
    if doc:
        rec = doc["synthetic_account_records"]
        text = doc["customer_request"].casefold()
        check("customer makes no meter allegation",
              "meter" not in text and "broken" not in text and "faulty" not in text)
        check("customer asks for no credit, refund or adjustment",
              "credit" in text and "not asking for a credit" in text
              and "refund" not in text and "adjust" not in text)
        check("both reads are actual", all(r["read_type"] == "actual" for r in rec["meter_reads"]))
        check("diagnostic passed with no flags",
              len(rec["diagnostic_records"]) == 1
              and rec["diagnostic_records"][0]["result"] == "PASS"
              and rec["diagnostic_records"][0]["tamper_flag"] is False
              and rec["diagnostic_records"][0]["register_fault_flag"] is False)
        check("no meter events, no adjustments, no prior contacts",
              rec["meter_events"] == [] and rec["adjustments"] == [] and rec["prior_contacts"] == [])
        history = {h["period"]: h["kwh"] for h in rec["usage_history_kwh"]}
        check("usage history shows the same seasonal rise the year before",
              history["2025-07"] > history["2025-06"] * 1.3
              and history["2026-07"] > history["2026-06"] * 1.3)
        check("bills are 480 kWh at $110.80 and 720 kWh at $161.20",
              [(b["kwh_billed"], b["amount_usd"]) for b in rec["billing_history"]]
              == [(480, 110.80), (720, 161.20)])

    doc = common("SYN-CASE-4007", expected_delta_matches=False)
    if doc:
        rec = doc["synthetic_account_records"]
        check("no diagnostic record exists", rec["diagnostic_records"] == [])
        check("exactly one meter event, a communication loss",
              len(rec["meter_events"]) == 1 and rec["meter_events"][0]["type"] == "communication_loss")
        check("the bill claims an actual end read",
              rec["billing_history"][-1]["read_type_end"] == "actual")
        check("the conflict is material: billed 910 kWh against 650 kWh of register movement",
              rec["billing_history"][-1]["kwh_billed"] == 910 and register_delta(rec) == 650)
        check("the customer request states no expected outcome",
              "credit" not in doc["customer_request"].casefold())

    print("\nRESULT: %d passed, %d failed" % (len(checks), len(fails)))
    for name, detail in fails:
        print("  FAILED: %s %s" % (name, detail))
    print("No model call. No workflow execution. Azure cost: $0.00")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
