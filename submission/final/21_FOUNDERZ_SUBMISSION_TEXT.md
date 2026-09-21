# Paste-ready text for the Founderz submission form

The rules ask for "a brief written description of the issue the AI agent
addresses, the impact of the AI agent, and how the agent was built using ...
Microsoft Foundry", and for the agent's purpose and audience, how it was built
and refined, example interactions and key lessons learned. The text below is
split the same way. If the form has one field, paste the sections in order. If
it has a tight limit, use `02_SUBMISSION_100_WORDS.md`.

Every statement here is taken from `docs/CURRENT_STATUS.md`.

## Title

GridResolve AI: evidence-first multi-agent utility billing resolution

## The issue it addresses

A customer's bill jumps and they are certain the meter is broken. Answering that
well is five questions with different owners: what the records show, what
consumption shows, what policy allows, what to tell the customer, and who may
approve any of it. A single assistant answers all five at once and then approves
its own answer, and under pressure from a confident customer the easiest output
is agreement. In utility billing that is a claim about a physical asset and
somebody's money.

## Purpose and audience

For utility billing operations: the staff who answer high-bill disputes, and the
supervisors who must approve any credit or adjustment. It investigates a dispute
from the records, explains only what the evidence supports, and hands open
questions to a person with a decision card. It will not confirm a meter fault
without evidence, promise a credit, or let the agent that wrote an answer approve
it.

## Impact

An explanation that cannot be defended does not reach a customer. Wrong
adjustments and needless technician visits are avoided, every released statement
traces to evidence and policy identifiers, every case ends in an audit record,
and cases that need a person arrive triaged with the missing evidence named. The
pattern transfers to any regulated workflow where an AI-drafted statement has
financial or legal consequence.

## How it was built with Microsoft Foundry

Nine Foundry agents run as one Foundry workflow, version 10, in sequence on a
shared conversation: triage, account evidence, usage analysis, policy knowledge,
resolution planning, customer communication, independent compliance, human
escalation and audit. All use gpt-5-mini with no external tools. The workflow is
declarative YAML with Power Fx conditions. Four agents return strict JSON schema
output. A message is released only when three things hold: compliance approved
with one exact token, all six customer-facing parts are readable, and the
investigation outputs are complete. Anything else withholds the message and goes
to a human. Whether the case still needs a person is a separate gate.

I also used the platform to check my own numbers. Azure Monitor metrics and the
spans Foundry wrote to Application Insights report the same token counts as my
runner, to the token, and 26 model requests in total. The default Foundry
guardrail, Microsoft.DefaultV2, evaluated every one of those calls and blocked
none. I read all of this back without calling a model.

## How it was refined

It ran for real three times, on one synthetic case. Reading the deployed
configuration first found two defects at no cost. Run 1 sent the customer a line
of unevaluated workflow code. Run 2 failed safe, withholding the message and
handing the case to a person, but two specialists stalled and compliance gave no
reasons, so why it escalated is not established. The platform's own record of
what each agent received showed the cause: agents were handed a conversation with
no new request. Version 10 gives each agent an explicit task, and was validated
at no cost on Microsoft's open-source workflow engine and its real Power Fx
engine before it ran.

## Example interaction, from the final real run

The customer wrote that the bill jumped and the meter must be broken. Nine of
nine agents did their work. The evidence agent built a 22-entry ledger: the
register moved 870 kWh, exactly what was billed, both reads were actual and the
diagnostic passed. Nine policies were mapped. Compliance approved the message
with recorded reasons. The released message explained the bill, said no evidence
of over-recording was found, said remote diagnostics do not rule out every fault,
offered a human-reviewed inspection, and promised no credit. Separately, the open
investigation went to a Billing Supervisor with a decision card. The audit
matched the platform record with zero findings. The run passed 14 of 14
acceptance criteria that were written down before it ran.

## Key lessons learned

1. Local tests did not catch what one real run caught. Run the real thing early,
   once, with evidence capture.
2. When a fix changes the wording of a failure but not the failure, the cause is
   elsewhere. Read what the platform recorded, not what the agent said.
3. Fix acceptance criteria before the run, and report a branch not taken as not
   observable, never as a pass.
4. A model's own audit of a run is a claim, not a record. Check it against the
   platform.
5. HTTP success is not correctness. Foundry marked every span in all three runs
   as successful, including the two runs where agents stalled. The stalls show
   only as spans lasting about a second. Alert on what the agent returned, not on
   the status code.

## What it is not

A runtime-demonstrated, production-oriented prototype, not a production system.
All data is synthetic. No utility billing, meter, customer or identity system is
connected. One case ran, and workflow v10 ran once. The 30 prepared evaluation
cases and 16 adversarial probes have not been executed. Three runs cost about
$0.13 by returned token counts, and the billed amount is not yet visible in Azure
Cost Management. Foundry Workflows is a preview that retires on 2026-12-01, and
I replayed the final run's nine real agent outputs through Agent Framework's
open-source engine on the same YAML, locally. It took the same path and released
the same 2,592 characters. That is a local proof, not a deployment. The
integration contracts, the evaluation package and its 13 deterministic checks are
also local. The final run passes 12 of those 13. The one it fails is a root cause
label that differs from the one I prepared in advance, and I have left it as a
failure.
