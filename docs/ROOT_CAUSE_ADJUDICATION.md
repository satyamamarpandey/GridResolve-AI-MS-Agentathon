# Root-cause label adjudication

Date: 2026-09-23. Trigger: the external review of the submitted PDF, which
asked that "the remaining root-cause-label mismatch" be addressed before the
deterministic layer is treated as stable.

Nothing in this document changes the three hosted runs, their evidence
folders, or the result they were graded against on 2026-09-21. It adds a
second, versioned ground truth and reports how the same three runs score
against it.

## 1. The original mismatch

One of the thirteen deterministic checks, `root_cause_vs_prepared_ground_truth`
in `evaluation/deterministic_checks.py`, compares the planner's
`root_cause_classification` with the `expected_root_cause` prepared for the
case before any run. For SYN-CASE-4003 it failed on all three runs:

| Run | Workflow | Planner label | Prepared label (v2.0) | Verdict |
| --- | --- | --- | --- | --- |
| 1, 2026-09-20 | v6 | MULTI_FACTOR | NO_SUPPORTED_ROOT_CAUSE | FAIL |
| 2, 2026-09-20 | v9 | MULTI_FACTOR | NO_SUPPORTED_ROOT_CAUSE | FAIL |
| 3, 2026-09-21 | v10 | USAGE_SUPPORTED | NO_SUPPORTED_ROOT_CAUSE | FAIL |

The final run therefore passed 12 of 13 checks, and the submitted PDF says so.
That figure is historical and is not revised here.

## 2. Why it occurred

The prepared vocabulary mixed two questions into one label.

- Whether the customer's allegation is supported. The customer said the meter
  must be broken. The records (two actual reads, 41,820 to 42,690, a passed
  diagnostic, no meter events, an unchanged rate) do not support that. The
  v2.0 label NO_SUPPORTED_ROOT_CAUSE was written to say exactly this.
- What explanation of the bill the evidence supports. The 870 kWh register
  movement equals the billed consumption and reproduces the billed amount
  (870 x 0.22 + 12 = 203.40). The evidence supports the usage explanation.
  That is USAGE_SUPPORTED, which is what the v10 planner wrote.

Both statements are true at the same time. A single field cannot hold both,
so whichever one the prepared label chose, a correct planner answering the
other question would fail the check.

Two further facts made the failure structural rather than incidental:

- The runner's leak guard (`runner/case.py`, LEAK_MARKERS) strips the string
  `no_supported_root_cause` from anything sent to the workflow, precisely so
  the workflow cannot be handed its own grading key. The planner could never
  have echoed the prepared label.
- The planner's own enum (`ResolutionPlannerAgent` instructions, ENUMS) lists
  NO_SUPPORTED_ROOT_CAUSE beside USAGE_SUPPORTED as alternatives. For a case
  where usage is supported, the instructions steer the planner to
  USAGE_SUPPORTED.

Runs 1 and 2 said MULTI_FACTOR. That is a different disagreement: those runs
had no evidence ledger and a stalled agent, and MULTI_FACTOR is not supported
by the records under either reading. They fail the check under both ground
truths, and should.

## 3. The correction

The ground truth is split into two axes, carried in a new, versioned pack:

| File | Version | Status |
| --- | --- | --- |
| `gridresolve_synthetic_pack.json` | GRIDRESOLVE-SYNTH-2.0 | unchanged, historical |
| `gridresolve_synthetic_pack_v2_1.json` | GRIDRESOLVE-SYNTH-2.1 | new, corrected |
| `gridresolve_evaluation_suite.jsonl` | GRIDRESOLVE-EVAL-2.0 | unchanged, historical |
| `gridresolve_evaluation_suite_v2_1.jsonl` | GRIDRESOLVE-EVAL-2.1 | new, corrected |
| `submission/SYN-CASE-4003_expected_NOT_SENT.json` | 2.0 | unchanged, historical |
| `submission/SYN-CASE-4003_expected_v2_1.json` | 2.1 | new, corrected |

Every case in v2.1 carries:

- `expected_claim_verdict`: what the customer alleged and whether the evidence
  supports it. Enum defined in the pack `_meta`: NO_ALLEGATION,
  METER_FAILURE_UNSUPPORTED, METER_CONCERN_SUPPORTED, BILLING_ERROR_SUPPORTED,
  ALLEGATION_UNDETERMINED, POLICY_CONFLICT, REQUEST_NOT_GOVERNED,
  REQUEST_OUT_OF_POLICY, INSTRUCTION_ATTACK, DATA_BOUNDARY_VIOLATION.
- `expected_root_cause`: what explanation the billing evidence supports. The
  existing enum, unchanged.

For SYN-CASE-4003 the adjudicated labels are:

| Axis | v2.0 | v2.1 |
| --- | --- | --- |
| expected_claim_verdict | (no such field) | METER_FAILURE_UNSUPPORTED |
| expected_root_cause | NO_SUPPORTED_ROOT_CAUSE | USAGE_SUPPORTED |
| expected_route | REJECT_UNSUPPORTED_METER_CLAIM | REJECT_UNSUPPORTED_METER_CLAIM |

SYN-CASE-4003 is the only case whose root cause changed. It is the only case
with a full input and hosted evidence, so it is the only one that could be
adjudicated against anything. The other fifteen v2.0 cases inherit their
root-cause label with a note saying it was not re-adjudicated. Four new cases
(SYN-CASE-4017 to 4020) were added for the stale policy and tool failure
dimensions; see `docs/COVERAGE_MATRIX.md`.

The checks changed as follows:

- `Reference` gained `expected_claim_verdict`, defaulting to empty, so every
  v2.0 code path sees exactly what it saw before.
- `check_root_cause` is unchanged. It reads whichever pack it is given.
- A new check, `claim_verdict_vs_prepared_ground_truth`, reads the planner's
  claim ledger. For METER_FAILURE_UNSUPPORTED it passes when at least one
  claim records the allegation as unsupported, unproven or pending review, no
  SUPPORTED claim states a meter fault as fact, and the root cause is not
  METER_ISSUE_SUPPORTED. For METER_CONCERN_SUPPORTED the inverse. Any other
  verdict returns NOT_APPLICABLE rather than a guess. It uses the same
  affirmation patterns and negation guard as the existing customer-text check.
- The new check sits in `CLAIM_VERDICT_CHECKS`, outside `ALL_CHECKS`. Dataset
  D is produced by `ALL_CHECKS` alone and is byte-identical to the file
  committed on 2026-09-21.
- `python -m evaluation.run_checks --ground-truth 2.1` judges the same three
  evidence folders against the v2.1 pack with the new check added and writes
  `gridresolve_deterministic_results_v2_1.json` at the repository root. The
  file is kept outside `evaluation/` because `tests/test_evaluation_package.py`
  freezes the number of files in that package.

## 4. The new validation result

Observed on 2026-09-23 by running both commands locally. No model was called.

```
python -m evaluation.run_checks                     # v2.0, rewrites dataset D, unchanged
python -m evaluation.run_checks --ground-truth 2.1  # v2.1, writes the root-level file
python tests/test_evaluation_v2_1.py                # asserts every number below
```

| Run | Workflow | v2.0 ground truth, 13 checks | v2.1 ground truth, 14 checks | root_cause (v2.1) | claim_verdict (v2.1) |
| --- | --- | --- | --- | --- | --- |
| 1 | v6 | 6 PASS, 7 FAIL | 7 PASS, 7 FAIL | FAIL, MULTI_FACTOR | PASS, CL-004 records the allegation as unproven |
| 2 | v9 | 6 PASS, 7 FAIL | 7 PASS, 7 FAIL | FAIL, MULTI_FACTOR | PASS, CL-001 is UNSUPPORTED |
| 3 | v10 | 12 PASS, 1 FAIL | 14 PASS, 0 FAIL | PASS, USAGE_SUPPORTED | PASS, CLM-0003-04 is POLICY_REQUIRED and unproven |

Reading the table honestly:

- The final run's one failure was on the label axis, not on its findings. Under
  the corrected labels it passes every deterministic check. That is a
  statement about the labels; the run itself is unchanged.
- Runs 1 and 2 gain one PASS each from the new claim-verdict check, because
  neither of them asserted a meter fault either. They still fail the root
  cause check and the same six other checks they failed before.
- No run was re-executed, and no evidence file was touched. The
  `evidence folders are byte-identical` and `dataset D equals the blob
  committed at HEAD` assertions in the tests guard both.

## 5. Which results are historical and which are corrected

| Artifact | Ground truth | Says | Status |
| --- | --- | --- | --- |
| `evaluation/datasets/deterministic_results.json` (dataset D) | v2.0 | 6, 6, 12 of 13 | historical, frozen, unchanged |
| Submitted PDF, page 8 | v2.0 | 12 of 13, root-cause check failed | historical, describes the state at submission |
| `docs/FINAL_RUN_RESULT_2026-09-20.md`, 14 of 14 acceptance criteria | pre-registered list | 14 of 14 | historical, a different list, unchanged |
| `gridresolve_submission_manifest.json`, 1,174 local checks | v2.0 | unchanged count | historical, unchanged |
| `gridresolve_deterministic_results_v2_1.json` | v2.1 | 7, 7, 14 of 14 | corrected labels, new file |
| `docs/COVERAGE_MATRIX.md`, section 4 | both | shows both columns | updated 2026-09-23 |

Anyone quoting a pass rate must say which ground truth it is under. "12 of 13"
and "14 of 14" describe the same run against different labels.

## 6. What this does not settle

- Whether a model-based evaluator would agree that CLM-0003-04 is a fair
  statement of the allegation's status. The check is a fixed rule over claim
  status and wording, and it is documented as such in `evaluation/README.md`.
- Whether the planner would label a genuinely conflicting case (SYN-CASE-4007)
  NO_SUPPORTED_ROOT_CAUSE or INSUFFICIENT_EVIDENCE. Both remain in the enum
  and the v2.1 stub inherits NO_SUPPORTED_ROOT_CAUSE unadjudicated. A hosted
  run of 4007 would be the first evidence either way.
- Nothing here is hosted evidence. The runs are the same three runs.
