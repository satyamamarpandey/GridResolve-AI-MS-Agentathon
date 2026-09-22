# Screenshot manifest

Updated 2026-09-20, after the final run. Every image listed as present exists on
disk and was inspected. Nothing was fabricated, reconstructed or recreated to
stand in for a portal capture.

Two kinds of image are kept strictly apart. `evidence/screenshots/` holds only
authentic Microsoft Foundry portal captures. `evidence/app-screenshots/` holds
only the local, offline Control Center. A local application screenshot is not
Foundry evidence, and no caption in the video or the deck presents it as one.

Runtime results are **not** shown as screenshots at all. The video and the deck
read the final run's evidence files at build time and render the figures as
slides labelled "Rendered from evidence/runtime/... Not a screenshot". The build
stops if the evidence ever stops saying what the slides say.

## Authentic Microsoft Foundry captures

Folder: `evidence/screenshots/`

| ID | Status | What it shows |
| --- | --- | --- |
| F10-WORKFLOW | Captured 2026-09-20, authentic, project name covered by one solid box | `GridResolveAIWorkflow` designer, **Version 10**, the node graph and the gate. Used in the video and on deck slide 3 |
| F10-COMPLIANCE | Captured 2026-09-20, authentic, project name covered by one solid box | `EvidenceComplianceAgent` **v6**, `gpt-5-mini`, Tools section empty. Used in the video |
| F10-RUN, F10-AGENTS | optional | The final run in the portal, and the nine-agent list |
| S02 | present, **superseded, unused** | Workflow designer at **v5**, with the v5 gate expression. History only |
| S04 | present, **superseded, unused** | `EvidenceComplianceAgent` at **v5**. The live agent is v6 |
| S09 | present, **superseded, unused** | Local suite totals before any run (354). Current totals are in `README.md` |

How to take the two that are needed, and what to redact:
`evidence/screenshots/FOUNDRY_CAPTURE_INSTRUCTIONS.md`.

S02 and S04 had the Foundry project name covered with `[project name redacted]`.
Unredacted originals are kept locally in `evidence/_originals_unredacted/`, which
is gitignored and never published. The same rule applies to the new captures.

## Control Center captures

Folder: `evidence/app-screenshots/`. Taken on 2026-09-20 by
`python scripts/capture_control_center.py`, which serves the built application on
localhost and captures it at 1920 x 1080 in the installed Microsoft Edge. They
are genuine captures of the application as built from this repository.

| ID | What it shows | Used |
| --- | --- | --- |
| APP01 | Dashboard, canonical figures, honest status table naming three real runs | no |
| APP02 | Customer Assistant, offline conversation, declining to confirm the meter fault | no |
| APP04 | Evidence Explorer, claim `CL-4003-06` UNSUPPORTED, zero records cited, and the note that the real final run's message did not assert it | video, deck slide 5 (cropped) |
| APP09 | System Status: three real Foundry runs, 228,769 tokens, about $0.13 provisional, billed amount NOT_YET_VISIBLE | no |
| APP09b | System Status scrolled to the table of the three runs | no |
| APP10 | Runtime Evidence, the final run, labelled ACTUAL FOUNDRY EXECUTION | video |

Every one carries the on-screen `DETERMINISTIC OFFLINE DEMONSTRATION` label or
the "recorded from evidence, not produced by this application" banner. The
application shows workflow v10 in its footer.

The earlier hand-taken captures of APP02, APP04 and APP09, which showed workflow
v5, "never run" and $0.00, are preserved unaltered in
`evidence/app-screenshots/superseded_2026-09-20_v5/`. They were true when taken.

**Where the offline walkthrough differs from the real run.** The Control Center
models the stricter path: the customer's meter claim is itself put to compliance,
which refuses it, and the case goes to a human. In the real final run no agent
asserted that claim, so compliance approved the message, and the open case went
to a human through the separate follow-up gate. The application says so on its
Dashboard and in the Evidence Explorer. APP02 is left out of the video so that a
local refusal cannot be mistaken for the Foundry result.

## Derived crop for the deck

| File | Source | Why |
| --- | --- | --- |
| `submission/final/deck-assets/APP04_claim.png` | `APP04.png` | The selected-claim panel only, so it is legible at slide size. Produced by `build_submission_deck.py`. A region selection, no pixel altered |
| `submission/final/deck-assets/S02_gate.png` | `S02.png` | **Unused.** Shows the v5 gate. Kept as history |

## Verification performed on every image in use

| Check | Result |
| --- | --- |
| Readable at full size | Pass |
| Workflow version shown | v10 in every Control Center capture |
| Canonical figures | Pass: $152.80 to $203.40, 640 to 870 kWh, register movement 870 kWh |
| Email addresses, subscription, tenant, resource group, project name | None visible in any Control Center capture. F10-WORKFLOW and F10-COMPLIANCE showed the project name in the breadcrumb. `scripts/redact_foundry_captures.py` covers it. The originals stay in `evidence/_originals_unredacted/`, which git ignores |
| Tokens, keys or credentials | None visible |
| Claims of a Foundry result made by a local screenshot | None |

## Video usage

The final video is built: `submission/video/GridResolve_Final_Video.mp4`, 172.0
seconds. It uses four captures, `screenshots used: 4 of 4`, and no placeholder.
Every other picture is a slide rendered from the evidence files at build time.

| Shot | Used at |
| --- | --- |
| F10-WORKFLOW | 0:15.9, "I orchestrated nine GPT-5 agents in a hosted Foundry workflow" |
| APP04 | 0:43.8, claim provenance in the local Control Center |
| APP10 | 0:47.0, actual Foundry execution kept apart from the offline demonstration |
| F10-COMPLIANCE | 0:56.9, the independent compliance agent |
