# Agent Team: Contracts

Roster and rationale are in `03_ARCHITECTURE.md`. This is the contract reference: what each agent consumes, what it must emit, and what it is forbidden to do. The prohibitions matter as much as the outputs, because they are what stop a role from quietly absorbing its neighbour's authority.

All nine: model `gpt-5-mini`, reasoning effort low, **zero tools**, synthetic data boundary, instruction-hierarchy rule, preserve `case_id` and `workflow_version`, never discard upstream state. Versions below are the ones the platform recorded in the final run on workflow v10.

Each agent is invoked by the workflow with an explicit input message naming its step and its task. No operator is present and none of them may ask for confirmation. Four return strict `json_schema` output, marked below, so a sentence in place of the object is not possible.

---

**1 CaseTriageAgent** (v5)
Consumes the customer request and any supplied case identifiers.
Emits `intent`, `investigation_type`, `billing_period`, `required_evidence`, `missing_evidence`, the three branch flags, `risk_flags`, `risk_class`, `confidence`, `human_review_candidate`, `triage_summary`.
Must never infer a root cause, promise an adjustment, or claim meter failure.

**2 AccountEvidenceAgent** (v9, strict schema)
Consumes triage plus supplied synthetic records.
Emits `evidence_ledger`, `billing_comparison`, `meter_read_status`, `rate_components`, `observed_changes`, `conflicts`, `missing_fields`, `evidence_quality`, `data_freshness`. Every entry carries `evidence_id`, `source_type`, `source_record_id`, `period`, `field`, `value`, `observation`, `source_timestamp`, `data_version`. Every derived calculation carries its formula and the evidence IDs used.
Must never interpret policy or reach a conclusion. Inspects only supplied records. In the final run it returned a 22-entry ledger, and every value and source record id matched the case input.

**3 UsageAnomalyAgent** (v4)
Emits `usage_pattern`, `comparison_periods`, `anomalies`, `supported_explanations`, `unsupported_hypotheses`, `confidence`, `required_additional_evidence`. Anomalies carry `anomaly_id`, `period`, `observation`, `magnitude_description`, `supporting_evidence_ids`, `confidence`.
Confidence is HIGH, MEDIUM, LOW or INSUFFICIENT. Fabricated numeric probabilities are forbidden.
The split between supported explanations and unsupported hypotheses is the structural device that keeps "the meter might be broken" in the second list where it belongs.

**4 PolicyKnowledgeAgent** (v6, strict schema)
Emits `policy_ledger`, `policy_constraints`, `policy_conflicts`, `adjustment_eligibility`, `required_customer_disclosures`, `required_human_approval`, `missing_policy`. Each reference carries `policy_id`, `policy_version`, `section`, `rule`, `applies_to`, `effect_on_resolution`.
Must never invent a policy. Missing policy for a governed action and any policy conflict both force HUMAN_REVIEW_REQUIRED. In the final run it mapped nine policies, all of which exist in the governed synthetic policy set.

**5 ResolutionPlannerAgent** (v6)
Emits `resolution_status`, `root_cause_classification`, `supported_findings`, `uncertainties`, `recommended_actions`, `customer_adjustment`, `claim_ledger`, `evidence_ids`, `policy_ids`, `confidence`, `reasoning_summary`, `human_review_reason`, `correction_count`.
`reasoning_summary` must be concise conclusions, not exposed chain of thought.
Ends with one line, `CASE_FOLLOWUP::HUMAN_REQUIRED` or `CASE_FOLLOWUP::NONE_REQUIRED`. The workflow reads it after a message is approved, and defaults to a human handoff unless the token is exactly NONE_REQUIRED.
Must never approve its own plan.

**6 CustomerCommunicationAgent** (v5, strict schema)
Emits `customer_summary`, `what_we_reviewed`, `what_we_found`, `why_bill_changed`, `what_happens_next`, `customer_action_needed`, `internal_claim_ids`, `internal_evidence_ids`, `internal_policy_ids`, `communication_risk_flags`, `required_disclosures_included`.
Must never introduce a claim absent from the claim ledger. Internal IDs are carried for audit and kept out of customer-facing text.
Output runs with `autoSend: false`. After approval the workflow releases the six customer-facing fields as readable text, never the JSON and never the internal IDs.

**7 EvidenceComplianceAgent** (v6)
Consumes the complete case state including all three ledgers and `correction_count`.
Emits `decision`, `failure_category`, `failed_checks`, `unsupported_claim_ids`, `unsupported_claims`, `missing_evidence`, `missing_policy`, `correction_target`, `correction_instructions`, `human_review_required`, `compliance_summary`, `correction_count`, `next_case_state`, then the mandatory route token line.
Decisions: APPROVE, REJECT_AND_REPLAN, REJECT_AND_REWRITE, HUMAN_REVIEW_REQUIRED.
HUMAN_REVIEW_REQUIRED is mandatory at `correction_count >= 2`, on policy conflict, missing governed policy, real-data contamination, unsupported financial commitment, LOW or INSUFFICIENT material confidence, or legal and regulatory concern.
The decision object and its reasons are required on every route. The token line alone is never a complete response, and the gate escalates if the object is missing.
It answers one question, whether this message is safe to release. Whether the case still needs a person is decided separately by the workflow, so a safe message is not rejected merely because follow-up is open.
**Must never approve an unsupported material claim.**

**8 EscalationCoordinatorAgent** (v5)
Emits `escalation_reason`, `risk_class`, `evidence_summary`, `policy_summary`, `unresolved_questions`, `recommended_reviewer`, `recommended_review_actions`, `customer_safe_interim_message`, and `decision_card` containing `decision_needed`, `known_facts`, `unknowns`, `applicable_policies`, `risk`, `recommended_next_step`.
Invoked on either human route: when the message is withheld, or after release when the case still needs a person. The workflow tells it which.
Must keep the AI recommendation visibly separate from established facts, and must never decide on the human's behalf.

**9 CaseAuditAgent** (v7, strict schema)
Emits `participating_agents` (each with `agent_name`, `agent_version`, `output_status`), `triage_result`, `evidence_ids`, `claim_ids`, `policy_ids`, `resolution_status`, `compliance_route_token`, `message_compliance_decision`, `compliance_reasons`, `correction_count`, `correction_history`, `case_human_review_status`, `human_review_status`, `escalation`, `final_disposition`, `audit_completeness`, `missing_audit_information`, `audit_notes`, `execution_status`, `record_basis`.
It reads the compliance route token before it states a decision, and records every agent version, its own included, as NOT_OBSERVED, because an agent cannot see platform metadata. The platform record, not the audit, is the source of truth for versions, route, delivery and tokens.
`audit_completeness`: COMPLETE or INCOMPLETE. `execution_status`: CONFIGURED, PREPARED_NOT_EXECUTED, RUNTIME_EXECUTED, RUNTIME_FAILED or PRODUCTION_TARGET.
Must never report RUNTIME_EXECUTED for a configuration review, a dry run or an empty conversation, and must never invent a successful execution.

---

## Contract corrections applied in this pass

Ledger naming was inconsistent: AccountEvidenceAgent emitted `evidence_records` and PolicyKnowledgeAgent emitted `applicable_policies`, while EvidenceComplianceAgent was instructed to verify `evidence_ledger` and `policy_ledger`. Compliance could have reported missing ledgers for the wrong reason and escalated on a naming mismatch rather than a real failure. Both producers now emit the canonical names.

CaseAuditAgent's `execution_status` enum had no value meaning the case actually ran, so a successful demonstration would have recorded itself as not executed. RUNTIME_EXECUTED and RUNTIME_FAILED were added, with explicit rules against claiming a run that did not happen.

All nine agents referenced `workflow_target=GridResolveAIWorkflow v3` while the deployed workflow was v4. Updated at the time. CaseTriageAgent and UsageAnomalyAgent still carry a stale descriptive header naming v5. It is inert text, and republishing two healthy agents before the final run was judged the larger risk.

## Contract corrections after the real runs

Run 1 and run 2 showed specialists stopping without working, a compliance verdict with no reasons, and an audit record that misstated the run. In response: every agent now receives an explicit input message, AccountEvidenceAgent, PolicyKnowledgeAgent and CaseAuditAgent gained strict output schemas, EvidenceComplianceAgent must record its reasons, and CaseAuditAgent may state no version. The compliance agent's twenty checks, four decisions and token rules were left byte-identical. Full record: `docs/V10_CORRECTIONS_2026-09-20.md`.
