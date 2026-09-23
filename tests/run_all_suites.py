"""Run every local suite and print one table. No model call, no network.

Each suite is a script that prints a final line of the form
``RESULT: <n> passed, <m> failed``. The Control Center suite is vitest and is
parsed from its own summary line. Nothing here is hardcoded: a suite that
cannot be read is reported as such and fails the run, so a broken runner cannot
look like a pass.

    python tests/run_all_suites.py            # everything
    python tests/run_all_suites.py --fast     # skip the two .NET engine suites
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PYTHON_SUITES = (
    ("Routing and case data", "tests/test_routing_and_data.py"),
    ("Synthetic data integrity", "tests/validate_synthetic_data.py"),
    ("Foundry runner", "tests/test_foundry_runner.py"),
    ("Evaluation package", "tests/test_evaluation_package.py"),
    ("Integration contracts", "tests/test_integration_contracts.py"),
    ("Escalation reason codes", "tests/test_escalation_reason_codes.py"),
    ("Scenario cases", "tests/test_scenario_cases.py"),
    ("Supervisor feedback", "tests/test_supervisor_feedback.py"),
    ("Evaluation v2.1", "tests/test_evaluation_v2_1.py"),
)
ENGINE_SUITES = (
    ("Workflow engine v10", "tests/test_workflow_engine.py"),
    ("Workflow engine v11", "tests/test_workflow_engine_v11.py"),
)
RESULT = re.compile(r"RESULT:\s*(\d+)\s*passed,\s*(\d+)\s*failed")
VITEST = re.compile(r"(?m)^\s*Tests\s+(?:(\d+) failed \| )?(\d+) passed")


def run_python(path: str) -> tuple[int, int] | None:
    if not os.path.isfile(os.path.join(ROOT, path)):
        return None
    done = subprocess.run([sys.executable, path], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    match = RESULT.search(done.stdout + done.stderr)
    return (int(match.group(1)), int(match.group(2))) if match else None


def run_vitest() -> tuple[int, int] | None:
    app = os.path.join(ROOT, "control-center")
    vitest = os.path.join(app, "node_modules", "vitest", "vitest.mjs")
    if not os.path.isfile(vitest):
        return None
    env = {**os.environ, "NO_COLOR": "1", "FORCE_COLOR": "0", "CI": "1"}
    done = subprocess.run(["node", vitest, "run", "--reporter=default"], cwd=app,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env)
    match = VITEST.search(done.stdout + done.stderr)
    if not match:
        return None
    return (int(match.group(2)), int(match.group(1) or 0))


def main(argv: list[str]) -> int:
    fast = "--fast" in argv
    rows: list[tuple[str, tuple[int, int] | None]] = []
    suites = PYTHON_SUITES + (() if fast else ENGINE_SUITES)
    for name, path in suites:
        print("  running %-28s" % name, end="", flush=True)
        result = run_python(path)
        print(" done" if result else " UNREADABLE")
        rows.append((name, result))
    print("  running %-28s" % "Control Center", end="", flush=True)
    app = run_vitest()
    print(" done" if app else " UNREADABLE")
    rows.append(("Control Center", app))

    print()
    passed = failed = 0
    unreadable = []
    for name, result in rows:
        if result is None:
            unreadable.append(name)
            print("  %-28s could not read result" % name)
            continue
        passed += result[0]
        failed += result[1]
        print("  %-28s %5d passed, %d failed" % (name, result[0], result[1]))
    print("  %s" % ("-" * 50))
    print("  %-28s %5d passed, %d failed" % ("TOTAL", passed, failed))
    ok = failed == 0 and not unreadable
    print("\n  %s" % ("ALL LOCAL SUITES PASS" if ok else "SUITE FAILURE"))
    print("  No model call. No workflow execution. Azure cost: $0.00")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
