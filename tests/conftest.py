"""Shared pytest fixtures for pyyunoheat tests."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

from yunoheat.auth import TokenData
from yunoheat.connection import Connection

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> Any:
    """Load a JSON fixture file by name (without .json extension)."""
    return json.loads((FIXTURES_DIR / f"{name}.json").read_text())


# ---------------------------------------------------------------------------
# Token fixtures
# ---------------------------------------------------------------------------

# A fake JWT with the right claims. Decoded payload:
# {"sub": "a4b3f7fd-...", "customer_id": 232971,
#  "customer_code": "b21afb1f-1e10-4d17-bf8a-cebd07daf40a",
#  "preferred_username": "user@example.com", "exp": 9999999999}
FAKE_ACCESS_TOKEN = (
    "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJzdWIiOiJhNGIzZjdmZC05NGNjLTQyYzgtYjcxNy1kYzM5MjA3ZjQwZDIiLCJjdXN0b21lcl9pZCI6MjMyOTcxLCJjdXN0b21lcl9jb2RlIjoiYjIxYWZiMWYtMWUxMC00ZDE3LWJmOGEtY2ViZDA3ZGFmNDBhIiwicHJlZmVycmVkX3VzZXJuYW1lIjoidXNlckBleGFtcGxlLmNvbSIsImV4cCI6OTk5OTk5OTk5OX0"
    ".signature"
)
FAKE_REFRESH_TOKEN = "fake-refresh-token"


@pytest.fixture
def valid_tokens() -> TokenData:
    """Return a TokenData that is fully valid (not expired)."""
    now = time.time()
    return TokenData(
        access_token=FAKE_ACCESS_TOKEN,
        refresh_token=FAKE_REFRESH_TOKEN,
        access_expires_at=now + 1800,
        refresh_expires_at=now + 2100,
    )


@pytest.fixture
def expired_access_tokens() -> TokenData:
    """Access token expired, refresh token still valid."""
    now = time.time()
    return TokenData(
        access_token=FAKE_ACCESS_TOKEN,
        refresh_token=FAKE_REFRESH_TOKEN,
        access_expires_at=now - 10,  # expired 10 s ago
        refresh_expires_at=now + 2100,
    )


@pytest.fixture
def fully_expired_tokens() -> TokenData:
    """Both access and refresh tokens expired."""
    now = time.time()
    return TokenData(
        access_token=FAKE_ACCESS_TOKEN,
        refresh_token=FAKE_REFRESH_TOKEN,
        access_expires_at=now - 200,
        refresh_expires_at=now - 10,
    )


# ---------------------------------------------------------------------------
# Connection factory
# ---------------------------------------------------------------------------

def make_connection(tokens: TokenData) -> Connection:
    """Create a Connection with the given tokens (no stored credentials)."""
    return Connection(tokens)
