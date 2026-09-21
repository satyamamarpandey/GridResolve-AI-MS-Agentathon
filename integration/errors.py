"""Typed failures raised at the integration boundary.

Refusals carry one fixed sentence each. They never name the case, account,
amount or reason, so a caller cannot learn anything by probing.
"""

AUTHENTICATION_REFUSED = "Authentication required."
AUTHORIZATION_REFUSED = "Not authorized for this resource."


class IntegrationError(Exception):
    """Base class for every failure this package raises on purpose."""


class AuthenticationError(IntegrationError):
    """No valid session. Missing, unknown, revoked and expired all look the same."""

    def __init__(self) -> None:
        super().__init__(AUTHENTICATION_REFUSED)


class AuthorizationError(IntegrationError):
    """The caller is known but may not do this. No detail is given."""

    def __init__(self) -> None:
        super().__init__(AUTHORIZATION_REFUSED)


class ValidationError(IntegrationError):
    """Input failed a boundary check. The message names the field, never the value."""


class TimeoutExceeded(IntegrationError):
    """A dependency answered after its deadline. Its answer was discarded."""

    def __init__(self, budget_seconds: float) -> None:
        super().__init__("Deadline of %s seconds exceeded." % budget_seconds)
        self.budget_seconds = budget_seconds


class TransientError(IntegrationError):
    """A dependency was briefly unavailable. Only reads may be tried again."""


class RetryNotAllowed(IntegrationError):
    """A retry was asked for on an operation that is not an idempotent read."""


class IdempotencyConflict(IntegrationError):
    """An idempotency key was reused with a different payload."""


class FourEyesViolation(IntegrationError):
    """The approver is the requester. A second person must decide."""


class AlreadyDecided(IntegrationError):
    """The request already has a decision, and this one differs."""
