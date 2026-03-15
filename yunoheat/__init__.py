"""pyyunoheat — async Python client for the Yuno Energy Heat API."""

from yunoheat.client import YunoHeatClient
from yunoheat.exceptions import (
    APIError,
    AuthError,
    EntityDiscoveryError,
    TokenExpiredError,
    YunoHeatError,
)
from yunoheat.models.account import EntityContext, PersonCustomer, PropertyCustomer
from yunoheat.models.billing import (
    Bill,
    CreditBalance,
    CreditBalancesResponse,
    Invoice,
    InvoicesResponse,
    OpenBillDue,
)
from yunoheat.models.consumption import (
    DailyReading,
    UsageEvent,
    UsageEventsResponse,
    UsageReport,
)

__version__ = "0.1.0"

__all__ = [
    "YunoHeatClient",
    # exceptions
    "YunoHeatError",
    "AuthError",
    "TokenExpiredError",
    "APIError",
    "EntityDiscoveryError",
    # account models
    "PersonCustomer",
    "PropertyCustomer",
    "EntityContext",
    # billing models
    "Bill",
    "Invoice",
    "InvoicesResponse",
    "OpenBillDue",
    "CreditBalance",
    "CreditBalancesResponse",
    # consumption models
    "UsageEvent",
    "UsageEventsResponse",
    "UsageReport",
    "DailyReading",
]
