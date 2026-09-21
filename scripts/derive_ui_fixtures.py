"""
Derive the Control Center UI fixtures from the supplied bundle, with the
canonical SYN-CASE-4003 figures substituted in.

WHY THIS EXISTS

The supplied bundle in data/ describes the same scenario as the canonical case,
a customer alleging meter failure after a bill increase, but uses different
illustrative figures: $124 to $197 over 720 to 1,015 kWh in a 33 day period,
against the canonical $152.80 to $203.40 over 640 to 870 kWh in a 31 day period.

Both reconcile internally. Neither is wrong. But showing two different bill
amounts under one case identifier makes the application look inconsistent, and
a judge should not have to work out which set is real.

None of the nine supplied UI assertions depends on the figures. They test
structure and labelling: that the unsupported claim renders as UNSUPPORTED with
no evidence, that nothing is presented as an executed run, that the simulated
compliance rejection surfaces POL-MTR-003. So the figures are not load bearing
and the demonstration is aligned to the canonical numbers.

WHAT IS AND IS NOT CHANGED

Changed: monetary amounts, usage, billing days, meter register readings, the
period labels that encode the day count, the two observation strings that quote
figures, and the one claim sentence that quotes amounts.

Not changed: case_id, workflow_version (the v4 label is preserved deliberately,
because the supplied README says not to relabel it), every identifier, every
status, every SIMULATED marker, the claim structure, the unsupported claim's
empty evidence list, and the compliance decision.

PROVENANCE

data/ is never written to. It stays exactly as supplied, and it is the input to
this script. tests/validate_synthetic_data.py re-runs this derivation in memory
and asserts the committed fixtures match it exactly, so the transform is
auditable and cannot drift silently.

Read only with respect to Azure. No model call, no cost.

Run: python scripts/derive_ui_fixtures.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SOURCES = {
    "intake": "data/SYN-CASE-4003_UI_01_INTAKE.json",
    "investigating": "data/SYN-CASE-4003_UI_02_INVESTIGATING.json",
    "rejection": "data/SYN-CASE-4003_UI_03_SIMULATED_REJECTION.json",
    "expectations": "data/SYN-CASE-4003_UI_EXPECTATIONS.json",
}

TARGETS = {
    "intake": "control-center/src/data/fixtures/intake.json",
    "investigating": "control-center/src/data/fixtures/investigating.json",
    "rejection": "control-center/src/data/fixtures/rejection.json",
    "expectations": "control-center/src/data/fixtures/expectations.json",
}


def load(rel: str):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def canonical_figures() -> dict:
    """Read the canonical case once, so no figure is hardcoded twice."""
    case = load("submission/SYN-CASE-4003_input.json")
    rec = case["synthetic_account_records"]
    prev, curr = rec["billing_history"]
    first, second = rec["meter_reads"]
    return {
        "prev_usd": float(prev["amount_usd"]),
        "curr_usd": float(curr["amount_usd"]),
        "prev_kwh": int(prev["kwh_billed"]),
        "curr_kwh": int(curr["kwh_billed"]),
        "prev_days": int(prev["billing_days"]),
        "curr_days": int(curr["billing_days"]),
        "start_kwh": int(first["register_kwh"]),
        "end_kwh": int(second["register_kwh"]),
    }


def money(value: float) -> str:
    """Render 203.4 as $203.40, matching how the application displays it."""
    return f"${value:,.2f}"


def align_snapshot(snapshot: dict, fig: dict) -> dict:
    """Return a new snapshot with canonical figures. The input is not mutated."""
    prev_period = f"PREVIOUS_{fig['prev_days']}_DAYS"
    curr_period = f"CURRENT_{fig['curr_days']}_DAYS"
    day_gap = fig["curr_days"] - fig["prev_days"]
    register_delta = fig["end_kwh"] - fig["start_kwh"]

    # Each entry replaces the value, the period label, and where the observation
    # quotes a figure, the observation too.
    replacements = {
        "SYN-EV-4003-01": {"value": fig["prev_usd"], "period": prev_period},
        "SYN-EV-4003-02": {"value": fig["curr_usd"], "period": curr_period},
        "SYN-EV-4003-03": {"value": fig["prev_kwh"], "period": prev_period},
        "SYN-EV-4003-04": {"value": fig["curr_kwh"], "period": curr_period},
        "SYN-EV-4003-05": {
            "value": fig["curr_days"],
            "period": curr_period,
            "observation": (
                f"Current billing period is {day_gap} day longer than previous."
                if day_gap == 1
                else f"Current billing period is {day_gap} days longer than previous."
            ),
        },
        "SYN-EV-4003-06": {
            "value": {
                "read_type": "ACTUAL",
                "start_kwh": fig["start_kwh"],
                "end_kwh": fig["end_kwh"],
            },
            "period": curr_period,
            "observation": (
                f"Recorded actual reads yield {register_delta:,} kWh; this alone "
                "does not establish meter accuracy or failure."
            ),
        },
        "SYN-EV-4003-07": {"period": curr_period},
        "SYN-EV-4003-08": {"period": curr_period},
        "SYN-EV-4003-09": {"period": curr_period},
    }

    out = json.loads(json.dumps(snapshot))  # deep copy, no shared references

    for evidence in out.get("evidence_ledger", []):
        patch = replacements.get(evidence["evidence_id"])
        if patch:
            evidence.update(patch)

    # The one claim sentence that quotes amounts.
    for claim in out.get("claim_ledger", []):
        if claim["claim_id"] == "SYN-CL-4003-01":
            claim["claim_text"] = (
                f"The current synthetic bill is {money(fig['curr_usd'])} versus "
                f"{money(fig['prev_usd'])} for the prior period."
            )

    return out


def main() -> int:
    fig = canonical_figures()
    written = []

    for name, source_rel in SOURCES.items():
        source = load(source_rel)
        # The expectations file carries no figures, so it passes through
        # untouched and stays byte identical to the supplied original.
        derived = source if name == "expectations" else align_snapshot(source, fig)

        target_path = os.path.join(ROOT, TARGETS[name])
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(derived, f, indent=2)
            f.write("\n")
        written.append(TARGETS[name])

    print("Canonical figures applied:")
    print(f"  bill    {money(fig['prev_usd'])} -> {money(fig['curr_usd'])}")
    print(f"  usage   {fig['prev_kwh']} kWh -> {fig['curr_kwh']} kWh")
    print(f"  days    {fig['prev_days']} -> {fig['curr_days']}")
    print(f"  register {fig['start_kwh']:,} -> {fig['end_kwh']:,}")
    print("\nDerived fixtures written:")
    for path in written:
        print(f"  {path}")
    print("\ndata/ was not modified. Originals preserved for provenance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
