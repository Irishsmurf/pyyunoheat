"""Integration tests — hit the real Yuno Energy Heat API.

Run with:
    pytest tests/integration/ -v

Skipped automatically when YUNOHEAT_EMAIL / YUNOHEAT_PASSWORD are not set.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest

from yunoheat import YunoHeatClient
from yunoheat.models.account import EntityContext

pytestmark = pytest.mark.skipif(
    not os.getenv("YUNOHEAT_EMAIL") or not os.getenv("YUNOHEAT_PASSWORD"),
    reason="Set YUNOHEAT_EMAIL and YUNOHEAT_PASSWORD in .env to run integration tests",
)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


async def test_login_obtains_tokens(tmp_path, monkeypatch) -> None:
    """Fresh login should return valid tokens and persist them to disk."""

    import yunoheat.auth as auth_module

    token_file = tmp_path / "tokens.json"
    monkeypatch.setattr(auth_module, "_token_path", lambda: token_file)

    from tests.integration.conftest import _EMAIL, _PASSWORD

    client = await YunoHeatClient.login(_EMAIL, _PASSWORD)  # type: ignore[arg-type]
    await client.close()

    assert token_file.exists(), "tokens.json should have been written after login"
    tokens = auth_module.load_tokens()
    assert tokens is not None
    assert tokens.access_is_valid()
    assert tokens.refresh_is_valid()


async def test_from_saved_tokens(client: YunoHeatClient) -> None:
    """Loading saved tokens should produce a working client without re-logging in."""
    # The `client` fixture already called from_saved_tokens or login.
    # Confirm the connection holds a valid access token.
    assert client._conn._tokens.access_is_valid()


# ---------------------------------------------------------------------------
# Entity discovery (bootstrap)
# ---------------------------------------------------------------------------


async def test_bootstrap_resolves_context(client: YunoHeatClient) -> None:
    """The 4-step entity discovery flow should populate all key IDs."""
    ctx: EntityContext = await client._ctx()

    assert ctx.person_customer_id > 0
    assert ctx.person_customer_code  # non-empty UUID string
    assert ctx.payment_group_id > 0
    assert ctx.property_customer_id > 0
    assert ctx.meter_identifier  # e.g. "04801107"


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------


async def test_get_person_customer(client: YunoHeatClient) -> None:
    person = await client.get_person_customer()

    assert person.id > 0
    assert person.status == "active"
    assert len(person.contact_infos) > 0
    assert "@" in (person.contact_infos[0].email or "")


async def test_get_open_bill_due(client: YunoHeatClient) -> None:
    result = await client.get_open_bill_due()

    assert isinstance(result.open_bill_due, float)
    assert result.open_bill_due >= 0


async def test_get_credit_balances(client: YunoHeatClient) -> None:
    result = await client.get_credit_balances()

    assert isinstance(result.objects, list)
    # Balance can be zero but the structure should be present
    for b in result.objects:
        assert isinstance(b.amount, float)


# ---------------------------------------------------------------------------
# Meter readings
# ---------------------------------------------------------------------------


async def test_get_usage_events_last_30_days(client: YunoHeatClient) -> None:
    now = datetime.now(UTC)
    result = await client.get_usage_events(
        date_from=now - timedelta(days=30),
        date_to=now,
        count=10,
    )

    assert isinstance(result.objects, list)
    assert result.total_num >= 0

    if result.objects:
        event = result.objects[0]
        assert event.event_id > 0
        assert event.quantity is not None and event.quantity >= 0
        assert event.amount_with_discount is not None
        assert event.fields is not None
        assert event.fields.time_of_read_dt is not None
        assert event.fields.meter_value_kwh is not None


async def test_usage_events_ordered_desc(client: YunoHeatClient) -> None:
    """Default order=desc should return newest events first."""
    now = datetime.now(UTC)
    result = await client.get_usage_events(
        date_from=now - timedelta(days=30),
        date_to=now,
        count=5,
        order="desc",
    )

    if len(result.objects) >= 2:
        timestamps = [
            int(e.fields.time_of_read or "0")
            for e in result.objects
            if e.fields and e.fields.time_of_read
        ]
        assert timestamps == sorted(timestamps, reverse=True), (
            "Events should be sorted newest-first"
        )


# ---------------------------------------------------------------------------
# Usage report
# ---------------------------------------------------------------------------


async def test_get_usage_report_daily(client: YunoHeatClient) -> None:
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    report = await client.get_usage_report(date_from=month_start, date_to=now)

    assert report.interval == "day"
    assert isinstance(report.readings, list)

    # At least some readings should exist for the current month
    non_zero = [r for r in report.readings if r.kwh > 0]
    assert len(non_zero) > 0, "Expected at least one day with non-zero kWh this month"

    for reading in non_zero:
        assert reading.kwh > 0
        assert reading.eur >= 0
        assert reading.date.tzinfo is not None


async def test_get_usage_report_weekly(client: YunoHeatClient) -> None:
    now = datetime.now(UTC)
    report = await client.get_usage_report(
        date_from=now - timedelta(days=60),
        date_to=now,
        interval="week",
    )

    assert report.interval == "week"
    assert len(report.readings) > 0


# ---------------------------------------------------------------------------
# Billing
# ---------------------------------------------------------------------------


async def test_get_invoices(client: YunoHeatClient) -> None:
    result = await client.get_invoices()

    assert isinstance(result.objects, list)
    if result.objects:
        bill = result.objects[0]
        assert bill.id > 0
