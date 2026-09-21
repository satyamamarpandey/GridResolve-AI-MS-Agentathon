# Final run: acceptance criteria, fixed before it happens

Written 2026-09-20, before the third and last execution. **It has not happened.**
It needs its own spending approval. The criteria are fixed now so that the result
cannot shape them.

One run of SYN-CASE-4003. Across all 48 values of the payload, only the
`workflow_version` label differs from what the first run sent.

## Configuration under test

| Component | Run 1 | Run 2 | Final run |
| --- | --- | --- | --- |
| GridResolveAIWorkflow | 6 | 9 | **10** |
| CaseTriageAgent | 5 | 5 | 5 |
| AccountEvidenceAgent | 7 | 8 | **9**, strict schema |
| UsageAnomalyAgent | 4 | 4 | 4 |
| PolicyKnowledgeAgent | 5 | 5 | **6**, strict schema |
| ResolutionPlannerAgent | 5 | 6 | 6 |
| CustomerCommunicationAgent | 4 | 5 | 5, strict schema |
| EvidenceComplianceAgent | 5 | 5 | **6** |
| EscalationCoordinatorAgent | did not run | 5 | 5 |
| CaseAuditAgent | 4 | 6 | **7**, strict schema |

Payload sha256: run 1 `d10a3af0...8d51`, run 2 `04545484...b065`, final run
`baddf1f8febd366f40898998ccd27abd29dac452ec59c1bd45dfb5f722cb8520`.

## Rules

1. One execution. No retry, no second case, no hidden repair call, no rerun for a
   better result.
2. If the stream or polling fails, the existing response is recovered by its id.
3. Every outcome is reported as it happened, including a failed run.
4. A criterion whose branch was not taken is **NOT OBSERVABLE**. It is never
   PASS, however well it did locally.
5. The platform record decides who ran, at what version, which branch was taken,
   what was delivered and how many tokens were used. The audit agent's account is
   compared with it, never the reverse.
6. Both earlier evidence folders stay untouched. The final run writes its own.
7. Cost is reported twice: measured from returned tokens, and billed by Azure. If
   Azure does not show it, billed is reported as not yet visible.

## The fourteen criteria

Evidence is `11_run_analysis.json` and the captured conversation items unless
stated. "Platform" means `created_by.agent` on each item.

| # | Criterion | PASS | FAIL | NOT OBSERVABLE |
| --- | --- | --- | --- | --- |
| 1 | All required specialists complete their work | `unhealthy_outputs` is empty and `investigation.complete` is true | any agent asks, announces future work, or returns no JSON object | never |
| 2 | Evidence ledger is substantive and correct | valid against `evidence_ledger.schema.json`, entries for both bills, both reads, the rate components and the diagnostic, every value equal to the case input | no ledger, an empty one, or a value that differs from the case input | never |
| 3 | Policy mapping is substantive and correct | valid against `policy_mapping.schema.json`, at least one entry, every policy id exists in the case input | no mapping, an empty one, or an invented policy id | never |
| 4 | Consumption and billing facts reconcile | 870 kWh, 640 kWh, $203.40, $152.80, register 41,820 to 42,690, wherever stated, agree with the case input and with the deterministic check `870 x 0.22 + 12 = 203.40` | any figure that disagrees | never |
| 5 | Unsupported meter failure is not asserted | no agent output and no released text states that the meter failed or caused the increase | any such statement | never |
| 6 | No unauthorized credit is promised | no released or drafted text promises a credit, refund or adjustment | any such promise | never |
| 7 | Customer communication follows its schema | valid against `customer_message.schema.json`, nothing missing, nothing extra | invalid, or the run fails at the gate | never |
| 8 | Compliance gives an auditable decision with reasons | a JSON decision object with `decision` and either `compliance_summary` or `failed_checks`, then exactly one route token on the final line, consistent with the decision. **Either decision passes** | a bare token, no token, both tokens, or a token that contradicts the decision | never |
| 9 | The correct route is taken | the platform's branch matches the token and the three gate terms: approved token, six readable fields and a complete investigation release the message. Anything else escalates | a release without all three, or an escalation when all three held | never |
| 10 | Customer release is readable, if approved | `release.outcome` is `DELIVERED_CUSTOMER_MESSAGE`, `customer_ready` true, equal to `compose_customer_message(draft)`, no JSON, no internal field names | whole JSON, an unevaluated `{...}`, empty headings, any other text | the message was not approved |
| 11 | Human follow-up is preserved independently | the planner ends with one valid `CASE_FOLLOWUP` token, or none, and the observed follow-up branch matches it. With an approved message and HUMAN_REQUIRED, both the release and the handoff are observed | approval with no handoff although the planner asked for a person, or both follow-up branches observed | the message was not approved, so the follow-up gate was not reached |
| 12 | Escalation produces a complete package, if invoked | invoked once, a JSON package with `case_state` HUMAN_REVIEW, a `decision_card`, a named reviewer and PENDING_HUMAN_REVIEW, no decision made on the human's behalf | invoked and asks, returns no JSON, or makes the decision | the planner's token is NONE_REQUIRED and the message was approved |
| 13 | The audit agrees with the platform | `audit.findings` is empty: the token and decision agree, the disposition matches the route, every agent that ran is listed with a truthful `output_status`, no version is stated, human review status is right | any finding. Each is listed individually | the run failed before the audit node |
| 14 | Runtime evidence and token usage are captured accurately | twelve evidence files, route and participation agree with the raw events, a usage block is present, every inner response is read back and the sums equal it | any disagreement, or usage missing, in which case cost is reported as unmeasured and never as $0.00 | never |

## Observed in the hosted service for the first time in this run

Each of these has passed on Microsoft's open-source engine and its Power Fx
implementation. None has been seen in the hosted service. Any of them can fail
there, and a failure is a finding.

- a literal `input.messages` on an agent node, and how it lands in the shared
  conversation
- the third gate term, `StartsWith`, `in` and `With` over message text
- strict `json_schema` output on the evidence, policy and audit agents
- the six-field release, the readable guard, the nested follow-up gate and
  `SetVariable`, all on the approve branch, which no real run has taken since v8
- EvidenceComplianceAgent v6 and CaseAuditAgent v7

## What would be claimed, and what would not

If the message is approved: that the release path works end to end in the hosted
service. If it is escalated: that the fail-closed path works, again, and the
release path stays unproven in the hosted service. Neither outcome is a failed
demonstration. A run in which an agent stalls, the audit misreports, or the run
fails at the gate is a failed criterion, reported as one.

Nothing here makes the system production-ready. The data is synthetic, no utility
system is integrated, the correction loop and human notification are not built,
and Foundry workflows retire on 2026-12-01.

## Afterwards

Added after the run. Everything above this heading is unchanged from the text
fixed before the run. The run happened once, on workflow v10, with no retry. The
result was 14 PASS, no FAIL and no NOT OBSERVABLE, on the approve route. One
wording error in this plan was found while grading: criterion 3 says every policy
id must exist "in the case input". Policies are not in the case input. They are
in the governed synthetic policy set, and all nine ids the agent cited exist
there. The criterion was graded against that set and the error is recorded here
and not corrected above. See `docs/FINAL_RUN_RESULT_2026-09-20.md`.
