"""Redaction applied to everything the runner writes to disk.

Two separate jobs:

1. Tenant identifiers (resource and project names) are replaced with markers, so
   captured evidence can be published without leaking them.
2. Anything shaped like a bearer token or a JWT is removed unconditionally, so a
   credential cannot reach an evidence file even if a future change accidentally
   passes a header through.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

RESOURCE_MARK = "<foundry-resource>"
PROJECT_MARK = "<foundry-project>"
TOKEN_MARK = "<redacted-token>"

_BEARER = re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE)
_JWT = re.compile(r"\beyJ[A-Za-z0-9\-_]{10,}\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_.+/=]+")


@dataclass(frozen=True)
class Redactor:
    """Replaces tenant identifiers and credential-shaped strings."""

    resource: str
    project: str

    def text(self, value: str) -> str:
        out = _BEARER.sub("Bearer " + TOKEN_MARK, value)
        out = _JWT.sub(TOKEN_MARK, out)
        if self.resource:
            out = out.replace(self.resource, RESOURCE_MARK)
        if self.project:
            out = out.replace(self.project, PROJECT_MARK)
        return out

    def data(self, value: Any) -> Any:
        """Redact recursively, returning a new structure. Nothing is mutated."""
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, dict):
            return {self.text(str(k)): self.data(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self.data(v) for v in value]
        return value


def for_config(config: Any) -> Redactor:
    return Redactor(resource=config.resource, project=config.project)
