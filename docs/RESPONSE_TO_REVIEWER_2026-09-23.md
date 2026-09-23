# Response to the external review, 2026-09-23

From Satyam Pandey. This is the text sent to the reviewer. Every figure in it
is taken from `docs/POST_REVIEW_VALIDATION_REPORT.md` and the files it cites.

---

Hello Anita,

Thank you for the substantive review. You named the exact gaps, and I spent the
days since closing the ones I could close and measuring the ones I could not.
Here is what happened, point by point.

Narrow evidence base. Before your review, the hosted evidence was three runs of
one synthetic case. Since then I published workflow v11 and a revised
compliance agent and executed five more hosted runs on Microsoft Foundry, one
each of SYN-CASE-4007, 4001, 4003, 4011 and 4002, under a spending cap and with
acceptance criteria written before each run. Eight hosted runs now exist across
five distinct synthetic cases. The historical three runs and their evidence are
untouched.

Unexplained escalation. The compliance agent now carries a mandatory
reason-code contract: any non-approval must cite the failed claim, the evidence
gap or the policy rule, and a decision that cannot be determined is an
escalation. That contract is enforced offline by 21 checks and by a check over
the real evidence, which still fails run 2 because that run gave no reasons. I
have to report plainly that no hosted run on the revised agent has yet produced
a non-approval, so the reason codes have not appeared in a hosted decision. The
case built to provoke an escalation, SYN-CASE-4007, was instead approved with a
message that states the record conflict and promises nothing, and the planner
sent the case to a person. Eight of its fourteen criteria passed and the
escalation target was missed. The decision text and citations are in the run
record.

Rejection and correction branches. Workflow v11 implements bounded
REJECT_AND_REWRITE and REJECT_AND_REPLAN routes: at most two corrections,
unrolled so no counter is under model control, only the latest draft can be
released, and a third rejection or a malformed token fails closed. The routes
are proven on Microsoft's open-source declarative workflow engine with the
byte-identical YAML, 76 checks. They are not proven in the hosted service. The
two runs designed to draw them, SYN-CASE-4011 and SYN-CASE-4002, were both
approved at the first attempt because the upstream agents produced compliant
output: the communication agent refused the injected promise of a credit, and
the planner referred the true-up case to a human. I count that as the agents
behaving correctly and the correction routes remaining hosted-unobserved, and
the documents say exactly that.

No-follow-up branch. Observed for the first time on 2026-09-23. SYN-CASE-4001
released an approved explanation, the planner cleared the case, the workflow
recorded no follow-up, the escalation agent was never invoked, and the audit
recorded that correctly. Twelve of twelve criteria passed. This run is also the
second annotated trace.

Root-cause label mismatch. I kept the v2.0 results frozen and adjudicated the
label as a versioned ground truth v2.1 with two axes, a claim verdict and a
root cause. Under v2.1 the final v10 run passes 14 of 14 deterministic checks.
The new runs also surfaced two new mismatches, on SYN-CASE-4011 and 4002, which
are recorded as failures and not adjudicated away.

Coverage matrix and metrics. The matrix now carries the observed results per
row, and every metric you listed is reported with its denominator: false
releases 1 of 8 and 0 of 6 since v10, unnecessary escalations 1 of 8 and 0 of 6
since v10, correction attempts 0 of 5, latency 165 to 220 seconds per v11 run,
about 78,000 to 106,000 input tokens per run, and an estimated USD 0.06 to 0.08
per run. Azure billing has confirmed USD 0.131 for the three historical runs
against an estimate of USD 0.131; the five new runs, estimated at USD 0.33 in
total, were not yet visible in billing when I wrote this.

Supervisor feedback loop. It is implemented and locally tested: an immutable
review record that distinguishes an actual human review from an offline
simulation, an append-only store on the audit log, and metric functions that
refuse to report without real decisions. No supervisor has reviewed any case,
so the override rate and the review-time reduction are reported as NotMeasured,
which is what the code returns.

Annotated trace and identifiers. Two traces are published, the historical v10
run and the new SYN-CASE-4001 run. Infrastructure identifiers were removed from
the submitted PDF and are absent from every new document and evidence file; a
scan is part of the publication checklist.

What is still open: the escalation route and both correction routes have not
been observed in the hosted service; 15 of the 20 prepared cases, 26 of the 36
evaluation rows and all 18 adversarial probes have not run; no human review has been recorded; no utility
system is integrated. The system is not production-ready and the documents do
not say otherwise.

The repository at https://github.com/satyamamarpandey/GridResolve-AI-MS-Agentathon
holds the consolidated post-review validation report, the updated PDF
revision, the per-run results and the eight evidence folders.

Thank you again for pushing on the failure paths. That is where the work went.

Satyam Pandey
