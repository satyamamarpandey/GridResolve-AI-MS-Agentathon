"""One row per hosted run, from the evidence folders. Read only.

    python scripts/hosted_run_metrics.py            # markdown table
    python scripts/hosted_run_metrics.py --json     # machine readable

Columns come from the runner's own files: the preflight (case, version), the
route analysis (branch, corrections), the final response usage block, the
usage report (elapsed, estimated cost at the carried price) and, when the
v2.1 results file lists the run, its deterministic verdicts. Nothing is
inferred from an agent's account of itself. Billed cost is not here; it comes
from Azure Cost Management, separately.
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE = os.path.join(ROOT, "evidence", "runtime")
V21 = os.path.join(ROOT, "gridresolve_deterministic_results_v2_1.json")
sys.path.insert(0, ROOT)
from evaluation.run_record import is_complete  # noqa: E402


def read(path, default=None):
    if default is not None and not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as handle:
        return json.load(handle) if path.endswith(".json") else handle.read()


def v21_verdicts():
    if not os.path.isfile(V21):
        return {}
    data = read(V21)
    out = {}
    for run in data.get("runs", []):
        checks = run.get("checks", [])
        out[run.get("run_id") or run.get("run")] = (
            sum(1 for c in checks if c.get("verdict") == "PASS"),
            sum(1 for c in checks if c.get("verdict") == "FAIL"),
            [c.get("check_id") for c in checks if c.get("verdict") == "FAIL"])
    return out


def rows():
    verdicts = v21_verdicts()
    for name in sorted(os.listdir(EVIDENCE)):
        run_dir = os.path.join(EVIDENCE, name)
        if not os.path.isdir(run_dir) or not is_complete(run_dir):
            continue
        pre = read(os.path.join(run_dir, "00_preflight.json"))
        ana = read(os.path.join(run_dir, "11_run_analysis.json"), default={})
        final = read(os.path.join(run_dir, "06_final_response.json"))
        report = read(os.path.join(run_dir, "10_usage_report.md"), default="")
        route = ana.get("route") or read(os.path.join(run_dir, "09_route.json"), default={})
        usage = final.get("usage") or {}
        elapsed = re.search(r"Elapsed \| ([0-9.]+)s", report)
        cost = re.search(r"\*\*Cost\*\* \| \*\*\$([0-9.]+)\*\*", report)
        comp = ana.get("compliance") or {}
        v = verdicts.get(name)
        yield {
            "run": name,
            "case": pre.get("case_id"),
            "workflow": "v%s" % pre.get("workflow_version"),
            "route": route.get("route"),
            "follow_up": route.get("case_follow_up"),
            "corrections": route.get("correction_attempts"),
            "rejections": route.get("rejections_observed"),
            "compliance_token": comp.get("token"),
            "agents": len(ana.get("participation") or []),
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "elapsed_s": float(elapsed.group(1)) if elapsed else None,
            "est_cost_usd": float(cost.group(1)) if cost else None,
            "v21_pass": v[0] if v else None,
            "v21_fail": v[1] if v else None,
            "v21_failed_checks": v[2] if v else None,
        }


def main(argv):
    data = list(rows())
    if "--json" in argv:
        print(json.dumps(data, indent=1))
        return 0
    cols = ("run", "case", "workflow", "route", "follow_up", "corrections",
            "agents", "input_tokens", "output_tokens", "elapsed_s",
            "est_cost_usd", "v21_pass", "v21_fail")
    print("| " + " | ".join(cols) + " |")
    print("|" + " --- |" * len(cols))
    for r in data:
        print("| " + " | ".join(str(r[c]) for c in cols) + " |")
    tot_in = sum(r["input_tokens"] or 0 for r in data)
    tot_out = sum(r["output_tokens"] or 0 for r in data)
    tot_cost = sum(r["est_cost_usd"] or 0 for r in data)
    print("\nruns %d, input %d, output %d, estimated USD %.4f" % (len(data), tot_in, tot_out, tot_cost))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
