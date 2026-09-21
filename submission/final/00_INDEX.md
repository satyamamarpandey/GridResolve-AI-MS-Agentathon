# GridResolve AI: Judge Index

Read this page and you have the whole solution. Everything else is depth.

**If you read only one document, read `JUDGE_NARRATIVE.md`.** It explains the
problem, the architecture, the evidence, the compliance gate, the human handoff
and the business impact in plain language, with no prior knowledge of utility
billing assumed and no technical dossier required.

The single reference for every current figure is `docs/CURRENT_STATUS.md`. Where
an older document disagrees with it, that page is right.

## 1. Project summary

GridResolve AI resolves utility high-bill investigations as a governed multi-agent workflow on Microsoft Foundry. Specialists gather evidence, analyze consumption and interpret policy. A planner turns that into a claim ledger where every material claim carries the evidence and policy IDs supporting it. A communication agent drafts a plain-language answer, and that draft is withheld until an **independent compliance agent** reviews it against the evidence and policy ledgers. Anything short of explicit approval routes to a human reviewer. Whether the case itself still needs a person is a second, separate decision. Every path terminates in an audit record.

It is a **runtime-demonstrated, production-oriented multi-agent prototype**. It ran end to end in the hosted service, on synthetic data. It is not a production system.

**The differentiator:** an AI-generated customer explanation is reviewed independently against evidence and policy before an approved response is released.

## 2. Business problem

A high bill combines billing records, meter readings, consumption patterns, a customer's stated concern and policy requirements. Answering it well means reconciling all five. A single assistant answers all five at once and then approves its own answer, which under customer pressure produces a confident, unsupported explanation. In utility billing that is not a bad chat reply. It is a claim about a physical asset and about a customer's money, carrying financial, regulatory and trust risk.

## 3. Target users

| User | Uses it for |
|---|---|
| Billing resolution specialist | Investigation with provenance instead of manual record reconciliation |
| Meter operations reviewer | Triaged meter concerns with the supporting evidence attached |
| Adjustment approver | A decision card, not a transcript, before funds move |
| Compliance supervisor | Policy conflicts surfaced rather than silently resolved |
| The customer | An explanation that is accurate, plain, and never invents a cause |

## 4 to 6. Architecture, agents, workflow

`03_ARCHITECTURE.md` (diagram and flow), `04_AGENT_TEAM.md` (contracts), `05_WORKFLOW.md` (how the workflow got from v4 to v10, and why), `architecture_diagram.html` (open in a browser).

Nine agents, all `gpt-5-mini`, reasoning effort low, **zero external tools**. Workflow **v10**, sequential, fail-closed. Versions observed by the platform in the final run: CaseTriage 5, AccountEvidence 9, UsageAnomaly 4, PolicyKnowledge 6, ResolutionPlanner 6, CustomerCommunication 5, EvidenceCompliance 6, EscalationCoordinator 5, CaseAudit 7.

## 7 to 9. Governance, compliance routing, human escalation

`07_GOVERNANCE.md`, `10_HUMAN_OVERSIGHT.md`.

The release gate in the deployed v10 YAML has three terms, and all three must hold:

```
=And(<approval token: exact, once, alone on the final line, no escalation token>,
     <all six customer fields hold readable text>,
     <evidence, usage, policy and compliance outputs are each a JSON object with their key field>)
```

If the gate holds, the workflow releases a six-part readable message built from the six customer fields, then a second gate reads the planner's follow-up token and, unless it says no person is needed, hands the open case to a human. If the gate does not hold, nothing is sent and the case escalates. Escalation is the default branch. Release is the exception and must be earned.

## 10. Evaluation methodology

`11_EVALUATION_READINESS.md`. 30 cases, 15 evaluators, a weighted rubric, 16 red-team scenarios, all machine-readable and structurally validated. **No evaluation has been run and no score exists.** What has been evaluated is one case, three times, the last time against fourteen criteria written before the run.

## 11. Demonstration scenario

SYN-CASE-4003. The customer asserts a broken meter and asks the system to confirm it and adjust the charge. The evidence does not support that: both reads actual, no meter events, diagnostic PASS with no tamper or register fault, consumption genuinely up from 640 to 870 kWh, the register delta equal to the billed consumption.

It has run **three times** in Microsoft Foundry. In the final run, on workflow v10, all nine agents did their work, compliance **approved** a message that asserts no meter failure and promises no credit, the readable message was released, the open case was handed to a Billing Supervisor, and the audit had zero findings. **14 of 14** pre-registered criteria passed. See `06_RUNTIME_PROOF.md` and `docs/FINAL_RUN_RESULT_2026-09-20.md`.

## 12 to 14. Impact, roadmap, limitations

`12_BUSINESS_IMPACT.md` (primary metric: unsupported claims reaching a customer, target zero), `14_PRODUCTION_ROADMAP.md`, `13_LIMITATIONS.md`.

## 15. Screenshots

`18_SCREENSHOT_MANIFEST.md` lists every capture, what it shows and whether it still reflects the current configuration. Authentic Foundry captures and local Control Center captures are kept in separate folders.

## 16. Video

`submission/video/`. Current status, including narration, is in `20_FINAL_SUBMISSION_CHECKLIST.md`.

## 17. Control Center application

`control-center/`. A local React and TypeScript application with ten views:
Overview, Customer Assistant, Billing Investigation, Evidence Explorer, Agent
Workflow, Supervisor Review, Governance, Evaluations, System Status and UI Test
Fixture.

Status: **OFFLINE_DEMONSTRATION**. Every figure is computed by thirteen
deterministic tools rather than by a model. It makes no network call at runtime,
holds no credential, and is labelled `DETERMINISTIC OFFLINE DEMONSTRATION` on
screen so it cannot be mistaken for Foundry execution. 156 application tests pass.

Run it from the production build, which needs no dev server:

```
python -m http.server 5180 --directory "control-center/dist"
```

Screenshot checklist: `evidence/app-screenshots/APP_SCREENSHOT_CHECKLIST.md`.
These are kept separate from `evidence/screenshots/`, which holds authentic
Foundry captures only.

## 18. Research and design documents

| Document | Covers | Status |
|---|---|---|
| `docs/CURRENT_STATUS.md` | Every current figure and the claims that must not be made | Current |
| `docs/FINAL_RUN_ACCEPTANCE_PLAN.md` | The fourteen criteria, written before the final run | Fixed before the run |
| `docs/FINAL_RUN_RESULT_2026-09-20.md` | The final run judged against them, and all three runs compared | Runtime record |
| `docs/V10_CORRECTIONS_2026-09-20.md` | Why specialists stalled in runs 1 and 2, and what v10 changed | Record |
| `docs/AGENT_FRAMEWORK_MIGRATION.md` | Parallel fan-out, typed routing, bounded correction loops | PRODUCTION_TARGET |
| `docs/GRIDRESOLVE_TOOLBOX.md` | Thirteen deterministic tools as future Foundry function tools | Implemented locally, not attached to any agent |
| `docs/GUARDRAILS_MATRIX.md` | 15 failure modes, five defense layers, and what is deliberately not guarded | Mixed, labelled per control |
| `docs/AZURE_SPEECH_FREE_TIER.md` | F0 allowances and limits, verified against Microsoft docs 2026-09-19 | Researched, not provisioned |
| `docs/LOCAL_TRACE_SCHEMA.md` | OpenTelemetry-compatible spans for the local application | Implemented locally |
| `docs/FOUNDRY_LOCAL_FEASIBILITY.md` | Hardware measured, local inference declined with reasons | Documented and skipped |
| `docs/MICROSOFT_FREE_FEATURE_MATRIX.md` | What was used, what was avoided, and the substitutions made | Complete |

## Status of every claim

| Label | What it covers |
|---|---|
| **CONFIGURED** | Nine agents, workflow v10, governance gates, audit record, ledger contracts |
| **STATICALLY_VALIDATED** | Live configuration (94 read-only checks), and 1,174 local checks: 83 routing, 151 synthetic data, 156 application, 357 runner, 91 workflow engine, 198 evaluation package, 138 integration contracts, plus 105 cases on the real Power Fx engine |
| **RUNTIME_OBSERVED** | Three executions of SYN-CASE-4003. The final one, on v10, passed 14 of 14 criteria on the approve route. The fail-closed route was observed once, on v9 |
| **OFFLINE_DEMONSTRATION** | The Control Center application and its customer conversation |
| **PREPARED_ONLY** | 30 evaluation cases, 16 red-team scenarios, disabled Live Foundry adapter |
| **PRODUCTION_TARGET** | Parallel investigation, correction loops, typed routing, App Insights tracing, AI Gateway, real system adapters, identity and roles |

Not observed: the fail-closed branch on v10, the follow-up branch where no person is needed, any case other than SYN-CASE-4003, any second run of v10. One run is one sample of a non-deterministic system.

## The engineering result we are most confident about

The project found its own defects, in order, and fixed each one on evidence.

1. **Before any spend.** Reading the deployed configuration found a live web search binding on all nine agents, an audit agent unable to record a successful run, and a compliance gate that **failed open**: it tested for the word "approve" anywhere in the compliance output, and Power Fx matches regardless of case. Preparing the first run then showed the gate is handed a table of message records, not text, so that gate and its first replacement do not compile on the real Power Fx engine. The v6 gate is correct on 24 of 24 adversarial outputs.
2. **Run 1, v6.** Compliance approved, and the customer was sent an unevaluated expression instead of the message. One specialist asked for confirmation instead of working.
3. **Run 2, v9.** The hosted fail-closed route worked: nothing was sent and a person received a review package. But two specialists stalled and compliance gave a token with no reasons, so why it escalated is not established.
4. **The cause.** The platform's own record of what each agent received showed that every agent after the first was invoked with an empty input on a shared conversation, with no new user turn. v10 gives each agent an explicit input message.
5. **Final run, v10.** Nine of nine agents did their work and 14 of 14 criteria, written beforehand, passed.

Provisional Azure cost for all three runs: about **$0.13**, from returned token counts at list price. The billed amount is **not yet visible** in Azure Cost Management, which is not the same as a confirmed zero.
