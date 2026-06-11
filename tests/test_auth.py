"""Tests for yunoheat/auth.py."""

from __future__ import annotations

import re
import time

import pytest
from aioresponses import aioresponses

from tests.conftest import load_fixture
from yunoheat.auth import (
    FileTokenStore,
    TokenData,
    get_valid_tokens,
    load_tokens,
    login,
    refresh,
    save_tokens,
)
from yunoheat.const import KEYCLOAK_AUTH_URL, KEYCLOAK_TOKEN_URL
from yunoheat.exceptions import AuthError, TokenExpiredError

# ---------------------------------------------------------------------------
# Login flow helpers
# ---------------------------------------------------------------------------

# Minimal Keycloak login page HTML containing a form with a known action URL
_FORM_ACTION = (
    "https://app.tridenstechnology.com/auth/realms/kaizen-energy-sandbox"
    "/login-actions/authenticate"
    "?session_code=testsession&execution=testexec&client_id=mobile-yuno&tab_id=testtab"
)
_FAKE_LOGIN_HTML = (
    f'<form id="kc-form-login" action="{_FORM_ACTION.replace("&", "&amp;")}" method="post">'
    '<input name="username"/><input name="password"/></form>'
)
# The redirect Keycloak sends after successful login (code in the fragment)
_FAKE_REDIRECT = (
    "https://kaizen-energy.tridenstechnology.com/monetization/self-care/account"
    "#code=test-auth-code-12345&state=somestate"
)

# ---------------------------------------------------------------------------
# TokenData helpers
# ---------------------------------------------------------------------------


def test_token_data_access_is_valid() -> None:
    now = time.time()
    tokens = TokenData(
        access_token="a",
        refresh_token="r",
        access_expires_at=now + 1800,
        refresh_expires_at=now + 2100,
    )
    assert tokens.access_is_valid()


def test_token_data_access_is_expired() -> None:
    now = time.time()
    tokens = TokenData(
        access_token="a",
        refresh_token="r",
        access_expires_at=now - 10,
        refresh_expires_at=now + 2100,
    )
    assert not tokens.access_is_valid()


def test_token_data_refresh_is_expired() -> None:
    now = time.time()
    tokens = TokenData(
        access_token="a",
        refresh_token="r",
        access_expires_at=now - 200,
        refresh_expires_at=now - 10,
    )
    assert not tokens.refresh_is_valid(margin=0)


def test_token_data_from_token_response() -> None:
    resp = load_fixture("token_response")
    tokens = TokenData.from_token_response(resp)
    assert tokens.access_token == resp["access_token"]
    assert tokens.refresh_token == resp["refresh_token"]
    assert tokens.access_expires_at > time.time()
    assert tokens.refresh_expires_at > time.time()


def test_token_data_serialisation_roundtrip() -> None:
    now = time.time()
    original = TokenData(
        access_token="at",
        refresh_token="rt",
        access_expires_at=now + 1000,
        refresh_expires_at=now + 2000,
    )
    restored = TokenData.from_dict(original.to_dict())
    assert restored.access_token == original.access_token
    assert restored.refresh_token == original.refresh_token
    assert abs(restored.access_expires_at - original.access_expires_at) < 0.001


# ---------------------------------------------------------------------------
# Disk persistence
# ---------------------------------------------------------------------------


def test_save_and_load_tokens(tmp_path) -> None:
    token_file = tmp_path / "tokens.json"
    store = FileTokenStore(token_file)

    now = time.time()
    tokens = TokenData(
        access_token="access",
        refresh_token="refresh",
        access_expires_at=now + 1800,
        refresh_expires_at=now + 2100,
    )
    # Use async version
    import asyncio
    asyncio.run(store.save(tokens))
    assert token_file.exists()

    loaded = asyncio.run(store.load())
    assert loaded is not None
    assert loaded.access_token == "access"
    assert loaded.refresh_token == "refresh"


def test_load_tokens_missing_file(tmp_path) -> None:
    token_file = tmp_path / "nonexistent.json"
    store = FileTokenStore(token_file)
    import asyncio
    assert asyncio.run(store.load()) is None


def test_load_tokens_corrupt_file(tmp_path) -> None:
    token_file = tmp_path / "tokens.json"
    token_file.write_text("{ not valid json }")
    store = FileTokenStore(token_file)
    import asyncio
    assert asyncio.run(store.load()) is None


# ---------------------------------------------------------------------------
# login() — Authorization Code flow (three HTTP calls)
# ---------------------------------------------------------------------------


async def test_login_success(tmp_path) -> None:
    import aiohttp

    token_file = tmp_path / "tokens.json"
    store = FileTokenStore(token_file)

    resp_data = load_fixture("token_response")
    with aioresponses() as m:
        # Step 1: GET Keycloak login page
        m.get(
            re.compile(rf"{re.escape(KEYCLOAK_AUTH_URL)}.*"),
            status=200,
            body=_FAKE_LOGIN_HTML,
        )
        # Step 2: POST credentials → 302 with auth code in fragment
        m.post(_FORM_ACTION, status=302, headers={"Location": _FAKE_REDIRECT})
        # Step 3: exchange code for tokens
        m.post(KEYCLOAK_TOKEN_URL, payload=resp_data, status=200)
        async with aiohttp.ClientSession() as session:
            tokens = await login(session, "user@example.com", "password", token_store=store)

    assert tokens.access_token == resp_data["access_token"]
    assert token_file.exists()


async def test_login_bad_credentials(tmp_path) -> None:
    import aiohttp

    token_file = tmp_path / "tokens.json"
    store = FileTokenStore(token_file)

    with aioresponses() as m:
        # Step 1: GET login page succeeds
        m.get(
            re.compile(rf"{re.escape(KEYCLOAK_AUTH_URL)}.*"),
            status=200,
            body=_FAKE_LOGIN_HTML,
        )
        # Step 2: POST credentials → 200 (Keycloak returns login page with error)
        m.post(_FORM_ACTION, status=200, body="<html>Invalid username or password.</html>")
        async with aiohttp.ClientSession() as session:
            from yunoheat.exceptions import ConfigEntryAuthFailed
            with pytest.raises(ConfigEntryAuthFailed) as exc_info:
                await login(session, "user@example.com", "wrongpassword", token_store=store)

    # Keycloak returns 200 (login page with error) instead of a redirect,
    # so the auth code flow raises ConfigEntryAuthFailed about the unexpected status.
    assert "200" in str(exc_info.value)


# ---------------------------------------------------------------------------
# refresh()
# ---------------------------------------------------------------------------


async def test_refresh_success(tmp_path, expired_access_tokens) -> None:
    import aiohttp

    token_file = tmp_path / "tokens.json"
    store = FileTokenStore(token_file)

    resp_data = load_fixture("token_response")
    with aioresponses() as m:
        m.post(KEYCLOAK_TOKEN_URL, payload=resp_data, status=200)
        async with aiohttp.ClientSession() as session:
            new_tokens = await refresh(session, expired_access_tokens, token_store=store)

    assert new_tokens.access_token == resp_data["access_token"]


async def test_refresh_raises_when_refresh_expired(fully_expired_tokens) -> None:
    import aiohttp

    async with aiohttp.ClientSession() as session:
        with pytest.raises(TokenExpiredError):
            await refresh(session, fully_expired_tokens)


# ---------------------------------------------------------------------------
# get_valid_tokens()
# ---------------------------------------------------------------------------


async def test_get_valid_tokens_access_still_valid(valid_tokens) -> None:
    """When access token is valid, no HTTP call should be made."""
    import aiohttp

    with aioresponses():  # no URLs registered — any call would raise
        async with aiohttp.ClientSession() as session:
            result = await get_valid_tokens(session, valid_tokens)

    assert result is valid_tokens  # same object, no copy


async def test_get_valid_tokens_access_expired_refresh_valid(
    tmp_path, expired_access_tokens
) -> None:
    import aiohttp

    token_file = tmp_path / "tokens.json"
    store = FileTokenStore(token_file)

    resp_data = load_fixture("token_response")
    with aioresponses() as m:
        m.post(KEYCLOAK_TOKEN_URL, payload=resp_data, status=200)
        async with aiohttp.ClientSession() as session:
            result = await get_valid_tokens(session, expired_access_tokens, token_store=store)

    assert result.access_token == resp_data["access_token"]


async def test_get_valid_tokens_both_expired_raises(fully_expired_tokens) -> None:
    import aiohttp

    async with aiohttp.ClientSession() as session:
        with pytest.raises(TokenExpiredError):
            await get_valid_tokens(session, fully_expired_tokens)
