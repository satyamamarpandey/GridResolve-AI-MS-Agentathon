# Screenshot capture checklist

Everything you need to capture, in one place. Verified against the actual
folders and the actual video builder on 2026-09-19.

## Current state, checked not assumed

| Folder | PNG or JPG files present |
| --- | --- |
| `evidence/screenshots/` | **0** |
| `evidence/app-screenshots/` | **0** |

Both folders contain only markdown instructions. Nothing has been captured yet,
and nothing was fabricated to fill the gap.

## What the video builder actually consumes

`submission/video/build_video.py` looks for **six** files, not twelve. It accepts
`.png`, `.jpg` or `.jpeg`, and falls back to a placeholder slide for any that are
missing.

| Shot | Exact path the builder looks for |
| --- | --- |
| S02 | `evidence/screenshots/S02.png` |
| S04 | `evidence/screenshots/S04.png` |
| S09 | `evidence/screenshots/S09.png` |
| APP02 | `evidence/app-screenshots/APP02.png` |
| APP04 | `evidence/app-screenshots/APP04.png` |
| APP09 | `evidence/app-screenshots/APP09.png` |

The other six application screenshots are worth capturing for the submission
package even though the video does not embed them.

**Keep the two folders separate.** `evidence/screenshots/` is for authentic
Microsoft Foundry portal captures only. `evidence/app-screenshots/` is for the
local Control Center. Mixing them would blur the line between configuration that
exists in Azure and a local offline demonstration, which is the one distinction
this submission cannot afford to blur.

---

## Part 1, Microsoft Foundry portal, 3 captures

These must come from the real portal. Do not recreate them locally.

### S02, workflow designer

| | |
| --- | --- |
| **Page** | Foundry portal, your GridResolve project, Workflows, `GridResolveAIWorkflow`, designer canvas |
| **Must be visible** | The full node graph, the version selector showing **v5**, and the conditional branch. Zoom out until all 13 nodes fit. |
| **Filename** | `S02.png` |
| **Destination** | `evidence/screenshots/` |
| **Hide before capture** | Account name and email in the top right avatar menu, subscription and tenant identifiers in any breadcrumb or properties pane, and the resource group name if the portal shows it. Sign out of unrelated tabs or crop them out. |

### S04, EvidenceComplianceAgent

| | |
| --- | --- |
| **Page** | Foundry portal, Agents, `EvidenceComplianceAgent`, configuration or instructions pane |
| **Must be visible** | The agent name, version **v5**, model **gpt-5-mini**, an empty tools list, and enough of the instructions to show the approved and escalate route tokens. |
| **Filename** | `S04.png` |
| **Destination** | `evidence/screenshots/` |
| **Hide before capture** | Same as S02. The instructions pane is the point, so scroll it so the token contract is readable. |

### S09, terminal with passing tests

| | |
| --- | --- |
| **Page** | A local terminal, not the portal |
| **Must be visible** | The command and its final line. Run all three suites so one capture proves the whole local claim. |
| **Filename** | `S09.png` |
| **Destination** | `evidence/screenshots/` |
| **Hide before capture** | Nothing sensitive is printed, but check the prompt does not show a path that reveals anything you would rather not publish. |

Run this, then capture the terminal:

```bash
python tests/test_routing_and_data.py
python tests/validate_synthetic_data.py
cd control-center && npx vitest run
```

Do **not** include `verify_live_config.py` output in S09. It prints the resource
and project names, which you have kept out of the public repository.

---

## Part 2, Control Center, 9 captures

Serve the production build first:

```bash
cd control-center && npm run build
cd .. && python -m http.server 5180 --directory "control-center/dist"
```

Then open `http://localhost:5180`. Capture at a window width of at least 1440px
so the two column grids do not collapse.

Nothing in this application is sensitive. Every identifier is synthetic, no
credential is present, and it makes no network call. The only thing to hide is
your own browser chrome: bookmarks bar, other tabs, and any profile avatar.

| ID | View | Must be visible | Filename |
| --- | --- | --- | --- |
| APP01 | Overview | The case headline and the verdict, with the mode banner showing the offline label | `APP01.png` |
| **APP02** | Customer Assistant | Ask "The meter has to be broken, can you confirm it?" and capture the reply. The refusal and the escalation notice must both be readable. **Used in the video.** | `APP02.png` |
| APP03 | Billing Investigation | The $152.80 to $203.40 decomposition, showing usage as the dominant driver and the rate effect at $0.00 | `APP03.png` |
| **APP04** | Evidence Explorer | Claim **CL-4003-06** selected, showing UNSUPPORTED with an empty evidence list. **Used in the video.** | `APP04.png` |
| APP05 | Agent Workflow | The nine agent graph with the fail-closed branch and the CONFIGURED_NOT_RUN labelling | `APP05.png` |
| APP06 | Supervisor Review | The pending specialist decision, with no approval recorded | `APP06.png` |
| APP07 | Governance | The twelve controls G01 to G12 with their status pills, including G08 as PARTIALLY_VALIDATED | `APP07.png` |
| APP08 | Evaluations | The 30 prepared cases marked as not run | `APP08.png` |
| **APP09** | System Status | The cost and resource panel: 0 model calls, 0 tokens, $0.00, and the empty Foundry trace panel. **Used in the video.** | `APP09.png` |

All nine go in `evidence/app-screenshots/`.

### Optional tenth

The UI Test Fixture view is worth one capture if you want to show the honesty
labelling explicitly. It displays the `OFFLINE_DEMONSTRATION` banner and the
simulated compliance rejection. Save it as `APP10.png` if you take it. The video
does not use it.

---

## After capturing

```bash
python submission/video/build_video.py
```

The builder prints `screenshots used: N of 6`. When that reads 6 of 6, every
placeholder slide has been replaced with real evidence.
