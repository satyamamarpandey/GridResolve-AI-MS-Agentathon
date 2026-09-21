# Run report: SYN-CASE-4003

| Field | Value |
| --- | --- |
| Response id | `wfresp_0e23435a002841f300QNFbMTKNows9FL4BUVI6SdrJswCRe72z` |
| Conversation id | `conv_0e23435a002841f3000IxWQBy3HxuTxffL3jOU66srd2Quj1pX` |
| Final status | **completed** |
| Stream events | 2091 |
| Stream interrupted | no |
| Elapsed | 179.5s |
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
| 1 | CaseTriageAgent | 5 | 2534 |
| 2 | AccountEvidenceAgent | 9 | 12260 |
| 3 | UsageAnomalyAgent | 4 | 6973 |
| 4 | PolicyKnowledgeAgent | 6 | 15568 |
| 5 | ResolutionPlannerAgent | 6 | 10681 |
| 6 | CustomerCommunicationAgent | 5 | 4094 |
| 7 | EvidenceComplianceAgent | 6 | 1989 |
| 8 | EscalationCoordinatorAgent | 5 | 12787 |
| 9 | CaseAuditAgent | 7 | 3734 |

## Token usage and cost

| Measure | Value |
| --- | --- |
| Input tokens | 94352 |
| Cached input tokens | 0 |
| Output tokens | 22433 |
| Total tokens | 116785 |
| **Cost** | **$0.0685** |
| Approved cap | $1.00 |
| Within cap | yes |

Prices: gpt-5-mini GlobalStandard, USD per 1M tokens: input 0.25, cached input 0.025, output 2.00. Verified against the Azure Retail Prices API on 2026-09-18. A re-check on 2026-09-20 returned no rows, so this figure is carried forward from that verification and is not a live quote.

Whether this usage block covers all nine inner agent calls or only part of the run is not documented. Reconcile it against Azure Cost Management before treating it as the full cost.
