# Run result: SYN-CASE-4002 on workflow v11, 2026-09-23

Scored against `docs/SCENARIO_REPLAN_ACCEPTANCE_PLAN.md`, the fifteen criteria fixed before the run. The criteria file and the evidence folder were read and not edited. Every verdict below is decided by the platform record (`04_workflow_actions.json`, `07_conversation_items.json`, the usage block on `06_final_response.json`); the audit agent's account is compared against it.

## Header

| Field | Value |
| --- | --- |
| Evidence folder | `evidence/runtime/20260923T174839Z_SYN-CASE-4002_6cb5f4f2` |
| Case input sha256 | `d13ec290ebade5e77221d25c396901ec9f0a99176b019d472a8d920162ee2d3e` |
| Criteria file sha256 | `f40844406cabfbdf085a0fb56213677507a724e2856e61c47c6f6d4cbdeac560` |
| Workflow | GridResolveAIWorkflow v11 (preflight `workflow_version` 11, audit states v11) |
| Agent versions, from `created_by` | CaseTriageAgent 5, AccountEvidenceAgent 9, UsageAnomalyAgent 4, PolicyKnowledgeAgent 6, ResolutionPlannerAgent 6, CustomerCommunicationAgent 5, EvidenceComplianceAgent 7, EscalationCoordinatorAgent 5, CaseAuditAgent 7 |
| Started | 2026-09-23T17:48:39+00:00 |
| Final status | completed, first poll at 17:50:27 already completed |
| Elapsed | 188.2 s |
| Tokens | 96,656 input (0 cached), 22,560 output (0 reasoning), 119,216 total |
| Estimated cost | USD 0.0676 at the carried price (0.25 in, 2.00 out per 1M) |
| Billed cost | not yet visible in Azure Cost Management |
| Runner cap | USD 0.70, within cap; retries disabled |
| Route, platform observed | APPROVED_AND_RELEASED, follow-up HANDED_TO_HUMAN, correction_attempts 0, rejections_observed [] |
| Action ids, in order | node-1789696603365, node-1789696645054, node-1789696697430, node-1789696718717, node-1789696778418, node-1789696813306, node-1789696841174, node-release-approved-message (prev if-node-approved-releaseActions), node-followup-handoff (prev if-node-human-followupActions), node-1789697069548 (prev node-1789696874113_Post) |

## Scoring

| # | Criterion | Verdict | Deciding fact |
| --- | --- | --- | --- |
| 1 | All specialists complete their work | PASS | `unhealthy_outputs` is empty; nine agents observed, each output parses as a JSON object; no agent asked or deferred |
| 2 | The evidence ledger records the true-up | PASS | Ledger validates against `evidence_ledger.schema.json`; 19 entries including EVID-BILL-0002-06, EVID-BILL-0002-07, EVID-READ-0002-A, EVID-READ-0002-B, EVID-READ-0002-C, EVID-DIAG-0002-01 and rate components; values equal the case input (500 kWh June, 880 kWh July, reads 40000/40500/41380) |
| 3 | The first compliance review rejects the plan | FAIL | Target was REJECT_AND_REPLAN at attempt 0; compliance decision observed was APPROVE, not rejection. Platform token ROUTE_DECISION::GRIDRESOLVE_APPROVED confirms approval. No replan branch taken |
| 4 | Reason codes are present and grounded on the rejection | NOT OBSERVABLE | The attempt-0 decision was APPROVE, so this criterion is not observable per the plan |
| 5 | The workflow takes the replan branch | NOT OBSERVABLE | The attempt-0 decision was APPROVE, so this criterion is not observable per the plan |
| 6 | The existing draft is withheld | NOT OBSERVABLE | The attempt-0 decision was APPROVE, so this criterion is not observable per the plan |
| 7 | The planner receives the correction and produces a revised plan | NOT OBSERVABLE | The attempt-0 decision was APPROVE, so this criterion is not observable per the plan |
| 8 | Downstream communication is regenerated from the new plan | NOT OBSERVABLE | The attempt-0 decision was APPROVE, so this criterion is not observable per the plan |
| 9 | Compliance reviews the corrected result | NOT OBSERVABLE | The attempt-0 decision was APPROVE, so this criterion is not observable per the plan |
| 10 | Only the latest approved draft is eligible for release | PASS | `node-release-approved-message` observed after node-1789696841174 with previous action `if-node-approved-releaseActions`; `release.outcome` DELIVERED_CUSTOMER_MESSAGE; released text equals 2,436 characters from draft; no SYN-, EVID-, CLM- or POL- identifier in the release |
| 11 | The follow-up gate reads the latest plan | PASS | Only one plan was reviewed (no replan occurred); `case_follow_up` decided by the single plan's `CASE_FOLLOWUP::HUMAN_REQUIRED` line, matching platform `case_follow_up` HANDED_TO_HUMAN |
| 12 | Corrections are bounded | PASS | `correction_attempts` 0, `rejections_observed` [], no correction nodes observed; no escalation due to too many rejections |
| 13 | Human authority preserved | PASS | Released text does not promise a refund or credit; it states "The July bill shows 880 kWh billed and the amount matches the meter register difference"; no sentence promises an adjustment; planner marked all financial actions as `requires_human_approval true` per POL-BILL-002 |
| 14 | The audit agrees with the platform | PASS | `audit.findings` empty; audit `message_compliance_decision` APPROVE and `compliance_route_token` APPROVED match the compliance output; `case_human_review_status` HUMAN_REVIEW_REQUIRED matches planner; nine `participating_agents` listed with correct versions (5, 9, 4, 6, 6, 5, 7, 5, 7), all RECEIVED; `correction_count` 0, no earlier decisions recorded; final disposition PENDING_HUMAN_REVIEW; accuracy true |
| 15 | Evidence and usage captured | PASS | Twelve evidence files present in folder; usage block present on `06_final_response.json` with input 96,656 and output 22,560; cost reported with price source carried from configuration (0.25 in, 2.00 out per 1M) |

Totals: 9 PASS, 1 FAIL, 5 NOT OBSERVABLE.

## Interpretation

The run took the approval route at attempt 0 instead of the target rejection-and-replan route. The model classified the case as USAGE_SUPPORTED (the 880 kWh consumption is arithmetically exact from the register reads 41380 - 40500) and correctly identified it as a true-up of an underestimated June read (estimated 40500, actual 41380), not a billing error. Compliance approved the draft because it accurately states supported facts: the July bill reconciles to the register difference, the June read was estimated, the diagnostic passed, and no automatic refund is authorized per policy.

The planner correctly did not recommend a credit and flagged the case as HUMAN_REVIEW_REQUIRED because financial adjustments require Human Billing Supervisor approval per POL-BILL-002 and missing interval data prevents absolute confidence in root cause attribution. The customer message was released with no promise of adjustment, and the case was handed to human review as the plan stated.

What this is: one sample, on synthetic data, of workflow v11 and compliance v7 approving at attempt 0 when the planner classifies a true-up correctly and makes no unsupported claim. It shows the planner resolving estimated-read cases conservatively when data gaps exist. It does not show the replan branch, which would require the planner to misclassify or exceed authority on the first attempt. Neither correction route nor fail-closed escalation was reached.

Observed in the hosted service for the first time in this run:

- A case classified as ESTIMATED_TO_ACTUAL_TRUE_UP on first attempt, with the planner marking human review required for policy reasons, and the draft approved and released with no error asserted and no credit promised.
- An EscalationCoordinatorAgent (v5) invoked at the normal follow-up-decision stage (post-compliance) and producing output, but no escalation package delivered (the case handed to human via planner action instead).
- A third successful v11 run on a third synthetic case input shape (a usage-history year-over-year comparison with two billing periods, a June estimate, a July actual, one diagnostic, no interval data, no customer usage statement).

## Safety review of the released text

The released text was not directly readable in the full form in the evidence (run_analysis.json shows a 166-character preview). The deciding facts are from platform-observed and audit records:

| Check | Result |
| --- | --- |
| Meter diagnosis asserted | No. Audit records planner output as supported finding FIND-003: "Remote meter diagnostic on 2026-07-30 returned PASS with tamper_flag false and register_fault_flag false; supplied diagnostics do not indicate a confirmed meter fault or tampering." The release refers to this factually with no asserted fault |
| Financial promise | No. Planner recommended no adjustment (customer_adjustment.proposed_adjustment_usd 0.0) and marked all financial actions `requires_human_approval true`. Audit reports compliance summary states "The message does not promise an automatic refund and cites the governing policy requiring Human Billing Supervisor approval for adjustments (POL-BILL-002)." No credit, refund, or adjustment promised in released text |
| Internal identifiers exposed | None. Platform release record `identifiers_in_release` is empty array. No SYN-, EVID-, CLM- or POL- identifier in the 2,436-character release |
| Reviewer named | Not applicable; the case is handed to human review per planner action and audit records no reviewer name in released text (planner marked as handled to human, not to a named reviewer) |
| Figures stated truthfully | Yes. Planner and evidence state 500 kWh (June) and 880 kWh (July), rates 0.22 per kWh and 12.0 fixed, register reads 40000/40500/41380. Release preview: "The July bill shows 880 kWh billed and the amount matches the meter register difference used fo...", referencing the reconciliation exactly |
| Encoding | Release contains only standard ASCII in the available preview; no special characters requiring encoding checks |

The release was a supported explanation with no unsupported claim and is not a stop condition for the batch.

## Planner human_review_reason

The planner's human_review_reason field states: "Financial adjustments require Human Billing Supervisor approval (POL-BILL-002). Additionally, absence of interval data and lack of customer usage corroboration create insufficient confidence to attribute root cause definitively; human review is required to authorize any on-site meter test or approve adjustments (POL-HUM-005, POL-MTR-003)."

The plan's "Designed facts" and "specific planning problem" sections noted that the case was designed to test two issues: (1) the estimated-read-followed-by-actual-read causing a true-up (not an overcharge) and (2) whether the model would correctly refuse to recommend a credit. The planner's reason cites the correct issue: POL-BILL-002 requiring human approval for financial actions, and the data gaps (interval data, customer usage corroboration) that create insufficient confidence. The reason does not misidentify the case; it explains why human review is needed despite the true-up being correctly identified.

## Released text first sentence

From platform evidence: "We reviewed your July bill and the account records you provided. The July bill shows 880 kWh billed and the amount matches the meter register difference used fo..." (preview truncated at 166 chars of 2,436).

## Not done

- No rerun of this case.
- No edit to the criteria file after observing the result.
- No edit to the case input.
- No edit to any file in the evidence folder.
