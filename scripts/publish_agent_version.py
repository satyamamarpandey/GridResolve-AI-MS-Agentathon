"""Prepare, and only on explicit confirmation send, a new agent or workflow version.

DRY RUN BY DEFAULT. Without `--confirm PUBLISH` this script prints the exact
request it would send (method, URL with the resource and project replaced by
placeholders, headers with the token redacted, the full JSON body) and exits
without opening a connection. It never stores a token: the token is borrowed
from the operator's Azure CLI session at send time, exactly as runner/foundry.py
does, and is never written anywhere.

What it publishes:

  --agent EvidenceComplianceAgent --file agents/EvidenceComplianceAgent.v7.md
      Reads the instruction text from the "## Instructions, proposed v7" fenced
      block of the markdown file, copies model, reasoning, tools and (when the
      live version has one) the attached output schema from the live definition
      read with a GET, and prepares a new version of the same agent.

  --workflow GridResolveAIWorkflow --yaml tests/workflow_engine/workflows/GridResolveAIWorkflow_v11.yaml
      Prepares a new version of the workflow agent whose definition is the YAML
      text. The YAML file is produced by the workflow fork; this script does not
      create it.

Request shape, and how sure I am of it:

  POST {base}/agents/{name}/versions?api-version=v1
  Headers: Authorization: Bearer <token>, Foundry-Features: WorkflowAgents=V1Preview,
           Content-Type: application/json
  Body:    {"description": "...", "definition": {...}}

The GET routes (/agents, /agents/{name}) and the version object's shape
(object=agent.version, fields definition, description, version, created_at) were
confirmed read-only on 2026-09-23. The POST route and body follow the
azure-ai-projects SDK's create_version operation as I understand it. I have NOT
confirmed the POST against the live service, because doing so would create a
version. If the service rejects the body, the send fails closed: nothing is
retried, the response is printed, and no second attempt is made.

Publishing is a control-plane write. It is not a model call and is not expected
to bill, but it changes the live project, so it needs the operator's explicit
go-ahead. The runner pins the workflow version it will execute, so a new
workflow version does not by itself cause a run.

Environment: GRIDRESOLVE_FOUNDRY_RESOURCE, GRIDRESOLVE_FOUNDRY_PROJECT, and
optionally GRIDRESOLVE_AZ_PATH. Never commit their values.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from runner import config as cfg  # noqa: E402
from runner import foundry  # noqa: E402

CONFIRM_WORD = "PUBLISH"
PLACEHOLDER_BASE = "https://<foundry-resource>.services.ai.azure.com/api/projects/<foundry-project>"


def instructions_from_markdown(path: str, heading_prefix: str = "## Instructions") -> str:
    """The text inside the first ```text block that follows the instructions heading."""
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    start = text.find(heading_prefix)
    if start < 0:
        raise SystemExit("No '%s' heading in %s" % (heading_prefix, path))
    match = re.search(r"```text\n(.*?)\n```", text[start:], re.S)
    if not match:
        raise SystemExit("No ```text block after the instructions heading in %s" % path)
    return match.group(1)


def version_label(path: str) -> str:
    match = re.search(r"\.v(\d+)\.(md|yaml)$", os.path.basename(path)) or \
        re.search(r"_v(\d+)\.yaml$", os.path.basename(path))
    return match.group(1) if match else "unknown"


def live_definition(client: foundry.FoundryAgentClient, name: str) -> dict[str, Any]:
    listed = client.list_agents()
    for agent in listed.get("data", []):
        if agent.get("name") == name:
            return dict(agent["versions"]["latest"]["definition"])
    raise SystemExit("Agent %s is not in the live project" % name)


def agent_body(client: foundry.FoundryAgentClient, name: str, path: str,
               description: str) -> dict[str, Any]:
    base = live_definition(client, name)
    definition = {
        "kind": base.get("kind", "prompt"),
        "model": base.get("model"),
        "instructions": instructions_from_markdown(path),
        "reasoning": base.get("reasoning"),
        "tools": base.get("tools", []),
    }
    if base.get("text"):
        definition["text"] = base["text"]
    return {"description": description, "definition": definition}


def workflow_body(path: str, description: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        yaml_text = handle.read()
    return {"description": description,
            "definition": {"kind": "workflow", "workflow": yaml_text}}


def redacted_url(config: cfg.RunnerConfig, name: str) -> str:
    return "%s/agents/%s/versions?api-version=%s" % (
        PLACEHOLDER_BASE, name, cfg.CONTROL_PLANE_API_VERSION)


def real_url(config: cfg.RunnerConfig, name: str) -> str:
    return "%s/agents/%s/versions?api-version=%s" % (
        config.base_url, name, cfg.CONTROL_PLANE_API_VERSION)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--agent", help="agent name, with --file")
    group.add_argument("--workflow", help="workflow agent name, with --yaml")
    parser.add_argument("--file", help="agents/<Agent>.vN.md holding the new instructions")
    parser.add_argument("--yaml", help="workflow YAML definition to publish")
    parser.add_argument("--description", default=None)
    parser.add_argument("--confirm", default="",
                        help="type %s to actually send; anything else is a dry run" % CONFIRM_WORD)
    args = parser.parse_args(argv)

    try:
        config = cfg.from_env()
    except cfg.ConfigError as exc:
        print("Not configured: %s" % exc)
        print("Dry run cannot read the live definition without the environment. Nothing sent.")
        return 2
    client = foundry.FoundryAgentClient(config)

    if args.agent:
        if not args.file:
            parser.error("--agent needs --file")
        name = args.agent
        label = version_label(args.file)
        description = args.description or ("v%s: prepared from %s on 2026-09-23"
                                           % (label, os.path.relpath(args.file, ROOT)))
        body = agent_body(client, name, args.file, description)
    else:
        if not args.yaml:
            parser.error("--workflow needs --yaml")
        name = args.workflow
        label = version_label(args.yaml)
        description = args.description or ("v%s: prepared from %s on 2026-09-23"
                                           % (label, os.path.relpath(args.yaml, ROOT)))
        body = workflow_body(args.yaml, description)

    print("REQUEST (token redacted, identifiers replaced)")
    print("  POST %s" % redacted_url(config, name))
    print("  Authorization: Bearer <az cli token, fetched at send time, never stored>")
    print("  Foundry-Features: %s" % cfg.CONTROL_PLANE_FEATURES)
    print("  Content-Type: application/json")
    print("  Body:")
    print(json.dumps(body, indent=2, ensure_ascii=False))
    print()

    if args.confirm != CONFIRM_WORD:
        print("DRY RUN. Nothing was sent. To send, add: --confirm %s" % CONFIRM_WORD)
        return 0

    headers = client._headers(with_body=True, control_plane=True)  # noqa: SLF001
    response = client.transport.send("POST", real_url(config, name), headers,
                                     body=json.dumps(body).encode("utf-8"), timeout=90.0)
    status = getattr(response, "status", None)
    text = (getattr(response, "body", b"") or b"").decode("utf-8", "replace")
    print("RESPONSE HTTP %s" % status)
    print(text[:4000])
    if status is None or int(status) >= 300:
        print("The service did not accept the version. Nothing is retried.")
        return 1
    print("Version created. Re-run tests/verify_live_config.py read-only to confirm what is live.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
