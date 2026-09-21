# GridResolve AI

Evidence-first multi-agent utility billing resolution, built on Microsoft Foundry.
Submitted to the Microsoft Agent-a-thon, Level 3 Architect.

## Submission summary

| Item | Where |
|---|---|
| **Read this first** | [`submission/final/JUDGE_NARRATIVE.md`](submission/final/JUDGE_NARRATIVE.md), plain language, no prior knowledge assumed |
| Submission deck, eight slides | [`submission/final/GridResolve_AI_Submission_Deck.pptx`](submission/final/GridResolve_AI_Submission_Deck.pptx) |
| Demo video | [`submission/video/GridResolve_Final_Video.mp4`](submission/video/GridResolve_Final_Video.mp4) is the final narrated video: 172.1 seconds, 1920x1080, about 8 MB, my own recorded narration at its own speed, authentic Foundry captures with the project name covered, the Control Center, and slides built from the final run's evidence. `python submission/video/build_video.py --final` builds an earlier scripted cut of the same narration and is kept for reference. Transcript: [`submission/video/FINAL_VIDEO_SCRIPT.md`](submission/video/FINAL_VIDEO_SCRIPT.md) |
| Case walkthrough | [`docs/JUDGE_WALKTHROUGH_SYN-CASE-4003.md`](docs/JUDGE_WALKTHROUGH_SYN-CASE-4003.md), seven stages end to end |
| Runtime evidence | [`evidence/runtime/`](evidence/runtime/), three unmodified run folders. Result: [`docs/FINAL_RUN_RESULT_2026-09-20.md`](docs/FINAL_RUN_RESULT_2026-09-20.md) |
| Screenshots | [`submission/final/18_SCREENSHOT_MANIFEST.md`](submission/final/18_SCREENSHOT_MANIFEST.md) |
| Validation report | [`docs/FINAL_VALIDATION_REPORT.md`](docs/FINAL_VALIDATION_REPORT.md) |

**In one paragraph.** A customer's bill rose from $152.80 to $203.40 and they are
certain the meter is broken. Nine specialist agents investigate as one governed
Foundry workflow. The register moved 870 kWh, matching billed consumption
exactly, both reads are actual, no meter events exist and the diagnostic passed,
so the increase is explained by measured consumption at an unchanged rate. The
evidence does not establish a meter failure, and no agent says it does. An
independent compliance agent approves the supported explanation, with recorded
reasons, and a readable message is released. A separate follow-up decision sends
the still-open investigation to a human reviewer, and a terminal audit records
what happened. The agent that writes the answer is never the agent that clears it
for release, and no agent can authorize money.

> **Status, 2026-09-20.** A runtime-demonstrated, production-oriented prototype.
> Three genuine executions on Microsoft Foundry, all of one synthetic case. The
> final run, on workflow **v10**, passed **14 of 14** acceptance criteria that
> were written down before it ran: nine of nine agents did their work, a 22-entry
> evidence ledger, nine policies mapped, compliance approved with reasons, a
> readable message released, the open case handed to a human, and an audit with
> zero findings. It is not production-ready, no utility system is integrated, and
> all data is synthetic. One page with every current fact:
> [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).

**What makes it credible.** The failures are in the repository too. Reading the
deployed configuration found two defects before any money was spent: a release
gate that Microsoft's real Power Fx engine refuses to compile, and an agent that
had been told the answer. The first real run then sent the customer a line of
unevaluated workflow code. The second failed safe, withholding the message and
handing the case to a person, but two specialists had stopped without doing their
work and the compliance agent gave no reasons, so **why it escalated is not
established**. The cause of the stalls was found in the platform's own record of
what each agent received, corrected in workflow v10, validated at no cost on
Microsoft's open-source workflow engine, and then tested once against criteria
fixed beforehand. Records:
[`docs/CORRECTION_2026-09-20.md`](docs/CORRECTION_2026-09-20.md),
[`docs/FIRST_RUN_AND_CORRECTIONS_2026-09-20.md`](docs/FIRST_RUN_AND_CORRECTIONS_2026-09-20.md),
[`docs/SECOND_RUN_RESULT_2026-09-20.md`](docs/SECOND_RUN_RESULT_2026-09-20.md),
[`docs/V10_CORRECTIONS_2026-09-20.md`](docs/V10_CORRECTIONS_2026-09-20.md),
[`docs/FINAL_RUN_ACCEPTANCE_PLAN.md`](docs/FINAL_RUN_ACCEPTANCE_PLAN.md),
[`docs/FINAL_RUN_RESULT_2026-09-20.md`](docs/FINAL_RUN_RESULT_2026-09-20.md).

## What this is

A nine-agent system that investigates a high utility bill, and refuses to tell the
customer anything the evidence does not support.

The customer in the synthetic demonstration case is certain their meter is broken.
The records do not support that. The interesting engineering problem is not
producing a fluent explanation, it is making sure the system cannot produce a
confident one that nobody can defend.

## Honest status

This matters more than the feature list, so it is stated first.

| Label | What it covers |
|---|---|
| CONFIGURED | Nine agents and workflow v10, deployed to Foundry and readable |
| STATICALLY_VALIDATED | Routing semantics, arithmetic, provenance, data isolation |
| OFFLINE_DEMONSTRATION | The Control Center application and its customer conversation |
| PREPARED_ONLY | 30 evaluation cases, 16 adversarial probes, disabled live adapter |
| PRODUCTION_TARGET | Parallel investigation, correction loops, tracing pipeline |
| **RUNTIME_OBSERVED, THREE RUNS** | Three executions of SYN-CASE-4003. **v6:** eight agents, compliance approved, the customer was sent an unevaluated expression. **v9:** nine agents, compliance escalated without giving a reason, nothing was sent, a complete review package was produced. Across those two runs 3 of 17 agent invocations stopped without doing their work. **v10, final:** nine of nine agents did their work, compliance approved with reasons, a readable message was released, the open case was handed to a human, the audit had zero findings. 14 of 14 pre-registered criteria passed |
| **NOT YET OBSERVED** | The fail-closed route on v10 (seen once, on v9). The follow-up branch where no human is needed. Any second run of v10. Any case other than SYN-CASE-4003. The 30 evaluation cases and 16 adversarial probes |

**Azure spend on this build: three workflow executions, about $0.13.** That is
186,614 input and 42,155 output tokens at list price ($0.0334, $0.0292 and
$0.0685), a provisional figure. The billed amount is **not yet visible** in Azure
Cost Management, which is not the same as a confirmed $0.00. Zero embeddings,
zero evaluation runs, zero billable resources created.

Every number in the documents and the application was produced by deterministic
code or read from deployed configuration. Model output exists in one place only,
`evidence/runtime/`, and is labelled as such.

## The defects this found

The compliance gate was originally written as:

```
Not("APPROVE" in Local.Var1497)
```

Power Fx `in` is case-insensitive substring matching, so refusal prose containing
"approve" would satisfy it. Under a local model that treats the compliance output
as text, that expression skips escalation on 5 of 11 mocked outputs.

**That figure is the output of a local text-only model. It was never observed in
the hosted service, where neither v4 nor v5 ever ran.** And the model was
too generous: `Local.Var1497` is filled by `output.messages`, which is a table of
message records. Evaluated with the real Power Fx engine against that table, the
v4 gate and its v5 replacement both fail to compile.

```bash
dotnet run --project tests/powerfx_gate    # v5: 0 of 24. v6: 24 of 24.
```

Workflow v6 reads `Last(Local.Var1497).Text` and approves only on an exact,
unique, final-line token with no escalation token present. The hosted service has
now evaluated that term three times: twice on an approval token, where it chose
the approve branch, and once on an escalation token, where it chose the escalate
branch. How it handles the other 22 local cases is **not yet established**. In
v10 the gate has two further terms, a readable-message guard and an
investigation-complete guard. The hosted service has evaluated the full
three-term gate once, in the final run, with every term true.

A second defect: AccountEvidenceAgent had been told, in its instructions, the
conclusion for the demonstration case, alongside figures that contradicted the
case input. v7 removes both.

All of it was found by reading the deployed configuration, before any money was
spent. Full record: [`docs/CORRECTION_2026-09-20.md`](docs/CORRECTION_2026-09-20.md).

## Verification

```bash
# routing semantics and case data, no network
python tests/test_routing_and_data.py            # 83 passed, 0 failed

# the compliance gate on the real Power Fx engine, no network, needs the .NET SDK
dotnet run --project tests/powerfx_gate          # 24 gate, 6 release, 7 harness, 15 follow-up, 36 guard, 17 investigation cases

# the real workflow YAML on Microsoft's open-source engine, agents scripted from
# the two captured runs, no network, needs the .NET SDK
python tests/test_workflow_engine.py             # 91 passed, 0 failed

# the Foundry runner, every API response mocked, no network
python tests/test_foundry_runner.py              # 357 passed, 0 failed

# every synthetic dataset, schema conformance and honesty labelling, no network
python tests/validate_synthetic_data.py          # 151 passed, 0 failed

# live Foundry configuration, read-only control plane calls, no cost
# requires az login and your own Foundry resource
set GRIDRESOLVE_FOUNDRY_RESOURCE=<your-resource>
set GRIDRESOLVE_FOUNDRY_PROJECT=<your-project>
python tests/verify_live_config.py               # 94 passed, 0 failed

# Control Center application
cd control-center
npm install
npx tsc -b && npx vitest run                     # 156 passed
npm run build
```

**1,174 local checks pass** (83 routing, 151 synthetic data, 156 application, 357
runner, 91 workflow engine, two of which pin a known limit, 198 evaluation package, 138 integration contracts), plus 105 real-engine Power Fx cases. None of them calls a model. The
runner suite replays the captured events and items of the first two real runs to
check evidence extraction. That is a replay of stored files, not a new execution.

The three local suites run with no network at all. `verify_live_config.py` is the
only script that contacts Azure, it performs read-only control plane GETs, and it
is excluded from that total because it needs your own credentials.

## Control Center

A local React and TypeScript application with eleven views, themed on the Industry
design system in `control-center/_ds/`. It makes no network call at runtime,
holds no credential, and is labelled `DETERMINISTIC OFFLINE DEMONSTRATION` on
screen so it cannot be mistaken for Foundry execution. The offline guarantee is
enforced by test: the stylesheet may not reference an external font or host.

```bash
cd control-center && npm install && npm run build
cd .. && python -m http.server 5180 --directory "control-center/dist"
```

Then open http://localhost:5180

Views: Overview, Runtime Evidence, Customer Assistant, Billing Investigation, Evidence Explorer,
Agent Workflow, Supervisor Review, Governance, Evaluations, System Status, and
UI Test Fixture.

### UI test fixtures

`data/` holds three display-only snapshots of SYN-CASE-4003 supplied for local
frontend testing. They declare `workflow_version: GridResolveAIWorkflow-v4` and
use `SYN-` prefixed identifiers, which do not match the canonical v10 engine.

That mismatch is **reported, not resolved**. The fixtures load through a separate
mapper into the UI Test Fixture view, keep their own version label, and never
merge into the canonical ledgers. Every fixture pane carries
`Synthetic - UI Simulation - Not Executed`. 24 tests assert the nine supplied UI
expectations, including that the meter-failure claim `SYN-CL-4003-02` is visibly
UNSUPPORTED with no linked evidence, and that the simulated compliance rejection
surfaces `POL-MTR-003`.

## Layout

```
control-center/        React application, 13 deterministic tools, 156 tests
  _ds/                 Industry design system, source of the theme tokens
  src/tools/           pure functions, errors as values, never thrown
  src/engine/          investigation engine, case memory, OTel-shaped traces
  src/fixtures/        UI test fixture loader and mapper, v4 shape preserved
  src/live/            Foundry adapter, disabled, refuses before the network
  src/views/           the eleven views, including Runtime Evidence for the three real runs
data/                  supplied UI test snapshots, display only
docs/                  run records, corrections, research and design documents
runner/                the guarded Foundry runner: preflight, one execution, offline analysis
evaluation/            deterministic checks, provenance trace, policy catalog, Foundry shaped datasets. Local, not model based
integration/           typed contracts and synthetic adapters for billing, meter, CRM, review, adjustment and audit
migration/             Microsoft Agent Framework parity proof, local, scripted agents
evidence/runtime/          the three genuine Foundry runs, unmodified
evidence/platform_telemetry/  redacted read-only summary of what Azure Monitor and Application Insights recorded
evidence/reanalysis/       offline re-reads of those runs, labelled as derived
evidence/screenshots/      authentic Foundry captures
evidence/app-screenshots/  Control Center captures, kept separate on purpose
submission/final/      the submission package, 22 documents
submission/video/      video builder, narration script, subtitles
tests/                 routing, data, runner, Power Fx gate, workflow engine, live configuration
```

## Documents

| Document | Covers |
|---|---|
| `docs/CURRENT_STATUS.md` | The canonical facts page. Every other document defers to it |
| `docs/FOUNDRY_CAPABILITY_INVENTORY.md` | Every Foundry capability, whether I use it, what it costs by Microsoft's documentation, and why the rest is off |
| `docs/SECURITY_AND_GOVERNANCE_EVIDENCE.md` | The guardrail and security settings as actually configured, and a control matrix with enforcement status |
| `docs/OPERATIONS_MONITORING_AND_COST.md` | Three cost figures kept apart, platform telemetry read back, and why HTTP success is not correctness |
| `docs/ROUTINES_SKILLS_TOOLS_MEMORY_DESIGN.md` | Designs only. Nothing enabled |
| `migration/agent_framework/README.md` | Local parity proof on Microsoft Agent Framework, 11 of 11, and what a real migration still needs |
| `evaluation/README.md` | Deterministic checks over the three real runs. Not model based |
| `integration/README.md` | Typed contracts for the systems a utility would connect, with synthetic adapters |
| `docs/AGENT_FRAMEWORK_MIGRATION.md` | Parallel fan-out, typed routing, bounded correction loops |
| `docs/GRIDRESOLVE_TOOLBOX.md` | Thirteen deterministic tools as Foundry function tools |
| `docs/GUARDRAILS_MATRIX.md` | 15 failure modes, five defense layers, and what is not guarded |
| `docs/AZURE_SPEECH_FREE_TIER.md` | F0 allowances and limits, verified against Microsoft docs |
| `docs/LOCAL_TRACE_SCHEMA.md` | OpenTelemetry-compatible spans for the offline application. The platform's own spans are covered in the operations page |
| `docs/FOUNDRY_LOCAL_FEASIBILITY.md` | Hardware measured, local inference declined with reasons |
| `docs/MICROSOFT_FREE_FEATURE_MATRIX.md` | What was used, what was avoided, and why |

## Data

**Synthetic only.** No real customer, account, meter, name, address or contact
detail appears anywhere. Case identifiers follow the `SYN-CASE-NNNN` pattern, and
the memory layer refuses to store anything that does not match it. That is a
guard enforced by test, not a convention.

No credential, key, token or connection string is committed. The Foundry resource
name is supplied through environment variables rather than hardcoded, because
this repository is public.

## License

MIT
