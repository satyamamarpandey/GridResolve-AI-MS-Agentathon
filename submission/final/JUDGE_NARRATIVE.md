# GridResolve AI, the whole story in plain language

Written for a judge who has never worked on a utility billing system and does not
want to read a technical dossier first. No jargon that is not explained where it
appears. Every local number can be reproduced by running one command, and every
runtime number comes from an evidence file in `evidence/runtime/`.

**In four lines.** GridResolve AI is a runtime-demonstrated, production-oriented
multi-agent prototype. It ran three times on Microsoft Foundry, on one synthetic
case. The first two runs exposed real defects. The third passed all 14 acceptance
criteria that were written down before it ran.

---

## 1. The problem

A customer opens their electricity bill and it has jumped. They call the utility
and say the same thing customers almost always say: the meter must be broken,
please fix the charge.

Answering that well is not one question. It is five, and they have different
owners:

1. What do the billing records actually show?
2. What does consumption show, independent of price?
3. What does policy allow the utility to say and do?
4. What do we tell the customer?
5. Who is actually permitted to approve any of it?

Get this wrong in either direction and it costs real money. Wrongly agree that
the meter failed, and the utility issues an adjustment it cannot justify, opens a
regulatory problem, and may dispatch a technician for nothing. Wrongly dismiss
the customer, and a genuine fault keeps billing them.

## 2. Why a single chatbot is not enough

Put one assistant on this and it answers all five questions at once, then
approves its own answer.

That is the whole failure. There is no separation between producing an
explanation and deciding the explanation is safe to send.

It matters most under pressure. The customer is certain, insistent and
sympathetic. The most fluent, most agreeable output is "yes, your meter is
faulty, we will correct it." A single model optimising for a satisfying reply
will drift toward exactly that, and it will sound confident while doing it.

In utility billing that is not a bad chat reply. It is a claim about a physical
asset and about somebody's money.

## 3. The nine-agent architecture

GridResolve AI splits the work so that no agent can both write an answer and
clear it for release. Nine agents run as one governed workflow on Microsoft
Foundry.

**Four investigate.** `CaseTriageAgent` classifies the complaint and records what
the customer actually asked for. `AccountEvidenceAgent` gathers the records.
`UsageAnomalyAgent` analyses consumption. `PolicyKnowledgeAgent` supplies the
rules that constrain what may be concluded.

**Two produce.** `ResolutionPlannerAgent` proposes a resolution against a claim
ledger. `CustomerCommunicationAgent` writes the plain-language draft.

**Three control.** `EvidenceComplianceAgent` independently reviews the draft
against the evidence and the policies. `EscalationCoordinatorAgent` prepares the
review package for a named human role whenever a person is needed.
`CaseAuditAgent` writes a terminal record on every path.

The investigating and drafting agents run with output withheld, so nothing they
produce can reach the customer directly. Only the control path can release
anything.

## 4. How evidence supports an explanation

The core idea is a **claim ledger**. Every material statement the system wants to
make is written down as a claim, and every claim must name the evidence records
and policy rules that support it. A claim with no evidence behind it is marked
unsupported automatically, not as a judgment call.

In the demonstration case, the evidence is:

| Record | What it shows |
| --- | --- |
| Previous bill | $152.80 for 640 kWh over 30 days |
| Current bill | $203.40 for 870 kWh over 31 days |
| Meter reading, 30 June | 41,820 kWh, an **actual** read, not an estimate |
| Meter reading, 31 July | 42,690 kWh, an **actual** read |
| Meter event log | **Empty.** No events recorded |
| Remote diagnostic | **Passed**, no tamper, no register fault |
| Consumption history | 590, 610, 640, then 870 kWh across four months |
| Rate schedule | $0.22 per kWh and $12.00 fixed, **unchanged** in both periods |

The decisive arithmetic: the meter register moved 42,690 minus 41,820, which is
**870 kWh**. That equals the billed consumption exactly. The meter measured what
the customer was charged for. The rate did not change, and both bills reconstruct
exactly from the published rate. The increase survives daily normalisation, so
one extra billing day does not explain 230 extra kWh.

So the bill is explained by measured consumption at an unchanged price.

What the evidence does **not** do is establish a meter fault. It also does not
disprove one, because proving a meter healthy needs a physical test nobody has
performed. The honest position is that the customer's claim is **unsupported**,
which is not the same as false. The system holds that line in both directions.

## 5. Why independent compliance matters

The draft goes to a different agent with its own decision vocabulary. The author
does not check its own work.

Compliance can only approve by emitting one exact token, alone on the final line
of its answer. Everything else falls through to a default branch that withholds
the message and hands the case to a human. Release is the exception that has to
be earned, and in the current workflow it has to be earned three ways at once:

1. the compliance agent approved, with the exact token,
2. all six customer-facing parts of the message contain readable text,
3. the evidence, usage, policy and compliance outputs are each a real, structured
   result, not a sentence promising one.

Compliance must also give its reasons. A verdict nobody can explain is not an
auditable decision, and the second real run is why that rule exists.

One more separation matters. "Is this message safe to send?" and "does this case
still need a person?" are different questions, and the workflow answers them
separately. A message can be perfectly safe to send while the case behind it
still needs a human decision. That is exactly what happened in the final run.

## 6. What happened when it ran, three times

Nothing here is simulated. Each run is one real execution on Microsoft Foundry of
the same synthetic case, and each left an evidence folder that has not been
edited since.

**Before any run,** reading the deployed configuration found two defects at no
cost. The release gate applied a text operator to what is actually a table of
message records, which Microsoft's real Power Fx engine refuses to compile. And
one agent had been told the answer to the demonstration case. Both were fixed.
The corrected gate is right on 24 of 24 adversarial outputs on the real engine,
where the obvious one-line fix manages 13.

**Run 1, workflow v6.** Eight agents ran. Compliance approved. But the customer
was sent a line of unevaluated workflow code instead of the message, one
specialist asked for confirmation instead of doing its work, and the audit
record misstated parts of the run. Four defects, none of which any local test had
caught.

**Run 2, workflow v9.** Nine agents ran. This time compliance escalated, nothing
was sent to the customer, and the escalation agent produced a complete review
package for a human. That is the hosted fail-closed route working. But two
specialists wrote one sentence announcing their output and stopped, the
compliance agent gave a verdict with no reasons, and the audit said compliance
had approved when it had not. Why compliance escalated in that run is **not
established**, and this project does not claim to know.

**Finding the cause.** The instructions had already been changed after run 1, and
the stall came back in different words. So the instructions were not the cause.
The platform keeps a record of exactly what each agent received. It showed that
every agent after the first was handed the conversation so far, with every
earlier agent's answer looking like its own previous turn, and no new request.
The model was being asked to continue a conversation it appeared to have just
finished. Workflow v10 gives every agent an explicit request naming its step,
makes a stalled investigation unable to reach the customer, requires structured
output from the evidence, policy and audit agents, and requires reasons from
compliance. All of that was validated locally, at no cost, on Microsoft's own
open-source workflow engine, where both earlier failures were first reproduced.

**The acceptance criteria were written down before the final run,** fourteen of
them, in `docs/FINAL_RUN_ACCEPTANCE_PLAN.md`, with a rule that a branch the run
did not take would be reported as not observable, never as a pass.

**Final run, workflow v10. 14 of 14 passed.**

| What was checked | What the platform record shows |
| --- | --- |
| Did every specialist do its work? | Nine of nine returned a structured result |
| Evidence | A 22-entry ledger. Every value matched the case input by a mechanical check |
| Policy | Nine governed policies mapped, none invented |
| Arithmetic | 870 kWh on the register equals 870 kWh billed. Both bills reconstruct from the rate |
| Meter claim | No agent asserted a meter failure. The message says none was found and that remote checks have limits |
| Money | No credit promised. Any adjustment needs a Human Billing Supervisor |
| Compliance | **Approved**, with reasons naming the evidence, the policies and the checks relied on |
| Customer message | A readable six-part message was released, exactly the approved draft |
| Human follow-up | Decided separately. The open investigation went to a Billing Supervisor with a decision card |
| Audit | Agrees with the platform record on every point. Zero findings |

Note what did **not** happen. Compliance did not reject the final message, and
the final run did not take the fail-closed route. The message was supportable, so
it was approved. The honest demonstration of the fail-closed route is run 2.

Full records: `docs/FINAL_RUN_RESULT_2026-09-20.md`, and for the earlier runs
`docs/FIRST_RUN_AND_CORRECTIONS_2026-09-20.md` and
`docs/SECOND_RUN_RESULT_2026-09-20.md`.

## 7. What the customer and the supervisor experience

**The customer** asked whether the meter is broken. In the final run they were
told, in plain language, what was reviewed, what was found, why the bill changed,
what happens next and what is needed from them. The message says the register
moved 870 kWh, which matches what was billed, that the diagnostic passed, and
that no evidence of over-recording was found. It also says remote diagnostics
have limits and do not rule out every fault, and it offers a human-reviewed
on-site inspection. It promises no credit, and it does not brush them off.

**The supervisor** does not get a transcript to wade through. They get a decision
card: the decision needed, the known facts with their evidence identifiers, the
unknowns, the policies that apply, the risk, and a recommended next step. The
decision stays with them. No agent made it for them, and no agent can authorize
money.

The Control Center application in this repository shows the same case as a local,
offline demonstration. It makes no network call, and it is labelled on screen so
it cannot be mistaken for a Foundry run.

## 8. What has been tested, and what has not

This is stated plainly because overstating it would undermine the entire point of
the project.

**Run for real on Microsoft Foundry:** three executions of one synthetic case,
about $0.13 in total by the token counts Foundry returned, at list price. The
billed amount is not yet visible in Azure Cost Management, so that figure is
provisional. It is not a confirmed $0.00 and it is not a confirmed $0.13.

**Verified against the live configuration, read-only, at no cost:** 94 checks
that workflow v10 and all nine agents are exactly the reviewed versions, with no
external tools attached.

**Verified locally: 1,174 checks, none of which calls a model,** plus 105 cases on
Microsoft's real Power Fx engine.

| Suite | Result |
| --- | --- |
| Routing and case data | **83 passed, 0 failed** |
| Synthetic data integrity | **151 passed, 0 failed** |
| Control Center application | **156 passed, 0 failed** |
| Foundry runner, every response mocked | **357 passed, 0 failed** |
| The v10 workflow on Microsoft's open-source engine | **91 passed, 0 failed** |
| Evaluation package, deterministic checks and provenance | **198 passed, 0 failed** |
| Integration contracts and synthetic adapters | **138 passed, 0 failed** |

**What has not been shown.** One run is one sample of a system that is not
deterministic. Only one case has ever run. The fail-closed route has not been
seen on v10, only on v9. The 30 prepared evaluation cases and 16 adversarial
probes have not been executed. The correction loop is not built. Nobody is
actually notified when a case goes to human review.

**What it would take to put this in front of real customers.** Every record in
this project is synthetic, and no utility system is connected. The documented
plan, none of which is live:

- read-only connections to the billing and account system of record, and to the
  meter data system, replacing the synthetic records
- case intake, the released message and the human work item carried by the
  customer relationship management system
- policies held in a versioned, access-controlled store, not in agent
  instructions
- Microsoft Entra ID identities for the agents and role-based permissions for
  each tool and each reviewer
- a human authorizing every financial decision, in the system of record
- monitoring, traces and audit records retained under the utility's own schedule
- timeouts, retries and fail-closed handling per agent, staged rollout, and
  evaluation gates before each release
- a move from Foundry Workflows, a preview that retires on 2026-12-01, to
  Microsoft Agent Framework, which runs the same workflow definition. The local
  test harness already runs the v10 definition on that open-source engine

So the accurate description is: a production-oriented prototype whose core
workflow has been demonstrated end to end, once, on real infrastructure, with
synthetic data. See `docs/CURRENT_STATUS.md`.

## 9. Business impact

The value is not faster replies. It is that an explanation which cannot be
defended never reaches a customer.

- **Avoided unjustified adjustments.** An adjustment issued on an unsupported
  meter-fault conclusion is money out the door plus a technician dispatched for
  nothing. No agent can authorize money, and a message that asserts what the
  evidence does not support has to get past an independent reviewer first.
- **Regulatory defensibility.** Every released statement traces to evidence
  identifiers and policy identifiers, and every case terminates in an audit
  record. A billing action can be reconstructed afterwards by somebody who was
  not there.
- **Human attention spent where it matters.** Cases that genuinely need a
  person arrive already triaged, with the evidence attached and the missing
  evidence named, as the final run's review package shows.
- **Trust that survives scrutiny.** The system tells customers what the records
  show and declines to go further. That is a slower answer and a more durable one.

The transferable part is the pattern, not the billing domain. Any regulated
workflow where an AI-drafted statement has financial or legal consequence needs
the same separation: the thing that writes the answer must not be the thing that
clears it for release.

---

## Try it yourself, at no cost

```bash
# the routing defect and its fix
python tests/test_routing_and_data.py

# every synthetic record, provenance and honesty labelling
python tests/validate_synthetic_data.py

# the release gate on Microsoft's real Power Fx engine, needs the .NET SDK
dotnet run --project tests/powerfx_gate

# the live v10 workflow definition on Microsoft's open-source workflow engine
python tests/test_workflow_engine.py

# the application, including the refusal behaviour under pressure
cd control-center && npm install && npx vitest run
```

The three real runs are not reproduced by these commands. They are recorded in
`evidence/runtime/`, and `python -m runner analyze --run-dir <folder>` re-reads
any of them offline, at no cost.

The Control Center runs entirely locally, makes no network call, holds no
credential, and is labelled as an offline demonstration on screen so it cannot be
mistaken for a live agent run.
