"""Build policy_catalog.json from the governed synthetic policy pack.

The catalog adds nothing the pack does not say. Where the pack is silent (it
records a status, not an effective date) the catalog says null and says why.
Each record carries a hash of its definition, so a later edit to a policy shows
up as a change that policy_change_impact.py can trace to the claims that cite it.

Run: python -m evaluation.policy.build_policy_catalog
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from typing import Any, Mapping

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PACK_PATH = os.path.join(ROOT, "gridresolve_synthetic_pack.json")
CATALOG_PATH = os.path.join(HERE, "policy_catalog.json")

DATE_NOTE = ("The synthetic pack records effective_status, not a date. I have "
             "not invented one. A production catalog needs an effective date "
             "and an end date on every version.")
MISSING_EVIDENCE_NOTE = ("The pack lists the evidence a policy needs but does "
                         "not define a per-policy fallback. When required "
                         "evidence is missing, no allowed action of this policy "
                         "is available and the case follows on_conflict.")


def definition_hash(policy: Mapping[str, Any]) -> str:
    body = json.dumps(policy, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def catalog_record(policy: Mapping[str, Any], pack: Mapping[str, Any]) -> dict:
    return {
        "policy_id": policy["policy_id"],
        "version": policy["version"],
        "title": policy["title"],
        "purpose": policy["purpose"],
        "effective_status": policy["effective_status"],
        "effective_date": None,
        "effective_date_note": DATE_NOTE,
        "supersedes": policy.get("supersedes"),
        "source": {
            "file": os.path.basename(PACK_PATH),
            "policy_version": pack["policy_version"],
            "dataset_version": pack["dataset_version"],
            "data_classification": pack["data_classification"],
        },
        "applicability": {
            "conditions": list(policy["conditions"]),
            "allowed_actions": list(policy["allowed_actions"]),
            "prohibited_actions": list(policy["prohibited_actions"]),
        },
        "human_authorization": policy["human_approval_requirement"],
        "customer_disclosure": policy["customer_disclosure_requirement"],
        "missing_evidence_handling": {
            "required_evidence": list(policy["required_evidence"]),
            "on_conflict": policy["conflict_behavior"],
            "note": MISSING_EVIDENCE_NOTE,
        },
        "definition_sha256": definition_hash(policy),
    }


def build_catalog(pack: Mapping[str, Any]) -> dict:
    return {
        "catalog": "GRIDRESOLVE-POLICY-CATALOG",
        "policy_version": pack["policy_version"],
        "data_classification": pack["data_classification"],
        "built_from": os.path.basename(PACK_PATH),
        "status": "LOCAL_FILE_ONLY. Not uploaded to Foundry, not indexed, not "
                  "attached to any agent.",
        "policies": [catalog_record(p, pack) for p in pack["policies"]],
    }


def main() -> int:
    with open(PACK_PATH, encoding="utf-8") as handle:
        pack = json.load(handle)
    catalog = build_catalog(pack)
    with open(CATALOG_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(catalog, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
    sys.stdout.write("Wrote %d policies to %s\n"
                     % (len(catalog["policies"]), os.path.relpath(CATALOG_PATH, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
