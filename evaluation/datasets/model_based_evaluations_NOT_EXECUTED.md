# Dataset E: model-based evaluations

Status: NOT EXECUTED

No Foundry evaluation job has been created or run for this project. No
evaluator model has been called. There are no model-based results to report,
and nothing in this folder should be read as one.

## What is prepared

| Item | File | Rows | State |
| --- | --- | --- | --- |
| Prepared cases | `prepared_cases.jsonl` | 30 | Prepared, never executed |
| Adversarial probes | `adversarial_probes.jsonl` | 16 | Prepared, never executed |
| Captured interactions | `captured_foundry_interactions.jsonl` | 26 | Real outputs from three runs. Could be graded by an evaluator without running the workflow again |
| Ground truth | `ground_truth.jsonl` | 16 | Expected outcomes from the synthetic pack |
| Rubrics | `../rubrics/` | 3 | Written, never applied by a model |

## Why it has not run

Every model-based evaluator is a model call, and a model call is billed. My
spending approvals covered three workflow runs and nothing else. Running the 30
cases end to end would also need a full case input for each one, and only
SYN-CASE-4003 has one today.

## Cost

Cost: not priced here. I have not estimated it, because an estimate from me
would look like a quote. It depends on the evaluator model, the number of
evaluators per row and the token count of each row, and it needs a new spending
approval with a specific dollar amount before anything starts.

## What would count as executing it

1. Upload a dataset to the Foundry project (check first whether dataset storage
   is billed).
2. Create an evaluation, choose the column mapping there, and choose the
   evaluators.
3. Run it once, capture the job id and the per-row output, and store them next
   to the three run folders as evidence.

Until those three things exist, the status stays NOT EXECUTED.
