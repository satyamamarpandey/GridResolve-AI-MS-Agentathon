# Workflow v11: bounded correction routes

Status: LOCAL DESIGN, TESTED ON THE OPEN-SOURCE ENGINE. NOT PUBLISHED. NOT HOSTED.
Date: 2026-09-23.

v10 collapses every compliance decision other than APPROVE into one fail-closed
escalation. That is safe, and it is also why the correction loop the agents were
written for (REJECT_AND_REWRITE, REJECT_AND_REPLAN, correction_count) has never
run: the workflow had no path back to the planner or the communication agent.
v11 adds those two paths, with a hard bound, and keeps everything else of v10.

## The contract

EvidenceComplianceAgent ends its output with exactly one final line, one of:

| Token | Workflow action |
| --- | --- |
| `ROUTE_DECISION::GRIDRESOLVE_APPROVED` | Release the latest draft, then the follow-up gate, as in v10 |
| `ROUTE_DECISION::GRIDRESOLVE_REJECT_REWRITE` | CustomerCommunicationAgent again, then EvidenceComplianceAgent, then gate |
| `ROUTE_DECISION::GRIDRESOLVE_REJECT_REPLAN` | ResolutionPlannerAgent, then CustomerCommunicationAgent, then EvidenceComplianceAgent, then gate |
| anything else | Fail closed: EscalationCoordinatorAgent, then CaseAuditAgent. Nothing is sent |

The JSON object before the token keeps the v6 fields (decision, failed_checks,
correction_target, correction_instructions, correction_count,
compliance_summary, human_review_required) and adds `reason_codes[]` when the
decision is not APPROVE. Reason codes are for people and for the offline
checks. They do not route anything: routing is the token and the presence of a
decision object, and a test proves that adding or removing reason codes changes
no action.

Release conditions, at every gate: the APPROVED token is the last non-blank
line, it occurs exactly once, none of the substrings `GRIDRESOLVE_ESCALATE` or
`GRIDRESOLVE_REJECT` appear anywhere in the text, all six customer fields of the
draft under review are non-blank, and the evidence, usage, policy and
compliance outputs each start with `{` and hold their key field. That is the
v10 expression plus the REJECT exclusion, on the variables of the attempt.

Correction conditions: the REJECT token is the last non-blank line, occurs
exactly once, no other route token appears anywhere, and the compliance output
starts with `{` and holds `"decision"`. A bare token with no decision object is
not corrected, it is escalated, because a correction agent would have nothing
to act on and a correction attempt is a paid model call.

## The bound

At most two correction attempts per case, of either kind. The bound is the
shape of the definition, not a counter: the tree is unrolled to depth two, and
the gate after the second correction has only two outcomes, release or fail
closed. No agent-written correction_count can extend it. A third non-approval
escalates. A malformed or missing token at any gate escalates.

```
  triage > evidence > usage > policy > planner > comms > compliance
                                                            |
                             gate 0 (v10 ids) --------------+
                             |        |          |          |
                          approve  rewrite    replan     escalate
                             |     comms      planner       |
                          release  compliance comms         |
                          followup   |        compliance    |
                                     |          |           |
                                  gate a1-rw  gate a1-rp    |
                                  |  |  |  |  (same four)   |
                            approve rw rp esc               |
                                    |  |                    |
                              gate a2 (approve | escalate only)
                                                            |
                                                          audit (always last)
```

Seven gates, seven release points, seven escalation points, one audit. Every
release sends only the draft reviewed at that gate, from a fresh
`responseObject` variable per attempt (`Local.VarCustomerMessage`,
`...A1Rw`, `...A1Rp`, `...A1RwA2Rp`, and so on). The follow-up gate at a
release point reads the latest plan (`Local.VarPlan`, or `Local.VarPlanA1Rp`
after a replan), so a corrected plan that clears the case is honoured and a
corrected plan that does not is handed to a person.

## Action ids

Attempt 0 keeps every v10 id, so the runner's v10 map, the run-2 and run-3
evidence and the live-config checks still read. New ids follow one rule, from
`tests/workflow_engine/build_v11.py` and `runner/workflow_v11.py`, and a test
asserts the two agree.

| Point | Id pattern | Example |
| --- | --- | --- |
| Correction branch under a gate | `if-node-{path}-a{n}-reject-{kind}` | `if-node-a1-reject-rewrite`, `if-node-a1-rewrite-a2-reject-replan` |
| Replanned plan | `node-{path}-planner` | `node-a1-replan-planner` |
| Redrafted message | `node-{path}-comms` | `node-a1-rewrite-comms` |
| Re-review | `node-{path}-compliance` | `node-a1-rewrite-compliance` |
| Gate after a correction | `node-{path}-gate` | `node-a1-rewrite-gate` |
| Release after a correction | `node-{path}-release-approved-message` | `node-a1-replan-release-approved-message` |
| Follow-up gate and its branches | `node-{path}-case-followup-gate`, `if-node-{path}-no-human-followup`, `node-{path}-record-no-followup`, `if-node-{path}-human-followup`, `node-{path}-followup-handoff` | |
| Fail closed after a correction | `if-node-{path}-failclosed-escalate`, `node-{path}-escalate` | `node-a1-rewrite-a2-rewrite-escalate` |

`{path}` is `a1-rewrite`, `a1-replan`, `a1-rewrite-a2-rewrite`,
`a1-rewrite-a2-replan`, `a1-replan-a2-rewrite` or `a1-replan-a2-replan`.
The definition has 99 unique action and branch ids, 37 agent invocations and
689 lines. It is generated; `python tests/workflow_engine/build_v11.py --check`
fails if the committed file drifts from the generator.

Every agent node passes a plain literal invocation message, never an
expression. Correction messages name the step, say `CORRECTION ATTEMPT n of
2`, tell the agent to read the correction_instructions, failed_checks and
reason_codes in the most recent EvidenceComplianceAgent output, and to change
only what was identified (rewrite) or to re-plan from the evidence without
filling gaps (replan). The audit message asks for correction_count and every
earlier decision with its failed checks and reason codes. No message states a
case figure, a finding, a verdict or a route token.

## What the runner does with it

`runner/workflow_v11.py` maps every id and extends `describe_route` with
`correction_attempts` (how many re-reviews ran), `rejections_observed` (the
kinds, in order, for example `["REPLAN", "REWRITE"]`) and `correction_bound`.
The route names are unchanged (`APPROVED_AND_RELEASED`,
`ESCALATED_TO_HUMAN`), so the evaluation checks keep working.

The runner interprets v10 unless `GRIDRESOLVE_WORKFLOW_VERSION=11` is set
(`runner/workflow_versions.py`). With it set, the live-definition check refuses
to execute unless the published workflow is v11 and carries the v11 ids. An old
evidence folder is always read with the map of the version its own preflight
record names, so runs 1 to 3 are unaffected.

## What is proven locally

`python tests/test_workflow_engine_v11.py`, 76 checks on Microsoft's
open-source declarative engine (`Microsoft.Agents.AI.Workflows.Declarative`),
with every agent replaced by a scripted reply. The scripted replies are the
genuine outputs of the final hosted run (v10, 2026-09-20), read and never
written, plus hand-built compliance decisions and edited drafts labelled
OFFLINE_FIXTURE. The harness now accepts a list of replies per agent, consumed
one per invocation, which is how a rejected draft is followed by a corrected
one.

| Behaviour | Result |
| --- | --- |
| Attempt 0 on the final run's real outputs | Same actions, same order, same nine agents and the identical 2,592 character release as v10 |
| Rewrite, then approve | The corrected draft is released, the rejected one is not; comms and compliance ran twice, planner once; the follow-up handoff follows from the original plan |
| Replan, then approve | Planner, comms and compliance ran twice; the follow-up gate reads the new plan, both ways |
| Rewrite, rewrite, then reject; replan, rewrite, then reject; a third rewrite or replan request | Nothing sent, escalated once, audited last; the runner reads two corrections then escalation |
| Three scripted approvals | One release, compliance consulted once |
| Malformed token, both tokens, prose, or empty output at attempt 1 | Nothing sent, escalated, audited |
| Approved token plus a REJECT token in the same text | Not released, not corrected, escalated |
| A REJECT token with no decision object | Not corrected, escalated |
| Reason codes present or absent | Identical actions and identical release |
| A corrected draft with a blank field, or not JSON | Withheld and escalated, as in v10 |
| Every path | The audit runs last and exactly once; at most one message reaches the customer |
| The v10 file and the final run's evidence | Unmodified |

The v10 suite (91), the runner suite (357), the evaluation package (198) and
the Agent Framework parity check (11 of 11) still pass after these changes.

## NOT HOSTED, stated plainly

- v11 is not published to Foundry. The live workflow is v10.
- EvidenceComplianceAgent v6, the live version, emits only the APPROVED and
  ESCALATE tokens. The REJECT tokens and reason_codes need a republished agent.
  That instruction text is a separate change.
- No hosted run has exercised any v11 path. The local engine reproduced the
  hosted service's behaviour on v6 and v10 for the runs that exist, which is why
  it is used as a stand-in for routing, and it is not the hosted service.
- Two known limits carry over from v10: a draft missing one of the six fields
  is a binding error at the gate rather than a Power Fx false, and the strict
  JSON schema on four agents is enforced by the Foundry agent definition, not by
  the engine.
- The runner refuses to execute against v11 until it is published, and it
  refuses to execute against v10 with the v11 setting. Either way it makes no
  model request without the confirmation phrase and a spending cap.
