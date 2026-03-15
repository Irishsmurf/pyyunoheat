"""Consumption models: usage events and aggregated usage reports."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class UsageEventFields(BaseModel):
    """The ``fields`` dict inside a usage event. All values arrive as strings."""

    model_config = ConfigDict(populate_by_name=True)

    property_code: str | None = Field(default=None, alias="property")  # e.g. "GFW296"
    identifier: str | None = None  # meter serial
    session_id: str | None = None
    meter_value: str | None = None  # cumulative kWh as a string
    reading_type: str | None = None  # "A" = actual reading
    time_of_read: str | None = None  # epoch ms as a string
    meter_value_unit: str | None = None  # "kWh"

    @property
    def time_of_read_dt(self) -> datetime | None:
        """Convert time_of_read epoch-ms string to a UTC datetime."""
        if self.time_of_read is None:
            return None
        return datetime.fromtimestamp(int(self.time_of_read) / 1000, tz=UTC)

    @property
    def meter_value_kwh(self) -> float | None:
        """Return the cumulative meter reading as a float kWh value."""
        return float(self.meter_value) if self.meter_value is not None else None


class UsageEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_id: int
    event_code: str | None = None
    amount_with_discount: float | None = None  # EUR cost for this period
    quantity: float | None = None  # kWh consumed in this period
    identifier: str | None = None
    created_at: int | None = None  # epoch ms
    service_type: str | None = None
    fields: UsageEventFields | None = None

    @property
    def created_at_dt(self) -> datetime | None:
        if self.created_at is None:
            return None
        return datetime.fromtimestamp(self.created_at / 1000, tz=UTC)


class UsageEventsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    objects: list[UsageEvent] = []
    total_num: int = 0


class DailyReading(BaseModel):
    """A single interval's data point parsed from the /reports/usage response."""

    model_config = ConfigDict(populate_by_name=True)

    date: datetime  # UTC start of the interval bucket
    kwh: float  # sum_quantity for the period
    eur: float  # sum_amount for the period


class UsageReport(BaseModel):
    """Parsed result of POST /reports/usage."""

    model_config = ConfigDict(populate_by_name=True)

    interval: str  # "day", "week", "month", etc.
    readings: list[DailyReading] = []
