# Control Center Screenshot Checklist

Date: 2026-09-19
Destination: `evidence/app-screenshots/`
Source: the local production build, served from `control-center/dist`

**These are LOCAL APPLICATION screenshots. They are not Foundry evidence.**
Keep them out of `evidence/screenshots/`, which holds authentic Microsoft Foundry
portal captures only. Mixing the two would let a local React page be read as
proof of a Foundry runtime, which is exactly the claim this project does not make.

## How to open the app

The static server is already running. Open:

```
http://localhost:5180
```

If it is not running, start it from the project root:

```
python -m http.server 5180 --directory "control-center/dist"
```

This serves the existing production build. Do not run `npm run dev` for
screenshots. The dev server costs several hundred megabytes of RAM and this
machine has been memory constrained today.

## Capture settings, apply to every shot

| Setting | Value |
| --- | --- |
| Resolution | 1920 x 1080 exactly |
| Browser zoom | 100 percent, press Ctrl+0 to reset |
| Browser chrome | Hidden. Press F11 for full screen. |
| Format | PNG |
| Case | `SYN-CASE-4003` is the only case, it loads by default. No selection needed. |
| Tool | Windows Key + Shift + S, or F11 then Print Screen |

To get exactly 1920 x 1080: set the display to 1920 x 1080, press F11 for full
screen, then capture the whole screen rather than a region. A region selection
will not be pixel exact and the video builder letterboxes anything that is not
16:9.

Before capturing, scroll each page to the top unless the shot notes say otherwise.

## The nine shots

### APP01, Overview

- Navigate: click **Overview** in the left sidebar. It is the default view.
- Scroll: top of page.
- Must be visible: the page heading, the mode banner reading
  `DETERMINISTIC OFFLINE DEMONSTRATION`, and the summary statistics row.
- Filename: `APP01_overview.png`

### APP02, Customer Assistant

- Navigate: click **Customer Assistant**.
- Action required: click the suggested question chip
  **"The meter has to be broken, can you confirm it?"** and wait for the reply.
- Must be visible: the customer question, the reply containing the phrase
  **"I cannot confirm that the meter is faulty"**, the evidence and policy pills
  beneath it, and the amber governance notice about human review.
- Also visible in the right column: the **Live Foundry (disabled)** button greyed
  out, and the voice panel showing `Azure Speech: NOT PROVISIONED`.
- Filename: `APP02_customer_assistant.png`
- This is the single most important application shot. It demonstrates refusal.

### APP03, Billing Investigation

- Navigate: click **Billing Investigation**.
- Scroll: top of page.
- Must be visible: the four statistic cards, the bill comparison bar chart, the
  consumption trend sparkline, and ideally the top of the rate decomposition
  table showing the driver breakdown.
- Filename: `APP03_billing_investigation.png`

### APP04, Evidence Explorer

- Navigate: click **Evidence Explorer**.
- Action required: click the claim row **CL-06**, the customer meter assertion.
  It is selected by default, but click it to be certain the row is highlighted.
- Must be visible: the claim ledger table with CL-06 highlighted and marked
  `UNSUPPORTED`, the selected claim panel, and the red note that the claim cites
  no evidence.
- Filename: `APP04_evidence_explorer.png`

### APP05, Agent Workflow

- Navigate: click **Agent Workflow**.
- Scroll: top of page.
- Must be visible: the sequential node list, the `ConditionGroup` box showing the
  literal condition
  `=("ROUTE_DECISION::GRIDRESOLVE_APPROVED" in Local.Var1497)`,
  and both branches including the escalation default.
- Filename: `APP05_agent_workflow.png`

### APP06, Supervisor Review

- Navigate: click **Supervisor Review**.
- Action required: click the decision **Authorize a field meter test**.
- Must be visible: the escalation package, the "what is not established" panel,
  the four reviewer roles, and the amber
  **SIMULATED DECISION, NOT APPLIED** banner that appears after selecting.
- Filename: `APP06_supervisor_review.png`
- The simulated banner must be in frame. Without it the shot could be read as a
  real approval workflow.

### APP07, Governance

- Navigate: click **Governance**.
- Scroll: enough to show the full twelve row control register.
- Must be visible: the four status count cards and the control register with the
  mixed status pills, including at least one `PREPARED_ONLY` and one
  `PRODUCTION_TARGET`.
- Filename: `APP07_governance.png`
- If all twelve rows do not fit at 1080p, capture from the register heading down
  so that G01 through G12 are all present. The count cards can be cropped out.

### APP08, Evaluations

- Navigate: click **Evaluations**.
- Scroll: top of page.
- Must be visible: the banner reading
  `LOCAL STATIC TESTS ARE EXECUTED, FOUNDRY MODEL EVALUATIONS ARE NOT`,
  the local suites table with its PASS pills, and the Foundry panel with the
  amber `NOT EXECUTED` pill.
- Filename: `APP08_evaluations.png`
- The side by side contrast is the point of this shot.

### APP09, System Status

- Navigate: click **System Status**.
- Scroll: top of page for the cost cards, then a second capture further down for
  the trace panels.
- Must be visible in the main shot: the banner
  `TOTAL AZURE SPEND ON THIS BUILD: ZERO` and the four statistic cards showing
  0 model calls, 0 tokens, $0.00.
- Filename: `APP09_system_status.png`
- Optional second shot: scroll to the two trace cards showing the populated
  `LOCAL_EXECUTION` span table beside the empty `FOUNDRY_EXECUTION` panel
  reading `NO_RUN_HAS_OCCURRED`. Save as `APP09b_traces.png`. This is a strong
  honesty shot if you have time.

## Verification after capture

Place all files in `evidence/app-screenshots/`, then tell me. I will check:

- Pixel dimensions are 1920 x 1080.
- No browser chrome, bookmarks bar or personal tabs are visible.
- No unrelated window, notification or taskbar content is in frame.
- No real identifier appears anywhere.
- The required element listed for each shot is actually present.

I cannot capture these myself. There is no browser automation in this
environment, and none will be installed.
