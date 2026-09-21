# Microsoft Agent Framework Migration Plan

Status: DESIGN ONLY. Nothing in this document has been built or executed.
Date: 2026-09-19
Scope: GridResolveAIWorkflow v5, nine agents, Microsoft Foundry.

## 1. Why migrate at all

The current system is a declarative Foundry Workflow. That gave us a deployable
orchestration quickly and a routing gate we could statically verify. It also has
three limits that matter for this problem:

1. Execution is strictly sequential. Seven investigating agents run one after
   another when four of them have no data dependency on each other.
2. There is no correction loop. When the compliance gate rejects a draft, the
   only available action is to escalate. There is no path back to the planner or
   the communication agent.
3. Deterministic work runs inside a language model. Bill arithmetic, meter
   reconciliation and claim provenance are computed by prompting rather than by
   code, which is both slower and less trustworthy than it needs to be.

The Microsoft Agent Framework addresses all three, because orchestration becomes
code rather than declarative YAML.

## 2. What maps directly

| Current, Foundry Workflow v5 | Agent Framework equivalent |
| --- | --- |
| Nine Foundry agents | Nine `ChatAgent` instances over the same model deployment |
| `InvokeAzureAgent` node | An agent invocation inside a workflow executor |
| `output.autoSend: false` | Return the result to the orchestrator instead of emitting it |
| `ConditionGroup` on a route token | A typed switch on a structured decision object |
| `SendActivity` | An explicit emit step, still gated |
| Sequential trigger actions | A `WorkflowBuilder` graph |

The agent instructions, the evidence contract and the policy library carry over
unchanged. That is deliberate. The migration changes orchestration, not the
domain logic, so the existing behavior remains comparable before and after.

## 3. What improves

### 3.1 Parallel investigation

AccountEvidenceAgent, UsageAnomalyAgent and PolicyKnowledgeAgent read different
inputs and produce independent outputs. They can fan out from CaseTriageAgent and
fan in to ResolutionPlannerAgent. On the current sequential path the wall-clock
cost is the sum of three agents; with a fan-out and join it is the maximum of the
three. Nothing about the result changes, only the latency.

The join must be a real join. Partial results are not acceptable input to the
planner, because a plan built on two of three evidence streams would produce
claims that reference evidence nobody collected.

### 3.2 Typed routing instead of string matching

The current gate matches a sentinel substring inside model prose using Power Fx
`in`, which is case-insensitive substring matching. That is why v4 failed open:
the condition `Not("APPROVE" in output)` was satisfied by any prose containing
the word "approved", "approval" or "disapprove". We fixed it by requiring an
exact sentinel token, and 72 local tests prove the fix.

A sentinel in prose is still a weaker contract than a typed object. In the Agent
Framework the compliance agent returns a structured decision:

```
ComplianceDecision {
  decision: APPROVE | REJECT_AND_REPLAN | REJECT_AND_REWRITE | HUMAN_REVIEW_REQUIRED
  unsupported_claim_ids: string[]
  reason: string
}
```

Routing then switches on `decision`, an enum, and an unparseable response falls
through to `HUMAN_REVIEW_REQUIRED` rather than to an accidental approval. The
fail-closed property is preserved and the matching ambiguity disappears.

### 3.3 Bounded correction loops

Two rejection paths become useful once routing is typed:

- `REJECT_AND_REPLAN` returns to ResolutionPlannerAgent with the list of
  unsupported claim identifiers.
- `REJECT_AND_REWRITE` returns to CustomerCommunicationAgent with the same list.

Both need a hard bound. The design limit is two correction attempts per case,
after which the case escalates regardless. An unbounded loop against a paid model
is a cost incident waiting to happen, and an agent that keeps rewriting until the
gate accepts it is optimizing against the gate rather than against the evidence.

The attempt count belongs in the audit packet, because "approved on the third
attempt" is a materially different record from "approved on the first".

### 3.4 Deterministic tools as real tools

Thirteen deterministic functions already exist in this repository and are covered
by 37 tests: bill change, usage change, rate effect decomposition, meter read
validation, estimated true-up detection, policy lookup, evidence and policy
identifier validation, claim ledger validation, duplicate adjustment detection,
case cost calculation, case state validation and audit packet assembly.

In the current Foundry configuration all nine agents have zero tools attached, so
the model does this arithmetic in prose. Under the Agent Framework these are
registered as callable tools. The financial numbers then come from code that is
tested, and the model's job narrows to interpretation and wording, which is what
it is actually good at.

This is the single largest correctness improvement available, and it costs
nothing to prepare because the functions are already written and tested.

## 4. Target workflow shape

```
CaseTriageAgent
      |
      +--> AccountEvidenceAgent ----+
      +--> UsageAnomalyAgent -------+--> ResolutionPlannerAgent
      +--> PolicyKnowledgeAgent ----+
                                          |
                                CustomerCommunicationAgent
                                          |
                                 EvidenceComplianceAgent
                                          |
        +-------------------+-------------+-------------------+
        |                   |             |                   |
     APPROVE       REJECT_AND_REPLAN  REJECT_AND_REWRITE  HUMAN_REVIEW
        |                   |             |                   |
      emit           back to planner  back to comms   EscalationCoordinator
        |              (max 2)          (max 2)               |
        +-------------------+-------------+-------------------+
                                          |
                                   CaseAuditAgent
```

CaseAuditAgent remains terminal on every path. An unaudited outcome is not an
acceptable outcome.

## 5. What does not change

- Fail-closed default. Anything that is not an explicit approval escalates.
- Human escalation is mandatory for unsupported material claims.
- No customer message is emitted before the gate approves it.
- Synthetic data only.
- The evidence and policy identifier contract.

## 6. Migration sequence

1. Port the thirteen deterministic tools into the agent tool registry. No
   behavior change, they are already tested.
2. Rebuild the sequential path in `WorkflowBuilder` and confirm it produces
   comparable output to v5 on the synthetic cases.
3. Convert the compliance output to a typed object and switch routing to the
   enum. Re-run the routing tests against the new shape.
4. Introduce the fan-out and join for the three independent investigators.
5. Add the two correction paths with the attempt bound and the audit field.
6. Add tracing spans per executor.

Steps 1 through 3 are pure refactors with test coverage on both sides. Steps 4
through 6 change observable behavior and need their own evaluation run.

## 7. Cost note

Every step above requires model execution to validate, which spends money. None
of it has been run. The plan is written so that the decision to spend is made
against a concrete sequence rather than an open-ended intention.

Current execution status: PREPARED_NOT_EXECUTED_DUE_TO_ZERO_COST_CONSTRAINT.
