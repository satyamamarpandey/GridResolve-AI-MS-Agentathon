"""OFFLINE FIXTURES. Not model output, not Foundry execution evidence.

No real run has produced an evidence ledger yet, so the healthy path of the local
acceptance harness needs one from somewhere. This builds it deterministically from
the supplied case records, field by field, with no model and no judgement: every
value is copied, and the two calculations are plain arithmetic on copied values.
Anything built here carries the marker OFFLINE_FIXTURE so it cannot be mistaken
for an agent's work.
"""
from __future__ import annotations

import json

MARKER = "OFFLINE_FIXTURE"


def evidence_ledger(case: dict) -> dict:
    """An AccountEvidenceAgent output that satisfies evidence_ledger.schema.json."""
    records = case["synthetic_account_records"]
    version = case["dataset_version"]
    ledger: list[dict] = []

    def add(source_type: str, record_id: str, period: str, field: str, value: object) -> str:
        evidence_id = "EV-%s-%02d" % (MARKER, len(ledger) + 1)
        ledger.append({"evidence_id": evidence_id, "source_type": source_type,
                       "source_record_id": record_id, "period": period, "field": field,
                       "value": str(value), "observation": "%s is %s." % (field, value),
                       "source_timestamp": period, "data_version": version})
        return evidence_id

    bills = {}
    for bill in records["billing_history"]:
        period = bill["period_start"][:7]
        bills[period] = {name: add("billing_history", bill["record_id"], period, name, bill[name])
                         for name in ("kwh_billed", "amount_usd", "read_type_end", "billing_days")}
    reads = [dict(read, evidence_id=add("meter_read", read["record_id"], read["read_date"],
                                        "register_kwh", read["register_kwh"]))
             for read in records["meter_reads"]]
    rates = [{"component": name, "value": str(value), "unit": "USD",
              "evidence_id": add("rate_component", name, "", name, value)}
             for name, value in records["rate_components"].items()]
    for diag in records["diagnostic_records"]:
        for name in ("result", "tamper_flag", "register_fault_flag"):
            add("diagnostic_record", diag["record_id"], diag["diagnostic_date"], name, diag[name])
    add("meter_event", "meter_event_note", "", "meter_event_note", records["meter_event_note"])

    first, last = reads[0], reads[-1]
    periods = sorted(bills)
    delta = last["register_kwh"] - first["register_kwh"]
    return {
        "case_id": case["case_id"], "workflow_version": case["workflow_version"],
        "case_state": "INVESTIGATING", "dataset_version": version,
        "evidence_ledger": ledger,
        "billing_comparison": [
            {"calculation": "register movement between the two reads",
             "formula": "%s - %s" % (last["register_kwh"], first["register_kwh"]),
             "result": "%s kWh" % delta, "evidence_ids": [first["evidence_id"], last["evidence_id"]]},
            {"calculation": "billed kWh, latest period against the one before",
             "formula": "kwh_billed(%s) against kwh_billed(%s)" % (periods[-1], periods[-2]),
             "result": "see the two cited entries",
             "evidence_ids": [bills[periods[-1]]["kwh_billed"], bills[periods[-2]]["kwh_billed"]]}],
        "meter_read_status": [{"source_record_id": read["record_id"], "read_date": read["read_date"],
                               "read_type": read["read_type"], "evidence_id": read["evidence_id"]}
                              for read in reads],
        "rate_components": rates,
        "observed_changes": [], "conflicts": [], "missing_fields": [],
        "evidence_quality": "HIGH", "data_freshness": MARKER,
        "evidence_summary": MARKER + ": copied from the supplied records, no conclusions drawn."}


def evidence_ledger_text(case: dict) -> str:
    return json.dumps(evidence_ledger(case), indent=2)
