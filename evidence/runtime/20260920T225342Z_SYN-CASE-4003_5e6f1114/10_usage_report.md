# Run report: SYN-CASE-4003

| Field | Value |
| --- | --- |
| Response id | `wfresp_049a4b2251233a8300PK4o7lIPmt8U8jvE3dwoDHX9mVtPADV4` |
| Conversation id | `conv_049a4b2251233a8300yVVW5AOffHtSE2LXhxPRthhXbCyqMsab` |
| Final status | **completed** |
| Stream events | 1182 |
| Stream interrupted | no |
| Elapsed | 71.6s |
| Route observed | **ESCALATED_TO_HUMAN** |
| Gate evaluated | observed |
| Audit ran | observed |
| Agents observed | CaseTriageAgent, AccountEvidenceAgent, UsageAnomalyAgent, PolicyKnowledgeAgent, ResolutionPlannerAgent, CustomerCommunicationAgent, EvidenceComplianceAgent, EscalationCoordinatorAgent, CaseAuditAgent |
| Compliance token | ESCALATE |
| Release step | NOT_RELEASED |
| Customer-ready message | no |
| Case follow-up, planner token | HUMAN_REQUIRED |
| Case follow-up, observed | HANDED_TO_HUMAN |
| Audit record accurate | NO, see notes |

## Agents the platform invoked

From `created_by.agent` on each conversation item, not from any agent's own account of the run.

| # | Agent | Version | Output chars |
| --- | --- | --- | --- |
| 1 | CaseTriageAgent | 5 | 2866 |
| 2 | AccountEvidenceAgent | 8 | 312 |
| 3 | UsageAnomalyAgent | 4 | 7031 |
| 4 | PolicyKnowledgeAgent | 5 | 256 |
| 5 | ResolutionPlannerAgent | 6 | 8025 |
| 6 | CustomerCommunicationAgent | 5 | 3591 |
| 7 | EvidenceComplianceAgent | 5 | 36 |
| 8 | EscalationCoordinatorAgent | 5 | 8091 |
| 9 | CaseAuditAgent | 6 | 4000 |

## Token usage and cost

| Measure | Value |
| --- | --- |
| Input tokens | 45452 |
| Cached input tokens | 0 |
| Output tokens | 8894 |
| Total tokens | 54346 |
| **Cost** | **$0.0292** |
| Approved cap | $1.00 |
| Within cap | yes |

Prices: gpt-5-mini GlobalStandard, USD per 1M tokens: input 0.25, cached input 0.025, output 2.00. Verified against the Azure Retail Prices API on 2026-09-18. A re-check on 2026-09-20 returned no rows, so this figure is carried forward from that verification and is not a live quote.

Whether this usage block covers all nine inner agent calls or only part of the run is not documented. Reconcile it against Azure Cost Management before treating it as the full cost.

## Notes

- AccountEvidenceAgent did not return its required output: NO_JSON_OBJECT.
- PolicyKnowledgeAgent did not return its required output: NO_JSON_OBJECT.
- EvidenceComplianceAgent did not return its required output: NO_JSON_OBJECT.
- Audit record: EscalationCoordinatorAgent is recorded as NOT_INVOKED, but the platform ran version 5.
- Audit record: CaseAuditAgent is recorded as version 'GRIDRESOLVE-AGENTS-3.0', the platform ran version 6.
