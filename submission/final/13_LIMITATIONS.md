# Known Limitations

Stated plainly. Nothing here is hidden from judges, because a reviewer who finds an undisclosed limitation discounts everything else.

## Demonstrated once, not validated

GridResolve AI is a runtime-demonstrated prototype. It is **not production-ready**, and passing one synthetic run does not make it so.

One synthetic case, SYN-CASE-4003, has run three times in Microsoft Foundry. Only the final run, on workflow v10, behaved as designed, passing 14 of 14 criteria written beforehand. That is one sample of a non-deterministic system. A second run of the same configuration could differ, and no second run of v10 exists. The first two runs each failed in ways no local test had predicted, which is the best available estimate of how much remains unknown.

## Not observed in the hosted service

- **The fail-closed branch on v10.** It was taken once, in run 2, on v9. In that run the compliance output was a token with no reasons, so why it escalated is not established. The project has never observed compliance rejecting a draft for a stated reason.
- **The follow-up branch where no person is needed**, and its `SetVariable`.
- **The third gate term returning false.** It evaluated true in the final run. Its false case is verified only on Microsoft's open-source engines.
- **Any case other than SYN-CASE-4003**, including the contrast case where a meter concern is genuinely supported.
- **Any adversarial input.** The 16 red-team scenarios have not been executed.

## Known defects and limits carried forward

- A field missing from the communication agent's JSON stops the run at the gate with nothing sent and **no terminal audit**. The strict output schema makes that unlikely. It does not rule it out.
- The white-space guard covers space, tab, carriage return and line feed. It does not cover other Unicode white space such as a non-breaking space.
- The gate can tell that a field is not empty. It cannot tell that the text is meaningful. That judgement is the compliance agent's, and it is probabilistic.
- The audit record has no field for what was released to the customer. The platform record holds that fact.
- The escalation package routes to a role, Billing Supervisor, not to a named person.
- CaseTriageAgent and UsageAnomalyAgent carry a stale descriptive header naming workflow v5. It is inert text.
- No cached input tokens were reported, so the shared conversation is billed in full at every step and input grows with each agent.

## Architectural limits of the current build

**Investigation is sequential, not parallel.** Account evidence, usage analysis and policy lookup could run concurrently and the design allows for it, but the deployed workflow runs them in order. No parallel fan-out or join is claimed.

**Correction loops are not wired.** The compliance agent can emit REJECT_AND_REPLAN and REJECT_AND_REWRITE, and the two-correction ceiling is defined in its contract, but the workflow does not implement an automatic loop back to the planner or the communication agent. Today those decisions route to human escalation. This is safe but less capable than the design describes.

**Typed routing is partial.** The workflow distinguishes approved from everything else. It does not route the four compliance decisions to four different destinations.

**Compliance is a review, not a network-level release gate.** Release control is implemented by withholding the draft and emitting it only on the approved branch. Within one Foundry conversation this is a workflow-level control, not an enforced channel boundary. A production deployment would place the gate at the customer channel itself.

**Compliance is a single model judgement.** The three gate terms around it are deterministic. The decision inside it is not.

## Data, integration and people

**Synthetic data only.** All accounts, meters, reads, bills and policies are fictional. The system has never touched a real billing system, meter data system, CRM or identity provider. **No such integration exists or is claimed.** `14_PRODUCTION_ROADMAP.md` describes the plan.

**The records arrive inside the case input.** No agent has a tool. Nothing is retrieved.

**Policies live in agent instructions.** The ten synthetic policies are embedded in the PolicyKnowledgeAgent prompt rather than a governed store. This is adequate for ten policies and would not scale to a real tariff library.

**No human is actually notified.** The handoff is a structured package in a conversation. No queue, no work item, no reviewer.

**Traces exist, operations do not.** I wrote earlier that no Application Insights resource existed. That was wrong. One was created with the Foundry project, and on 2026-09-21 I found 61 platform spans in it covering all three real runs. Their token totals match my runner exactly. Nothing alerts on them, no dashboard exists, and message content recording is on, which is acceptable only because the data is synthetic. The primary evidence is still the platform's conversation and response records, captured by the runner. See `docs/OPERATIONS_MONITORING_AND_COST.md`. The OpenTelemetry-shaped traces in the repository belong to the local application only.

**Screenshots.** Several captures predate the current configuration. `18_SCREENSHOT_MANIFEST.md` states which still reflect it.

## Evaluation

The 30-case evaluation suite and 16-scenario red-team pack are authored, machine-readable and validated for structure and referential integrity. **No evaluation has been run and no score exists.** Every target in the rubric is a target, not a result. The fourteen acceptance criteria of the final run are a different thing: a pre-registered check of one case.

## Platform

Foundry Workflows Preview retires on 2026-12-01. Production orchestration must migrate to Microsoft Agent Framework, which runs the same declarative YAML. The local test harness already runs the v10 YAML on that open-source engine. The hosted service is closed source, so agreement between the two is observed case by case, not guaranteed. This is a known, dated constraint rather than a surprise.

## Cost

About **$0.13** across three runs, from returned token counts at list price. That figure is provisional. **The billed amount is not yet visible** in Azure Cost Management, which returned zero rows after the final run. Billing lags, so this is not a confirmed figure of any kind, and not a confirmed zero. The runner's spending cap is a local safeguard, not a platform-enforced billing limit.
