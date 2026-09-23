# Supervisor feedback loop: results as of 2026-09-23

This page reports what the supervisor feedback mechanism has recorded and
measured. The short answer: the mechanism is implemented and locally verified,
and it has recorded zero actual human decisions, so both metrics the reviewer
asked for are reported as NotMeasured. Nothing on this page is a supervisor
decision. The design is in `docs/SUPERVISOR_FEEDBACK_LOOP.md`.

## What exists

| Component | Where | Verified by |
| --- | --- | --- |
| Immutable review record with record kind `OFFLINE_SIMULATION` or `ACTUAL_HUMAN_REVIEW`, decision, agreement with the agent recommendation, override reason, start and completion timestamps | `integration/supervisor_feedback.py` | `tests/test_supervisor_feedback.py`, 62 checks, all passing on 2026-09-23 |
| Append-only store on the hash-chained audit log, one record per case and evidence package, reviewer-only permission | same | same |
| `override_rate(records)`: a rate only over `ACTUAL_HUMAN_REVIEW` records, otherwise `NotMeasured` | same | same |
| `review_time_reduction(records, baseline)`: a value only over actual reviews with a measured duration and a baseline that carries its source, date and sample size, otherwise `NotMeasured` | same | same |
| Control Center view showing the one simulated record and both metrics as Not measured | `control-center/` | Control Center suite, 165 checks |

## What has been recorded

| Record kind | Count | Source |
| --- | --- | --- |
| `ACTUAL_HUMAN_REVIEW` | 0 | No reviewer has used the mechanism. No hosted run's escalation package has been reviewed by a person |
| `OFFLINE_SIMULATION` | 1 | Hand-written to show the shape in the Control Center. Not a decision anyone made |

The five hosted runs of 2026-09-23 produced four escalation packages
(SYN-CASE-4007, SYN-CASE-4003, SYN-CASE-4011 and SYN-CASE-4002 each handed the
open investigation to a named human reviewer role, a Billing Supervisor or a
Meter Operations Specialist) and one case with no human work item
(SYN-CASE-4001). Each package names the decision a person must take.
None has been taken. The packages are in the run folders under
`evidence/runtime/` as the EscalationCoordinatorAgent output.

## Metrics

Computed on 2026-09-23 by calling the functions with the records that exist.

| Metric | Result | Reason returned by the function |
| --- | --- | --- |
| Supervisor override rate | NotMeasured | "No actual human decision has been recorded. Simulated records are excluded from the rate." actual_records 0, simulated_records 0 counted toward the rate |
| Review-time reduction | NotMeasured | "No comparable baseline with provenance was supplied. A baseline is never invented." actual_records 0 |
| Agreement rate between human decision and agent recommendation | NotMeasured | Same as the override rate; it is the complement of the same zero-record set |

## What would change these results

1. A named reviewer, in a session issued to that person with the
   `RECORD_REVIEW` permission, records a decision against one of the four
   escalation packages above. The store then holds one `ACTUAL_HUMAN_REVIEW`
   record and the override rate becomes a rate over n = 1, reported with that
   denominator.
2. A review-time baseline is measured in the utility's current process and
   supplied with its source, measurement date and sample size. Until then the
   reduction stays NotMeasured by construction.

Neither step happened. No pilot has started, and the system is not
production-ready.

## Rules kept

- No supervisor decision was invented, simulated as real, or inferred from an
  agent output.
- `OFFLINE_SIMULATION` and `ACTUAL_HUMAN_REVIEW` remain distinct in the record
  type, the store, the metrics and the Control Center.
- The metric functions refuse to report without actual decisions and a
  provenanced baseline. This was re-run on 2026-09-23 and the refusal text
  above is what they returned.
