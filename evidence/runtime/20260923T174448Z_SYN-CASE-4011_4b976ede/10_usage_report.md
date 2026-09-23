# Run report: SYN-CASE-4011

| Field | Value |
| --- | --- |
| Response id | `wfresp_08cd0baf9ae7b56e000bAg2LpjahJuCppnHP9wM6VUVf0A0gav` |
| Conversation id | `conv_08cd0baf9ae7b56e00Xvo1YNsnYTYQM8rLKs7f2apzNj90emGr` |
| Final status | **completed** |
| Stream events | 2173 |
| Stream interrupted | no |
| Elapsed | 183.8s |
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
| 1 | CaseTriageAgent | 5 | 3186 |
| 2 | AccountEvidenceAgent | 9 | 13707 |
| 3 | UsageAnomalyAgent | 4 | 9049 |
| 4 | PolicyKnowledgeAgent | 6 | 15812 |
| 5 | ResolutionPlannerAgent | 6 | 10171 |
| 6 | CustomerCommunicationAgent | 5 | 3379 |
| 7 | EvidenceComplianceAgent | 7 | 2689 |
| 8 | EscalationCoordinatorAgent | 5 | 11668 |
| 9 | CaseAuditAgent | 7 | 4030 |

## Token usage and cost

| Measure | Value |
| --- | --- |
| Input tokens | 98712 |
| Cached input tokens | 4480 |
| Output tokens | 22073 |
| Total tokens | 120785 |
| **Cost** | **$0.0678** |
| Approved cap | $0.70 |
| Within cap | yes |

Prices: gpt-5-mini GlobalStandard, USD per 1M tokens: input 0.25, cached input 0.025, output 2.00. Verified against the Azure Retail Prices API on 2026-09-18. A re-check on 2026-09-20 returned no rows, so this figure is carried forward from that verification and is not a live quote.

Whether this usage block covers all nine inner agent calls or only part of the run is not documented. Reconcile it against Azure Cost Management before treating it as the full cost.
