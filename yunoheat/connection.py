"""Low-level async HTTP wrapper with automatic token injection and refresh."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from yunoheat.auth import TokenData, get_valid_tokens, login
from yunoheat.const import API_BASE_URL
from yunoheat.exceptions import APIError, AuthError, TokenExpiredError

_LOGGER = logging.getLogger(__name__)


class Connection:
    """Async HTTP client that injects Bearer tokens and handles token refresh.

    Parameters
    ----------
    tokens:
        Initial token state. Updated in-place by refresh/re-login.
    username:
        Stored for silent re-authentication if the refresh token expires.
    password:
        Stored for silent re-authentication if the refresh token expires.
    session:
        External ``aiohttp.ClientSession`` (useful for testing). When None,
        one is created lazily on first use and owned by this instance.
    """

    def __init__(
        self,
        tokens: TokenData,
        username: str | None = None,
        password: str | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._tokens = tokens
        self._username = username
        self._password = password
        self._external_session = session
        self._session: aiohttp.ClientSession | None = session
        self._session_owned = session is None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _get_auth_header(self) -> str:
        """Return a Bearer token string, refreshing or re-logging-in as needed."""
        session = await self._ensure_session()
        try:
            self._tokens = await get_valid_tokens(session, self._tokens)
        except TokenExpiredError:
            if self._username and self._password:
                _LOGGER.info("Tokens expired; re-authenticating with stored credentials.")
                self._tokens = await login(session, self._username, self._password)
            else:
                raise
        return f"Bearer {self._tokens.access_token}"

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        **kwargs: Any,
    ) -> Any:
        """Perform an authenticated HTTP request.

        Returns the parsed JSON response body, or None for 204 No Content.

        Raises
        ------
        AuthError
            On HTTP 401.
        APIError
            On any other non-2xx response.
        """
        session = await self._ensure_session()
        auth_header = await self._get_auth_header()
        headers = {"Authorization": auth_header}

        async with session.request(
            method,
            url,
            params=params,
            json=json,
            headers=headers,
            **kwargs,
        ) as resp:
            if resp.status == 401:
                raise AuthError("Unauthorized — token may have been revoked.", status=401)
            if resp.status == 204:
                return None
            if not resp.ok:
                try:
                    body = await resp.text()
                except Exception:  # noqa: BLE001
                    body = "<unreadable response>"
                raise APIError(body, status=resp.status)
            return await resp.json(content_type=None)

    async def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """GET {API_BASE_URL}{path}."""
        return await self.request("GET", f"{API_BASE_URL}{path}", params=params)

    async def post(
        self,
        path: str,
        *,
        json: Any,
    ) -> Any:
        """POST {API_BASE_URL}{path} with a JSON body."""
        return await self.request("POST", f"{API_BASE_URL}{path}", json=json)

    async def close(self) -> None:
        """Close the session if owned by this instance."""
        if self._session_owned and self._session is not None:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> Connection:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
