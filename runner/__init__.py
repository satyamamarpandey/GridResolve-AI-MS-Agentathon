"""Foundry workflow execution runner for GridResolve AI.

Nothing in this package performs a model request unless the operator issues the
explicit `execute` command with the confirmation phrase and a spending cap.
Importing the package, or running any other command, cannot bill.
"""

__all__ = ["config", "pricing", "redaction", "case", "transport", "foundry",
           "evidence", "execute", "cli"]
