# Escalation branch validation plan

Prepared 2026-09-20. **Nothing in this folder has been deployed or executed.**
Every step below that contacts the hosted service needs its own explicit
approval.

## Why this is needed

The one real run, SYN-CASE-4003 on workflow v6, took the approve branch. The
draft it approved asserted no meter failure and promised no credit, and the
pre-registered grader file `submission/SYN-CASE-4003_expected_NOT_SENT.json`
already listed "explains that supplied records do not confirm a meter defect and
states next steps" as an acceptable outcome. The approval was not a defect.

**Update, after the second real run on workflow v9.** That run did take
`if-node-failclosed-escalate`, on a genuine escalation token, so the hosted gate
has now selected each branch once. The compliance agent gave no reason, so the
run is evidence about the gate and the wiring, not about a compliance judgement.
See `docs/SECOND_RUN_RESULT_2026-09-20.md`. The rest of this section is kept as
written before that run.

It does mean the fail-closed branch, `if-node-failclosed-escalate`, has never
been observed in the hosted service. Locally the gate is correct on 24 of 24
outputs with the real Power Fx engine. Whether the hosted engine agrees is
unknown for every input except the one it has seen.

The compliance agent is **not** to be changed to produce a rejection. Two
separate tests answer two separate questions, and they must never be reported as
each other.

## Test A. Gate harness: does the hosted gate select the right branch?

File: `gate_harness.yaml`

| Property | Value |
| --- | --- |
| Agents invoked | none |
| Model requests | none, so no token charge is expected. Confirm against billing |
| Gate condition | byte-identical to `tests/powerfx_gate/gate_v6.txt`. In v10 the production condition is `And(<that gate>, <draft is readable>, <investigation is complete>)`. The harness has no draft and no specialists, so it tests the gate term alone |
| Node ids | the production ids, so the runner's route reporting applies unchanged |
| Input | the compliance text is typed in by the operator as the first message |

`SetVariable` fills `Local.Var1497` with a one-row table holding the injected
text, the gate runs, and each branch sends a fixed marker. The approve branch
also echoes the text through a `{...}` template, which checks in the hosted
service, without paying for a nine-agent run, that templates are evaluated.

Suggested inputs, taken from the local 24-case set:

1. a clean approval, JSON then the approved token as the final line
2. a clean escalation, JSON then the escalate token
3. a refusal that quotes the approved token, then the escalate line
4. a refusal that ends in the approved token with no escalate token
5. compliance prose with no token at all
6. both tokens

**What a result establishes:** how the hosted Power Fx engine evaluates the
production gate expression, and that the branch wiring and the release template
behave as designed.

**What it never establishes:** that EvidenceComplianceAgent rejects anything.
The text is injected. Every artifact from this test must carry the label
`GATE HARNESS, INJECTED INPUT, NOT A MODEL DECISION`, and it must not be counted
as a workflow execution of a case.

**Limits.** It needs a second workflow definition in the project, which is a
free control-plane write but is still a new object. The table it builds has one
column, `Text`, where production has the full message record. The gate reads
only `.Text`, and this shape is checked locally in `tests/powerfx_gate`.
`System.LastMessage.Text` and `SetVariable` are used as in Microsoft's
DeepResearch sample, but have not been observed in this project.

## Test B. End to end: does the system escalate a case that needs a human?

File: `SYN-CASE-4021_input.json`

A different synthetic account whose records genuinely conflict. The July bill
labels its closing read `actual`. The meter read record for the same date is
labelled `estimated`, and a communication-loss event covers the last eight days
of the period. The arithmetic is consistent, 910 kWh at $0.22 plus $12.00 is
$212.20, so the only problem is the conflict itself.

Why this legitimately calls for human review under the instructions already
deployed, none of which are changed:

- AccountEvidenceAgent: "If records conflict, preserve both and flag
  HUMAN_REVIEW_REQUIRED."
- EvidenceComplianceAgent: HUMAN_REVIEW_REQUIRED for "LOW or INSUFFICIENT
  material confidence".

Safeguards on the case itself:

- The input states no conclusion. The word "conflict" does not appear in it, and
  it uses only the fields of the canonical case, so it passes the runner's
  allowlist.
- The id SYN-CASE-4021 appears in no agent's instructions. SYN-CASE-4007 was
  deliberately not used, because AccountEvidenceAgent's reference block
  describes that case in a sentence, which is the contamination that was removed
  for SYN-CASE-4003.
- No grader file is sent. If one is written it carries the `_NOT_SENT` suffix.

**The outcome is not predetermined.** The agents may write a careful draft and
compliance may approve it. If that happens it is a finding about the design, not
a failed demo: the gate would be approving a *draft* while the *case* still needs
a person. It must be reported as it happens and the run must not be repeated to
get a different answer.

To run it, register the case in `runner/case.py` `CASES`, one line, and use the
same guarded command as any other run. Estimated cost is the same order as the
first run, about $0.03 to $0.05, against a modelled worst case of $0.33.

## Can the escalation branch be exercised independently?

Yes, in the hosted service, with Test A, at no model cost, as a test of the gate
and the wiring only. No, not as a compliance decision: the only honest way to
observe EvidenceComplianceAgent rejecting something is to give the whole system
a case that deserves it, which is Test B, and to accept whatever it decides.

## Order

1. One verification run of SYN-CASE-4003 on v9. Done, see the update above. The
   final acceptance run on v10 is planned in `docs/FINAL_RUN_ACCEPTANCE_PLAN.md`.
2. Test A, if a second workflow definition is acceptable.
3. Test B, once.
