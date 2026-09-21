"""Export the three genuine Foundry runs for the Control Center.

Read-only over evidence/runtime. Calls nothing on the network. Every value in
the output is read or derived from the captured platform records, or from the
written acceptance result. Nothing here is typed in by hand, apart from the
list price used to turn returned token counts into a provisional cost.

Model outputs sometimes contain typographic dashes. Project text must not, and
model text must not be edited, so a field that contains one is left out and the
omission is recorded. The script fails if a dash reaches the output.

Usage: python scripts/export_runtime_evidence.py
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from runner.analysis import (  # noqa: E402
    _agent_of, _json_object_in, analyze_run_dir, items_of, text_of)
from runner.workflow_map import compose_customer_message  # noqa: E402

EVIDENCE_DIR = ROOT / "evidence" / "runtime"
OUTPUT = ROOT / "control-center" / "src" / "data" / "generated" / "runtimeEvidence.json"
ACCEPTANCE_PLAN = "docs/FINAL_RUN_ACCEPTANCE_PLAN.md"
ACCEPTANCE_RESULT = "docs/FINAL_RUN_RESULT_2026-09-20.md"

WORKFLOW_NAME = "GridResolveAIWorkflow"
INPUT_USD_PER_MILLION = 0.25
OUTPUT_USD_PER_MILLION = 2.00
EXPECTED_INPUT_TOKENS = 186_614
EXPECTED_OUTPUT_TOKENS = 42_155
FORBIDDEN = (chr(0x2014), chr(0x2013))  # em dash, en dash, named by code point

FOLDER_RE = re.compile(r"^(\d{8}T\d{6}Z)_(SYN-CASE-\d+)_[0-9a-f]+$")
ELAPSED_RE = re.compile(r"\|\s*Elapsed\s*\|\s*([\d.]+)s\s*\|")
CRITERION_RE = re.compile(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*\*\*([^*]+)\*\*")
EVIDENCE_ID_RE = re.compile(r"\bEVID-[A-Z0-9-]+\b")
POLICY_ID_RE = re.compile(r"\bPOL-[A-Z]+-\d+\b")


def has_dash(text: str) -> bool:
    return any(mark in text for mark in FORBIDDEN)


def load_json(path: Path) -> object:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def clean_sentences(text: str) -> tuple[list[str], int]:
    """Verbatim sentences of a model text that carry no typographic dash."""
    sentences = [s.strip() for s in re.split(r"(?<=\.)\s+", text) if s.strip()]
    kept = [s for s in sentences if not has_dash(s)]
    for sentence in kept:
        assert sentence in text, sentence
    return kept, len(sentences) - len(kept)


def outputs_by_agent(items: list[dict]) -> dict[str, str]:
    """Last assistant text per author, as the platform recorded it."""
    found: dict[str, str] = {}
    for item in items:
        if item.get("type") == "message" and item.get("role") == "assistant":
            name = _agent_of(item).get("name")
            if name:
                found = {**found, str(name): text_of(item)}
    return found


def platform_workflow_version(items: list[dict], final: dict) -> str:
    versions = unique([str(_agent_of(i).get("version")) for i in items
                       if _agent_of(i).get("name") == WORKFLOW_NAME])
    assert len(versions) == 1, versions
    reference = final.get("agent_reference") or {}
    if reference.get("version") is not None:
        assert str(reference["version"]) == versions[0], (reference, versions)
    return versions[0]


def started_at(folder: str) -> str:
    match = FOLDER_RE.match(folder)
    assert match, folder
    stamp = datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    return stamp.strftime("%Y-%m-%dT%H:%M:%SZ")


def elapsed_seconds(run_dir: Path) -> float:
    match = ELAPSED_RE.search((run_dir / "10_usage_report.md").read_text(encoding="utf-8"))
    assert match, "no Elapsed row in %s" % run_dir.name
    return float(match.group(1))


def provisional_usd(input_tokens: int, output_tokens: int) -> float:
    cost = (input_tokens * INPUT_USD_PER_MILLION + output_tokens * OUTPUT_USD_PER_MILLION) / 1_000_000
    return round(cost, 4)


def agents_block(analysis: dict) -> list[dict]:
    problems = {u["agent"]: list(u["problems"]) for u in analysis["unhealthy_outputs"]}
    return [{"agent": p["agent"],
             "version": str(p["version"]),
             "output_chars": p["output_chars"],
             "healthy": p["agent"] not in problems,
             "problems": problems.get(p["agent"], [])}
            for p in analysis["participation"]]


def ledger_block(text: str | None, key: str, agent_row: dict | None) -> dict:
    parsed = _json_object_in(text) if text else None
    entries = parsed.get(key) if isinstance(parsed, dict) else None
    if isinstance(entries, list) and entries:
        return {"status": "PRODUCED", "count": len(entries), "problems": []}
    return {"status": "NOT_PRODUCED", "count": 0,
            "problems": list(agent_row["problems"]) if agent_row else ["AGENT_NOT_OBSERVED"]}


def compliance_block(text: str | None, analysis: dict) -> dict:
    parsed = _json_object_in(text) if text else None
    base = {"token": analysis["compliance"]["token"],
            "final_line": analysis["compliance"]["final_line"]}
    if not isinstance(parsed, dict):
        return {**base, "decision": None, "reasons_given": False, "failed_checks": None,
                "human_review_required": None, "summary_sentences": [],
                "summary_sentences_omitted": 0, "evidence_ids_cited": [], "policy_ids_cited": []}
    summary = str(parsed.get("compliance_summary") or "")
    kept, omitted = clean_sentences(summary)
    return {**base,
            "decision": parsed.get("decision"),
            "reasons_given": bool(summary),
            "failed_checks": len(parsed.get("failed_checks") or []),
            "human_review_required": parsed.get("human_review_required"),
            "summary_sentences": kept,
            "summary_sentences_omitted": omitted,
            "evidence_ids_cited": unique(EVIDENCE_ID_RE.findall(summary)),
            "policy_ids_cited": unique(POLICY_ID_RE.findall(summary))}


def release_block(outputs: dict[str, str], analysis: dict) -> dict:
    outcome = analysis["release"]["outcome"]
    released = outputs.get(WORKFLOW_NAME, "")
    assert len(released) == analysis["release"]["released_chars"], outcome
    assert not has_dash(released), "released text contains a typographic dash"
    draft = _json_object_in(outputs.get("CustomerCommunicationAgent") or "")
    composed = compose_customer_message(draft) if isinstance(draft, dict) else None
    return {"outcome": outcome,
            "customer_ready": analysis["release"]["customer_ready"],
            "released_chars": len(released),
            "text": released,
            "equals_composed_draft": bool(released) and composed is not None and released == composed}


def human_review_block(text: str | None, analysis: dict) -> dict:
    follow_up = analysis["case_follow_up"]
    base = {"planner_token": follow_up["planner_token"],
            "planner_resolution_status": follow_up["planner_resolution_status"],
            "follow_up_observed": follow_up["observed"],
            "follow_up_gate_evaluated": analysis["route"]["follow_up_gate_evaluated"],
            "findings": list(follow_up["findings"])}
    package = _json_object_in(text) if text else None
    if not isinstance(package, dict):
        return {**base, "package_produced": False, "recommended_reviewer": None,
                "routing_target": None, "routing_fallback": None, "disposition": None,
                "case_state": None, "decision_card": None}
    routing = package.get("routing") if isinstance(package.get("routing"), dict) else {}
    card = package.get("decision_card") if isinstance(package.get("decision_card"), dict) else {}
    return {**base,
            "package_produced": True,
            "recommended_reviewer": package.get("recommended_reviewer"),
            "routing_target": routing.get("route_to"),
            "routing_fallback": routing.get("escalate_to_if_unavailable"),
            "disposition": package.get("final_disposition"),
            "case_state": package.get("case_state"),
            "decision_card": {"parts": len(card),
                              "known_facts": len(card.get("known_facts") or []),
                              "unknowns": len(card.get("unknowns") or []),
                              "applicable_policies": len(card.get("applicable_policies") or [])}}


def export_run(run_dir: Path) -> dict:
    analysis = analyze_run_dir(str(run_dir))
    final = load_json(run_dir / "06_final_response.json")
    ids = load_json(run_dir / "03_response_id.json")
    items = items_of(load_json(run_dir / "07_conversation_items.json"))
    outputs = outputs_by_agent(items)
    agents = agents_block(analysis)
    by_name = {a["agent"]: a for a in agents}
    usage = final["usage"]
    assert final["id"] == ids["response_id"], run_dir.name
    assert usage["input_tokens_details"]["cached_tokens"] == 0, "cached tokens change the price"
    return {
        "evidence_folder": run_dir.name,
        "case_id": FOLDER_RE.match(run_dir.name).group(2),
        "case_sha256": analysis["case_sha256"],
        "response_id": ids["response_id"],
        "final_status": final["status"],
        "workflow_version": platform_workflow_version(items, final),
        "started_at": started_at(run_dir.name),
        "elapsed_seconds": elapsed_seconds(run_dir),
        "stream_events": analysis["stream_events"],
        "conversation_items": len(items),
        "agents": agents,
        "agents_invoked": len(agents),
        "agents_healthy": sum(1 for a in agents if a["healthy"]),
        "agents_not_observed": list(analysis["route"]["agents_not_observed"]),
        "investigation_complete": analysis["investigation"]["complete"],
        "usage": {"input_tokens": usage["input_tokens"],
                  "cached_input_tokens": usage["input_tokens_details"]["cached_tokens"],
                  "output_tokens": usage["output_tokens"],
                  "reasoning_tokens": usage["output_tokens_details"]["reasoning_tokens"],
                  "total_tokens": usage["total_tokens"]},
        "provisional_usd": provisional_usd(usage["input_tokens"], usage["output_tokens"]),
        "evidence_ledger": ledger_block(outputs.get("AccountEvidenceAgent"), "evidence_ledger",
                                        by_name.get("AccountEvidenceAgent")),
        "policy_mapping": ledger_block(outputs.get("PolicyKnowledgeAgent"), "policy_ledger",
                                       by_name.get("PolicyKnowledgeAgent")),
        "compliance": compliance_block(outputs.get("EvidenceComplianceAgent"), analysis),
        "route": {"observed": analysis["route"]["route"],
                  "gate_evaluated": analysis["route"]["gate_evaluated"],
                  "audit_ran": analysis["route"]["audit_ran"]},
        "release": release_block(outputs, analysis),
        "human_review": human_review_block(outputs.get("EscalationCoordinatorAgent"), analysis),
        "audit": {"parsed": analysis["audit"]["audit_parsed"],
                  "accurate": analysis["audit"]["accurate"],
                  "findings": list(analysis["audit"]["findings"])},
    }


def acceptance(final_run: dict) -> dict:
    lines = (ROOT / ACCEPTANCE_RESULT).read_text(encoding="utf-8").splitlines()
    rows = [m for m in (CRITERION_RE.match(line) for line in lines) if m]
    items = [{"number": int(m.group(1)), "title": m.group(2),
              "verdict": m.group(3).split(",")[0].strip()} for m in rows]
    assert [i["number"] for i in items] == list(range(1, len(items) + 1)), items
    verdicts = [i["verdict"] for i in items]
    assert set(verdicts) <= {"PASS", "FAIL", "NOT OBSERVABLE"}, verdicts
    return {"criteria": len(items),
            "passed": verdicts.count("PASS"),
            "failed": verdicts.count("FAIL"),
            "not_observable": verdicts.count("NOT OBSERVABLE"),
            "evidence_folder": final_run["evidence_folder"],
            "evidence_ledger_entries": final_run["evidence_ledger"]["count"],
            "policies_mapped": final_run["policy_mapping"]["count"],
            "plan": ACCEPTANCE_PLAN,
            "result": ACCEPTANCE_RESULT,
            "items": items}


def build() -> dict:
    run_dirs = sorted(p for p in EVIDENCE_DIR.iterdir() if p.is_dir() and FOLDER_RE.match(p.name))
    runs = [export_run(p) for p in run_dirs]
    ledger = load_json(EVIDENCE_DIR / "RUN_LEDGER.json")
    ledger_entries = ledger.get("runs", ledger) if isinstance(ledger, dict) else ledger
    assert len(runs) == 3, [p.name for p in run_dirs]
    assert len(ledger_entries) == len(runs), "RUN_LEDGER.json disagrees with the evidence folders"
    totals = {"runs": len(runs),
              "input_tokens": sum(r["usage"]["input_tokens"] for r in runs),
              "output_tokens": sum(r["usage"]["output_tokens"] for r in runs),
              "provisional_usd": round(sum(r["provisional_usd"] for r in runs), 4)}
    assert totals["input_tokens"] == EXPECTED_INPUT_TOKENS, totals
    assert totals["output_tokens"] == EXPECTED_OUTPUT_TOKENS, totals
    return {"content_kind": "ACTUAL_FOUNDRY_EXECUTION",
            "generated_by": "scripts/export_runtime_evidence.py",
            "source": "evidence/runtime",
            "pricing": {"input_usd_per_million": INPUT_USD_PER_MILLION,
                        "output_usd_per_million": OUTPUT_USD_PER_MILLION,
                        "basis": "Returned token counts at list price. Provisional, not a billed amount."},
            "runs": runs,
            "totals": totals,
            "final_acceptance": acceptance(runs[-1])}


def main() -> int:
    text = json.dumps(build(), indent=2, ensure_ascii=False) + "\n"
    assert not has_dash(text), "a typographic dash reached the export"
    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    print("wrote %s, %d bytes" % (OUTPUT.relative_to(ROOT).as_posix(), len(text.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
