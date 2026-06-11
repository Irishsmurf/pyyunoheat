"""Authentication helpers: Keycloak Authorization Code flow, token refresh, persistence."""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import parse_qs, urlparse

import aiohttp

from yunoheat.const import (
    DEFAULT_TOKEN_PATH_PARTS,
    KEYCLOAK_AUTH_URL,
    KEYCLOAK_CLIENT_ID,
    KEYCLOAK_REDIRECT_URI,
    KEYCLOAK_SCOPES,
    KEYCLOAK_TOKEN_URL,
    TOKEN_REFRESH_MARGIN,
)
from yunoheat.exceptions import AuthError, ConfigEntryAuthFailed, TokenExpiredError

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
        return asdict(self)

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


class TokenStore(Protocol):
    """Protocol for pluggable token storage (file, memory, HA config entry, etc)."""

    async def load(self) -> TokenData | None:
        """Load tokens. Return None if not found."""
        ...

    async def save(self, tokens: TokenData) -> None:
        """Persist tokens."""
        ...


class FileTokenStore:
    """Default file-based token store; stores tokens in ~/.config/yunoheat/tokens.json."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path(*DEFAULT_TOKEN_PATH_PARTS).expanduser()

    async def load(self) -> TokenData | None:
        """Read TokenData from disk. Returns None if the file doesn't exist or is invalid."""
        if not self._path.exists():
            return None
        try:
            with self._path.open() as f:
                return TokenData.from_dict(json.load(f))
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Could not load tokens from %s: %s", self._path, exc)
            return None

    async def save(self, tokens: TokenData) -> None:
        """Atomically write TokenData to disk with mode 0o600."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        try:
            with tmp.open("w") as f:
                json.dump(tokens.to_dict(), f, indent=2)
            os.chmod(tmp, 0o600)
            os.replace(tmp, self._path)
        except Exception as exc:
            _LOGGER.error("Failed to save tokens to %s: %s", self._path, exc)
            raise


class InMemoryTokenStore:
    """In-memory token store. Useful for testing or short-lived sessions."""

    def __init__(self) -> None:
        self._tokens: TokenData | None = None

    async def load(self) -> TokenData | None:
        return self._tokens

    async def save(self, tokens: TokenData) -> None:
        self._tokens = tokens


# Backward compatibility: module-level functions using default file store
_default_store = FileTokenStore()


async def load_tokens() -> TokenData | None:
    """Read TokenData from default file store. Deprecated: use FileTokenStore directly."""
    return await _default_store.load()


async def save_tokens(tokens: TokenData) -> None:
    """Write TokenData to default file store. Deprecated: use FileTokenStore directly."""
    await _default_store.save(tokens)


async def _fetch_auth_code(
    session: aiohttp.ClientSession,
    username: str,
    password: str,
) -> str:
    """Automate the Keycloak Authorization Code flow without a browser.

    Steps:
      1. GET the Keycloak login page to obtain the form action URL.
      2. POST credentials to the form action URL with redirects disabled.
      3. Extract the authorization code from the ``Location`` header fragment.

    Returns the authorization code string.
    Raises ConfigEntryAuthFailed on authentication failure (bad credentials).
    Raises AuthError on network/form parsing failures.
    """
    auth_params = {
        "client_id": KEYCLOAK_CLIENT_ID,
        "redirect_uri": KEYCLOAK_REDIRECT_URI,
        "response_mode": "fragment",
        "response_type": "code",
        "scope": KEYCLOAK_SCOPES,
        "nonce": str(uuid.uuid4()),
        "state": str(uuid.uuid4()),
    }

    # Step 1 — fetch the login page and extract the form action URL
    async with session.get(KEYCLOAK_AUTH_URL, params=auth_params) as resp:
        if resp.status != 200:
            raise AuthError(
                f"Keycloak login page returned HTTP {resp.status}", status=resp.status
            )
        html = await resp.text()

    match = re.search(r'<form[^>]+action="([^"]+)"', html)
    if not match:
        raise AuthError("Could not find login form in Keycloak auth page")
    form_action = match.group(1).replace("&amp;", "&")

    # Step 2 — POST credentials; capture the redirect without following it
    form_data = {
        "username": username,
        "password": password,
        "rememberMe": "on",
        "credentialId": "",
    }
    async with session.post(form_action, data=form_data, allow_redirects=False) as resp:
        if resp.status not in (301, 302):
            raise ConfigEntryAuthFailed(
                f"Expected redirect after login, got HTTP {resp.status}. "
                "Check your credentials.",
                status=resp.status,
            )
        location = resp.headers.get("Location", "")

    # Step 3 — parse the code from the Location header
    # response_mode=fragment → code is in the URL fragment (#code=xxx)
    # also handle response_mode=query as a fallback
    parsed = urlparse(location)
    for params in (parse_qs(parsed.fragment), parse_qs(parsed.query)):
        if "error" in params:
            error = params["error"][0]
            desc = params.get("error_description", [""])[0]
            raise ConfigEntryAuthFailed(f"{error}: {desc}")
        if "code" in params:
            return params["code"][0]

    raise AuthError(f"No authorization code in Keycloak redirect: {location}")


async def login(
    session: aiohttp.ClientSession,
    username: str,
    password: str,
    *,
    token_store: TokenStore | None = None,
) -> TokenData:
    """Authenticate via the Keycloak Authorization Code flow (headless).

    Direct grant (grant_type=password) is not enabled for this client.
    This function automates the browser-based login by posting credentials
    directly to the Keycloak form and capturing the auth code from the redirect.

    Persists tokens to the provided token_store (or default file store).
    Raises ConfigEntryAuthFailed on bad credentials.
    Raises AuthError on network/server failures.
    """
    code = await _fetch_auth_code(session, username, password)

    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": KEYCLOAK_CLIENT_ID,
        "redirect_uri": KEYCLOAK_REDIRECT_URI,
    }
    async with session.post(KEYCLOAK_TOKEN_URL, data=token_data) as resp:
        body = await resp.json(content_type=None)
        if resp.status != 200:
            error = body.get("error", "unknown_error")
            description = body.get("error_description", str(body))
            raise ConfigEntryAuthFailed(f"{error}: {description}", status=resp.status)
        tokens = TokenData.from_token_response(body)

    # Persist tokens
    store = token_store or _default_store
    await store.save(tokens)
    return tokens


async def refresh(
    session: aiohttp.ClientSession,
    tokens: TokenData,
    *,
    token_store: TokenStore | None = None,
) -> TokenData:
    """Exchange a refresh token for a new token pair.

    Persists updated tokens to the provided token_store (or default file store).
    Raises TokenExpiredError if the refresh token has expired.
    Raises AuthError on network/server failures.
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

    # Persist updated tokens
    store = token_store or _default_store
    await store.save(new_tokens)
    return new_tokens


async def get_valid_tokens(
    session: aiohttp.ClientSession,
    tokens: TokenData,
    *,
    token_store: TokenStore | None = None,
) -> TokenData:
    """Return tokens valid for immediate use, refreshing if the access token has expired.

    Raises TokenExpiredError if both access and refresh tokens are expired.
    """
    if tokens.access_is_valid():
        return tokens
    if not tokens.refresh_is_valid(margin=0):
        raise TokenExpiredError("Both access and refresh tokens have expired; please log in again.")
    return await refresh(session, tokens, token_store=token_store)
