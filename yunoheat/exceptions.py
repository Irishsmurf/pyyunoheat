"""Exception hierarchy for pyyunoheat."""

from __future__ import annotations


class YunoHeatError(Exception):
    """Base for all pyyunoheat errors."""


class AuthError(YunoHeatError):
    """Raised when authentication fails (e.g. bad credentials or 401 response)."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


class TokenExpiredError(AuthError):
    """
    Raised when the refresh token has expired and re-authentication
    with credentials is required.
    """


class APIError(YunoHeatError):
    """Raised when the API returns a non-2xx response other than 401."""

    def __init__(self, message: str, status: int) -> None:
        super().__init__(f"HTTP {status}: {message}")
        self.message = message
        self.status = status


class EntityDiscoveryError(YunoHeatError):
    """
    Raised when the entity discovery flow (person → property) fails because
    expected objects are missing from the API responses.
    """
