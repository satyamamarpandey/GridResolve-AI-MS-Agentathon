# Run report: SYN-CASE-4003

| Field | Value |
| --- | --- |
| Response id | `wfresp_0e74508741ea3ef600XeSZg2eU2GjWnR72Jnm7T4D2IsyPdhBc` |
| Conversation id | `conv_0e74508741ea3ef600PlzhMldsZyRTEpd4WbkdIpTHH5Yui6bL` |
| Final status | **completed** |
| Stream events | 1303 |
| Stream interrupted | no |
| Elapsed | 85.6s |
| Route observed | **APPROVED_AND_RELEASED** |
| Gate evaluated | not observed |
| Audit ran | observed |
| Agents observed | CaseTriageAgent, CaseTriageAgent, AccountEvidenceAgent, AccountEvidenceAgent, UsageAnomalyAgent, UsageAnomalyAgent, PolicyKnowledgeAgent, PolicyKnowledgeAgent, ResolutionPlannerAgent, ResolutionPlannerAgent, CustomerCommunicationAgent, CustomerCommunicationAgent, EvidenceComplianceAgent, EvidenceComplianceAgent, CaseAuditAgent, CaseAuditAgent |

## Token usage and cost

| Measure | Value |
| --- | --- |
| Input tokens | 46810 |
| Cached input tokens | 0 |
| Output tokens | 10828 |
| Total tokens | 57638 |
| **Cost** | **$0.0334** |
| Approved cap | $1.00 |
| Within cap | yes |

Prices: gpt-5-mini GlobalStandard, USD per 1M tokens: input 0.25, cached input 0.025, output 2.00. Verified against the Azure Retail Prices API on 2026-09-18. A re-check on 2026-09-20 returned no rows, so this figure is carried forward from that verification and is not a live quote.

Whether this usage block covers all nine inner agent calls or only part of the run is not documented. Reconcile it against Azure Cost Management before treating it as the full cost.
