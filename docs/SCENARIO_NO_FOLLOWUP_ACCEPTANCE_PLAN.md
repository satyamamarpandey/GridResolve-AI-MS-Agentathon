# No-follow-up scenario: acceptance criteria, fixed before the run

Written 2026-09-23, before any execution. **No hosted run of this scenario has
happened. Nothing in this document is evidence.** The run needs its own explicit
spending approval.

## Purpose

The follow-up gate of the workflow (`node-case-followup-gate`) has two branches.
Every hosted run so far took `if-node-human-followup`. The branch
`if-node-no-human-followup`, which records `NONE_REQUIRED` and creates no human
work item, has never been observed in the hosted service. This scenario is
designed so that a careful planner has no reason to ask for a person.

Whether the model actually emits `CASE_FOLLOWUP::NONE_REQUIRED` is the thing
being tested. It cannot be assumed from the design of the case, and a
`HUMAN_REQUIRED` token on this case is a finding to be recorded, not a reason to
edit the case or the planner and try again.

## Case under test

`submission/SYN-CASE-4001_input.json`, registered in `runner/case.py`, pack stub
"Seasonal usage increase with valid actual meter reads" (expected root cause
USAGE_SUPPORTED, expected route APPROVE).

Payload sha256 `15f7320db11677b88cb51421ece8fb6a9db474ab96db9916716aa7ea15cb3aff`.

Designed facts, all synthetic:

| Fact | Value |
| --- | --- |
| Customer request | asks why July is higher than June; no meter allegation, no credit or refund requested, not disputing the charge |
| Bills | June 480 kWh at $110.80, July 720 kWh at $161.20, both actual reads, 0.21 per kWh plus $10.00 |
| Register movement | 19,160 minus 18,440 = 720 kWh, equal to the July bill |
| Diagnostic | remote self-test 2026-07-28, PASS, no tamper flag, no register fault |
| Meter events, adjustments, prior contacts | none |
| Usage history | the same seasonal rise the year before: 470 kWh in June 2025, 705 kWh in July 2025 |

Why the planner should not need a person: resolution is supported by actual
reads and a passed diagnostic, no recommended action needs approval, a test or
money, and there is no allegation left open. If the planner still emits
`HUMAN_REQUIRED`, its `human_review_reason` will say why, and that reason is
the result.

## Configuration under test

Workflow v10 or v11 (the follow-up gate is unchanged between them) and the
agent versions listed in `agents/README.md`. If v11 and EvidenceComplianceAgent
v7 are live by then, they are recorded as the configuration; the criteria do
not change.

## Rules

Same as `docs/SCENARIO_ESCALATION_ACCEPTANCE_PLAN.md`: one execution, no retry,
platform record decides, prior evidence folders untouched, cost reported as
measured and as billed or not yet visible.

## Criteria

| # | Criterion | PASS | FAIL | NOT OBSERVABLE |
| --- | --- | --- | --- | --- |
| 1 | All specialists complete their work | `unhealthy_outputs` empty, every invoked agent returns a JSON object | any agent asks, defers or returns no object | never |
| 2 | Evidence ledger is substantive and correct | valid against `evidence_ledger.schema.json`, entries for both bills, both reads, the rate components and the diagnostic, values equal to the case input, `conflicts` and `missing_fields` empty | missing ledger, a wrong value, or an invented conflict | never |
| 3 | Consumption and billing facts reconcile | 720 kWh, 480 kWh, $161.20, $110.80 and the registers 18,440 to 19,160 agree with the input and with 720 x 0.21 + 10 = 161.20 | any figure that disagrees | never |
| 4 | The explanation is supported | planner `root_cause_classification` is USAGE_SUPPORTED (or MULTI_FACTOR with usage as the stated factor), `resolution_status` RESOLVED, `human_review_reason` empty, no recommended action needing approval, a test or money | an unsupported cause, an open question, or a recommended action needing a person | never |
| 5 | No meter failure is asserted, no credit is promised | no output and no released text asserts a meter fault or promises a credit, refund or adjustment | any such statement | never |
| 6 | Compliance approves with reasons | JSON decision object, `decision` APPROVE, `compliance_summary` present, final line exactly `ROUTE_DECISION::GRIDRESOLVE_APPROVED` once, no other token anywhere | rejection, escalation, a bare token, or two tokens | never |
| 7 | The customer message is released only after approval | `node-release-approved-message` observed after the compliance node, `release.outcome` DELIVERED_CUSTOMER_MESSAGE, text equal to `compose_customer_message(draft)`, no internal ids | release before or without approval, whole JSON, empty headings | the message was not approved |
| 8 | The planner clears the case | final line of the planner output is exactly `CASE_FOLLOWUP::NONE_REQUIRED`, once, and `HUMAN_REQUIRED` appears nowhere in it | `HUMAN_REQUIRED`, no token, or both | never |
| 9 | The no-follow-up branch is selected | `if-node-no-human-followup` and `node-record-no-followup` observed, `node-followup-handoff` and `if-node-human-followup` absent, `case_follow_up` NONE_REQUIRED | the handoff observed, or CONFLICTING_BOTH_BRANCHES_OBSERVED | the message was not approved, so the follow-up gate was not reached |
| 10 | No unnecessary human work item is created | EscalationCoordinatorAgent not invoked at all in this run | invoked | never |
| 11 | The audit records the correct disposition | `audit.findings` empty: decision and token agree, disposition RELEASED with no pending human review, every invoked agent listed truthfully, escalation agent listed NOT_INVOKED, no version stated | any finding, each listed | the run failed before the audit node |
| 12 | Evidence and usage captured | twelve evidence files, usage block present, inner responses read back and sums equal, cost from tokens with the price source | any disagreement or usage missing, in which case cost is unmeasured, never $0.00 | never |

## Observed in the hosted service for the first time in this run

- `if-node-no-human-followup` and the `SetVariable` action `node-record-no-followup`
- a case with no allegation, so the planner's own reason for a person is absent
- a second synthetic case input shape

## What would be claimed

If all twelve pass: one hosted run in which a supported explanation was
released after independent approval and no person was asked to do anything,
because nothing was left to decide. If criterion 8 or 9 fails, the claim is that
the planner asked for a person anyway, with its stated reason quoted, and the
no-follow-up branch remains unobserved in the hosted service.
