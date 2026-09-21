# Three-Minute Judge Pitch

Spoken version. The video script covers the same ground with visuals; this is for a live room and for Q&A.

---

**Problem (0:00 to 0:20)**

A customer's bill jumps from 640 to 870 kilowatt hours. They call and say: my meter has to be broken, confirm it and fix the charge. They have already decided the answer. They want the system to agree.

That single sentence is where utility AI goes wrong.

**Why a chatbot is unsafe here (0:20 to 0:40)**

A single assistant gathers the evidence, decides the cause, writes the explanation, and approves its own answer, all in one pass. Under pressure from a confident customer, the easiest output is agreement. In billing that is not a bad chat reply. That is an unsupported claim about a physical asset, and the utility has to defend it to a regulator.

**Architecture (0:40 to 1:05)**

GridResolve AI splits it into nine accountable agents on Microsoft Foundry: triage, account evidence, usage analysis, policy, planning, communication, independent compliance, human escalation, and audit. Every material claim carries the evidence IDs and policy IDs supporting it. The agent that writes the answer is never the agent that approves it, and the workflow releases nothing unless three conditions hold: an exact approval token, a readable message, and a complete investigation.

**What happened when we ran it (1:05 to 2:00)**

We ran this case three times in Foundry, and I want to tell you about all three.

Run one approved the draft, and then sent the customer a raw expression instead of the message. Run two failed safe: nothing went to the customer and a person got a review package. But compliance gave a verdict with no reasons, and two specialists stopped without doing their work. So we do not claim to know why it escalated.

We did not guess at the cause. The platform records what each agent actually received. Every agent after the first was handed a conversation that ended in another agent's turn, with no new instruction. So some of them just continued it. Version ten gives every agent an explicit message.

Then we wrote fourteen acceptance criteria before the final run, so the result could not shape them. Fourteen passed. Nine of nine agents did their work. Twenty-two evidence entries, every value matched to the case. Nine policies. The meter register moved 870 kilowatt hours, exactly what was billed, at an unchanged rate.

**Compliance, release, human, audit (2:00 to 2:25)**

The draft asserted no meter failure and promised no credit. So independent compliance approved it, and recorded why. The workflow released a readable message. Then a separate decision, from the planner's own follow-up token, sent the unresolved investigation to a Billing Supervisor with a decision card, because only a physical test can settle the customer's claim and only a person can approve money. An approved message did not erase the open case. And the audit record matched the platform record, with zero findings.

**Honest status (2:25 to 2:45)**

This is a runtime-demonstrated prototype, not a production system. One synthetic case, one successful run. Compliance approved, so the final run did not exercise the rejection branch. No utility system is connected, thirty evaluation cases and sixteen red-team scenarios are written and not yet run, and Foundry Workflows retires in December, so the plan is Microsoft Agent Framework, which already runs our workflow file in our local tests. About thirteen cents so far, by token count. Azure has not shown a billed figure yet.

**Impact and close (2:45 to 3:00)**

The metric that matters is unsupported claims reaching a customer, target zero. A wrong billing explanation costs a truck roll, a complaint, and sometimes a regulatory finding.

GridResolve AI is an evidence-first multi-agent system that will not let an AI explanation approve itself.

---

## Delivery notes

Lead with the customer sentence, not the architecture. Nine agents is not the story; self-approval is.

Tell all three runs. The two failures are the credibility argument, not an embarrassment: a system that failed safe, a cause proven from the record instead of guessed, and a fix that then passed criteria fixed in advance. Hiding runs one and two would make the third look like luck.

Do not say compliance rejected the draft. It approved a supported message, with reasons, and the case still reached a human. If a judge asks where the rejection is: the agents upstream never asserted the meter fault, so there was nothing unsupported to reject. Run two took the fail-closed route, and we say plainly that it gave no reasons.

Do not call it production-ready, and do not state a billed amount.

If time runs short, cut the impact line. Never cut the three runs.

## Candidate one-line positioning

Chosen: **"GridResolve AI is an evidence-first multi-agent utility resolution system that will not let an AI explanation approve itself."**

It names the domain, the method and the differentiator in one breath, and the final clause is concrete rather than abstract.

Alternatives considered:
- "GridResolve AI turns complex billing investigations into evidence-backed, policy-controlled decisions with independent AI compliance and human authority." Accurate but four concepts long, and it fades.
- "No agent gathers the evidence, writes the answer, and approves it too." Punchier, but omits the domain.
