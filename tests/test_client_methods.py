"""Tests for YunoHeatClient public API methods."""

from __future__ import annotations

import re
from datetime import UTC, datetime

import pytest
from aioresponses import aioresponses

from tests.conftest import load_fixture
from yunoheat.client import YunoHeatClient
from yunoheat.connection import Connection
from yunoheat.const import API_BASE_URL
from yunoheat.models.account import EntityContext

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Pre-baked entity context — skip bootstrap in method tests
_CTX = EntityContext(
    person_customer_id=232971,
    person_customer_code="b21afb1f-1e10-4d17-bf8a-cebd07daf40a",
    person_billing_profile_id=47891,
    payment_group_id=32762,
    property_customer_id=201411,
    property_subscription_id=14582,
    property_balance_group_id=14583,
    meter_identifier="04801107",
)


def make_client(valid_tokens) -> YunoHeatClient:
    """Return a YunoHeatClient with the context pre-seeded (no bootstrap needed)."""
    conn = Connection(valid_tokens)
    return YunoHeatClient(conn, context=_CTX)


# ---------------------------------------------------------------------------
# get_person_customer
# ---------------------------------------------------------------------------


async def test_get_person_customer(valid_tokens) -> None:
    client = make_client(valid_tokens)
    fixture = load_fixture("customer")
    try:
        with aioresponses() as m:
            m.get(
                f"{API_BASE_URL}/customers/b21afb1f-1e10-4d17-bf8a-cebd07daf40a",
                payload=fixture,
            )
            person = await client.get_person_customer()
    finally:
        await client.close()

    assert person.id == 232971
    assert person.code == "b21afb1f-1e10-4d17-bf8a-cebd07daf40a"
    assert person.status == "active"
    assert person.contact_infos[0].email == "user@example.com"


# ---------------------------------------------------------------------------
# get_open_bill_due
# ---------------------------------------------------------------------------


async def test_get_open_bill_due(valid_tokens) -> None:
    client = make_client(valid_tokens)
    fixture = load_fixture("open_bill_due")
    try:
        with aioresponses() as m:
            m.get(
                f"{API_BASE_URL}/customers/232971/open-bill-due",
                payload=fixture,
            )
            result = await client.get_open_bill_due()
    finally:
        await client.close()

    assert result.open_bill_due == pytest.approx(87.83)


# ---------------------------------------------------------------------------
# get_usage_events
# ---------------------------------------------------------------------------


async def test_get_usage_events(valid_tokens) -> None:
    client = make_client(valid_tokens)
    fixture = load_fixture("usage_events")
    date_from = datetime(2026, 3, 13, tzinfo=UTC)
    date_to = datetime(2026, 3, 15, tzinfo=UTC)

    try:
        with aioresponses() as m:
            m.get(
                re.compile(rf"{re.escape(API_BASE_URL)}/customers/201411/usage-events.*"),
                payload=fixture,
            )
            result = await client.get_usage_events(date_from=date_from, date_to=date_to)
    finally:
        await client.close()

    assert result.total_num == 2
    assert len(result.objects) == 2

    first = result.objects[0]
    assert first.event_id == 17886462
    assert first.quantity == pytest.approx(5.0)
    assert first.amount_with_discount == pytest.approx(1.306)
    assert first.fields is not None
    assert first.fields.meter_value == "9809"
    assert first.fields.meter_value_kwh == pytest.approx(9809.0)
    assert first.fields.time_of_read_dt is not None


# ---------------------------------------------------------------------------
# get_usage_report
# ---------------------------------------------------------------------------


async def test_get_usage_report_daily(valid_tokens) -> None:
    client = make_client(valid_tokens)
    fixture = load_fixture("usage_report")
    date_from = datetime(2026, 3, 13, tzinfo=UTC)
    date_to = datetime(2026, 3, 15, tzinfo=UTC)

    try:
        with aioresponses() as m:
            m.post(f"{API_BASE_URL}/reports/usage", payload=fixture)
            report = await client.get_usage_report(date_from=date_from, date_to=date_to)
    finally:
        await client.close()

    assert report.interval == "day"
    assert len(report.readings) == 2

    # Readings should be in the order returned by the Euro bucket's by_amount histogram
    r0, r1 = report.readings
    assert r0.kwh == pytest.approx(4.0)
    assert r0.eur == pytest.approx(1.182)
    assert r1.kwh == pytest.approx(5.0)
    assert r1.eur == pytest.approx(1.306)


async def test_get_usage_report_empty_response(valid_tokens) -> None:
    client = make_client(valid_tokens)
    date_from = datetime(2026, 3, 1, tzinfo=UTC)
    date_to = datetime(2026, 3, 2, tzinfo=UTC)

    try:
        with aioresponses() as m:
            m.post(
                f"{API_BASE_URL}/reports/usage",
                payload={"aggregations": {"chart": {"buckets": []}}},
            )
            report = await client.get_usage_report(date_from=date_from, date_to=date_to)
    finally:
        await client.close()

    assert report.readings == []


# ---------------------------------------------------------------------------
# get_invoices
# ---------------------------------------------------------------------------


async def test_get_invoices(valid_tokens) -> None:
    client = make_client(valid_tokens)
    fixture = load_fixture("invoices")

    try:
        with aioresponses() as m:
            m.get(
                re.compile(rf"{re.escape(API_BASE_URL)}/customers/232971/bills.*"),
                payload=fixture,
            )
            result = await client.get_invoices()
    finally:
        await client.close()

    assert result.total_num == 1
    assert len(result.objects) == 1
    bill = result.objects[0]
    assert bill.id == 100001
    assert bill.due_amount == pytest.approx(38.50)
    assert bill.valid_from_dt is not None


# ---------------------------------------------------------------------------
# get_bill
# ---------------------------------------------------------------------------


async def test_get_bill(valid_tokens) -> None:
    client = make_client(valid_tokens)
    bill_fixture = {
        "id": 791134,
        "status": "active",
        "valid_from": 1773269943547,
        "valid_to": 253370764800000,
        "due_amount": 5.224,
        "total_amount": 5.224,
        "customer": {"id": 201411},
        "billing_profile": {"id": 14284},
    }

    try:
        with aioresponses() as m:
            m.get(
                f"{API_BASE_URL}/customers/201411/bills/791134",
                payload=bill_fixture,
            )
            bill = await client.get_bill(791134)
    finally:
        await client.close()

    assert bill.id == 791134
    assert bill.status == "active"
    assert bill.due_amount == pytest.approx(5.224)
    assert bill.valid_from_dt is not None
