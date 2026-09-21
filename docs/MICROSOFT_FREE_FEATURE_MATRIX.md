# Microsoft Free Feature Matrix

Date: 2026-09-19
Purpose: record which Microsoft capabilities were used, which were deliberately
avoided, and why, under a hard zero-spend constraint.

## 1. The rule applied

When cost behavior could not be verified in advance from published documentation,
the action was skipped and recorded as
`PREPARED_NOT_EXECUTED_DUE_TO_ZERO_COST_CONSTRAINT`.

Three assumptions were explicitly refused:

- That a preview feature is free.
- That a catalog entry is a provisioned service.
- That a free request allowance eliminates infrastructure or dependent-resource
  charges. A service with free transactions can still bill for the storage,
  gateway or observability resource it requires.

## 2. Used, with no charge incurred

| Capability | How it was used | Why it cost nothing |
| --- | --- | --- |
| Foundry agents control plane | Created and read nine agents and five workflow versions over the REST API | Configuration reads and writes are control-plane operations, not inference |
| Foundry Workflows Preview | Deployed workflow v5 with the `Foundry-Features: WorkflowAgents=V1Preview` header | Saving a definition is not executing it |
| Azure CLI token acquisition | `az account get-access-token --resource https://ai.azure.com` | Authentication is free |
| Azure Retail Prices API | Verified gpt-5-mini pricing before estimating any run | Public, unauthenticated, free |
| Azure Cost Management, month to date | Confirmed actual spend rather than assuming it | Included in the subscription, though it rate limits |
| Browser Web Speech API | Speech to text and text to speech in the Control Center | A browser capability, not an Azure service |
| Local Vite and React | The entire Control Center runs locally | No hosting resource was created |

## 3. Available but deliberately not used

| Capability | Why it was skipped | Status |
| --- | --- | --- |
| gpt-5-mini inference | Every completion is billed per token | NOT_INVOKED |
| text-embedding-3-large | Billed per token | NOT_INVOKED |
| Workflow execution and preview run | Executes agents, therefore bills | NOT_EXECUTED |
| Foundry evaluations and LLM judge | One or more model calls per case per evaluator | PREPARED_ONLY |
| Agent Optimizer | Requires runs to optimize against | NOT_INVOKED |
| Bing grounding and Web Search | Billed per query, and unnecessary on synthetic data | NOT_INVOKED |
| Foundry IQ | Cost behavior not verifiable in advance | NOT_INVOKED |
| Azure AI Search | Billed hourly from the moment of provisioning, regardless of use | NOT_PROVISIONED |
| Foundry managed memory store | Replaced with local browser memory | NOT_PROVISIONED |
| Voice Live API and Azure Speech | Replaced with the browser Web Speech API | NOT_PROVISIONED |
| Application Insights | Corrected 2026-09-21. One was created with the Foundry project on 2026-09-17 and is connected to it. It holds 61 platform spans, about 2.5 MB, from the three real runs. I added nothing to it | PROVISIONED WITH THE PROJECT |
| API Management, AI Gateway | Tier pricing could not be confirmed as free for this use, so it was skipped rather than guessed | NOT_PROVISIONED |
| Azure Storage, databases, Functions, Logic Apps | No supporting infrastructure was needed for a local demonstration | NOT_PROVISIONED |
| Hosted agent deployment, published endpoints | Hosting is billed | NOT_DEPLOYED |
| Foundry Local | Investigated as an offline inference option, not installed | PREPARED_ONLY |

## 4. Substitutions made

Each substitution preserves the demonstrable behavior while removing the charge.

| Paid capability | Local substitute | What is preserved | What is lost |
| --- | --- | --- | --- |
| Foundry Memory | Per-case namespaced browser storage with isolation tests | Case-scoped conversation continuity and a provable isolation guarantee | Cross-session and cross-device persistence |
| Azure Speech | Browser Web Speech API | The voice interaction pattern, both directions | Service-grade accuracy, custom voices, and telemetry |
| Application Insights | An OpenTelemetry-compatible span schema defined locally, plus a read-only export of the platform's own spans in `evidence/platform_telemetry/` | The shape of the local trace, and what the platform recorded for the three real runs | Alerting, dashboards, or a content recording policy |
| LLM-judged evaluation | 192 local static tests across seven suites | Provable correctness of routing, arithmetic, provenance and isolation | Judgement of language quality, which genuinely needs a model |
| Live agent responses | Deterministic template responder | A demonstrable conversation that refuses to guess | Natural language flexibility, which is the whole point of the model |

The last row is the important one. The offline responder is not presented as a
model and is not a substitute for one. It demonstrates the interaction contract:
what the system will say, what it refuses to say, and what it escalates.

## 5. Net position

| Measure | Value |
| --- | --- |
| Model completions requested | 0 |
| Tokens spent | 0 |
| Workflow executions | 0 |
| Evaluation runs | 0 |
| Billable resources created | 0 |
| Azure cost incurred | $0.00 |
| Local checks executed and passing | 192 |
| Configuration defects found and fixed before any run | 6 |

The defects were found by static verification rather than by a run, which is the
substantive point. A fail-open compliance gate that skipped escalation on 5 of 11
cases requiring it was identified, fixed and proven fixed without spending
anything.
