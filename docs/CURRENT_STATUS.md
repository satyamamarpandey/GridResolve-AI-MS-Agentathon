# GridResolve AI: current verified status

Updated 2026-09-20, after the third and last real execution. The implementation
is frozen. This page is the single reference for every current claim in the
README, the judge narrative, the deck and the video. Where another document
disagrees with this page, this page is right and the other is out of date.

## What it is

A runtime-demonstrated, production-oriented multi-agent prototype. Nine
specialist agents run as one governed workflow on Microsoft Foundry and
investigate a synthetic utility billing dispute. It is not a production system.

## The verified story, from the final run's platform record

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

## Numbers to use

| Fact | Value |
| --- | --- |
| Live workflow | GridResolveAIWorkflow **v10** |
| Agents | nine: CaseTriage 5, AccountEvidence 9, UsageAnomaly 4, PolicyKnowledge 6, ResolutionPlanner 6, CustomerCommunication 5, EvidenceCompliance 6, EscalationCoordinator 5, CaseAudit 7 |
| Model | gpt-5-mini, reasoning low, no tools attached to any agent |
| Genuine Foundry workflow executions | **three**, all of SYN-CASE-4003, all on 2026-09-20 local time |
| Final acceptance | **14 of 14 PASS**, against criteria written before the run |
| Final evidence ledger | **22 entries**, every value matched to the case input |
| Final policy mapping | **nine policies**, none invented |
| Final audit | **zero findings** |
| Final run | 179.5 s, 94,352 tokens in, 22,433 out, about $0.07 |
| Provisional Azure cost, all three runs | **about $0.13** ($0.0334 + $0.0292 + $0.0685), from returned token counts at list price |
| Confirmed billed amount | **not yet visible** in Azure Cost Management. This is not a confirmed $0.00 |
| Embeddings, evaluation runs, billable resources created | none |
| Local checks | 1,174 (83 routing, 151 synthetic data, 156 application, 357 runner, 91 workflow engine, 198 evaluation package, 138 integration contracts), plus 105 cases on the real Power Fx engine, plus 94 read-only live configuration checks |

## The three executions

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
Evidence: `evidence/runtime/`, three folders, unmodified.

## Added on 2026-09-21, at no Azure cost

Nothing below touched the agents, the workflow, the case data or the three
evidence folders. No model was called. The resource still shows 26 lifetime model
requests, all from the three approved runs.

| Addition | Status | Where |
| --- | --- | --- |
| Platform telemetry read back | Runtime verified, read only. Azure Monitor and the platform's own spans report the same tokens as my runner, to the token: 186,614 in, 42,155 out, 26 model requests. 61 spans, 0 failed, 0 content filter blocks | `evidence/platform_telemetry/`, `docs/OPERATIONS_MONITORING_AND_COST.md` |
| Guardrail and security configuration, as actually set | Read from Azure. `Microsoft.DefaultV2` is attached and evaluated all 26 calls. No custom policy exists. Public network access and key authentication are still on | `docs/SECURITY_AND_GOVERNANCE_EVIDENCE.md` |
| Foundry capability inventory with cost classes | Read only | `docs/FOUNDRY_CAPABILITY_INVENTORY.md` |
| Evaluation package: 13 deterministic checks, 8 link provenance trace, policy catalog, Foundry shaped datasets | Locally tested, 198 checks. Not model based. The final run passes 12 of 13 and resolves 8 of 8 provenance links. Runs 1 and 2 resolve 3 and 1 | `evaluation/` |
| Integration contracts with synthetic adapters | Locally tested, 138 checks. An agent principal cannot authorize an adjustment | `integration/` |
| Microsoft Agent Framework parity proof | Locally tested, 11 of 11. The final run's nine real outputs, replayed through Microsoft's open-source engine on the same v10 YAML, take the same path and release the same 2,592 characters | `migration/agent_framework/` |
| Runtime Evidence view | Locally tested, part of the 156 application tests | Control Center |
| Routines, skills, tools and memory | Design only. Nothing enabled | `docs/ROUTINES_SKILLS_TOOLS_MEMORY_DESIGN.md` |

Two things I corrected today. First, I had written that no Application Insights
resource existed. One was created with the project and holds the platform's spans
for all three runs. Second, the one deterministic check the final run fails: the
planner labelled the root cause `USAGE_SUPPORTED`, and the label I prepared before
any run says `NO_SUPPORTED_ROOT_CAUSE`. The two may answer different questions. I
have not settled it, so it stays a FAIL. It was not one of the 14 pre-registered
acceptance criteria, which the run still passes 14 of 14.

## Not observed

- The fail-closed branch on v10. It was observed once, on v9.
- The follow-up branch where no human is needed.
- The third gate term returning false in the hosted service.
- Any case other than SYN-CASE-4003, and any second run of v10. One run is one
  sample of a non-deterministic system.
- The 30 prepared evaluation cases and 16 adversarial probes. Not executed.
- The correction loop. Not built.

## Production readiness

Demonstrated once, end to end, on synthetic data. Not production-ready. What a
utility would need, none of which is implemented or claimed as live:

| Area | Plan |
| --- | --- |
| Billing and account systems | Replace the synthetic records in the case input with read-only function tools over the billing system of record. `docs/GRIDRESOLVE_TOOLBOX.md` defines thirteen deterministic tools for this |
| Meter data systems | Interval reads, events and diagnostics from the meter data management system, read-only, with data freshness recorded in the evidence ledger |
| Customer relationship management | Case intake and the released message go through the CRM, which also carries the human handoff as a work item |
| Governed policy knowledge | The policy ledger moves from agent instructions to a versioned, access-controlled policy store, so a policy change is a reviewed release and not a prompt edit |
| Microsoft Entra ID and roles | Managed identities for the agents, role-based access per tool, and reviewer roles mapped to Entra groups |
| Human authorization for money | No agent may authorize a credit or adjustment. A Human Billing Supervisor approves, in the system of record, with the decision card as the input |
| Monitoring, traceability, audit retention | Platform spans already reach the Application Insights resource that came with the project, with no alerting and with content recording on. Production adds alerts on semantic signals, a content recording decision, the platform record as the source of truth, the audit record retained under the utility's records schedule. `docs/LOCAL_TRACE_SCHEMA.md` |
| Failure handling and deployment | Timeouts and retries per agent with state preserved, fail-closed to human review, staged rollout, evaluation gates before each release. `docs/GUARDRAILS_MATRIX.md` |
| Platform migration | Foundry Workflows is a preview that retires on 2026-12-01. The plan is Microsoft Agent Framework, which runs the same declarative YAML. `docs/AGENT_FRAMEWORK_MIGRATION.md`. The local test harness already runs the v10 YAML on that open-source engine |

## Claims that must not be made

- That compliance rejected the final message, or that the final run escalated at
  the gate.
- That run 2 escalated because compliance identified an unsupported claim.
- That only one or two runs happened, or that v10 has not executed.
- That Azure billing confirmed $0.00, or any billed figure.
- That any utility, meter, CRM or identity integration is live.
- That the system is production-ready.
- That evaluations, red-team probes, parallel execution or a correction loop ran.
