"""Exception hierarchy for pyyunoheat."""

from __future__ import annotations


class YunoHeatError(Exception):
    """Base for all pyyunoheat errors."""


class AuthError(YunoHeatError):
    """Raised when a session-level authentication fails (e.g. 401 response)."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


class ConfigEntryAuthFailed(YunoHeatError):
    """Raised when authentication fails due to invalid credentials.

    This should trigger Home Assistant's ConfigEntryAuthFailed flow,
    prompting the user to re-authenticate.
    """

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


class TokenExpiredError(AuthError):
    """Raised when the refresh token has expired.

    Re-authentication with stored credentials is required, or the user must
    log in again if credentials are not available.
    """


class APIConnectionError(YunoHeatError):
    """Raised on network-level connection failures (timeout, connection refused, etc)."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.cause = cause


class APIError(YunoHeatError):
    """Raised when the API returns a non-2xx response (other than 401)."""

    def __init__(self, message: str, status: int) -> None:
        super().__init__(f"HTTP {status}: {message}")
        self.message = message
        self.status = status


class EntityDiscoveryError(YunoHeatError):
    """Raised when the entity discovery flow fails due to missing API data."""
