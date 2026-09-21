# Security and governance evidence

Written 2026-09-21. This page separates what Microsoft Foundry enforces from what
my own code and workflow enforce, and it states the actual enforcement status of
each control, with the evidence. A policy that exists in the portal is not counted
as protection unless I can show it attached to the deployment and, where possible,
show it acting on a real call.

Everything in section 1 was read from Azure with GET requests and read-only log
queries on 2026-09-21. Nothing was changed. No policy was attached, replaced or
created.

Status words used here:

- **ENFORCED, OBSERVED**: active, and I have evidence of it acting on a real run.
- **ENFORCED, NOT EXERCISED**: active by configuration, never triggered, so its
  behaviour under attack is unproven.
- **LOCALLY TESTED**: enforced by my code and proven by local tests only.
- **SPECIFIED ONLY**: written down, not enforced anywhere.
- **NOT IN PLACE**: absent.

## 1. Platform controls, as actually configured

### Content filter on the model deployment

The `gpt-5-mini` deployment has `raiPolicyName` set to `Microsoft.DefaultV2`. That
is Microsoft's system managed default policy, in blocking mode. I read its
contents from the resource:

| Filter | Applies to | Enabled | Blocking | Threshold |
| --- | --- | --- | --- | --- |
| Hate, Sexual, Violence, Self harm | Prompt and completion | Yes | Yes | Medium |
| Jailbreak | Prompt | Yes | Yes | n/a |
| Protected material, text | Completion | Yes | Yes | n/a |
| Protected material, code | Completion | Yes | No, annotate only | n/a |

There are no custom blocklists and no custom policy. Indirect prompt attack
detection is not part of this policy.

Evidence that it ran: every one of the 26 agent spans the platform recorded for
the three real runs carries a `microsoft.foundry.content_filter.results`
attribute, with a verdict for the prompt and for the completion. All 26 show
`blocked: false`, every category `safe`, and `jailbreak.detected: false`. The
blocked and jailbreak flags for each span are in
`evidence/platform_telemetry/platform_telemetry_summary.json`.

What that does and does not show: the filter evaluated every real call. It was
never asked to block anything, because the synthetic case contains nothing
harmful and no injection attempt. I have no runtime evidence of how the system
behaves when the filter does block, and the workflow has no branch for a blocked
call. The red-team probes I wrote have never been run against the hosted agents.

### Identity and network

| Setting | Value read from Azure | What it means |
| --- | --- | --- |
| Authentication used by my runner | Entra ID token, audience `https://ai.azure.com` | No key is stored or used by my code |
| `disableLocalAuth` | false | API keys are still accepted by the resource. I do not use them, but they exist and would work if leaked |
| `publicNetworkAccess` | Enabled, default action Allow | The endpoint is reachable from the internet. No private endpoint, no IP rules |
| Role assignments at the resource | Owner for one user. Azure AI User for two users and one service principal | Least privilege is not tuned. I have not reviewed why the second user and the service principal hold the role |
| Managed identity | System assigned | Present, not used for anything yet |
| Customer managed key | None | Microsoft managed encryption at rest |
| Application Insights connection | API key authentication | The project's telemetry connection uses a key, not Entra ID |
| Diagnostic settings | None | No resource logs, so no audit trail of control plane changes beyond the Azure activity log |
| Model version upgrade | `OnceNewDefaultVersionAvailable` | The model under the validated agents can change without my action. A production system would pin it |

### Agent configuration

All nine agents have no tools attached. They cannot browse, search, run code, call
an API or write to anything. I confirmed this from the agent definitions with
`tests/verify_live_config.py` (94 checks, read only). The only thing an agent can
do is return text to the workflow.

## 2. Control matrix

| Control | Threat addressed | Implementation location | Actual enforcement status | Evidence | Test coverage | Remaining limitation |
| --- | --- | --- | --- | --- | --- | --- |
| Default content filter, `Microsoft.DefaultV2` | Harmful content in or out, direct jailbreak, protected text | Foundry, attached to the `gpt-5-mini` deployment | ENFORCED, NOT EXERCISED. It evaluated all 26 real calls and blocked none | Deployment `raiPolicyName`, policy contents, 26 span verdicts | None of mine. It is Microsoft's control | No indirect attack filter. No workflow branch for a blocked call. Never seen blocking |
| No tools on any agent | An agent taking an action, exfiltrating data, or being steered into a tool call | Foundry agent definitions | ENFORCED, OBSERVED. 26 spans, no tool call in any | `tests/verify_live_config.py`, conversation items of all three runs | 94 live read-only checks | Attaching a tool later removes this. It needs review each time |
| No financial action path | An agent issuing a credit or adjustment | Workflow has no such node. `integration/adjustments.py` requires a human supervisor principal | ENFORCED by absence in the hosted system. LOCALLY TESTED for the future port | v10 YAML. `integration/README.md` | `tests/test_integration_contracts.py`, 138 checks, including forged roles and self approval | The real billing system is not connected, so the control has never faced a real credential |
| Fail-closed release gate | Releasing a message that compliance did not approve, or that came from an incomplete investigation | Workflow v10, Power Fx `And(gate_v6, readable_v9, investigated_v10)` | ENFORCED, OBSERVED. True in the final run. The v9 form of the gate was false in run 2, which escalated | `09_route.json` in the run 2 and run 3 evidence folders | 105 Power Fx cases on Microsoft's interpreter, 91 engine checks | The third term has never been seen returning false in the hosted service |
| Deterministic release template | The model rewording the approved message after approval | Workflow `SendActivity`, mirrored by `compose_customer_message` | ENFORCED, OBSERVED. The 2,592 released characters equal the template applied to the approved draft | Final run `08_output.txt`, `migration/agent_framework/parity_result.json` | Runner tests, parity check | One case, one run |
| Evidence ledger with value matching | Invented figures in the customer message | AccountEvidenceAgent strict JSON schema, then runner cross-check against the case input | Schema ENFORCED by Foundry. Value match LOCALLY TESTED and applied to the real run after the fact | 22 ledger entries, all matched, in the final run analysis | 357 runner checks, 80 of 80 mutants killed | The value match runs after the run, in my runner. It does not gate the hosted release |
| Policy provenance | Citing a policy that does not exist or is out of date | `evaluation/` catalog and validator | LOCALLY TESTED | Catalog and validator output | `tests/test_evaluation_package.py` | Not connected to the hosted agents. It checks their output after the fact |
| Separate human follow-up gate | Closing a case that still needs a person | Workflow v10 follow-up gate on the planner token | ENFORCED, OBSERVED on the human branch | Final run route `HANDED_TO_HUMAN`, escalation package to a Billing Supervisor | Power Fx and engine tests for both branches | The no-follow-up branch has never run hosted. No real person is notified |
| Independent audit agent | A run that looks fine and is not | CaseAuditAgent, last node, plus runner health checks | ENFORCED, OBSERVED. Zero findings in the final run. In run 2 the audit agent recorded an approval that never happened. My runner missed that on the day, and the corrected runner now reports it | Run 3 analysis, `evidence/reanalysis/` for run 2 | Runner tests | The audit agent is a model. The runner's deterministic checks are the ones I trust |
| Spend guard | Runaway cost | `runner/`, `--max-usd`, duplicate run guard, run ledger | LOCALLY TESTED, and used on all three runs | `evidence/runtime/RUN_LEDGER.json` | Runner tests | It is my code, not an Azure limit. No Azure budget is verified |
| Synthetic data only | Exposure of customer data | `SYN-` identifier patterns, validators | LOCALLY TESTED, and true of every run | Case sha256 in each preflight file | 151 synthetic data checks, integration tests refuse non synthetic ids | With real data, the content recording noted below becomes a privacy issue |
| Entra ID authentication | Stolen keys | Runner uses `az` tokens only | ENFORCED in my code. NOT ENFORCED by the resource, which still accepts keys | Account setting `disableLocalAuth: false` | None | Set `disableLocalAuth` to true before production. I have not changed it |
| Network isolation | Access from untrusted networks | None | NOT IN PLACE | `publicNetworkAccess: Enabled` | None | Private endpoint and network rules are production work |
| Custom guardrail policy for billing claims | Unsupported promises such as refunds or fault admissions | Compliance agent instructions, and the local deterministic checks in `evaluation/` | SPECIFIED ONLY as a Foundry policy. The behaviour is enforced by the compliance agent and gate, not by a Foundry guardrail | Final run compliance decision with reasons | Evaluation package checks | No custom Foundry policy or blocklist exists. I do not claim one |
| Telemetry content recording | Sensitive text in logs | Application Insights connected to the project | ON. 52 of 61 spans hold message content | `platform_telemetry_summary.json` | None | Acceptable only for synthetic data. Must be decided before any real case |
| Secrets hygiene | Credentials in the repository or evidence | `.gitignore`, runner placeholders for resource and project names, export script refuses to write identifiers | LOCALLY TESTED | Leak scan in `docs/PUBLICATION_PLAN_2026-09-20.md` | Scan repeated before publication | Unredacted portal captures stay outside git |

## 3. What I do not claim

- I do not claim that a custom Foundry guardrail protects this system. Only the
  Microsoft default policy is attached.
- I do not claim prompt injection resistance has been demonstrated on the hosted
  agents. The jailbreak filter is on and was never triggered.
- I do not claim network isolation, key rotation, customer managed keys or tuned
  role assignments.
- I do not claim the content filter's behaviour on a block has been tested.

## 4. Changes I would make before production, none of them made

1. Set `disableLocalAuth` to true.
2. Disable public network access and add a private endpoint.
3. Review the three Azure AI User assignments and remove what is not needed.
4. Pin the model version.
5. Turn off message content recording, or move it to a workspace with its own
   access and retention rules.
6. Add a custom content filter with indirect attack detection, and a workflow
   branch that routes a blocked call to a human.
7. Add diagnostic settings and an Azure budget with an alert.

Each of these is a configuration change to a validated system, so each needs a
review and a test run of its own. I have left the system exactly as it was when
the final run passed.
