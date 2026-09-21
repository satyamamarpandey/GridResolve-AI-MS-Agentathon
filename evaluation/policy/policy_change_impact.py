"""What would a policy change touch?

Two pure functions. diff_catalogs compares two catalogs by definition and
names the fields that changed. impact_of lists, for each policy, the claims,
actions, disclosures and handoff packages in captured runs that cite it, so a
reviewer knows which past answers to look at again.

Local and read-only. It reads captured runs. It does not re-run anything.

Run: python -m evaluation.policy.policy_change_impact POL-MTR-003
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Iterable, Mapping, Sequence

from evaluation import deterministic_checks as dc
from evaluation.run_record import RunRecord, load_all

IGNORED_FIELDS = frozenset({"definition_sha256"})


def _by_id(catalog: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {p["policy_id"]: p for p in catalog["policies"]}


def diff_catalogs(old: Mapping[str, Any], new: Mapping[str, Any]) -> list[dict]:
    before, after = _by_id(old), _by_id(new)
    changes = []
    for policy_id in sorted(set(before) | set(after)):
        if policy_id not in after:
            changes.append({"policy_id": policy_id, "change": "REMOVED",
                            "changed_fields": []})
        elif policy_id not in before:
            changes.append({"policy_id": policy_id, "change": "ADDED",
                            "changed_fields": []})
        else:
            fields = sorted(
                f for f in (set(before[policy_id]) | set(after[policy_id]))
                - IGNORED_FIELDS
                if before[policy_id].get(f) != after[policy_id].get(f))
            if fields:
                changes.append({"policy_id": policy_id, "change": "MODIFIED",
                                "changed_fields": fields})
    return changes


def _citing(rows: Any, id_key: str, policy_key: str, policy_id: str) -> list[str]:
    if not isinstance(rows, list):
        return []
    return [str(r.get(id_key)) for r in rows if isinstance(r, dict)
            and policy_id in (r.get(policy_key) or [])]


def _run_impact(policy_id: str, run: RunRecord) -> dict:
    planner = run.data_of(dc.PLANNER_AGENT)
    policy = run.data_of(dc.POLICY_AGENT)
    handoff = run.data_of(dc.ESCALATION_AGENT)
    disclosures = [
        str(d.get("disclosure")) for d in policy.get("required_customer_disclosures")
        or [] if isinstance(d, dict) and policy_id in str(d.get("policy_reference"))]
    return {
        "run": run.run_id,
        "workflow_version": run.workflow_version,
        "claims": _citing(planner.get("claim_ledger"), "claim_id",
                          "policy_ids", policy_id),
        "actions": _citing(planner.get("recommended_actions"), "action_id",
                           "policy_basis_ids", policy_id),
        "disclosures": disclosures,
        "in_handoff_package": policy_id in json.dumps(
            handoff.get("policy_ledger") or []),
        "released_to_customer": run.released is not None
        and run.analysis.get("release", {}).get("customer_ready") is True,
    }


def impact_of(policy_ids: Iterable[str], runs: Sequence[RunRecord]) -> list[dict]:
    result = []
    for policy_id in policy_ids:
        per_run = [_run_impact(policy_id, run) for run in runs]
        result.append({
            "policy_id": policy_id,
            "claims": sorted({c for r in per_run for c in r["claims"]}),
            "actions": sorted({a for r in per_run for a in r["actions"]}),
            "runs": per_run,
        })
    return result


def main(argv: Sequence[str]) -> int:
    if len(argv) < 2:
        sys.stderr.write("usage: python -m evaluation.policy."
                         "policy_change_impact POLICY_ID [POLICY_ID ...]\n")
        return 2
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    runs = load_all(os.path.join(root, "evidence", "runtime"))
    sys.stdout.write(json.dumps(impact_of(argv[1:], runs), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
