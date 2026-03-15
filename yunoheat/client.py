"""YunoHeatClient — the main entry point for the pyyunoheat library."""

from __future__ import annotations

import base64
import json
import logging
from datetime import UTC, datetime
from typing import Any, Literal

import aiohttp

from yunoheat.auth import load_tokens, login
from yunoheat.connection import Connection
from yunoheat.const import (
    HEAT_SERVICE_TYPE,
    REPORT_INTERVAL_DAY,
    RESOURCE_EURO,
)
from yunoheat.exceptions import AuthError, EntityDiscoveryError
from yunoheat.models.account import (
    EntityContext,
    PaymentGroupsResponse,
    PersonCustomer,
    PropertyCustomersResponse,
)
from yunoheat.models.billing import (
    Bill,
    BillsResponse,
    CreditBalancesResponse,
    OpenBillDue,
)
from yunoheat.models.consumption import (
    DailyReading,
    UsageEventsResponse,
    UsageReport,
)

_LOGGER = logging.getLogger(__name__)


class YunoHeatClient:
    """Async client for the Yuno Energy Heat API.

    Typical usage::

        async with await YunoHeatClient.login(email, password) as client:
            balance = await client.get_open_bill_due()
            events  = await client.get_usage_events(date_from=..., date_to=...)
            report  = await client.get_usage_report(date_from=..., date_to=...)

    Parameters
    ----------
    connection:
        Configured and authenticated ``Connection``.
    context:
        Pre-resolved entity context. If ``None``, resolved lazily on first
        API call via ``_bootstrap()``.
    """

    def __init__(
        self,
        connection: Connection,
        context: EntityContext | None = None,
    ) -> None:
        self._conn = connection
        self._context: EntityContext | None = context

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    @classmethod
    async def login(
        cls,
        username: str,
        password: str,
        *,
        session: aiohttp.ClientSession | None = None,
    ) -> YunoHeatClient:
        """Authenticate with username/password, save tokens, and return a client.

        Entity discovery is deferred until the first data access.
        """
        _session = session or aiohttp.ClientSession()
        tokens = await login(_session, username, password)
        conn = Connection(tokens, username=username, password=password, session=_session)
        # Mark as owned only when we created the session
        if session is None:
            conn._session_owned = True
        return cls(conn)

    @classmethod
    async def from_saved_tokens(
        cls,
        username: str | None = None,
        password: str | None = None,
    ) -> YunoHeatClient:
        """Load tokens from ``~/.config/yunoheat/tokens.json`` and return a client.

        Raises ``AuthError`` if no tokens are saved on disk.
        If ``username``/``password`` are supplied they are stored on the
        ``Connection`` for automatic re-login when the refresh token expires.
        """
        tokens = load_tokens()
        if tokens is None:
            raise AuthError(
                "No saved tokens found. Call YunoHeatClient.login() first."
            )
        conn = Connection(tokens, username=username, password=password)
        return cls(conn)

    # ------------------------------------------------------------------
    # Bootstrap (entity discovery)
    # ------------------------------------------------------------------

    async def _bootstrap(self) -> EntityContext:
        """Run the 4-step entity discovery flow and cache the result."""
        if self._context is not None:
            return self._context

        # Step 1 — decode JWT claims (no signature verification needed)
        claims = self._decode_jwt_claims(self._conn._tokens.access_token)
        customer_id: int = int(claims["customer_id"])
        customer_code: str = claims["customer_code"]

        # Step 2 — fetch person customer (not strictly needed here but confirms reachability)
        _LOGGER.debug("Bootstrap: fetching person customer %s", customer_code)
        await self._conn.get(f"/customers/{customer_code}")

        # Step 3 — fetch payment group (links person → property)
        _LOGGER.debug("Bootstrap: fetching payment groups for customer %d", customer_id)
        groups_raw = await self._conn.get(
            f"/customers/{customer_id}/groups", params={"type": "payment"}
        )
        groups = PaymentGroupsResponse.model_validate(groups_raw)
        if not groups.objects:
            raise EntityDiscoveryError(
                f"No payment groups found for customer {customer_id}."
            )
        group = groups.objects[0]
        payment_group_id = group.id
        person_billing_profile_id: int | None = (
            group.owner_billing_profile.get("id") if group.owner_billing_profile else None
        )

        # Step 4 — fetch property customer(s) via payment group
        _LOGGER.debug("Bootstrap: fetching property customers for group %d", payment_group_id)
        props_raw = await self._conn.get(
            "/customers", params={"parent-group": payment_group_id}
        )
        props = PropertyCustomersResponse.model_validate(props_raw)
        if not props.objects:
            raise EntityDiscoveryError(
                f"No property customers found for payment group {payment_group_id}."
            )
        prop = props.objects[0]

        self._context = EntityContext(
            person_customer_id=customer_id,
            person_customer_code=customer_code,
            person_billing_profile_id=person_billing_profile_id,
            payment_group_id=payment_group_id,
            property_customer_id=prop.id,
            property_subscription_id=prop.subscription_id,
            property_balance_group_id=prop.balance_group_id,
            meter_identifier=prop.meter_identifier,
        )
        _LOGGER.debug("Bootstrap complete: %s", self._context)
        return self._context

    async def _ctx(self) -> EntityContext:
        """Return the cached entity context, bootstrapping if necessary."""
        return await self._bootstrap()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _decode_jwt_claims(access_token: str) -> dict[str, Any]:
        """Decode JWT payload without signature verification using standard base64."""
        parts = access_token.split(".")
        if len(parts) < 2:
            raise ValueError("Malformed JWT: expected at least 2 segments")
        # Restore base64 padding
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(payload_b64))

    @staticmethod
    def _dt_to_epoch_ms(dt: datetime) -> int:
        """Convert a datetime to epoch milliseconds."""
        return int(dt.timestamp() * 1000)

    @staticmethod
    def _build_usage_report_query(
        property_customer_id: int,
        date_from: datetime,
        date_to: datetime,
        interval: str,
    ) -> dict[str, Any]:
        """Construct the Elasticsearch DSL body for POST /reports/usage."""
        fmt = "%Y-%m-%dT%H:%M:%S.000Z"
        gte = date_from.astimezone(UTC).strftime(fmt)
        lte = date_to.astimezone(UTC).strftime(fmt)

        return {
            "size": 0,
            "query": {
                "bool": {
                    "filter": {
                        "nested": {
                            "path": "event_fields",
                            "query": {
                                "range": {
                                    "event_fields.time_of_read.date": {
                                        "gte": gte,
                                        "lte": lte,
                                    }
                                }
                            },
                        }
                    },
                    "must": [
                        {
                            "query_string": {
                                "query": f"({HEAT_SERVICE_TYPE})",
                                "analyze_wildcard": True,
                                "fields": ["service_type"],
                            }
                        },
                        {
                            "query_string": {
                                "query": str(property_customer_id),
                                "analyze_wildcard": True,
                                "fields": ["customer_id"],
                            }
                        },
                        {
                            "terms": {
                                "resource_name": ["Heat - Meter Value", "Euro"]
                            }
                        },
                    ],
                }
            },
            "aggs": {
                "chart": {
                    "terms": {"field": "resource_name"},
                    "aggs": {
                        "by_amount": {
                            "nested": {"path": "event_fields"},
                            "aggs": {
                                "history": {
                                    "date_histogram": {
                                        "field": "event_fields.time_of_read.date",
                                        "interval": interval,
                                        "min_doc_count": 0,
                                        "time_zone": "+00:00",
                                        "extended_bounds": {"min": gte, "max": lte},
                                    },
                                    "aggs": {
                                        "reverse": {
                                            "reverse_nested": {},
                                            "aggs": {
                                                "sum_amount": {"sum": {"field": "amount"}}
                                            },
                                        }
                                    },
                                }
                            },
                        },
                        "by_quantity": {
                            "nested": {"path": "event_fields"},
                            "aggs": {
                                "history": {
                                    "date_histogram": {
                                        "field": "event_fields.time_of_read.date",
                                        "interval": interval,
                                        "min_doc_count": 0,
                                        "time_zone": "+00:00",
                                        "extended_bounds": {"min": gte, "max": lte},
                                    },
                                    "aggs": {
                                        "reverse": {
                                            "reverse_nested": {},
                                            "aggs": {
                                                "sum_quantity": {"sum": {"field": "quantity"}}
                                            },
                                        }
                                    },
                                }
                            },
                        },
                    },
                }
            },
        }

    @staticmethod
    def _parse_usage_report(raw: dict[str, Any], interval: str) -> UsageReport:
        """Parse the ES aggregation response into a UsageReport."""
        buckets: list[dict[str, Any]] = (
            raw.get("aggregations", {})
            .get("chart", {})
            .get("buckets", [])
        )

        euro_bucket: dict[str, Any] | None = None
        for b in buckets:
            if b.get("key") == RESOURCE_EURO:
                euro_bucket = b
                break

        if euro_bucket is None:
            return UsageReport(interval=interval, readings=[])

        amount_buckets = (
            euro_bucket.get("by_amount", {})
            .get("history", {})
            .get("buckets", [])
        )
        quantity_buckets = (
            euro_bucket.get("by_quantity", {})
            .get("history", {})
            .get("buckets", [])
        )

        # Index quantity by epoch-ms key for O(1) lookup
        qty_by_key: dict[int, float] = {
            b["key"]: b.get("reverse", {}).get("sum_quantity", {}).get("value", 0.0)
            for b in quantity_buckets
        }

        readings: list[DailyReading] = []
        for b in amount_buckets:
            key_ms: int = b["key"]
            eur = b.get("reverse", {}).get("sum_amount", {}).get("value", 0.0)
            kwh = qty_by_key.get(key_ms, 0.0)
            dt = datetime.fromtimestamp(key_ms / 1000, tz=UTC)
            readings.append(DailyReading(date=dt, kwh=kwh or 0.0, eur=eur or 0.0))

        return UsageReport(interval=interval, readings=readings)

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    async def get_person_customer(self) -> PersonCustomer:
        """Return the person customer record."""
        ctx = await self._ctx()
        raw = await self._conn.get(f"/customers/{ctx.person_customer_code}")
        return PersonCustomer.model_validate(raw)

    async def get_open_bill_due(self) -> OpenBillDue:
        """Return the current outstanding balance in EUR."""
        ctx = await self._ctx()
        raw = await self._conn.get(f"/customers/{ctx.person_customer_id}/open-bill-due")
        return OpenBillDue.model_validate(raw)

    async def get_credit_balances(self) -> CreditBalancesResponse:
        """Return credit balance(s) for the person customer."""
        ctx = await self._ctx()
        params: dict[str, Any] = {"customer": ctx.person_customer_id}
        if ctx.person_billing_profile_id is not None:
            params["billing-profile"] = ctx.person_billing_profile_id
        raw = await self._conn.get("/credit-balances", params=params)
        return CreditBalancesResponse.model_validate(raw)

    async def get_usage_events(
        self,
        *,
        date_from: datetime,
        date_to: datetime,
        page: int = 1,
        count: int = 50,
        order: Literal["asc", "desc"] = "desc",
    ) -> UsageEventsResponse:
        """Return paginated meter reading events for the property.

        Parameters
        ----------
        date_from / date_to:
            Inclusive date range. Timezone-aware datetimes are recommended;
            naive datetimes are treated as UTC.
        page:
            1-indexed page number.
        count:
            Results per page (max determined by the API).
        order:
            ``"desc"`` (newest first) or ``"asc"`` (oldest first).
        """
        ctx = await self._ctx()
        params: dict[str, Any] = {
            "time-from": self._dt_to_epoch_ms(date_from),
            "time-to": self._dt_to_epoch_ms(date_to),
            "service-type": HEAT_SERVICE_TYPE,
            "page": page,
            "count": count,
            "order-dir": order,
        }
        if ctx.property_balance_group_id is not None:
            params["balance-group"] = ctx.property_balance_group_id
        if ctx.meter_identifier is not None:
            params["identifier"] = ctx.meter_identifier
        raw = await self._conn.get(
            f"/customers/{ctx.property_customer_id}/usage-events", params=params
        )
        return UsageEventsResponse.model_validate(raw)

    async def get_usage_report(
        self,
        *,
        date_from: datetime,
        date_to: datetime,
        interval: str = REPORT_INTERVAL_DAY,
    ) -> UsageReport:
        """Return aggregated kWh and EUR data over a date range.

        Parameters
        ----------
        interval:
            Bucket size — one of ``"day"``, ``"week"``, ``"month"``,
            ``"quarter"``, ``"year"``.
        """
        ctx = await self._ctx()
        body = self._build_usage_report_query(
            ctx.property_customer_id, date_from, date_to, interval
        )
        raw = await self._conn.post("/reports/usage", json=body)
        return self._parse_usage_report(raw, interval)

    async def get_invoices(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        count: int = 10,
    ) -> BillsResponse:
        """Return paginated bills for the person customer."""
        ctx = await self._ctx()
        params: dict[str, Any] = {"page": page, "count": count}
        if date_from is not None:
            params["time-from"] = self._dt_to_epoch_ms(date_from)
        if date_to is not None:
            params["time-to"] = self._dt_to_epoch_ms(date_to)
        raw = await self._conn.get(
            f"/customers/{ctx.person_customer_id}/bills", params=params
        )
        if isinstance(raw, list):
            objects = [Bill.model_validate(i) for i in raw]
            return BillsResponse(objects=objects, total_num=len(objects))
        return BillsResponse.model_validate(raw)

    async def get_bill(self, bill_id: int) -> Bill:
        """Return a specific bill by ID."""
        ctx = await self._ctx()
        raw = await self._conn.get(
            f"/customers/{ctx.property_customer_id}/bills/{bill_id}"
        )
        return Bill.model_validate(raw)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying connection."""
        await self._conn.close()

    async def __aenter__(self) -> YunoHeatClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
