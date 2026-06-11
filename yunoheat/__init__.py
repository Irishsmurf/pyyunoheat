"""pyyunoheat — async Python client for the Yuno Energy Heat API."""

from yunoheat.auth import (
    TokenData,
    TokenStore,
    FileTokenStore,
    InMemoryTokenStore,
)
from yunoheat.client import YunoHeatClient
from yunoheat.exceptions import (
    APIConnectionError,
    APIError,
    AuthError,
    ConfigEntryAuthFailed,
    EntityDiscoveryError,
    TokenExpiredError,
    YunoHeatError,
)
from yunoheat.models.account import EntityContext, PersonCustomer, PropertyCustomer
from yunoheat.models.billing import (
    Bill,
    BillsResponse,
    CreditBalance,
    CreditBalancesResponse,
    OpenBillDue,
)
from yunoheat.models.consumption import (
    DailyReading,
    UsageEvent,
    UsageEventsResponse,
    UsageReport,
)

__version__ = "0.2.0"

__all__ = [
    "YunoHeatClient",
    # auth
    "TokenData",
    "TokenStore",
    "FileTokenStore",
    "InMemoryTokenStore",
    # exceptions
    "YunoHeatError",
    "AuthError",
    "ConfigEntryAuthFailed",
    "TokenExpiredError",
    "APIError",
    "APIConnectionError",
    "EntityDiscoveryError",
    # account models
    "PersonCustomer",
    "PropertyCustomer",
    "EntityContext",
    # billing models
    "Bill",
    "BillsResponse",
    "OpenBillDue",
    "CreditBalance",
    "CreditBalancesResponse",
    # consumption models
    "UsageEvent",
    "UsageEventsResponse",
    "UsageReport",
    "DailyReading",
]
