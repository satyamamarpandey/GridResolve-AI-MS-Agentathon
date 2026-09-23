"""Run every deterministic check and the provenance trace over the genuine runs,
and write dataset D (datasets/deterministic_results.json).

No model, no network, no Azure call. The evidence folders are opened for
reading only. Runs 1 and 2 are expected to fail several checks. That is the
history, and the checks are not adjusted per run.

Run: python -m evaluation.run_checks

With --escalation it instead prints the escalation reason-code check for each
run and writes nothing, so dataset D stays exactly as frozen.

With --ground-truth 2.1 it judges the same three runs against the v2.1 pack
(gridresolve_synthetic_pack_v2_1.json, the 2026-09-23 adjudication, two
axes) with the claim-verdict check added, and writes
gridresolve_deterministic_results_v2_1.json at the repository root. Dataset D
is not read or written on that path. The file lives outside evaluation/ so the
frozen file count of tests/test_evaluation_package.py is unchanged.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

from evaluation import deterministic_checks as dc
from evaluation import provenance
from evaluation.run_record import load_all

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE = os.path.join(ROOT, "evidence", "runtime")
PACK_PATH = os.path.join(ROOT, "gridresolve_synthetic_pack.json")
CATALOG_PATH = os.path.join(ROOT, "evaluation", "policy", "policy_catalog.json")
RESULTS_PATH = os.path.join(ROOT, "evaluation", "datasets",
                            "deterministic_results.json")

PACK_V21_PATH = os.path.join(ROOT, "gridresolve_synthetic_pack_v2_1.json")
RESULTS_V21_PATH = os.path.join(ROOT,
                                "gridresolve_deterministic_results_v2_1.json")
GROUND_TRUTHS = {"2.0": (PACK_PATH, RESULTS_PATH, ()),
                 "2.1": (PACK_V21_PATH, RESULTS_V21_PATH,
                         dc.CLAIM_VERDICT_CHECKS)}


def reference_for(case_id: str, pack_path: str = PACK_PATH) -> dc.Reference:
    with open(pack_path, encoding="utf-8") as handle:
        pack = json.load(handle)
    matching = [c for c in pack["cases"] if c["case_id"] == case_id]
    case = matching[0] if matching else {}
    return dc.Reference(
        governed_policy_ids=frozenset(p["policy_id"] for p in pack["policies"]),
        expected_root_cause=str(case.get("expected_root_cause", "")),
        expected_claim_verdict=str(case.get("expected_claim_verdict", "")))


def compute(evidence_root: str = EVIDENCE, pack_path: str = PACK_PATH,
            extra_checks: tuple[dc.Check, ...] = ()) -> dict[str, Any]:
    catalog_ids = provenance.catalog_ids_from(CATALOG_PATH)
    with open(pack_path, encoding="utf-8") as handle:
        dataset_version = json.load(handle).get("dataset_version")
    runs = []
    for run in load_all(evidence_root):
        reference = reference_for(str(run.case.get("case_id")), pack_path)
        results = dc.run_all(run, reference) + dc.run_with(run, reference,
                                                           extra_checks)
        checks = [r.as_dict() for r in results]
        links = [link.as_dict() for link in provenance.trace(run, catalog_ids)]
        runs.append({
            "run_id": run.run_id,
            "workflow_version": run.workflow_version,
            "case_id": run.case.get("case_id"),
            "totals": {v: sum(1 for c in checks if c["verdict"] == v)
                       for v in (dc.PASS, dc.FAIL, dc.NOT_APPLICABLE)},
            "checks": checks,
            "provenance": links,
        })
    result = {
        "evaluation_type": "DETERMINISTIC_LOCAL_CHECKS",
        "model_based": False,
        "foundry_evaluation_job": False,
        "azure_calls": 0,
        "note": "Plain Python over captured evidence. These are not Foundry "
                "model-based evaluation results. One synthetic case, three "
                "runs. The same checks ran on every run, unadjusted.",
        "runs": runs,
    }
    if extra_checks or pack_path != PACK_PATH:
        # Only the v2.1 path carries these keys, so the v2.0 output stays
        # byte-identical to the frozen dataset D.
        result = {**result, "ground_truth": dataset_version,
                  "ground_truth_note": (
                      "Judged against the adjudicated two-axis labels of "
                      "2026-09-23. The historical result under GRIDRESOLVE-"
                      "SYNTH-2.0 is evaluation/datasets/deterministic_results"
                      ".json and is unchanged. See docs/ROOT_CAUSE_"
                      "ADJUDICATION.md.")}
    return result


def matrix(results: dict[str, Any]) -> str:
    runs = results["runs"]
    lines = ["%-40s %s" % ("check", "  ".join("v%-5s" % r["workflow_version"]
                                              for r in runs))]
    for index, first in enumerate(runs[0]["checks"]):
        lines.append("%-40s %s" % (first["check_id"], "  ".join(
            "%-6s" % {"NOT_APPLICABLE": "N/A"}.get(r["checks"][index]["verdict"],
                                                   r["checks"][index]["verdict"])
            for r in runs)))
    for index, first in enumerate(runs[0]["provenance"]):
        lines.append("%-40s %s" % ("link: " + first["link"], "  ".join(
            "%-6s" % r["provenance"][index]["status"][:6] for r in runs)))
    return "\n".join(lines)


def compute_escalation(evidence_root: str = EVIDENCE) -> tuple[dc.CheckResult, ...]:
    """The escalation reason-code check over every run. Writes nothing."""
    return tuple(
        result
        for run in load_all(evidence_root)
        for result in dc.run_escalation(
            run, reference_for(str(run.case.get("case_id")))))


def escalation_matrix(results: tuple[dc.CheckResult, ...]) -> str:
    return "\n".join("%-42s %-14s %s" % (r.run, r.verdict, r.detail)
                     for r in results)


def ground_truth_of(argv: tuple[str, ...]) -> str:
    """The --ground-truth value, 2.0 when absent. Anything else is refused."""
    args = list(argv)
    if "--ground-truth" not in args:
        return "2.0"
    index = args.index("--ground-truth")
    value = args[index + 1] if index + 1 < len(args) else ""
    if value not in GROUND_TRUTHS:
        raise SystemExit("--ground-truth must be one of %s, got %r"
                         % (", ".join(sorted(GROUND_TRUTHS)), value))
    return value


def main(argv: tuple[str, ...] = tuple(sys.argv[1:])) -> int:
    if "--escalation" in argv:
        sys.stdout.write(escalation_matrix(compute_escalation()) + "\n")
        return 0
    pack_path, results_path, extra = GROUND_TRUTHS[ground_truth_of(argv)]
    results = compute(pack_path=pack_path, extra_checks=extra)
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(results, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
    sys.stdout.write(matrix(results) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
