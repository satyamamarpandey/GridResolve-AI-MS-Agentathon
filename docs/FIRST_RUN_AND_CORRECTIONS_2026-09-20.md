# First real run, and what it corrected, 2026-09-20

One workflow execution has now happened in Microsoft Foundry. This records what
it showed, the four defects it exposed, their root causes, and the corrections.
The corrections are deployed and verified locally and by read-only checks. **They
have not been verified by a second run.**

## The run

| Field | Value |
| --- | --- |
| Case | SYN-CASE-4003, synthetic |
| Workflow | GridResolveAIWorkflow **v6** |
| Response id | `wfresp_0e74508741ea3ef600XeSZg2eU2GjWnR72Jnm7T4D2IsyPdhBc` |
| Status | completed, 85.6 s, 1303 stream events, 22 conversation items |
| Route | approved and released. EscalationCoordinatorAgent did not run |
| Tokens | 46,810 input, 10,828 output |
| Cost | **$0.0334, provisional.** From reported tokens at list price. Not yet reconciled with Azure billing |
| Evidence | `evidence/runtime/20260920T205607Z_SYN-CASE-4003_80391bf2/`, 11 files, unmodified |

The sum of the eight inner agent responses, read back individually, equals the
workflow's usage block exactly. The token count is therefore complete. The dollar
figure stays provisional until it appears in Azure billing.

### The approval was not a defect

The customer draft said "we cannot confirm the meter is broken", cited evidence
for each claim and promised no credit. The grader file written before the run,
`submission/SYN-CASE-4003_expected_NOT_SENT.json`, lists exactly that as an
acceptable outcome. No agent asserted a meter failure at any stage.

What the run contradicts is the description, elsewhere in this repository, that
this case ends in a refusal and a human escalation. It did not. The fail-closed
branch has never been observed in the hosted service. See
`tests/escalation_validation/PLAN.md`.

## D1. The customer was sent an expression instead of the draft

**Observed.** The released message was the 34 characters
`=Last(Local.VarCustomerDraft).Text`.

**Root cause.** `SendActivity.activity` is a **template**, not an expression.
Text is sent as written and only `{...}` segments are evaluated. A leading `=`
means nothing there. Conditions and `SetVariable` values are expressions and do
take `=`, which is why the gate worked and the release did not.

- Microsoft Learn, *Build a workflow in Microsoft Foundry*: "in the **Message to
  send** area, enter `{Upper(Local.Var01)}`".
- `microsoft/agent-framework`, `workflow-samples/CustomerSupport.yaml`:
  `activity: "Created ticket #{Local.TicketParameters.TicketId}"`.
- `Extensions/TemplateExtensions.cs`: a `TextSegment` is emitted verbatim, an
  `ExpressionSegment` is evaluated.

**Why it was missed.** The earlier local test evaluated
`Last(Local.VarCustomerDraft).Text` as a bare expression, got a string, and
passed. It tested the wrong contract. The v5 form, `=Local.VarCustomerDraft`,
had the same fault.

**Reproduced.** `tests/powerfx_gate` now parses the activity with
`TemplateLine.Parse` from `Microsoft.Agents.ObjectModel`, the parser the
open-source engine uses. The v6 activity yields the literal string the hosted
service delivered, character for character.

**Correction, workflow v7.** `activity: "{Last(Local.VarCustomerDraft).Text}"`.
Nothing else in the workflow changed. The gate is byte-identical.

## D2. AccountEvidenceAgent asked for confirmation instead of working

**Observed.** Its whole output was 363 characters: "Per instructions, this
response is the intake/triage. If you want, I will now produce the full ...
Please confirm to proceed." No evidence ledger was produced. Downstream agents
worked from the raw case records, so their findings still hold.

**Root cause.** Every agent is invoked on one shared conversation with
`input.messages: ""`. The agent therefore sees the case, then the triage output
as an assistant turn, and no new instruction. It took the triage output for its
own earlier turn and offered to continue. Nothing in its instructions said that
it runs unattended or that earlier assistant messages come from other agents.

**Correction, AccountEvidenceAgent v8.** An AUTOMATED INVOCATION paragraph: no
human is present, earlier assistant messages are other agents' outputs, never ask
for confirmation, produce the complete output now. Its evidence rules, its
authority rules and "Never infer meter failure" are unchanged.

**The same gap exists in the other agents.** None of the nine had that paragraph.
One of eight stumbled. Only the two agents republished for other reasons received
it. See remaining risks.

## D3. The audit record was partly wrong

**Observed.** Four participating agents listed where eight ran, agent versions
given as "v1.0", and `execution_status: CONFIGURED` for a real execution. The
workflow version, compliance decision, evidence ids and policy ids were correct.

**Root cause.**

- *CONFIGURED.* The agent's own metadata line ended
  `execution_status=CONFIGURED`. It copied it, against the rule further down that
  defines RUNTIME_EXECUTED.
- *Versions.* No upstream output states an agent version, and an agent cannot
  see platform metadata. The instruction "agent_versions ... when available"
  left the model to fill the gap. "v1.0" appears nowhere upstream.
- *Four of eight.* Upstream outputs do not name the agent that wrote them, and
  the audit agent was never told the pipeline.

**Correction, in two parts.**

1. CaseAuditAgent v5: the pipeline order is stated, every agent is listed with
   an output status of RECEIVED, MISSING_OR_MALFORMED or NOT_INVOKED, versions
   are reported as NOT_OBSERVED and never invented, and the CONFIGURED token is
   gone from the metadata line.
2. The authoritative record now comes from the platform. Every conversation item
   carries `created_by.agent` with the name and version actually invoked. The
   runner reads that into `11_run_analysis.json` and compares the audit agent's
   account against it. For the first run the platform recorded: CaseTriageAgent
   5, AccountEvidenceAgent 7, UsageAnomalyAgent 4, PolicyKnowledgeAgent 5,
   ResolutionPlannerAgent 5, CustomerCommunicationAgent 4,
   EvidenceComplianceAgent 5, CaseAuditAgent 4. That also settles an open
   question: agents referenced by name resolve to their latest version.

## D4. The runner misreported the gate and listed agents twice

**Root cause.** The hosted service emits no `workflow_action` item for the
ConditionGroup. The gate is visible only as the predecessor of later actions,
`if-node-approved-releaseActions` and `node-1789696874113_Post`. The mocked
events had assumed an item of its own. Separately, every action arrives twice, as
`added` then `done`, and both were listed.

**Correction.** `describe_route` counts the gate as evaluated when any emitted
action names it or one of its branches as predecessor, and de-duplicates ids. A
new module, `runner/analysis.py`, derives participation, the compliance token,
whether the release delivered the draft, and the accuracy of the audit, from
captured items. `python -m runner analyze --run-dir <dir>` replays any earlier
run offline and writes nothing. The runner also now refuses to run against a
workflow whose `activity` starts with `=`.

Replayed against the real capture, the corrected code reports the approve route,
the gate as evaluated, eight distinct agents each once, their true versions,
`UNEVALUATED_EXPRESSION` for the release, and six inaccuracies in the audit.

## Versions

**Superseded.** This table is as it stood before the second run, on workflow v9.
A second run has since happened and the live configuration is workflow v10. See
`docs/SECOND_RUN_RESULT_2026-09-20.md` and `docs/V10_CORRECTIONS_2026-09-20.md`
for current versions and the current payload hash.

| | First run | Before the second run |
| --- | --- | --- |
| GridResolveAIWorkflow | 6 | **9** |
| AccountEvidenceAgent | 7 | **8** |
| ResolutionPlannerAgent | 5 | **6** |
| CustomerCommunicationAgent | 4 | **5** |
| CaseAuditAgent | 4 | **6** |
| EscalationCoordinatorAgent | did not run (was 4) | **5** |
| CaseTriage 5, UsageAnomaly 4, PolicyKnowledge 5, EvidenceCompliance 5 | unchanged | unchanged |

EvidenceComplianceAgent is v5, as it was. Its approval rules were not touched.

The case input's `workflow_version` label moved from v6 to v9, that field only,
checked leaf by leaf against the payload the first run actually sent.

| Payload | sha256 |
| --- | --- |
| Sent in the first run, label v6 | `d10a3af0396a842cc18a69ed96f132fef04bb3b5937263ddd545a04ae22c8d51` |
| Superseded, label v8, never sent | `e7e71cb93ba0924356b86a97e92c40c8481d8af90b151806b28bd862bd3d4f03` |
| Current, label v9 | `045454848ca43de3d5aec6da9f7982a5965ca1e74735a3b95c91884e6f97b065` |

## Not established

- That workflow v9 and the republished agents behave as intended in the hosted service. Only a run shows that.
- That the hosted gate ever selects the escalate branch.
- The billed dollar amount of the first run.

## Pre-verification hardening, workflow v8

Done after the corrections above and before any second run. No model was called.

### A local stand-in for the hosted engine, calibrated against the real run

`tests/workflow_engine` runs the real workflow YAML on Microsoft's open-source
declarative workflow engine (`Microsoft.Agents.AI.Workflows.Declarative`), with
each agent replaced by the genuine output it produced in the first run.

Run on the **v6** definition it reproduces what the hosted service did: the same
eight agents in the same order, the same branch, the same internal action ids the
service named as predecessors, and the same literal
`=Last(Local.VarCustomerDraft).Text` sent to the customer. Had this existed
before the first run, D1 would have been caught for free.

It is still not the hosted service. It is the closest thing available, and it is
now known to agree with the hosted service on the one case where both are known.

### The customer now receives a customer-ready message

v7 would have evaluated its template and sent the communication agent's whole
JSON object, internal claim and policy ids included.

v8 saves that agent's JSON with `output.responseObject`, the route Microsoft
documents for structured agent output, and releases six fields under plain
headings: the summary, what was reviewed, what was found, why the bill changed,
what happens next, and what is needed from the customer. Internal ids stay in the
conversation record and the audit.

Two hazards were found by running candidates in the engine, not by reasoning:

- A draft that was not valid JSON would have sent the customer empty headings.
  v8 releases only when all six fields are non-blank. Otherwise the message is
  withheld and the case escalates. Tested for non-JSON, code-fenced, and
  blank-field drafts.
- A draft with a field *missing* fails the run at the gate. Power Fx cannot catch
  it, it is a binding error, and `IfError` was tried. Nothing reaches the
  customer, but there is no audit either. This is closed at the source:
  CustomerCommunicationAgent v5 has a strict JSON schema requiring every field,
  and the runner refuses to spend money unless that schema is live. The schema is
  not a guess. The genuine first-run draft validates against it exactly.

`ParseJSON` was considered and rejected: the open-source engine does not enable
the Power Fx JSON functions, so it could not be tested.

#### What an incomplete draft does in v8, case by case

Run on the local engine with the genuine first-run draft altered one field at a
time, all six fields in turn.

| Draft | Sent to customer | Escalated | Terminal audit |
| --- | --- | --- | --- |
| not JSON, code-fenced, or truncated | nothing | yes | yes |
| a field is an empty string or null | nothing | yes | yes |
| a field is missing, or the output is `{}` or an array | nothing | **no** | **no, the run fails at the gate** |
| a field holds only spaces, tabs or line breaks | **the message, with a heading over nothing** | per follow-up gate | yes |

Two limits follow, and neither is hidden.

1. **An output that breaks the schema can still prevent the terminal audit.** A
   missing field is a Power Fx binding error, the gate action fails, and the
   workflow stops there. Nothing reaches the customer, which is the fail-closed
   property that matters most, but no escalation package and no CaseAuditAgent
   record are written either. The platform still holds the run, and the runner
   treats `failed` as a terminal status and writes the same evidence files,
   reporting the status as failed and never as completed. That runner path is
   covered by mocked tests only, it has not been seen against the service. The strict
   schema is what is meant to make this path unreachable: strict structured
   output is documented to constrain the model to the schema, so a field cannot
   be omitted. That has not yet been observed in this project. If the service
   did not enforce it, this is the outcome.
2. **A field containing only whitespace is released.** `IsBlank("   ")` is false
   in Power Fx, and a JSON schema that the service accepts in strict mode cannot
   require non-whitespace content. The workflow does not prevent this. The
   runner reports it after the fact: `11_run_analysis.json` records
   `customer_ready: false` and the report says so. A guard that trims spaces,
   tabs and line breaks before the blank test withholds all of these drafts on
   the local engine and leaves the genuine message byte-identical. It has
   **not** been deployed, because it is a new workflow version and a new payload
   hash, and that decision was left to the owner. **It was then approved and
   deployed as workflow v9. See the last section.**

No incomplete message is released when a field is absent, null or empty. One is
released when a field is present and holds only whitespace.

### Message approval and human review are now separate questions

The first run showed the gap. The planner wrote that an on-site meter test and
any adjustment needed a person. Compliance, correctly, approved a safe message.
The workflow then had nowhere to send the first fact, and the audit recorded
`NO_HUMAN_REVIEW_REQUIRED`. Approval of the message had erased the review.

| Question | Answered by | Routed by |
| --- | --- | --- |
| A. Is this message safe to send? | EvidenceComplianceAgent, unchanged | the existing gate |
| B. Does the case still need a person? | ResolutionPlannerAgent v6, a `CASE_FOLLOWUP` token on its final line | a second gate, inside the approve branch |

The second gate mirrors the first: only an exact, unique, final-line
`CASE_FOLLOWUP::NONE_REQUIRED` skips the handoff. A missing token, both tokens, a
quoted token, lower case, or an empty plan all hand the case to
EscalationCoordinatorAgent. The genuine first-run plan, which has no token, is
one of the test inputs and hands off.

Compliance was not changed and is never asked to reject a safe message because
the case needs follow-up.

**Implemented:** the token, the second gate, the handoff, the audit agent
recording the two answers separately, and runner checks that flag an audit which
lets approval erase a human review, and a run where the planner asked for a
person and no handoff was observed.
**Planned only:** a correction loop that returns a rejected draft to the writer,
and any notification to a real person. The handoff is a prepared package, as
before.

### The audit cannot be the source of truth about the run

CaseAuditAgent v6 must report agent versions as NOT_OBSERVED, list every pipeline
agent with an output status, and label its record
`MODEL_PRODUCED_FROM_CONVERSATION`. The runner's `11_run_analysis.json` carries
the platform's own record of who ran at which version, marks which of its fields
are platform-observed and which are model-produced, and lists every disagreement
between the two. An invented participant, a false NOT_INVOKED, a wrong version
hidden behind a later correct entry, and an erased human review are each tested.

What this does not do is prove how the v6 audit agent will behave. A language
model cannot be run locally. Its instructions are verified, and its first-run
predecessor's output is correctly judged inaccurate on seven counts.

### Unattended invocation in the other agents

The cause of D2, a shared conversation with an empty input message, applies to
every agent after the first. Four agents now carry the unattended-invocation
paragraph, each republished for another reason. UsageAnomaly, PolicyKnowledge and
EvidenceCompliance do not, and each produced complete output in the real run, so
there is no evidence for changing them. CaseTriageAgent runs first and sees no
earlier assistant turn, so the mechanism does not reach it.
EscalationCoordinatorAgent has never run and will now run in most cases, so it
was the one agent where the risk was open. It was republished as **v5** with the
same paragraph, word for word. Its header line also lost the stale
`GridResolveAIWorkflow v5` and `execution_status=CONFIGURED`, the text
CaseAuditAgent copied into the first run's record. Everything from BOUNDARY
onward, its triggers, reviewer routing, output contract, authority limits and
failure rule, is byte-identical to v4, checked before publishing and on readback.
Workflow v8 names its agents without a version, and the first run showed names
resolve to the latest version, so v8 did not need republishing. The runner flags
any agent, in any position, that asks instead of working.

### Line endings

`runner/case.py` decodes the case file as UTF-8, drops a byte-order mark and
normalises line endings before hashing and sending, in one named function. A
CRLF checkout, a BOM, or both produce the same sha256 and the same payload, by
test. `.gitattributes` pins the case files and the deployed expressions to LF and
marks `evidence/runtime/**` as binary so Git never rewrites captured evidence.

## Workflow v9: whitespace-only fields are withheld

Approved by the owner after the finding above, and deployed before any second
run. No model was called.

**The change.** One line of the workflow differs from v8, the gate condition, and
inside it only the readable guard. For each of the six customer fields

    !IsBlank(Local.VarCustomerMessage.<field>)

became

    !IsBlank(Trim(Substitute(Substitute(Substitute(Local.VarCustomerMessage.<field>, Char(10), ""), Char(13), ""), Char(9), "")))

Line feeds, carriage returns and tabs are removed, `Trim` removes the spaces, and
what is left is blank exactly when the field held nothing but those four
characters, or was empty or null. The compliance term of the gate is
byte-identical to `gate_v6.txt`. Every action, id, agent reference, branch,
template and `autoSend` flag is identical to v8, asserted on the parsed YAML
before publishing and confirmed on readback. No agent was changed.

**Verified on Microsoft's Power Fx engine, 36 rows.** Prose, prose containing
tabs and line breaks, prose padded with white space and a single character are
released. Empty, null, spaces-only, and seven further white-space shapes are
withheld. A missing field is still a binding error. The v8 guard run on the same
rows releases all 14 white-space rows, which reproduces the defect.

**Verified on Microsoft's workflow engine with the actual v9 YAML.** Six
white-space shapes, each placed in each of the six fields, 36 runs: nothing is
sent, the case escalates once, and the terminal audit runs. The genuine first-run
draft produces exactly the message v8 produced. Prose that merely contains tabs
and line breaks is released unaltered.

**What v9 does not do.**

- It does not cover Unicode white space outside those four characters, such as a
  non-breaking space. The runner's own check is stricter and would report such a
  release as not customer-ready.
- It cannot judge whether text is meaningful, only that it is not empty. A field
  holding a single full stop passes. Whether the prose is adequate is the
  compliance agent's question, not the gate's.
- A field missing from the output still stops the run at the gate with nothing
  sent and no terminal audit, as described above.
- None of this has been observed in the hosted service.

**Version consistency.** The runner, the read-only verification, the Control
Center and the case label all name v9. The runner refuses a case file labelled
v8 and refuses a live workflow at v8, each with zero requests, by test.

**The escalation agent and unattended invocation.** A language model cannot be
run locally, so its behaviour is not tested. What is tested: in v9 it is invoked
once on either route with no input step before it, a reply that asks for
confirmation does not stop the terminal audit, and the runner reports such a
reply as `ASKS_FOR_CONFIRMATION` while leaving a complete package unflagged.
