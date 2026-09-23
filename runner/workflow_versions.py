"""Which workflow definition the runner interprets.

The runner refuses to execute against any workflow version other than the one
it was reviewed for, because action ids belong to one definition. The default
is v10, the version that produced every hosted run so far. Setting

    GRIDRESOLVE_WORKFLOW_VERSION=11

selects the bounded-correction design in `workflow_v11`, which is a local
design until it is published. Any other value is refused. Analysis of an old
evidence folder uses the version its own preflight record names, never this
setting, so an old run is judged against the definition it ran on.
"""
from __future__ import annotations

import os
from types import ModuleType
from typing import Final, Mapping

from . import workflow_map, workflow_v11
from .config import ConfigError

ENV_VAR: Final = "GRIDRESOLVE_WORKFLOW_VERSION"
DEFAULT_VERSION: Final = workflow_map.WORKFLOW_VERSION
VERSIONS: Final[Mapping[str, ModuleType]] = {
    workflow_map.WORKFLOW_VERSION: workflow_map,
    workflow_v11.WORKFLOW_VERSION: workflow_v11,
}
# v5 to v9 kept the action ids v10 interprets (see workflow_map), so their
# evidence folders are read with the v10 map. They cannot be executed.
LEGACY_VERSIONS: Final = ("5", "6", "7", "8", "9")


def for_version(version: str) -> ModuleType:
    """The action map that reads a run of `version`, or ConfigError."""
    key = str(version)
    module = workflow_map if key in LEGACY_VERSIONS else VERSIONS.get(key)
    if module is None:
        raise ConfigError(
            "Workflow version %r is not one this runner can interpret. Known: %s."
            % (version, ", ".join(sorted(VERSIONS) + list(LEGACY_VERSIONS))))
    return module


def active(env: Mapping[str, str] | None = None) -> ModuleType:
    """The action map the runner executes against, from the environment.

    Only a current version may be selected here. Defaults to v10.
    """
    source = os.environ if env is None else env
    version = source.get(ENV_VAR, DEFAULT_VERSION)
    if version not in VERSIONS:
        raise ConfigError(
            "%s=%r is not a version this runner can execute against. Known: %s."
            % (ENV_VAR, version, ", ".join(sorted(VERSIONS))))
    return VERSIONS[version]


def active_version(env: Mapping[str, str] | None = None) -> str:
    return active(env).WORKFLOW_VERSION
