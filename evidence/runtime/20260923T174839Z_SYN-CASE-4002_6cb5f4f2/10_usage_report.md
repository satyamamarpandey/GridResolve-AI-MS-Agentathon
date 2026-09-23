# Run report: SYN-CASE-4002

| Field | Value |
| --- | --- |
| Response id | `wfresp_058c236aa08383fd00qjhUPU1jbp5kBavVA2w819WBKl39FUZ0` |
| Conversation id | `conv_058c236aa08383fd0087geOEdZEI2twCyBexO1wRldNv2ZTprI` |
| Final status | **completed** |
| Stream events | 2191 |
| Stream interrupted | no |
| Elapsed | 188.2s |
| Route observed | **APPROVED_AND_RELEASED** |
| Gate evaluated | observed |
| Audit ran | observed |
| Agents observed | CaseTriageAgent, AccountEvidenceAgent, UsageAnomalyAgent, PolicyKnowledgeAgent, ResolutionPlannerAgent, CustomerCommunicationAgent, EvidenceComplianceAgent, EscalationCoordinatorAgent, CaseAuditAgent |
| Compliance token | APPROVED |
| Release step | DELIVERED_CUSTOMER_MESSAGE |
| Customer-ready message | yes |
| Case follow-up, planner token | HUMAN_REQUIRED |
| Case follow-up, observed | HANDED_TO_HUMAN |
| Audit record accurate | yes |

## Agents the platform invoked

From `created_by.agent` on each conversation item, not from any agent's own account of the run.

| # | Agent | Version | Output chars |
| --- | --- | --- | --- |
| 1 | CaseTriageAgent | 5 | 2730 |
| 2 | AccountEvidenceAgent | 9 | 9837 |
| 3 | UsageAnomalyAgent | 4 | 9167 |
| 4 | PolicyKnowledgeAgent | 6 | 17078 |
| 5 | ResolutionPlannerAgent | 6 | 11234 |
| 6 | CustomerCommunicationAgent | 5 | 3651 |
| 7 | EvidenceComplianceAgent | 7 | 2067 |
| 8 | EscalationCoordinatorAgent | 5 | 14263 |
| 9 | CaseAuditAgent | 7 | 4463 |

## Token usage and cost

| Measure | Value |
| --- | --- |
| Input tokens | 96656 |
| Cached input tokens | 7680 |
| Output tokens | 22560 |
| Total tokens | 119216 |
| **Cost** | **$0.0676** |
| Approved cap | $0.70 |
| Within cap | yes |

Prices: gpt-5-mini GlobalStandard, USD per 1M tokens: input 0.25, cached input 0.025, output 2.00. Verified against the Azure Retail Prices API on 2026-09-18. A re-check on 2026-09-20 returned no rows, so this figure is carried forward from that verification and is not a live quote.

Whether this usage block covers all nine inner agent calls or only part of the run is not documented. Reconcile it against Azure Cost Management before treating it as the full cost.
