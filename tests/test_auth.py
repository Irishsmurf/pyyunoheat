"""Tests for yunoheat/auth.py."""

from __future__ import annotations

import time

import pytest
from aioresponses import aioresponses

from tests.conftest import load_fixture
from yunoheat.auth import (
    TokenData,
    get_valid_tokens,
    load_tokens,
    login,
    refresh,
    save_tokens,
)
from yunoheat.const import KEYCLOAK_TOKEN_URL
from yunoheat.exceptions import AuthError, TokenExpiredError

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


def test_save_and_load_tokens(tmp_path, monkeypatch) -> None:
    token_file = tmp_path / "tokens.json"

    # Patch _token_path to use a temporary location
    import yunoheat.auth as auth_module

    monkeypatch.setattr(auth_module, "_token_path", lambda: token_file)

    now = time.time()
    tokens = TokenData(
        access_token="access",
        refresh_token="refresh",
        access_expires_at=now + 1800,
        refresh_expires_at=now + 2100,
    )
    save_tokens(tokens)
    assert token_file.exists()

    loaded = load_tokens()
    assert loaded is not None
    assert loaded.access_token == "access"
    assert loaded.refresh_token == "refresh"


def test_load_tokens_missing_file(tmp_path, monkeypatch) -> None:
    import yunoheat.auth as auth_module

    monkeypatch.setattr(auth_module, "_token_path", lambda: tmp_path / "nonexistent.json")
    assert load_tokens() is None


def test_load_tokens_corrupt_file(tmp_path, monkeypatch) -> None:
    import yunoheat.auth as auth_module

    token_file = tmp_path / "tokens.json"
    token_file.write_text("{ not valid json }")
    monkeypatch.setattr(auth_module, "_token_path", lambda: token_file)
    assert load_tokens() is None


# ---------------------------------------------------------------------------
# login()
# ---------------------------------------------------------------------------


async def test_login_success(tmp_path, monkeypatch) -> None:
    import aiohttp

    import yunoheat.auth as auth_module

    monkeypatch.setattr(auth_module, "_token_path", lambda: tmp_path / "tokens.json")

    resp_data = load_fixture("token_response")
    with aioresponses() as m:
        m.post(KEYCLOAK_TOKEN_URL, payload=resp_data, status=200)
        async with aiohttp.ClientSession() as session:
            tokens = await login(session, "user@example.com", "password")

    assert tokens.access_token == resp_data["access_token"]
    assert (tmp_path / "tokens.json").exists()


async def test_login_bad_credentials(tmp_path, monkeypatch) -> None:
    import aiohttp

    import yunoheat.auth as auth_module

    monkeypatch.setattr(auth_module, "_token_path", lambda: tmp_path / "tokens.json")

    error_payload = {
        "error": "invalid_grant",
        "error_description": "Invalid user credentials",
    }
    with aioresponses() as m:
        m.post(KEYCLOAK_TOKEN_URL, payload=error_payload, status=401)
        async with aiohttp.ClientSession() as session:
            with pytest.raises(AuthError) as exc_info:
                await login(session, "user@example.com", "wrongpassword")

    assert exc_info.value.status == 401
    assert "invalid_grant" in str(exc_info.value)


# ---------------------------------------------------------------------------
# refresh()
# ---------------------------------------------------------------------------


async def test_refresh_success(tmp_path, monkeypatch, expired_access_tokens) -> None:
    import aiohttp

    import yunoheat.auth as auth_module

    monkeypatch.setattr(auth_module, "_token_path", lambda: tmp_path / "tokens.json")

    resp_data = load_fixture("token_response")
    with aioresponses() as m:
        m.post(KEYCLOAK_TOKEN_URL, payload=resp_data, status=200)
        async with aiohttp.ClientSession() as session:
            new_tokens = await refresh(session, expired_access_tokens)

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
    tmp_path, monkeypatch, expired_access_tokens
) -> None:
    import aiohttp

    import yunoheat.auth as auth_module

    monkeypatch.setattr(auth_module, "_token_path", lambda: tmp_path / "tokens.json")

    resp_data = load_fixture("token_response")
    with aioresponses() as m:
        m.post(KEYCLOAK_TOKEN_URL, payload=resp_data, status=200)
        async with aiohttp.ClientSession() as session:
            result = await get_valid_tokens(session, expired_access_tokens)

    assert result.access_token == resp_data["access_token"]


async def test_get_valid_tokens_both_expired_raises(fully_expired_tokens) -> None:
    import aiohttp

    async with aiohttp.ClientSession() as session:
        with pytest.raises(TokenExpiredError):
            await get_valid_tokens(session, fully_expired_tokens)
