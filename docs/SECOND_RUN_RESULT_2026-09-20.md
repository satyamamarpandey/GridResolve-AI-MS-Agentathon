# Second real run, judged against criteria fixed beforehand

One execution of SYN-CASE-4003 on GridResolveAIWorkflow v9, 2026-09-20. It was
judged against `docs/SECOND_RUN_COMPARISON_PLAN.md`, written before the run. It
was not repeated. Nothing was changed afterwards to improve the result.

## The run

| Field | First run | Second run |
| --- | --- | --- |
| Workflow | v6 | **v9** |
| Response id | `wfresp_0e74...PdhBc` | `wfresp_049a4b2251233a8300PK4o7lIPmt8U8jvE3dwoDHX9mVtPADV4` |
| Status | completed, 85.6 s | completed, 71.6 s |
| Stream events, items | 1303, 22 | 1182, 22 |
| Agents the platform invoked | 8 | **9** |
| Compliance token | APPROVED | **ESCALATE** |
| Route | approved and released | **fail-closed escalation**, nothing sent |
| Sent to the customer | a literal expression | nothing |
| Tokens in, out | 46,810, 10,828 | 45,452, 8,894 |
| Cost from tokens, provisional | $0.0334 | **$0.0292** |
| Payload sha256 | `d10a3af0...8d51` | `04545484...b065` |
| Evidence | `evidence/runtime/20260920T205607Z_...80391bf2/` | `evidence/runtime/20260920T225342Z_SYN-CASE-4003_5e6f1114/` |

The nine inner responses were read back individually with GET requests. Their
usage sums exactly to the workflow's usage block, so the token count is complete.
Neither run is visible in Azure billing yet. Cost Management returned HTTP 429.

Platform-observed versions: CaseTriage 5, AccountEvidence 8, UsageAnomaly 4,
PolicyKnowledge 5, ResolutionPlanner 6, CustomerCommunication 5,
EvidenceCompliance 5, EscalationCoordinator 5, CaseAudit 6. All as configured.

## The eight checks

| # | Check | Verdict | What the evidence shows |
| --- | --- | --- | --- |
| 1 | AccountEvidenceAgent produces its evidence ledger | **FAIL** | 312 characters, 64 output tokens, no JSON. It wrote "I'll now produce the full mandated JSON output" and stopped. Status completed, not truncated. It did not ask for confirmation this time, but there is still no ledger. Second failure in two runs |
| 2 | CustomerCommunicationAgent follows its strict schema | **PASS** | v5, valid against the shipped schema, nothing missing, nothing extra. Billing figures correct: 870 kWh, $0.22, $12 |
| 3 | EvidenceComplianceAgent evaluates independently | **PASS as written, with a defect** | Exactly one route token on the final line, which is the criterion. But the token is the entire output: 36 characters, 16 tokens, no decision object and no reasons. That it evaluated anything is not evidenced |
| 4 | The approved message is readable customer prose | **NOT OBSERVABLE** | Compliance did not approve, so nothing was released. The six-field template has still never been seen in the hosted service |
| 5 | Follow-up is independent of message approval | **NOT OBSERVABLE** | The planner did emit `CASE_FOLLOWUP::HUMAN_REQUIRED` on its final line, which is new and correct. The follow-up gate sits inside the approve branch, which was not taken |
| 6 | EscalationCoordinatorAgent runs when a person is needed | **PASS** | v5, invoked once, first time ever. 8,091 characters, a complete package: `case_state` HUMAN_REVIEW, a six-part `decision_card`, a named reviewer, PENDING_HUMAN_REVIEW, workflow v9. No asking. It makes no decision on the human's behalf |
| 7 | CaseAuditAgent records the actual disposition | **FAIL** | Better than run one, still wrong where it matters. Details below |
| 8 | The runner captures accurate platform evidence | **PASS, with two gaps found** | Route, gate, nine agents each once, versions and usage all agree with the raw events. Its audit cross-check missed two of the audit's errors. Details below |

## Defects this run exposed

**R2-1. Two agents announce their work and stop.** AccountEvidenceAgent (v8, 64
output tokens) and PolicyKnowledgeAgent (v5, 49 output tokens) each wrote one
sentence promising the JSON and ended the turn. Zero reasoning tokens in both.
PolicyKnowledgeAgent produced full output in the first run, so this is not
confined to one agent. The unattended-invocation paragraph changed
AccountEvidenceAgent's wording, from asking to announcing, and did not fix it.
Across both runs, 3 of 17 agent invocations stalled. The common factor is the
workflow's design: every agent after the first is invoked with an empty input on
a shared conversation that ends in another agent's assistant turn.
AccountEvidenceAgent again described the previous message as its own. This points
at the invocation shape, not at instruction wording. Not yet fixed.

**R2-2. The compliance agent gave a verdict with no reasons.** Its instructions
require a decision object before the token. It returned the token alone. The
route was fail-closed and safe. But an escalation nobody can explain is not an
auditable decision, and with no evidence ledger and no policy mapping upstream it
is likely that compliance escalated because its inputs were missing, not because
the draft was unsafe. The draft itself was schema-valid and asserted no meter
failure. That reading is an inference. The record does not say.

**R2-3. The audit record contradicts the run.**

- It records `message_compliance_decision: APPROVE` and states that compliance
  approved the message. Compliance escalated.
- It records EscalationCoordinatorAgent as NOT_INVOKED. The platform ran it, and
  the audit itself summarises an escalation package.
- It records AccountEvidenceAgent and PolicyKnowledgeAgent as RECEIVED. Neither
  produced its output.
- It gives its own version as `GRIDRESOLVE-AGENTS-3.0`. The platform ran v6.
- It declares itself COMPLETE with nothing missing.

What it got right, and got wrong in the first run: RUNTIME_EXECUTED, workflow v9,
all nine agents listed, other versions NOT_OBSERVED and not invented, human
review required, PENDING_HUMAN_REVIEW, and the model-produced label. The design
decision that the audit is not the source of truth held up. The platform record
is what caught it.

**R2-4. The runner's audit cross-check is incomplete.** It reported the audit as
inaccurate, which is correct, but listed two findings of the five above. It does
not compare `message_compliance_decision` with the platform-observed token, and
it does not compare each `output_status` with its own output-health finding. Both
were found by reading the evidence. Not yet fixed.

## What this run established for the first time

- The hosted gate selects the fail-closed escalate branch. The action path shows
  `if-node-failclosed-escalateActions`, and no SendActivity fired.
- The terminal audit runs on the escalate route.
- Strict `json_schema` output works on a prompt agent invoked from a workflow.
- `responseObject` on the communication node did not break the run.
- The planner emits its follow-up token.
- Agent names resolve to the latest versions, again.
- Nothing was sent to the customer when compliance did not approve.

## What is still not established

- The six-field release, the readable guard, the nested follow-up gate and
  `SetVariable`, in the hosted service. All sit on the approve branch.
- Why compliance escalated.
- That the pipeline produces an evidence ledger at all. It has not, in two runs.
- The billed amount of either run.

## Honest summary

The safety behaviour worked: an unexplained or under-evidenced case was withheld
from the customer and handed to a person with a usable package. The investigation
quality did not: two of the four evidence-gathering agents produced nothing, the
compliance decision carries no reasons, and the audit misreports the decision it
exists to record. This is a system that fails safe, not yet one that works as
designed.

## Afterwards

This document is left as written on the day of the run. R2-1 to R2-4 were then
traced and corrected in workflow v10, with no model call. The cause of R2-1 was
confirmed from the platform's record of what each agent received. See
`docs/V10_CORRECTIONS_2026-09-20.md`. None of those corrections has run in the
hosted service.
