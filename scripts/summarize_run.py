"""Print the platform-observed facts of one hosted run folder, read only.

    python scripts/summarize_run.py evidence/runtime/<run dir>

Everything printed is read from the evidence files the runner wrote. Nothing
is inferred from an agent's own account of the run except where labelled
"model-produced". No network, no model call.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from runner import analysis  # noqa: E402


def load(run_dir: str, name: str):
    path = os.path.join(run_dir, name)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as handle:
        if name.endswith(".jsonl"):
            return [json.loads(l) for l in handle if l.strip()]
        if name.endswith(".json"):
            return json.load(handle)
        return handle.read()


def main(run_dir: str) -> int:
    pre = load(run_dir, "00_preflight.json") or {}
    ana = load(run_dir, "11_run_analysis.json") or {}
    usage = load(run_dir, "06_final_response.json") or {}
    items = analysis.items_of(load(run_dir, "07_conversation_items.json") or [])
    actions = load(run_dir, "04_workflow_actions.json") or []
    print("run dir          ", os.path.basename(run_dir))
    print("case, sha256     ", pre.get("case_id"), pre.get("case_sha256"))
    print("workflow version ", pre.get("workflow_version"))
    print("final status     ", (usage.get("status") if isinstance(usage, dict) else None))
    route = ana.get("route") or {}
    print("route            ", json.dumps({k: route.get(k) for k in (
        "route", "gate_evaluated", "case_follow_up", "correction_attempts",
        "rejections_observed", "audit_ran")}))
    print("agents observed  ", [(p.get("agent"), p.get("version")) for p in ana.get("participation", [])])
    print("unhealthy outputs", ana.get("unhealthy_outputs"))
    print("release          ", json.dumps(ana.get("release")))
    print("compliance token ", json.dumps(ana.get("compliance")))
    print("case follow-up   ", json.dumps(ana.get("case_follow_up")))
    print("audit            ", json.dumps(ana.get("audit"))[:600])
    ids = []
    for a in actions:
        wa = a.get("workflow_action") if isinstance(a, dict) else None
        if isinstance(wa, dict):
            ids.append(wa.get("action_id") or wa.get("id"))
        elif isinstance(a, dict):
            ids.append(a.get("action_id") or a.get("id"))
    seen = []
    for i in ids:
        if i and i not in seen:
            seen.append(i)
    print("action ids       ", seen)
    # model-produced: the compliance decision objects, in order
    texts = []
    for item in items:
        if item.get("type") == "message" and item.get("role") == "assistant":
            name = (item.get("created_by") or {}).get("agent", {}).get("name")
            if name == "EvidenceComplianceAgent":
                texts.append(analysis.text_of(item))
    for n, text in enumerate(texts, 1):
        obj = analysis._json_object_in(text) or {}
        last = [l for l in text.splitlines() if l.strip()][-1] if text.strip() else ""
        print("compliance #%d    decision=%s correction_count=%s final_line=%s" % (
            n, obj.get("decision"), obj.get("correction_count"), last[:60]))
        print("   failed_checks ", obj.get("failed_checks"))
        print("   reason_codes  ", json.dumps(obj.get("reason_codes"))[:700])
        print("   summary       ", str(obj.get("compliance_summary"))[:400])
    u = (usage.get("usage") if isinstance(usage, dict) else None) or {}
    print("usage            ", {k: u.get(k) for k in ("input_tokens", "output_tokens", "total_tokens")})
    print("report tail")
    rep = load(run_dir, "10_usage_report.md") or ""
    for line in rep.splitlines():
        if any(k in line for k in ("Elapsed", "Cost", "Within cap", "Route observed", "Final status")):
            print("  ", line.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
