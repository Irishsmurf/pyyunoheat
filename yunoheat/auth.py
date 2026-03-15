"""Authentication helpers: Keycloak direct-grant login, token refresh, and persistence."""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiohttp

from yunoheat.const import (
    DEFAULT_TOKEN_PATH_PARTS,
    KEYCLOAK_CLIENT_ID,
    KEYCLOAK_SCOPES,
    KEYCLOAK_TOKEN_URL,
    TOKEN_REFRESH_MARGIN,
)
from yunoheat.exceptions import AuthError, TokenExpiredError

_LOGGER = logging.getLogger(__name__)


@dataclass
class TokenData:
    """Holds a Keycloak token pair with precomputed expiry timestamps."""

    access_token: str
    refresh_token: str
    # Unix timestamps (float seconds) — computed at login/refresh time
    access_expires_at: float
    refresh_expires_at: float

    def access_is_valid(self, margin: float = TOKEN_REFRESH_MARGIN) -> bool:
        """True if the access token has more than *margin* seconds remaining."""
        return time.time() < (self.access_expires_at - margin)

    def refresh_is_valid(self, margin: float = TOKEN_REFRESH_MARGIN) -> bool:
        """True if the refresh token has more than *margin* seconds remaining."""
        return time.time() < (self.refresh_expires_at - margin)

    def to_dict(self) -> dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "access_expires_at": self.access_expires_at,
            "refresh_expires_at": self.refresh_expires_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TokenData:
        return cls(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            access_expires_at=float(data["access_expires_at"]),
            refresh_expires_at=float(data["refresh_expires_at"]),
        )

    @classmethod
    def from_token_response(cls, resp: dict[str, Any]) -> TokenData:
        """Build from a Keycloak token endpoint response dict."""
        now = time.time()
        return cls(
            access_token=resp["access_token"],
            refresh_token=resp["refresh_token"],
            access_expires_at=now + int(resp["expires_in"]),
            refresh_expires_at=now + int(resp["refresh_expires_in"]),
        )


def _token_path() -> Path:
    """Return the path to the token file, creating parent directories if needed."""
    path = Path(*DEFAULT_TOKEN_PATH_PARTS).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_tokens() -> TokenData | None:
    """Read TokenData from disk. Returns None if the file doesn't exist or is invalid."""
    path = _token_path()
    if not path.exists():
        return None
    try:
        with path.open() as f:
            return TokenData.from_dict(json.load(f))
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("Could not load tokens from %s: %s", path, exc)
        return None


def save_tokens(tokens: TokenData) -> None:
    """Atomically write TokenData to disk with mode 0o600."""
    path = _token_path()
    tmp = path.with_suffix(".tmp")
    try:
        with tmp.open("w") as f:
            json.dump(tokens.to_dict(), f, indent=2)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except Exception as exc:
        _LOGGER.error("Failed to save tokens to %s: %s", path, exc)
        raise


async def login(
    session: aiohttp.ClientSession,
    username: str,
    password: str,
) -> TokenData:
    """Authenticate via Keycloak direct grant (grant_type=password).

    Raises AuthError on failure. Saves tokens to disk on success.
    """
    data = {
        "grant_type": "password",
        "client_id": KEYCLOAK_CLIENT_ID,
        "username": username,
        "password": password,
        "scope": KEYCLOAK_SCOPES,
    }
    async with session.post(KEYCLOAK_TOKEN_URL, data=data) as resp:
        body = await resp.json(content_type=None)
        if resp.status != 200:
            error = body.get("error", "unknown_error")
            description = body.get("error_description", str(body))
            raise AuthError(f"{error}: {description}", status=resp.status)
        tokens = TokenData.from_token_response(body)
    save_tokens(tokens)
    return tokens


async def refresh(
    session: aiohttp.ClientSession,
    tokens: TokenData,
) -> TokenData:
    """Exchange a refresh token for a new token pair.

    Raises TokenExpiredError if the refresh token is already expired before the call.
    Raises AuthError on HTTP failure.
    Saves updated tokens to disk on success.
    """
    if not tokens.refresh_is_valid(margin=0):
        raise TokenExpiredError("Refresh token has expired; please log in again.")

    data = {
        "grant_type": "refresh_token",
        "client_id": KEYCLOAK_CLIENT_ID,
        "refresh_token": tokens.refresh_token,
    }
    async with session.post(KEYCLOAK_TOKEN_URL, data=data) as resp:
        body = await resp.json(content_type=None)
        if resp.status != 200:
            error = body.get("error", "unknown_error")
            description = body.get("error_description", str(body))
            if resp.status == 400 and "expired" in description.lower():
                raise TokenExpiredError(f"{error}: {description}", status=resp.status)
            raise AuthError(f"{error}: {description}", status=resp.status)
        new_tokens = TokenData.from_token_response(body)
    save_tokens(new_tokens)
    return new_tokens


async def get_valid_tokens(
    session: aiohttp.ClientSession,
    tokens: TokenData,
) -> TokenData:
    """Return tokens valid for immediate use, refreshing if the access token has expired.

    Raises TokenExpiredError if both access and refresh tokens are expired.
    """
    if tokens.access_is_valid():
        return tokens
    if not tokens.refresh_is_valid(margin=0):
        raise TokenExpiredError("Both access and refresh tokens have expired; please log in again.")
    return await refresh(session, tokens)
