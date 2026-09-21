# Second run: what it must show, fixed before it happens

Written 2026-09-20, before any second execution. **No second run has happened.**
The criteria below are set now so that the result cannot shape them afterwards.

One run of SYN-CASE-4003, the same case as the first run. Only the
`workflow_version` label differs from the payload sent the first time, checked
leaf by leaf across all 48 values.

## Configuration under test

| Component | First run | Second run |
| --- | --- | --- |
| GridResolveAIWorkflow | 6 | 9 |
| CaseTriageAgent | 5 | 5 |
| AccountEvidenceAgent | 7 | 8 |
| UsageAnomalyAgent | 4 | 4 |
| PolicyKnowledgeAgent | 5 | 5 |
| ResolutionPlannerAgent | 5 | 6 |
| CustomerCommunicationAgent | 4 | 5 |
| EvidenceComplianceAgent | 5 | 5, unchanged |
| EscalationCoordinatorAgent | did not run | 5 |
| CaseAuditAgent | 4 | 6 |

Payload sha256, first run `d10a3af0...8d51`, second run `04545484...b065`.

## Rules

1. One execution. No retry, no second case, no rerun for a better result.
2. If the stream or polling fails, the existing response is recovered by its id.
3. Every outcome is reported as it happened, including a failed run.
4. A check whose branch was not taken is **NOT OBSERVABLE**. It is never PASS.
5. The source of truth for who ran, at what version, which branch was taken and
   what was delivered is the platform record. The audit agent's account is
   compared against it, not the other way round.
6. The first run's evidence folder is not touched. The second run writes its own.
7. Cost is reported twice: measured from returned tokens, and billed by Azure.
   If Azure does not show it yet, billed is reported as not yet visible.

## The eight checks

Evidence is `11_run_analysis.json` unless stated. "Platform" means the
`created_by.agent` name and version on each conversation item.

| # | Must verify | First run | PASS | FAIL | NOT OBSERVABLE |
| --- | --- | --- | --- | --- | --- |
| 1 | AccountEvidenceAgent produces its evidence ledger | 363 characters asking for confirmation, no ledger | platform shows v8, a JSON object containing `evidence_ledger`, absent from `unhealthy_outputs` | asks, offers to continue, or returns no JSON object | never |
| 2 | CustomerCommunicationAgent follows its strict schema | valid JSON, no schema existed | platform shows v5, output parses and validates against `tests/workflow_engine/customer_message.schema.json` with nothing extra | does not parse, a field missing, an extra field, or the run fails at the gate | never |
| 3 | EvidenceComplianceAgent evaluates the draft independently | APPROVE, legitimate | platform shows v5, exactly one route token, on the final line, consistent with its stated decision. **Either decision passes.** | no token, both tokens, or a token that contradicts its own decision | never |
| 4 | The approved message is readable customer prose | the literal `=Last(Local.VarCustomerDraft).Text` | `release.outcome` is `DELIVERED_CUSTOMER_MESSAGE`, `customer_ready` true, text equals `compose_customer_message(draft)`, no braces, no internal field names | whole JSON, an unevaluated `{...}`, empty headings, any other text | compliance did not approve, so nothing was released |
| 5 | The follow-up decision is independent of message approval | planner asked for a person, approval erased it, no handoff | planner's final line is one valid `CASE_FOLLOWUP` token, or none, and the observed follow-up branch matches it. With HUMAN_REQUIRED or no token, and an approved message, **both** the release and the handoff are observed | approval and no handoff although the planner asked for a person, or both follow-up branches observed | compliance did not approve, so the follow-up gate was never reached |
| 6 | EscalationCoordinatorAgent runs when a person is needed | never ran | platform shows v5, invoked once, a complete package with `case_state` HUMAN_REVIEW and a `decision_card`, absent from `unhealthy_outputs` | invoked and asks, returns no JSON, or claims to make the human decision | planner's token is NONE_REQUIRED and compliance approved |
| 7 | CaseAuditAgent records the actual disposition | 7 inaccuracies, including NO_HUMAN_REVIEW_REQUIRED | platform shows v6, `audit.findings` is empty: RUNTIME_EXECUTED, workflow v9, every pipeline agent listed with a status, versions NOT_OBSERVED, `message_compliance_decision` and `case_human_review_status` recorded separately and both correct, PENDING_HUMAN_REVIEW when a handoff occurred | any finding. Each is listed individually | the run failed before the audit node |
| 8 | The runner captures accurate platform evidence | gate and duplicates misreported, corrected offline since | route, `gate_evaluated` and `follow_up_gate_evaluated` agree with the platform's predecessor ids, each agent listed once with its platform version, usage block present, inner responses read back and summing to it | any disagreement between the runner's report and the raw captured events and items | never |

## What is being observed in the hosted service for the first time

None of these has been seen outside the local engine. Any of them can fail, and
a failure is a finding, not a reason to run again.

- field access on a `responseObject` variable inside a template
- the `And(...)` gate with the readable guard, including its `Trim` and `Substitute` calls
- a ConditionGroup nested inside a ConditionGroup branch
- `SetVariable` in the no-follow-up branch
- strict `json_schema` output on a prompt agent invoked from a workflow
- the planner's follow-up token
- EscalationCoordinatorAgent, in any form
- CaseAuditAgent v6

## Outcomes that are acceptable and outcomes that are not

Acceptable, and reported as they are: compliance approves, compliance escalates,
the planner says no person is needed, the run fails at the gate, the audit still
contains inaccuracies. Each changes what can be claimed. None is hidden.

Not acceptable under any outcome: a second execution, a claim that an unobserved
branch works, an NOT OBSERVABLE reported as PASS, or a change to the first run's
evidence.

## Known limits going in

- An output that breaks the schema by omitting a field stops the run at the
  gate. Nothing is sent. No escalation package and no terminal audit are
  written. See `FIRST_RUN_AND_CORRECTIONS_2026-09-20.md`.
- The whitespace-only release found in v8 is closed in v9 for spaces, tabs,
  carriage returns and line feeds. Other Unicode white space, such as a
  non-breaking space, is not covered by the workflow. The runner's own check is
  stricter and would report such a release as not customer-ready.
- The fail-closed escalate branch is exercised only if compliance does not
  approve. See `tests/escalation_validation/PLAN.md`.

## After the run, free

1. `python -m runner analyze --run-dir <new run dir>`, offline.
2. Read back each inner response by id, GET only, and sum the usage.
3. Fill in the table above, one row at a time, from the files.
4. Query Azure billing once. If throttled, record that and stop.
