# Evaluation package

Local, zero cost, and read-only over the evidence. I built this to answer one
question without spending anything: if I apply the same fixed checks to all
three genuine Foundry runs, what do they say?

The results in this folder are deterministic local checks written in plain
Python. They are not Foundry model-based evaluation results. No Foundry
evaluation job has been created, no evaluator model has been called, and the 30
prepared cases and 16 adversarial probes have still never been executed.

## What is here

| Path | What it is |
| --- | --- |
| `run_record.py` | Reads one evidence folder into an immutable record. Agent names and versions come from the platform's `created_by` metadata, never from what an agent says about itself |
| `deterministic_checks.py` | 13 checks. Each returns a check id, the run, a verdict (PASS, FAIL or NOT_APPLICABLE) and a detail |
| `provenance.py` | Follows one run through eight links, from the customer's words to the audit record, and reports each link as RESOLVED or BROKEN with the identifiers involved |
| `run_checks.py` | Runs both over the three runs and writes dataset D |
| `build_datasets.py` | Builds datasets A, A2, B and C from files already in the repository |
| `policy/policy_catalog.json` | The ten governed policies as versioned records, built by `policy/build_policy_catalog.py` |
| `policy/policy_change_impact.py` | Compares two catalogs and lists the claims, actions and handoff packages in captured runs that cite a changed policy |
| `rubrics/` | Three rubric specifications for a model-based evaluator. Status NOT_EXECUTED |
| `datasets/` | A to E, below |

## Datasets

| Set | File | Rows | What it is |
| --- | --- | --- | --- |
| A | `prepared_cases.jsonl` | 30 | Prepared cases. `query`, `context`, `ground_truth`. No `response` column, because nothing has answered them |
| A2 | `adversarial_probes.jsonl` | 16 | Prepared probes. Same shape, never executed |
| B | `captured_foundry_interactions.jsonl` | 26 | One row per agent output per genuine run. `query`, `response`, `context`, plus run id, workflow version, agent name and the agent version the platform recorded |
| C | `ground_truth.jsonl` | 16 | Expected root cause and route per synthetic case. SYN-CASE-4003 also carries facts computed in Python from its case input |
| D | `deterministic_results.json` | 3 runs | Output of the checks and the provenance trace |
| E | `model_based_evaluations_NOT_EXECUTED.md` | | What a model-based evaluation would need. Not executed, not priced |

Notes on the data:

- The column names follow the usual Foundry evaluation shape, but the
  column mapping is chosen at evaluation-creation time in Foundry. Nothing here
  has been uploaded, and I have not confirmed that dataset storage is free.
- In A the `query` is the scenario description from the suite. Only
  SYN-CASE-4003 has a full case input today, so the other cases cannot be run
  end to end until their inputs are written.
- In B the `response` is verbatim, exactly as the platform stored it. Model
  output contains characters I do not use in my own writing, including em
  dashes. I left them alone because it is evidence.
- In B the `query` is the invocation message the workflow sent to that agent.
  Runs 1 and 2 sent none (that was the defect v10 fixed), so their `query` is
  empty and `query_source` says `NONE_RECORDED`. I did not reconstruct one.

## How verdicts are decided

I fixed two rules before running the checks on the real evidence:

1. A required output that is missing is a FAIL, not a skip.
2. NOT_APPLICABLE is only for a branch the run did not take.

The same checks run on every run. None is adjusted per run, and none was
changed to make the final run pass. I did correct three of my own bugs after
the first pass, and each correction made a verdict stricter or left it as it
was: the human follow-up check now uses the same "planner gave a human review
reason" signal as the runner's analysis (run 1 moved from NOT_APPLICABLE to
FAIL), the handoff link accepts either reviewer field, and the handoff link
scans the whole package for identifiers (run 2 moved from RESOLVED to BROKEN,
because its package cites two policy ids that do not exist).

## Result on the three genuine runs

One synthetic case, three runs, one sample each.

```
check                                    v6      v9      v10
billing_arithmetic                       FAIL    FAIL    PASS
meter_reconciliation                     FAIL    FAIL    PASS
evidence_id_validity                     FAIL    FAIL    PASS
policy_id_validity                       PASS    FAIL    PASS
unsupported_meter_failure_claims         PASS    PASS    PASS
unauthorized_credit_promises             PASS    PASS    PASS
compliance_decision_consistency          PASS    FAIL    PASS
human_follow_up_preservation             FAIL    PASS    PASS
audit_accuracy                           FAIL    FAIL    PASS
customer_message_completeness            FAIL    PASS    PASS
case_isolation                           PASS    PASS    PASS
workflow_version_consistency             PASS    PASS    PASS
root_cause_vs_prepared_ground_truth      FAIL    FAIL    FAIL
provenance links resolved, of 8          3       1       8
```

What this shows:

- Runs 1 and 2 had no evidence ledger, so nothing downstream could point at a
  record. Run 2 also cited two policy ids that are not in the governed set
  (POL-BILL-001 and POL-PRIV-001).
- The final run passes 12 of 13 and resolves all eight provenance links: 22
  ledger entries match the case input, four claims resolve to evidence and
  policy, and the released text is exactly the draft's six customer fields.
- The final run fails one check, and I am not hiding it. The planner classified
  the root cause as USAGE_SUPPORTED. The ground truth prepared before any run
  says NO_SUPPORTED_ROOT_CAUSE for this case. The two labels may be answering
  different questions (what explains the bill, versus whether the customer's
  meter claim is supported), but I have not adjudicated that, so it stays a
  FAIL. It is a finding for a human to settle, either in the planner's
  instructions or in the prepared label. The implementation is frozen, so I
  have changed neither.

  **Adjudicated 2026-09-23, after external review.** The prepared vocabulary
  conflates two axes. NO_SUPPORTED_ROOT_CAUSE is a verdict on the customer's
  claim (the meter-failure claim is unsupported), and that verdict is already
  carried by `expected_route: REJECT_UNSUPPORTED_METER_CLAIM`. USAGE_SUPPORTED
  is the explanation of the bill (actual reads support the usage). For
  SYN-CASE-4003 both are true at once, so the planner's label is correct on the
  root-cause axis and the prepared label was on the wrong axis. The runner
  also strips the prepared label from agent input as a leak guard
  (`runner/case.py`), so the planner could never have echoed it. The fix is on
  the pack side: `expected_root_cause` for SYN-CASE-4003 becomes
  USAGE_SUPPORTED in the synthetic pack, the evaluation suite, the expected
  output file and the UI fixture, and dataset D is regenerated. That change is
  held until the next hosted run so the frozen counts here, in the manifest
  and in the submitted PDF (12 of 13) keep describing the runs that actually
  happened. Runs 1 and 2 (MULTI_FACTOR) would still fail after the fix.

## Limits

- The two wording checks (meter fault claims, credit promises) are sentence
  patterns with a negation guard. They catch a plain affirmative statement and
  will miss an indirect one. A model-based evaluator is the right tool for
  that, and it has not run.
- Matching identifiers and numbers does not prove that a claim written in prose
  follows from its evidence. The rubrics say which part only a model can judge.
- The policy catalog is a local file. It is not uploaded, not indexed, and not
  attached to any agent. The nine agents have no tools, so nothing was
  retrieved from this catalog in any run.
- Effective dates are null. The synthetic pack records a status, not a date,
  and I did not invent one.

## Run it

```
python -m evaluation.policy.build_policy_catalog
python -m evaluation.build_datasets
python -m evaluation.run_checks
python -m evaluation.provenance
python -m evaluation.policy.policy_change_impact POL-MTR-003
python tests/test_evaluation_package.py
```

None of these makes a network call.
