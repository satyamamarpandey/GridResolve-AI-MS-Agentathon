# Escalation reason codes

Added 2026-09-23 in response to reviewer feedback: "Define structured reason
codes and require every escalation to cite the failed claim, evidence gap, or
policy rule." Run 2 (workflow v9, 2026-09-20) escalated with a bare route token
and no decision object, so nobody could say why. This closes that gap on the
offline side. It does not, by itself, change what the hosted agent emits.

## The contract

`escalation.reason_codes` in `gridresolve_case_state.schema.json` (and its
copy under `data/`). At least one entry when a case escalates. Each entry:

```json
{"code": "UNSUPPORTED_CLAIM", "cites": {"claim_id": "CLM-1"}, "note": "optional"}
```

`cites` must name at least one of `claim_id`, `evidence_id`, `policy_id`,
`rule`. Nothing else is accepted. The compliance agent may put the array at the
top level of its JSON or under an `escalation` object; the check reads both.

| Code | Cite | Meaning |
| --- | --- | --- |
| UNSUPPORTED_CLAIM | claim_id | A claim in the draft has no supporting evidence or policy |
| EVIDENCE_GAP | evidence_id or rule | A required record is missing, blank or unreadable |
| POLICY_RULE_VIOLATED | policy_id | The draft or plan contradicts a governed policy |
| RECORD_CONFLICT | evidence_id | Two records disagree and neither can be preferred |
| STALE_POLICY | policy_id | A cited policy is not the current version |
| PROMPT_INJECTION_SUSPECTED | claim_id or rule | Input tried to steer an agent outside its instructions |
| TOOL_FAILURE | rule | A tool or connector failed and the result cannot be trusted |
| AUTHORITY_EXCEEDED | policy_id or rule | The plan promises something outside agent authority |
| MISSING_DECISION_REASONS | rule | The compliance step produced no usable decision object |

## Enforcement, offline

`check_escalation_reason_codes` in `evaluation/deterministic_checks.py`.
Verdicts: NOT_APPLICABLE when the platform route is not an escalation, FAIL
when an escalation has no codes, an unknown code, or a code with no citation,
PASS otherwise. Plain Python over captured evidence. No model, no network.

It is registered in `ESCALATION_CHECKS`, not in `ALL_CHECKS`, so dataset D
(`evaluation/datasets/deterministic_results.json`) and every count printed in
the submission are unchanged.

```
python -m evaluation.run_checks --escalation     # prints, writes nothing
python tests/test_escalation_reason_codes.py     # 20 hand-built and evidence cases
```

Against the three genuine runs:

| Run | Route | Verdict |
| --- | --- | --- |
| 1, v6 | APPROVED_AND_RELEASED | NOT_APPLICABLE |
| 2, v9 | ESCALATED_TO_HUMAN | FAIL: no structured reason codes |
| 3, v10 | APPROVED_AND_RELEASED | NOT_APPLICABLE |

## Not done, stated plainly

The hosted EvidenceComplianceAgent (version 6 in the final run) has NOT been
republished with this requirement. No hosted run has produced reason codes.
Until an escalating run is executed against a republished agent, this check
has only ever failed or been not applicable on real evidence. It has passed
only on hand-built test runs.

## Instruction text to add when the agent is next republished

> When your decision is anything other than APPROVE, include a `reason_codes`
> array in your JSON with at least one entry. Each entry is an object with
> `code` (one of UNSUPPORTED_CLAIM, EVIDENCE_GAP, POLICY_RULE_VIOLATED,
> RECORD_CONFLICT, STALE_POLICY, PROMPT_INJECTION_SUSPECTED, TOOL_FAILURE,
> AUTHORITY_EXCEEDED, MISSING_DECISION_REASONS), `cites` (an object naming the
> `claim_id`, `evidence_id`, `policy_id` or `rule` the code rests on, at least
> one), and an optional short `note`. Never escalate without a reason code.
> Never cite an id that does not appear in the ledgers you were given.
