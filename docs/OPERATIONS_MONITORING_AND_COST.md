# Operations, monitoring and cost

Written 2026-09-21. Everything here was read back from Azure with GET requests and
read-only log queries. I called no model, ran no workflow and created no resource
to produce it. The reads are reproducible with
`python scripts/export_platform_telemetry.py`, and the redacted result is in
`evidence/platform_telemetry/platform_telemetry_summary.json`.

## 1. A correction first

Until today my documents said that no Application Insights resource existed and
that no trace of the real runs was kept. That was wrong, and I had not checked.

An Application Insights resource and its Log Analytics workspace were created
together with the Foundry project on 2026-09-17, and the project has a default
connection to it. Foundry has been writing its own spans there on every run. I
found this on 2026-09-21 while taking an inventory of the resource group. I have
corrected the Control Center and the documents that repeated the claim.

I did not create, enable or change any of it.

## 2. Three cost figures, kept separate

| Figure | Value | Source | Status |
| --- | --- | --- | --- |
| Runner calculated | $0.1311 for 186,614 input and 42,155 output tokens | Usage fields of the three workflow responses, reconciled against every inner agent response, priced at the gpt-5-mini Global Standard rates configured in the runner ($0.25 in, $2.00 out per million, 0 cached tokens reported) | Provisional. It is arithmetic on platform token counts, not a bill |
| Foundry portal estimate | About $0.16 and 152.1K tokens | The portal's monitoring page, from a screenshot I took | An estimate by the portal. I do not know its time range or its price table |
| Azure Cost Management billed | Nothing visible yet | One query over the resource group, 2026-09-17 to 2026-09-21, returned 0 rows | Not yet visible. Microsoft documents a delay of 8 to 24 hours, and up to 72 hours on pay-as-you-go subscriptions. This is not the same as $0.00 |

### What I can explain

The token counts are settled. Azure Monitor's platform metrics for the resource,
which are the meter closest to billing that I can read, agree with my runner to
the token:

| Hour (UTC) | Run | Input tokens | Output tokens | Model requests |
| --- | --- | --- | --- | --- |
| 2026-09-20 20:00 | 1, workflow v6 | 46,810 | 10,828 | 8 |
| 2026-09-20 22:00 | 2, workflow v9 | 45,452 | 8,894 | 9 |
| 2026-09-21 00:00 | 3, workflow v10 | 94,352 | 22,433 | 9 |
| Total | | 186,614 | 42,155 | 26 |

The spans in Application Insights give the same three totals per run. So three
independent sources agree: the response usage fields my runner saved, Azure
Monitor metrics, and the platform's own traces.

The same metrics show 26 model requests in the whole life of the resource. All 26
belong to the three approved runs. No other model call has ever been made on this
resource, including during today's work.

### What I cannot explain

The portal's 152.1K tokens is lower than the 228,769 that Azure Monitor reports,
and its $0.16 is higher than my $0.1311. I do not know why. Possible causes are
the time range selected when I took the screenshot, a delay in the portal's own
aggregation, or a price table that differs from the one in my runner. I have not
been able to test any of these, so I report the portal figure as it appeared and
draw nothing from it.

The only figure that will settle the cost is the bill. Until Cost Management
shows it, the cost of the three runs is about $0.13 provisional.

## 3. What the platform recorded

| Item | Value |
| --- | --- |
| Workflow request spans | 3, one per run, named `execute_workflow GridResolveAIWorkflow`. These sit in the requests table, on top of the 61 dependency spans below |
| Agent spans (`invoke_agent`) | 26, carrying agent name and version |
| Model spans (`chat gpt-5-mini`) | 26, carrying input, output and cached token counts, all with finish reason `stop` |
| Other workflow spans | 9 (`workflow.build`, `workflow.session`, `workflow_invoke`) |
| Exceptions | 0 |
| Failed spans | 0 |
| Data ingested | About 2.5 MB in total, about 0.8 MB per run |
| Message content | Recorded. 52 of 61 spans carry input or output messages |

The agent versions on the spans match what I published before each run. Run 3
shows AccountEvidenceAgent 9, PolicyKnowledgeAgent 6, EvidenceComplianceAgent 6
and CaseAuditAgent 7, which is the v10 line up.

## 4. HTTP success is not semantic correctness

This is the most useful thing the traces taught me.

The platform marked every one of the 61 spans as successful. All three workflow
requests returned 200. The portal shows a 100 percent success rate. By those
measures nothing has ever gone wrong.

Runs 1 and 2 were not correct. My offline analysis of the saved evidence found
agents that returned a sentence about what they were going to do, and no JSON:

| Run | Agent | Platform span | Duration | What it actually returned |
| --- | --- | --- | --- | --- |
| 1 | AccountEvidenceAgent 7 | success | 1.3 s | 363 characters, no evidence ledger |
| 2 | AccountEvidenceAgent 8 | success | 1.2 s | 312 characters, no evidence ledger |
| 2 | PolicyKnowledgeAgent 5 | success | 0.9 s | 256 characters, no policy ledger |
| 2 | EvidenceComplianceAgent 5 | success | 0.6 s | The escalate token alone, 36 characters, no reasons |

In the final run the same three agents took 30.7 s, 24.9 s and 6.4 s and produced
complete output. The stalls are visible in the traces as implausibly short spans,
but only if you already know what a healthy span looks like. Nothing in the
platform's success signal separates the two.

That is why the runner carries its own health checks (JSON present, required
fields present, no announcement of future work, reasons given), and why the v10
gate has a third term that refuses to release when the investigation did not
complete. A production deployment needs an alert on the semantic signal, for
example agent span duration under two seconds or output under 500 characters, not
on HTTP status.

## 5. Throttling and failure signals

| Signal | Value | Reading |
| --- | --- | --- |
| Deployment rate limit | 50 requests and 50,000 tokens per minute | The final run used 116,785 tokens over about three minutes across nine sequential calls. It did not hit the limit, but a second concurrent case would |
| `BlockedCalls` metric | 6 in total, none in a run hour | Calls the resource rejected for rate or quota on 2026-09-19 and 2026-09-21. None was a model request, because the model request count did not move in those hours. I have not identified which API calls they were. I do not retry throttled calls in a loop |
| Model call failures | 0 of 26 | From the spans |
| Content filter blocks | 0 of 26 | From the spans, see `docs/SECURITY_AND_GOVERNANCE_EVIDENCE.md` |
| Cached tokens | 0 | Each agent's prompt differs, so prompt caching did nothing |

## 6. What is not in place

- No alert rule on anything. An action group exists in the resource group, and
  nothing is wired to it by me.
- No dashboard or workbook.
- No diagnostic settings on the Foundry resource, so no resource logs are kept.
- No budget or cost alert that I have verified. The runner's `--max-usd` is a
  guard in my code, not an Azure limit.
- Message content recording is on. With synthetic data that is harmless. With
  real customer data it would put bill amounts, addresses and complaint text into
  a Log Analytics workspace with 30 day retention and its own access rules. It
  has to be a deliberate decision, and the default should be off.
- The workspace is on the pay-as-you-go tier with no daily cap. At 0.8 MB per run
  the volume is trivial, but I have not confirmed from a bill that it costs
  nothing, so I do not claim that.

## 7. What I would run in production

| Need | Signal | Source |
| --- | --- | --- |
| Agent stalled | Agent span under 2 s, or output with no JSON object | Spans, plus the runner's health checks |
| Wrong route | Release without a complete evidence ledger, or audit findings above zero | Runner analysis, already implemented |
| Cost drift | Tokens per case against the 116,785 baseline | `InputTokens` and `OutputTokens` metrics, free to read |
| Throttling | Any 429 on the model deployment | `AzureOpenAIRequests` by status code |
| Safety | Any content filter block or jailbreak detection | Span attribute `microsoft.foundry.content_filter.results` |
| Spend | A budget on the resource group with an alert at a fixed amount | Azure Cost Management |
