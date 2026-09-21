"""Runner configuration, read from the environment.

The Foundry resource and project names are tenant-specific identifiers. They are
supplied through environment variables and never committed, because this
repository is public. No credential is read here: the access token is obtained
from the operator's existing Azure CLI session at call time and is never stored.

Request contract, and where each part was confirmed:

  Route      {project}/openai/v1/...   no api-version query parameter
             Source: azure-ai-projects `get_openai_client()` builds exactly this
             base URL, and the live project answers GET on these routes. The
             live project also rejects `/openai/responses?api-version=v1` with
             "api-version=v1 is not allowed. Use /v1 path instead."
  Audience   https://ai.azure.com
             Source: the same SDK requests scope https://ai.azure.com/.default.
  Headers    Authorization only. The SDK adds Foundry-Features solely when it is
             bound to a dedicated agent endpoint, which this runner does not use.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final

DEFAULT_AZ_PATH: Final = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
DEFAULT_AGENT: Final = "GridResolveAIWorkflow"
EXPECTED_WORKFLOW_VERSION: Final = "10"
CONTROL_PLANE_API_VERSION: Final = "v1"

# Needed on the agent management routes (/agents/...), which are preview-gated.
CONTROL_PLANE_FEATURES: Final = "WorkflowAgents=V1Preview"

TOKEN_SCOPE: Final = "https://ai.azure.com"
MIN_IDENTIFIER_LENGTH: Final = 6


class ConfigError(ValueError):
    """The runner cannot be configured from the current environment."""


@dataclass(frozen=True)
class RunnerConfig:
    """Immutable runner configuration."""

    resource: str
    project: str
    agent_name: str = DEFAULT_AGENT
    az_path: str = DEFAULT_AZ_PATH

    def __repr__(self) -> str:
        # The generated dataclass repr would print the tenant identifiers, and
        # it is inherited by anything that holds a config, such as the client.
        return "RunnerConfig(resource=<redacted>, project=<redacted>, " \
               "agent_name=%r)" % self.agent_name

    @property
    def base_url(self) -> str:
        return "https://%s.services.ai.azure.com/api/projects/%s" % (
            self.resource, self.project)

    @property
    def openai_root(self) -> str:
        return self.base_url + "/openai/v1"

    def agent_url(self) -> str:
        return "%s/agents/%s?api-version=%s" % (
            self.base_url, self.agent_name, CONTROL_PLANE_API_VERSION)

    def agents_url(self) -> str:
        return "%s/agents?api-version=%s&limit=100" % (
            self.base_url, CONTROL_PLANE_API_VERSION)

    def conversations_url(self) -> str:
        return self.openai_root + "/conversations"

    def responses_url(self, response_id: str = "") -> str:
        return self.openai_root + "/responses" + (
            "/" + response_id if response_id else "")

    def conversation_items_url(self, conversation_id: str) -> str:
        return "%s/conversations/%s/items?limit=100&order=asc" % (
            self.openai_root, conversation_id)


def from_env(env: dict[str, str] | None = None) -> RunnerConfig:
    """Build a configuration, failing fast with an actionable message."""
    src = os.environ if env is None else env
    resource = (src.get("GRIDRESOLVE_FOUNDRY_RESOURCE") or "").strip()
    project = (src.get("GRIDRESOLVE_FOUNDRY_PROJECT") or "").strip()
    named = (("GRIDRESOLVE_FOUNDRY_RESOURCE", resource),
             ("GRIDRESOLVE_FOUNDRY_PROJECT", project))
    missing = [n for n, v in named if not v]
    if missing:
        raise ConfigError(
            "Set %s before running. These are deliberately not committed, "
            "because this repository is public and a resource name is a "
            "tenant-specific identifier." % " and ".join(missing))
    # Redaction replaces these values wherever they occur as text. A very short
    # name would also match ordinary words and corrupt the captured evidence, so
    # it is refused rather than allowed to damage the record of a billed run.
    too_short = [n for n, v in named if len(v) < MIN_IDENTIFIER_LENGTH]
    if too_short:
        raise ConfigError(
            "%s is shorter than %d characters. Evidence redaction matches these "
            "values as plain text, and a name that short would also redact "
            "unrelated words." % (" and ".join(too_short), MIN_IDENTIFIER_LENGTH))
    return RunnerConfig(
        resource=resource,
        project=project,
        agent_name=(src.get("GRIDRESOLVE_FOUNDRY_AGENT") or DEFAULT_AGENT).strip(),
        az_path=(src.get("GRIDRESOLVE_AZ_PATH") or DEFAULT_AZ_PATH).strip(),
    )
