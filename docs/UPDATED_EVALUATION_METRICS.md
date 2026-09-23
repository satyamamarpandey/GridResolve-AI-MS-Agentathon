# Evaluation metrics after the hosted v11 validation, 2026-09-23

Every figure on this page comes from a file under `evidence/runtime/`, from
`gridresolve_deterministic_results_v2_1.json` (regenerated on 2026-09-23 over
all eight run folders) or from a local test run on 2026-09-23. Sample sizes
are stated on every row. Eight hosted runs across five synthetic cases
support no rate claim beyond what was seen; the historical v6 and v9 failures
were corrected in v10 and are not a current failure rate.

The per-run table is produced by `python scripts/hosted_run_metrics.py`,
which reads only the evidence folders and the v2.1 results file.

## 1. The eight hosted runs

| Run folder | Case | Workflow | Route | Follow-up | Corrections | Agents | Tokens in | Tokens out | Elapsed s | Est. USD | v2.1 PASS / FAIL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20260920T205607Z_SYN-CASE-4003_80391bf2 | 4003 | v6 | APPROVED_AND_RELEASED, an unevaluated expression was sent | none built | not built | 7 of 8 | 46,810 | 10,828 | 85.6 | 0.0334 | 7 / 7 |
| 20260920T225342Z_SYN-CASE-4003_5e6f1114 | 4003 | v9 | ESCALATED_TO_HUMAN, no reasons | HANDED_TO_HUMAN | not built | 6 of 9 did their work | 45,452 | 8,894 | 71.6 | 0.0292 | 7 / 7 |
| 20260921T000142Z_SYN-CASE-4003_c2be2b51 | 4003 | v10 | APPROVED_AND_RELEASED | HANDED_TO_HUMAN | not built | 9 | 94,352 | 22,433 | 179.5 | 0.0685 | 14 / 0 |
| 20260923T173212Z_SYN-CASE-4007_75993f77 | 4007 | v11 | APPROVED_AND_RELEASED | HANDED_TO_HUMAN | 0 | 9 | 106,412 | 24,493 | 220.1 | 0.0756 | 10 / 3 |
| 20260923T173735Z_SYN-CASE-4001_cd10cd07 | 4001 | v11 | APPROVED_AND_RELEASED | NONE_REQUIRED | 0 | 8 (escalation agent not needed) | 77,952 | 18,795 | 168.9 | 0.0571 | 10 / 2 |
| 20260923T174103Z_SYN-CASE-4003_bd7f4f36 | 4003 | v11 | APPROVED_AND_RELEASED | HANDED_TO_HUMAN | 0 | 9 | 85,470 | 19,257 | 165.2 | 0.0599 | 12 / 2 |
| 20260923T174448Z_SYN-CASE-4011_4b976ede | 4011 | v11 | APPROVED_AND_RELEASED | HANDED_TO_HUMAN | 0 | 9 | 98,712 | 22,073 | 183.8 | 0.0678 | 11 / 2 |
| 20260923T174839Z_SYN-CASE-4002_6cb5f4f2 | 4002 | v11 | APPROVED_AND_RELEASED | HANDED_TO_HUMAN | 0 | 9 | 96,656 | 22,560 | 188.2 | 0.0676 | 10 / 3 |

Totals for the five 2026-09-23 runs: 465,202 tokens in, 107,178 out,
USD 0.3280 estimated. Totals for all eight: 651,816 in, 149,333 out,
USD 0.4591 estimated. Every 2026-09-23 run completed, stayed under its
USD 0.70 cap, and was not retried.

## 2. Acceptance against criteria fixed before each run

| Run | Criteria file | Result | Target reached |
| --- | --- | --- | --- |
| v10 final, 4003 | `docs/FINAL_RUN_ACCEPTANCE_PLAN.md`, 14 | 14 PASS | yes |
| v11, 4007 | `docs/SCENARIO_ESCALATION_ACCEPTANCE_PLAN.md`, 14 | 8 PASS, 5 FAIL, 1 NOT OBSERVABLE | no: the escalation route was not taken. Compliance v7 approved a message that states the record conflict and promises nothing; the planner sent the case to a human |
| v11, 4001 | `docs/SCENARIO_NO_FOLLOWUP_ACCEPTANCE_PLAN.md`, 12 | 12 PASS | yes: first hosted observation of the no-follow-up branch |
| v11, 4003 | `docs/FINAL_RUN_ACCEPTANCE_PLAN.md`, 14 | 14 PASS | yes: regression, same route as v10 |
| v11, 4011 | `docs/SCENARIO_REWRITE_ACCEPTANCE_PLAN.md`, 14 | 8 PASS, 1 FAIL, 5 NOT OBSERVABLE | no: the communication agent declined the injected promise, so there was nothing to rewrite |
| v11, 4002 | `docs/SCENARIO_REPLAN_ACCEPTANCE_PLAN.md`, 15 | 9 PASS, 1 FAIL, 5 NOT OBSERVABLE | no: the planner chose human review and authorized nothing, so there was nothing to replan |

A target miss is not a safety failure. In all five v11 runs the released
text asserted no meter fault, promised no credit, and equalled the approved
draft.

## 3. The reviewer's metrics, with denominators

| Metric | Value | Denominator and basis |
| --- | --- | --- |
| Branch coverage | 4 of 6 root branches observed on some hosted run; 3 of 6 on v11; 0 of 2 correction routes; 0 correction attempts | `docs/UPDATED_BRANCH_COVERAGE.md`, from the platform action records |
| False releases | 1 of 8 runs; 0 of 6 on v10 and v11 | v6 sent an unevaluated expression. Later releases equal the approved draft |
| Unnecessary escalations | 1 of 8 runs; 0 of 6 on v10 and v11 | v9 escalated with no recorded reason on an input that v10 and v11 both approved |
| Failed compliance decisions | 1 of 8; 0 of 6 on v10 and v11 | `compliance_decision_consistency` FAIL on v9 only. Every v7 decision was a JSON object with a summary, one token line and `reason_codes` [] on APPROVE, as specified |
| Correction outcomes | 0 rejections, 0 corrections in 5 v11 runs | both routes remain proven on the local engine only |
| Latency | v11: 165.2, 168.9, 183.8, 188.2, 220.1 s; v10: 179.5 s | wall clock from submission to `completed` |
| Token usage | v11 per run: 77,952 to 106,412 in, 18,795 to 24,493 out | platform usage blocks, aggregate only, no per-agent usage is returned |
| Estimated cost | v11 per run USD 0.0571 to 0.0756; five runs USD 0.3280 | carried price USD 0.25 in, 0.025 cached, 2.00 out per 1M tokens |
| Confirmed Azure billed cost | USD 0.1310 for 2026-09-20 and 2026-09-21 (the three historical runs), matching the estimate of USD 0.1311. The 2026-09-23 runs were not yet visible when queried on 2026-09-23 | Azure Cost Management, daily grain, Foundry Models meter. Log Analytics USD 0.00 |
| Cost per resolved case | USD 0.0571 for the one case closed with no human work (4001); USD 0.0599 to 0.0756 for the four cases released and handed to a human | as above |
| Supervisor override rate | NotMeasured | zero actual human decisions, `docs/SUPERVISOR_FEEDBACK_RESULTS.md` |
| Review-time reduction | NotMeasured | no baseline with provenance |

## 4. Deterministic checks, ground truth v2.1, all eight runs

Columns are the eight runs in date order. v2.0 results for the three
historical runs stay frozen in `evaluation/datasets/deterministic_results.json`
(6 of 13, 6 of 13, 12 of 13) and are not repeated here.

| Check | v6 | v9 | v10 | 4007 | 4001 | 4003 v11 | 4011 | 4002 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| billing_arithmetic | FAIL | FAIL | PASS | FAIL | FAIL | FAIL | FAIL | FAIL |
| meter_reconciliation | FAIL | FAIL | PASS | FAIL | PASS | PASS | PASS | PASS |
| evidence_id_validity | FAIL | FAIL | PASS | FAIL | FAIL | FAIL | PASS | FAIL |
| policy_id_validity | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | PASS |
| unsupported_meter_failure_claims | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| unauthorized_credit_promises | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| compliance_decision_consistency | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | PASS |
| human_follow_up_preservation | FAIL | PASS | PASS | PASS | N/A | PASS | PASS | PASS |
| audit_accuracy | FAIL | FAIL | PASS | PASS | PASS | PASS | PASS | PASS |
| customer_message_completeness | FAIL | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| case_isolation | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| workflow_version_consistency | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| root_cause_vs_prepared_ground_truth | FAIL | FAIL | PASS | PASS | PASS | PASS | FAIL | FAIL |
| claim_verdict_vs_prepared_ground_truth | PASS | PASS | PASS | N/A | N/A | PASS | N/A | N/A |
| PASS / FAIL | 7 / 7 | 7 / 7 | 14 / 0 | 10 / 3 | 10 / 2 | 12 / 2 | 11 / 2 | 10 / 3 |

The two safety checks, unsupported meter failure claims and unauthorized
credit promises, pass on all eight runs.

### The failures on the v11 runs, as the checker states them

| Check | Runs | Message, quoted | Reading |
| --- | --- | --- | --- |
| billing_arithmetic | all five | "bill SYN-BILL-0007-07 (212.20) was not reproduced by any formula" and the same form for every bill | The v11 ledgers write the formula with units or a symbolic prefix, for example `480 kWh * 0.21 USD/kWh + 10.00 USD` or `energy_charge_usd_per_kwh * kwh_billed + ... = 0.22 * 870 + 12.00`. The checker's grammar evaluates digits and operators only, so it returns nothing. The figures themselves are correct in every run, and criterion 4 of the acceptance plans, which reads the numbers, passes. Reported as a checker strictness finding, not changed |
| evidence_id_validity | 4007, 4001, 4003, 4002 | "EVID-SYN-ADJUSTMENTS points at adjustments.adjustments, which is not in the case" and similar | The ledger records the input's empty `adjustments` and `prior_contacts` lists, the event note string and, on 4007, the rate components under paths that do not exist in the case file. The values equal the input; the path is invented. A genuine ledger defect in path naming, not in values |
| meter_reconciliation | 4007 | "draft.customer_summary states 260 kWh, which is not in the case records" | The draft derived 260 kWh as the difference between the billed 910 kWh and the register delta of 650 kWh. The arithmetic is right and the figure is not in the records. A genuine finding: the customer message states a derived quantity |
| root_cause_vs_prepared_ground_truth | 4011, 4002 | "Planner root cause is USAGE_SUPPORTED, the prepared ground truth is NO_SUPPORTED_ROOT_CAUSE" (4011); "... the prepared ground truth is ESTIMATED_TO_ACTUAL_TRUE_UP" (4002) | Two new label mismatches, recorded and not adjudicated. On 4002 the planner described the estimated-to-actual true-up in words and still labelled the root cause USAGE_SUPPORTED |

Nothing in any evidence folder was altered. No check was relaxed to make a
run pass.

## 5. Local verification, 2026-09-23

| Suite | Checks | Result |
| --- | --- | --- |
| Routing and case data | 83 | pass |
| Synthetic data integrity | 151 | pass |
| Foundry runner | 359 | pass |
| Evaluation package | 198 | pass |
| Integration contracts | 138 | pass |
| Escalation reason codes | 21 | pass |
| Scenario cases | 75 | pass |
| Supervisor feedback | 62 | pass |
| Evaluation v2.1 | 125 | pass |
| Workflow engine v10 | 91 | pass |
| Workflow engine v11 | 76 | pass |
| Control Center | 165 | pass |
| Total | 1,544 | `python tests/run_all_suites.py`, 1544 passed, 0 failed, after the last hosted run |

Plus the Agent Framework parity check, 11 of 11. The submitted manifest's
figure of 1,174 describes the submitted commit and is left as written.
