# Integration contracts and local mocks

This folder is where I wrote down what GridResolve AI would need from a
utility's systems, and the security rules those connections would have to keep.

**What this is.** Typed contracts, port interfaces, authorization rules and
in-memory adapters backed by the synthetic case. It is plain Python, standard
library only.

**What this is not.** A real utility billing system, meter data system, CRM or
identity provider is not connected. This code is not deployed anywhere. It makes
no network call, no Azure call and no model call, and it costs nothing to run.
The nine Foundry agents do not call it: workflow v10 ran with no tools, and I
have not attached any. Everything here is a design, tested locally against
synthetic payloads.

## Files

| File | Holds |
| --- | --- |
| `contracts.py` | Frozen dataclasses: account, rate, billing record, meter reading, meter event history, diagnostic result, usage period, CRM case, outbound message, review assignment, adjustment request and authorization, audit record |
| `ports.py` | Protocols: four read-only evidence ports, CRM, review assignment, adjustment authorization, audit store |
| `auth.py` | Roles, permissions, the principal, the synthetic identity provider, the access guard |
| `validation.py` | Identifier patterns and boundary checks |
| `synthetic_store.py` | Parses a synthetic case file into immutable records |
| `synthetic_adapters.py` | Evidence, CRM and review adapters, and the environment builder |
| `adjustments.py` | Adjustment requests and supervisor decisions |
| `audit_store.py` | Append-only, hash-chained audit records |
| `reliability.py` | Deadline wrapper, bounded retry, idempotency ledger |
| `errors.py` | Typed failures |

Evidence contracts use the field names of `submission/SYN-CASE-4003_input.json`,
so the adapter serves the same records the agents saw in the three real runs.
The file is only read. The case's empty `adjustments` and `prior_contacts` lists
have no contract yet.

## Rules the tests prove

Run `python tests/test_integration_contracts.py`.

1. **Authentication boundary.** Every port method takes a session first. A
   missing, made-up, revoked or expired session is refused, and all four look the
   same to the caller.
2. **Read-only evidence.** The evidence ports have `get_` methods only, for every
   role. Returned records are frozen and collections are tuples.
3. **Case-level authorization.** An agent principal is scoped to exactly one case.
4. **Customer-data isolation.** Another customer's case, a case that does not
   exist, and another customer's account id all get the same fixed sentence. The
   refusal names no case, account, amount or reading.
5. **Input validation.** Identifiers must match the synthetic patterns, such as
   `SYN-CASE-NNNN`. A rejected value is never echoed. The store refuses data not
   labelled `SYNTHETIC_ONLY`.
6. **Timeouts.** A call that answers after its deadline raises, and its answer is
   discarded. The clock is injected, so the tests never sleep. The check runs
   after the call returns and does not interrupt it. A real connector also needs
   a transport timeout.
7. **Idempotency.** The same key and payload returns the first result. The same
   key with a different payload is refused.
8. **Safe retry.** Only reads are retried, only on a transient error, at most
   five times. Writes and authorizations are never retried. A refusal is never
   retried.
9. **Supervisor-only adjustment authority.** Only a session resolved to
   `HUMAN_BILLING_SUPERVISOR` can authorize. A role passed as a string, a
   hand-built principal and a token that looks privileged all fail.
10. **Four eyes.** A supervisor cannot decide their own request.
11. **Audit integrity.** Records are hash-chained per case. An edit, a deletion, a
    reordering, and an edit with a recomputed hash are all detected. The store
    has no method that changes or drops a record. The actor comes out of the
    session, never out of an argument.

## What "an agent cannot cause an adjustment" means here

A caller that holds an agent session and these ports cannot request, authorize or
list an adjustment, and its attempts are written to the audit chain. Beyond that,
no method in this package applies money to an account at all. An authorization is
a recorded human decision. Applying it would be the billing system's job.

The limit of that claim: the synthetic identity provider is the trust root. Code
that can reach it can issue itself any session. In these mocks only the test
harness holds it. Python also cannot stop code in the same process from reaching
into private fields, so this is a contract and a test suite, not a sandbox.

## What a real implementation would need

- **Entra ID managed identities.** One identity per agent and one for the
  workflow, with no shared secrets. Human approvers sign in through Entra ID with
  MFA, and the supervisor role comes from a group or app role claim in a validated
  token. `SyntheticIdentityProvider` would be replaced by token validation.
- **RBAC per port.** Each port is a separate API with its own role assignment.
  Agent identities get read-only evidence scopes. The adjustment API accepts only
  human supervisor tokens and rejects every managed identity.
- **Case scoping done by the server.** The allowed case comes out of the workflow
  run's context, not out of anything an agent writes.
- **Private networking.** Private endpoints and no public ingress to the billing,
  meter and CRM systems.
- **The system of record as the only writer.** Billing data changes in the
  utility's billing system, through its own approval process. This layer would
  pass a supervisor's decision to it and would never write a balance.
- **A durable audit store.** Immutable storage with retention, and the chain head
  anchored outside the store.
- **Durable idempotency keys and transport timeouts** in place of the in-memory
  ledger and the after-the-fact deadline check.

I have built and deployed none of these.
