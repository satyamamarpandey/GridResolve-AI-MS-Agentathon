"""Production integration contracts and local synthetic mocks for GridResolve AI.

Contracts, ports, authorization rules and in-memory adapters only. No real
utility, meter, CRM or identity system is connected, nothing here is deployed,
and no module in this package opens a network connection.
"""

__all__ = [
    "adjustments",
    "audit_store",
    "auth",
    "contracts",
    "errors",
    "ports",
    "reliability",
    "synthetic_adapters",
    "synthetic_store",
    "validation",
]
