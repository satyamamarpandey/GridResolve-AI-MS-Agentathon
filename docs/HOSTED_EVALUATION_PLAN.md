# Hosted evaluation plan

Written 2026-09-23. Status: PREPARED, NOT EXECUTED. No case in this plan has
been run on the hosted service since the three runs of SYN-CASE-4003 on
2026-09-20 and 2026-09-21. Every "actual" column below is blank on purpose.
A prepared test is not an executed test, and this document must not be read
as evidence of anything except what was planned and what it will cost.

Sources: `gridresolve_synthetic_pack_v2_1.json` (20 cases),
`gridresolve_evaluation_suite_v2_1.jsonl` (36 rows),
`gridresolve_red_team_pack_v2_1.jsonl` (18 probes), the readiness field on
each, and `docs/COST_ESTIMATE_SYN-CASE-4003.md` for prices.

## 1. Readiness, as it stands

| Readiness | Cases | Which | Meaning |
| --- | --- | --- | --- |
| READY_HOSTED | 3 | SYN-CASE-4001, SYN-CASE-4003, SYN-CASE-4007 | A full case input exists under `submission/` and passes `runner.case` validation |
| READY_LOCAL | 2 | SYN-CASE-4019, SYN-CASE-4020 | The behaviour is exercised locally against `integration/reliability.py` in `tests/test_evaluation_v2_1.py`. The hosted agents have no tools, so these cannot run hosted today |
| PREPARED_ONLY | 15 | the rest | A stub with expected outcomes and no input file |

Probes: 17 PREPARED_ONLY, 1 READY_LOCAL (RT-15, the third gate term in
`tests/test_workflow_engine.py`). No probe harness exists for the hosted
service; a probe run would need the probe text placed in a case's
`customer_request` and a full input written around it.

Only the three READY_HOSTED cases can be executed after approval. Nothing else
can be counted, planned into a budget, or reported as run.

## 2. Ordered execution list, READY_HOSTED only

Order is by what each run proves and by cost of a wrong result. Each run needs
its own explicit spend approval; the runner refuses to start without it.

| Order | Case | Workflow | Why this order | Expected outcome, fixed before execution |
| --- | --- | --- | --- | --- |
| 1 | SYN-CASE-4007 | v11 (after publish) or v10 | Exercises the escalation gate with a genuine record conflict (register delta 650 kWh against 910 kWh billed, no diagnostic). Proves reason codes on a real escalation, which run 2 never gave | Route ESCALATED_TO_HUMAN. No release action. Compliance decision HUMAN_REVIEW_REQUIRED or REJECT_AND_REPLAN with reason codes RECORD_CONFLICT and EVIDENCE_GAP citing ids that exist in the ledger. Escalation package present. Audit records the escalation. Claim verdict ALLEGATION_UNDETERMINED; root cause NO_SUPPORTED_ROOT_CAUSE or INSUFFICIENT_EVIDENCE, either accepted, recorded which |
| 2 | SYN-CASE-4001 | v11 or v10 | Exercises the never-observed no-follow-up branch. The customer alleges nothing and asks for nothing | Route APPROVED_AND_RELEASED. Follow-up branch `if-node-no-human-followup`, action `node-record-no-followup`, no handoff. Planner token CASE_FOLLOWUP::NONE_REQUIRED. Root cause USAGE_SUPPORTED, claim verdict NO_ALLEGATION. Whether the model emits NONE_REQUIRED is the thing under test and is not assumed |
| 3 | SYN-CASE-4003 | v11 (after publish) | Regression of the one known-good case on the new workflow. Same input as the three historical runs | Same as run 3 of 2026-09-21: released, follow-up handed to a human, 14 of 14 under v2.1 ground truth. Any difference is a finding about v11, not about the case |

Runs of v11 require the workflow and the compliance agent v7 to be published
first. Publishing is a control-plane write, not a model call; it is listed in
the approval request as its own step.

## 3. Cost, upper bound

Superseded on 2026-09-23 by docs/PREFLIGHT_V11_2026-09-23.md, section 1,
which reconciles this table against the measured final run, the v11 tree
and the billed figure now visible in Azure Cost Management. The figures
that page adopts: applicable estimate USD 0.07 to 0.13 per run, conservative
bound USD 0.37 per run (USD 1.10 for three), runner cap USD 0.70 per run.
The earlier bound of USD 1.30 for three runs assumed 200,000 output tokens
per run and is withdrawn.

Charges outside model tokens: Application Insights and Log Analytics
ingestion, pay per GB, no daily cap set, billed USD 0.00 so far. No evaluation
job, embedding, search or storage is created by these runs.

## 4. Record template, one row per executed case

Columns are fixed. A row is added only when a run has finished and its
evidence folder exists under `evidence/runtime/`. Until then the table stays
exactly like this.

| Case id | Expected outcome | Actual outcome | Workflow version | Model version | Release status | Human handoff status | Audit status | Failed checks | Reason codes | Latency | Estimated cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SYN-CASE-4007 | ESCALATED_TO_HUMAN, no release, RECORD_CONFLICT + EVIDENCE_GAP | NOT EXECUTED | NOT EXECUTED | NOT EXECUTED | NOT EXECUTED | NOT EXECUTED | NOT EXECUTED | NOT EXECUTED | NOT EXECUTED | NOT EXECUTED | NOT EXECUTED |
| SYN-CASE-4001 | APPROVED_AND_RELEASED, no-follow-up branch, no handoff | NOT EXECUTED | NOT EXECUTED | NOT EXECUTED | NOT EXECUTED | NOT EXECUTED | NOT EXECUTED | NOT EXECUTED | NOT EXECUTED | NOT EXECUTED | NOT EXECUTED |
| SYN-CASE-4003 | APPROVED_AND_RELEASED, handoff, 14 of 14 (v2.1) | NOT EXECUTED | NOT EXECUTED | NOT EXECUTED | NOT EXECUTED | NOT EXECUTED | NOT EXECUTED | NOT EXECUTED | NOT EXECUTED | NOT EXECUTED | NOT EXECUTED |

How each column is filled, when it is:

- Actual outcome, release status, human handoff status: from
  `09_route.json` and `11_run_analysis.json`, platform-observed action ids
  only. Never from what an agent says about itself.
- Workflow version, model version: from the platform `created_by` metadata in
  `07_conversation_items.json` and the deployment record.
- Audit status: `audit_accuracy` check verdict plus the runner's audit
  cross-check findings count.
- Failed checks: names from `python -m evaluation.run_checks --ground-truth 2.1`
  once the new folder is included.
- Reason codes: from the compliance decision object, validated by
  `check_escalation_reason_codes`. Empty is a FAIL on an escalated run.
- Latency: `Elapsed` in `10_usage_report.md`.
- Estimated cost: token counts from the platform at the verified prices,
  labelled estimated, never reconciled here with Azure billing.

## 5. The remaining 15 cases and 17 probes

They stay PREPARED_ONLY until each has a full case input in the canonical
shape (`submission/SYN-CASE-4003_input.json`) that passes the runner's
allowlist and leak checks. Writing those inputs costs nothing and can be done
one case at a time. The prior estimate for running all of them once, about 8
USD for the suite and 4 USD for the probes, is carried over from
`docs/FINAL_VALIDATION_REPORT.md` and remains a projection.

The two tool-failure cases (SYN-CASE-4019, SYN-CASE-4020) and the tool-failure
probe (RT-18) cannot become READY_HOSTED on the current agents at all, because
no agent has a tool attached. They would need a tool-enabled agent version,
which is a design change and is not planned in this document.

## 6. What must be true before the first run

1. Explicit written approval naming the case, the workflow version and the
   dollar cap, in that form. The runner's `--confirm` and `--max-usd` flags
   are set from that text.
2. The acceptance criteria for the case, already written in
   `docs/SCENARIO_ESCALATION_ACCEPTANCE_PLAN.md` and
   `docs/SCENARIO_NO_FOLLOWUP_ACCEPTANCE_PLAN.md`, are not edited after the
   run starts.
3. The evidence folder is written by the runner and then never modified.
4. If a run exceeds its cap or the platform bills something unexpected, the
   batch stops and the remaining rows stay NOT EXECUTED.
