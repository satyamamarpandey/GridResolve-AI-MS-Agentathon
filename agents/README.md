# Agent definitions, captured copies

Captured 2026-09-23 with a read-only GET on the Foundry project's control plane
(the same call `tests/verify_live_config.py` makes). Nothing here is the source
of truth: the hosted project is. These files exist so that a reviewer can read
what each agent was told without an Azure login, and so that a proposed new
version can be diffed against the live one before anything is published.

What is deliberately left out: the platform's identity fields (principal ids,
client ids, agent guids, blueprint references). They are infrastructure
identifiers and do not belong in a public repository. Nothing in the
instruction text names a resource, subscription or endpoint.

| Agent | Live version | Schema attached | File |
| --- | --- | --- | --- |
| CaseTriageAgent | 5 | no | `CaseTriageAgent.v5.md` |
| AccountEvidenceAgent | 9 | yes | `AccountEvidenceAgent.v9.md` |
| UsageAnomalyAgent | 4 | no | `UsageAnomalyAgent.v4.md` |
| PolicyKnowledgeAgent | 6 | yes | `PolicyKnowledgeAgent.v6.md` |
| ResolutionPlannerAgent | 6 | no | `ResolutionPlannerAgent.v6.md` |
| CustomerCommunicationAgent | 5 | yes | `CustomerCommunicationAgent.v5.md` |
| EvidenceComplianceAgent | 6 | no | `EvidenceComplianceAgent.v6.md` |
| EscalationCoordinatorAgent | 5 | no | `EscalationCoordinatorAgent.v5.md` |
| CaseAuditAgent | 7 | yes | `CaseAuditAgent.v7.md` |

Proposed, not published:

| Agent | Proposed version | File | What changes |
| --- | --- | --- | --- |
| EvidenceComplianceAgent | 7 | `EvidenceComplianceAgent.v7.md` | four route tokens, mandatory reason codes, reason codes never route |

These are the versions the final genuine run of 2026-09-20 used (workflow v10).
The model on every agent is gpt-5-mini with reasoning effort low and no tools.
Re-capture with the read-only script before trusting this table again; a
republish changes it.

Publishing a new version: `python scripts/publish_agent_version.py --agent
EvidenceComplianceAgent --file agents/EvidenceComplianceAgent.v7.md` prints the
exact request and sends nothing. Sending needs `--confirm PUBLISH` and the
operator's explicit go-ahead, because it changes the live project.
