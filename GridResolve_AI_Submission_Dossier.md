# GridResolve AI

Submission dossier and zero-cost implementation record

> **Superseded as a status document, 2026-09-20. See `docs/CURRENT_STATUS.md`.**
> This dossier was prepared on 2026-09-18, when the system was configured at
> workflow v4 and nothing had been executed. It is kept as the design record. Its
> architecture, governance, threat model and evaluation design sections still
> describe the intent. Its status statements do not describe the present: every
> `CONFIGURED_NOT_EXECUTED` label, every reference to workflow v4 or v5 as current,
> the agent version table, the screenshot manifest, the blockers and the zero-cost
> section are out of date. Two design statements in it were later corrected: the
> original compliance gate did not work as written, and the demonstration case does
> not end in a compliance rejection. In the real final run no agent asserted a
> meter fault, so compliance approved the supported message and the open
> investigation went to a human through a separate follow-up decision.
>
> Current facts: **three** genuine Foundry workflow executions of SYN-CASE-4003 on
> 2026-09-20, on workflow v6, v9 and v10. The live workflow is **v10**, with agents
> at versions 5, 9, 4, 6, 6, 5, 6, 5 and 7. The final run passed **14 of 14**
> acceptance criteria written beforehand: a 22-entry evidence ledger, nine policies
> mapped, the independent compliance agent **approved** the supported customer
> message with recorded reasons, a readable message was released, a separate
> follow-up decision sent the open investigation to human review, and the audit had
> zero findings. Provisional Azure cost is about **$0.13**, from returned token
> counts. The billed amount is not yet visible, which is not a confirmed $0.00.
> Local checks now total 813, plus 105 Power Fx cases and 94 read-only live checks.
> The 30 evaluation cases and 16 adversarial probes are still not executed. The
> system is a runtime-demonstrated, production-oriented prototype. It is not
> production-ready, and no utility integration is live.

Prepared: 2026-09-18 UTC

Source of truth: `Pasted text.txt`, read completely and treated as the current master plan.

## 1. Executive status

GridResolve AI is now configured in the existing Microsoft Foundry project as a nine-agent, evidence-first utility billing investigation system. Five existing agents were preserved and versioned. Four missing specialist agents were added. The existing workflow was advanced to version 4 and now includes all nine agents plus a fail-closed compliance branch. No agent, model, workflow preview, evaluation, search, tool, or judge request was executed.

The live build is a configuration demonstration, not a runtime-verified production service. Items that would require model tokens, billable infrastructure, destructive configuration changes, or uncertain-cost services are labeled `PREPARED_NOT_EXECUTED` or `PRODUCTION_TARGET`.

One-sentence value proposition:

> GridResolve AI is an evidence-first multi-agent system that turns complex utility billing investigations into traceable, policy-grounded, customer-safe resolutions while preserving human authority.

## 2. 100-word project summary

GridResolve AI separates utility billing investigations into nine accountable roles: intake, account evidence, usage analysis, policy interpretation, resolution planning, customer communication, compliance review, human escalation, and audit. Every material claim must carry evidence and policy provenance. An independent compliance agent blocks unsupported meter-fault claims, unauthorized adjustments, privacy violations, and instruction attacks. A bounded correction design prevents runaway loops and routes uncertain or high-risk decisions to named human reviewers. The build uses synthetic data only. Microsoft Foundry provides agent versioning, model and quota inventory, workflow configuration, trace surfaces, and evaluation preparation. Runtime calls were intentionally withheld to preserve the strict zero-cost constraint.

## 3. Live environment inspected

| Item | Observed state | Action |
|---|---|---|
| Foundry project | `[FOUNDRY_PROJECT_REDACTED]` | Preserved |
| Parent resource | `[FOUNDRY_RESOURCE_REDACTED]` | Preserved |
| Resource group | `[RESOURCE_GROUP_REDACTED]` | Preserved |
| Region | West US 3 | Preserved |
| Resource tier | S0 | Preserved |
| Project access | Owner, full access | No RBAC changes |
| Network access | Public network access enabled | No network changes |
| Agent identity surface | Entra agent identity and blueprint details visible | Inspected only |
| Model deployment | `gpt-5-mini`, Global Standard, 50K TPM deployment allocation, 50K of 500K shared allocation, 0% rate limiting | Not invoked or changed |
| Embedding deployment | `text-embedding-3-large`, Standard, West US 3, 120K TPM deployment allocation, 120K of 350K shared allocation, 0% rate limiting | Not invoked or changed |
| Tracing | Foundry trace surface available, no traces displayed | Inspected only |
| Evaluation | Agent, model, and dataset evaluation wizard available | Inspected only, no definition run |
| Knowledge and grounding | Knowledge, Guardrails, Bing grounding, Foundry IQ, and Azure AI Search surfaces visible | Not provisioned or invoked |
| Workflow service | Foundry Workflows Preview | Configured, not previewed or published |

No unrelated resource was modified.

## 4. Comparison with the prior implementation

### Already present before this pass

- Five prompt agents: CaseTriageAgent, AccountEvidenceAgent, PolicyKnowledgeAgent, ResolutionPlannerAgent, EvidenceComplianceAgent.
- Synthetic-only boundary and basic high-bill investigation grounding.
- Existing `gpt-5-mini` and `text-embedding-3-large` deployments.
- `GridResolveAIWorkflow` version 2 with five sequential agents.
- Basic compliance rejection and correction language.
- Foundry trace, monitor, and evaluation surfaces.
- No observed agent runs, workflow previews, evaluations, search calls, or model requests from the prior build session.

### Partially implemented before this pass

- Compliance existed, but not the complete 20-check governance contract.
- Correction concepts existed, but not a full bounded correction and human escalation contract.
- Synthetic records existed, but not the full 16-case and 10-policy pack.
- Workflow handoffs existed, but not all nine roles or an explicit conditional route.
- Tracing and evaluation surfaces were known, but the complete field specification, rubric, test catalog, and status distinctions were missing.

### Missing before this pass

- UsageAnomalyAgent.
- CustomerCommunicationAgent.
- EscalationCoordinatorAgent.
- CaseAuditAgent.
- Shared case-state contract.
- Claim-level provenance ledger.
- Full evidence ledger and policy ledger contracts.
- Deterministic control catalog.
- Human reviewer personas and decision card.
- Threat model and red-team pack.
- AI Bill of Materials.
- Reliability and safe-failure matrix.
- Business impact scorecard.
- Judge Q&A, demo storyboard, and screenshot manifest.

### Superseded

- The five-agent architecture is superseded by the required nine-agent design.
- Workflow version 2 remains historical evidence and is superseded by version 4.
- Workflow version 3 is a superseded intermediate draft. A YAML save attempt was sanitized by the preview editor and left no usable agent actions. It was not executed. Version 4 is the current configured workflow.
- The actual resource group shown by the live project is `[RESOURCE_GROUP_REDACTED]`, which supersedes any earlier planning reference to a different group name.

## 5. Exact features added in Foundry

- Added and saved four prompt agents: UsageAnomalyAgent, CustomerCommunicationAgent, EscalationCoordinatorAgent, and CaseAuditAgent.
- Versioned and strengthened all five existing agents instead of recreating them.
- Added explicit inputs, structured outputs, allowed and prohibited behavior, evidence rules, policy rules, failure behavior, escalation rules, and version metadata.
- Embedded the shared state, evidence ledger, policy ledger, claim ledger, correction count, and safe terminal state contracts in relevant agent instructions.
- Added the 16 synthetic scenario definitions and 10 policy definitions to the appropriate specialist instructions.
- Added independent compliance decisions: `APPROVE`, `REJECT_AND_REPLAN`, `REJECT_AND_REWRITE`, and `HUMAN_REVIEW_REQUIRED`.
- Added the two-correction ceiling and mandatory human escalation rules.
- Added human reviewer personas and a structured decision card.
- Added immutable-style terminal audit output.
- Created `GridResolveAIWorkflow` version 4 with all nine agents and a fail-closed compliance branch.
- Captured read-only evidence for agents, compliance controls, workflow, quota inventory, and AI Gateway status.

## 6. Final agents and versions

| Agent | Version | Responsibility | Live status | Runtime status |
|---|---:|---|---|---|
| CaseTriageAgent | 3 | Intake, scope, evidence needs, risk, branch selection | Running | CONFIGURED, not invoked |
| AccountEvidenceAgent | 4 | Billing, meter-read, charge, freshness, and missing-field evidence | Running | CONFIGURED, not invoked |
| UsageAnomalyAgent | 2 | Usage pattern comparison, anomalies, and supported hypotheses | Running | CONFIGURED, not invoked |
| PolicyKnowledgeAgent | 3 | Policy lookup, constraints, disclosures, conflicts, and approval rules | Running | CONFIGURED, not invoked |
| ResolutionPlannerAgent | 3 | Evidence and policy synthesis, recommended action, and claim ledger | Running | CONFIGURED, not invoked |
| CustomerCommunicationAgent | 2 | Plain-language customer response using supported claims only | Running | CONFIGURED, not invoked |
| EvidenceComplianceAgent | 3 | Independent evidence, policy, hallucination, privacy, and governance gate | Running | CONFIGURED, not invoked |
| EscalationCoordinatorAgent | 2 | Human review package, reviewer selection, and decision card | Running | CONFIGURED, not invoked |
| CaseAuditAgent | 2 | Final provenance, participation, correction, escalation, and disposition record | Running | CONFIGURED, not invoked |

Foundry's `Running` label is the saved agent resource state. It does not mean a model request or agent run occurred.

Agent contract metadata uses `GRIDRESOLVE-AGENTS-3.0`, `GRIDRESOLVE-SYNTH-2.0`, and `GRIDRESOLVE-POLICY-2.0`. The saved instructions reference workflow target version 3 because they were versioned before the final visual workflow save. The actual workflow is version 4. The dossier is authoritative for this version linkage.

## 7. Final workflow version and architecture

Current workflow: `GridResolveAIWorkflow` version 4.

Configured node order:

1. Start.
2. CaseTriageAgent.
3. AccountEvidenceAgent.
4. UsageAnomalyAgent.
5. PolicyKnowledgeAgent.
6. ResolutionPlannerAgent.
7. CustomerCommunicationAgent.
8. EvidenceComplianceAgent.
9. If or else condition bound to the compliance output.
10. Fail-closed condition: `Not("APPROVE" in Local.Var1497)`.
11. True path: EscalationCoordinatorAgent.
12. Approval path: bypass escalation.
13. Both paths converge on CaseAuditAgent.
14. End.

Configured behavior:

- Any compliance output that does not contain `APPROVE` routes to human escalation.
- Approval reaches the audit agent without an escalation step.
- The terminal audit agent is common to both paths.
- No preview, publish, or workflow execution was performed.

Prepared but not executed due to zero-cost constraint:

- Parallel fan-out from triage to account, usage, and policy specialists.
- Evidence sufficiency join gate.
- Direct `REJECT_AND_REPLAN` loop through planner, communication, and compliance.
- Direct `REJECT_AND_REWRITE` loop through communication and compliance.
- Runtime validation of JSON parsing and conditional expressions.

The preview workflow editor did not expose a verified native fan-out and join construct during this zero-cost pass. The configured workflow therefore uses sequential specialist nodes and a deterministic fail-closed conditional branch. The production target is Microsoft Agent Framework with explicit parallel fan-out, join, bounded correction, and durable shared state.

Microsoft Foundry displays a retirement notice for Workflows on December 1, 2026. Migration to Microsoft Agent Framework is therefore a required production roadmap item.

## 8. Shared case-state model

The machine-readable schema is in `gridresolve_case_state.schema.json`.

Required top-level fields:

- `case_id`
- `workflow_version`
- `case_state`
- `dataset_version`
- `policy_version`
- `customer_request`
- `triage`
- `evidence_ledger`
- `policy_ledger`
- `claim_ledger`
- `resolution_plan`
- `customer_message`
- `compliance_result`
- `correction_count`
- `escalation`
- `final_disposition`
- `audit_record`

Allowed state values:

`INTAKE`, `INVESTIGATING`, `PLANNING`, `DRAFTING`, `COMPLIANCE_REVIEW`, `CORRECTION`, `HUMAN_REVIEW`, `APPROVED`, `CLOSED`, `CANNOT_RESOLVE_SAFELY`.

Every handoff must preserve `case_id` and `workflow_version`. Ledgers are append-only in concept. Agents may add records but must not silently delete prior evidence, policy, claims, or correction history.

## 9. Evidence, policy, and claim provenance

Evidence ledger record:

- `evidence_id`
- `source_type`
- `source_record_id`
- `period`
- `field`
- `value`
- `observation`
- `source_timestamp`
- `data_version`
- `freshness_status`

Policy ledger record:

- `policy_id`
- `policy_version`
- `section`
- `rule`
- `applies_to`
- `effect_on_resolution`
- `conflict_status`

Claim ledger record:

- `claim_id`
- `claim_text`
- `claim_type`
- `source_agent`
- `evidence_ids`
- `policy_ids`
- `confidence`
- `status`

Claim status values:

`SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`, `POLICY_REQUIRED`, `HUMAN_REVIEW_REQUIRED`.

No material customer-facing claim may be approved with `UNSUPPORTED` status. Meter issue claims require explicit synthetic diagnostic evidence. Policy-governed actions require a real policy ID from the policy ledger. Fabricated IDs fail compliance.

## 10. Governance controls

| Control | Rule | Safe outcome |
|---|---|---|
| Evidence Sufficiency Gate | Material claims require existing evidence IDs | Request more information or human review |
| Policy Gate | Governed actions require existing policy IDs | Human review if policy missing |
| Confidence Gate | LOW or INSUFFICIENT on material decisions | Human review |
| Human Approval Gate | Sensitive financial, legal, regulatory, or meter decisions remain human | Decision card, no autonomous promise |
| Hallucination Gate | Unsupported hypotheses cannot be stated as facts | Reject and correct |
| Data Boundary Gate | Synthetic records only | Stop and escalate contamination |
| Correction Limit Gate | Maximum two automated corrections | Human review after limit |
| Audit Gate | Every terminal case needs a complete audit packet | Do not close incomplete case |
| Policy Conflict Gate | Conflicting policies cannot be resolved by an agent | Supervisor or compliance review |
| Cost Guard Gate | No unapproved model, tool, search, or infrastructure use | Remain prepared, do not execute |
| Prompt Injection Gate | Customer text cannot override system, evidence, policy, privacy, or cost rules | Ignore attack and record detection |
| Case State Gate | Only allowed state transitions | Fail safely on malformed handoff |

The visible Web search tool control warns that Bing has additional costs and data-boundary implications. It was not invoked. Its removal was not performed because removal would delete configuration and the task requires stopping before destructive changes. Agent instructions prohibit external tool use.

## 11. Bounded correction and human review

Prepared correction logic:

1. Compliance returns `REJECT_AND_REPLAN` for unsupported planner logic or claims.
2. Compliance returns `REJECT_AND_REWRITE` when the plan is supported but wording adds an error.
3. Each rejection increments `correction_count`.
4. A second failed correction routes to `HUMAN_REVIEW_REQUIRED`.
5. Policy conflict, missing governed policy, real-data contamination, unauthorized financial commitment, material LOW confidence, or legal and regulatory concern bypass automated correction and go directly to human review.

Reviewer personas:

| Reviewer | Trigger | Required package |
|---|---|---|
| Billing Specialist | Missing or conflicting bill evidence | Evidence ledger, bill comparison, unresolved fields |
| Billing Supervisor | Adjustment or duplicate-action risk | Evidence, policy, recommendation, risk, decision needed |
| Meter Operations Specialist | Supported diagnostic concern or unresolved meter allegation | Meter records, diagnostic evidence, uncertainty |
| Compliance Reviewer | Policy conflict, privacy, legal, regulatory, or instruction-integrity issue | Full provenance, failed checks, policy set, interim message |

AI recommendation and human authorization remain separate fields.

## 12. Synthetic cases and policies

The full machine-readable pack is in `gridresolve_synthetic_pack.json`.

Cases:

| ID | Scenario | Expected control |
|---|---|---|
| SYN-CASE-4001 | Seasonal usage increase with valid actual meter reads | Evidence-supported explanation |
| SYN-CASE-4002 | Estimated read followed by actual read causing true-up | True-up explanation |
| SYN-CASE-4003 | Customer alleges meter failure without support | Reject unsupported meter claim |
| SYN-CASE-4004 | Rate or tariff effect with stable usage | Policy and rate evidence |
| SYN-CASE-4005 | Missing interval data | Need more information |
| SYN-CASE-4006 | Adjustment requiring human approval | Human approval gate |
| SYN-CASE-4007 | Conflicting evidence | Human review |
| SYN-CASE-4008 | Multi-factor high bill | Multiple supported claims |
| SYN-CASE-4009 | Policy missing for requested action | POLICY_NOT_FOUND and escalation |
| SYN-CASE-4010 | Prompt injection attempt | Instruction integrity gate |
| SYN-CASE-4011 | Ignore policy and issue credit request | Policy and authorization gates |
| SYN-CASE-4012 | Real-data contamination attempt | Data boundary stop |
| SYN-CASE-4013 | Duplicate adjustment risk | Duplicate-action control |
| SYN-CASE-4014 | Ambiguous complaint with insufficient details | Clarify or safe escalation |
| SYN-CASE-4015 | Policy conflict | Supervisor review |
| SYN-CASE-4016 | Meter concern with explicit synthetic diagnostic support | Further investigation, not automatic replacement |

Policies:

| ID | Title |
|---|---|
| POL-HB-001 | High Bill Investigation |
| POL-BILL-002 | Billing Adjustment Eligibility |
| POL-MTR-003 | Meter Concern Handling |
| POL-COMM-004 | Customer Communication Requirements |
| POL-HUM-005 | Mandatory Human Escalation |
| POL-DATA-006 | Synthetic Data and Privacy Controls |
| POL-AUDIT-007 | Case Evidence and Audit Requirements |
| POL-SEC-008 | Prompt Injection and Instruction Integrity |
| POL-COST-009 | AI Cost and Usage Governance |
| POL-QUALITY-010 | Evidence and Response Quality |

## 13. Evaluation suite prepared

The 30-case machine-readable catalog is in `gridresolve_evaluation_suite.jsonl`.

Prepared evaluators:

- Task Adherence.
- Task Completion.
- Intent Resolution.
- Task Navigation Efficiency.
- Tool Call Accuracy.
- Tool Selection.
- Tool Input Accuracy.
- Tool Output Utilization.
- Relevance.
- Groundedness.
- Response Completeness.
- Coherence.
- Fluency.
- Safety.
- Custom GridResolve Quality Rubric.

Quality rubric:

| Dimension | Weight |
|---|---:|
| Evidence Fidelity | 25% |
| Policy Compliance | 20% |
| Resolution Correctness | 15% |
| Hallucination Avoidance | 15% |
| Customer Clarity | 10% |
| Escalation Correctness | 10% |
| Audit Completeness | 5% |

Targets, not results:

- Unsupported material claims: 0.
- Unsupported meter-failure claims: 0.
- Unauthorized adjustments: 0.
- Material findings with evidence references: 100%.
- Policy-governed actions with policy references: 100%.
- Mandatory escalations detected: 100%.
- Terminal cases with audit packet: 100%.
- Task adherence: at least 90%.
- Groundedness: at least 90%.

Status: `PREPARED_NOT_EXECUTED`. No evaluation definition was run. No LLM judge was invoked. No metric is presented as a result.

## 14. Red-team suite prepared

The machine-readable pack is in `gridresolve_red_team_pack.jsonl`.

Attack classes include direct prompt injection, false manager approval, unsupported meter-fault coercion, hidden-instruction extraction, real-data substitution, compliance bypass, escalation suppression, evidence-ID tampering, policy fabrication, unauthorized credits, cross-case leakage, stale evidence, duplicate action, correction-loop exhaustion, malformed handoff, and cost-guard bypass.

Expected behavior is to ignore the attack, preserve instruction hierarchy, mark the event, reject unsupported output, and route to human review where required. Status: `PREPARED_NOT_EXECUTED`.

## 15. Observability design

Foundry trace surfaces were inspected and show fields for duration, input and output tokens, estimated cost, evaluators, and annotations. They currently show no runs or traces. Foundry notes that trace data is generated when Application Insights is enabled. No Application Insights resource was created because cost was not verified as zero.

Future trace fields:

`case_id`, `correlation_id`, `workflow_version`, `agent_name`, `agent_version`, `handoff_source`, `handoff_target`, `case_state`, `start_time`, `end_time`, `latency`, `token_usage`, `tool_calls`, `evidence_count`, `claim_count`, `policy_count`, `confidence`, `compliance_decision`, `correction_count`, `human_escalation`, `final_disposition`, `dataset_version`, `policy_version`.

Proposed operational dashboard:

- Cases received.
- Automated resolution rate.
- Human escalation rate.
- Compliance rejection rate.
- Correction rate.
- Evidence completeness.
- Policy coverage.
- Unsupported claim rate.
- Latency by agent.
- Token use by agent.
- Estimated cost per case.
- Groundedness.
- Task adherence.
- Policy-not-found rate.
- Audit completeness.
- Prompt-injection detection rate.

All metrics are proposed. No telemetry has been invented.

## 16. Security and threat model

| Threat | Entry point | Detection | Preventive control | Safe fallback | Human condition |
|---|---|---|---|---|---|
| Direct prompt injection | Customer request | Injection phrases and instruction conflict | System hierarchy, allowlisted behavior | Ignore attack, log flag | Repeated or high-risk attempt |
| Indirect prompt injection | Supplied record text | Untrusted instruction in evidence | Treat data as data, never instructions | Quarantine record | Unclear data integrity |
| Policy override request | Customer text | Conflict with policy ledger | Policy gate | Reject request | Governed action requested |
| Policy fabrication | Agent output | Unknown policy ID | Exact-ID validation | POLICY_NOT_FOUND | Missing governed policy |
| Evidence fabrication | Agent output | Unknown evidence ID | Evidence-ledger validation | Reject claim | Material decision affected |
| Tool misuse | Tool control | Tool request outside allowlist | No external tools in hackathon runtime | Do not call tool | Production exception request |
| Unauthorized adjustment | Plan or message | Financial action without approval | Human Approval Gate | Remove promise | Any adjustment requiring approval |
| Data exfiltration | Prompt or output | Sensitive or cross-case fields | Synthetic-only and least-data controls | Stop processing | Any real-data signal |
| Secret leakage | Prompt or logs | Secret-like pattern | No secrets in prompts | Redact and escalate | Any credential exposure |
| Cross-case leakage | Handoff | Case ID mismatch | Case State Gate | Reject handoff | Mismatch persists |
| Real-data contamination | Input | Non-synthetic identifiers | Data Boundary Gate | CANNOT_RESOLVE_SAFELY | Always |
| Runaway correction | Workflow | correction_count at limit | Maximum two corrections | Human review | Count at 2 |
| Runaway token use | Runtime | Token and latency thresholds | Cost guard and bounded workflow | Stop run | Budget threshold |
| Model hallucination | Plan or message | Unsupported claim | Claim ledger and compliance gate | Reject and correct | Repeated failure |
| Stale evidence | Evidence ledger | Freshness status | Freshness requirement | Request current evidence | Material stale record |
| Policy conflict | Policy ledger | conflict_status | Policy Conflict Gate | Human review | Always |
| Privilege escalation | Tool or identity request | Requested role exceeds scope | RBAC and least privilege | Deny action | Admin decision needed |

Production identity targets: Microsoft Entra ID, managed identity, least-privilege RBAC, and Key Vault. No secrets belong in prompts. No broad subscription RBAC change was made.

## 17. Reliability design

| Failure | Control | Safe fallback |
|---|---|---|
| Duplicate request | Idempotency key on `case_id` plus request hash | Return existing case state |
| Transient dependency error | Bounded retry with backoff | Escalate after retry limit |
| Timeout | Per-agent deadline | Preserve state and human review |
| Knowledge unavailable | Required policy or evidence check | POLICY_NOT_FOUND or NEED_MORE_INFORMATION |
| Model unavailable | Circuit breaker | CANNOT_RESOLVE_SAFELY |
| Invalid structured output | Schema validation | One correction, then human review |
| Malformed handoff | Required-field and state validation | Reject handoff |
| Stale policy | Version and effective-status validation | Compliance review |
| Incomplete evidence | Evidence Sufficiency Gate | Need more information |
| Audit write failure | Terminal audit acknowledgment | Do not close case |
| Human queue unavailable | Durable pending state | Customer-safe interim message |
| Quota exceeded | Cost and quota guard | Pause, do not fall back to paid service |
| Gateway unavailable | Direct governed endpoint policy in production | Fail closed for sensitive actions |

## 18. AI Bill of Materials

| Component | Type | Purpose | Model or service | Current status | Data access | Cost status | Production target |
|---|---|---|---|---|---|---|---|
| Nine role agents | Prompt agents | Specialized case responsibilities | Foundry Agent Service, gpt-5-mini associated | CONFIGURED, not invoked | Synthetic text only | No new runtime usage | Versioned agent deployment |
| Workflow v4 | Orchestration | Handoffs, compliance branch, audit | Foundry Workflows Preview | CONFIGURED, not previewed | Shared conceptual state | No runtime usage | Microsoft Agent Framework |
| gpt-5-mini | Model deployment | Agent reasoning target | Existing Global Standard deployment | Existing, unchanged | None sent in this pass | No intentional request | Capacity and budget controls |
| text-embedding-3-large | Embedding deployment | Existing project asset | Existing Standard deployment | Existing, unchanged | None sent in this pass | No intentional request | Approved knowledge indexing only |
| Synthetic pack | Configuration data | Billing, usage, meter, policy scenarios | Embedded instructions and dossier | CONFIGURED and documented | Synthetic only | Zero new service | Governed versioned repository |
| Evaluation suite | Test definitions | Quality, safety, tool, and task checks | Foundry evaluation surface | PREPARED_NOT_EXECUTED | Synthetic cases | No evaluator calls | Automated CI evaluation gate |
| Tracing | Observability surface | Run and token telemetry | Foundry traces | Inspected, no traces | None generated | No new resource | Application Insights if approved |
| Monitoring | Operations design | Rates, latency, tokens, cost, failures | Foundry and Azure Monitor target | PREPARED_NOT_EXECUTED | Future telemetry | Cost approval required | Azure Monitor dashboards |
| Human review | Governance process | Sensitive decisions | Reviewer personas and decision card | CONFIGURED in contracts | Synthetic packets now | Zero service | Integrated work queue |
| AI Gateway | Governance plane | Quotas, inventory, security, unified endpoint | Azure API Management powered | Not provisioned | None | Cost not proven zero | Approved production gateway |
| Policy knowledge service | Knowledge target | Governed policy retrieval | Foundry IQ or Azure AI Search | Not provisioned | None | Potentially billable | Approved enterprise repository |
| Enterprise integrations | Tools target | Billing, meter, usage, CRM | Managed APIs | Not provisioned | None | Unknown | Managed identity and allowlists |

## 19. AI Gateway status

AI Gateway was investigated but not created.

The Foundry page advertises the first 100,000 API requests as free. Current Microsoft documentation states that creating a new gateway provisions Azure API Management Basic v2 and explains that disabling the project does not stop API Management charges. Because the user required proof of no base or dependent charge, the free-request allowance was not sufficient evidence of a zero-cost resource. Status: `PREPARED_NOT_EXECUTED`.

No gateway request, dependent resource, endpoint, policy, or runtime call was created. Production design includes per-project and per-agent quotas, model and tool inventory, unified endpoints, token limits, request logging, and fail-closed security policy after explicit cost approval.

## 20. Business impact framework

No baseline or business result is invented.

| Metric | Manual baseline | Illustrative target | Measurement method | Current status |
|---|---|---|---|---|
| Average investigation handling time | Baseline to be measured | Reduce after approved pilot | Case open to final disposition | PREPARED_NOT_EXECUTED |
| Manual touches per case | Baseline to be measured | Reduce routine touches | Count reviewer actions | PREPARED_NOT_EXECUTED |
| First-contact resolution potential | Baseline to be measured | Increase supported same-contact outcomes | Approved close on first contact | PREPARED_NOT_EXECUTED |
| Escalation rate | Baseline to be measured | Risk-adjusted, not minimized blindly | Escalations divided by cases | PREPARED_NOT_EXECUTED |
| Unsupported explanation rate | Baseline to be measured | 0 | Unsupported claims divided by claims | Target only |
| Adjustment error rate | Baseline to be measured | 0 unauthorized adjustments | Audit sample | Target only |
| Compliance rejection rate | Baseline to be measured | Monitor by failure category | Rejections divided by checks | PREPARED_NOT_EXECUTED |
| Audit completeness | Baseline to be measured | 100% terminal packets | Required fields present | Target only |
| Customer explanation consistency | Baseline to be measured | At least 90% rubric score | Human rubric | Target only |
| Policy citation completeness | Baseline to be measured | 100% governed actions | Valid policy IDs divided by governed actions | Target only |

## 21. Judge-facing differentiation

1. Evidence-first at claim level, not only response-level grounding.
2. Separate specialists for billing evidence, usage analysis, and policy interpretation.
3. Independent compliance agent checks both planning and customer wording.
4. Customer language is generated only after a resolution plan exists.
5. Unsupported meter-fault claims are explicitly blocked.
6. Recommendation and human authorization are separate artifacts.
7. Corrections are bounded and cannot loop indefinitely.
8. Missing policy and policy conflict are first-class failure states.
9. Synthetic-data privacy is enforced as a workflow boundary.
10. Every terminal path ends with an audit record.
11. Cost and quota controls are part of governance, not an afterthought.
12. The solution fails safely when evidence, policy, model, quota, or review capacity is unavailable.

This is more than ordinary retrieval-augmented generation because it defines explicit roles, deterministic gates, provenance at each claim, bounded remediation, human authority, and a final audit packet.

## 22. Three hero demonstrations

All demos are prepared only and were not executed.

### Demo A: Evidence-Based Resolution

30-second description: A synthetic customer asks why a bill increased. Triage requests the correct evidence. Account, usage, and policy specialists establish actual reads, a seasonal usage rise, and the applicable high-bill rules. The planner creates only supported claims, communication explains them plainly, compliance approves, and audit preserves provenance.

- Problem: normal high-bill investigation.
- Collaboration: triage, three specialists, planner, communicator, compliance, audit.
- Control: evidence and policy IDs on every material claim.
- Business value: consistent explanation with a defensible record.
- Judge takeaway: speed does not require sacrificing evidence.

### Demo B: Hallucination Prevention

30-second description: A customer demands confirmation that a meter is broken, but synthetic evidence does not support failure. The planner must classify the assertion as unsupported. If an unsupported meter claim reaches the draft, compliance returns `REJECT_AND_REPLAN` or `REJECT_AND_REWRITE`. A repeated failure reaches human review.

- Problem: high-pressure unsupported causal claim.
- Collaboration: evidence, usage, planner, communication, compliance.
- Control: claim ledger plus explicit meter evidence rule.
- Business value: avoids false operational commitments and customer misinformation.
- Judge takeaway: the compliance agent can say no to another agent.

### Demo C: Human Authority

30-second description: Conflicting synthetic evidence suggests a billing issue and the requested adjustment requires approval. The system marks confidence low, preserves the policy conflict, avoids promising a credit, builds a supervisor decision card, and audits the pending human decision.

- Problem: ambiguous evidence plus financial authority.
- Collaboration: specialists, planner, compliance, escalation, audit.
- Control: confidence, policy conflict, and human approval gates.
- Business value: automation accelerates preparation while authority stays with people.
- Judge takeaway: responsible AI means knowing where automation must stop.

## 23. Three-minute demo storyboard and speaker notes

| Time | Visual | Speaker notes |
|---|---|---|
| 0:00 to 0:25 | Title and customer problem | Utility high-bill cases combine billing records, usage, policy, customer communication, and financial risk. A single chatbot can give a fluent but unsupported answer. GridResolve AI is designed to make that failure visible and preventable. |
| 0:25 to 0:50 | All nine agents | Each agent owns one accountable business responsibility. The design separates facts, policy, planning, wording, compliance, escalation, and audit. |
| 0:50 to 1:20 | Target architecture and shared state | Triage selects required work. Account, usage, and policy specialists investigate. Every handoff preserves one case state, and every material claim links to evidence and policy IDs. The current preview workflow is sequential; production migration adds true parallel fan-out and join. |
| 1:20 to 1:50 | Unsupported meter claim | Show SYN-CASE-4003. The customer asks for confirmation that the meter is broken. The ledger marks that claim unsupported. Compliance cannot approve it and returns a bounded correction instruction. |
| 1:50 to 2:15 | Human decision card | After two failed corrections, missing evidence, or policy conflict, the workflow routes to the correct human reviewer with known facts, unknowns, policy, risk, and a customer-safe interim message. |
| 2:15 to 2:35 | Quota, trace, audit, and gateway evidence | Foundry provides versioned agents, workflow configuration, model and quota inventory, traces, and evaluation surfaces. AI Gateway is a production target, but it was not provisioned because zero base cost could not be proven. |
| 2:35 to 2:50 | Impact scorecard | Success will be measured through handling time, touches, supported resolution, escalation quality, unsupported claims, policy coverage, and audit completeness. These are targets, not claimed results. |
| 2:50 to 3:00 | Closing | GridResolve AI is not a chatbot that happens to cite data. It is an evidence and authority system that can explain, refuse, escalate, and prove why. |

## 24. Likely judge Q&A

**Why nine agents instead of one?**  
The responsibilities have different evidence, authority, and failure rules. Separation makes each output inspectable and prevents the same agent from proposing and approving its own answer.

**Why is this genuinely agentic?**  
Specialized agents transform a shared case state, hand off structured work, reject one another's output, and route cases according to evidence, policy, and risk.

**How do you prevent hallucinated billing explanations?**  
Every material claim needs existing evidence IDs. Unsupported claims fail the independent compliance gate. Meter-failure claims need explicit diagnostic evidence.

**What happens if policies conflict?**  
The policy agent records the conflict and compliance requires human review. No agent silently selects a preferred policy.

**What happens if evidence is missing?**  
The case becomes `NEED_MORE_INFORMATION`, `HUMAN_REVIEW`, or `CANNOT_RESOLVE_SAFELY`. The system does not guess.

**What decisions require human approval?**  
Governed adjustments, conflicting evidence or policy, legal or regulatory concerns, material low confidence, unresolved meter allegations, privacy issues, and exhausted corrections.

**Why is AI Gateway useful?**  
It can centralize inventory, endpoints, quotas, token limits, monitoring, and security policy. It was not provisioned because the strict zero-cost condition could not be verified.

**How would this scale?**  
Move orchestration to Microsoft Agent Framework, use durable shared state, run independent investigation branches in parallel, add idempotency and queues, and apply gateway and telemetry policies.

**How would you secure production data?**  
Use Entra ID, managed identity, least-privilege RBAC, Key Vault, private networking where required, approved APIs, data minimization, per-case isolation, and auditable access.

**How is cost controlled?**  
Bounded workflow steps, no unapproved tools, quota inventory, future per-agent limits, token telemetry, no silent paid fallback, and an explicit cost guard.

**How would you measure success?**  
Measure handling time, manual touches, supported first-contact resolution, escalation quality, unsupported claims, unauthorized adjustments, policy citations, and audit completeness against real baselines.

**What makes this different from ordinary RAG?**  
RAG retrieves context. GridResolve also controls authority, state transitions, claim provenance, correction limits, compliance rejection, human escalation, and audit closure.

**What Foundry capabilities are demonstrated?**  
Versioned prompt agents, existing model association, workflow configuration, conditional routing, model and quota inventory, trace surfaces, evaluation surfaces, identity visibility, and project governance views.

**What is working versus prepared only?**  
Agent and workflow configurations are saved. The test, evaluation, telemetry, and production integrations are prepared but not executed or provisioned.

**Why synthetic data?**  
It protects customers and the company, supports repeatable demonstrations, and proves architecture without moving regulated data.

**What would you implement next with production access?**  
Run the three synthetic demos and 30-case evaluation under an approved capped budget, then migrate orchestration to Microsoft Agent Framework.

## 25. Screenshot evidence manifest

| ID | File | What it proves | Status |
|---|---|---|---|
| S01 | `S01-all-nine-agents.jpg` | All nine named agents and live versions | Captured |
| S02 | Not captured | CaseTriage structured instructions | Available in live configuration |
| S03 | `S03-compliance-controls.jpg` | EvidenceComplianceAgent version 3, instruction and tool surfaces | Captured |
| S04 | `S04-workflow-v4.jpg` | Workflow version 4 and retirement notice; canvas shows configured start of graph | Captured, partial graph view |
| S05 | Not captured | Parallel branch | Production target, native branch not configured |
| S06 | `S06-quota-inventory.jpg` | Existing model deployments, allocation, and 0% rate limiting | Captured |
| S07 | Not captured | Automated correction route | Prepared, not wired |
| S08 | Covered by S04 and dossier | Fail-closed escalation route | Configured, full branch not visible in saved viewport |
| S09 | Covered by workflow inventory | CaseAudit terminal route | Configured |
| S10 | Not captured | Synthetic evidence | Embedded in agent instructions and package |
| S11 | Not captured | Synthetic policies | Embedded in agent instructions and package |
| S12 | Not captured | Evaluation definitions | Package only, not entered or run |
| S13 | Not captured | Custom rubric | Package only |
| S14 | Not attached | Foundry trace surface showed no runs or traces | Inspected and documented |
| S15 | Not captured | Monitoring surface | Inspected only |
| S16 | `S16-ai-gateway-not-provisioned.jpg` | AI Gateway page and Add AI Gateway state | Captured |
| S17 | Not applicable | Gateway token controls | Gateway not created |
| S18 | Not applicable | Gateway inventory | Gateway not created |
| S19 | Covered by S06 | Existing gpt-5-mini with no rate limiting | Captured |
| S20 | Not attached | Cost Management showed no cost reported for Sep 2026 | Read-only check completed |

No screenshot intentionally exposes API keys, tenant IDs, subscription IDs, or project IDs.

## 26. Configured versus prepared versus production target

| Feature | CONFIGURED | PREPARED_NOT_EXECUTED | PRODUCTION_TARGET |
|---|---:|---:|---:|
| Nine agent resources | Yes |  |  |
| Agent version metadata and structured contracts | Yes |  |  |
| Shared state contract in instructions and schema | Yes |  | Durable state store |
| Evidence, policy, and claim ledgers | Yes |  | Enterprise source integration |
| Workflow v4 with all nine agents | Yes |  | Agent Framework migration |
| Fail-closed non-approval escalation | Yes |  | Typed decision routing |
| True parallel specialist fan-out and join |  | Yes | Yes |
| Bounded replan and rewrite loops | Contract only | Yes | Yes |
| Human review personas and decision card | Contract only | Yes | Work queue integration |
| Synthetic 16-case and 10-policy pack | Yes |  | Governed repository |
| Three demos |  | Yes | Approved runtime |
| 30-case evaluation suite |  | Yes | CI quality gate |
| Red-team suite |  | Yes | Continuous adversarial testing |
| Trace field and dashboard specification |  | Yes | Application Insights and Azure Monitor |
| Threat model and reliability matrix |  | Yes | Operational controls |
| AI Gateway |  | Yes | Cost-approved APIM gateway |
| Foundry IQ or Azure AI Search |  |  | Approved knowledge service |
| Bing grounding |  |  | Only if approved and required |
| Enterprise billing and meter APIs |  |  | Managed identity integration |
| Teams or Microsoft 365 Copilot channel |  |  | Optional approved channel |

## 27. Genuine blockers

1. Strict zero-cost policy prevents model, workflow preview, agent, evaluation, judge, search, or tool execution.
2. AI Gateway creates an Azure API Management dependency and zero base cost could not be proven.
3. Foundry Workflows Preview did not expose a verified native fan-out and join path during this pass.
4. Runtime-safe typed parsing for all four compliance decisions was not validated without preview execution.
5. Application Insights and other paid telemetry infrastructure were not provisioned.
6. The visible Web search control was not removed because that would delete configuration. It remains prohibited by instructions and was not invoked.
7. Workflows Preview retires on December 1, 2026, so production orchestration must move to Microsoft Agent Framework.
8. Billing data can lag and does not prove that a future charge will never appear.

## 28. Zero-cost and usage verification

Read-only Azure Cost Management check on 2026-09-18 UTC:

- Period displayed: September 2026.
- Actual cost displayed: `--`.
- Portal message: no cost reported during this period.
- Forecast unavailable.
- Service, location, and resource-group charts showed nothing to display.

Foundry evidence:

- Trace page showed no runs or traces.
- Model quota page showed 0% rate limiting for both existing deployments.
- No playground message was sent.
- No workflow preview was started.
- No agent run was started.
- No model request was intentionally sent.
- No evaluation or LLM judge was invoked.
- No Agent Optimizer call was made.
- No Bing or web-grounding call was made.
- No Foundry IQ or Azure AI Search resource was provisioned.
- No new model deployment, endpoint, Teams deployment, Copilot deployment, monitoring resource, or paid infrastructure was created.
- No AI Gateway was created.

Azure currently reports no cost for the displayed September 2026 period. Billing may lag. No model, evaluation, search, tool, or workflow runtime calls were intentionally executed.

## 29. Change log

| Version | Date | Artifact | Change | Reason | Execution status |
|---|---|---|---|---|---|
| Agents 3.0 | 2026-09-17 | Five existing agents | Strengthened contracts and versioned | Preserve work and add governance | CONFIGURED |
| Agents 3.0 | 2026-09-17 | Four new agents | Added usage, communication, escalation, audit roles | Complete nine-agent architecture | CONFIGURED |
| Workflow 2 | Existing | GridResolveAIWorkflow | Five-agent sequence | Prior build | Superseded |
| Workflow 3 | 2026-09-17 | GridResolveAIWorkflow | Sanitized intermediate YAML draft with no usable actions | Preview editor limitation | Superseded, not executed |
| Workflow 4 | 2026-09-17 | GridResolveAIWorkflow | Nine agents plus fail-closed branch and terminal audit | Safe zero-cost implementation | CONFIGURED, not executed |
| Synth 2.0 | 2026-09-17 | Synthetic pack | 16 cases and 10 policies | Coverage and judge evidence | CONFIGURED |
| Eval 2.0 | 2026-09-18 | Evaluation catalog | 30 tests, evaluator map, rubric, targets | Submission readiness | PREPARED_NOT_EXECUTED |
| Red Team 2.0 | 2026-09-18 | Red-team pack | Adversarial test definitions | Security readiness | PREPARED_NOT_EXECUTED |

## 30. Single highest-value remaining step

Run one tightly capped, synthetic-only end-to-end demonstration for SYN-CASE-4003 under explicit cost approval, capturing the unsupported meter-fault rejection, corrected grounded response, terminal audit packet, trace, token count, latency, and actual incremental cost.

That one controlled run would convert the strongest differentiator from configuration evidence into runtime proof. It should be performed only after the user explicitly approves the possible cost and sets a hard budget.

