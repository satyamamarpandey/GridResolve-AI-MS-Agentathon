# Cost Guard

## Status, 2026-09-20

Three workflow executions were each approved separately by the owner, with a named dollar cap, and each ran once with no retry. Every approval is spent. The implementation is frozen and **no further billable action is authorized**.

| Run | Workflow | Cap approved | Provisional cost from tokens |
|---|---|---|---|
| 1 | v6 | owner-approved single run | $0.0334 |
| 2 | v9 | $1.00 | $0.0292 |
| 3, final | v10 | $1.00 | $0.0685 |
| Total | | | about $0.13 |

Billed amount: not yet visible in Azure Cost Management, which returned zero rows after the final run. That is not a confirmed $0.00. Billing lags. The runner's `--max-usd` is a runner-level safeguard, not an Azure-enforced cap. Zero embeddings, zero evaluation runs, zero new resources.

## Rule

No billable action without the owner's explicit approval naming a dollar amount. The phrase `APPROVE ONE SYNTHETIC DEMO RUN` is only the runner's confirmation string and is not spending approval by itself. If uncertain, stop that action and record PREPARED_NOT_EXECUTED_DUE_TO_ZERO_COST_CONSTRAINT.

## Prohibited without explicit approval
- Run any agent, send any model request or playground message
- Workflow preview or validation that invokes a model
- Evaluation runs, LLM-as-judge, Agent Optimizer
- Foundry IQ, Azure AI Search, Bing or web grounding, MCP runtime calls to external services
- New model deployment, hosted endpoint, Teams or M365 Copilot deployment
- Application Insights, database, storage, Function App, Logic Apps
- API Management, AI Gateway
- Any new paid Azure resource or operation with uncertain cost

## Allowed (read-only, free)
- az account show, az cognitiveservices ... list/show
- Public Azure Retail Prices API
- Local file work, portal viewing without running anything

## AI Gateway
Not created. Create only if current docs and the subscription prove zero base cost, no recurring API Management charge, no paid dependencies.

## Data
Synthetic only. No real customer data, credentials, tokens, or Exelon confidential material in local files.
