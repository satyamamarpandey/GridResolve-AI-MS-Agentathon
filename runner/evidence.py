"""Structured capture of what a run actually did.

Everything written here passes through the redactor first, so no access token
and no tenant identifier reaches a file that could be committed or screenshotted.

The run ledger is written before the billable request is sent, not after. If the
process dies mid-run, the ledger still records that a request was attempted, so
a later run cannot be started in the belief that nothing has happened yet.
"""
from __future__ import annotations

import json
import os
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterator

from .redaction import Redactor

RUNTIME_DIR = os.path.join("evidence", "runtime")
LEDGER_NAME = "RUN_LEDGER.json"
LOCK_NAME = "RUN_LEDGER.lock"


class SafetyError(RuntimeError):
    """A guard refused to proceed."""


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class EvidenceWriter:
    """Writes redacted artefacts into one run directory."""

    directory: str
    redactor: Redactor

    def ensure(self) -> None:
        os.makedirs(self.directory, exist_ok=True)

    def write_json(self, name: str, payload: Any) -> str:
        self.ensure()
        path = os.path.join(self.directory, name)
        safe = self.redactor.data(payload)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(safe, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        return path

    def write_text(self, name: str, text: str) -> str:
        self.ensure()
        path = os.path.join(self.directory, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.redactor.text(text))
        return path

    def append_jsonl(self, name: str, record: Any) -> str:
        self.ensure()
        path = os.path.join(self.directory, name)
        with open(path, "a", encoding="utf-8") as fh:
            json.dump(self.redactor.data(record), fh, ensure_ascii=False)
            fh.write("\n")
        return path


def ledger_path(root: str) -> str:
    return os.path.join(root, RUNTIME_DIR, LEDGER_NAME)


def read_ledger(root: str) -> list[dict]:
    path = ledger_path(root)
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise SafetyError(
            "The run ledger at %s could not be read (%s). Refusing to start a "
            "billable run while the record of previous runs is unreadable."
            % (path, exc)) from exc
    return data if isinstance(data, list) else []


def prior_attempts(root: str, case_id: str) -> list[dict]:
    return [e for e in read_ledger(root) if e.get("case_id") == case_id]


@contextmanager
def _ledger_lock(root: str) -> Iterator[None]:
    """Exclusive lock around every ledger read-modify-write.

    O_CREAT | O_EXCL is atomic on the filesystem, so two processes started in
    the same instant cannot both pass the "has this case run" check. A lock left
    behind by a crash blocks further runs on purpose: the state of the previous
    attempt is unknown, and that must be looked at by a person, not skipped.
    """
    path = os.path.join(root, RUNTIME_DIR, LOCK_NAME)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise SafetyError(
            "Another run holds the ledger lock at %s, or a previous run crashed "
            "while holding it. Refusing to start a billable run. Confirm no run "
            "is in progress, check the Foundry portal for an unrecorded run, "
            "then delete the lock file." % path) from exc
    try:
        os.write(handle, utc_iso().encode("utf-8"))
        os.close(handle)
        yield
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def claim_run_slot(root: str, case_id: str, run_dir: str,
                   allow_additional: bool) -> dict:
    """Record the intent to spend, before spending.

    Refuses a second run for the same case unless the operator opts in, so a
    repeated command or a re-run of a script cannot quietly bill twice. The
    check and the write happen under one exclusive lock.
    """
    with _ledger_lock(root):
        return _claim_locked(root, case_id, run_dir, allow_additional)


def _claim_locked(root: str, case_id: str, run_dir: str,
                  allow_additional: bool) -> dict:
    existing = prior_attempts(root, case_id)
    if existing and not allow_additional:
        last = existing[-1]
        raise SafetyError(
            "%s already has %d recorded run attempt(s), the most recent at %s "
            "(%s). Refusing to run again. Pass --allow-additional-run only if a "
            "further billable run is intended."
            % (case_id, len(existing), last.get("started_at", "unknown"),
               last.get("run_dir", "unknown")))

    entry = {
        "case_id": case_id,
        "started_at": utc_iso(),
        "run_dir": os.path.relpath(run_dir, root).replace("\\", "/"),
        "outcome": "ATTEMPT_RECORDED_BEFORE_REQUEST",
    }
    path = ledger_path(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    entries = read_ledger(root) + [entry]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(entries, fh, indent=2)
        fh.write("\n")
    return entry


def close_run_slot(root: str, run_dir: str, outcome: str,
                   detail: str = "") -> None:
    """Update the ledger entry for this run directory with its outcome."""
    path = ledger_path(root)
    key = os.path.relpath(run_dir, root).replace("\\", "/")
    with _ledger_lock(root):
        updated = [
            dict(e, outcome=outcome, finished_at=utc_iso(), detail=detail)
            if e.get("run_dir") == key and e.get("outcome",
                                                 "").startswith("ATTEMPT_RECORDED")
            else e
            for e in read_ledger(root)
        ]
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(updated, fh, indent=2)
            fh.write("\n")


def new_run_dir(root: str, case_id: str, stamp: str | None = None) -> str:
    """A directory name that two runs in the same second cannot share."""
    unique = uuid.uuid4().hex[:8]
    return os.path.join(root, RUNTIME_DIR,
                        "%s_%s_%s" % (stamp or utc_stamp(), case_id, unique))
