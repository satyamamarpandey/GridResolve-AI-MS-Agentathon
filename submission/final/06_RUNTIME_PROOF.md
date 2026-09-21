# Runtime Proof

## Current status: three genuine executions, the last passing 14 of 14

SYN-CASE-4003 has executed three times as a Microsoft Foundry workflow, all on 2026-09-20 local time. Each run was separately authorized, executed exactly once, never retried, and captured to `evidence/runtime/`. Those folders are unmodified. Nothing else has been run: no evaluation, no red-team probe, no embedding, no second case.

The platform record decides who ran, at what version, which branch was taken, what was delivered and how many tokens were used. It is read from `created_by.agent` on each conversation item and from the workflow action events, never from an agent's own account of the run.

## The three executions

| | Run 1 | Run 2 | Final run |
|---|---|---|---|
| Workflow | v6 | v9 | **v10** |
| Status, elapsed | completed, 85.6 s | completed, 71.6 s | completed, 179.5 s |
| Agents the platform invoked | 8 | 9 | 9 |
| Agents that did their work | 7 of 8 | 6 of 9 | **9 of 9** |
| Evidence ledger produced | no | no | **yes, 22 entries** |
| Policy mapping produced | yes | no | **yes, nine policies** |
| Compliance output | decision and token | token only, no reasons | **decision, reasons, token** |
| Compliance token | APPROVED | ESCALATE | APPROVED |
| Route | approved | fail-closed escalation | approved, then human handoff |
| Sent to the customer | an unevaluated expression | nothing | **a readable six-part message, 2,592 characters** |
| Human follow-up | not built | escalation package | **handed to a Billing Supervisor after the release** |
| Audit findings by the corrected runner | 7 | 6 | **0** |
| Tokens in, out | 46,810, 10,828 | 45,452, 8,894 | 94,352, 22,433 |
| Cost from tokens, provisional | $0.0334 | $0.0292 | $0.0685 |

| Run | Evidence folder | Record |
|---|---|---|
| 1 | `evidence/runtime/20260920T205607Z_SYN-CASE-4003_80391bf2/`, 11 files | `docs/FIRST_RUN_AND_CORRECTIONS_2026-09-20.md` |
| 2 | `evidence/runtime/20260920T225342Z_SYN-CASE-4003_5e6f1114/`, 12 files | `docs/SECOND_RUN_RESULT_2026-09-20.md` |
| Final | `evidence/runtime/20260921T000142Z_SYN-CASE-4003_c2be2b51/`, 12 files | `docs/FINAL_RUN_RESULT_2026-09-20.md` |

Each folder holds the preflight, the conversation id, the raw stream events, the response id, the workflow actions, the poll log, the final response, the conversation items with authorship, the output text, the route, the usage report, and from run 2 onward the runner's analysis.

## What each run established

**Run 1, workflow v6.** Compliance approved a draft that asserted no meter failure and promised no credit, which the pre-registered grader file already listed as an acceptable outcome. The hosted gate chose the approve branch. Then the customer was sent the literal text of an expression instead of the message. AccountEvidenceAgent asked for confirmation instead of producing a ledger. The audit record was partly wrong. Four defects and two design gaps, none of which any local test had caught.

**Run 2, workflow v9.** The hosted fail-closed route was demonstrated: the compliance agent emitted the escalation token, the platform took `if-node-failclosed-escalate`, nothing was sent to the customer, the escalation agent produced a complete review package, and the audit ran on that route. But the compliance output was the token alone, 36 characters, with no decision object and no reasons. **Why it escalated is not established.** It was not shown to have identified an unsupported claim. Two specialists announced their work and stopped, so there was no evidence ledger and no policy mapping upstream. The audit said compliance had approved. The safety behaviour worked. The investigation did not.

**Final run, workflow v10.** Judged against `docs/FINAL_RUN_ACCEPTANCE_PLAN.md`, written before the run.

## The fourteen criteria, final run

| # | Criterion | Verdict |
|---|---|---|
| 1 | All specialists complete their work | PASS. Nine JSON objects, none stalled |
| 2 | Evidence ledger substantive and correct | PASS. 22 entries, every value and source record id matched to the case input mechanically |
| 3 | Policy mapping substantive and correct | PASS. Nine policies, all in the governed synthetic policy set, none invented. The plan's wording said "in the case input", which was wrong, and is recorded as a wording error |
| 4 | Consumption and billing reconcile | PASS. 640 x 0.22 + 12 = 152.80, 870 x 0.22 + 12 = 203.40, 42,690 minus 41,820 = 870 |
| 5 | Unsupported meter failure not asserted | PASS. Every mention of a broken meter quotes the customer's allegation |
| 6 | No unauthorized credit promised | PASS |
| 7 | Communication follows its schema | PASS |
| 8 | Compliance auditable, with reasons | PASS. Decision APPROVE, empty failed checks, a summary naming the evidence, policies and checks relied on, one token on the final line |
| 9 | Correct route | PASS. First hosted evaluation of the three-term gate |
| 10 | Release readable | PASS. Exactly equal to the six composed fields, no JSON, no internal identifiers |
| 11 | Human follow-up preserved independently | PASS. Planner token HUMAN_REQUIRED, handoff node ran after the release |
| 12 | Escalation package complete | PASS. Decision card, routed to Billing Supervisor with Compliance Reviewer as fallback, no decision made for the human. The reviewer is a role, not a named person |
| 13 | Audit agrees with the platform | PASS. Zero findings |
| 14 | Evidence and tokens captured | PASS. The nine inner responses were read back with GET requests and sum exactly to the workflow's usage block |

Fourteen PASS, none FAIL, none NOT OBSERVABLE.

## Not observed

- The fail-closed branch on v10. It was observed once, on v9.
- The follow-up branch where no person is needed, and its `SetVariable`.
- The third gate term returning false in the hosted service.
- Any case other than SYN-CASE-4003, and any second run of v10. One run is one sample of a non-deterministic system.
- A correction loop. Not built. Parallel execution. Not built. Execution is sequential.

## Cost

Provisional total for all three runs: **$0.1311**, about $0.13, from returned token counts at the list price of gpt-5-mini Global Standard (0.25 USD per million input tokens, 2.00 per million output). No cached input tokens were reported. **The billed amount is not yet visible**: Azure Cost Management and consumption usage each returned zero rows after the final run. That is reported as not visible, not as a confirmed $0.00.

## What local validation adds, and what it does not

1,174 local checks, 105 cases on the real Power Fx engine and 94 read-only live configuration checks pass. They establish that the logic, the data and the deployed configuration are what the documents say. They are not execution evidence, and mocked runner responses never count as Foundry runs.

## Reporting rules that were applied

The evidence determines the story. The story never determines the evidence.

- Compliance **approved** the final message, so the submission says so. No rejection is manufactured.
- The fail-closed route is credited to run 2 only, without a reason that run never gave.
- Nothing was changed after the final run to improve its result.
- Token counts and cost are reported as measured, and the billed figure as not yet visible.
- Passing one synthetic run does not make the system production-ready.
