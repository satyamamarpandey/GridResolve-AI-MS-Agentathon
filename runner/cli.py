"""Command line interface for the Foundry workflow runner.

Safety model, in one place:

    python -m runner preflight    free. The default. Makes no model request.
    python -m runner verify-api   free. Read-only GETs against the endpoint.
    python -m runner report       free. Retrieves a run that already exists.
    python -m runner analyze      free. Offline. Re-reads a run's evidence files.
    python -m runner execute      BILLABLE. Requires --confirm and --max-usd.

`execute` is the only command that can spend money, and it refuses to run
without the exact confirmation phrase, an explicit cap, and a clean run ledger.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from . import analysis
from . import case as case_mod
from . import config as cfg
from . import evidence as ev
from . import execute as ex
from . import foundry, pricing
from .redaction import Redactor, for_config
from .transport import TransportError

RULE = "=" * 68


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m runner",
        description="Execute and inspect GridResolve AI workflow runs on "
                    "Microsoft Foundry. The default command makes no model "
                    "request and cannot bill.")
    subs = parser.add_subparsers(dest="command")

    for name, help_text in (
            ("preflight", "validate the case and estimate cost, free"),
            ("verify-api", "probe the endpoint with read-only GETs, free")):
        sub = subs.add_parser(name, help=help_text)
        sub.add_argument("--case", default="SYN-CASE-4003",
                         choices=case_mod.available_cases())
        sub.add_argument("--max-usd", type=float, default=None,
                         help="the cap a run would be held to")

    run = subs.add_parser("execute", help="BILLABLE: run the workflow once")
    run.add_argument("--case", default="SYN-CASE-4003",
                     choices=case_mod.available_cases())
    run.add_argument("--confirm", required=True,
                     help="must be exactly: " + ex.CONFIRM_PHRASE)
    run.add_argument("--max-usd", type=float, required=True,
                     help="approved spending cap for this run, in USD")
    run.add_argument("--allow-additional-run", action="store_true",
                     help="permit a further billable run for a case that has "
                          "already been run")
    run.add_argument("--accept-known-defects", action="store_true",
                     help="run even though the live configuration has known "
                          "defects that undermine the result")
    run.add_argument("--deadline-seconds", type=float,
                     default=ex.DEFAULT_DEADLINE_SECONDS)
    run.add_argument("--poll-seconds", type=float, default=ex.DEFAULT_POLL_SECONDS)

    rep = subs.add_parser("report", help="retrieve an existing run, free")
    rep.add_argument("--response-id", required=True)
    rep.add_argument("--conversation-id", default="",
                     help="also list the conversation items of that run")

    ana = subs.add_parser("analyze", help="re-read a finished run's evidence "
                                          "files, offline, free")
    ana.add_argument("--run-dir", required=True,
                     help="an evidence/runtime/<run> directory. Never modified.")
    return parser


def _print_preflight(checks: ex.Preflight) -> None:
    print("\n" + RULE)
    print("  PREFLIGHT, no model request was made")
    print(RULE)
    print("\n  Case         %s" % checks.case_id)
    print("  Source       %s" % checks.case_path)
    print("  sha256       %s" % checks.case_sha256)
    print("  Endpoint     %s" % checks.endpoint)
    print("  Prior runs   %d" % checks.prior_attempt_count)

    print("\n  Request that `execute` would send:\n")
    for line in checks.request_preview.splitlines():
        print("    " + line)

    print("\n  Estimated cost. Assumed token counts, never measured:\n")
    print("    %-14s %10s %10s %10s" % ("scenario", "input", "output", "USD"))
    for s in checks.scenarios:
        print("    %-14s %10d %10d %10.4f"
              % (s.name, s.input_tokens, s.output_tokens, s.usd))
    print("\n    %s" % pricing.PRICE_SOURCE)
    if checks.cap_usd is not None:
        print("\n  Cap supplied $%.2f against a modelled worst case of $%.2f"
              % (checks.cap_usd, checks.worst_case_usd))

    print()
    if checks.can_execute:
        print("  READY. No request has been sent. To run it, add:")
        print('    execute --confirm "%s" --max-usd <cap>' % ex.CONFIRM_PHRASE)
    else:
        print("  BLOCKED. `execute` would refuse:")
        for b in checks.blockers:
            print("    - " + b)
    print(RULE + "\n")


def _cmd_preflight(args: argparse.Namespace) -> int:
    config = cfg.from_env()
    checks = ex.preflight(config, args.case, args.max_usd)
    _print_preflight(checks)
    return 0


def _cmd_verify_api(args: argparse.Namespace) -> int:
    """Read-only confirmation that the execution routes exist.

    A GET against a route that exists returns data or a parameter error. A route
    that does not exist returns 404. Neither can invoke a model.
    """
    config = cfg.from_env()
    client = foundry.FoundryAgentClient(config)
    redactor = for_config(config)
    print("\n" + RULE)
    print("  API SURFACE, read-only GETs, no model request")
    print(RULE + "\n")
    ok = True
    try:
        blockers = ex.live_blockers(client)
        for b in blockers:
            ok = False
            print("  [FAIL] %s" % redactor.text(b))
        if not blockers:
            print("  [PASS] %-40s v%s, enabled, not a draft"
                  % ("live workflow is the reviewed version",
                     ex.workflow_map.WORKFLOW_VERSION))
        for d in ex.configuration_defects(client, args.case):
            ok = False
            print("  [FAIL] %s" % redactor.text(d))
        listed = client.list_responses()
        count = len(listed.get("data", [])) if isinstance(listed, dict) else -1
        print("  [PASS] %-40s %d existing response(s) in the project"
              % ("responses route reachable", count))
    except TransportError as exc:
        ok = False
        print("  [FAIL] %s" % redactor.text(str(exc)))
    print("\n" + RULE + "\n")
    return 0 if ok else 1


def _cmd_report(args: argparse.Namespace) -> int:
    config = cfg.from_env()
    client = foundry.FoundryAgentClient(config)
    redactor = for_config(config)
    response = redactor.data(client.get_response(args.response_id))
    usage = pricing.usage_from_response(response)
    print("\n  status  %s" % foundry.status_of(response))
    if usage.reported:
        print("  tokens  in %d, out %d, total %d"
              % (usage.input_tokens, usage.output_tokens, usage.total_tokens))
        print("  cost    $%.4f" % usage.usd)
    else:
        print("  tokens  not reported by the API for this response")
    print("  text    %s" % (ex.extract_output_text(response)[:400] or "none"))
    if args.conversation_id:
        items = redactor.data(client.get_conversation_items(args.conversation_id))
        data = items.get("data", []) if isinstance(items, dict) else []
        print("  items   %d conversation item(s)" % len(data))
    print()
    return 0


def _cmd_analyze(args: argparse.Namespace) -> int:
    """Offline. Reads evidence files and prints. Writes nothing."""
    try:
        result = analysis.analyze_run_dir(args.run_dir)
    except (OSError, ValueError) as exc:
        raise ev.SafetyError("That run directory could not be read: %s" % exc)
    print(json.dumps(result, indent=2))
    return 0


def _cmd_execute(args: argparse.Namespace) -> int:
    config = cfg.from_env()
    result = ex.execute_once(
        config, args.case, cap_usd=args.max_usd, confirm_phrase=args.confirm,
        allow_additional=args.allow_additional_run,
        accept_known_defects=args.accept_known_defects,
        poll_seconds=args.poll_seconds, deadline_seconds=args.deadline_seconds)
    print("\n" + ex.usage_report(result))
    print("  Evidence written to %s\n" % result.run_dir)
    return 1 if result.over_cap or result.status != "completed" else 0


def _harden_console() -> None:
    """Never let an unencodable character crash the process after a billed run.

    Model output can contain characters a Windows console code page cannot
    encode. Evidence files are written as UTF-8 before anything is printed, so
    nothing would be lost, but a traceback at that moment would look like a
    failed run and invite a second one.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(errors="replace")
            except (ValueError, OSError):
                pass


def main(argv: Sequence[str] | None = None) -> int:
    _harden_console()
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    handlers = {
        None: _cmd_preflight,
        "preflight": _cmd_preflight,
        "verify-api": _cmd_verify_api,
        "report": _cmd_report,
        "analyze": _cmd_analyze,
        "execute": _cmd_execute,
    }
    if args.command is None:
        args.case = "SYN-CASE-4003"
        args.max_usd = None
    try:
        return handlers[args.command](args)
    except (cfg.ConfigError, case_mod.CaseError, ev.SafetyError) as exc:
        print("\n  REFUSED: %s\n" % _safe(exc), file=sys.stderr)
        return 2
    except TransportError as exc:
        print("\n  FAILED: %s\n" % _safe(exc), file=sys.stderr)
        return 3


def _safe(exc: BaseException) -> str:
    """Redact an error before it reaches the terminal.

    Service error bodies and TLS failures can echo the request host, which
    carries the resource name. A terminal is as publishable as a file once it
    is screenshotted, so errors get the same treatment as evidence.
    """
    text = str(exc)
    try:
        return for_config(cfg.from_env()).text(text)
    except cfg.ConfigError:
        return Redactor("", "").text(text)
