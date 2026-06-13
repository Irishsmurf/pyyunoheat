# User Guide

This guide walks you through using the `pyyunoheat` library, covering basic client initialization, telemetry queries, token management, custom storage backends, and error handling.

---

## Installation

Ensure you have Python 3.11 or higher installed. Install the package using `pip`:

```bash
pip install pyyunoheat
```

---

## Authentication and Client Initialization

`pyyunoheat` authenticates directly against the Keycloak provider used by the Tridens platform. It supports direct credential login and loading existing sessions from a token storage layer.

### Direct Login

Use `YunoHeatClient.login()` to authenticate using your Yuno Energy portal credentials:

```python
import asyncio
from yunoheat import YunoHeatClient

async def main():
    # Credentials are used to perform keycloak oauth login
    async with await YunoHeatClient.login("username@example.com", "password") as client:
        balance = await client.get_open_bill_due()
        print(f"Owed: €{balance.open_bill_due:.2f}")

asyncio.run(main())
```

!!! note
    By default, `login()` persists tokens to `~/.config/yunoheat/tokens.json`.

### Reusing Saved Sessions

On subsequent startups, you can instantiate the client directly from saved tokens. If the access token is expired, but the refresh token is valid, it will refresh the session automatically. If the refresh token is also expired, it will attempt a silent re-login if credentials are provided.

```python
from yunoheat import YunoHeatClient, TokenExpiredError

async def main():
    try:
        # Attempts to load existing session; if access token expired,
        # it will refresh using username/password if supplied.
        client = await YunoHeatClient.from_saved_tokens(
            username="username@example.com",
            password="password"
        )
    except TokenExpiredError:
        # No saved token exists, or session is totally expired and cannot be refreshed
        client = await YunoHeatClient.login("username@example.com", "password")
        
    async with client:
        balance = await client.get_open_bill_due()
        print(f"Owed: €{balance.open_bill_due:.2f}")
```

---

## Pluggable Token Storage

In custom environments (like Home Assistant, database-backed apps, or daemon processes), persisting tokens to a raw JSON file on disk might not be appropriate. You can define a custom `TokenStore` matching the protocol:

```python
from typing import Protocol
from pyyunoheat import TokenData

class TokenStore(Protocol):
    async def load(self) -> TokenData | None:
        """Retrieve stored credentials, or None if empty."""
        ...

    async def save(self, tokens: TokenData) -> None:
        """Persist the token dataset."""
        ...
```

### Example: Storing Tokens in memory or a database

Here is an example wrapping a database or a simple custom storage:

```python
from pyyunoheat import YunoHeatClient, TokenStore, TokenData

class DatabaseTokenStore(TokenStore):
    def __init__(self, db_connection, user_id):
        self.db = db_connection
        self.user_id = user_id

    async def load(self) -> TokenData | None:
        row = await self.db.fetch_row(
            "SELECT access_token, refresh_token, access_expires_at, refresh_expires_at "
            "FROM user_tokens WHERE user_id = $1", 
            self.user_id
        )
        if not row:
            return None
        return TokenData(
            access_token=row["access_token"],
            refresh_token=row["refresh_token"],
            access_expires_at=row["access_expires_at"],
            refresh_expires_at=row["refresh_expires_at"]
        )

    async def save(self, tokens: TokenData) -> None:
        await self.db.execute(
            "INSERT INTO user_tokens (user_id, access_token, refresh_token, access_expires_at, refresh_expires_at) "
            "VALUES ($1, $2, $3, $4, $5) "
            "ON CONFLICT (user_id) DO UPDATE SET "
            "access_token = EXCLUDED.access_token, "
            "refresh_token = EXCLUDED.refresh_token, "
            "access_expires_at = EXCLUDED.access_expires_at, "
            "refresh_expires_at = EXCLUDED.refresh_expires_at",
            self.user_id, tokens.access_token, tokens.refresh_token, 
            tokens.access_expires_at, tokens.refresh_expires_at
        )

# Instantiate and pass to the client
store = DatabaseTokenStore(db_conn, user_id=42)
client = await YunoHeatClient.login("user@example.com", "password", token_store=store)
```

Built-in implementations:
- `FileTokenStore(path=None)`: Default. Stores JSON file in `~/.config/yunoheat/tokens.json` (or a custom path).
- `InMemoryTokenStore()`: Retains tokens purely in memory. Ideal for testing.

---

## Querying Consumption and Cost Telemetry

### Usage Report (Aggregated Data)

The `get_usage_report()` method is the recommended way to fetch consumption statistics. It utilizes Elasticsearch aggregation on the backend to bucket consumption by time interval (`"day"`, `"week"`, `"month"`, `"quarter"`, or `"year"`).

```python
from datetime import datetime, timedelta, UTC
from yunoheat import YunoHeatClient

async def main():
    async with await YunoHeatClient.login("you@example.com", "password") as client:
        today = datetime.now(UTC)
        start_date = today - timedelta(days=30)
        
        # Query daily usage report
        report = await client.get_usage_report(
            date_from=start_date,
            date_to=today,
            interval="day"
        )
        
        print(f"{'Date':<12} {'Energy (kWh)':>12} {'Cost (€)':>10}")
        print("-" * 38)
        for reading in report.readings:
            if reading.kwh > 0:
                print(f"{reading.date:%Y-%m-%d}  {reading.kwh:12.2f}  €{reading.eur:9.3f}")
```

### Usage Events (Raw Telemetry)

To fetch individual, paginated meter reading events as they are sent to the system, use `get_usage_events()`.

```python
from datetime import datetime, timedelta, UTC
from yunoheat import YunoHeatClient

async def main():
    async with await YunoHeatClient.login("you@example.com", "password") as client:
        today = datetime.now(UTC)
        
        # Query last 7 days of raw events
        events_response = await client.get_usage_events(
            date_from=today - timedelta(days=7),
            date_to=today,
            page=1,
            count=10,
            order="desc"
        )
        
        for event in events_response.objects:
            print(
                f"Time: {event.fields.time_of_read_dt:%Y-%m-%d %H:%M} | "
                f"Reading: {event.fields.meter_value_kwh:.1f} kWh | "
                f"Consumed: {event.quantity:.1f} kWh | "
                f"Cost: €{event.amount_with_discount:.3f}"
            )

asyncio.run(main())
```

---

## Sharing Web Sessions (`aiohttp`)

If you are building an integration within an existing network loop (like Home Assistant or a FastAPI application), you should share your application's `aiohttp.ClientSession` to avoid creating unnecessary connections.

```python
import aiohttp
from yunoheat import YunoHeatClient

async def main():
    async with aiohttp.ClientSession() as session:
        # Pass the external session to the client
        client = await YunoHeatClient.login(
            "you@example.com",
            "password",
            session=session
        )
        async with client:
            balance = await client.get_open_bill_due()
            print(f"Outstanding balance: €{balance.open_bill_due:.2f}")
        
        # Since the session was passed externally, pyyunoheat will NOT close it.
        # It remains open for other HTTP requests in your application.
```

---

## Error and Exception Handling

The library raises typed exceptions extending `YunoHeatError` for predictable failure states.

| Exception | Base Class | Trigger Scenario | Corrective Action |
|-----------|------------|------------------|-------------------|
| `ConfigEntryAuthFailed` | `YunoHeatError` | Invalid username/password, or account disabled. | Prompt user to update their credentials. |
| `TokenExpiredError` | `AuthError` | The refresh token has expired and credentials are not available for auto-refresh. | Trigger a full credential login flow. |
| `AuthError` | `YunoHeatError` | Keycloak tokens failed to refresh or exchange due to backend errors. | Retry after a delay (transient) or reauth. |
| `APIConnectionError` | `YunoHeatError` | DNS failure, timeout, or TCP connection failure. | Check network connection, retry with backoff. |
| `APIError` | `YunoHeatError` | Tridens server returned a non-2xx response (e.g. 500 Internal Error). | Check request payload, retry later. |
| `EntityDiscoveryError` | `YunoHeatError` | Bootstrapping succeeded but subscription or property IDs were not found. | Verify the account owns an active heat contract. |

```python
from yunoheat import (
    YunoHeatClient,
    ConfigEntryAuthFailed,
    TokenExpiredError,
    APIConnectionError,
    APIError,
)

async def run_safe():
    try:
        client = await YunoHeatClient.from_saved_tokens()
        async with client:
            return await client.get_open_bill_due()
    except TokenExpiredError:
        print("Session expired! Please login again with credentials.")
    except ConfigEntryAuthFailed:
        print("Incorrect username or password. Please verify credentials.")
    except APIConnectionError:
        print("Network connectivity issue. Will retry later...")
    except APIError as e:
        print(f"Tridens platform API error: {e}")
```
