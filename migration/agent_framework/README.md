# Microsoft Agent Framework migration proof

Foundry workflow agents are a preview feature, and the hosted workflow I tested
may not be where this system lives long term. I wanted to know, before anyone
asks, whether the same definition runs on Microsoft Agent Framework, the open
source runtime Microsoft publishes for agents and workflows.

**What this is:** a local proof, in its own directory, that the v10 workflow
definition runs unchanged on Agent Framework's declarative engine and takes the
same path the hosted Foundry service took in the final real run.

**What this is not:** a deployment. Nothing here replaces or modifies the live
v10 workflow. The agents are scripted, no model is called, and nothing here counts
as Foundry execution evidence.

## How the proof works

`parity_check.py` reads the final run's evidence folder
(`evidence/runtime/20260921T000142Z_SYN-CASE-4003_c2be2b51`), takes the nine
genuine agent outputs from `07_conversation_items.json`, and hands them to the
engine in `tests/workflow_engine` as scripted replies. That harness references
the NuGet package `Microsoft.Agents.AI.Workflows.Declarative` 1.22.0 and loads
`GridResolveAIWorkflow_v10.yaml`, the same YAML that is published in Foundry. The
Power Fx gate expressions are evaluated by the engine, not by my code.

It then compares the local run with what the hosted service recorded.

```
python migration/agent_framework/parity_check.py
```

Result on 2026-09-21: 11 of 11 checks passed. The machine-readable result is in
`parity_result.json`.

## Parity matrix

| Behaviour | Hosted Foundry, final run | Agent Framework, local replay | Parity |
| --- | --- | --- | --- |
| Agents invoked | Nine, in pipeline order | The same nine, same order | Verified |
| Action ids and order | 10 distinct actions in `04_workflow_actions.json` | All 10 executed, same order | Verified |
| Release gate, `And(gate_v6, readable_v9, investigated_v10)` | Evaluated true, release node ran | Evaluated true by the engine's Power Fx interpreter, release node ran | Verified |
| Customer message | 2,592 characters | Identical, character for character | Verified |
| Follow-up gate, planner token `CASE_FOLLOWUP::HUMAN_REQUIRED` | `node-followup-handoff` ran | `node-followup-handoff` ran | Verified |
| Branches not taken (fail closed, no follow-up) | Not taken | Not taken | Verified |
| Audit | CaseAuditAgent ran last | CaseAuditAgent ran last | Verified |
| Fail-closed branch | Observed hosted on v9 only | Covered by `tests/test_workflow_engine.py`, 91 checks | Local only for v10 |
| Literal `input.messages` per agent node | Confirmed from conversation items | The engine passes the same literal | Verified locally, see note |
| Agent reasoning | gpt-5-mini | Scripted replies | Not comparable, by design |
| Strict JSON schema on four agents | Enforced by the Foundry agent definition | Not enforced by the engine. It would move into each agent's response format | Open |
| Conversation storage, response read-back | Foundry conversations and responses API | None in this harness | Open |
| Identity | Entra ID, Azure AI User role | None, it is a local process | Open |
| Content filter | `Microsoft.DefaultV2` on the deployment | None, no model is called | Open |
| Telemetry | Spans in Application Insights | Engine events printed to stdout | Open |

Note on calibration: the same harness, given the v6 definition and run 1's
outputs, reproduces the defect the hosted service showed on 2026-09-20, including
the literal text `=Last(Local.VarCustomerDraft).Text` being sent to the customer.
That is my reason for treating the engine as a fair stand-in for routing. It is
not proof that the closed-source hosted service and the open-source engine agree
in every case.

## How the nine agents map

Each Foundry prompt agent becomes a `ChatClientAgent` with the same name,
instructions and response format. The workflow YAML does not change.

| Foundry piece | Agent Framework equivalent |
| --- | --- |
| Nine prompt agents, versioned in Foundry | Nine `ChatClientAgent` instances built from the exported instruction files in `agents/`, resolved by name through a `WorkflowAgentProvider` |
| `InvokeAzureAgent` nodes with literal `input.messages` | Unchanged. The declarative engine executes the same node type |
| Strict `json_schema` response format (AccountEvidence, PolicyKnowledge, CustomerCommunication, CaseAudit) | `ChatResponseFormat.ForJsonSchema` on the agent's chat options, using the four schema files already in `tests/workflow_engine` |
| Compliance and planner token lines | Unchanged, they are plain text the gates read |
| Release gate and follow-up gate (Power Fx) | Unchanged, evaluated by the engine |
| Release template, `compose_customer_message` | Unchanged, it is a `SendActivity` with a Power Fx expression |
| Escalation package to a Billing Supervisor | Unchanged as data. Delivery would go through the ticketing port in `integration/` |
| Foundry conversation per run | A thread store I would have to provide |
| Guarded runner (`runner/`) | Still needed. Budget cap, duplicate-run guard, evidence capture and offline analysis are mine, not the platform's |

## What a real migration would still need

1. A model client. `AzureOpenAIClient` with Entra ID, pointed at the existing
   gpt-5-mini deployment. This is the first step that costs money, so I have not
   done it.
2. One paid parity run on the same synthetic case, judged against the same 14
   pre-registered criteria, before trusting it.
3. Hosting. A container or Azure Functions app with a managed identity. None
   exists today.
4. Conversation and evidence storage that I own, with retention rules.
5. Content safety on the model call path, confirmed from a response header or a
   trace, not assumed.
6. OpenTelemetry export wired to a collector, with content recording switched off
   for real customer data.
7. The same release discipline: versioned agent definitions, a frozen workflow,
   and a run ledger.
