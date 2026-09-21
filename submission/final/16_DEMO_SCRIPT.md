# Demo Script

A live walkthrough for a judge, about three minutes. Everything shown is real: the deployed configuration, the stored evidence of three genuine runs, and local tests. **Nothing is executed during the demo.** No model is called and nothing is spent. The video has its own narration script in `submission/video/`. This script covers the same verified story for a live room.

Keep two things visibly apart throughout: hosted Foundry evidence, and the local Control Center, which is an offline demonstration and is labelled that way on screen.

---

**1. The case (25s)**
Open `submission/SYN-CASE-4003_input.json`. Read the customer line aloud: "My bill jumped significantly this month. The meter has to be broken. Please confirm the meter caused the increase and fix the charge."

Point at the evidence: two actual reads, 41820 and 42690, a difference of exactly the 870 kWh billed. No meter events. Diagnostic PASS, no tamper, no register fault. Usage rose 590, 610, 640, 870.

Say: "The customer has already decided the answer. The evidence does not support it. And note what is not in this file: nowhere does it tell the system what the right answer is."

**2. The agents and the workflow (35s)**
Foundry agents list, nine agents. Open EvidenceComplianceAgent. Show the decision vocabulary and the line "Never approve an UNSUPPORTED material claim."

Workflow designer, v10. Trace the sequence, then stop on the condition node.

Say: "The agent that writes the customer response is not the agent that approves it. Escalation is the default branch. Release is the exception, and it needs three things: an exact approval token, six readable customer fields, and a complete investigation."

**3. What really happened, three times (75s)**
Open `evidence/runtime/`. Three folders, one per genuine execution.

Say: "Run one approved, and then sent the customer a raw expression instead of the message. Run two failed safe: nothing was sent and a person got a review package. But compliance gave a verdict with no reasons, and two specialists stopped without doing their work, so we do not claim to know why it escalated."

Open `docs/V10_CORRECTIONS_2026-09-20.md`.

Say: "We did not guess at the cause. The platform records what each agent actually received. Every agent after the first was handed a conversation that ended in another agent's turn, and no new instruction. Version ten gives every agent an explicit message."

Open the final run folder, `07_conversation_items.json`, then `11_run_analysis.json`.

Say: "Final run. Nine of nine agents did their work. Twenty-two evidence entries, every value checked against the case input. Nine policies. Compliance approved the message and recorded why: it asserts no meter failure and promises no credit. The workflow released a readable message. Then a separate decision sent the still-open investigation to a Billing Supervisor. And the audit matched the platform record, zero findings."

Show `docs/FINAL_RUN_ACCEPTANCE_PLAN.md` beside `docs/FINAL_RUN_RESULT_2026-09-20.md`.

Say: "Fourteen criteria, written before the run. Fourteen passed."

**4. The message the customer received (20s)**
Show the released text in the final run's evidence.

Say: "It tells them what the records show, that the meter claim cannot be confirmed from them, that remote diagnostics do not rule everything out, and that a person will decide about an inspection. It does not promise a credit and it does not brush them off."

**5. Honest status (20s)**

Say: "This is a runtime-demonstrated prototype, not a production system. One synthetic case. Compliance approved, so the final run did not exercise the rejection branch. That was seen once, on version nine. No utility system is connected, the thirty evaluation cases have not been run, and the platform retires in December. About thirteen cents so far by token count. Azure has not shown a billed figure yet."

**6. Close (10s)**
"GridResolve AI is an evidence-first multi-agent system that will not let an AI explanation approve itself."

---

## Optional, if a judge wants to see something run

All local, all free, none of it a model call.

```
python tests/test_routing_and_data.py        # 83 passed
dotnet run --project tests/powerfx_gate      # 105 cases on Microsoft's Power Fx engine
python tests/test_workflow_engine.py         # 91 passed, the real v10 YAML on Microsoft's open-source engine
python -m runner analyze --run-dir evidence/runtime/20260921T000142Z_SYN-CASE-4003_c2be2b51
```

The last command re-reads the stored evidence of the final run offline and reprints the route, the release and the audit cross-check. The Control Center can be opened alongside to show the evidence and the claim ledger interactively. Say aloud that it is an offline demonstration and not Foundry output.

## Rules

- Never say compliance rejected the final draft. It approved it, with reasons.
- Never say the final run took the fail-closed branch. Run 2 did, on v9, without reasons.
- Never claim parallel execution, a correction loop, an evaluation score or a live integration.
- Never state a billed amount. The provisional figure is about $0.13 and the billed figure is not yet visible.
- Never call it production-ready.
- Never show an invented trace, score or token count. If a judge asks what was not proven, answer directly and name it, because the labeling throughout the submission is the credibility argument.
