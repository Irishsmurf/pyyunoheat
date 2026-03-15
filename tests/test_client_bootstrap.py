"""Tests for YunoHeatClient entity discovery bootstrap."""

from __future__ import annotations

import re

import pytest
from aioresponses import aioresponses

from tests.conftest import load_fixture
from yunoheat.client import YunoHeatClient
from yunoheat.connection import Connection
from yunoheat.const import API_BASE_URL
from yunoheat.exceptions import EntityDiscoveryError

# Compiled regex patterns for endpoints that include query params
_RE_CUSTOMER_UUID = re.compile(
    rf"{re.escape(API_BASE_URL)}/customers/b21afb1f-1e10-4d17-bf8a-cebd07daf40a.*"
)
_RE_GROUPS = re.compile(rf"{re.escape(API_BASE_URL)}/customers/232971/groups.*")
_RE_CUSTOMERS_ROOT = re.compile(rf"{re.escape(API_BASE_URL)}/customers\?.*")


def make_client(valid_tokens) -> YunoHeatClient:
    conn = Connection(valid_tokens)
    return YunoHeatClient(conn)


# ---------------------------------------------------------------------------
# Bootstrap resolves entity context
# ---------------------------------------------------------------------------


async def test_bootstrap_resolves_entity_context(valid_tokens) -> None:
    client = make_client(valid_tokens)
    customer = load_fixture("customer")
    groups = load_fixture("payment_groups")
    props = load_fixture("property_customers")

    try:
        with aioresponses() as m:
            m.get(_RE_CUSTOMER_UUID, payload=customer)
            m.get(_RE_GROUPS, payload=groups)
            m.get(_RE_CUSTOMERS_ROOT, payload=props)
            ctx = await client._bootstrap()
    finally:
        await client.close()

    assert ctx.person_customer_id == 232971
    assert ctx.person_customer_code == "b21afb1f-1e10-4d17-bf8a-cebd07daf40a"
    assert ctx.person_billing_profile_id == 47891
    assert ctx.payment_group_id == 32762
    assert ctx.property_customer_id == 201411
    assert ctx.property_subscription_id == 14582
    assert ctx.property_balance_group_id == 14583
    assert ctx.meter_identifier == "04801107"


async def test_bootstrap_called_once(valid_tokens) -> None:
    """Second call to _ctx() must not repeat the HTTP calls."""
    client = make_client(valid_tokens)
    customer = load_fixture("customer")
    groups = load_fixture("payment_groups")
    props = load_fixture("property_customers")

    try:
        with aioresponses() as m:
            m.get(_RE_CUSTOMER_UUID, payload=customer)
            m.get(_RE_GROUPS, payload=groups)
            m.get(_RE_CUSTOMERS_ROOT, payload=props)
            await client._ctx()
            # Second call — no more URLs registered; any HTTP call would raise
            ctx2 = await client._ctx()

        assert ctx2.property_customer_id == 201411
    finally:
        await client.close()


# ---------------------------------------------------------------------------
# Bootstrap error cases
# ---------------------------------------------------------------------------


async def test_bootstrap_raises_when_no_payment_groups(valid_tokens) -> None:
    client = make_client(valid_tokens)
    customer = load_fixture("customer")

    try:
        with aioresponses() as m:
            m.get(_RE_CUSTOMER_UUID, payload=customer)
            m.get(_RE_GROUPS, payload={"objects": [], "total_num": 0})
            with pytest.raises(EntityDiscoveryError, match="No payment groups"):
                await client._bootstrap()
    finally:
        await client.close()


async def test_bootstrap_raises_when_no_property_customers(valid_tokens) -> None:
    client = make_client(valid_tokens)
    customer = load_fixture("customer")
    groups = load_fixture("payment_groups")

    try:
        with aioresponses() as m:
            m.get(_RE_CUSTOMER_UUID, payload=customer)
            m.get(_RE_GROUPS, payload=groups)
            m.get(_RE_CUSTOMERS_ROOT, payload={"objects": [], "total_num": 0})
            with pytest.raises(EntityDiscoveryError, match="No property customers"):
                await client._bootstrap()
    finally:
        await client.close()
