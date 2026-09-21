# Evidence Capture Checklist (SYN-CASE-4003 run)

Before run
- [ ] Screenshot Azure Cost Management, current month, showing cost state (before)
- [ ] Screenshot each agent Tools section showing no Web search/Bing/MCP (or record which are on)
- [ ] Screenshot workflow GridResolveAIWorkflow v4 canvas with version visible
- [ ] Screenshot model deployment gpt-5-mini (Global Standard, 50K TPM)
- [ ] Note start timestamp (UTC)

During run
- [ ] Paste exact input from submission/SYN-CASE-4003_input.json, no edits
- [ ] Run once only. No retries, no re-runs unless the user approves.

After run
- [ ] Screenshot per-agent outputs: Triage (meter concern), AccountEvidence, UsageAnomaly, PolicyKnowledge, Planner, Communication, EvidenceCompliance decision, Escalation (if routed), CaseAudit record
- [ ] Screenshot trace with span timeline (if tracing available; else record that it was not)
- [ ] Record input tokens, output tokens, total, per agent and total
- [ ] Record end-to-end latency
- [ ] Compute cost = in x 0.25/1M + out x 2.00/1M; compare with the $0.50 cap
- [ ] Save final customer-facing message and confirm it does not assert a meter defect
- [ ] Screenshot Cost Management after (may lag; note the time)
- [ ] Save all files under evidence/ and update STATE and SUBMISSION_STATUS
- [ ] State clearly: sequential execution, no parallel, no correction loop unless it actually ran
