# Workflow: v4 to v10

Full flow and node list are in `03_ARCHITECTURE.md`. This document records what changed and why, because the sequence of changes is the most substantive engineering result in the project. The live version is **v10**. It has executed once in the hosted service and passed 14 of 14 pre-registered criteria.

| Version | What changed | Found by | Ran in the hosted service |
|---|---|---|---|
| v4 | Original. Gate tested for the word "approve". Every node auto-sent its output | | no |
| v5 | Exact sentinel token, escalation as the default branch, drafts withheld | Reading the deployed YAML | no |
| v6 | Gate reads the text of the last message, approves only on an exact, unique, final-line token | The real Power Fx engine: v4 and v5 do not compile | **run 1** |
| v7 | Release changed from an `=expression` to a `{...}` template | Run 1: the customer was sent the expression as literal text | no |
| v8 | Six customer fields released instead of raw JSON. A separate follow-up gate after approval | Review of what a customer would actually receive | no |
| v9 | White-space-only fields are withheld | Local tests on the real engine | **run 2** |
| v10 | An explicit input message on every agent node. A third gate term: the investigation must be complete | Run 2, and the platform's record of what each agent received | **final run** |

## v4 to v5: the routing condition

**v4**
```yaml
- condition: =Not("APPROVE" in Local.Var1497)
  actions: [ InvokeAzureAgent EscalationCoordinatorAgent ]
- condition: "true"
  actions: []
```

`Local.Var1497` holds the EvidenceComplianceAgent output, including free-text fields such as `compliance_summary` and `correction_instructions`. Microsoft documents the Power Fx `in` operator as matching regardless of case, with `exactin` as the case-sensitive form.

So, treating that output as text, a rejection whose explanation read "cannot approve this unsupported meter claim" contained "approve", making the condition false, skipping escalation, and sending the case straight to audit. `tests/test_routing_and_data.py` reproduces it on eleven mocked outputs: the v4 condition skips escalation on 5. That is a local text-only model. It was never observed in the hosted service, where v4 never ran.

**v5** replaced the word with an exact sentinel token and inverted the branches so that escalation is the default and release is the exception. It also set `autoSend: false` on all seven investigation and drafting nodes. In v4 the drafted customer message was published before compliance had seen it.

## v5 to v6: the gate did not compile

Preparing the first real run meant evaluating the gate on Microsoft's own Power Fx engine against the real variable shape. `Local.Var1497` is filled by `output.messages`, which is a **table of message records**, not text. The v4 gate and the v5 gate both fail to compile against it. On the open-source workflow engine a run would have stopped at the gate after seven agents had billed, with no escalation and no audit.

v6 reads `Last(Local.Var1497).Text` and approves only when the approval token appears exactly once, in exact case, alone on the final line, with no escalation token anywhere. It is correct on 24 of 24 adversarial outputs, where the obvious one-line fix manages 13. That term is byte-identical in v10.

## v6 to v9: what run 1 showed

Run 1 took the approve branch, correctly. It then sent the customer the literal text `=Last(Local.VarCustomerDraft).Text`. `SendActivity.activity` is a template, not an expression. v7 uses a `{...}` template.

v8 stopped releasing the communication agent's JSON and releases its six customer-facing fields as readable text with plain headings. It also separated two questions that v6 had merged: whether the message is safe to send, and whether the case still needs a person. After an approval, a second gate reads the planner's `CASE_FOLLOWUP` token and hands the case to a human unless the token is exactly `NONE_REQUIRED`.

v9 withholds the message when any of the six fields holds only spaces, tabs, carriage returns or line feeds.

## v9 to v10: why specialists stalled

In runs 1 and 2, three of seventeen agent invocations ended with the agent asking for confirmation or announcing its work and stopping. Instruction changes after run 1 altered the wording of the stall and did not remove it.

The platform's record of each inner response shows what each agent received: the case as one user message, every earlier agent's output as plain assistant messages with no author, and **no new user turn**. Through v9 every node passed `input: messages: ""`. The model was continuing a conversation whose last speaker looked like itself. Microsoft's open-source engine reproduces the shape on the v9 YAML.

v10 sets `input.messages` on all ten agent nodes to a plain literal string, which Microsoft's agent-framework source converts to a user message. No expression is involved. The gate also gains a third term, so that a specialist that returns a sentence instead of a JSON object sends the case to a human:

```
=And(<compliance token term, v6>, <six readable fields, v9>, <investigation complete, v10>)
```

In the final run every agent received its message as a user turn, every agent returned its JSON object, and the three-term gate compiled and evaluated in the hosted service.

## Verification

| Suite | Result |
|---|---|
| `tests/test_routing_and_data.py`, routing semantics and case data | 83 passed |
| `tests/powerfx_gate`, Microsoft's Power Fx engine | 105 cases, 0 failures: 24 gate, 6 release, 7 harness, 15 follow-up, 36 white-space, 17 investigation |
| `tests/test_workflow_engine.py`, the actual YAML on Microsoft's open-source workflow engine, agents scripted | 91 passed. Both historical failures are reproduced on v9 first, then run on v10 |
| `tests/verify_live_config.py`, read-only against the live configuration | 94 passed |

None of those calls a model, and none is Foundry execution evidence. The execution evidence is in `evidence/runtime/`.

## What is still not proven

- The fail-closed branch on v10. It was taken once, on v9.
- The follow-up branch where no person is needed.
- The third gate term returning false in the hosted service.
- A field missing from the communication JSON still stops the run at the gate with nothing sent and no audit. The strict schema makes that unlikely and does not rule it out.
- White space outside space, tab, carriage return and line feed is not covered.
- Any second run. One run is one sample of a non-deterministic system.

Every earlier workflow version remains in Foundry version history, so each change is reversible.
