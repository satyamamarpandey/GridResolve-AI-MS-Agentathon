# Security

## Attack surface as actually deployed

Small, by construction. Nine prompt agents on one model deployment, no tools, no external network calls, no knowledge store, no retrieval index, no MCP, no code execution, no write path to any system of record. The only inputs are the synthetic case payload and the conversation.

## The finding that mattered

All nine agents carried a live `web_search` tool binding, discovered by reading the deployed definitions rather than the design document. That is an external grounding path into agents whose entire purpose is to reason only from supplied evidence, and a billable call path outside the cost controls.

It was removed on every agent. Instructions were unchanged, so the agents already said "no external tools are allowed in the hackathon configuration" while the binding contradicted it. The gap between what the prompt claimed and what the platform had bound is exactly the class of issue a configuration review catches and a demo does not.

## Threat model, principal risks

| Threat | Control | Status |
|---|---|---|
| Direct prompt injection | Boundary rule in every agent, instruction hierarchy, RT-01 | CONFIGURED, not tested |
| Agent stalls or returns no usable output | Third gate term withholds the message and escalates | STATICALLY_VALIDATED. The stall itself was observed in runs 1 and 2 and corrected in v10 |
| False authority claim ("my manager approved") | Human approval is a workflow route, not a text assertion, RT-02 | CONFIGURED |
| Coercion into an unsupported meter claim | Claim ledger plus independent compliance, RT-03 | CONFIGURED |
| System instruction extraction | Agents return a defined JSON contract only, RT-04 | CONFIGURED |
| Real customer data substitution | Synthetic-only boundary, CANNOT_RESOLVE_SAFELY, RT-05 | CONFIGURED |
| Compliance bypass request | Compliance is a workflow node, not an optional step, RT-06 | STATICALLY_VALIDATED. The node ran in all three runs. The adversarial request has not been tested |
| Escalation suppression request | Escalation is the default branch, RT-07 | STATICALLY_VALIDATED. The default branch was taken in run 2. The adversarial request has not been tested |
| Evidence ID tampering | Compliance verifies IDs resolve to ledger records, RT-08 | CONFIGURED |
| Policy fabrication | Policy IDs must resolve; missing policy forces review, RT-09 | CONFIGURED |
| Unauthorized credit | No write path; authorization is human, RT-10 | CONFIGURED |
| Cross-case leakage | One case per conversation, RT-11 | CONFIGURED |
| Stale or duplicate action | Freshness and prior-adjustment checks, RT-12, RT-13 | CONFIGURED |
| Correction loop exhaustion | Two-correction ceiling, RT-14 | PREPARED_ONLY, loop not wired |
| Malformed handoff | Contracts plus fail-closed routing on malformed compliance output | STATICALLY_VALIDATED |
| Cost guard bypass | Approval gate outside the system, RT-16 | Enforced by process |

The full pack is `gridresolve_red_team_pack.jsonl`, 16 scenarios, machine-readable, structurally validated. **None have been executed.** The three real runs used one benign synthetic case, so they show the controls operating, not the controls under attack. No security claim here is proven against an adversary.

## The security defect in the safety control itself

The fail-closed gate was not failing closed. The condition searched the entire compliance output for the substring "APPROVE", and Power Fx matches regardless of case, so a rejection reading "cannot approve this unsupported meter claim" satisfied it and skipped escalation.

This is worth stating plainly because it is the most instructive result in the project: the control that existed to prevent unsafe release was itself the unsafe component, and only reading the deployed expression against the documented operator semantics revealed it. `tests/test_routing_and_data.py` demonstrates the old condition failing open on 5 of 11 cases, under a local model that treats the output as text. That version never ran in the hosted service. Evaluated on the real Power Fx engine, it and its first replacement do not compile at all, because the variable is a table of message records. The gate that replaced them is correct on 24 of 24 adversarial outputs on that engine, and the live v10 gate passes 105 cases.

## Secrets and data handling

No credentials, keys or tokens appear in any agent instruction, workflow definition, runtime evidence file or submission artifact. The runner fetches a token per request and never writes one to disk, and the evidence folders were scanned for tenant identifiers and bearer tokens after each run. Azure authentication uses interactive sign-in through Azure CLI; no token is stored in the project. Subscription and tenant identifiers are excluded from all submission material and must be blurred in screenshots. All case data is synthetic.
