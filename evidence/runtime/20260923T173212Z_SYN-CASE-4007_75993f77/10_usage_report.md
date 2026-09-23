# Run report: SYN-CASE-4007

| Field | Value |
| --- | --- |
| Response id | `wfresp_0bda0dede922bc5000xmkgV6pvee4lQXMmGLWgCp5i4RLP9kSd` |
| Conversation id | `conv_0bda0dede922bc50007HYs5jAVrSw1GTFyjD7m2zqElzV2nmUY` |
| Final status | **completed** |
| Stream events | 2381 |
| Stream interrupted | no |
| Elapsed | 220.1s |
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
| 1 | CaseTriageAgent | 5 | 2943 |
| 2 | AccountEvidenceAgent | 9 | 12977 |
| 3 | UsageAnomalyAgent | 4 | 11490 |
| 4 | PolicyKnowledgeAgent | 6 | 14570 |
| 5 | ResolutionPlannerAgent | 6 | 12663 |
| 6 | CustomerCommunicationAgent | 5 | 4950 |
| 7 | EvidenceComplianceAgent | 7 | 1967 |
| 8 | EscalationCoordinatorAgent | 5 | 12212 |
| 9 | CaseAuditAgent | 7 | 4356 |

## Token usage and cost

| Measure | Value |
| --- | --- |
| Input tokens | 106412 |
| Cached input tokens | 0 |
| Output tokens | 24493 |
| Total tokens | 130905 |
| **Cost** | **$0.0756** |
| Approved cap | $0.70 |
| Within cap | yes |

Prices: gpt-5-mini GlobalStandard, USD per 1M tokens: input 0.25, cached input 0.025, output 2.00. Verified against the Azure Retail Prices API on 2026-09-18. A re-check on 2026-09-20 returned no rows, so this figure is carried forward from that verification and is not a live quote.

Whether this usage block covers all nine inner agent calls or only part of the run is not documented. Reconcile it against Azure Cost Management before treating it as the full cost.
