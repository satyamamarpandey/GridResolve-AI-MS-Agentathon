"""
Parity check: the final real Foundry run, replayed through Microsoft Agent Framework.

I take the nine genuine agent outputs of the final run (workflow v10, 2026-09-21),
hand them to the open-source declarative workflow engine from Microsoft Agent
Framework (NuGet: Microsoft.Agents.AI.Workflows.Declarative) as scripted replies,
run the same v10 YAML locally, and compare what the local engine did with what the
hosted Foundry service recorded.

No network, no Azure call, no model request, no cost. The evidence folder is read,
never written. This is a local migration proof. It is not a deployment, and it is
not Foundry execution evidence.

Needs the .NET SDK. Run: python migration/agent_framework/parity_check.py
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tests", "workflow_engine"))

import test_workflow_engine as harness  # noqa: E402
from runner import workflow_map as wm  # noqa: E402

FINAL_RUN = os.path.join(ROOT, "evidence", "runtime", "20260921T000142Z_SYN-CASE-4003_c2be2b51")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "parity_result.json")
NOT_AGENT_ACTIONS = ("node-release-approved-message", "node-followup-handoff")
# Branches the hosted final run did not take: fail-closed escalation, and the no-follow-up record.
UNTAKEN_ACTIONS = ("if-node-failclosed-escalate", "node-1789697115060", "if-node-no-human-followup",
                   "node-record-no-followup")

results = []


def check(name, passed, detail=""):
    results.append({"check": name, "passed": bool(passed), "detail": detail})
    print("  [%s] %-70s %s" % ("PASS" if passed else "FAIL", name, detail))


def load(name):
    with open(os.path.join(FINAL_RUN, name), encoding="utf-8") as handle:
        return json.load(handle)


def main():
    before = {n: os.path.getmtime(os.path.join(FINAL_RUN, n)) for n in os.listdir(FINAL_RUN)}
    scenario = harness.real_run_scenario(FINAL_RUN)
    hosted_route = load("09_route.json")
    hosted_actions = load("04_workflow_actions.json")
    with open(os.path.join(FINAL_RUN, "08_output.txt"), encoding="utf-8") as handle:
        hosted_output = handle.read()

    dll = harness.build()
    local = harness.run_engine(dll, tempfile.mkdtemp(prefix="gridresolve_parity_"), "v10", scenario)

    print("\nFINAL RUN, HOSTED FOUNDRY SERVICE AGAINST LOCAL AGENT FRAMEWORK ENGINE")
    check("the local engine ran the v10 definition without a failed action", local["failed"] == [],
          str(local["failed"])[:80])
    recorded = [i for i in load("07_conversation_items.json")["data"]
                if i.get("role") == "assistant" and i.get("created_by", {}).get("agent", {}).get("name") in scenario["agents"]]
    recorded_text = {i["created_by"]["agent"]["name"]: "".join(c.get("text", "") for c in i.get("content", []))
                     for i in recorded}
    genuine = [n for n, text in scenario["agents"].items() if recorded_text.get(n) == text]
    check("all nine scripted replies equal the text the platform stored for that agent", len(genuine) == 9,
          "%d of %d" % (len(genuine), len(scenario["agents"])))
    check("same nine agents, same order", local["invoked"] == hosted_route["agents_observed"],
          "%d local, %d hosted" % (len(local["invoked"]), len(hosted_route["agents_observed"])))

    hosted_ids = []
    for action in hosted_actions:
        if action["action_id"] not in hosted_ids:
            hosted_ids.append(action["action_id"])
    local_shared = [a for a in local["executed"] if a in hosted_ids]
    check("every action the hosted service reported also ran locally", set(hosted_ids) <= set(local["executed"]),
          str(set(hosted_ids) - set(local["executed"])))
    check("those actions ran in the same order", local_shared == hosted_ids)
    for action in NOT_AGENT_ACTIONS:
        check("both took the branch through %s" % action, action in hosted_ids and action in local["executed"])
    untaken = [a for a in UNTAKEN_ACTIONS if a in local["executed"]]
    check("the local engine took no branch the hosted run skipped", untaken == [], str(untaken))

    draft = json.loads(scenario["agents"]["CustomerCommunicationAgent"])
    expected = wm.compose_customer_message(draft)
    check("the local engine released exactly one customer message", len(local["sent"]) >= 1 and
          sum(1 for s in local["sent"] if s.strip() == expected.strip()) == 1)
    check("that message is character for character what the hosted service released",
          expected.strip() in hosted_output and any(s.strip() == expected.strip() for s in local["sent"]),
          "%d characters" % len(expected))

    after = {n: os.path.getmtime(os.path.join(FINAL_RUN, n)) for n in os.listdir(FINAL_RUN)}
    check("the evidence folder was not touched", before == after)

    passed = sum(1 for r in results if r["passed"])
    summary = {
        "what_this_is": "Local parity check of the final real run against Microsoft Agent Framework's declarative engine. Scripted agents, no model, no Azure call. Not Foundry execution evidence.",
        "engine_package": "Microsoft.Agents.AI.Workflows.Declarative",
        "definition": "tests/workflow_engine/workflows/GridResolveAIWorkflow_v10.yaml",
        "replayed_from": os.path.relpath(FINAL_RUN, ROOT).replace("\\", "/"),
        "passed": passed, "total": len(results), "checks": results,
        "local_sent_messages": len(local["sent"]), "local_invoked": local["invoked"],
    }
    with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(summary, indent=1) + "\n")
    print("\n%d of %d parity checks passed" % (passed, len(results)))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
