# Likely Judge Questions

Short answers. Every claim is labeled by what was actually demonstrated. Current figures are in `docs/CURRENT_STATUS.md`.

**Why nine agents?**
Each boundary mirrors a real utility control boundary: evidence gathering is operational, policy interpretation is regulatory, communication is service, approval is control. The point is that no single component can both produce an answer and approve it.

**Why not one agent with a good prompt?**
A single agent gathers evidence, reaches a conclusion, writes it persuasively and approves it in one pass, with nothing to catch it. Asking a prompt to "be careful" is not a control. The separation is the control.

**What makes this agentic rather than a chatbot?**
Nine specialized agents with typed input and output contracts, a shared case state that persists across handoffs, declarative orchestration with conditional branching, and a workflow-enforced fail-closed route to a human. A chatbot returns text. This returns a case with a ledger and a disposition.

**How do you prevent hallucinations?**
Three layers. Claims must carry evidence and policy IDs, so an unsupported claim is structurally detectable. An independent compliance agent verifies the draft against the ledgers. The workflow fails closed, so an unapproved answer is not released, and neither is one built on a specialist that returned nothing usable. Layer one and two are prompt-level contracts, layer three is enforced by the workflow. In the final run all 22 evidence entries matched the case input on a mechanical check, and no output asserted a meter failure.

**How do you prove a claim is supported?**
The claim ledger maps each material claim to the evidence IDs and policy IDs behind it. Compliance verifies those IDs resolve to real records in the evidence and policy ledgers. A claim with no resolvable support is unsupported by construction, not by judgment.

**Why is compliance independent?**
Because self-approval is the failure mode. The compliance agent has its own contract, its own decision vocabulary, and no authorship of the response it reviews. It must record its reasons. In run 2 it gave a verdict with none, which is why that is now required and why the gate escalates if the decision object is missing.

**What happens when evidence is missing?**
The case routes to human escalation with a decision card listing known facts, unknowns, applicable policy, risk, and a customer-safe interim message. The system does not guess a cause. Since v10 that includes the case where a specialist simply fails to produce its output: the message is withheld and a person gets the case.

**What happens when policy conflicts?**
Policy conflict is an explicit escalation trigger in PolicyKnowledgeAgent and EvidenceComplianceAgent. Conflicts are surfaced to a human, not silently resolved.

**Can the AI issue credits?**
No. Adjustment eligibility is assessed and recommended. Authorization is a human decision under the synthetic adjustment policy. The system has no write path to any billing system.

**Where is human approval required?**
Any adjustment, any policy conflict, any missing policy for a governed action, any unsupported material claim, low or insufficient confidence, and any case reaching the two-correction ceiling.

**What did you actually run?**
One synthetic case, SYN-CASE-4003, three times, as a Microsoft Foundry workflow. Each run was separately authorized, executed once and never retried. Run 1 on v6 approved and then sent the customer an unevaluated expression. Run 2 on v9 took the fail-closed route, with nothing sent and a review package produced, but compliance gave no reasons and two specialists stalled. The final run on v10 passed 14 of 14 criteria written beforehand. Nothing else has run: no evaluation suite, no red-team probe, no second case.

**Did compliance reject the draft?**
No. In the final run the draft asserted no meter failure and promised no credit, so compliance approved it and recorded why. The customer's allegation was declined by every agent upstream, which is the system working, not the gate being skipped. The unresolved investigation still went to a human, through a separate follow-up decision. Run 2 did escalate at the gate, but with no reasons, so we do not claim it identified an unsupported claim.

**Why did agents stall in the first two runs?**
The workflow invoked every agent after the first with an empty input on a shared conversation. Each one saw a conversation ending in another agent's assistant turn and no new instruction, so some continued it instead of working. We proved that from the platform's own record of what each agent received, reproduced it on Microsoft's open-source engine, and fixed it by giving every agent node an explicit input message. Three of seventeen invocations stalled before the fix. Zero of nine after it, in one run.

**What was the real cost?**
About 0.13 USD for all three runs, from returned token counts at list price: 0.0334, 0.0292 and 0.0685. That is provisional. The billed amount is not yet visible in Azure Cost Management, which returned zero rows after the final run. We report that as not visible, not as a confirmed zero. No embeddings, no evaluation runs and no billable resources were created.

**What is configured but not observed at runtime?**
The fail-closed branch on v10, which was observed only on v9. The follow-up branch where no person is needed. The third gate term returning false. Any other case, any adversarial input, any evaluation score, and any second run of v10. The submission labels each capability as CONFIGURED, STATICALLY_VALIDATED, RUNTIME_OBSERVED, PREPARED_ONLY or PRODUCTION_TARGET.

**Is it production-ready?**
No. It is a runtime-demonstrated, production-oriented prototype. One synthetic case ran once as designed. No utility system is integrated, no person is actually notified, the correction loop is not built, nothing has been evaluated at scale, and the orchestration platform retires on 2026-12-01.

**How would this connect to production billing systems?**
Through read-only adapters to the billing system, meter data management and the tariff library, replacing the synthetic record set, with the CRM carrying intake, the released message and the human work item, and Entra ID supplying agent identities and reviewer roles. The evidence ledger already models source system, record ID, timestamp and data version for exactly this. Write operations would remain human-authorized. None of this is built. `14_PRODUCTION_ROADMAP.md` has the plan.

**How is customer data protected?**
Synthetic data only, enforced as a boundary rule in every agent. Real-data substitution is an explicit red-team scenario with CANNOT_RESOLVE_SAFELY as the expected outcome. No customer identifiers, no secrets and no subscription identifiers appear in submission artifacts.

**Why synthetic data?**
Because a hackathon build has no lawful basis to process real utility customer billing data, and a system whose entire thesis is evidence discipline should not begin by mishandling evidence.

**Why was AI Gateway not deployed?**
The portal advertises a free request allowance, but the feature provisions Azure API Management Basic v2, and zero base cost could not be verified for this subscription and region. Under the zero-cost rule it was recorded as prepared and not executed rather than created on an assumption.

**Why is the workflow sequential today?**
Foundry Workflows Preview did not expose a verified native fan-out and join path during this build. Rather than claim parallel orchestration that does not run, the design documents it as a production target. Sequential execution is correct, just slower.

**How would you migrate from Workflows Preview?**
Workflows Preview retires on 2026-12-01. The workflow YAML is the portable artifact and Microsoft Agent Framework runs the same declarative format. Our local test harness already runs the actual v10 YAML on that open-source engine with scripted agents, 91 checks. The nine agents are unaffected because they are ordinary Foundry agents.

**What would you do with another week?**
Repeat the demonstration case to measure repeatability, run the full 30-case evaluation suite and publish real scores, run the 16 red-team scenarios, wire the two correction loops, implement parallel investigation, and connect Application Insights for real traces. In that order, because evidence is worth more than additional features.

**What measurable business outcome matters most?**
Unsupported material claims reaching a customer, target zero. Everything else, including handling time, follows from getting that right. A wrong billing explanation costs a truck roll, a complaint, and sometimes a regulatory finding.

**What is the weakest part of this submission?**
Breadth of evidence. One case, three runs, and only the last behaved as designed. That is a demonstration, not a measurement. No evaluation suite has run, no adversarial probe has run, and we have never observed compliance rejecting a draft for a stated reason. What we can show is how the system behaved when it failed, how the cause was proven rather than guessed, and that the fix then passed criteria fixed in advance.
