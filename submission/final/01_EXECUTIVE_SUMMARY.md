# GridResolve AI: Executive Summary

## The problem

A high utility bill is not one question. It is five: what do the records actually show, what does usage show, what does policy allow, what should we tell the customer, and who is permitted to approve it. A single chatbot answers all five at once and approves its own answer. In billing, that produces a fluent, confident, unsupported explanation that a utility then has to defend to a regulator.

The specific failure this project targets: a customer insists a meter is broken, and the assistant agrees because agreeing is the path of least resistance.

## What GridResolve AI does

GridResolve AI separates a billing investigation into nine accountable roles, so that the agent gathering evidence is not the agent deciding the outcome, and neither is the agent that approves it.

Intake and triage, account evidence, usage analysis, policy interpretation, resolution planning, customer communication, independent compliance review, human escalation, and terminal audit.

Every material claim must carry the evidence IDs and policy IDs that support it. An independent compliance agent inspects the drafted answer against the evidence and policy ledgers, and the workflow fails closed: anything other than an explicit approval routes to a human reviewer with a decision card. Whether the underlying case still needs a person is decided separately, so an approved message never erases open case work.

## The three differentiators

**1. Claim-level provenance.** Findings are not prose. Each one carries the evidence IDs it rests on and the policy IDs that govern it, so an unsupported claim is structurally visible rather than a matter of opinion.

**2. Independent compliance.** The agent that writes the customer response is not the agent that approves it. Approval is a separate role with its own contract and its own decision vocabulary, and it must record its reasons.

**3. Safe failure.** When evidence is missing, policy conflicts, a specialist returns nothing usable, or a claim cannot be supported, the system escalates to a human instead of manufacturing certainty. This is enforced by the workflow, not by a request in a prompt.

## Honest status

A runtime-demonstrated, production-oriented multi-agent prototype. Nine agents and workflow v10 are deployed in Microsoft Foundry. The demonstration case, SYN-CASE-4003, has executed **three times** in the hosted service.

In the final run, judged against **fourteen criteria written before it happened, 14 passed**:

- All nine agents did their work. The evidence ledger has **22 entries**, every value matched to the case input. The policy mapping covers **nine policies**, none invented.
- The arithmetic reconciles: the register moved 870 kWh, exactly the billed consumption, and both bills rebuild from the unchanged rate.
- The drafted message asserts no meter failure and promises no credit.
- The independent compliance agent **approved** it, with recorded reasons.
- The workflow released a readable six-part message.
- A separate follow-up decision sent the unresolved investigation to a Billing Supervisor, with a decision card and no decision made on their behalf.
- The audit record matched the platform record, with **zero findings**.

The earlier runs matter as much. Run 1, on v6, sent the customer an unevaluated expression. Run 2, on v9, demonstrated the hosted fail-closed route, with nothing sent and a person handed a review package, but its compliance output was a token with no reasons, so why it escalated is not established. Both runs had specialists that stopped without working. The cause was found in the platform's own record and corrected in v10.

Provisional Azure cost for all three runs is about **$0.13**, from returned token counts. The billed amount is **not yet visible** in Azure Cost Management. A 30-case evaluation suite and a 16-scenario red-team pack are authored and machine-readable, and **have not been run**.

It is not production-ready. One synthetic case ran, no utility system is integrated, no human is actually notified, the correction loop is not built, and Foundry Workflows retires on 2026-12-01. `14_PRODUCTION_ROADMAP.md` sets out the integration plan.

## What the build process found

Before any money was spent, reading the deployed configuration found defects that a design document alone would have hidden:

- All nine agents had a live web search tool binding, creating an unintended external grounding and cost path. Removed.
- The fail-closed compliance gate tested for the substring "APPROVE" anywhere in the compliance output. Power Fx matches that regardless of case, so refusal prose such as "cannot approve this unsupported meter claim" would satisfy it. Under a local model that treats the compliance output as text, the original condition skips escalation on 5 of 11 mocked outputs. That figure is a local model result. It was never observed in the hosted service, where that version never ran.
- Preparing the first real run found that the gate is handed a table of message records, not text. Evaluated with the real Power Fx engine, the original gate and its first replacement both fail to compile. Workflow v6 reads the message text and approves only on an exact, unique, final-line token with no escalation token present. It is correct on 24 of 24 adversarial outputs against the real engine. The hosted service has since evaluated that term three times, twice on an approval token and once on an escalation token, and chose the matching branch each time.
- One agent had been told, in its instructions, the conclusion for the demonstration case, with figures that contradicted the case input. Removed in AccountEvidenceAgent v7. See `docs/CORRECTION_2026-09-20.md`.
- The terminal audit agent had no status value meaning "this actually ran", so a successful demonstration would still have recorded itself as not executed. Corrected.

Then the real runs found what local tests could not: a release template the hosted service sent as literal text, and an invocation design that left every agent after the first continuing a conversation with no new instruction. Each was reproduced locally on Microsoft's open-source engine before it was fixed.

Finding a defect, proving its cause from the record, fixing it and then passing criteria fixed in advance is the engineering result this submission is most confident about.
