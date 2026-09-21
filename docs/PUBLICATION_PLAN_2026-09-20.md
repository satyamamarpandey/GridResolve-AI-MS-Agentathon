# Commit and publication plan

Prepared 2026-09-20. **Nothing has been committed, pushed or submitted.** Each
step below needs the owner's explicit approval.

Branch `master`, remote `origin`, last commit `370a62b`. About 64 tracked files
are modified and the items below are untracked.

## Untracked, and needed

| Path | Why it must be published |
| --- | --- |
| `evidence/runtime/` | The three genuine Foundry runs. The whole submission rests on them. Commit unmodified |
| `evidence/reanalysis/` | Offline re-reads of those runs, labelled as derived |
| `runner/` | The guarded runner that made the runs and analyses them offline |
| `tests/test_foundry_runner.py`, `tests/test_workflow_engine.py`, `tests/powerfx_gate/`, `tests/workflow_engine/`, `tests/escalation_validation/` | Reproduce 357 runner checks, 91 workflow engine checks and 105 Power Fx cases. `bin/` and `obj/` are already ignored |
| `docs/CORRECTION_2026-09-20.md`, `docs/FIRST_RUN_AND_CORRECTIONS_2026-09-20.md`, `docs/SECOND_RUN_COMPARISON_PLAN.md`, `docs/SECOND_RUN_RESULT_2026-09-20.md`, `docs/V10_CORRECTIONS_2026-09-20.md`, `docs/FINAL_RUN_ACCEPTANCE_PLAN.md`, `docs/FINAL_RUN_RESULT_2026-09-20.md`, `docs/CURRENT_STATUS.md`, this file | The run records, the pre-registered criteria and the current status |
| `control-center/src/data/foundryRuns.ts` | The recorded facts the status page shows |
| `scripts/build_submission_deck.py`, `scripts/capture_control_center.py`, `scripts/run_local_suites.ps1` | Rebuild the deck, the application captures and the local totals |
| `submission/video/narration_text.py` | The narration, shared by the script and the subtitles |
| `submission/final/21_FOUNDERZ_SUBMISSION_TEXT.md`, `submission/final/GridResolve_AI_Submission_Deck.pptx`, `submission/final/deck-assets/` | Submission text, the deck and its derived crop |
| `evidence/app-screenshots/APP01, APP02, APP04, APP09, APP09b` and `superseded_2026-09-20_v5/` | Current application captures, and the earlier ones kept as history |
| `evidence/screenshots/S02.png`, `S04.png`, `S09.png` | The redacted v5-era Foundry captures, kept as history |
| `.gitattributes` | Line ending rules |
| `evaluation/`, `tests/test_evaluation_package.py` | Added 2026-09-21. Deterministic checks, provenance trace, policy catalog, Foundry shaped datasets. 198 checks. Dataset B holds verbatim model output, including dash characters I do not use myself |
| `integration/`, `tests/test_integration_contracts.py` | Added 2026-09-21. Typed contracts and synthetic adapters. 138 checks |
| `migration/agent_framework/` | Added 2026-09-21. Agent Framework parity proof and its result |
| `evidence/platform_telemetry/`, `scripts/export_platform_telemetry.py` | Added 2026-09-21. Redacted read-only summary of Azure Monitor metrics and Application Insights spans. The script refuses to write if a tenant identifier is in the output |
| `docs/FOUNDRY_CAPABILITY_INVENTORY.md`, `docs/SECURITY_AND_GOVERNANCE_EVIDENCE.md`, `docs/OPERATIONS_MONITORING_AND_COST.md`, `docs/ROUTINES_SKILLS_TOOLS_MEMORY_DESIGN.md` | Added 2026-09-21 |
| `scripts/export_runtime_evidence.py`, `scripts/redact_foundry_captures.py`, the Runtime Evidence view in `control-center/` | Added 2026-09-21 |
| `evidence/screenshots/F10-WORKFLOW.png`, `F10-COMPLIANCE.png`, `evidence/app-screenshots/APP10.png` | Redacted Foundry captures and the new application capture |
| `submission/video/GridResolve_Final_Video.mp4` | Finished 2026-09-21: 172.1 s, 1920x1080, about 8 MB, well under GitHub's 100 MB file limit |

## Must stay out

| Path | Why | How |
| --- | --- | --- |
| `evidence/_originals_unredacted/` | Shows the Foundry project name | Already in `.gitignore` |
| `submission/video/narration.wav` | Large, and your voice is in the MP4 anyway | Already in `.gitignore` |
| `submission/video/build/`, `control-center/dist/`, `node_modules/`, `__pycache__/`, `.ruff_cache/`, `tests/*/bin`, `tests/*/obj` | Build output | Already ignored |
| New `F10-*.png` captures before redaction | The portal breadcrumb shows the project name | Redact first. Keep originals in `evidence/_originals_unredacted/` |

## Checked on 2026-09-20, over every file git would see

- The Foundry resource name, project name and resource group: **not found**.
- JWT-shaped strings, bearer tokens, keys: **not found**.
- Email addresses and local user paths: **not found**.
- GUIDs: one, `3e63ea09-...`, which is the design system's folder name and is
  already public. Not an Azure identifier.
- The runtime evidence holds response and conversation identifiers. They are
  useless without an authenticated session in the owner's tenant, and the runner
  writes placeholders in place of the resource and project names.

Checked again on 2026-09-21 over all 230 modified and untracked files, after the additions above and the redacted F10 captures: nothing found. Run it once more after adding the MP4.

## Proposed commits, in order

1. `feat: guarded Foundry runner, real Power Fx gate tests and workflow engine harness`
   `runner/`, the five test paths, `scripts/run_local_suites.ps1`.
2. `docs: evidence and records of three real Foundry runs of SYN-CASE-4003`
   `evidence/runtime/`, `evidence/reanalysis/`, the dated run documents,
   `docs/CURRENT_STATUS.md`.
3. `fix: control center reports the three real runs instead of denying them`
   `control-center/`, `scripts/capture_control_center.py`,
   `evidence/app-screenshots/`.
4. `docs: bring submission materials to workflow v10 and the final run result`
   `README.md`, `submission/final/`, the root status files, the manifest,
   `tests/validate_synthetic_data.py`, `tests/verify_live_config.py`.
5. `feat: video and deck built from the final run's evidence`
   `submission/video/`, `scripts/build_submission_deck.py`, the deck.
6. After the narration and captures: `docs: final video and Foundry v10 captures`.

No history rewrite, no force push. `git push -u origin master` only after the
owner approves, and after a last run of:

```
python tests/test_routing_and_data.py
python tests/validate_synthetic_data.py
python tests/test_foundry_runner.py
python tests/test_workflow_engine.py
dotnet run --project tests/powerfx_gate
cd control-center && npx tsc -b && npx vitest run && npm run build
```

## After the push

Open the public repository in a private browser window and check that the README
renders, the links to `docs/CURRENT_STATUS.md` and the run records resolve, the
MP4 link works, and no capture shows the project name.
