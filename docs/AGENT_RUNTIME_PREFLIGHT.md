# Agent Runtime Preflight

Method: Foundry project agents API, GET (read-only) on 2026-09-18, then one corrective write (below). Evidence: evidence/pre-run/PRE04a and PRE04b.

## Finding and correction
BEFORE: all nine agents had `tools: [{"type":"web_search"}]` in their latest definition. This was an actual runtime binding, not only a visible UI control. Web search can bill per call.
ACTION: created a new version of each agent with `tools: []`. Model, reasoning (effort low), and instructions are byte-identical. Old versions still exist (reversible). Nothing deleted. No shared resource touched. Workflow definition unchanged (still v4).
AFTER: verified by re-listing: all nine have no tools.
Note: instructions still say "No external tools are allowed in the hackathon configuration", which is now true.

## Table
| Agent | Version (was) | Version (now) | Model | External Tools | Paid Tool Risk | Safe for Demo | Notes |
|---|---|---|---|---|---|---|---|
| CaseTriageAgent | 3 | 4 | gpt-5-mini | NONE | None | Yes | reasoning effort low |
| AccountEvidenceAgent | 4 | 5 | gpt-5-mini | NONE | None | Yes | |
| UsageAnomalyAgent | 2 | 3 | gpt-5-mini | NONE | None | Yes | |
| PolicyKnowledgeAgent | 3 | 4 | gpt-5-mini | NONE | None | Yes | policy text embedded in instructions, no knowledge store |
| ResolutionPlannerAgent | 3 | 4 | gpt-5-mini | NONE | None | Yes | |
| CustomerCommunicationAgent | 2 | 3 | gpt-5-mini | NONE | None | Yes | |
| EvidenceComplianceAgent | 3 | 4 | gpt-5-mini | NONE | None | Yes | see branch-condition risk in WORKFLOW_V4_RUNTIME_MAP |
| EscalationCoordinatorAgent | 2 | 3 | gpt-5-mini | NONE | None | Yes | |
| CaseAuditAgent | 2 | 3 | gpt-5-mini | NONE | None | Yes | |

## Other capability status (from definitions: only keys kind, model, instructions, reasoning, tools exist)
Knowledge / Foundry IQ / Azure AI Search / MCP / Bing / code execution / external actions: none present in any agent definition. Not provisioned per dossier.

## Submission wording
Versions in the dossier (v3, v4, v2...) describe the configured build. The runtime-proven build is the tool-free versions above. Use the "now" versions in all submission material.
