# Final Submission Checklist

Updated 2026-09-20, after the final run. Requirements below are quoted from the
official Microsoft Agent-a-thon rules, `aka.ms/AgentathonRules`, read on
2026-09-20. Check the Founderz submission page itself as well, because the rules
say entries must also follow "any additional submission requirements and the
submission process identified on the Founderz platform".

## Deadline

The rules give two times. Section 3 and section 4 say **23:59 PDT on September
24, 2026**. The prize table says **September 24, 2026 at 23:59 GMT**, which is
seven hours earlier. Treat the earlier one as the deadline: **2026-09-24, 23:59
GMT, which is 19:59 EDT and 16:59 PDT.** Submit a day early. Late entries are
not judged "regardless of reason or fault".

## What the rules require

| Rule | Requirement | Status |
| --- | --- | --- |
| Entry information | A video, "no more than 3 minutes in duration and 150MB in size", via the Founderz platform | **BUILT**: `submission/video/GridResolve_Final_Video.mp4`, 172.1 seconds, about 8 MB. Watch it once with sound before uploading |
| Entry information | "a brief written description of the issue the AI agent addresses, the impact of the AI agent, and how the agent was built using ... Microsoft Foundry" | Ready: `02_SUBMISSION_100_WORDS.md`, `01_EXECUTIVE_SUMMARY.md`. Paste-ready text is in `21_FOUNDERZ_SUBMISSION_TEXT.md` |
| AI agent | "a clear purpose and audience, a summary of how it was built and refined, screen shots and example interactions and key lessons learned" | Ready: deck slides 1, 3, 4 and 6, `JUDGE_NARRATIVE.md` sections 3 and 6 |
| Supporting documentation | Optional. "PPTX, PDF, DOCX, DOC, PPT or TXT" | Ready: `GridResolve_AI_Submission_Deck.pptx`, eight slides. Markdown is **not** an accepted format, so export `JUDGE_NARRATIVE.md` to PDF if you want to attach it |
| Video | "Demonstrates the innovation, impact, and usability of the AI agent" | Script covers all three |
| Original work | The entry, the documentation and the video "must be the participant's original work", and videos, "including but not limited to, their filming, editing, graphic design", "must be solely the work of the participant" | **Your decision.** The narration is your own voice. The slides and the video assembly are produced by scripts in this repository, written with AI assistance. Read that rule and decide whether you are comfortable, or re-edit the video yourself from the rendered frames in `submission/video/build/` |
| Judging | Up to 30 points each for innovation, usability and impact, 90 in total | The deck and narrative are organised around these |

## Blocking items, in order

| # | Item | Owner | How |
| --- | --- | --- | --- |
| 1 | Two Foundry captures: `F10-WORKFLOW.png`, `F10-COMPLIANCE.png` | Done 2026-09-21 | Your originals are in `evidence/_originals_unredacted/`, outside git. `scripts/redact_foundry_captures.py` covers the project name and nothing else |
| 2 | Narration | Done 2026-09-21 | Recorded by me, 165.824 seconds, used unedited and at its own speed. `FINAL_VIDEO_SCRIPT.md` is now the transcript of that recording |
| 3 | Build the video | Done 2026-09-21 | `python submission/video/build_video.py --final` printed `VERDICT: READY TO SUBMIT` |
| 4 | Watch the whole video once | You | Pictures and subtitles are placed on the times the words are spoken, taken from a local transcription of the recording. Listen for two phrases the transcription was unsure of: "missing user turns" near 1:30, and "evidence-first" near 0:05. If a subtitle differs from what you said, tell me the words |
| 5 | Rebuild the deck | Done 2026-09-21 | Slide 3 includes the redacted Foundry capture |
| 6 | Approve the commit and push | You | Plan: `docs/PUBLICATION_PLAN_2026-09-20.md`. Nothing has been committed |
| 7 | Submit on Founderz | You | Steps below |

## Submitting on Founderz

1. Sign in at `https://learn.founderz.com` with the Microsoft account you
   registered for Level 3 with, at `aka.ms/AgentathonSep2026`.
2. Open the Agent-a-thon Level 3, Architect, final activity and its submission
   form.
3. Upload `submission/video/GridResolve_Final_Video.mp4`. Confirm it is under 3
   minutes and under 150 MB before uploading. The builder prints both.
4. Paste the written description from `21_FOUNDERZ_SUBMISSION_TEXT.md`: the
   issue, the impact, and how it was built with Microsoft Foundry. If the form
   has separate fields, the text is already split that way. If it has a
   character limit, use the 100 word version.
5. Attach `GridResolve_AI_Submission_Deck.pptx` as supporting documentation.
   Optionally attach a PDF export of `JUDGE_NARRATIVE.md`.
6. If the form has a link field, give the public repository URL, after the push.
7. Submit, then reopen the entry and confirm the video plays and the text saved.
   Take a dated screenshot of the confirmation for your own records.

## Verification before export

- [x] Workflow stated as **v10** in every current document
- [x] Agent versions match Foundry: Triage 5, AccountEvidence 9, UsageAnomaly 4, PolicyKnowledge 6, ResolutionPlanner 6, CustomerCommunication 5, EvidenceCompliance 6, EscalationCoordinator 5, CaseAudit 7
- [x] Three genuine runs stated everywhere, never one or two
- [x] No statement that v10 has not executed
- [x] No statement that compliance rejected the final message, or that the final run took the fail-closed route
- [x] Run 2's escalation reason stated as not established
- [x] Spend stated as about $0.13 provisional, billed amount not yet visible, never a confirmed $0.00
- [x] No integration described as live, and no claim of production readiness
- [x] No claim that evaluations, red-team probes, parallel execution or a correction loop ran
- [x] Every runtime figure in the video and the deck is read from `evidence/runtime/` at build time
- [x] Local suites: 83 routing, 151 synthetic data, 156 application, 357 runner, 91 workflow engine, 198 evaluation package, 138 integration contracts, 105 Power Fx cases
- [x] Control Center captures show v10 and the three runs, and are labelled as local
- [x] No subscription, tenant, resource, resource group or project name in any document or Control Center capture
- [x] No em dash characters in submitted text
- [x] All three runtime evidence folders byte-identical to their manifests
- [x] Project name redacted in F10-WORKFLOW and F10-COMPLIANCE
- [x] `build_video.py --verify` prints READY TO SUBMIT: 172.0 s, 1920x1080, audio present, about 7 MB
- [x] Deck rebuilt with the Foundry capture, slides 3 and 8 looked at again
- [ ] Commit and push approved
