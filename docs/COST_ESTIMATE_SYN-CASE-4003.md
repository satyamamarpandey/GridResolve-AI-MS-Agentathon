# Cost Estimate: one SYN-CASE-4003 run (revised)

No model call made to produce this.

## Price (VERIFIED, Azure Retail Prices API, 2026-09-18), GPT-5-mini Global Standard
Input 0.25, cached input 0.025, output 2.00 USD per 1M tokens. Reasoning tokens bill as output.
Formula: cost = in/1e6*0.25 + out/1e6*2.00 (+ cached_in/1e6*0.025, not assumed).

## Structure driving tokens
All agents share one conversation, so each agent re-reads every earlier agent's output. Input grows roughly quadratically along the 9-step chain. Agent instructions are 2.7k to 4.6k characters, about 0.7k to 1.2k tokens. Reasoning effort is low on every agent.

## Assumptions (NOT measured)
| Scenario | Visible output/agent | Reasoning/agent | Input total | Output total | Cost |
|---|---|---|---|---|---|
| Expected | 2.5k | 1k | about 105k | about 32k | 0.026 + 0.064 = **$0.09** |
| Conservative | 5k | 3k | about 250k | about 100k | 0.0625 + 0.20 = **$0.26** |
| Earlier flat-model max | | | 180k | 144k | $0.33 |

Operational maximum budget: **$0.50** (a budget target that I monitor, NOT a platform-enforced billing cap; no Foundry hard cap was found or configured).

## Tool cost
Web search was bound to all nine agents. Removed (see AGENT_RUNTIME_PREFLIGHT.md). No other tool exists. Tool-call cost now $0.

## Token limits
No per-agent or per-run output cap found in agent definitions (only kind, model, instructions, reasoning, tools) or in the workflow YAML. Not changed. Reasoning effort is already low.

## Risks to the estimate
- 50K TPM deployment limit: a run with 250k input tokens spread over minutes may hit 429 throttling. Throttled calls are not billed but may fail the run partway. Do not auto-retry.
- Tracing: no Application Insights, so traces may not persist. Token counts may come from the response usage fields instead.
- Unknown token counts until run. Real numbers will replace these.
