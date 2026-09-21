# Active Workflow Version

Question: is workflow v5 merely saved, or is it the version that would actually execute?

**Answer: v5 is the executable version. No publish step is required, and none was performed.**

Verified read-only on 2026-09-19 via the Foundry control plane. Reproduce with `python tests/verify_live_config.py`.

## Evidence

```json
"state": "enabled",
"agent_endpoint": {
  "version_selector": {
    "version_selection_rules": [
      { "type": "FixedRatio", "agent_version": "@latest", "traffic_percentage": 100 }
    ]
  },
  "protocols": ["responses"],
  "authorization_schemes": [{ "type": "Entra" }],
  "publish_approval_status": "not_published"
}
```

The version selector routes **100 percent of traffic to `@latest`**. The latest workflow version is 5, status active, `draft: false`. Therefore an invocation resolves to v5.

Identical selector configuration exists on every one of the nine agents, so `agent: {name: CaseTriageAgent}` in the workflow YAML resolves to each agent's latest version. Those are the corrected, tool-free versions.

## What `publish_approval_status: not_published` means

It refers to publishing the agent endpoint for external consumption, for example to a channel or an approved shared catalog. It does **not** gate execution from the Foundry portal or the project API. No publish action was taken, because none is needed and its cost behavior was not verified.

## Current executable configuration

| Component | Version | Notes |
|---|---|---|
| GridResolveAIWorkflow | **5** | v1 to v4 retained, all status active, selectable for rollback |
| CaseTriageAgent | 5 | |
| AccountEvidenceAgent | 6 | |
| UsageAnomalyAgent | 4 | |
| PolicyKnowledgeAgent | 5 | |
| ResolutionPlannerAgent | 5 | |
| CustomerCommunicationAgent | 4 | |
| EvidenceComplianceAgent | 5 | emits the route token |
| EscalationCoordinatorAgent | 4 | |
| CaseAuditAgent | 4 | execution_status supports RUNTIME_EXECUTED |

All nine: model `gpt-5-mini`, reasoning effort low, **zero tools**.

## Entry point and routing, as stored

- Trigger: `OnConversationStart`
- Seven nodes carry `autoSend: false`, so investigation output and the customer draft are withheld
- Approve branch: `=("ROUTE_DECISION::GRIDRESOLVE_APPROVED" in Local.Var1497)` then `SendActivity activity: =Local.VarCustomerDraft`
- Default branch `"true"`: `EscalationCoordinatorAgent`, `autoSend: true`
- `CaseAuditAgent` terminal on both paths, `autoSend: true`
- The v4 condition `Not("APPROVE" in ...)` is absent

## Operational note worth knowing

Because the selector is pinned to `@latest` rather than to explicit versions, any future edit to an agent or the workflow becomes live immediately. For a controlled demonstration that is acceptable, since nothing will be edited between now and the run. For production, pinning explicit versions and promoting deliberately would be safer. Not changed here, because changing the selector is a configuration alteration with no current need.

## Limit of this verification

This confirms which definition would execute. It does not confirm how the platform evaluates the routing expression at runtime, because v5 has never run.
