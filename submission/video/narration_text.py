"""
The narration as recorded, with the time each phrase is spoken.

narration.wav is the authority. I recorded it on 2026-09-21 and spoke a different
text from the draft script, so this file was rewritten from the recording. The
words and their times come from a local, offline transcription of that file
(faster-whisper, small.en, CPU), which I then corrected where it misheard a
project term. The audio itself is never edited, sped up or replaced.

CUES: (start seconds, end seconds, text). One cue is at most two subtitle lines.
The subtitles, the SRT file and FINAL_VIDEO_SCRIPT.md are all built from CUES.
"""

NARRATION_SECONDS = 165.824   # length of narration.wav
VIDEO_SECONDS = 172.0         # the closing frame holds after the last word

CUES = [
    (0.00, 4.55, "Hello, I'm Satyam Pandey, and this is GridResolve AI,"),
    (4.55, 8.80, "evidence-first utility billing resolution, built on Microsoft Foundry."),
    (9.00, 12.70, "A customer says their bill jumped, so the meter must be broken."),
    (12.90, 15.70, "GridResolve investigates instead of agreeing."),
    (16.00, 20.10, "I orchestrated nine GPT-5 agents in a hosted Foundry workflow."),
    (20.20, 23.10, "Four investigate, one plans, one drafts,"),
    (23.10, 27.50, "and three handle independent compliance, human escalation, and audit."),
    (27.80, 33.70, "In the final synthetic case, usage rose from 640 to 870 kilowatt hours."),
    (33.80, 36.10, "The meter readings reconciled to the bill."),
    (36.10, 41.60, "The evidence agent produced 22 traceable entries, and the policy agent mapped nine policies."),
    (41.90, 43.80, "None establishes meter failure."),
    (44.00, 46.60, "My Control Center visualizes claim provenance"),
    (46.60, 51.30, "and separates actual Foundry execution from the offline demonstration."),
    (51.60, 56.40, "Every conclusion can be traced back to its supporting evidence and applicable policy."),
    (57.00, 61.80, "Evidence Compliance Agent independently reviews the draft and records its reasons."),
    (62.20, 65.50, "A Power Fx gate requires an exact approval token,"),
    (65.50, 69.00, "complete investigations, and six readable message fields."),
    (69.10, 71.80, "Human case follow-up remains a separate decision."),
    (72.70, 74.60, "This separation actually matters."),
    (74.80, 78.30, "Approving a customer explanation never authorizes a financial adjustment,"),
    (78.30, 82.80, "confirms a defective meter, or closes an unresolved investigation."),
    (83.60, 88.90, "Early Foundry runs exposed defects: a literal release expression and stalled agents,"),
    (89.10, 93.30, "and traced the stalls to missing user turns in shared conversation history,"),
    (93.30, 95.70, "and corrected every agent handoff."),
    (96.10, 101.30, "Workflow version 10 then passed all 14 pre-registered hosted acceptance criteria."),
    (101.70, 103.60, "All nine agents completed."),
    (104.00, 106.85, "Compliance approved the supported message without promising a credit."),
    (106.85, 112.20, "The workflow released readable prose and prepared a Billing Supervisor review package."),
    (112.40, 114.60, "The audit matched the platform evidence."),
    (115.00, 121.20, "Another 1,174 local checks and 105 Power Fx cases passed."),
    (121.50, 125.20, "Foundry tracing and Azure Monitor reconciled token usage."),
    (125.30, 130.40, "Three runs cost about 13 cents by token estimate, pending billing confirmation."),
    (130.70, 134.50, "Beyond the hosted workflow, I built eight typed integration ports,"),
    (134.50, 138.70, "synthetic adapters, and locally tested Microsoft Agent Framework migration."),
    (138.90, 144.40, "I also prepared 30 evaluation cases and 16 adversarial scenarios for a broader validation."),
    (144.80, 149.90, "The next milestone is connecting these validated interfaces to real utility systems,"),
    (150.30, 155.20, "completing operational security testing, and piloting the workflow with billing supervisors."),
    (155.70, 158.40, "GridResolve AI: evidence before explanation,"),
    (158.50, 163.30, "independent review before release, and human authority over consequential decisions."),
    (163.80, 165.40, "Thank you for watching."),
]

NARRATION = [text for _, _, text in CUES]
