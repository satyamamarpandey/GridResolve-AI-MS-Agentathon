"""Build the evaluation datasets from files already in the repository.

  A   prepared_cases.jsonl                 30 prepared cases, never executed
  A2  adversarial_probes.jsonl             16 prepared probes, never executed
  B   captured_foundry_interactions.jsonl  one row per agent output per real run
  C   ground_truth.jsonl                   expected outcome per synthetic case

D (deterministic_results.json) is written by run_checks.py. E is a hand-written
note, model_based_evaluations_NOT_EXECUTED.md.

Nothing is sent anywhere. No model, no network. The source packs and the
evidence folders are opened for reading only. Rows in B are verbatim.

Run: python -m evaluation.build_datasets
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Iterable, Mapping

from evaluation import deterministic_checks as dc
from evaluation.run_record import RunRecord, load_all

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASETS = os.path.join(ROOT, "evaluation", "datasets")
SUITE_PATH = os.path.join(ROOT, "gridresolve_evaluation_suite.jsonl")
PROBES_PATH = os.path.join(ROOT, "gridresolve_red_team_pack.jsonl")
PACK_PATH = os.path.join(ROOT, "gridresolve_synthetic_pack.json")
CASE_INPUT_PATH = os.path.join(ROOT, "submission", "SYN-CASE-4003_input.json")
EVIDENCE = os.path.join(ROOT, "evidence", "runtime")

PREPARED = "PREPARED_NOT_EXECUTED"
ACTUAL = "ACTUAL_FOUNDRY_EXECUTION"
NO_QUERY = "NONE_RECORDED"


def read_jsonl(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    return [r for r in rows if "_meta" not in r]


def read_json(path: str) -> Any:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_jsonl(name: str, rows: Iterable[Mapping[str, Any]]) -> int:
    os.makedirs(DATASETS, exist_ok=True)
    count = 0
    with open(os.path.join(DATASETS, name), "w", encoding="utf-8",
              newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def prepared_case_rows(suite: list[dict], pack: Mapping[str, Any]) -> list[dict]:
    cases = {c["case_id"]: c for c in pack["cases"]}
    rows = []
    for item in suite:
        case = cases.get(item["case_id"], {})
        root_cause = item.get("expected_root_cause", case.get("expected_root_cause"))
        route = item.get("expected_route", case.get("expected_route"))
        rows.append({
            "query": item["scenario"],
            "context": json.dumps({
                "case_id": item["case_id"],
                "case_scenario": case.get("scenario"),
                "required_evidence": case.get("required_evidence"),
                "dataset_version": pack["dataset_version"],
                "policy_version": pack["policy_version"]}),
            "ground_truth": "Expected root cause: %s. Expected route: %s. "
                            "Assertions: %s." % (root_cause, route,
                                                 "; ".join(item["assertions"])),
            "eval_id": item["eval_id"],
            "case_id": item["case_id"],
            "category": item["category"],
            "expected_root_cause": root_cause,
            "expected_route": route,
            "assertions": item["assertions"],
            "intended_evaluators": item["evaluators"],
            "status": PREPARED,
            "source": os.path.basename(SUITE_PATH),
        })
    return rows


def probe_rows(probes: list[dict]) -> list[dict]:
    return [{
        "query": p["synthetic_probe"],
        "context": json.dumps({"attack_class": p["attack_class"],
                               "data_classification": "SYNTHETIC_ONLY"}),
        "ground_truth": "Expected behaviour: %s. Fails if: %s."
                        % ("; ".join(p["expected_behavior"]), p["fail_condition"]),
        "attack_id": p["attack_id"],
        "attack_class": p["attack_class"],
        "expected_behavior": p["expected_behavior"],
        "fail_condition": p["fail_condition"],
        "status": PREPARED,
        "source": os.path.basename(PROBES_PATH),
    } for p in probes]


def captured_rows(runs: Iterable[RunRecord]) -> list[dict]:
    rows = []
    for run in runs:
        for position, output in enumerate(run.outputs, 1):
            rows.append({
                "query": output.invocation or "",
                "response": output.text,
                "context": run.case_text,
                "query_source": "PLATFORM_CONVERSATION_ITEM"
                if output.invocation else NO_QUERY,
                "run_id": run.run_id,
                "workflow_name": run.workflow_name,
                "workflow_version": run.workflow_version,
                "agent_name": output.agent,
                "agent_version": output.version,
                "agent_version_source": "PLATFORM_CREATED_BY_METADATA",
                "position_in_run": position,
                "response_id": output.response_id,
                "response_is_json": output.data is not None,
                "case_id": run.case.get("case_id"),
                "evidence_class": ACTUAL,
                "source": "evidence/runtime/%s/07_conversation_items.json"
                          % run.run_id,
            })
    return rows


def computed_facts(case: Mapping[str, Any]) -> dict:
    """Facts computed in Python from the case input. No model is involved."""
    records = case["synthetic_account_records"]
    delta = dc.register_delta(case)
    last_bill = sorted(records["billing_history"],
                       key=lambda b: b["period_end"])[-1]
    return {
        "bill_amounts_recomputed_usd": {
            k: "%.2f" % v for k, v in dc.recomputed_bills(case).items()},
        "bill_amounts_on_record_usd": {
            b["record_id"]: "%.2f" % b["amount_usd"]
            for b in records["billing_history"]},
        "register_delta_kwh": str(delta),
        "latest_billed_kwh": str(last_bill["kwh_billed"]),
        "register_delta_equals_billed_kwh":
            delta == dc.to_decimal(last_bill["kwh_billed"]),
        "all_reads_actual": all(r["read_type"] == "actual"
                                for r in records["meter_reads"]),
        "diagnostic_results": [d["result"] for d in records["diagnostic_records"]],
        "meter_events_recorded": len(records["meter_events"]),
        "prior_adjustments": len(records["adjustments"]),
    }


def ground_truth_rows(pack: Mapping[str, Any], case_input: Mapping[str, Any]
                      ) -> list[dict]:
    rows = []
    for case in pack["cases"]:
        truth: dict[str, Any] = {
            "expected_root_cause": case["expected_root_cause"],
            "expected_route": case["expected_route"],
            "required_evidence": case["required_evidence"],
        }
        has_input = case["case_id"] == case_input["case_id"]
        if has_input:
            truth = {**truth, "computed_facts": computed_facts(case_input)}
        rows.append({
            "case_id": case["case_id"],
            "scenario": case["scenario"],
            "ground_truth": truth,
            "full_case_input_available": has_input,
            "source": os.path.basename(PACK_PATH),
            "dataset_version": pack["dataset_version"],
        })
    return rows


def main() -> int:
    pack = read_json(PACK_PATH)
    written = {
        "prepared_cases.jsonl": write_jsonl(
            "prepared_cases.jsonl",
            prepared_case_rows(read_jsonl(SUITE_PATH), pack)),
        "adversarial_probes.jsonl": write_jsonl(
            "adversarial_probes.jsonl", probe_rows(read_jsonl(PROBES_PATH))),
        "captured_foundry_interactions.jsonl": write_jsonl(
            "captured_foundry_interactions.jsonl",
            captured_rows(load_all(EVIDENCE))),
        "ground_truth.jsonl": write_jsonl(
            "ground_truth.jsonl",
            ground_truth_rows(pack, read_json(CASE_INPUT_PATH))),
    }
    for name, count in written.items():
        sys.stdout.write("%-40s %d rows\n" % (name, count))
    return 0


if __name__ == "__main__":
    sys.exit(main())
