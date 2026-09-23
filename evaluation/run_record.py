"""One captured run, read into an immutable record.

Read-only. The source is the platform's own conversation record
(07_conversation_items.json), where every item carries the agent name and
version the service recorded. Nothing here trusts what an agent says about
itself.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from runner import analysis as runner_analysis


@dataclass(frozen=True)
class AgentOutput:
    agent: str
    version: str
    text: str
    data: Mapping[str, Any] | None
    tail: str
    invocation: str | None
    response_id: str | None


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    workflow_name: str
    workflow_version: str
    platform_workflow_versions: tuple[str, ...]
    case_text: str
    case: Mapping[str, Any]
    outputs: tuple[AgentOutput, ...]
    released: str | None
    analysis: Mapping[str, Any]

    def output(self, agent: str) -> AgentOutput | None:
        found = [o for o in self.outputs if o.agent == agent]
        return found[-1] if found else None

    def data_of(self, agent: str) -> Mapping[str, Any]:
        found = self.output(agent)
        return found.data if found and found.data is not None else {}


def split_json_and_tail(text: str) -> tuple[dict | None, str]:
    """The leading JSON object of an output, and whatever follows it."""
    stripped = text.lstrip()
    if not stripped.startswith("{"):
        return None, text
    try:
        value, end = json.JSONDecoder().raw_decode(stripped)
    except json.JSONDecodeError:
        return None, text
    return (value, stripped[end:]) if isinstance(value, dict) else (None, text)


def _agent(item: dict) -> dict:
    created = item.get("created_by")
    agent = created.get("agent") if isinstance(created, dict) else None
    return agent if isinstance(agent, dict) else {}


def _parse_case(text: str) -> dict:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def build_run(run_id: str, workflow_name: str, workflow_version: str,
              items: list[dict], analysis: Mapping[str, Any]) -> RunRecord:
    """Build a record from platform conversation items, oldest first."""
    outputs: list[AgentOutput] = []
    released: str | None = None
    case_text = ""
    pending_invocation: str | None = None
    seen_case = False
    for item in items:
        if item.get("type") != "message":
            continue
        text = runner_analysis.text_of(item)
        if item.get("role") == "user":
            if not seen_case:
                case_text, seen_case = text, True
            else:
                pending_invocation = text
            continue
        name = str(_agent(item).get("name"))
        if name == workflow_name:
            released = text
            continue
        data, tail = split_json_and_tail(text)
        created = item.get("created_by") or {}
        outputs.append(AgentOutput(
            agent=name, version=str(_agent(item).get("version")), text=text,
            data=MappingProxyType(data) if data is not None else None,
            tail=tail if data is not None else "",
            invocation=pending_invocation,
            response_id=created.get("response_id")))
        pending_invocation = None
    versions = tuple(sorted({
        str(_agent(i).get("version")) for i in items
        if _agent(i).get("name") == workflow_name}))
    return RunRecord(
        run_id=run_id, workflow_name=workflow_name,
        workflow_version=str(workflow_version),
        platform_workflow_versions=versions, case_text=case_text,
        case=MappingProxyType(_parse_case(case_text)), outputs=tuple(outputs),
        released=released, analysis=MappingProxyType(dict(analysis)))


def load_run(run_dir: str) -> RunRecord:
    """Read one evidence folder. Opens files for reading only."""
    def load(name: str) -> Any:
        with open(os.path.join(run_dir, name), encoding="utf-8") as handle:
            return json.load(handle)

    preflight = load("00_preflight.json")
    items = runner_analysis.items_of(load("07_conversation_items.json"))
    return build_run(
        run_id=os.path.basename(os.path.normpath(run_dir)),
        workflow_name=str(preflight.get("workflow")),
        workflow_version=str(preflight.get("workflow_version")),
        items=items, analysis=runner_analysis.analyze_run_dir(run_dir))


REQUIRED_FILES = ("07_conversation_items.json", "04_workflow_actions.json")


def is_complete(run_dir: str) -> bool:
    """A folder the runner finished writing. A run still streaming, or one
    that failed before the conversation was read back (99_error.txt), has no
    record to judge and is skipped rather than guessed at."""
    return all(os.path.isfile(os.path.join(run_dir, n)) for n in REQUIRED_FILES)


def load_all(evidence_root: str) -> tuple[RunRecord, ...]:
    names = sorted(n for n in os.listdir(evidence_root)
                   if os.path.isdir(os.path.join(evidence_root, n))
                   and is_complete(os.path.join(evidence_root, n)))
    return tuple(load_run(os.path.join(evidence_root, n)) for n in names)
