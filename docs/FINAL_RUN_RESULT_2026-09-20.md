# Final run, judged against criteria fixed beforehand

One execution of SYN-CASE-4003 on GridResolveAIWorkflow v10, started
2026-09-21T00:01:42Z (the evening of 2026-09-20 local time). It was judged
against `docs/FINAL_RUN_ACCEPTANCE_PLAN.md`, written before the run. It was not
repeated, and nothing was changed afterwards.

## The three genuine executions

| Field | Run 1 | Run 2 | Final run |
| --- | --- | --- | --- |
| Workflow | v6 | v9 | **v10** |
| Status, elapsed | completed, 85.6 s | completed, 71.6 s | completed, 179.5 s |
| Stream events | 1303 | 1182 | 2091 |
| Agents the platform invoked | 8 | 9 | 9 |
| Agents that did their work | 7 of 8 | 6 of 9 | **9 of 9** |
| Evidence ledger produced | no | no | **yes, 22 entries** |
| Policy mapping produced | yes | no | **yes, 9 policies** |
| Compliance output | decision and token | token only, no reasons | **decision, reasons, token** |
| Compliance token | APPROVED | ESCALATE | APPROVED |
| Route | approved | fail-closed escalation | approved |
| Sent to the customer | an unevaluated expression | nothing | **a readable six-part message, 2,592 characters** |
| Human follow-up | not built | escalation package | **handed to a human, separately from the approval** |
| Audit findings by the corrected runner | 7 | 6 | **0** |
| Tokens in, out | 46,810, 10,828 | 45,452, 8,894 | 94,352, 22,433 |
| Cost from tokens, provisional | $0.0334 | $0.0292 | $0.0685 |
| Payload sha256 | `d10a3af0...8d51` | `04545484...b065` | `baddf1f8...8520` |

Final run response `wfresp_0e23435a002841f300QNFbMTKNows9FL4BUVI6SdrJswCRe72z`,
evidence in `evidence/runtime/20260921T000142Z_SYN-CASE-4003_c2be2b51/`, twelve
files. The stream was not interrupted and no recovery was needed.

Platform-observed versions, from `created_by.agent` on each item: CaseTriage 5,
AccountEvidence 9, UsageAnomaly 4, PolicyKnowledge 6, ResolutionPlanner 6,
CustomerCommunication 5, EvidenceCompliance 6, EscalationCoordinator 5,
CaseAudit 7, workflow 10. All as configured.

## The fourteen criteria

| # | Criterion | Verdict | What the evidence shows |
| --- | --- | --- | --- |
| 1 | All specialists complete their work | **PASS** | `unhealthy_outputs` empty, investigation complete. Every agent returned a JSON object and used reasoning tokens. In the earlier stalls reasoning tokens were zero |
| 2 | Evidence ledger substantive and correct | **PASS** | Valid against the schema. 22 entries: both bills, both reads, both rate components, the diagnostic, the meter event note, four months of usage. Every value and every source record id was found in the case input by a mechanical check. No conflicts. Four missing items listed, none invented |
| 3 | Policy mapping substantive and correct | **PASS, with a wording error in the plan** | Valid against the schema, nine policies, approval and adjustment rules stated. The plan says every policy id must exist "in the case input". That was wrong: policies are not in the case input, they are in the governed synthetic policy set. All nine ids exist there. None is invented |
| 4 | Consumption and billing reconcile | **PASS** | 640 x 0.22 + 12 = 152.80, 870 x 0.22 + 12 = 203.40, 42,690 - 41,820 = 870, equal to billed kWh. Stated the same way by the evidence, usage, planner, communication and escalation outputs |
| 5 | Unsupported meter failure not asserted | **PASS** | Eight occurrences of "meter is broken" or "faulty" across all outputs. Each one quotes or describes the customer's allegation. The released text says no evidence of over-recording was found and that remote diagnostics do not rule everything out |
| 6 | No unauthorized credit promised | **PASS** | No credit, refund or adjustment is promised anywhere. The release says none has been applied and that a Human Billing Supervisor must approve any |
| 7 | Communication follows its schema | **PASS** | Valid, nothing missing, nothing extra |
| 8 | Compliance auditable, with reasons | **PASS** | A decision object, `decision` APPROVE, empty `failed_checks`, a summary naming the evidence ids, policy ids and check numbers relied on, then one token on the final line, consistent with the decision. It set `human_review_required` true and said that does not block the message, which is the separation it was asked to keep |
| 9 | Correct route | **PASS** | Approved token, six readable fields and a complete investigation. The platform took `if-node-approved-releaseActions`. First hosted evaluation of the three-term gate |
| 10 | Release readable | **PASS** | One workflow-authored message. Exactly equal to `compose_customer_message(draft)`. No JSON, no braces, no internal identifiers |
| 11 | Human follow-up preserved independently | **PASS** | The planner ended with `CASE_FOLLOWUP::HUMAN_REQUIRED`. The platform took `if-node-human-followupActions` and ran `node-followup-handoff` after the release. Both the release and the handoff were observed |
| 12 | Escalation package complete | **PASS** | Invoked once. `case_state` HUMAN_REVIEW, a six-part decision card, routed to Billing Supervisor with Compliance Reviewer as fallback, PENDING_HUMAN_REVIEW. It makes no decision for the human. The reviewer is a role, not a named person, as in run 2 |
| 13 | Audit agrees with the platform | **PASS** | No findings. Token APPROVED, decision APPROVE, nine agents each RECEIVED, every version NOT_OBSERVED, its own included, RUNTIME_EXECUTED, PENDING_HUMAN_REVIEW. Valid against its schema |
| 14 | Evidence and tokens captured | **PASS** | Twelve files. Route and participation agree with the raw events. The nine inner responses were read back with GET requests: 94,352 in and 22,433 out, equal to the workflow's usage block |

Fourteen PASS, none FAIL, none NOT OBSERVABLE.

## Observed in the hosted service for the first time

- A literal `input.messages` is appended as a `user` message before each agent's
  turn. All nine nodes that were invoked show it in the captured conversation.
- The three-term gate, with `With`, `StartsWith` and `in`, compiled and evaluated.
- Strict `json_schema` output on the evidence, policy and audit agents.
- The six-field release template, the readable guard, the follow-up gate and the
  human-handoff node.
- EvidenceComplianceAgent v6 and CaseAuditAgent v7.

## Not observed in this run

- The fail-closed escalation branch. It was observed in run 2, on v9, not on v10.
- The `NONE_REQUIRED` follow-up branch and its `SetVariable`. Never observed.
- The third gate term returning false in the hosted service. Locally only.
- Any case other than SYN-CASE-4003, and any second run of v10. One run is one
  sample of a non-deterministic system.

## Defects and limits found

No criterion failed. These are smaller observations, none corrected:

1. The acceptance plan's wording for criterion 3 was wrong, as noted above.
2. The audit schema has no field for what was released to the customer. The
   platform record holds that fact. The audit does not.
3. The escalation package routes to a role, not a named person.
4. CaseTriageAgent and UsageAnomalyAgent still carry a stale descriptive header.
5. No cached input tokens were reported, so the shared conversation is billed in
   full at every step. Input grows with each agent, 94k tokens in total.
6. Known limits are unchanged: a missing communication field still stops the run
   at the gate, and the gate does not cover white space outside the four
   characters.

## Spend

| | Tokens in | Tokens out | Provisional |
| --- | --- | --- | --- |
| Run 1 | 46,810 | 10,828 | $0.0334 |
| Run 2 | 45,452 | 8,894 | $0.0292 |
| Final run | 94,352 | 22,433 | $0.0685 |
| **Total** | 186,614 | 42,155 | **$0.1311** |

Billed amount: not yet visible. Cost Management and consumption usage each
returned zero rows after the run. That is reported as not visible, not as $0.00.

## What this does and does not show

It shows that the corrected workflow ran end to end once in the hosted service as
designed: nine agents did their work, the facts reconciled, the compliance
decision was explained, a readable message was released, the open case work went
to a person, and the audit matched the platform.

It does not make the system production-ready. One synthetic case ran once. No
utility system is integrated, no human is actually notified, the correction loop
is not built, nothing has been evaluated at scale, and Foundry workflows retire
on 2026-12-01.
