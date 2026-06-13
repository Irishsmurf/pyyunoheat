<p align="center">
  <img src="https://raw.githubusercontent.com/Irishsmurf/pyyunoheat/main/docs/assets/logo.svg" alt="pyyunoheat logo" width="550">
</p>

<p align="center">
  <strong>An elegant, async-first Python client for the Yuno Energy Heat API.</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/pyyunoheat/"><img src="https://img.shields.io/pypi/v/pyyunoheat.svg?color=3C79EE" alt="PyPI version"></a>
  <a href="https://pypi.org/project/pyyunoheat/"><img src="https://img.shields.io/pypi/pyversions/pyyunoheat.svg?color=5C3FD6" alt="Supported Python versions"></a>
  <a href="https://github.com/Irishsmurf/pyyunoheat/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Irishsmurf/pyyunoheat.svg?color=20D5DF" alt="License"></a>
</p>

---

**pyyunoheat** is an async Python client for the **Yuno Energy Heat** API (formerly Kaizen Energy), a communal heating scheme operating across apartment developments in Ireland. 

The underlying API runs on the Tridens Monetization self-care platform. This library handles OAuth2/Keycloak authentication, dual-tier entity discovery, and telemetry data access with no browser automation or scraping required.

📖 **Full Documentation**: [https://Irishsmurf.github.io/pyyunoheat/](https://Irishsmurf.github.io/pyyunoheat/)

---

## Key Features

* **Async-First**: Built on top of `aiohttp` for efficient, non-blocking network calls.
* **Dual-Tier Discovery**: Automatically bootstraps the Tridens customer hierarchy (Person Account ➔ Payment Group ➔ Property Account ➔ Heat Meter Subscriptions) to retrieve entity identifiers.
* **Flexible Storage**: Support for pluggable token stores, allowing you to easily inject secure database backends or Home Assistant configuration storage.
* **Consumption Telemetry**: Fetch daily, weekly, or monthly usage reports with energy (kWh) and monetary cost (EUR) breakdowns.
* **Robust Exceptions**: Standardized error classes extending `YunoHeatError` for clean error recovery.

---

## Installation

Install via pip:

```bash
pip install pyyunoheat
```

---

## Quick Start

### 1. Check your outstanding balance

```python
import asyncio
from yunoheat import YunoHeatClient

async def main():
    async with await YunoHeatClient.login("you@example.com", "password") as client:
        balance = await client.get_open_bill_due()
        print(f"Outstanding balance: €{balance.open_bill_due:.2f}")

asyncio.run(main())
```

### 2. Daily usage report for the current month

```python
from datetime import datetime, UTC
from yunoheat import YunoHeatClient

async def main():
    today = datetime.now(UTC)
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    async with await YunoHeatClient.login("you@example.com", "password") as client:
        report = await client.get_usage_report(date_from=month_start, date_to=today)

    print(f"{'Date':<12} {'kWh':>6}  {'Cost':>7}")
    print("-" * 28)
    for r in report.readings:
        if r.kwh > 0:
            print(f"{r.date:%Y-%m-%d}  {r.kwh:6.1f}  €{r.eur:6.3f}")

asyncio.run(main())
```

---

## Pluggable Token Storage

By default, the client persists authentication tokens to `~/.config/yunoheat/tokens.json`. You can easily implement a custom `TokenStore` to save tokens elsewhere (e.g. database, secure vault, or Home Assistant configuration entry):

```python
from pyyunoheat import YunoHeatClient, TokenStore, TokenData

class CustomTokenStore(TokenStore):
    async def load(self) -> TokenData | None:
        # Load tokens from database/store
        ...
    async def save(self, tokens: TokenData) -> None:
        # Save tokens to database/store
        ...

store = CustomTokenStore()
client = await YunoHeatClient.login(
    "you@example.com", 
    "password",
    token_store=store,
)
```

---

## API Reference Overview

Below are the primary methods available on `YunoHeatClient`.

### Factory Methods
| Method | Returns | Description |
|:---|:---|:---|
| `login(username, password, *, token_store=None, session=None)` | `YunoHeatClient` | Authenticate and create a new client session. |
| `from_saved_tokens(username, password, *, token_store=None, session=None)` | `YunoHeatClient` | Restore session from cached tokens (optionally supplying credentials for fallback refresh). |

### Client Methods
| Method | Returns | Description |
|:---|:---|:---|
| `get_open_bill_due()` | `OpenBillDue` | Fetch current outstanding balance (EUR). |
| `get_usage_events(date_from, date_to, ...)` | `UsageEventsResponse` | Fetch paginated raw meter readings. |
| `get_usage_report(date_from, date_to, interval)` | `UsageReport` | Retrieve aggregated kWh + EUR by day, week, month, etc. |
| `get_person_customer()` | `PersonCustomer` | Retrieve account and contact details. |
| `get_invoices(date_from, date_to, ...)` | `InvoicesResponse` | Retrieve list of historical invoices. |
| `get_bill(bill_id)` | `Bill` | Fetch a single bill by ID. |
| `get_credit_balances()` | `CreditBalancesResponse` | Fetch current prepaid credit balances. |

---

## Technical Notes

* **Sessions**: Access tokens are valid for 30 minutes. The library automatically performs silent background refreshes when calling API methods.
* **External Session**: Pass a shared `aiohttp.ClientSession` using the `session` keyword argument to reuse connections in integrations (e.g., Home Assistant).
* **Timestamps**: All times are parsed to UTC. Monetary fields are returned in EUR. Energy usage is in kWh.

---

## Contributing

Please see the [Contributing Guide](https://Irishsmurf.github.io/pyyunoheat/contributing/) to set up a local development environment, run tests, and format code.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
