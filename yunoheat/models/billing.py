"""Billing models: bills, invoices, balances."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class Bill(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    status: str | None = None  # "active", "billing", "closed", "inactive"
    valid_from: int | None = None  # epoch ms
    valid_to: int | None = None  # epoch ms
    due_amount: float | None = None  # EUR
    total_amount: float | None = None  # EUR
    customer: dict[str, Any] = {}
    billing_profile: dict[str, Any] = {}

    @property
    def valid_from_dt(self) -> datetime | None:
        if self.valid_from is None:
            return None
        return datetime.fromtimestamp(self.valid_from / 1000, tz=UTC)

    @property
    def valid_to_dt(self) -> datetime | None:
        if self.valid_to is None:
            return None
        return datetime.fromtimestamp(self.valid_to / 1000, tz=UTC)


class OpenBillDue(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    open_bill_due: float  # EUR


class CreditBalance(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    amount: float


class CreditBalancesResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    objects: list[CreditBalance] = []
    total_num: int = 0


class Invoice(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    status: str | None = None
    start_time: int | None = None  # epoch ms
    end_time: int | None = None  # epoch ms
    due_amount: float | None = None  # EUR
    total_amount: float | None = None  # EUR
    payment_due: int | None = None  # epoch ms

    @property
    def start_dt(self) -> datetime | None:
        if self.start_time is None:
            return None
        return datetime.fromtimestamp(self.start_time / 1000, tz=UTC)

    @property
    def end_dt(self) -> datetime | None:
        if self.end_time is None:
            return None
        return datetime.fromtimestamp(self.end_time / 1000, tz=UTC)

    @property
    def payment_due_dt(self) -> datetime | None:
        if self.payment_due is None:
            return None
        return datetime.fromtimestamp(self.payment_due / 1000, tz=UTC)


class InvoicesResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    objects: list[Invoice] = []
    total_num: int = 0
