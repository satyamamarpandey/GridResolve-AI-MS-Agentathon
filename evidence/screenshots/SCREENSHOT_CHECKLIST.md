# Screenshot Capture Checklist

**No screenshots exist yet. Claude Code has no browser automation tool in this session, so it cannot capture these. Every one requires your manual action.**

What was checked: the connected MCP server exposes `browser_act`, `browser_session_record`, `browser_cookie_use`, `browser_session_replay` and `browser_template_apply`, but no screenshot or page-capture tool. `browser_act` also requires an OpenAI-compatible LLM provider key that is not configured, so it would return degraded. No screenshot capability exists, and none is claimed.

All captures below are free. Viewing pages in the portal costs nothing. **Do not press Run, Run Workflow, Preview, or start an evaluation.**

## Setup

1. Sign in at https://ai.azure.com/nextgen with the New Foundry toggle on. Project `[your Foundry project, see GRIDRESOLVE_FOUNDRY_PROJECT]`.
2. Browser zoom 100%, window maximized.
3. Close unrelated tabs, disable notification popups.
4. Save each file as PNG into `evidence/screenshots/` with the exact ID as the filename, for example `S02.png`.

## Capture at 1920x1080, this matters

The video builder renders a 16:9 capture **full bleed at 1:1**, so a 1920x1080 screenshot keeps every pixel of its text. Anything else is resampled and the text softens.

| Capture size | Result |
|---|---|
| **1920x1080** | Pixel perfect, no resampling. Use this |
| 2560x1440 | Downscaled to 75%, still readable |
| 1600x1400 or other non-16:9 | Letterboxed to about 65%, text noticeably softer |
| 3440x1440 ultrawide | Letterboxed to about 52%, avoid |

On a higher-resolution display, capture a 1920x1080 **region** rather than the whole screen. Windows Snipping Tool, Win+Shift+S, then rectangular mode. Or set display scaling so the browser viewport is close to 1920x1080.

## Redact before saving

Blur or crop: subscription ID, tenant ID, full resource IDs, your email address, account name in the top-right avatar menu, any employer information. Check the browser tab strip and notification toasts, which is where identifiers usually leak.

## Priority 1: needed by the video

These three are wired into `build_video.py`. Save them and rerun the builder and the placeholders are replaced automatically.

| ID | Page | Must show | Proves |
|---|---|---|---|
| **S02** | Build, workflow GridResolveAIWorkflow, designer | Full v5 graph including the condition branch and both outgoing paths | Governed multi-agent orchestration with a fail-closed branch |
| **S04** | Agents, EvidenceComplianceAgent, detail | Instructions with the decision vocabulary, and the empty tools section | Independent compliance exists as a separate configured role |
| **S09** | Local terminal, not the portal | `python tests/test_routing_and_data.py` full output, comparison table plus `72 passed, 0 failed` | Static verification, and the defect quantified at 5 of 11 |

S09 is the single strongest asset in the submission. Use terminal font 16pt or larger and high contrast, and fit the comparison table and the final line in one frame.

## Priority 2: submission evidence

| ID | Page | Must show | Proves |
|---|---|---|---|
| S01 | Agents list | All nine agents with current versions, and the workflow entry | Specialist collaboration is real, not a diagram |
| S03 | CaseTriageAgent detail | Instructions and empty tool list | Typed contract, no external tools |
| S05 | Workflow YAML view | The ConditionGroup block and the `autoSend: false` lines | The gate and release control as code |
| S06 | Workflow designer, approved branch | The SendActivity node on the approved path | The approved response release point |
| S07 | Workflow designer, else branch | EscalationCoordinatorAgent on the default path | Human escalation is the default, not an afterthought |
| S08 | CaseAuditAgent detail | Output contract including `execution_status` values | Terminal auditability |
| S09b | Version dropdown | v5 listed beside v4 and earlier | Versioning and reversibility |

## Priority 3: context

| ID | Page | Must show | Proves |
|---|---|---|---|
| S10 | PolicyKnowledgeAgent detail, scrolled to the policy ledger | The synthetic policies, POL-MTR-003 visible | Policy-grounded decisions, synthetic data |
| S11 | Foundry monitoring or tracing | The empty trace list | Honest absence of runtime evidence |
| S12 | Azure Cost Management, current month | No cost reported | Cost-aware architecture, zero spend |

S11 is worth keeping precisely because it is empty. Showing it while saying the system has not been run is what makes every other claim credible.

## Note on S10, evaluation configuration

There is no evaluation definition configured in Foundry, because creating and running one costs money and was not authorized. The evaluation suite exists as `gridresolve_evaluation_suite.jsonl`, 30 cases, machine readable. If you want a visual for evaluation methodology, screenshot that file in an editor rather than the Foundry evaluation wizard, and label it as the prepared suite. Do not screenshot an empty evaluation wizard and imply it is configured.

## After capture

Run `python submission/video/build_video.py`. It reports which shots it found and which are still missing, and rebuilds the MP4.
