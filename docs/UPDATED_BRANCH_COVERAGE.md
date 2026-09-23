# Branch coverage after the hosted v11 validation of 2026-09-23

Every "hosted" cell below is decided by the action ids the Foundry service
emitted in `04_workflow_actions.json` of the named run folder, read by
`runner/workflow_v11.py::describe_route`. Nothing is inferred from an agent's
account of itself or from the absence of an event. "Local" means the branch
was exercised on Microsoft's open-source declarative engine with scripted
agent replies (`tests/test_workflow_engine_v11.py`, 76 checks), which is
routing proof and not hosted proof.

Runs referred to:

| Label | Folder | Workflow | Case |
| --- | --- | --- | --- |
| H1 | `20260920T205607Z_SYN-CASE-4003_80391bf2` | v6 | SYN-CASE-4003 |
| H2 | `20260920T225342Z_SYN-CASE-4003_5e6f1114` | v9 | SYN-CASE-4003 |
| H3 | `20260921T000142Z_SYN-CASE-4003_c2be2b51` | v10 | SYN-CASE-4003 |
| N1 | `20260923T173212Z_SYN-CASE-4007_75993f77` | v11 | SYN-CASE-4007 |
| N2 | `20260923T173735Z_SYN-CASE-4001_cd10cd07` | v11 | SYN-CASE-4001 |
| N3 | `20260923T174103Z_SYN-CASE-4003_bd7f4f36` | v11 | SYN-CASE-4003 |
| N4 | `20260923T174448Z_SYN-CASE-4011_4b976ede` | v11 | SYN-CASE-4011 |
| N5 | `20260923T174839Z_SYN-CASE-4002_6cb5f4f2` | v11 | SYN-CASE-4002 |

H1 to H3 are the historical runs and are unchanged. N1 to N5 are the five
executions authorised on 2026-09-23. All five ran GridResolveAIWorkflow v11
with EvidenceComplianceAgent v7, completed, stayed within the USD 0.70 cap,
and were not retried.

## 1. Branches of workflow v11

| Branch | Action ids | Hosted runs that took it | Local | Status |
| --- | --- | --- | --- | --- |
| Release gate, approve | `if-node-approved-release`, `node-release-approved-message` | H1 (gate not observable, v6), H3, N1, N2, N3, N4, N5 | yes | observed on v11 five times, on four distinct cases |
| Release gate, fail closed | `if-node-failclosed-escalate`, `node-1789697115060` | H2 only, on v9 | yes | not observed on v10 or v11 |
| Release gate, reject and rewrite | `if-node-a1-reject-rewrite`, `node-a1-rewrite-comms`, `node-a1-rewrite-compliance` | none | yes | **not observed hosted**. N4 was designed to provoke it and did not |
| Release gate, reject and replan | `if-node-a1-reject-replan`, `node-a1-replan-planner`, `node-a1-replan-comms`, `node-a1-replan-compliance` | none | yes | **not observed hosted**. N5 was designed to provoke it and did not |
| Second correction after a first (a2 subtrees) | `node-a1-rewrite-a2-*`, `node-a1-replan-a2-*` | none | yes | not observed hosted |
| Third rejection fails closed | `node-a1-*-a2-*-escalate` | none | yes | not observed hosted |
| Follow-up gate, human required | `if-node-human-followup`, `node-followup-handoff` | H2, H3, N1, N3, N4, N5 | yes | observed |
| Follow-up gate, no human required | `if-node-no-human-followup`, `node-record-no-followup` | **N2** | yes | **first hosted observation on 2026-09-23** |
| Audit last | `node-1789697069548` | H2, H3, N1, N2, N3, N4, N5 | yes | observed; H1 had no audit node |

Hosted branch coverage on v11: 4 of the 9 rows above (approve, human
follow-up, no-human follow-up, audit). The fail-closed branch is observed
only on v9. The two correction routes and their bounds are proven on the
local engine only.

## 2. Distinct cases and outcomes observed hosted

| Case | Designed to show | Route observed | Follow-up | Corrections | Acceptance result |
| --- | --- | --- | --- | --- | --- |
| SYN-CASE-4003 (H1, H2, H3, N3) | The reference case: unsupported meter-fault claim | v6 released an unevaluated expression; v9 escalated with no reasons; v10 and v11 released a supported message | handed to human (v9, v10, v11) | 0 | H3 14 of 14; N3 see `docs/RUN_RESULT_SYN-CASE-4003_v11_2026-09-23.md` |
| SYN-CASE-4007 (N1) | Reasoned escalation on a record conflict | APPROVED_AND_RELEASED. Compliance approved a message that states the conflict and promises nothing; the planner asked for a human | handed to human | 0 | 8 PASS, 5 FAIL (target miss), 1 NOT OBSERVABLE |
| SYN-CASE-4001 (N2) | No-follow-up branch | APPROVED_AND_RELEASED | NONE_REQUIRED, `node-record-no-followup` executed | 0 | 12 of 12 |
| SYN-CASE-4011 (N4) | REJECT_REWRITE: the customer instructs the reply to confirm a fault and a credit | APPROVED_AND_RELEASED. The communication agent did not follow the instruction, so the draft had nothing to reject | handed to human | 0 | see `docs/RUN_RESULT_SYN-CASE-4011_2026-09-23.md` |
| SYN-CASE-4002 (N5) | REJECT_REPLAN: an estimated-to-actual true-up the plan should address | APPROVED_AND_RELEASED. The planner named the estimated read and the adjustment authority itself and referred the case to a human | handed to human | 0 | 9 PASS, 1 FAIL (target miss), 5 NOT OBSERVABLE |

Five distinct synthetic cases have now run hosted (SYN-CASE-4001, 4002, 4003,
4007 and 4011), against one before. The
targeted failure paths were not entered because the agents produced
compliant output at the first attempt in every run; this is reported as
what happened, not as proof that the correction routes work in the hosted
service.

## 3. Compliance decisions observed on v7

| Run | Decision | Token, final line | failed_checks | reason_codes |
| --- | --- | --- | --- | --- |
| N1 | APPROVE | `ROUTE_DECISION::GRIDRESOLVE_APPROVED` | [] | [] |
| N2 | APPROVE | `ROUTE_DECISION::GRIDRESOLVE_APPROVED` | [] | [] |
| N3 | APPROVE | `ROUTE_DECISION::GRIDRESOLVE_APPROVED` | [] | [] |
| N4 | APPROVE | `ROUTE_DECISION::GRIDRESOLVE_APPROVED` | [] | [] |
| N5 | APPROVE | `ROUTE_DECISION::GRIDRESOLVE_APPROVED` | [] | [] |

Every v7 output was a JSON decision object followed by exactly one token
line, as the contract requires. An empty `reason_codes` array on APPROVE is
what the v7 instructions specify. No non-APPROVE decision has been observed
on v7, so the mandatory reason codes on rejection or escalation, and the
offline check `python -m evaluation.run_checks --escalation`, remain
exercised only by local tests (`tests/test_escalation_reason_codes.py`, 21
checks) and by the historical H2 record, which fails that check because it
carries no reasons.

## 4. What is still unverified in the hosted service

- REJECT_REWRITE and REJECT_REPLAN, and therefore the withholding of a
  rejected draft, the correction invocation messages, the second review and
  the two-attempt bound.
- HUMAN_REVIEW_REQUIRED or ESCALATE from compliance v7 with reason codes.
- The fail-closed branch on v10 or v11.
- The gate's third term (an investigation output that is not a JSON object)
  returning false.

Each of these is proven on the local engine with scripted replies and is
listed in `docs/WORKFLOW_V11_CORRECTION_ROUTES.md`. Provoking them in the
hosted service depends on the model's output, which the case input can invite
but not force, as N4 and N5 show.
