# API Reference

This page describes the classes, models, exception hierarchy, and protocols exported by the `pyyunoheat` package.

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
Authenticates credentials against Keycloak, initializes the client, and bootstraps the initial customer data.
* **Parameters**:
    * `username` (`str`): User account email address.
    * `password` (`str`): User account password.
    * `session` (`aiohttp.ClientSession`, optional): Shared custom HTTP session.
    * `token_store` (`TokenStore`, optional): Custom token storage. Defaults to `FileTokenStore`.
* **Raises**:
    * `ConfigEntryAuthFailed`: If credentials are invalid.
    * `AuthError`: If Keycloak authentication fails.

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
Instantiates the client using cached sessions. If the access token is expired, it uses the refresh token. If both are expired, it attempts a direct credentials re-login if `username` and `password` are supplied.
* **Parameters**:
    * `username` (`str`, optional): Account email address for fallback re-login.
    * `password` (`str`, optional): Account password for fallback re-login.
    * `session` (`aiohttp.ClientSession`, optional): Shared custom HTTP session.
    * `token_store` (`TokenStore`, optional): Custom token storage.
* **Raises**:
    * `TokenExpiredError`: If tokens are expired and no credentials were provided for refresh.
    * `AuthError`: If no tokens are found in storage.

---

### Lifecycle Methods

#### `close`
```python
async def close(self) -> None
```
Closes the client. If the client created its own internal `aiohttp.ClientSession`, it is closed. Externally injected sessions are left open.

---

### Data Fetching Methods

#### `get_open_bill_due`
```python
async def get_open_bill_due(self, *, timeout: float = 30.0) -> OpenBillDue
```
Retrieves the current outstanding balance.
* **Returns**: `OpenBillDue` containing the outstanding balance.
* **Raises**: `APIConnectionError`, `APIError`.

---

#### `get_usage_events`
```python
async def get_usage_events(
    self,
    date_from: datetime,
    date_to: datetime,
    *,
    page: int = 1,
    count: int = 20,
    order: str = "desc",
    timeout: float = 30.0,
) -> UsageEventsResponse
```
Fetches raw meter readings.
* **Parameters**:
    * `date_from` (`datetime`): Start filter bounds (UTC).
    * `date_to` (`datetime`): End filter bounds (UTC).
    * `page` (`int`): Page number (1-indexed).
    * `count` (`int`): Number of events per page.
    * `order` (`str`): `"asc"` or `"desc"`.
* **Returns**: `UsageEventsResponse` containing a list of `UsageEvent` objects.

---

#### `get_usage_report`
```python
async def get_usage_report(
    self,
    date_from: datetime,
    date_to: datetime,
    *,
    interval: str = "day",
    timeout: float = 30.0,
) -> UsageReport
```
Retrieves aggregated energy and cost telemetry.
* **Parameters**:
    * `date_from` (`datetime`): Start boundary.
    * `date_to` (`datetime`): End boundary.
    * `interval` (`str`): Interval bucket size (`"day"`, `"week"`, `"month"`, `"quarter"`, or `"year"`).
* **Returns**: `UsageReport` containing a list of `DailyReading` aggregations.

---

#### `get_person_customer`
```python
async def get_person_customer(self, *, timeout: float = 30.0) -> PersonCustomer
```
Retrieves detailed account information for the main contact profile.
* **Returns**: `PersonCustomer` model.

---

#### `get_credit_balances`
```python
async def get_credit_balances(self, *, timeout: float = 30.0) -> CreditBalancesResponse
```
Gets current prepaid credit balances.

---

#### `get_invoices`
```python
async def get_invoices(
    self,
    date_from: datetime,
    date_to: datetime,
    *,
    page: int = 1,
    count: int = 10,
    timeout: float = 30.0,
) -> InvoicesResponse
```
Fetches historical invoices.

---

#### `get_bill`
```python
async def get_bill(self, bill_id: int, *, timeout: float = 30.0) -> Bill
```
Retrieves a single bill by its identifier.

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

* **`FileTokenStore(path: Path | str | None = None)`**
  Saves tokens as a JSON file in `~/.config/yunoheat/tokens.json` (or custom path) with secure file permissions (`0600`).
* **`InMemoryTokenStore()`**
  Keeps tokens in memory. Ideal for testing and transient usage.

---

## Models

Data structures are backed by standard python classes and `dataclasses`.

### `TokenData`
Tracks session credentials.
* **Fields**:
    * `access_token` (`str`): Raw OAuth JWT access token.
    * `refresh_token` (`str`): Raw OAuth JWT refresh token.
    * `access_expires_at` (`float`): Unix timestamp when access token expires.
    * `refresh_expires_at` (`float`): Unix timestamp when refresh token expires.
* **Methods**:
    * `access_is_valid(buffer_seconds=60) -> bool`: Checks if the access token has not expired.
    * `refresh_is_valid(buffer_seconds=60) -> bool`: Checks if the refresh token has not expired.
    * `to_dict() -> dict`: Serializes fields for JSON storage.
    * `from_dict(d: dict) -> TokenData`: Re-instantiates from serialized data.

### `EntityContext`
Stores cached identifier mapping for Tridens requests.
* **Fields**:
    * `person_customer_id` (`int`)
    * `person_customer_code` (`str`)
    * `payment_group_id` (`int`)
    * `property_customer_id` (`int`)
    * `property_subscription_id` (`int`)
    * `meter_identifier` (`str`)

### `OpenBillDue`
Tracks account balance.
* **Fields**:
    * `open_bill_due` (`float`): Outstanding amount in EUR.

### `DailyReading`
Represents an aggregated telemetry interval bucket.
* **Fields**:
    * `date` (`datetime`): Interval start time (UTC).
    * `kwh` (`float`): Total energy consumed in kWh.
    * `eur` (`float`): Total cost in EUR.

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
