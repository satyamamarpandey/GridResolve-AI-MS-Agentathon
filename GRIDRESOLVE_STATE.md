# GridResolve AI State

Updated: 2026-09-20, after the final run. Deadline: 2026-09-24. Implementation
frozen. Reference for every figure: `docs/CURRENT_STATUS.md`.
Identifiers are redacted here deliberately, because this folder may be zipped for submission. Retrieve them with `az account show`.

## Azure context (VERIFIED via az CLI + Foundry API)
- Account: [REDACTED user principal], tenant [REDACTED], subscription [REDACTED], Pay-As-You-Go, spending limit off
- Foundry resource: [FOUNDRY_RESOURCE_REDACTED], AIServices S0, westus3, RG [REDACTED]
- Project: [FOUNDRY_PROJECT_REDACTED]
- Deployments: gpt-5-mini 2025-08-07 GlobalStandard cap 50; text-embedding-3-large v1 Standard cap 120. The embedding deployment has never been called.
- Foundry agents API is fully readable and writable from the CLI token. Workflow writes need header `Foundry-Features: WorkflowAgents=V1Preview`.
- Local Azure CLI setting changed: `core.enable_broker_on_windows=false` (needed for browser login)

## Current deployed state (VERIFIED 2026-09-20, read-only, 94 of 94 checks)
Workflow: **GridResolveAIWorkflow v10**. Earlier versions retained.
Agents, all gpt-5-mini, reasoning effort low, **zero tools**:
Triage v5, AccountEvidence v9, UsageAnomaly v4, PolicyKnowledge v6, ResolutionPlanner v6, CustomerCommunication v5, EvidenceCompliance v6, EscalationCoordinator v5, CaseAudit v7.
Strict json_schema output on AccountEvidence, PolicyKnowledge, CustomerCommunication and CaseAudit.
Agent names resolve to the latest version, so any edit goes live immediately. Do not edit anything. The configuration is frozen.

## What was corrected, in order (all control plane only, no model call)
- v4 to v5: web_search removed from all nine agents, sentinel approval token, escalation as the default branch, release by SendActivity only.
- v5 to v6: the gate reads `Last(Local.Var1497).Text`. The v4 and v5 conditions do not compile on the real Power Fx engine against a table of messages. AccountEvidenceAgent v7 no longer contains the answer to the demonstration case. `docs/CORRECTION_2026-09-20.md`.
- v6 to v8, after run 1: release is a template and not an expression, six customer fields released instead of the whole JSON, a separate follow-up gate from the planner's token, unattended-invocation wording. `docs/FIRST_RUN_AND_CORRECTIONS_2026-09-20.md`.
- v9: whitespace-only customer fields are withheld.
- v10, after run 2: every agent node passes an explicit input message, a third gate term withholds the message when an investigation output is not a JSON object, strict schemas on evidence, policy and audit, compliance must give reasons, audit cross-checks in the runner. `docs/V10_CORRECTIONS_2026-09-20.md`.

## Runtime status
Three genuine executions of SYN-CASE-4003 on 2026-09-20: v6, v9, v10. The final
run passed 14 of 14 pre-registered criteria: nine of nine agents did their work,
22-entry evidence ledger, nine policies, compliance approved with reasons, a
readable message was released, human follow-up ran separately, audit had zero
findings. Compliance did not reject the final message. Run 2 took the hosted
fail-closed branch with no stated reason. Evidence: `evidence/runtime/`, three
folders, never modified. Record: `docs/FINAL_RUN_RESULT_2026-09-20.md`.
No further execution is planned or authorized.

## Verification status
Local, no model: 83 routing, 151 synthetic data, 156 application, 357 runner, 91 workflow engine, 198 evaluation package, 138 integration contracts, total 1,174. Plus 105 cases on the real Power Fx engine. Plus 94 read-only live configuration checks. Mutation testing of the runner: 80 of 80 caught.

## Cost
Provisional from returned tokens at list price: $0.0334 + $0.0292 + $0.0685, about $0.13. Billed amount not yet visible: Cost Management and consumption usage returned zero rows after the final run. That is not a confirmed $0.00. Billing lags. Zero embeddings, evaluations or new resources.

## Video
`submission/video/GridResolve_Final_Video.mp4` is the final narrated video, finished 2026-09-21: 172.1 seconds, my own recorded narration, authentic redacted Foundry captures. The older silent draft is not part of the published repository. The narration recording itself stays out of the repository.

## Browser automation
NOT AVAILABLE for the Foundry portal, which needs interactive sign-in. Portal screenshots require manual capture by the owner.

## Blockers
1. **Narration audio.** Not recorded.
2. **Two Foundry portal captures of v10**, `F10-WORKFLOW.png` and `F10-COMPLIANCE.png`. The existing Foundry captures show v5 and are unused. The Control Center captures were retaken and are current.
3. **Owner approval** to commit, push and submit. Nothing is committed.
4. **No evaluation scores.** The 30 cases and 16 probes are prepared and not executed. No spend is authorized.
