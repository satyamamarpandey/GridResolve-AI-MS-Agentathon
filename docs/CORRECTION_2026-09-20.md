# Correction record, 2026-09-20

Two defects were found in the deployed Microsoft Foundry configuration while
preparing the first real run, before any model had been called and before any
money had been spent. Both are now corrected. One earlier claim in this
repository was stronger than the evidence supported, and it is corrected here.

Nothing in this document is runtime evidence. No version of the workflow has
ever executed in the hosted service.

## 1. The compliance gate did not evaluate text

### What was deployed

Workflow v5 routed on:

```
=("ROUTE_DECISION::GRIDRESOLVE_APPROVED" in Local.Var1497)
```

and released the customer draft with:

```
activity: =Local.VarCustomerDraft
```

Both variables are filled by `output.messages`. In the open-source declarative
workflow engine (`microsoft/agent-framework`,
`Microsoft.Agents.AI.Workflows.Declarative`) that assigns a **table of message
records** with the columns Id, Role, Author, Content, Text and Metadata. It is
not a text string.

### What the real Power Fx engine does with it

Evaluated with `Microsoft.PowerFx.Interpreter`, configured with
`Features.PowerFxV1` as that engine configures it, against a table of that exact
schema:

| Expression | Result |
| --- | --- |
| v4 gate, `Not("APPROVE" in Local.Var1497)` | does not compile: "Invalid schema, expected a one-column table" |
| v5 gate, `"...APPROVED" in Local.Var1497` | does not compile, same error, on 24 of 24 inputs |
| v5 release, `Local.VarCustomerDraft` | yields a table, where the engine requires a string and throws |

The same engine throws when a condition is neither Boolean nor Blank. It does not
fall through to the default branch. On that engine a v5 run would have stopped at
the gate, after seven agents had already been billed, with no escalation and no
audit.

Reproduce: `dotnet run --project tests/powerfx_gate`

### What is not established

Microsoft Foundry's hosted workflow service is closed source. Whether it types
these variables and evaluates these expressions exactly as the open-source engine
does has **not** been observed. Only a real run can establish that.

### What v6 deploys

The gate reads the text of the last message and approves only when all of these
hold. Every other outcome, including any evaluation that yields Blank, takes the
default branch, which escalates to a human.

1. The text is not blank.
2. The escalate token does not appear anywhere, in any letter case. Escalation
   takes precedence over approval.
3. The approved token appears exactly once, in exact case.
4. The last non-blank line is exactly the approved token and nothing else.

The release step sends `Last(Local.VarCustomerDraft).Text`, which is a string.

The deployed expression is `tests/powerfx_gate/gate_v6.txt`. The live
configuration check asserts that the stored workflow contains that exact string.

### How v6 was tested

24 compliance outputs against the real engine: the nine original adversarial
cases, plus a refusal that ends in the token, the token inside quoted evidence, a
prompt injection quoting the token, the token written twice, a lowercase escalate
token beside an approve line, trailing or leading text on the token line, a
suffixed token, a blank Text field, an empty message table, an approval followed
by a later escalation message, and four legitimate approvals with differing line
endings and whitespace.

| Expression | Correct |
| --- | --- |
| v5, superseded | 0 of 24, all compile errors |
| The idiom from Microsoft's sample alone, `"..." in Last(var).Text` | 13 of 24 |
| **v6, deployed** | **24 of 24** |

v6 changed those two expressions only. Every action id, all nine agent
references, the seven `autoSend: false` nodes, the default escalation branch and
the terminal audit node are structurally identical to v5.

## 2. Correction to an earlier claim

Earlier documents stated that the original v4 gate "failed open on 5 of 11 cases
that required escalation", and presented that as a defect found in the deployed
configuration.

**What is actually established:** `tests/test_routing_and_data.py` modelled the
gate expression as if the compliance output were a text string. Under that
text-only model, the v4 expression skips escalation on 5 of 11 mocked outputs,
because Power Fx `in` matches a substring regardless of case and the word
"approve" appears in ordinary refusal prose.

**What is not established:** that the hosted service ever behaved that way. No
version of this workflow has run there. Against the real message table the v4
expression does not compile at all, so on the open-source engine it would have
failed rather than failed open.

The substring weakness is real as a property of the expression, and it is the
reason v6 refuses any approval that is not an exact, unique, final-line token.
The figure "5 of 11" must be read as the output of a local text-only model, never
as observed hosted behaviour.

## 3. One agent was told the answer

AccountEvidenceAgent v6 carried, in its instructions:

```
SYN-CASE-4003 maps to SYN-2002, unsupported meter-fault claim.
SYN-2002: 2026-06 720 kWh, actual, total $149.20. 2026-07 1480 kWh, actual, total $286.45.
```

Two problems. The agent was given the conclusion it was supposed to reach, so a
run could not have shown that the conclusion came from the records. And the
embedded figures contradicted the canonical case input, 640 to 870 kWh and
$152.80 to $203.40, while a separate instruction told the agent to distrust
supplied records that did not match its embedded dataset.

AccountEvidenceAgent v7 removes the SYN-CASE-4003 line and the SYN-2002 and
SYN-3003 reference records, states that structured records supplied with a case
are authoritative for that case, and states that the remaining reference records
apply only when a case supplies none. Model, reasoning effort and the empty tool
list are unchanged. The instructions never to infer meter failure, and to flag
conflicting records for human review, are unchanged.

No other agent, no case file, no evaluation expectation and no document in this
repository contained the conflicting figures. The canonical figures are
unchanged everywhere.

### Known residue, not changed

The same reference block still describes other synthetic cases in a sentence
each, for example "SYN-CASE-4001 maps to SYN-1001, seasonal usage increase".
Those lines do not affect SYN-CASE-4003. They would weaken an evaluation of those
other cases in the same way, and should be reviewed before any such evaluation is
run.

## 4. Evidence that is now superseded

Kept unaltered, and marked rather than rewritten:

| Item | Status |
| --- | --- |
| `evidence/screenshots/S02.png` | Authentic capture of workflow **v5**. Superseded by v6. The node graph is unchanged, the expression shown in the If node is not |
| `evidence/screenshots/S09.png` | Authentic capture of the local suite totals on 2026-09-20 before this correction. Counts have since changed |
| `evidence/app-screenshots/APP09.png` | Shows "workflow v5, active version, never run", which was true when captured |
| `evidence/screenshots/S04.png` | Still current. EvidenceComplianceAgent remains v5 and was not changed |

## 5. Version label, corrected

The canonical case input carried `"workflow_version": "GridResolveAIWorkflow v5"`.
Every one of the nine agents is instructed to preserve `workflow_version` from
shared state, and none compares it with anything, so that one field is what the
terminal audit record would have carried. A v6 run would have recorded itself as
v5.

Corrected by changing that single field to `GridResolveAIWorkflow v6`. No other
field of the case changed, the file length is unchanged, and no agent version was
published.

| | sha256 of the exact payload |
| --- | --- |
| Before | `81ec94aee6aab305a5b18c8efe5ea3a0198f9ffb62c67f8312f2c3ae7e504a74` |
| After | `d10a3af0396a842cc18a69ed96f132fef04bb3b5937263ddd545a04ae22c8d51` |

Three links are now enforced, so the label cannot drift again without a refusal:
the runner refuses if the case label differs from the version it targets, refuses
if that target differs from the live workflow, and the live configuration check
asserts the case label against the live version directly.

### Left as it is, deliberately

All nine agents still carry `workflow_target=GridResolveAIWorkflow v5` in the
configuration metadata line at the top of their instructions. It is not an output
field and no instruction reads it. Correcting it would mean publishing nine new
agent versions for a string with no functional role, and would supersede capture
S04, the one Foundry screenshot that is still current. The UI test fixtures keep
their `GridResolveAIWorkflow-v4` label on purpose, as documented in
`control-center/src/data/fixtures/PROVENANCE.md`.
