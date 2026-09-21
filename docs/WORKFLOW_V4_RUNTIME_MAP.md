# Workflow v4 Runtime Map

Source: workflow YAML read via API (evidence/pre-run/PRE03-workflow-v4.yaml). Workflow: GridResolveAIWorkflow, version 4, trigger OnConversationStart. Agents are invoked by name (latest version), sharing one conversation (`conversationId = System.ConversationId`), each with autoSend output.

## CONFIGURED_AND_RUNNABLE (actual nodes, in order)
1. CaseTriageAgent
2. AccountEvidenceAgent
3. UsageAnomalyAgent
4. PolicyKnowledgeAgent
5. ResolutionPlannerAgent
6. CustomerCommunicationAgent
7. EvidenceComplianceAgent (output captured into Local.Var1497)
8. ConditionGroup:
   - IF `Not("APPROVE" in Local.Var1497)` THEN EscalationCoordinatorAgent
   - ELSE (condition "true") no action
9. CaseAuditAgent (runs on both paths)

Terminal paths: approved = 1..7, 9. Not approved = 1..7, EscalationCoordinator, 9.

## PREPARED_NOT_RUNTIME_WIRED (do not claim as runtime)
- Parallel fan-out and join (steps 2 to 4 run sequentially)
- Typed routing on the four compliance decisions (only APPROVE vs not)
- Automatic REJECT_AND_REWRITE and REJECT_AND_REPLAN loops, correction_count enforcement outside agent text
- Second-order human decision step (escalation agent only produces a decision card)
- Any tool, knowledge, or gateway integration

## Risk: branch condition is a substring test (NOT yet observed at runtime)
Var1497 holds the compliance agent's full output (a JSON object with free-text fields such as compliance_summary). "APPROVE" is matched as a substring. In Power Fx the `in` operator on text is, to my knowledge, case-insensitive (unverified here). A rejection whose text contains "approve" (for example "cannot approve unsupported claim") would evaluate as approved and skip EscalationCoordinatorAgent, going straight to CaseAuditAgent. The audit agent still records the disposition, but the escalation step would not run.
Impact on demo: the run may or may not hit this. The report must describe what actually happens.
Candidate minimal fix (NOT applied, cannot be tested without a paid run): compare a parsed decision field instead of a substring. Needs approval since it edits the workflow.
Also: Var1497 may be a message object rather than plain text, which also affects the test. Unknown until run.

## Not enforced by workflow
Nothing withholds the customer message: every agent's output is autoSent to the conversation, including the draft from CustomerCommunicationAgent before compliance runs. Describe compliance as an independent review recorded in the case, not a network-level release gate.
