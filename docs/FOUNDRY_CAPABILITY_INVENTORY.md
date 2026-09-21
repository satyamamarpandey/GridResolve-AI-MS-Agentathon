# Microsoft Foundry capability inventory

Taken 2026-09-21 by read-only inspection of the existing project. Every Azure call
behind this page was a GET, a read-only log query, or one Cost Management query.
No model was called, no workflow ran, and nothing was created, attached or
enabled. After the inspection the resource shows the same 26 lifetime model
requests it showed before, all from the three approved runs.

The rule I applied: a capability goes into the system only if it adds technical
substance, leaves the validated v10 workflow alone, and is free by Microsoft's own
documentation. If I could not confirm the price, I did not do it.

## Cost classes

| Class | Meaning |
| --- | --- |
| FREE AND VERIFIED | Microsoft documents no charge, and I checked the current resource configuration |
| FREE CONTROL PLANE | Reading or defining configuration. No inference, no storage meter |
| COST UNKNOWN | I could not find a price in official documentation. Not done |
| BILLABLE | Documented charge. Not done |
| NEEDS PAID INFRASTRUCTURE | Depends on a resource that bills on its own. Not done |

## Pricing sources I relied on

| Topic | What the documentation says | Source |
| --- | --- | --- |
| Agents and workflows | "There is no additional charge for creating or running Foundry-native agents using prompts and workflows." Model tokens and tools are billed | azure.microsoft.com/pricing/details/foundry-agent-service |
| Standard and Global Standard deployments | Pay per token. An idle deployment costs nothing | learn.microsoft.com/azure/foundry/foundry-models/concepts/deployment-types |
| File Search | $0.10 per GB of vector storage per day | learn.microsoft.com/azure/foundry/agents/how-to/tools/file-search |
| Code Interpreter | Charged per session on top of tokens | learn.microsoft.com/azure/foundry/agents/how-to/tools/code-interpreter |
| Evaluations | Quality evaluators bill as model tokens with no surcharge. Safety, red teaming and playground evaluations bill on a separate AI evaluations meter | azure.microsoft.com/pricing/details/foundryobservability |
| Memory (preview) | "You're billed for usage of the underlying chat and embedding models you configure." | learn.microsoft.com/azure/foundry/agents/concepts/what-is-memory |
| Azure Monitor | Platform metrics are free to collect. Queries on analytics logs are not charged. Log ingestion is billed per GB, with 31 days of retention included. I could not confirm the size of the free monthly allowance from the page, so I do not rely on it | learn.microsoft.com/azure/azure-monitor/logs/cost-logs |
| Content filters | Deployment level filters are included in model pricing, with no separate meter. The source is a Microsoft Q and A answer, not a pricing page, so I treat it as likely rather than certain | learn.microsoft.com/answers/questions/5841263 |
| Fine-tuning | Hourly training cost, plus an hourly hosting fee for the deployed model | learn.microsoft.com/azure/foundry/openai/how-to/fine-tuning-cost-management |
| Routines and schedules | No pricing found | learn.microsoft.com/azure/foundry/agents/how-to/use-routines |
| Workflows | Preview. "Microsoft Foundry is retiring workflows on December 1, 2026." Microsoft points to Agent Framework | learn.microsoft.com/azure/foundry/agents/concepts/workflow |
| Cost Management | Usage appears in 8 to 24 hours, up to 72 hours on pay-as-you-go | learn.microsoft.com/azure/cost-management-billing/costs/understand-cost-mgt-data |

## Build

Columns: configured today, used by GridResolve, relevant to utility billing, can
be added without touching the workflow, free to create, free to operate, could
start model inference, could create recurring charges, would improve the
technical evidence, what proves it.

| Capability | Configured | Used | Relevant | No workflow change | Free to create | Free to operate | Can start inference | Recurring charge | Improves evidence | Proof | Class | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Agents | Yes, 9 prompt agents, versions 4 to 9 | Yes | Yes | n/a | Yes | Tokens only | Yes, when invoked | No | Already the core | `tests/verify_live_config.py`, F10-AGENTS capture | FREE CONTROL PLANE to read | Frozen. Read only |
| Workflows | Yes, GridResolveAIWorkflow v10 | Yes | Yes | n/a | Yes | Tokens only | Yes, when run | No | Already the core | Three evidence folders, F10-WORKFLOW capture | FREE CONTROL PLANE to read | Frozen. Retires 2026-12-01, so I proved the Agent Framework path locally |
| Routines | No, 0 schedules | No | Yes, for overnight batch review | Yes | Unknown | No, every firing runs an agent | Yes | Yes | Only if run | Schedule listing returns 0 | COST UNKNOWN | Design only, `docs/ROUTINES_SKILLS_TOOLS_MEMORY_DESIGN.md` |
| Models | Yes, `gpt-5-mini` Global Standard 50K TPM. `text-embedding-3-large` Standard, never called | `gpt-5-mini` only | Yes | n/a | Yes | Tokens only, idle is free | Yes | No | No | Deployment listing | FREE CONTROL PLANE to read | No change. The embedding deployment has 0 requests |
| Services (Speech, Language and similar) | No | No | Low | Yes | Varies | No | Some | Some | No | n/a | BILLABLE | Excluded, no value for this case |
| Tools | None attached to any agent | No, by design | Yes, for read-only account lookups | No, it changes validated agents | Yes | Depends on the tool | Indirectly | Depends | Not without a run | Agent definitions show no tools | BILLABLE for File Search, Code Interpreter, Bing | Not attached. Typed contracts and mocks built locally in `integration/` |
| Toolboxes | No, 0 | No | Low | Yes | Unknown | Unknown | No | Unknown | No | Listing returns 0 | COST UNKNOWN | Excluded. An empty toolbox proves nothing |
| Skills | Not inspected by API | No | Medium | Yes | Unknown | Unknown | Yes when used | Unknown | No | n/a | COST UNKNOWN | Specified as local deterministic skills only |
| Knowledge (Foundry IQ, Azure AI Search) | No, 0 indexes | No | Yes, for the tariff library | Yes | No | No | Embeddings at index time | Yes, hourly | Only with a run | Index listing returns 0 | NEEDS PAID INFRASTRUCTURE | Excluded. Local policy catalog with provenance built instead |
| Memory | No, 0 memory stores | No | Low. A billing case must not inherit another customer's context | Yes | Yes | No, chat and embedding tokens | Yes | Per use | No | Listing returns 0 | BILLABLE | Excluded. Design note only |
| Guardrails | Yes, `Microsoft.DefaultV2` on both deployments | Yes, on every call | Yes | n/a | Included | Included | No | No | Yes, strongly | Policy contents, plus 26 span verdicts | FREE AND VERIFIED to read | Evidence gathered. No custom policy created or attached, see `docs/SECURITY_AND_GOVERNANCE_EVIDENCE.md` |
| Data (datasets) | No, 0 datasets, 0 files | No | Yes | Yes | Unknown, storage location not confirmed | Unknown | No | Possibly | Marginal | Listing returns 0 | COST UNKNOWN | Not uploaded. Foundry shaped JSONL prepared locally in `evaluation/datasets/` |
| Evaluations | No, 0 evals, 0 evaluators listed | No | Yes | Yes | Yes | No, tokens or the evaluations meter | Yes | Per run | Yes, if run | Listing returns 0 | BILLABLE | Not started. Deterministic local checks run instead, and clearly labelled as such |
| Red teaming | No, 0 runs | No | Yes | Yes | Yes | No, evaluations meter | Yes | Per run | Yes, if run | Listing returns 0 | BILLABLE | Not started. 16 probes prepared, never executed |
| Fine-tuning | No, 0 jobs | No | No, three runs is not training data | Yes | No | No | Yes | Yes, hourly hosting | No | Listing returns 0 | BILLABLE | Excluded |

## Operate

| Capability | Configured | Used | What I found | Class | Decision |
| --- | --- | --- | --- | --- | --- |
| Overview and assets | Yes | Read | 10 agent assets: the workflow and nine agents | FREE CONTROL PLANE | Read only |
| Compliance | Yes, the default guardrail is what the portal reports on | Read | Default policy on both deployments, no custom policy | FREE CONTROL PLANE | Documented in the governance page |
| Agent monitoring | Yes | Read | The portal shows 100 percent success. Two of the three runs had stalled agents, so that number measures HTTP status, not correctness | FREE CONTROL PLANE | Explained in `docs/OPERATIONS_MONITORING_AND_COST.md` |
| Traces | Yes. Application Insights was connected when the project was created | Found today | 61 spans for the three runs, with agent versions, token counts and content filter verdicts. About 2.5 MB ingested | Reading is FREE AND VERIFIED. Ingestion was already on and is billed per GB | Exported a redacted summary. Changed nothing. Flagged that ingestion and content recording are on |
| Usage metrics | Yes, platform metrics | Read | 186,614 input and 42,155 output tokens, 26 model requests. Equal to my runner's figures to the token | FREE AND VERIFIED | Used as independent confirmation |
| Estimated cost | Yes | Read | Portal shows about $0.16. My runner computes $0.1311. Cost Management shows nothing yet | FREE CONTROL PLANE | Three figures reported separately |

## Manage

| Capability | What I found | Class | Decision |
| --- | --- | --- | --- |
| Project configuration | One project, system assigned identity, default connection to Application Insights | FREE CONTROL PLANE | Read only |
| Resource configuration | AIServices, S0, public network access enabled, key authentication still allowed, no customer managed key, no diagnostic settings | FREE CONTROL PLANE | Reported as gaps. Not changed, because each change alters a validated system |
| Quota | `gpt-5-mini` 50 requests and 50,000 tokens per minute. Embedding 120 | FREE CONTROL PLANE | Enough for one sequential case. Not for concurrent cases |
| Deployment configuration | Model version upgrades automatically when a new default appears | FREE CONTROL PLANE | Reported. A production system would pin it |
| Access control | Owner for one user. Azure AI User for two users and one service principal | FREE CONTROL PLANE | Reported for review |
| Connected resources | Application Insights, Log Analytics workspace, one action group, all created with the project | FREE CONTROL PLANE | Reported. I added none |

## Meaningful free improvements, in priority order

| Priority | Improvement | Why it matters | Status |
| --- | --- | --- | --- |
| 1 | Read back the platform's own traces and metrics for the three runs | Independent confirmation of tokens, agent versions and guardrail verdicts, from Microsoft's side | Done. `scripts/export_platform_telemetry.py`, `evidence/platform_telemetry/` |
| 1 | State actual guardrail and security configuration, with a control matrix | Replaces assumption with what is attached and what it did | Done. `docs/SECURITY_AND_GOVERNANCE_EVIDENCE.md` |
| 1 | Reconcile three cost figures and separate HTTP success from correctness | The portal's success rate hides the two stalled runs | Done. `docs/OPERATIONS_MONITORING_AND_COST.md` |
| 2 | Deterministic evaluation package over the three genuine runs, with Foundry shaped datasets | Reusable, repeatable, and honest about what has not been executed | Done locally. `evaluation/` |
| 2 | Policy catalog with provenance and change impact | Traces each customer facing claim to a policy version | Done locally. `evaluation/policy/` |
| 2 | Agent Framework parity proof | The hosted workflow feature retires on 2026-12-01 | Done locally. `migration/agent_framework/`, 11 of 11 |
| 2 | Typed integration contracts with synthetic adapters | Shows where real systems plug in, and proves an agent cannot authorize money | Done locally. `integration/`, 138 checks |
| 3 | Runtime evidence view with four content labels | Lets a reviewer see real runs apart from offline material | Done. Control Center |
| 3 | Designs for routines, skills, tools and memory | Shows the intended use without enabling anything that bills | Done as a design page |

## Inspected and deliberately left alone

Routines, toolboxes, skills, knowledge indexes, memory stores, dataset uploads,
Foundry evaluations, red teaming, fine-tuning, custom guardrail policies, and
every change to the resource's security settings. The reason is the same each
time: either it bills, or I could not confirm that it does not, or it would alter
the system that passed the final run.
