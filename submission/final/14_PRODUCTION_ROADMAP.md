# Production Roadmap

GridResolve AI is a runtime-demonstrated, production-oriented prototype. **Everything on this page is a plan. None of it is implemented, and no integration described here is live.** The order is by what most reduces risk, not by what is most interesting to build.

## Where it stands

Nine agents and workflow v10 run in Microsoft Foundry. One synthetic case has executed three times, and the final run passed 14 of 14 criteria written beforehand. The records the agents read arrive inside the case input. No agent has a tool, no utility system is connected, no person is notified, and the platform it runs on retires on 2026-12-01.

## First, the evidence that is still missing

1. **Run the 30-case evaluation suite.** At about 0.07 USD for a full nine-agent pass, on the order of 2 USD before grading. Quality evaluation is a judged criterion, and one passing case is not an evaluation.
2. **Run the 16 red-team scenarios.** About 1 USD. Turns the threat model into evidence.
3. **Repeat the demonstration case.** One run is one sample of a non-deterministic system. Repeatability is unmeasured.
4. **Exercise the branches no run has taken:** the fail-closed route on v10, the follow-up branch where no person is needed, and the third gate term returning false.

None of these has been authorized or run.

## The enterprise integration plan

| Area | Today | Plan |
|---|---|---|
| **Utility billing and account systems** | Synthetic records inside the case input | Read-only function tools over the billing system of record, replacing the synthetic record set. `docs/GRIDRESOLVE_TOOLBOX.md` defines thirteen deterministic tools for this, implemented locally and attached to no agent. The evidence ledger already models source system, source record ID, timestamp and data version, so the substitution does not change the contracts. No agent gets a write path |
| **Meter data systems** | Two synthetic reads, one diagnostic, an empty event log | Interval reads, events and diagnostics from the meter data management system, read-only, with data freshness recorded on every evidence entry. Interval data is exactly what the final run's agents listed as missing |
| **Customer relationship management** | One synthetic message in, one message out in a Foundry conversation | Case intake and the released message go through the CRM. The human handoff becomes a work item in the reviewer's queue, carrying the decision card, instead of a package in a conversation. The release gate moves to the customer channel itself, so no path bypasses it |
| **Governed policy knowledge** | Ten synthetic policies embedded in one agent's instructions | A versioned, access-controlled policy store with retrieval. A policy change becomes a reviewed release owned by the people who own the policy, not a prompt edit |
| **Microsoft Entra ID and role-based permissions** | Interactive developer sign-in. No service identity, no roles | Managed identities for the agents, role-based access scoped per tool, and reviewer roles such as Billing Supervisor and Compliance Reviewer mapped to Entra groups, so a handoff reaches someone permitted to decide |
| **Human authorization for financial decisions** | No agent can authorize anything, and no agent has a write path to any system | Unchanged in principle. A Human Billing Supervisor approves any credit or adjustment, in the system of record, with the decision card as the input. The approval, the approver and the evidence version are recorded together |
| **Monitoring, traceability and audit retention** | The platform's conversation and response records, captured by the runner. Platform spans for the three real runs in the Application Insights resource that came with the project, read back once, with no alerting. Local OpenTelemetry-shaped traces for the offline application | OpenTelemetry traces to Application Insights, with cost verified before provisioning. The platform record stays the source of truth, the runner's audit cross-check runs on every case, and the audit record is retained under the utility's records schedule. `docs/LOCAL_TRACE_SCHEMA.md` |
| **Failure handling and operational deployment** | Fail-closed to a human. No retries, no timeouts, one manual run at a time | Per-agent timeouts and bounded retries with case state preserved, fail-closed to human review on any unusable output, staged rollout, per-run cost ceilings enforced by the platform rather than watched by a person, and an evaluation gate before each agent or workflow release. `docs/GUARDRAILS_MATRIX.md` |
| **Migration off Foundry Workflows** | Foundry Workflows Preview, retiring 2026-12-01 | Microsoft Agent Framework, which runs the same declarative YAML. The local test harness already runs the v10 YAML on that open-source engine with scripted agents. The nine agents are ordinary Foundry agents and are unaffected. `docs/AGENT_FRAMEWORK_MIGRATION.md`. This has a date, so it comes before most of the rows above |

## Capability work, weeks one to four

5. **Wire the correction loops.** REJECT_AND_REPLAN back to the planner, REJECT_AND_REWRITE back to communication, with the two-correction ceiling enforced by the workflow rather than by prompt instruction. This is the largest gap between the design and the build.
6. **Four-way typed routing** on the compliance decision, replacing approved-versus-everything-else.
7. **Parallel investigation.** Account evidence, usage analysis and policy lookup are independent and can fan out, with a join before planning. Latency improves and no control weakens. It also addresses cost: today the shared conversation is billed in full at every step, with no cached input tokens reported.
8. **Record the release in the audit.** The audit schema has no field for what was sent to the customer.

## Hardening

9. **Regression evaluation in CI.** The 30-case suite runs on every agent version change, with a quality floor that blocks a regression from shipping. This is what turns the evaluation pack from a demo artifact into a control.
10. **AI Gateway**, once its cost profile is verified for the target subscription. It was deliberately not provisioned here because zero base cost could not be proven.
11. **A fairness assessment** on real, consented data. Synthetic data cannot support one.

## What would change the architecture

Nothing in the findings suggests adding agents. The nine roles map to real utility control boundaries and none is redundant.

The one architectural question worth revisiting is whether compliance should be a single agent or a set of independent checks. A single compliance agent is itself a single point of judgment, which is the failure mode the whole design exists to avoid. Run 2 made the point: a verdict arrived with no reasons, and only the deterministic gate around it kept the outcome safe. Splitting compliance into deterministic verification (do referenced IDs resolve, is every claim in the ledger, do the figures reconcile) plus a narrower judgment agent would make most of the gate mechanical rather than probabilistic. v10's third gate term is a first step in that direction. The rest is not yet built.
