# Final GridResolve AI Status

Updated 2026-09-20, after the third and last real execution. Submission deadline
2026-09-24. The implementation is frozen. The reference for every figure here is
`docs/CURRENT_STATUS.md`. The version of this file dated 2026-09-19 said nothing
had been executed. That is no longer true and has been replaced.

## 1. Runtime-demonstrated

Three genuine Microsoft Foundry workflow executions of SYN-CASE-4003, all on
2026-09-20 local time. Evidence in `evidence/runtime/`, three folders, unmodified.

| | Run 1 | Run 2 | Final run |
|---|---|---|---|
| Workflow | v6 | v9 | **v10** |
| Agents that did their work | 7 of 8 | 6 of 9 | 9 of 9 |
| Evidence ledger | none | none | 22 entries |
| Compliance | approved | escalated, gave no reasons | approved, with reasons |
| Sent to the customer | an unevaluated expression | nothing | a readable message |
| Human follow-up | not built | escalation package | handoff after the release |
| Audit findings by the runner | 7 | 6 | 0 |
| Cost, provisional | $0.0334 | $0.0292 | $0.0685 |

The final run passed **14 of 14** acceptance criteria written before it ran
(`docs/FINAL_RUN_ACCEPTANCE_PLAN.md`, result in
`docs/FINAL_RUN_RESULT_2026-09-20.md`). Nine policies mapped, none invented. Audit
zero findings. Compliance **approved** the final message. It did not reject it, and
the final run did not take the fail-closed branch. Run 2 did take the hosted
fail-closed branch, but its compliance output was the token alone, so why it
escalated is not established.

This is one synthetic case, run once on v10. It is a runtime-demonstrated,
production-oriented prototype. It is not production-ready.

## 2. Live configuration, verified read-only

GridResolveAIWorkflow **v10**. Nine agents, all gpt-5-mini, reasoning low, no
tools: CaseTriage 5, AccountEvidence 9, UsageAnomaly 4, PolicyKnowledge 6,
ResolutionPlanner 6, CustomerCommunication 5, EvidenceCompliance 6,
EscalationCoordinator 5, CaseAudit 7. `tests/verify_live_config.py`: **94 of 94**,
read-only control plane GETs, no model call.

## 3. Verified locally, no model, no network

| Suite | Result |
|---|---|
| Routing and case data | 83 passed |
| Synthetic data | 151 passed |
| Control Center application | 156 passed, typecheck and build clean |
| Foundry runner, every response mocked | 357 passed |
| Workflow engine, Microsoft's open-source engine on the live v10 YAML | 91 passed |
| Evaluation package, deterministic checks and provenance | 198 passed |
| Integration contracts and synthetic adapters | 138 passed |
| **Total** | **1,174** |
| Power Fx gate, Microsoft's engine | 105 cases, 0 failures |
| Mutation testing of the runner | 80 of 80 deliberate faults caught |

None of these is Foundry execution evidence.

## 4. Prepared only, not executed

30-case evaluation suite, 15 evaluators, weighted rubric. 16 red-team scenarios.
Neither has been run. No evaluation score exists.

## 5. Not built, production targets

Parallel investigation fan-out. Automatic replan and rewrite loops. Application
Insights tracing. AI Gateway. Read-only adapters to billing, account, meter data
and customer relationship systems. Policy as a versioned store and not prompt
text. Microsoft Entra ID roles and managed identities. Real human notification and
supervisor authorization in a system of record. Migration to Microsoft Agent
Framework before Foundry Workflows Preview retires on 2026-12-01. None of these is
live. The plan is in `docs/CURRENT_STATUS.md` and
`submission/final/14_PRODUCTION_ROADMAP.md`.

## 6. Actual token usage

| | Tokens in | Tokens out |
|---|---|---|
| Run 1 | 46,810 | 10,828 |
| Run 2 | 45,452 | 8,894 |
| Final run | 94,352 | 22,433 |
| Total | 186,614 | 42,155 |

For each run every inner agent response was read back with a GET request, and
the sums equal the workflow usage block.

## 7. Cost

Provisional, from returned token counts at list price: **about $0.13** in total.
gpt-5-mini Global Standard, 0.25 USD per million input tokens, 2.00 output, 0.025
cached input, verified 2026-09-18 via the Azure Retail Prices API.

Confirmed billed amount: **not yet visible.** Azure Cost Management and
consumption usage each returned zero rows after the final run. That is not a
confirmed $0.00. Zero embeddings, zero evaluation runs, zero billable resources
created.

## 8. Not observed

The fail-closed branch on v10 (seen once, on v9). The follow-up branch where no
human is needed. The third gate term returning false in the hosted service. Any
other case. Any second run of v10.

## 9. Known limitations

Full list in `submission/final/13_LIMITATIONS.md`. The material ones: one sample
of a non-deterministic system; execution is sequential; the correction loop is
not built; policies live in prompt text; nobody is actually notified on a human
handoff, and the reviewer is a role and not a named person; no persisted traces;
no fairness assessment; a field missing from the communication JSON still stops
the run at the gate; the platform retires on 2026-12-01.

## 10. Remaining blockers for submission

1. Narration audio for the video. No recording exists in the repository.
2. Two authentic Foundry portal captures showing workflow v10, `F10-WORKFLOW.png`
   and `F10-COMPLIANCE.png`. The existing Foundry captures show v5, which was true
   when they were taken, and are unused. The Control Center captures are current.
3. Owner approval to commit, push and submit. Nothing has been committed.
