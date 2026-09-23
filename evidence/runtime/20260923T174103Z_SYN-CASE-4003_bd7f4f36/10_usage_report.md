# Run report: SYN-CASE-4003

| Field | Value |
| --- | --- |
| Response id | `wfresp_0d852a8a379bedfd00mBDl0ALOUUYqegbuZwiJ6bTJvWcZSOu4` |
| Conversation id | `conv_0d852a8a379bedfd007BExiBDnqfSHrmgnUSA9WxrggrtpTeIt` |
| Final status | **completed** |
| Stream events | 1945 |
| Stream interrupted | no |
| Elapsed | 165.2s |
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
| 1 | CaseTriageAgent | 5 | 2869 |
| 2 | AccountEvidenceAgent | 9 | 11079 |
| 3 | UsageAnomalyAgent | 4 | 6209 |
| 4 | PolicyKnowledgeAgent | 6 | 11213 |
| 5 | ResolutionPlannerAgent | 6 | 10657 |
| 6 | CustomerCommunicationAgent | 5 | 4220 |
| 7 | EvidenceComplianceAgent | 7 | 1483 |
| 8 | EscalationCoordinatorAgent | 5 | 10106 |
| 9 | CaseAuditAgent | 7 | 4058 |

## Token usage and cost

| Measure | Value |
| --- | --- |
| Input tokens | 85470 |
| Cached input tokens | 0 |
| Output tokens | 19257 |
| Total tokens | 104727 |
| **Cost** | **$0.0599** |
| Approved cap | $0.70 |
| Within cap | yes |

Prices: gpt-5-mini GlobalStandard, USD per 1M tokens: input 0.25, cached input 0.025, output 2.00. Verified against the Azure Retail Prices API on 2026-09-18. A re-check on 2026-09-20 returned no rows, so this figure is carried forward from that verification and is not a live quote.

Whether this usage block covers all nine inner agent calls or only part of the run is not documented. Reconcile it against Azure Cost Management before treating it as the full cost.
