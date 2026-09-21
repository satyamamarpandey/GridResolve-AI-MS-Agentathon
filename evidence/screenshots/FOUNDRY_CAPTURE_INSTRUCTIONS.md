# Foundry captures needed for the final video and deck

Rewritten 2026-09-20 for workflow v10. Only a person signed in to the Foundry
portal can take these. They cannot be generated, and nothing stands in for them:
the video builder renders a red placeholder and refuses to build a final file
until both exist.

The three older captures in this folder, S02, S04 and S09, show workflow v5 and
the pre-run totals. They are kept as history and are no longer used by the video
or the deck.

## Required, two captures

Browser window at 1920 x 1080, zoom 100 percent, light theme. Save as PNG into
this folder with exactly these names.

| File | Page | Must be visible |
| --- | --- | --- |
| `F10-WORKFLOW.png` | Foundry portal, Agents, `GridResolveAIWorkflow`, the workflow designer | The name `GridResolveAIWorkflow`, **Version 10**, the node graph with the nine agent nodes, the If/else gate and the branches |
| `F10-COMPLIANCE.png` | Foundry portal, Agents, `EvidenceComplianceAgent`, the agent detail page | The name, **version 6**, model `gpt-5-mini`, the **Tools section empty**, and the start of the instructions |

## Optional, use if the portal shows it

| File | Page | Why |
| --- | --- | --- |
| `F10-RUN.png` | The final run's conversation or trace, if the portal lists it. Response id `wfresp_0e23435a002841f300QNFbMTKNows9FL4BUVI6SdrJswCRe72z` | A portal view of the real run. The video does not depend on it, because the run is shown from the evidence files |
| `F10-AGENTS.png` | The agents list showing all nine agents and the workflow | Shows the nine-agent team in Foundry |

## Before saving, check every capture

- The Foundry **project name**, the resource name, the resource group, the
  subscription id, the tenant id and your email address must not be readable.
  The breadcrumb at the top of the portal shows the project name. Crop it out or
  cover it with a plain rectangle labelled `[project name redacted]`, as was done
  for S02 and S04. Keep the unredacted original outside the repository, or in
  `evidence/_originals_unredacted/`, which is gitignored.
- No access token, key or connection string is on screen.
- The version numbers are legible at full size.
- Nothing is edited apart from that redaction. A crop or a cover rectangle is a
  redaction. Changing a number is fabrication.

## Then

```
python submission/video/build_video.py --check     # should report 4 of 4
python scripts/build_submission_deck.py            # slide 3 picks up F10-WORKFLOW
```

Control Center captures are not taken by hand any more. They are produced by
`python scripts/capture_control_center.py`, and they live in
`evidence/app-screenshots/`, never here.
