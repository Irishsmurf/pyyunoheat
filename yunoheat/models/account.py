"""Account models: person customer, property customer, entity context."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ContactInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    address: str | None = None
    city: str | None = None
    zip: str | None = None
    phone: str | None = None


class CreditCard(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    card_type: str | None = None
    last_4: str | None = None
    expiration_month: int | None = None
    expiration_year: int | None = None


class PayInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    method: str | None = None
    default_credit_card: CreditCard | None = None


class BalanceGroupRef(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int


class SubscriptionRef(BaseModel):
    """Lightweight subscription reference as it appears on a customer object."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    code: str | None = None
    name: str | None = None
    status: str | None = None
    # Present on property customer subscriptions but absent on person customer subscriptions
    balance_group: BalanceGroupRef | None = None


class ServiceType(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    code: str
    mandatory_fields: str | None = None


class Service(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    identifier: str  # e.g. "04801107" — the meter serial
    service_type: ServiceType | None = None


class PersonCustomer(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    code: str  # UUID
    status: str | None = None
    contact_infos: list[ContactInfo] = []
    pay_info: PayInfo | None = None
    subscriptions: list[SubscriptionRef] = []
    custom_attributes: dict[str, str] = {}


class PropertyCustomer(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    code: str | None = None
    status: str | None = None
    subscriptions: list[SubscriptionRef] = []
    services: list[Service] = []

    @property
    def meter_identifier(self) -> str | None:
        """Return the heat meter serial from the first heat service."""
        for svc in self.services:
            if svc.service_type and "HEAT" in svc.service_type.code:
                return svc.identifier
        return self.services[0].identifier if self.services else None

    @property
    def subscription_id(self) -> int | None:
        return self.subscriptions[0].id if self.subscriptions else None

    @property
    def balance_group_id(self) -> int | None:
        if self.subscriptions and self.subscriptions[0].balance_group:
            return self.subscriptions[0].balance_group.id
        return None


class PaymentGroup(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    type: str | None = None
    name: str | None = None
    owner: dict[str, Any] = {}
    owner_billing_profile: dict[str, Any] = {}


class PaymentGroupsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    objects: list[PaymentGroup] = []
    total_num: int = 0


class PropertyCustomersResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    objects: list[PropertyCustomer] = []
    total_num: int = 0


class EntityContext(BaseModel):
    """Resolved entity IDs cached after the 4-step discovery flow.

    Not returned directly from the API — computed by YunoHeatClient._bootstrap().
    """

    model_config = ConfigDict(populate_by_name=True)

    person_customer_id: int
    person_customer_code: str  # UUID
    person_billing_profile_id: int | None = None
    payment_group_id: int
    property_customer_id: int
    property_subscription_id: int | None = None
    property_balance_group_id: int | None = None
    meter_identifier: str | None = None
