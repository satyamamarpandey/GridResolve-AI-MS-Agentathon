# TODO (remaining only)

Updated 2026-09-20, after the final run. Deadline 2026-09-24. Status:
FINAL_GRIDRESOLVE_STATUS.md and docs/CURRENT_STATUS.md. The implementation is
frozen: no Foundry edits, no further executions, no spend.

## Done
- Three genuine Foundry runs of SYN-CASE-4003 (v6, v9, v10). Final run 14 of 14. Record: docs/FINAL_RUN_RESULT_2026-09-20.md.
- Workflow v10 and nine agents live and verified read-only, 94 of 94.
- 1,174 local checks, 105 Power Fx cases, all passing.

## Blocking, needs the owner
1. Capture two Foundry portal screenshots, `F10-WORKFLOW.png` and `F10-COMPLIANCE.png`, following `evidence/screenshots/FOUNDRY_CAPTURE_INSTRUCTIONS.md`. The existing S02, S04 and S09 show v5 and are no longer used. The Control Center captures were retaken on 2026-09-20 and show v10 and the three runs.
2. Record narration from the revised `submission/video/FINAL_VIDEO_SCRIPT.md`. No recording exists yet.
3. Approve the commit, the push and the submission. Nothing is committed.

Claude Code cannot do 1 or 2. The portal needs interactive sign-in, and there is no audio capture in this session.

## Then
4. Build the final narrated MP4 with `python submission/video/build_video.py --final`, and verify duration under 180 s, 1920x1080, audio present, subtitles in sync, no placeholder, no outdated version label.
5. Only after the MP4 exists, link it from README.md.
6. Re-run the local suites and the QC sweep before export.

## Not authorized, do not run
- 30-case evaluation suite, about 8 USD. Prepared, not executed.
- 16 red-team scenarios, about 4 USD. Prepared, not executed.
- Any further workflow execution.

## Known open risks
- One run of v10 is one sample of a non-deterministic system.
- The fail-closed branch has not been observed on v10, only on v9.
- Agent names resolve to the latest version, so any edit goes live immediately. Do not edit agents or the workflow.
- Correction loops are not built. Do not claim them.
- Foundry Workflows Preview retires on 2026-12-01.
