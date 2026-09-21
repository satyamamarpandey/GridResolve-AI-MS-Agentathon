# Workflow v10: why specialists stalled, and what was changed

Written 2026-09-20, after the second real run and before any third. Everything
here was done with control-plane calls, read-only GETs and local tests. **No
model was called. Workflow v10 has not executed.**

## The cause, from the platform's own record

In two real runs, 3 of 17 agent invocations ended without the agent doing its
work. AccountEvidenceAgent asked for confirmation (run 1, 363 characters), then
announced its output and stopped (run 2, 312 characters, 64 output tokens).
PolicyKnowledgeAgent did the same in run 2 (256 characters, 49 tokens), after
producing a full mapping in run 1. Each response had status completed, zero
reasoning tokens and was not truncated.

`GET /openai/v1/responses/{id}/input_items` on every inner response of both runs
shows what each agent actually received. The first agent got one user message,
the case. Every later agent got that same user message, then every earlier
agent's output as plain `assistant` messages with no author, in some cases with
other agents' reasoning items, and **no new user turn**. The model was asked to
continue a conversation in which the last speaker looked like itself. In run 2
AccountEvidenceAgent described the previous agent's message as its own.

Through v9 every agent node had `input: messages: ""` on a shared conversation.
That is the cause. The instruction changes made after run 1 altered the wording
of the stall, from asking to announcing, and did not remove it.

Microsoft's open-source engine, run on the v9 YAML, reproduces the shape: no
message is given to any agent, and the last visible role is `user` for the first
agent and `assistant` for the other eight.

## The invocation correction

`InvokeAzureAgentExecutor.GetInputMessages` in Microsoft's agent-framework source
evaluates `input.messages` and converts a string to `ChatMessage(ChatRole.User,
text)`. Microsoft's `DeepResearch.yaml` and `CustomerSupport.yaml` samples pass an
explicit message on every agent node.

v10 sets `input.messages` on all ten agent nodes to a **plain literal string**.
No expression is used, so there is nothing for the expression engine to reject.
The empty string v9 used is the same form. The texts are in
`tests/workflow_engine/invocation_messages_v10.json`. Each one:

- begins `WORKFLOW STEP n of 9: <AgentName>.`
- says that the assistant messages above were written by other agents
- names the task, what to read and the output required
- says no operator is present and no confirmation will be given

None states a finding, a verdict or an expected outcome, by test. The case is not
repeated. The longest is 963 characters. The two escalation nodes state which
branch was taken, which is a fact the workflow knows and the agent cannot.

## A stalled investigation can no longer reach the customer

The gate gains a third term:

    =And(<compliance gate, byte-identical to v6>, <six readable fields, v9>, <investigation complete, v10>)

The new term reads text only, so it cannot raise a binding error. For the
evidence, usage, policy and compliance outputs it strips line feeds, carriage
returns, tabs and outer spaces, then requires the text to begin with `{` and to
contain its key field: `evidence_id`, `usage_summary`, `policy_id`, `decision`.
On the real outputs of both runs, 14 of 14 healthy outputs begin with `{` and 4 of
4 defective ones do not. The run 2 stall text contains the words
"evidence_ledger", which is why a keyword alone is not enough.

If the term is false the case takes the existing fail-closed escalation, and the
terminal audit runs. No retry loop and no new customer-visible message was added.

## Output contracts

Strict `json_schema` output, which run 2 showed working on a workflow agent, now
also applies to:

| Agent | Schema | Required fields |
| --- | --- | --- |
| AccountEvidenceAgent v9 | `evidence_ledger.schema.json` | 14, including `evidence_ledger`, `billing_comparison`, `meter_read_status`, `conflicts`, `missing_fields` |
| PolicyKnowledgeAgent v6 | `policy_mapping.schema.json` | 12, including `policy_ledger`, `policy_constraints`, `required_human_approval`. The genuine run 1 output validates against it |
| CaseAuditAgent v7 | `case_audit.schema.json` | 24. `agent_version` admits only `NOT_OBSERVED` |
| CustomerCommunicationAgent v5 | `customer_message.schema.json` | 14, unchanged |

Only `type`, `enum`, `required`, `properties`, `items`, `description` and
`additionalProperties: false` are used. The service accepted all three and read
back exactly what was sent. With a strict schema the agent cannot return a
sentence in place of its object.

The compliance and planner agents stay free text, because each must end with a
token line after its JSON, which a schema would forbid. The gate term above
covers compliance.

## Compliance must give reasons, and answers one question

EvidenceComplianceAgent v6. Its twenty checks, four decisions, bounded correction
rule and route-token rules are byte-identical to v5, asserted before publishing.
Added:

- the decision object and its reasons are required on every route, and the token
  line alone is never a complete response
- two questions are kept apart: whether this message is safe to release, which is
  the agent's, and whether the case still needs a person, which the workflow
  decides from the planner's follow-up token

It is told no verdict for any case. It may approve or escalate SYN-CASE-4003.
Either is acceptable if the reasons are given.

## The audit records what it can read

CaseAuditAgent v7 copies `compliance_route_token` from the final line of the
compliance output before it states a decision, and may record
`ESCALATED_WITHOUT_DECISION_OBJECT`. It judges participation and output status
from the WORKFLOW STEP messages, which are now in the conversation. It records
NOT_OBSERVED for every agent version, its own included. The platform record, not
the audit, remains the source of truth for versions, route, delivery and tokens.

## The runner checks the audit against the platform

Run 2's audit said compliance approved, and the runner did not notice. It now
compares the platform's token with the audit's decision, the route with
`final_disposition`, and each `output_status` with its own finding about that
output. It flags an output that announces future work, lacks its key field, or
gives a verdict without reasons. Replayed over the stored captures it reports six
audit findings for run 2 and seven for run 1.

It also refuses to execute, with zero requests, if any agent node has an empty
input, the gate lacks the investigation term, or one of the four schema agents is
not strict.

## Versions

| | Run 1 | Run 2 | Now |
| --- | --- | --- | --- |
| GridResolveAIWorkflow | 6 | 9 | **10** |
| CaseTriageAgent | 5 | 5 | 5 |
| AccountEvidenceAgent | 7 | 8 | **9** |
| UsageAnomalyAgent | 4 | 4 | 4 |
| PolicyKnowledgeAgent | 5 | 5 | **6** |
| ResolutionPlannerAgent | 5 | 6 | 6 |
| CustomerCommunicationAgent | 4 | 5 | 5 |
| EvidenceComplianceAgent | 5 | 5 | **6** |
| EscalationCoordinatorAgent | did not run | 5 | 5 |
| CaseAuditAgent | 4 | 6 | **7** |

Five agents were left alone: there is no failure evidence against them, and the
input message reaches them through the workflow. CaseTriageAgent and
UsageAnomalyAgent still carry a stale descriptive header naming workflow v5. It is
inert text, and republishing two healthy agents before a final run was judged the
larger risk.

| Payload | sha256 |
| --- | --- |
| Sent in run 1, label v6 | `d10a3af0396a842cc18a69ed96f132fef04bb3b5937263ddd545a04ae22c8d51` |
| Sent in run 2, label v9 | `045454848ca43de3d5aec6da9f7982a5965ca1e74735a3b95c91884e6f97b065` |
| Current, label v10, not sent | `baddf1f8febd366f40898998ccd27abd29dac452ec59c1bd45dfb5f722cb8520` |

All 48 values were compared with the run 1 payload. Only `workflow_version`
differs.

## Validated locally, with no model

- **Power Fx, Microsoft's engine, 105 cases.** Includes 17 for the new term, using
  the genuine outputs of both runs.
- **Workflow engine, Microsoft's open-source engine on the actual v10 YAML, 91
  checks.** Both historical failures are first reproduced on v9, then run on v10.
  All nine invocations receive a user message and see `user` as the last role.
  Scenarios: a healthy investigation approved with and without follow-up, a
  stalled evidence agent, a stalled policy agent, a token-only compliance output,
  an escalation with reasons, white-space fields, and a stalled escalation agent.
  The one healthy evidence ledger is an **offline fixture**, built
  deterministically from the case records and labelled `OFFLINE_FIXTURE`, because
  no real run has produced a ledger.
- **Runner, 357 checks, every response mocked.** Mutation testing on temporary
  copies: 80 of 80 deliberate faults in the runner are caught by those checks.
- **Live configuration, read-only, 94 checks.** Versions, the exact three-term
  gate, the ten messages, the four schemas, and the compliance rules.

None of this is Foundry execution evidence.

## Not established until a hosted run

- That the hosted service appends a literal `input.messages` as a user turn.
- That the hosted engine evaluates the third gate term as the local one does.
- Strict schemas on the evidence, policy and audit agents inside a workflow.
- That compliance v6 gives reasons and audit v7 is accurate. These are model
  behaviours and cannot be tested locally.
- Everything on the approve branch: the six-field release, the readable guard,
  the follow-up gate and `SetVariable`.
- The billed amount of either run.

Known limits carried forward: a field missing from the communication JSON still
stops the run at the gate with nothing sent and no audit, which the strict schema
makes unlikely and does not rule out. White space outside space, tab, carriage
return and line feed is not covered by the gate. The gate cannot judge meaning.

## Afterwards

Added later on 2026-09-20. The body above is left as written before the final
run, including its statements that workflow v10 has not executed. v10 has since
executed once, with separate owner approval. The behaviours listed under "Not
established until a hosted run" were then observed on the approve route: the
literal input message arriving as a user turn, the three-term gate, the strict
schemas, compliance giving reasons, an accurate audit, the six-field release and
the human follow-up handoff. The run passed 14 of 14 criteria written beforehand.
Still not observed: the fail-closed branch on v10, the third gate term returning
false, and the follow-up branch where no human is needed, with its `SetVariable`.
The billed amount is still not visible.
See `docs/FINAL_RUN_RESULT_2026-09-20.md`.
