# Supervisor feedback loop

Added 2026-09-23 in response to the external review: "add a compact supervisor
feedback loop that records whether the evidence package reduced review time and
whether the final decision agreed with the agent's recommendation."

Status: implemented and tested locally. Not used. No supervisor has reviewed a
GridResolve case, so nothing below is a measurement.

## Where it lives

| Path | What it is |
| --- | --- |
| `integration/supervisor_feedback.py` | The record, the store, the metrics. Standard library only, no network, no model |
| `integration/auth.py` | One new permission, `RECORD_REVIEW`, held by `HUMAN_REVIEWER` and `HUMAN_BILLING_SUPERVISOR` only |
| `tests/test_supervisor_feedback.py` | 62 deterministic checks on a fixed clock |
| `control-center/src/views/SupervisorFeedback.tsx` | The Control Center view, under Governance, showing one simulated record and two metrics marked Not measured |
| `control-center/src/views/SupervisorFeedback.test.tsx` | 9 view and metric checks |

## The record

`HumanReviewRecord`, a frozen dataclass. Every field is required unless stated.

| Field | Meaning |
| --- | --- |
| `case_id` | `SYN-CASE-NNNN` |
| `evidence_package_ref` | The escalation package or run the reviewer read, for example a `wfresp_` id or an evidence folder name |
| `agent_recommendation` | The route or decision the agents produced |
| `human_decision` | What the person decided |
| `agreement` | `AGREE` or `DISAGREE`. Derived from the two fields above after trimming and case folding. The caller cannot supply it |
| `review_started_at`, `review_completed_at` | ISO 8601 with a UTC offset, taken from the injected clock |
| `review_duration_seconds` | Computed from the two timestamps. Only set when both exist and completion is not before start; `duration_note` says how |
| `override_reason` | Required when `agreement` is `DISAGREE` |
| `reviewer_comments` | Optional |
| `final_disposition` | For example `PENDING_HUMAN_REVIEW` |
| `reviewer_principal_id` | Taken from the session the store resolved, never from an argument |
| `reviewer_role` | One of the review roles in `integration/contracts.py` |
| `record_kind` | `ACTUAL_HUMAN_REVIEW` or `OFFLINE_SIMULATION`. A field on the record, not a comment or a file name |

## Rules the tests prove

1. Only a session resolved to a human review role holding `RECORD_REVIEW` may
   record. An agent, the workflow service and an auditor are refused, and each
   refusal is appended to the case's audit chain with the principal that tried.
2. One record per `(case_id, evidence_package_ref)`. A second one, from anyone,
   is refused with `DuplicateFeedback`.
3. A missing decision (`MissingDecision`), a missing or malformed timestamp
   (`MissingTimestamp`, `ValidationError`) and a completion earlier than the
   start (`TimestampOrder`) are refused. Nothing is defaulted.
4. A disagreement without an override reason is refused
   (`MissingOverrideReason`).
5. Every accepted record is appended to the hash-chained audit record with
   action `HUMAN_REVIEW_RECORDED`, the reviewer as the actor, and the package,
   decision, agreement and record kind in the detail. The chain verifies after
   every write, and an edited entry is detected.
6. The store has no method that changes or drops a record. Returned collections
   are tuples of frozen records.

## Metrics, and why they are not reported

`override_rate(records)` returns a rate only when at least one
`ACTUAL_HUMAN_REVIEW` record exists. Simulated records are excluded from the
rate and counted separately. With zero actual records it returns a `NotMeasured`
result that names the metric and the reason.

`review_time_reduction(records, baseline)` returns a value only when a
`ReviewTimeBaseline` is supplied that carries its own source, measurement date
and sample size, and only over actual reviews with a measured duration. With no
baseline, or with only simulated durations, it returns `NotMeasured`. A baseline
is never invented and a simulated duration is never used.

**No supervisor override rate and no review-time reduction can be reported
today, because zero actual human decisions have been recorded.** The Control
Center shows both metrics as Not measured with those reasons.

## Simulated versus actual

The one record shown in the Control Center is `OFFLINE_SIMULATION`, written by
hand to show the shape. The test file builds records marked
`ACTUAL_HUMAN_REVIEW` as fixtures so the metric arithmetic can be checked; they
are harness fixtures, not decisions anyone made. The first genuine record would
be written by a named reviewer, in a session issued to that person, against the
escalation package of a hosted run, with the clock's real timestamps.

## Not done

- No reviewer has used it. No case has been reviewed.
- The Control Center view is read-only. It records nothing, because a decision
  recorded in a browser on synthetic data would not be an actual human review.
- No baseline for review time exists. Measuring one is a pilot activity.
