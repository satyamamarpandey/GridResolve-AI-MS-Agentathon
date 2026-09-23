# Run report: SYN-CASE-4001

| Field | Value |
| --- | --- |
| Response id | `wfresp_06041dbd077c1f2300A9MDz685W57NRsabE2skOMsP7NeIGVhC` |
| Conversation id | `conv_06041dbd077c1f23008p67M18B96aWDhoZmgFKO001nrET7d9s` |
| Final status | **completed** |
| Stream events | 1894 |
| Stream interrupted | no |
| Elapsed | 168.9s |
| Route observed | **APPROVED_AND_RELEASED** |
| Gate evaluated | observed |
| Audit ran | observed |
| Agents observed | CaseTriageAgent, AccountEvidenceAgent, UsageAnomalyAgent, PolicyKnowledgeAgent, ResolutionPlannerAgent, CustomerCommunicationAgent, EvidenceComplianceAgent, CaseAuditAgent |
| Compliance token | APPROVED |
| Release step | DELIVERED_CUSTOMER_MESSAGE |
| Customer-ready message | yes |
| Case follow-up, planner token | NONE_REQUIRED |
| Case follow-up, observed | NONE_REQUIRED |
| Audit record accurate | yes |

## Agents the platform invoked

From `created_by.agent` on each conversation item, not from any agent's own account of the run.

| # | Agent | Version | Output chars |
| --- | --- | --- | --- |
| 1 | CaseTriageAgent | 5 | 2859 |
| 2 | AccountEvidenceAgent | 9 | 11973 |
| 3 | UsageAnomalyAgent | 4 | 9734 |
| 4 | PolicyKnowledgeAgent | 6 | 14573 |
| 5 | ResolutionPlannerAgent | 6 | 9958 |
| 6 | CustomerCommunicationAgent | 5 | 3208 |
| 7 | EvidenceComplianceAgent | 7 | 1463 |
| 8 | CaseAuditAgent | 7 | 3868 |

## Token usage and cost

| Measure | Value |
| --- | --- |
| Input tokens | 77952 |
| Cached input tokens | 0 |
| Output tokens | 18795 |
| Total tokens | 96747 |
| **Cost** | **$0.0571** |
| Approved cap | $0.70 |
| Within cap | yes |

Prices: gpt-5-mini GlobalStandard, USD per 1M tokens: input 0.25, cached input 0.025, output 2.00. Verified against the Azure Retail Prices API on 2026-09-18. A re-check on 2026-09-20 returned no rows, so this figure is carried forward from that verification and is not a live quote.

Whether this usage block covers all nine inner agent calls or only part of the run is not documented. Reconcile it against Azure Cost Management before treating it as the full cost.
