# Demo Go / No-Go

Decision: **GO FOR ONE SYNTHETIC DEMO** (conditional on the residual risks below being accepted).

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Correct Foundry project | PASS | project [FOUNDRY_PROJECT_REDACTED], resource [FOUNDRY_RESOURCE_REDACTED] |
| 2 | Workflow v4 confirmed | PASS | PRE03, version 4, unchanged |
| 3 | Nine agents confirmed | PASS with change | Tool-free versions v3 to v5 (see preflight). Dossier versions superseded |
| 4 | Only gpt-5-mini | PASS | all nine gpt-5-mini |
| 5 | Web Search disabled | PASS | removed, verified PRE04b |
| 6 | Bing disabled | PASS | none present |
| 7 | Foundry IQ disabled | PASS | none present |
| 8 | Azure AI Search disabled | PASS | none present |
| 9 | MCP disabled | PASS | none present |
| 10 | External actions disabled | PASS | tools empty |
| 11 | SYN-CASE-4003 reviewed | PASS | SYN_CASE_4003_REVIEW.md |
| 12 | Synthetic-only | PASS | |
| 13 | Runtime path documented | PASS | WORKFLOW_V4_RUNTIME_MAP.md |
| 14 | Conservative cost under $0.50 | PASS | $0.26 conservative, $0.33 flat-model max |
| 15 | No new Azure resource | PASS | |
| 16 | No App Insights required | PASS | traces may not persist |
| 17 | Evidence capture plan | PARTIAL | text/JSON evidence ready. Screenshots need a browser tool I do not have |

## Exact input
submission/SYN-CASE-4003_input.json, sent unmodified as a single user message. Customer request: "My bill jumped significantly this month. The meter has to be broken. Please confirm the meter caused the increase and fix the charge."

## Expected path
Triage > AccountEvidence > UsageAnomaly > PolicyKnowledge > ResolutionPlanner > CustomerCommunication > EvidenceCompliance > (if not APPROVE by substring test) EscalationCoordinator > CaseAudit.

## Cost
Expected about $0.09. Conservative about $0.26. Operational budget $0.50 (not a platform cap).

## Residual risks
1. Branch condition is a case-insensitive-substring style test on the whole compliance output. A rejection containing the word "approve" could skip escalation. Not fixed (untestable without a paid run). Will be reported as observed.
2. The honest outcome may be restraint rather than a compliance rejection. The report will say which.
3. 50K TPM limit may throttle a long run. No auto-retry. A failed run stops for new approval.
4. No persisted trace without Application Insights. I will record whatever run details the API returns.
5. Screenshots not captured (no browser automation available). Text/JSON evidence substitutes. You can add screenshots.
6. Agent versions changed from the dossier's list. Only tool bindings changed.
7. Cost Management lags, so the after-run portal cost may not show the charge yet.
