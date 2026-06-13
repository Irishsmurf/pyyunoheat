# API Reference

This page describes the classes, models, exception hierarchy, and protocols exported by the `yunoheat` package.

---

## Client: `YunoHeatClient`

The primary class for interacting with the Yuno Energy Heat API.

### Factory Methods

#### `login`
```python
@classmethod
async def login(
    cls,
    username: str,
    password: str,
    *,
    session: aiohttp.ClientSession | None = None,
    token_store: TokenStore | None = None,
) -> YunoHeatClient
```
Authenticates credentials against Keycloak, initializes the client session, and prepares it for API calls. *Note: Entity discovery/bootstrap is deferred until the first data access.*

*   **Parameters**:
    *   `username` (`str`): Keycloak username (usually an email address).
    *   `password` (`str`): Keycloak password.
    *   `session` (`aiohttp.ClientSession`, optional): Shared custom HTTP session. If omitted, one is created and managed internally.
    *   `token_store` (`TokenStore`, optional): Custom token storage. Defaults to a `FileTokenStore` persisting to `~/.config/yunoheat/tokens.json`.
*   **Returns**: 
    *   `YunoHeatClient`: An authenticated client instance.
*   **Raises**:
    *   `ConfigEntryAuthFailed`: If credentials are invalid.
    *   `AuthError`: On connection, network, or Keycloak identity server failures.

---

#### `from_saved_tokens`
```python
@classmethod
async def from_saved_tokens(
    cls,
    username: str | None = None,
    password: str | None = None,
    *,
    session: aiohttp.ClientSession | None = None,
    token_store: TokenStore | None = None,
) -> YunoHeatClient
```
Instantiates the client using cached sessions. If the access token has expired, it automatically performs a background refresh. If both are expired, it attempts a direct re-login if credentials are provided.

*   **Parameters**:
    *   `username` (`str`, optional): Account email address for fallback re-login.
    *   `password` (`str`, optional): Account password for fallback re-login.
    *   `session` (`aiohttp.ClientSession`, optional): Shared custom HTTP session.
    *   `token_store` (`TokenStore`, optional): Custom token storage. Defaults to `FileTokenStore`.
*   **Returns**:
    *   `YunoHeatClient`: Client authenticated with saved tokens.
*   **Raises**:
    *   `AuthError`: If no tokens are found in the store, or if automatic refresh fails.

---

### Lifecycle Methods

#### `close`
```python
async def close(self) -> None
```
Closes the client and cleans up open connections. If the client created its own internal `aiohttp.ClientSession`, it is closed. Externally injected sessions are left open.

*   **Parameters**: None.
*   **Returns**: None.
*   **Raises**: None.

---

### Data Fetching Methods

#### `get_open_bill_due`
```python
async def get_open_bill_due(self) -> OpenBillDue
```
Retrieves the current outstanding balance on the account in EUR.

*   **Parameters**: None.
*   **Returns**:
    *   [`OpenBillDue`](#openbilldue): Model containing the outstanding balance amount.
*   **Raises**:
    *   `APIConnectionError`: On connection timeout or network failure.
    *   `APIError`: If the API server returns a non-2xx response.
    *   `AuthError`: If session-level authentication or automatic refresh fails.

---

#### `get_credit_balances`
```python
async def get_credit_balances(self) -> CreditBalancesResponse
```
Retrieves prepaid credit balances for the customer.

*   **Parameters**: None.
*   **Returns**:
    *   [`CreditBalancesResponse`](#creditbalancesresponse): List of credit balances matching the payment profile.
*   **Raises**:
    *   `APIConnectionError`: On connection timeout or network failure.
    *   `APIError`: If the API server returns a non-2xx response.
    *   `AuthError`: If session-level authentication or automatic refresh fails.

---

#### `get_person_customer`
```python
async def get_person_customer(self) -> PersonCustomer
```
Retrieves detailed account information for the primary contact profile.

*   **Parameters**: None.
*   **Returns**:
    *   [`PersonCustomer`](#personcustomer): Detailed contact and profile information.
*   **Raises**:
    *   `APIConnectionError`: On connection timeout or network failure.
    *   `APIError`: If the API server returns a non-2xx response.
    *   `AuthError`: If session-level authentication or automatic refresh fails.

---

#### `get_usage_events`
```python
async def get_usage_events(
    self,
    *,
    date_from: datetime,
    date_to: datetime,
    page: int = 1,
    count: int = 50,
    order: Literal["asc", "desc"] = "desc",
) -> UsageEventsResponse
```
Retrieves paginated raw meter reading events (telemetry logs) for the property.

*   **Parameters**:
    *   `date_from` (`datetime`): Inclusive start range (UTC).
    *   `date_to` (`datetime`): Inclusive end range (UTC).
    *   `page` (`int`, optional): 1-indexed page number. Defaults to `1`.
    *   `count` (`int`, optional): Results per page. Defaults to `50`.
    *   `order` (`str`, optional): Sorting direction — `"desc"` (newest first, default) or `"asc"`.
*   **Returns**:
    *   [`UsageEventsResponse`](#usageeventsresponse): List of raw usage events and pagination metadata.
*   **Raises**:
    *   `APIConnectionError`: On connection timeout or network failure.
    *   `APIError`: If the API server returns a non-2xx response.
    *   `AuthError`: If session-level authentication or automatic refresh fails.
    *   `EntityDiscoveryError`: If bootstrap discovery failed to map the entity ID graph.

---

#### `get_usage_report`
```python
async def get_usage_report(
    self,
    *,
    date_from: datetime,
    date_to: datetime,
    interval: str = "day",
) -> UsageReport
```
Retrieves aggregated consumption (kWh) and monetary cost (EUR) over a date range.

*   **Parameters**:
    *   `date_from` (`datetime`): Start boundary for report aggregation (UTC).
    *   `date_to` (`datetime`): End boundary for report aggregation (UTC).
    *   `interval` (`str`, optional): Bucket size — one of `"day"` (default), `"week"`, `"month"`, `"quarter"`, or `"year"`.
*   **Returns**:
    *   [`UsageReport`](#usagereport): Aggregated usage readings list grouped by the interval bucket.
*   **Raises**:
    *   `APIConnectionError`: On connection timeout or network failure.
    *   `APIError`: If the API server returns a non-2xx response.
    *   `AuthError`: If session-level authentication or automatic refresh fails.
    *   `EntityDiscoveryError`: If bootstrap discovery failed to map the entity ID graph.

---

#### `get_invoices`
```python
async def get_invoices(
    self,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    count: int = 10,
) -> BillsResponse
```
Retrieves historical bills/invoices for the customer account.

*   **Parameters**:
    *   `date_from` (`datetime`, optional): Filter start range (UTC).
    *   `date_to` (`datetime`, optional): Filter end range (UTC).
    *   `page` (`int`, optional): 1-indexed page number. Defaults to `1`.
    *   `count` (`int`, optional): Invoices per page. Defaults to `10`.
*   **Returns**:
    *   [`BillsResponse`](#billsresponse): Paginated historical bills.
*   **Raises**:
    *   `APIConnectionError`: On connection timeout or network failure.
    *   `APIError`: If the API server returns a non-2xx response.
    *   `AuthError`: If session-level authentication or automatic refresh fails.

---

#### `get_bill`
```python
async def get_bill(self, bill_id: int) -> Bill
```
Retrieves a single historical bill in detail by its identifier.

*   **Parameters**:
    *   `bill_id` (`int`): The unique ID of the bill to retrieve.
*   **Returns**:
    *   [`Bill`](#bill): Detail model of the requested bill.
*   **Raises**:
    *   `APIConnectionError`: On connection timeout or network failure.
    *   `APIError`: If the API server returns a non-2xx response.
    *   `AuthError`: If session-level authentication or automatic refresh fails.

---

## Token Storage Protocol: `TokenStore`

The pluggable interface to customize session persistence.

```python
class TokenStore(Protocol):
    async def load(self) -> TokenData | None:
        """Load tokens; return None if empty."""
        ...

    async def save(self, tokens: TokenData) -> None:
        """Persist tokens."""
        ...
```

### Built-in Store Classes

*   **`FileTokenStore(path: Path | str | None = None)`**
    Saves tokens as a JSON file in `~/.config/yunoheat/tokens.json` (or a custom path) with secure file permissions (`0600`).
*   **`InMemoryTokenStore()`**
    Keeps tokens in memory. Ideal for testing and transient usage.

---

## Models

Data structures are backed by standard Python classes and `dataclasses`.

### `TokenData`
Tracks session credentials.
*   **Fields**:
    *   `access_token` (`str`): Raw OAuth JWT access token.
    *   `refresh_token` (`str`): Raw OAuth JWT refresh token.
    *   `access_expires_at` (`float`): Unix timestamp when access token expires.
    *   `refresh_expires_at` (`float`): Unix timestamp when refresh token expires.
*   **Methods**:
    *   `access_is_valid(buffer_seconds=60) -> bool`: Checks if the access token has not expired.
    *   `refresh_is_valid(buffer_seconds=60) -> bool`: Checks if the refresh token has not expired.
    *   `to_dict() -> dict`: Serializes fields for JSON storage.
    *   `from_dict(d: dict) -> TokenData`: Re-instantiates from serialized data.

### `EntityContext`
Stores cached identifier mapping for Tridens requests.
*   **Fields**:
    *   `person_customer_id` (`int`): Primary contact customer ID.
    *   `person_customer_code` (`str`): Primary contact UUID code.
    *   `payment_group_id` (`int`): Billing relationship group ID.
    *   `property_customer_id` (`int`): Property customer account ID.
    *   `property_subscription_id` (`int`): Subscribed heat service ID.
    *   `meter_identifier` (`str`): Meter serial number.

### `OpenBillDue`
Tracks account balance.
*   **Fields**:
    *   `open_bill_due` (`float`): Outstanding amount in EUR.

### `PersonCustomer`
Detailed contact and profile information for the account owner.
*   **Fields**:
    *   `id` (`int`): The customer ID.
    *   `code` (`str`): The Keycloak UUID string.
    *   `status` (`str`): Status of the person account (e.g. `"active"`).
    *   `contact_infos` (`list[ContactInfo]`): List of addresses, emails, and phone numbers.
    *   `pay_info` (`PayInfo`): Details on payment methods and card info.
    *   `subscriptions` (`list[SubscriptionRef]`): List of subscriptions owned.

### `CreditBalancesResponse`
A list wrapper for prepayment credit balances.
*   **Fields**:
    *   `objects` (`list[CreditBalance]`): Prepayment credit items.
    *   `total_num` (`int`): Total count of credit balance objects.

### `CreditBalance`
A single credit record.
*   **Fields**:
    *   `id` (`int`): Credit balance ID.
    *   `amount` (`float`): Available prepaid balance.

### `UsageEventsResponse`
A paginated list wrapper for raw meter telemetry readings.
*   **Fields**:
    *   `objects` (`list[UsageEvent]`): Raw meter telemetry events.
    *   `total_num` (`int`): Total count of reading events.

### `UsageEvent`
A single usage telemetry reading log.
*   **Fields**:
    *   `event_id` (`int`): Event transaction ID.
    *   `event_code` (`str`): Reference code.
    *   `amount_with_discount` (`float`): Cost in EUR for this period.
    *   `quantity` (`float`): Consumption in kWh for this period.
    *   `identifier` (`str`): Meter serial number.
    *   `created_at` (`int`): Epoch milliseconds timestamp.
    *   `fields` (`UsageEventFields`): Nested metadata dictionary.

### `UsageEventFields`
Nested fields dictionary inside a `UsageEvent`.
*   **Fields**:
    *   `property` (`str`): Property code (e.g. `"GFW296"`).
    *   `identifier` (`str`): Meter serial number.
    *   `meter_value` (`str`): Cumulative reading in kWh.
    *   `time_of_read` (`str`): Read timestamp (epoch milliseconds).

### `UsageReport`
Parsed aggregations over a period.
*   **Fields**:
    *   `interval` (`str`): Interval bucket size (e.g. `"day"`).
    *   `readings` (`list[DailyReading]`): Aggregated telemetry entries.

### `DailyReading`
A single interval's consumption and cost aggregation.
*   **Fields**:
    *   `date` (`datetime`): Start date of the bucket (UTC).
    *   `kwh` (`float`): Energy consumed in kWh.
    *   `eur` (`float`): Cost in EUR.

### `BillsResponse`
A wrapper for list of bills.
*   **Fields**:
    *   `objects` (`list[Bill]`): Details of bills.
    *   `total_num` (`int`): Total number of bills.

### `Bill`
A single bill record.
*   **Fields**:
    *   `id` (`int`): Bill identifier.
    *   `status` (`str`): Invoice state (e.g. `"active"`, `"closed"`).
    *   `valid_from` (`int`): Billing period start (epoch ms).
    *   `valid_to` (`int`): Billing period end (epoch ms).
    *   `due_amount` (`float`): Outstanding amount (EUR).
    *   `total_amount` (`float`): Total invoiced amount (EUR).

---

## Exceptions

All exceptions extend the base class `YunoHeatError`.

```
YunoHeatError (base package exception)
 ├── AuthError
 │    └── TokenExpiredError (refresh token expired)
 ├── ConfigEntryAuthFailed (invalid credentials / login failed)
 ├── APIError (HTTP error status code from Tridens)
 ├── APIConnectionError (TCP, DNS, or connection timeout)
 └── EntityDiscoveryError (bootstrap discovery failed)
```
