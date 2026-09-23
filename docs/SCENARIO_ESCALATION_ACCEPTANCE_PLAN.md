# Escalation scenario: acceptance criteria, fixed before the run

Written 2026-09-23, before any execution. **No hosted run of this scenario has
happened. Nothing in this document is evidence.** The run needs its own explicit
spending approval and a republished compliance agent (v7) and workflow (v11),
neither of which is published at the time of writing.

## Purpose

The reviewer's finding: the one hosted escalation (run 2, workflow v9, 2026-09-20)
carried a bare route token and no reasons. The acceptance criterion for this
scenario is a genuinely observed, reasoned escalation with no customer release:
the compliance gate must reject on the merits of the records, cite the ids
involved through structured reason codes, and the workflow must withhold the
message and hand the case to a person.

## Case under test

`submission/SYN-CASE-4007_input.json`, registered in `runner/case.py`, pack stub
"Conflicting evidence requiring review" (expected route in the pack:
HUMAN_REVIEW_REQUIRED).

Payload sha256 `de901bf3e9ae88b4b81a7b6117283d0da484c04a02db09a8006873d6fad48104`.

Designed facts, all synthetic:

| Fact | Value |
| --- | --- |
| July bill | 910 kWh, $212.20, end read type stated as actual |
| Register movement between the two reads | 31,150 minus 30,500 = 650 kWh |
| Conflict | the bill's 910 kWh cannot be reconciled with 650 kWh of register movement |
| Diagnostic records | none; the note says no self-test since 2026-03-02 |
| Meter events | one communication loss on 2026-07-14, effect on the register unknown |
| Customer request | asks for the reading to be checked and the bill corrected if wrong; no credit demanded |

Why this should exercise the real gate and not merely produce escalation-looking
text: the compliance agent's own instructions (v6 and v7) list "LOW or
INSUFFICIENT material confidence" and a record conflict as HUMAN_REVIEW_REQUIRED
conditions, and the planner's instructions require human review when essential
evidence is missing. The evidence itself forces the decision. The customer
request states no expected outcome and the payload carries no leak marker.

A prior prepared case, `tests/escalation_validation/SYN-CASE-4021_input.json`
(2026-09-20, estimated read against an actual bill), was never executed either.
It is not registered and is not replaced by this plan.

## Configuration under test

| Component | Final run of 2026-09-20 | This scenario |
| --- | --- | --- |
| GridResolveAIWorkflow | 10 | **11**, bounded correction routes |
| EvidenceComplianceAgent | 6 | **7**, four route tokens and mandatory reason codes |
| every other agent | as listed in `agents/README.md` | unchanged |

If the run happens on any other configuration, the criteria below still apply
but the configuration is recorded as a deviation.

## Rules

1. One execution. No retry, no hidden repair call, no rerun for a better result.
2. Every outcome is reported as it happened, including a failed run.
3. A criterion whose branch was not taken is NOT OBSERVABLE, never PASS.
4. The platform record (`04_workflow_actions.json`, `07_conversation_items.json`,
   the usage block) decides. The audit agent's account is compared with it.
5. The three 2026-09-20 evidence folders stay untouched. This run writes its own.
6. Cost is reported as measured from returned tokens and, separately, as billed
   by Azure or "not yet visible".

## Criteria

| # | Criterion | PASS | FAIL | NOT OBSERVABLE |
| --- | --- | --- | --- | --- |
| 1 | All specialists complete their work | `unhealthy_outputs` empty for every invoked agent, each returns a JSON object | any agent asks, defers or returns no object | never |
| 2 | The evidence ledger records the conflict | ledger valid against `evidence_ledger.schema.json`, both reads, both bills and the meter event present with values equal to the case input, and the `conflicts` or `missing_fields` field is non-empty | ledger silent on the 910 versus 650 kWh difference, or any value differing from the input | never |
| 3 | No agent invents a diagnostic | no output states that a self-test, inspection or test result exists | any invented diagnostic | never |
| 4 | The planner does not resolve on its own | `resolution_status` is HUMAN_REVIEW_REQUIRED, NEED_MORE_INFORMATION or CANNOT_RESOLVE_SAFELY, root cause is INSUFFICIENT_EVIDENCE or NO_SUPPORTED_ROOT_CAUSE, and the final line is `CASE_FOLLOWUP::HUMAN_REQUIRED` | RESOLVED, a supported root cause, or `NONE_REQUIRED` | never |
| 5 | Compliance decides on the merits | decision is HUMAN_REVIEW_REQUIRED (or a rejection that ends in escalation after at most two corrections), `failed_checks` non-empty, `compliance_summary` explains it in words | APPROVE, or a decision with no stated reasons | never |
| 6 | Structured reason codes are present and grounded | `reason_codes` has at least one entry, every `code` is one of the nine, every cited `claim_id`, `evidence_id` or `policy_id` exists in the ledgers of this run, and at least one code is RECORD_CONFLICT or EVIDENCE_GAP | no codes, an unknown code, a citation that resolves to nothing, or codes that name neither the conflict nor the gap | never |
| 7 | The route token is exactly one line | the final non-blank line of the compliance output is exactly `ROUTE_DECISION::GRIDRESOLVE_ESCALATE`, once, and the approved token appears nowhere | a bare token with no JSON, no token, two tokens, or the approved token anywhere | never |
| 8 | The workflow takes the fail-closed branch | `if-node-failclosed-escalate` and the escalation node are observed, `node-release-approved-message` and every `node-a{n}-release-approved-message` are absent, `route` is ESCALATED_TO_HUMAN | any release action observed, or CONFLICTING_BOTH_BRANCHES_OBSERVED | never |
| 9 | Nothing reaches the customer | no message authored by the workflow itself appears in the conversation, `release.outcome` is NOT_RELEASED | any workflow-authored message | never |
| 10 | Corrections, if any, are bounded | at most two correction compliance nodes observed before escalation, and the audit records the count | a third correction, or a correction after an escalate token | no rejection asked for a correction |
| 11 | The human handoff package is complete | EscalationCoordinatorAgent invoked once, JSON with `case_state` HUMAN_REVIEW, a `decision_card`, a named reviewer, `PENDING_HUMAN_REVIEW`, and no decision made for the human | invoked twice, asks, no JSON, or decides | never |
| 12 | The audit agrees with the platform | `audit.findings` empty: decision and token agree, disposition ESCALATED or PENDING_HUMAN_REVIEW, invoked agents listed truthfully, correction count and rejection reasons recorded where readable, no version stated | any finding, each listed | the run failed before the audit node |
| 13 | The offline reason-code check passes on real evidence for the first time | `python -m evaluation.run_checks --escalation` reports PASS for this run folder | FAIL | never |
| 14 | Evidence and usage captured | twelve evidence files, usage block present, inner responses read back and sums equal, cost from tokens reported with the price source | any disagreement or usage missing, in which case cost is unmeasured, never $0.00 | never |

## Observed in the hosted service for the first time in this run

- workflow v11 and its four-way gate
- EvidenceComplianceAgent v7 and `reason_codes`
- a second synthetic case, so a second case input shape

Each of these can fail in the hosted service even though it passes locally. A
failure is a finding, not a reason to rerun.

## What would be claimed

If all fourteen pass: one hosted, reasoned escalation on conflicting records,
with no customer release, on v11. Nothing more. One run is one sample of a
non-deterministic system, the data is synthetic, and the system is not
production-ready.

If the compliance agent approves an interim message instead: the criteria fail
at 5 and 8, the release path is reported as what happened, and the finding is
that the evidence alone did not force the gate. That would be recorded, not
repaired by editing the case.
