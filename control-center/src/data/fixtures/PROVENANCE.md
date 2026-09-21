# UI fixture provenance

These four files are **derived artifacts**. Do not edit them by hand.

## Where they come from

| Committed file | Derived from |
| --- | --- |
| `intake.json` | `data/SYN-CASE-4003_UI_01_INTAKE.json` |
| `investigating.json` | `data/SYN-CASE-4003_UI_02_INVESTIGATING.json` |
| `rejection.json` | `data/SYN-CASE-4003_UI_03_SIMULATED_REJECTION.json` |
| `expectations.json` | `data/SYN-CASE-4003_UI_EXPECTATIONS.json`, copied unchanged |

The originals in `data/` are the operator-supplied bundle. They are never
written to, and they remain exactly as supplied for provenance.

## What the derivation changes

`scripts/derive_ui_fixtures.py` substitutes the canonical SYN-CASE-4003 figures,
read from `submission/SYN-CASE-4003_input.json`, into the supplied structure.

The supplied bundle described the same scenario with different illustrative
numbers: $124.00 to $197.00 over 720 to 1,015 kWh in a 33 day period. The
canonical case uses $152.80 to $203.40 over 640 to 870 kWh in a 31 day period.
Showing both under one case identifier made the application look inconsistent,
and none of the nine supplied UI assertions depends on the figures, so the
demonstration was aligned to the canonical numbers.

**Changed:** monetary amounts, usage, billing days, meter register readings, the
period labels that encode the day count, the two observation strings that quote
figures, and the single claim sentence that quotes amounts.

**Not changed:** `case_id`, `workflow_version` (the v4 label is preserved
deliberately, because the supplied README says not to relabel it), every
identifier, every status, every `SIMULATED` marker, the claim structure, the
unsupported claim's empty evidence list, and the compliance decision.

## How it is enforced

`tests/validate_synthetic_data.py` imports the derivation, re-runs it in memory
against the supplied originals, and asserts the committed files match exactly.
It separately asserts that every identity, version and honesty field survived
the transform untouched, and that the register movement still reconciles with
the usage figure.

The Control Center also compares fixture figures against the canonical engine at
render time and raises a `FIGURE DRIFT` card if they ever disagree.

## To regenerate

```bash
python scripts/derive_ui_fixtures.py
python tests/validate_synthetic_data.py
```
