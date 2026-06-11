# pyyunoheat

Async Python client for the **Yuno Energy Heat** API (formerly Kaizen Energy), a communal heating scheme operating across apartment developments in Ireland.

The API runs on the Tridens Monetization platform. This library handles authentication, entity discovery, and data access with no browser or scraping required.

## Installation

```bash
pip install pyyunoheat
```

## Quick start

### Check your current balance

```python
import asyncio
from yunoheat import YunoHeatClient

async def main():
    async with await YunoHeatClient.login("you@example.com", "password") as client:
        balance = await client.get_open_bill_due()
        print(f"Outstanding balance: €{balance.open_bill_due:.2f}")

asyncio.run(main())
```

```
Outstanding balance: €87.83
```

### View this week's meter readings

```python
from datetime import datetime, timedelta, UTC
from yunoheat import YunoHeatClient

async def main():
    async with await YunoHeatClient.login("you@example.com", "password") as client:
        now = datetime.now(UTC)
        events = await client.get_usage_events(
            date_from=now - timedelta(days=7),
            date_to=now,
        )
        for e in events.objects:
            print(
                f"{e.fields.time_of_read_dt:%Y-%m-%d}  "
                f"{e.quantity:5.1f} kWh  "
                f"€{e.amount_with_discount:.3f}"
            )

asyncio.run(main())
```

```
2026-03-14   5.0 kWh  €1.306
2026-03-13   4.0 kWh  €1.182
2026-03-12   6.0 kWh  €1.430
```

### Daily usage report for the current month

```python
from datetime import datetime, UTC
from yunoheat import YunoHeatClient

async def main():
    today = datetime.now(UTC)
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    async with await YunoHeatClient.login("you@example.com", "password") as client:
        report = await client.get_usage_report(date_from=month_start, date_to=today)

    total_kwh = sum(r.kwh for r in report.readings)
    total_eur = sum(r.eur for r in report.readings)

    print(f"{'Date':<12} {'kWh':>6}  {'Cost':>7}")
    print("-" * 28)
    for r in report.readings:
        if r.kwh > 0:
            print(f"{r.date:%Y-%m-%d}  {r.kwh:6.1f}  €{r.eur:6.3f}")
    print("-" * 28)
    print(f"{'Total':<12} {total_kwh:6.1f}  €{total_eur:6.3f}")

asyncio.run(main())
```

```
Date          kWh     Cost
----------------------------
2026-03-01    3.0  € 0.372
2026-03-02    4.0  € 1.182
2026-03-03    5.0  € 1.306
...
2026-03-14    5.0  € 1.306
----------------------------
Total        58.0  €15.834
```

### Re-use saved tokens (skip re-login)

After the first `login()` call, tokens are saved to `~/.config/yunoheat/tokens.json`. On subsequent runs you can load them directly:

```python
from yunoheat import YunoHeatClient, TokenExpiredError

async def main():
    try:
        # Loads saved tokens; pass credentials for silent re-login on expiry
        client = await YunoHeatClient.from_saved_tokens(
            username="you@example.com",
            password="password",
        )
    except TokenExpiredError:
        # Tokens missing or too old — fall back to full login
        client = await YunoHeatClient.login("you@example.com", "password")

    async with client:
        balance = await client.get_open_bill_due()
        print(f"€{balance.open_bill_due:.2f}")

asyncio.run(main())
```

## API reference

### `YunoHeatClient`

| Factory | Returns | Description |
|---------|---------|-------------|
| `login(username, password, *, token_store=None, session=None)` | `YunoHeatClient` | Authenticate and create client |
| `from_saved_tokens(username, password, *, token_store=None, session=None)` | `YunoHeatClient` | Load saved tokens and create client |

| Method | Returns | Description |
|--------|---------|-------------|
| `get_open_bill_due()` | `OpenBillDue` | Current outstanding balance (EUR) |
| `get_usage_events(date_from, date_to, ...)` | `UsageEventsResponse` | Paginated meter readings |
| `get_usage_report(date_from, date_to, interval)` | `UsageReport` | Aggregated kWh + EUR by day/week/month |
| `get_person_customer()` | `PersonCustomer` | Account and contact details |
| `get_invoices(date_from, date_to, ...)` | `InvoicesResponse` | Paginated invoices |
| `get_bill(bill_id)` | `Bill` | Single bill by ID |
| `get_credit_balances()` | `CreditBalancesResponse` | Credit balance on account |

`get_usage_report` accepts `interval` values: `"day"` (default), `"week"`, `"month"`, `"quarter"`, `"year"`.

### Key model fields

**`UsageEvent`**
- `quantity` — kWh consumed in this period
- `amount_with_discount` — EUR cost
- `fields.time_of_read_dt` — UTC datetime of the reading
- `fields.meter_value_kwh` — cumulative meter reading (kWh)

**`DailyReading`** (from `UsageReport.readings`)
- `date` — UTC datetime of the bucket start
- `kwh` — kWh consumed
- `eur` — EUR cost

## Advanced usage

### Custom token storage

By default, tokens are persisted to `~/.config/yunoheat/tokens.json`. For Home Assistant or other custom scenarios, you can provide your own `TokenStore`:

```python
from yunoheat import YunoHeatClient, TokenStore, TokenData
import json

class CustomTokenStore(TokenStore):
    """Example: store tokens in a dict or database."""
    
    async def load(self) -> TokenData | None:
        """Load stored tokens, or None if missing."""
        # e.g., read from database, config store, etc.
        return None
    
    async def save(self, tokens: TokenData) -> None:
        """Persist tokens."""
        # e.g., write to database, config store, etc.
        pass

# Use custom store
store = CustomTokenStore()
client = await YunoHeatClient.login(
    "you@example.com", 
    "password",
    token_store=store,
)
```

### External aiohttp session

For Home Assistant integrations, you can provide an external `aiohttp.ClientSession` to share it across the application:

```python
import aiohttp
from yunoheat import YunoHeatClient

async with aiohttp.ClientSession() as session:
    client = await YunoHeatClient.login(
        "you@example.com",
        "password",
        session=session,
    )
    # The client uses your session; it won't be closed when client closes
    balance = await client.get_open_bill_due()
    # Session remains open for other tasks
```

### Exception handling

The library raises specific exception types for different error scenarios:

```python
from yunoheat import (
    YunoHeatClient,
    ConfigEntryAuthFailed,  # Invalid credentials; user must re-authenticate
    AuthError,              # Token refresh failed; may be transient
    TokenExpiredError,      # Refresh token expired; requires full login
    APIConnectionError,     # Network error; may be transient
    APIError,               # API returned 4xx/5xx error
    EntityDiscoveryError,   # Bootstrap failed (entity context resolution)
)

async def safe_login(username: str, password: str):
    try:
        return await YunoHeatClient.login(username, password)
    except ConfigEntryAuthFailed:
        print("Invalid credentials. Please check your username and password.")
        raise
    except AuthError as e:
        print(f"Auth error (may be transient): {e}")
        raise
    except APIConnectionError as e:
        print(f"Network error: {e}")
        raise
```

## Notes

- **Token storage**: Tokens are persisted to `~/.config/yunoheat/tokens.json` by default (mode `0600`). Use a custom `TokenStore` to store tokens elsewhere (e.g., Home Assistant config entry storage).
- **Token refresh**: Access tokens expire after 30 minutes. The library refreshes them automatically on demand.
- **Session ownership**: If you provide an external `aiohttp.ClientSession`, the library will not close it. If the library creates its own session, it will be closed on `await client.close()`.
- **Timestamps**: All times are UTC. Monetary values are EUR. Energy values are kWh.
- **API endpoint**: The underlying API is the Tridens Monetization self-care platform at `app.tridenstechnology.com`.
