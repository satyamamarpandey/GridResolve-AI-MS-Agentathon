# Submission Checklist

Deadline 2026-09-24. Updated 2026-09-20, after the final run. The implementation is frozen. The live tracker for the video, narration, deck and screenshots is `20_FINAL_SUBMISSION_CHECKLIST.md`. Where the two disagree, that file is current.

## Legend
**COMPLETE**, **NEEDS_SCREENSHOT**, **NEEDS_NARRATION**, **READY_TO_SUBMIT** (complete and consistent with `docs/CURRENT_STATUS.md`)

## Written artifacts

| Artifact | Status |
|---|---|
| 00_INDEX.md, judge entry point | READY_TO_SUBMIT |
| 01_EXECUTIVE_SUMMARY.md | READY_TO_SUBMIT |
| 02_SUBMISSION_100_WORDS.md (100 words) | READY_TO_SUBMIT |
| 03_ARCHITECTURE.md | READY_TO_SUBMIT, describes workflow v10 |
| 04_AGENT_TEAM.md | READY_TO_SUBMIT |
| 05_WORKFLOW.md | READY_TO_SUBMIT, v4 to v10 history |
| 06_RUNTIME_PROOF.md | READY_TO_SUBMIT. Three genuine runs, 14 of 14 on the final one |
| 07_GOVERNANCE.md | READY_TO_SUBMIT |
| 08_SECURITY.md | READY_TO_SUBMIT |
| 09_RESPONSIBLE_AI.md | READY_TO_SUBMIT |
| 10_HUMAN_OVERSIGHT.md | READY_TO_SUBMIT |
| 11_EVALUATION_READINESS.md | COMPLETE. Scores absent by design, labeled PREPARED_ONLY |
| 12_BUSINESS_IMPACT.md | READY_TO_SUBMIT |
| 13_LIMITATIONS.md | READY_TO_SUBMIT |
| 14_PRODUCTION_ROADMAP.md | READY_TO_SUBMIT. Integration plan, nothing claimed as live |
| 15_JUDGE_QA.md | READY_TO_SUBMIT |
| 16_DEMO_SCRIPT.md | READY_TO_SUBMIT. Performable from stored evidence, no execution needed |
| 17_THREE_MINUTE_PITCH.md | READY_TO_SUBMIT |
| 18_SCREENSHOT_MANIFEST.md | See `20_FINAL_SUBMISSION_CHECKLIST.md` |
| 19_COMPETITION_EVIDENCE_MATRIX.md | READY_TO_SUBMIT |
| 20_FINAL_SUBMISSION_CHECKLIST.md | Live tracker |
| JUDGE_NARRATIVE.md | See `20_FINAL_SUBMISSION_CHECKLIST.md` |
| architecture_diagram.html | Check against `03_ARCHITECTURE.md` before submitting |

## Machine-readable artifacts

| Artifact | Status |
|---|---|
| gridresolve_synthetic_pack.json, 16 cases, 10 policies | READY_TO_SUBMIT |
| gridresolve_evaluation_suite.jsonl, 30 cases | READY_TO_SUBMIT as a prepared suite, not executed |
| gridresolve_red_team_pack.jsonl, 16 scenarios | READY_TO_SUBMIT as a prepared pack, not executed |
| gridresolve_case_state.schema.json | READY_TO_SUBMIT |
| submission/SYN-CASE-4003_input.json | READY_TO_SUBMIT, frozen, the payload the final run sent |
| tests/test_routing_and_data.py, 83 checks | READY_TO_SUBMIT |
| tests/validate_synthetic_data.py, 151 checks | READY_TO_SUBMIT |
| tests/test_foundry_runner.py, 357 checks, every response mocked | READY_TO_SUBMIT |
| tests/test_workflow_engine.py, 91 checks | READY_TO_SUBMIT |
| tests/powerfx_gate, 105 cases on the real Power Fx engine | READY_TO_SUBMIT |
| tests/verify_live_config.py, 94 read-only live checks | READY_TO_SUBMIT, needs the judge's own Foundry resource to run |
| control-center, 156 application tests | READY_TO_SUBMIT |

## Runtime evidence

| Item | Status |
|---|---|
| Run 1, workflow v6 | COMPLETE. `evidence/runtime/20260920T205607Z_SYN-CASE-4003_80391bf2/`, 11 files, unmodified |
| Run 2, workflow v9 | COMPLETE. `evidence/runtime/20260920T225342Z_SYN-CASE-4003_5e6f1114/`, 12 files, unmodified |
| Final run, workflow v10, 14 of 14 | COMPLETE. `evidence/runtime/20260921T000142Z_SYN-CASE-4003_c2be2b51/`, 12 files, unmodified |
| Acceptance criteria written before the final run | COMPLETE. `docs/FINAL_RUN_ACCEPTANCE_PLAN.md` |
| 30-case evaluation results | NOT RUN. Not authorized |
| 16 red-team results | NOT RUN. Not authorized |
| Traces | Platform spans for the three runs exist in the project's Application Insights resource and were read back, read only. Alerting and dashboards are PRODUCTION_TARGET |
| Billed Azure amount | Not yet visible. Provisional cost from tokens is about $0.13 |

No further execution is planned or authorized. The evidence folders must not be edited.

## Visual evidence and video

Tracked in `20_FINAL_SUBMISSION_CHECKLIST.md` and `18_SCREENSHOT_MANIFEST.md`. Two rules apply to whatever is captured:

- Authentic Foundry portal captures and local Control Center captures stay in separate folders and are labelled apart on screen and in the video.
- A capture that shows an older workflow or agent version is history, and may only be used where the narration says so.

Portal screenshots and narration audio cannot be produced by Claude Code. They need a person.

## Before submitting, check every deliverable says the same thing

- Three genuine executions, not one or two. Workflow v10 has executed.
- Compliance **approved** the final message, with reasons. It did not reject it.
- The final run did not take the fail-closed branch. Run 2 did, on v9, without reasons.
- The open case went to a human after the release. Follow-up was not erased.
- 14 of 14, 22 ledger entries, nine policies, zero audit findings.
- About $0.13 provisional. Billed amount not yet visible. Never a confirmed $0.00.
- No utility, meter, CRM or identity integration is live.
- A runtime-demonstrated, production-oriented prototype. Not production-ready.
- No em dash characters. No Foundry resource, project or resource group name anywhere.
