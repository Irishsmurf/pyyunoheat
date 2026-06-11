"""Integration test configuration.

Requires real credentials in the .env file (or environment variables):

    YUNOHEAT_EMAIL=you@example.com
    YUNOHEAT_PASSWORD=yourpassword

All tests in this directory are skipped automatically when those variables
are not set.
"""

from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv

from yunoheat import YunoHeatClient
from yunoheat.auth import load_tokens

load_dotenv()

_EMAIL = os.getenv("YUNOHEAT_EMAIL")
_PASSWORD = os.getenv("YUNOHEAT_PASSWORD")

_CREDS_MISSING = not _EMAIL or not _PASSWORD

pytestmark = pytest.mark.skipif(
    _CREDS_MISSING,
    reason="Set YUNOHEAT_EMAIL and YUNOHEAT_PASSWORD in .env to run integration tests",
)


@pytest.fixture
async def client():
    """Authenticated YunoHeatClient.

    Loads saved tokens from disk when available (fast); falls back to a full
    login only when no tokens exist. Credentials are kept on the Connection so
    the library can silently re-authenticate when the refresh token expires.
    """
    tokens = await load_tokens()
    if tokens is not None:
        c = await YunoHeatClient.from_saved_tokens(username=_EMAIL, password=_PASSWORD)
    else:
        c = await YunoHeatClient.login(_EMAIL, _PASSWORD)  # type: ignore[arg-type]

    async with c:
        yield c
