# pyyunoheat

<div class="hero-banner">
  <h1>pyyunoheat</h1>
  <p>An elegant, async Python client for the Yuno Energy Heat API, designed for home automation, telemetry tracking, and custom integrations.</p>
</div>

Welcome to the official documentation for **pyyunoheat**. 

This library provides full programmatic access to the **Yuno Energy Heat** communal heating scheme API (formerly Kaizen Energy) running on the Tridens Monetization platform. It enables discovery, real-time balance checks, consumption telemetry, and history retrieval without relying on browser automation or page scraping.

## Key Features

* **Async-First**: Built from the ground up using `aiohttp` for non-blocking, high-performance I/O.
* **Pluggable Token Storage**: Inject custom persistence layers (e.g., for Home Assistant configuration storage or database backends).
* **Robust Discovery**: Automatic bootstrapping of Tridens person, subscription, payment group, and property entities.
* **Granular Telemetry**: Retrieve daily, weekly, or monthly usage reports with energy (kWh) and monetary cost (EUR) breakdowns.
* **Production Ready**: Full exception hierarchy designed for clean and resilient error handling.

## Quick Installation

Install the package via `pip`:

```bash
pip install pyyunoheat
```

## Quick Start

```python
import asyncio
from yunoheat import YunoHeatClient

async def main():
    # Authenticate and initialize the client
    async with await YunoHeatClient.login("you@example.com", "password") as client:
        # Check current balance
        balance = await client.get_open_bill_due()
        print(f"Outstanding balance: €{balance.open_bill_due:.2f}")

asyncio.run(main())
```

---

## Next Steps

* **[User Guide](user-guide.md)**: Learn about authentication, token management, custom stores, and detailed telemetry queries.
* **[Architecture](architecture.md)**: Explore the underlying Tridens Monetization API, key realm configurations, and entity mapping.
* **[API Reference](api.md)**: View the complete reference for `YunoHeatClient`, exception types, and data models.
* **[Contributing Guide](contributing.md)**: Find instructions on setting up local development, running tests, and code formatting guidelines.
