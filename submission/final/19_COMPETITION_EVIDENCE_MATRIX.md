# Competition Evidence Matrix

Judging is 30 points each for Innovation, Usability and Impact, with Level 3 adding agent design, observability, quality evaluations and multi-agent orchestration. Verify the current criteria on the submission page.

Status vocabulary: **CONFIGURED** (deployed), **STATICALLY_VALIDATED** (verified without execution), **RUNTIME_OBSERVED** (seen in a genuine Foundry run of one synthetic case), **PREPARED_ONLY** (authored, not wired or run), **PRODUCTION_TARGET** (designed, not built).

RUNTIME_OBSERVED means observed, on SYN-CASE-4003, a small number of times. It does not mean validated, and it does not mean production-ready.

| Criterion | What we can show | Evidence | Status | Gap |
|---|---|---|---|---|
| Innovation | Claim-level provenance, independent compliance with recorded reasons, a three-term workflow-enforced fail-closed gate, and message approval kept separate from case follow-up | 03_ARCHITECTURE, workflow v10 YAML, final run evidence | RUNTIME_OBSERVED | One case |
| Usability | A readable six-part customer message actually released by the hosted workflow, and a decision card for the reviewer | Final run, `evidence/runtime/20260921T000142Z_SYN-CASE-4003_c2be2b51/` | RUNTIME_OBSERVED | No real customer or reviewer has used it. No channel or queue is integrated |
| Impact | Unsupported claims to customers, target zero; utility handling cost framing | 12_BUSINESS_IMPACT | PREPARED_ONLY | All business figures are targets, none measured |
| Agent design | Nine agents, typed IO contracts, strict output schemas on four, explicit prohibitions, explicit invocation messages | Agent definitions, 04_AGENT_TEAM | RUNTIME_OBSERVED | Nine of nine did their work in one run. Three of seventeen invocations stalled before the v10 fix |
| Multi-agent orchestration | Declarative YAML workflow, conditional fail-closed branch, release control, nested follow-up gate | Workflow v10, all three runs | RUNTIME_OBSERVED | Sequential only; no parallel, no loops. Fail-closed branch seen on v9, not v10 |
| Governance | 12 gates, human authority, audit record cross-checked against the platform record | 07_GOVERNANCE, final run analysis | RUNTIME_OBSERVED | Correction ceiling never reached, loop not wired |
| Evaluation | 14 acceptance criteria written before the final run, 14 passed. Separately: 30 cases, 15 evaluators, weighted rubric, 16 red-team scenarios | `docs/FINAL_RUN_ACCEPTANCE_PLAN.md`, `docs/FINAL_RUN_RESULT_2026-09-20.md`, both JSONL packs | One case pre-registered and judged. The suite is PREPARED_ONLY | **No evaluation scores exist. Directly judged criterion** |
| Observability | Platform conversation and response records captured per run: authorship, versions, branch, delivery, tokens, with every inner response read back and reconciled | `evidence/runtime/`, three folders, `runner/` | RUNTIME_OBSERVED for capture. Platform spans read back on 2026-09-21, summary in `evidence/platform_telemetry/` | **No alerting, no dashboard, content recording left on. Directly judged criterion** |
| Technical architecture | Versioned agents, versioned workflow, reversible changes, no external tools, a runner that refuses to execute against an unreviewed configuration | Foundry version history, `tests/verify_live_config.py`, 94 checks | CONFIGURED + STATICALLY_VALIDATED | |
| Demonstration | Video, deck, this package | `submission/video`, `20_FINAL_SUBMISSION_CHECKLIST.md` | See the checklist for current status | Narration and final build status are tracked there |
| Documentation | Judge narrative, current status page, run records, limitations, judge Q&A | submission/final, docs | COMPLETE | |
| Engineering rigor | Defects found by reading the configuration before spending, by two real runs, and by the platform's own records. Each reproduced locally before it was fixed. 1,174 local checks, 105 Power Fx cases, 80 of 80 runner mutants killed | `docs/V10_CORRECTIONS_2026-09-20.md`, test suites | STATICALLY_VALIDATED, then confirmed by the final run | Strongest hard evidence we hold |

## The gaps that cost the most points

1. **No evaluation results.** Quality evaluations are an explicitly named Level 3 criterion, and 30 authored cases with no scores read as unfinished. One pre-registered case is a good method and a small sample.
2. **No tracing.** Observability rests on captured platform records, not on an instrumented pipeline.
3. **One case, one good run.** Repeatability is unmeasured, and the rejection path has never been observed with a stated reason.
4. **No integration and no real users.** Usability is demonstrated as an output, not as an experience.

## What is genuinely strong

Most entries will present an architecture diagram and a happy-path demo. This one can show three genuine executions with the first two failing in instructive ways, the cause of the failure read from the platform's own record rather than guessed, the fix reproduced on Microsoft's open-source engine before it was deployed, and a final run judged against fourteen criteria that were written down first.

It can also show what it does not know, item by item, in `13_LIMITATIONS.md`.

That is an engineering story, and it is true.
