"""
Live Foundry configuration verification. Read-only control plane calls only.
No model invocation, no workflow execution, no cost.

Requires: az CLI logged in, and the Foundry resource identified by environment
variables so that no tenant-specific identifier is committed to this repository.

    set GRIDRESOLVE_FOUNDRY_RESOURCE=<your-resource-name>
    set GRIDRESOLVE_FOUNDRY_PROJECT=<your-project-name>

Run: python tests/verify_live_config.py
"""
import json
import os
import re
import subprocess
import sys
import urllib.request

AZ = os.environ.get(
    "GRIDRESOLVE_AZ_PATH",
    r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd",
)
RESOURCE = os.environ.get("GRIDRESOLVE_FOUNDRY_RESOURCE")
PROJECT = os.environ.get("GRIDRESOLVE_FOUNDRY_PROJECT")
if not RESOURCE or not PROJECT:
    sys.exit(
        "Set GRIDRESOLVE_FOUNDRY_RESOURCE and GRIDRESOLVE_FOUNDRY_PROJECT before "
        "running. These are deliberately not committed, because this repository "
        "is public and a resource name is a tenant-specific identifier."
    )
BASE = "https://%s.services.ai.azure.com/api/projects/%s" % (RESOURCE, PROJECT)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXPECTED_AGENTS = {
    "CaseTriageAgent": 5, "AccountEvidenceAgent": 9, "UsageAnomalyAgent": 4,
    "PolicyKnowledgeAgent": 6, "ResolutionPlannerAgent": 6,
    "CustomerCommunicationAgent": 5, "EvidenceComplianceAgent": 6,
    "EscalationCoordinatorAgent": 5, "CaseAuditAgent": 7,
}
EXPECTED_WORKFLOW_VERSION = "10"
APPROVED_TOKEN = "ROUTE_DECISION::GRIDRESOLVE_APPROVED"

checks, fails = [], []


def ok(name, cond, detail=""):
    (checks if cond else fails).append((name, detail))
    print("  [%s] %-52s %s" % ("PASS" if cond else "FAIL", name, detail))


def token():
    r = subprocess.run([AZ, "account", "get-access-token", "--resource",
                        "https://ai.azure.com", "--query", "accessToken", "-o", "tsv"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("az token failed. Run: az login")
        sys.exit(2)
    return r.stdout.strip()


def get(path, tok):
    req = urllib.request.Request(BASE + path, headers={
        "Authorization": "Bearer " + tok,
        "Foundry-Features": "WorkflowAgents=V1Preview"})
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def main():
    tok = token()

    print("\n1. ACTIVE WORKFLOW VERSION")
    wf = get("/agents/GridResolveAIWorkflow?api-version=v1", tok)
    latest = wf["versions"]["latest"]
    ok("workflow latest version is v%s" % EXPECTED_WORKFLOW_VERSION,
       latest["version"] == EXPECTED_WORKFLOW_VERSION, "found v" + latest["version"])
    ok("workflow agent state enabled", wf.get("state") == "enabled", wf.get("state", "?"))
    rules = wf["agent_endpoint"]["version_selector"]["version_selection_rules"]
    sel = rules[0] if rules else {}
    ok("traffic routes to @latest at 100%",
       sel.get("agent_version") == "@latest" and sel.get("traffic_percentage") == 100,
       "%s @ %s%%" % (sel.get("agent_version"), sel.get("traffic_percentage")))
    ok("latest version is not a draft", latest.get("draft") is False,
       "draft=%s status=%s" % (latest.get("draft"), latest.get("status")))

    print("\n2. WORKFLOW DEFINITION")
    y = latest["definition"]["workflow"]
    ok("entry trigger is OnConversationStart", "kind: OnConversationStart" in y)
    ok("approve branch requires the exact sentinel token", APPROVED_TOKEN in y)
    ok("old failing substring condition is gone",
       'Not("APPROVE" in' not in y)
    ok("escalation is on the default true branch",
       y.index('condition: "true"') < y.index("EscalationCoordinatorAgent"),
       "true-branch precedes escalation node")
    # SendActivity.activity is a template. The first real run showed that an
    # =expression there is delivered to the customer as literal text.
    repo_yaml = open(os.path.join(ROOT, "tests", "workflow_engine", "workflows",
                                  "GridResolveAIWorkflow_v%s.yaml"
                                  % EXPECTED_WORKFLOW_VERSION), encoding="utf-8").read()
    ok("live definition is byte-identical to the one run through the engine tests",
       y.replace("\r\n", "\n") == repo_yaml.replace("\r\n", "\n"),
       "%d chars live, %d in the repository" % (len(y), len(repo_yaml)))
    release_path = os.path.join(ROOT, "tests", "powerfx_gate", "release_v8.txt")
    release = open(release_path, encoding="utf-8").read().strip().split("\n")
    ok("release sends the six customer-facing fields, never the whole draft",
       "kind: SendActivity" in y
       and all(line.strip() in y for line in release if line.strip())
       and "Last(Local.VarCustomerDraft).Text" not in y)
    ok("the communication agent's JSON is saved for the release template",
       "responseObject: Local.VarCustomerMessage" in y)
    readable = open(os.path.join(ROOT, "tests", "powerfx_gate", "readable_v9.txt"),
                    encoding="utf-8").read().strip()
    ok("an approved draft is released only when every customer field is readable",
       "=And(" in y and readable in y)
    investigated = open(os.path.join(ROOT, "tests", "powerfx_gate", "investigated_v10.txt"),
                        encoding="utf-8").read().strip()
    ok("the whole gate is exactly And(compliance gate, six-field guard, investigation guard)",
       ("condition: '=And(" + open(os.path.join(ROOT, "tests", "powerfx_gate", "gate_v6.txt"),
                                   encoding="utf-8").read().strip()
        + ", " + readable + ", " + investigated + ")'") in y)
    ok("the investigation guard covers evidence, usage, policy and the compliance decision",
       all(('Last(%s).Text' % v) in investigated and ('"""%s"""' % k) in investigated
           for v, k in (("Local.VarEvidence", "evidence_id"), ("Local.VarUsage", "usage_summary"),
                        ("Local.VarPolicy", "policy_id"), ("Local.Var1497", "decision"))))
    ok("the investigation guard reads text only, so it cannot raise a binding error",
       "Local.VarCustomerMessage" not in investigated and "responseObject" not in investigated)
    import yaml as _yaml
    node_messages = {k: v for k, v in json.load(open(os.path.join(
        ROOT, "tests", "workflow_engine", "invocation_messages_v10.json"),
        encoding="utf-8")).items() if not k.startswith("_")}
    live_nodes = {}

    def _walk(actions):
        for act in actions:
            if act.get("kind") == "InvokeAzureAgent":
                live_nodes[act["id"]] = act
            for cond in act.get("conditions", []):
                _walk(cond.get("actions", []))
    _walk(_yaml.safe_load(y)["trigger"]["actions"])
    ok("all ten agent nodes pass the reviewed input message, none is empty",
       len(live_nodes) == 10
       and {n: a["input"]["messages"] for n, a in live_nodes.items()} == node_messages)
    ok("every input message is a plain literal, never an expression",
       not any(str(a["input"]["messages"]).startswith("=") for a in live_nodes.values()))
    ok("every agent node still shares the one conversation",
       all(a.get("conversationId") == "=System.ConversationId" for a in live_nodes.values()))
    ok("each message names the agent its node invokes",
       all(a["agent"]["name"] in a["input"]["messages"] for a in live_nodes.values()))
    old_guard = open(os.path.join(ROOT, "tests", "powerfx_gate", "readable_v8.txt"),
                     encoding="utf-8").read().strip()
    ok("the guard rejects whitespace-only fields: spaces, tabs, CR and LF, all six fields",
       old_guard not in y
       and y.count("Trim(Substitute(Substitute(Substitute(Local.VarCustomerMessage.") == 6
       and all(("Local.VarCustomerMessage.%s, Char(10), \"\"), Char(13), \"\"), Char(9), \"\")))"
                % f) in y for f in ("customer_summary", "what_we_reviewed", "what_we_found",
                                    "why_bill_changed", "what_happens_next",
                                    "customer_action_needed")))
    followup = open(os.path.join(ROOT, "tests", "powerfx_gate", "followup_v8.txt"),
                    encoding="utf-8").read().strip()
    ok("a separate human follow-up gate reads the planner, not compliance",
       "id: node-case-followup-gate" in y and followup in y
       and "Last(Local.VarPlan).Text" in y)
    ok("the follow-up gate defaults to a human handoff",
       y.index("id: if-node-no-human-followup") < y.index("id: if-node-human-followup")
       and y.index("id: if-node-human-followup") < y.index("id: node-followup-handoff"))
    ok("no SendActivity activity is written as an =expression",
       not re.search(r"""^\s*activity:\s*['"]?=""", y, re.MULTILINE))
    ok("gate reads message text, not the message table",
       "Last(Local.Var1497).Text" in y and "in Local.Var1497)" not in y)
    gate_path = os.path.join(ROOT, "tests", "powerfx_gate", "gate_v6.txt")
    tested = open(gate_path, encoding="utf-8").read().strip()
    ok("live gate is the expression tested in tests/powerfx_gate", tested in y)
    ok("gate gives the escalate token precedence",
       '!("GRIDRESOLVE_ESCALATE" in t)' in y)
    ok("seven nodes withhold output (autoSend false)",
       y.count("autoSend: false") == 7, "count=%d" % y.count("autoSend: false"))
    ok("both escalation paths and the audit remain visible (autoSend true)",
       y.count("autoSend: true") == 3, "count=%d" % y.count("autoSend: true"))
    ok("CaseAuditAgent is terminal on both paths",
       y.rindex("CaseAuditAgent") > y.rindex("EscalationCoordinatorAgent"))
    for name in EXPECTED_AGENTS:
        if name not in y:
            ok("workflow references " + name, False, "missing")
    ok("workflow references all nine agents",
       all(n in y for n in EXPECTED_AGENTS))

    print("\n3. AGENT VERSIONS AND TOOLS")
    agents = get("/agents?api-version=v1&limit=100", tok)["data"]
    by = {a["name"]: a for a in agents}
    for name, want in sorted(EXPECTED_AGENTS.items()):
        a = by.get(name)
        if not a:
            ok(name + " exists", False, "not found")
            continue
        v = a["versions"]["latest"]
        d = v["definition"]
        tools = [t.get("type") for t in d.get("tools", [])]
        schema_files = {"CustomerCommunicationAgent": "customer_message.schema.json",
                        "AccountEvidenceAgent": "evidence_ledger.schema.json",
                        "PolicyKnowledgeAgent": "policy_mapping.schema.json",
                        "CaseAuditAgent": "case_audit.schema.json"}
        if name in schema_files:
            fmt = ((d.get("text") or {}).get("format") or {})
            schema = fmt.get("schema") or {}
            shipped = json.load(open(os.path.join(
                ROOT, "tests", "workflow_engine", schema_files[name]), encoding="utf-8"))
            ok("%s returns a strict json_schema output" % name,
               fmt.get("type") == "json_schema" and fmt.get("strict") is True,
               "type=%s strict=%s" % (fmt.get("type"), fmt.get("strict")))
            ok("%s: the live schema is the shipped schema" % name,
               schema == shipped, "%d required" % len(schema.get("required", [])))
        else:
            ok("%s has no output format override" % name, not d.get("text"),
               str(d.get("text"))[:40])
        ok("%s v%d, model %s, no tools" % (name, want, d.get("model")),
           v["version"] == str(want) and not tools and d.get("model") == "gpt-5-mini",
           "v%s tools=%s" % (v["version"], tools or "none"))

    print("\n4. COMPLIANCE ROUTE TOKEN CONTRACT")
    ec = by["EvidenceComplianceAgent"]["versions"]["latest"]["definition"]["instructions"]
    ok("compliance agent is told to emit the approved token", APPROVED_TOKEN in ec)
    ok("compliance agent has an escalate token",
       "ROUTE_DECISION::GRIDRESOLVE_ESCALATE" in ec)
    ok("compliance agent must never approve unsupported claims",
       "Never approve an UNSUPPORTED material claim" in ec)
    ca = by["CaseAuditAgent"]["versions"]["latest"]["definition"]["instructions"]
    ok("audit agent can record a real run", "RUNTIME_EXECUTED" in ca)
    ae = by["AccountEvidenceAgent"]["versions"]["latest"]["definition"]["instructions"]
    pk = by["PolicyKnowledgeAgent"]["versions"]["latest"]["definition"]["instructions"]
    ok("account evidence agent is not told any case verdict",
       "SYN-CASE-4003" not in ae and "unsupported meter-fault" not in ae)
    ok("account evidence agent carries no conflicting reference figures",
       not any(x in ae for x in ("SYN-2002", "SYN-3003", "286.45", "149.20")))
    ok("supplied structured records are authoritative",
       "are the declared synthetic dataset for that case and are authoritative" in ae)
    ok("account evidence agent is told it runs unattended and must not ask",
       "AUTOMATED INVOCATION" in ae and "Never ask for confirmation" in ae)
    ok("audit agent is told it runs unattended and must not ask",
       "AUTOMATED INVOCATION" in ca and "Never ask for confirmation" in ca)
    ok("audit agent lists every pipeline agent with an output status",
       "PARTICIPATION RULES" in ca and "MISSING_OR_MALFORMED" in ca
       and all(n in ca for n in EXPECTED_AGENTS))
    ok("audit agent must not invent agent versions",
       "Never invent a version" in ca and "NOT_OBSERVED" in ca)
    ok("audit agent's metadata line no longer carries a CONFIGURED status",
       "execution_status=CONFIGURED" not in ca)
    rp = by["ResolutionPlannerAgent"]["versions"]["latest"]["definition"]["instructions"]
    cc = by["CustomerCommunicationAgent"]["versions"]["latest"]["definition"]["instructions"]
    ok("planner emits a separate fail-closed case follow-up token",
       "CASE_FOLLOWUP::HUMAN_REQUIRED" in rp and "CASE_FOLLOWUP::NONE_REQUIRED" in rp
       and "hands the case to a human by design" in rp)
    ok("planner is not told the follow-up answer for any case",
       "SYN-CASE-" not in rp)
    ok("planner and communication agent are told they run unattended",
       "AUTOMATED INVOCATION" in rp and "AUTOMATED INVOCATION" in cc)
    ok("communication agent still may not expose internal ids to the customer",
       "Do not expose internal IDs in the customer-visible fields." in cc)
    ok("audit records message approval and case human review separately",
       "TWO SEPARATE QUESTIONS" in ca
       and "A compliance APPROVE never clears case_human_review_status" in ca)
    ok("audit labels its record as model-produced, platform records take precedence",
       "MODEL_PRODUCED_FROM_CONVERSATION" in ca
       and "platform records take precedence" in ca)
    ok("audit knows the escalation agent also runs after an approved message",
       "message was approved but the case itself still needs a person" in ca)
    ok("compliance still runs all twenty checks and keeps its four decisions",
       all(("\n%d. " % n) in ec for n in range(1, 21))
       and "APPROVE, REJECT_AND_REPLAN, REJECT_AND_REWRITE, HUMAN_REVIEW_REQUIRED." in ec)
    ok("compliance route token rules are intact",
       "Emit ROUTE_DECISION::GRIDRESOLVE_APPROVED only when decision is exactly APPROVE." in ec
       and "never write both tokens" in ec
       and "If the token is missing the workflow escalates by design." in ec)
    ok("compliance must give its decision object and reasons on every route",
       "AUDITABLE DECISION" in ec and "The route token line alone is never a complete response." in ec
       and "failed_checks" in ec and "compliance_summary" in ec)
    ok("compliance separates message approval from case follow-up",
       "TWO SEPARATE QUESTIONS" in ec
       and "is this customer message safe to release" in ec
       and "only for the conditions listed under DECISION" in ec)
    ok("compliance output stays free text, because the token line follows the JSON",
       not by["EvidenceComplianceAgent"]["versions"]["latest"]["definition"].get("text"))
    ok("compliance is told no verdict for any case", "SYN-CASE-" not in ec)
    ok("audit reads the route token before it states the compliance decision",
       "COMPLIANCE RECORD" in ca and "compliance_route_token" in ca
       and "ESCALATED_WITHOUT_DECISION_OBJECT" in ca
       and "Never infer the decision from the wording of the customer message" in ca)
    ok("audit judges participation and output status from the WORKFLOW STEP markers",
       "begins WORKFLOW STEP" in ca and "a promise of later work, a bare token" in ca)
    ok("audit may state no agent version, its own included",
       "yourself included" in ca and "is not an agent version" in ca
       and "unless an upstream output explicitly states its own version" not in ca)
    ok("evidence and policy agents are told their output format is enforced",
       "The output format is enforced by a JSON schema." in ae
       and "The output format is enforced by a JSON schema." in pk
       and "AUTOMATED INVOCATION" in pk and "execution_status=CONFIGURED" not in pk)
    es = by["EscalationCoordinatorAgent"]["versions"]["latest"]["definition"]["instructions"]
    ok("escalation agent is told it runs unattended and must not ask",
       "AUTOMATED INVOCATION" in es and "Never ask for confirmation" in es)
    ok("escalation agent's metadata line carries no stale version or CONFIGURED status",
       "execution_status=CONFIGURED" not in es and "GridResolveAIWorkflow v5" not in es)
    ok("escalation agent still prepares the package and never makes the human decision",
       "never make the human decision, authorize an adjustment" in es
       and "Keep AI recommendation visibly separate from human authorization." in es
       and "final_disposition=PENDING_HUMAN_REVIEW" in es)
    ok("escalation agent keeps its triggers, reviewer routing and fail-safe reviewer",
       all(x in es for x in ("TRIGGERS", "unresolved meter allegation", "REVIEWER ROUTING",
                             "Billing Supervisor", "Meter Operations Specialist",
                             "choose Compliance Reviewer", "do not guess",
                             "Include evidence and policy IDs")))
    ok("escalation agent is not told any case verdict", "SYN-CASE-" not in es)
    ok("canonical ledger names in use",
       "evidence_ledger" in ae and "policy_ledger" in pk)

    print("\n5. SYNTHETIC INPUT")
    p = os.path.join(ROOT, "submission", "SYN-CASE-4003_input.json")
    case = json.load(open(p, encoding="utf-8"))
    ok("input file parses", True)
    ok("case id is SYN-CASE-4003", case["case_id"] == "SYN-CASE-4003")
    ok("marked synthetic only", case.get("data_classification") == "SYNTHETIC_ONLY")
    # Agents preserve workflow_version from shared state, so this label is what
    # the terminal audit record will carry. It must name the live version.
    ok("case input labels the live workflow version",
       case.get("workflow_version")
       == "GridResolveAIWorkflow v" + latest["version"],
       "%s, live v%s" % (case.get("workflow_version"), latest["version"]))
    blob = json.dumps(case).casefold()
    ok("no expected answer leaked into the input",
       not any(k in blob for k in ("expected", "must_not", "no_supported_root_cause")))
    rec = case["synthetic_account_records"]
    rate = rec["rate_components"]
    okmath = all(
        round(b["kwh_billed"] * rate["energy_charge_usd_per_kwh"]
              + rate["fixed_charge_usd_per_period"], 2) == b["amount_usd"]
        for b in rec["billing_history"])
    ok("billing arithmetic is consistent", okmath)
    ok("meter failure is unsupported by the evidence",
       rec["meter_events"] == [] and rec["diagnostic_records"][0]["result"] == "PASS"
       and rec["diagnostic_records"][0]["register_fault_flag"] is False)

    print("\n" + "=" * 68)
    print("RESULT: %d passed, %d failed" % (len(checks), len(fails)))
    print("=" * 68)
    if fails:
        print("\nNO-GO. Blockers:")
        for n, d in fails:
            print("  - %s %s" % (n, d))
        sys.exit(1)
    print("\nAll live configuration checks passed.")
    print("This verifies CONFIGURATION ONLY, with read-only calls. It runs no model and is")
    print("not execution evidence. The three real runs, on 2026-09-20, used v6, v9 and")
    print("v%s. See evidence/runtime." % EXPECTED_WORKFLOW_VERSION)
    return 0


if __name__ == "__main__":
    sys.exit(main())
