"""Tests for yunoheat/connection.py."""

from __future__ import annotations

import pytest
from aioresponses import aioresponses

from tests.conftest import load_fixture
from yunoheat.auth import TokenData
from yunoheat.connection import Connection
from yunoheat.const import API_BASE_URL, KEYCLOAK_TOKEN_URL
from yunoheat.exceptions import APIError, AuthError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_conn(tokens: TokenData, **kwargs) -> Connection:
    return Connection(tokens, **kwargs)


# ---------------------------------------------------------------------------
# GET success
# ---------------------------------------------------------------------------


async def test_get_success(valid_tokens) -> None:
    conn = make_conn(valid_tokens)
    try:
        with aioresponses() as m:
            m.get(f"{API_BASE_URL}/customers/test", payload={"id": 1})
            result = await conn.get("/customers/test")
        assert result == {"id": 1}
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


async def test_get_401_raises_auth_error(valid_tokens) -> None:
    conn = make_conn(valid_tokens)
    try:
        with aioresponses() as m:
            m.get(f"{API_BASE_URL}/customers/test", status=401)
            with pytest.raises(AuthError) as exc_info:
                await conn.get("/customers/test")
        assert exc_info.value.status == 401
    finally:
        await conn.close()


async def test_get_500_raises_api_error(valid_tokens) -> None:
    conn = make_conn(valid_tokens)
    try:
        with aioresponses() as m:
            m.get(f"{API_BASE_URL}/customers/test", status=500, body="Internal Server Error")
            with pytest.raises(APIError) as exc_info:
                await conn.get("/customers/test")
        assert exc_info.value.status == 500
    finally:
        await conn.close()


async def test_get_404_raises_api_error(valid_tokens) -> None:
    conn = make_conn(valid_tokens)
    try:
        with aioresponses() as m:
            m.get(f"{API_BASE_URL}/customers/missing", status=404, body="Not found")
            with pytest.raises(APIError) as exc_info:
                await conn.get("/customers/missing")
        assert exc_info.value.status == 404
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# POST success
# ---------------------------------------------------------------------------


async def test_post_success(valid_tokens) -> None:
    conn = make_conn(valid_tokens)
    try:
        with aioresponses() as m:
            m.post(f"{API_BASE_URL}/reports/usage", payload={"aggregations": {}})
            result = await conn.post("/reports/usage", json={"size": 0})
        assert result == {"aggregations": {}}
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Token refresh before request
# ---------------------------------------------------------------------------


async def test_token_refreshed_before_request(tmp_path, monkeypatch, expired_access_tokens) -> None:
    """Expired access token should trigger a silent refresh before the API call."""
    import yunoheat.auth as auth_module

    monkeypatch.setattr(auth_module, "_token_path", lambda: tmp_path / "tokens.json")

    new_token_resp = load_fixture("token_response")
    conn = make_conn(expired_access_tokens)
    try:
        with aioresponses() as m:
            # First call: Keycloak token refresh
            m.post(KEYCLOAK_TOKEN_URL, payload=new_token_resp)
            # Second call: the actual API request
            m.get(f"{API_BASE_URL}/site", payload={"id": 142})
            result = await conn.get("/site")
        assert result == {"id": 142}
        # Access token should now be updated
        assert conn._tokens.access_token == new_token_resp["access_token"]
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Re-login on refresh expiry (when credentials stored)
# ---------------------------------------------------------------------------


async def test_relogin_when_refresh_expired(tmp_path, monkeypatch, fully_expired_tokens) -> None:
    import yunoheat.auth as auth_module

    monkeypatch.setattr(auth_module, "_token_path", lambda: tmp_path / "tokens.json")

    new_token_resp = load_fixture("token_response")
    conn = make_conn(
        fully_expired_tokens,
        username="user@example.com",
        password="password",
    )
    try:
        with aioresponses() as m:
            # Re-login call
            m.post(KEYCLOAK_TOKEN_URL, payload=new_token_resp)
            # Actual API call
            m.get(f"{API_BASE_URL}/site", payload={"id": 142})
            result = await conn.get("/site")
        assert result == {"id": 142}
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


async def test_context_manager(valid_tokens) -> None:
    with aioresponses() as m:
        m.get(f"{API_BASE_URL}/site", payload={"id": 142})
        async with Connection(valid_tokens) as conn:
            result = await conn.get("/site")
    assert result == {"id": 142}
