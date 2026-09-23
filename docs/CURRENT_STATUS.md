# GridResolve AI: current verified status

Updated 2026-09-23, after the five hosted executions of workflow v11. This
page is the single reference for every current claim in the README, the
judge narrative, the deck, the video and the post-review validation report.
Where another document disagrees with this page, this page is right and the
other is out of date. The section "Status as submitted, 2026-09-20" is kept
below, unchanged, because the submitted PDF and video describe that state.

## What it is

A runtime-demonstrated, production-oriented multi-agent prototype. Nine
specialist agents run as one governed workflow on Microsoft Foundry and
investigate synthetic utility billing disputes. It is not a production system.
No utility, meter, CRM or identity system is integrated. All data is synthetic.

## Numbers to use, 2026-09-23

| Fact | Value |
| --- | --- |
| Live workflow | GridResolveAIWorkflow **v11**, published 2026-09-23, read back byte for byte |
| Live compliance agent | EvidenceComplianceAgent **v7**, four route tokens, mandatory reason codes on any non-approval |
| Other agents | CaseTriage 5, AccountEvidence 9, UsageAnomaly 4, PolicyKnowledge 6, ResolutionPlanner 6, CustomerCommunication 5, EscalationCoordinator 5, CaseAudit 7, unchanged |
| Model | gpt-5-mini, reasoning low, no tools attached to any agent |
| Genuine Foundry workflow executions | **eight**: three of SYN-CASE-4003 (v6, v9, v10) on 2026-09-20 and 2026-09-21, then SYN-CASE-4007, 4001, 4003, 4011 and 4002 on v11 on 2026-09-23 |
| Distinct synthetic cases executed | **five** |
| Acceptance, v11 runs | 4007: 8 of 14, escalation target missed. 4001: **12 of 12**, no-follow-up branch observed. 4003: **14 of 14**, regression. 4011: 8 of 14 with 5 not observable, rewrite target missed. 4002: 9 of 15 with 5 not observable, replan target missed |
| Routes observed on v11 | approve and release (5 of 5), human handoff (4), no follow-up (1). Escalation, rewrite and replan: none |
| Safety on every release | no meter fault asserted, no credit promised, released text equals the approved draft, in all six releases since v10 |
| Deterministic checks, v2.1 | v10 14 of 14; v11 runs 10, 10, 12, 11 and 10 of 14. The two safety checks pass on all eight runs. Failures are listed with the checker's own messages in `docs/UPDATED_EVALUATION_METRICS.md` |
| Tokens and cost, 2026-09-23 | 465,202 in, 107,178 out, USD 0.3280 estimated for five runs; per run USD 0.0571 to 0.0756, cap USD 0.70, none retried |
| Confirmed billed amount | USD 0.1310 for the three historical runs, matching the estimate of USD 0.1311. The 2026-09-23 runs were not yet visible in Azure Cost Management on 2026-09-23 |
| Supervisor override rate, review-time reduction | NotMeasured: zero actual human decisions, no baseline |
| Local checks | 1,544 across twelve suites (`tests/run_all_suites.py`), plus 105 Power Fx cases, 11 of 11 Agent Framework parity and 94 read-only live configuration checks |

## The five v11 executions

| | 4007 | 4001 | 4003 | 4011 | 4002 |
| --- | --- | --- | --- | --- | --- |
| Designed to show | reasoned escalation on a record conflict | no-follow-up branch | regression of the final run | REJECT_REWRITE after an injected promise | REJECT_REPLAN on a true-up |
| What happened | approved and released a message that states the conflict; planner asked for a human | approved and released; planner cleared the case; escalation agent never invoked | same route as v10, 14 of 14 | communication agent refused the injected promise; approved; handed to a human | planner referred the true-up to a human and authorized nothing; approved |
| Target reached | no | **yes** | yes | no | no |
| Corrections | 0 | 0 | 0 | 0 | 0 |
| Audit findings | 0 | 0 | 0 | 0 | 0 |
| Cost, estimated | USD 0.0756 | USD 0.0571 | USD 0.0599 | USD 0.0678 | USD 0.0676 |

Records: `docs/RUN_RESULT_SYN-CASE-4007_2026-09-23.md`,
`docs/RUN_RESULT_SYN-CASE-4001_2026-09-23.md`,
`docs/RUN_RESULT_SYN-CASE-4003_v11_2026-09-23.md`,
`docs/RUN_RESULT_SYN-CASE-4011_2026-09-23.md`,
`docs/RUN_RESULT_SYN-CASE-4002_2026-09-23.md`. Consolidated:
`docs/POST_REVIEW_VALIDATION_REPORT.md`. Evidence: `evidence/runtime/`, eight
folders, unmodified.

## Still not observed in the hosted service

- The fail-closed escalation branch on v10 or v11. Observed once, on v9,
  without reasons.
- Structured reason codes on a hosted decision. Every v7 decision so far was
  an approval, which carries none by design.
- REJECT_REWRITE and REJECT_REPLAN, and therefore the two-attempt bound.
  Proven on the local engine only.
- The third gate term returning false.
- 15 of the 20 prepared cases and all 18 adversarial probes.
- Any actual supervisor decision.

## Claims that must not be made

- That compliance rejected any draft on v7, or that a correction route ran in
  the hosted service.
- That run 2 escalated because compliance identified an unsupported claim.
- That the 2026-09-23 runs have a confirmed billed amount.
- That any utility, meter, CRM or identity integration is live.
- That a supervisor reviewed any case.
- That the system is production-ready.

---

## Status as submitted, 2026-09-20

Updated 2026-09-20, after the third and last real execution before submission.
The implementation was frozen at that point. The submitted PDF and video
describe this state.

### The verified story, from the final run's platform record

1. A synthetic customer says their bill jumped from $152.80 to $203.40 and that
   the meter must be broken.
2. Nine Foundry agents investigate the case in sequence.
3. The evidence does not establish a meter failure. The register moved from
   41,820 to 42,690, which is 870 kWh, exactly the billed consumption. Both reads
   are actual, the diagnostic passed, no meter events exist, and the rate did not
   change. 640 x 0.22 + 12 = 152.80 and 870 x 0.22 + 12 = 203.40.
4. The agents built a 22-entry evidence ledger and mapped nine governed policies.
5. A customer-facing explanation was drafted. It asserts no meter failure and
   promises no credit.
6. The independent compliance agent **approved** that message, with recorded
   reasons, and emitted the approval token.
7. The workflow released a readable six-part message, 2,592 characters.
8. A separate follow-up decision, taken from the planner's own token, sent the
   unresolved investigation to human review. The escalation agent produced a
   review package for a Billing Supervisor. No decision was made for the human.
9. The audit agent recorded that outcome correctly. The runner's cross-check of
   the audit against the platform record found nothing to correct.

Compliance did **not** reject the final draft. The final run did **not** take the
fail-closed branch.

### Numbers as submitted

| Fact | Value |
| --- | --- |
| Live workflow at submission | GridResolveAIWorkflow v10 |
| Genuine Foundry workflow executions at submission | three, all of SYN-CASE-4003 |
| Final acceptance | 14 of 14 PASS, against criteria written before the run |
| Final evidence ledger | 22 entries, every value matched to the case input |
| Final policy mapping | nine policies, none invented |
| Final audit | zero findings |
| Final run | 179.5 s, 94,352 tokens in, 22,433 out, about $0.07 |
| Provisional Azure cost, three runs | about $0.13 ($0.0334 + $0.0292 + $0.0685), since confirmed by billing at $0.1310 |
| Local checks at submission | 1,174, plus 105 Power Fx cases and 94 live configuration checks |

### The three executions

| | Run 1 | Run 2 | Final run |
| --- | --- | --- | --- |
| Workflow | v6 | v9 | v10 |
| Agents that did their work | 7 of 8 | 6 of 9 | 9 of 9 |
| Evidence ledger | none | none | 22 entries |
| Compliance | approved | escalated, **gave no reasons** | approved, with reasons |
| Sent to the customer | an unevaluated expression | nothing | a readable message |
| Human follow-up | not built | escalation package | handoff after the release |
| Audit findings | 7 | 6 | 0 |
| Cost, provisional | $0.0334 | $0.0292 | $0.0685 |

Run 1 exposed four defects. Run 2 demonstrated the hosted fail-closed route: the
case was withheld from the customer and handed to a person. Its compliance output
was the token alone, so **why it escalated is not established**. Two specialists
stalled in that run. The cause was found in the platform's own record of what
each agent received: every agent after the first was invoked with an empty input
on a shared conversation, with no new user turn. v10 gives every agent an
explicit input message, adds a third gate term that withholds the message when an
investigation output is not a JSON object, and puts strict output schemas on the
evidence, policy and audit agents.

Records: `docs/FIRST_RUN_AND_CORRECTIONS_2026-09-20.md`,
`docs/SECOND_RUN_RESULT_2026-09-20.md`, `docs/V10_CORRECTIONS_2026-09-20.md`,
`docs/FINAL_RUN_ACCEPTANCE_PLAN.md`, `docs/FINAL_RUN_RESULT_2026-09-20.md`.

### Added on 2026-09-21, at no Azure cost

Platform telemetry read back (Azure Monitor and the platform's spans report the
same tokens as the runner: 186,614 in, 42,155 out, 26 model requests), the
guardrail configuration as actually set (`Microsoft.DefaultV2` attached, no
custom policy), the Foundry capability inventory, the evaluation package (13
deterministic checks, 8 provenance links), integration contracts (138 checks),
the Agent Framework parity proof (11 of 11) and the Runtime Evidence view.
Details: `docs/OPERATIONS_MONITORING_AND_COST.md`,
`docs/SECURITY_AND_GOVERNANCE_EVIDENCE.md`, `evaluation/`, `integration/`,
`migration/agent_framework/`.

## Production readiness

Demonstrated end to end on synthetic data, eight times. Not production-ready.
What a utility would need, none of which is implemented or claimed as live:

| Area | Plan |
| --- | --- |
| Billing and account systems | Replace the synthetic records in the case input with read-only function tools over the billing system of record. `docs/GRIDRESOLVE_TOOLBOX.md` defines thirteen deterministic tools for this |
| Meter data systems | Interval reads, events and diagnostics from the meter data management system, read-only, with data freshness recorded in the evidence ledger |
| Customer relationship management | Case intake and the released message go through the CRM, which also carries the human handoff as a work item |
| Governed policy knowledge | The policy ledger moves from agent instructions to a versioned, access-controlled policy store, so a policy change is a reviewed release and not a prompt edit |
| Microsoft Entra ID and roles | Managed identities for the agents, role-based access per tool, and reviewer roles mapped to Entra groups |
| Human authorization for money | No agent may authorize a credit or adjustment. A Human Billing Supervisor approves, in the system of record, with the decision card as the input. The supervisor feedback store is the record of that decision |
| Monitoring, traceability, audit retention | Platform spans already reach the Application Insights resource that came with the project, with no alerting and with content recording on. Production adds alerts on semantic signals, a content recording decision, the platform record as the source of truth, the audit record retained under the utility's records schedule. `docs/LOCAL_TRACE_SCHEMA.md` |
| Failure handling and deployment | Timeouts and retries per agent with state preserved, fail-closed to human review, staged rollout, evaluation gates before each release. `docs/GUARDRAILS_MATRIX.md` |
| Platform migration | Foundry Workflows is a preview that retires on 2026-12-01. The plan is Microsoft Agent Framework, which runs the same declarative YAML. `docs/AGENT_FRAMEWORK_MIGRATION.md`. The local test harness already runs the v10 and v11 YAML on that open-source engine |
