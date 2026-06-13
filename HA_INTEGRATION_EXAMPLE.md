# Home Assistant Integration Example

This guide shows how to integrate `pyyunoheat` into a Home Assistant custom integration using the refactored library.

## 1. Installation

In your HACS integration's `manifest.json`:

```json
{
  "domain": "yuno_heat",
  "name": "Yuno Energy Heat",
  "codeowners": ["@yourname"],
  "config_flow": true,
  "documentation": "...",
  "issue_tracker": "...",
  "requirements": ["pyyunoheat>=0.2.0"],
  "version": "1.0.0"
}
```

## 2. Config Flow (`config_flow.py`)

```python
"""Config flow for Yuno Heat integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from yunoheat import (
    ConfigEntryAuthFailed,
    InMemoryTokenStore,
    TokenData,
    YunoHeatClient,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class YunoHeatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Yuno Heat."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}
        try:
            # Validate credentials by attempting login
            # Use in-memory store during validation (tokens will be saved in step_import)
            client = await YunoHeatClient.login(
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
                token_store=InMemoryTokenStore(),
                session=async_get_clientsession(self.hass),
            )
            
            # Bootstrap to verify entity discovery works
            context = await client._bootstrap()
            
            await client.close()
            
            return self.async_create_entry(
                title=user_input[CONF_USERNAME],
                data={
                    CONF_USERNAME: user_input[CONF_USERNAME],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    "tokens": None,  # Will be populated by coordinator
                },
            )

        except ConfigEntryAuthFailed as err:
            _LOGGER.error("Invalid credentials: %s", err)
            errors["base"] = "invalid_credentials"
        except Exception as err:
            _LOGGER.error("Unexpected error during config flow: %s", err)
            errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> FlowResult:
        """Handle import from YAML."""
        return await self.async_step_user(user_input=import_data)
```

## 3. Token Store Implementation (`token_store.py`)

```python
"""Token store that wraps Home Assistant's config entry."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from yunoheat import TokenData, TokenStore

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class HAConfigEntryTokenStore(TokenStore):
    """Stores tokens in Home Assistant's config entry data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the token store."""
        self.hass = hass
        self.entry = entry

    async def load(self) -> TokenData | None:
        """Load tokens from config entry data."""
        token_dict = self.entry.data.get("tokens")
        if not token_dict:
            return None
        try:
            return TokenData.from_dict(token_dict)
        except Exception as err:
            _LOGGER.error("Failed to load tokens from config entry: %s", err)
            return None

    async def save(self, tokens: TokenData) -> None:
        """Save tokens to config entry data."""
        self.hass.config_entries.async_update_entry(
            self.entry,
            data={
                **self.entry.data,
                "tokens": tokens.to_dict(),
            },
        )
        _LOGGER.debug("Tokens saved to config entry")
```

## 4. Data Coordinator (`coordinator.py`)

```python
"""Data coordinator for Yuno Heat integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from yunoheat import (
    APIConnectionError,
    APIError,
    AuthError,
    ConfigEntryAuthFailed,
    TokenExpiredError,
    YunoHeatClient,
)

from .const import DOMAIN
from .token_store import HAConfigEntryTokenStore

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(hours=1)


class YunoHeatCoordinator(DataUpdateCoordinator):
    """Data coordinator for Yuno Heat."""

    def __init__(self, hass: HomeAssistant, client: YunoHeatClient) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> dict:
        """Fetch data from Yuno Heat API."""
        try:
            # Fetch today's usage report
            now = datetime.now()
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
            
            report = await self.client.get_usage_report(
                date_from=start,
                date_to=end,
                interval="day",
            )
            
            balance = await self.client.get_open_bill_due()
            
            return {
                "usage_report": report,
                "balance": balance,
            }

        except ConfigEntryAuthFailed as err:
            # Credentials are invalid; require user action
            _LOGGER.error("Authentication failed: %s", err)
            raise UpdateFailed("Invalid credentials") from err

        except TokenExpiredError as err:
            # Refresh token expired; user must log in again
            _LOGGER.error("Refresh token expired: %s", err)
            raise UpdateFailed("Refresh token expired") from err

        except (APIConnectionError, APIError) as err:
            # Transient API errors; will retry
            _LOGGER.warning("API error during update: %s", err)
            raise UpdateFailed(f"API error: {err}") from err

        except Exception as err:
            # Unexpected error
            _LOGGER.error("Unexpected error during update: %s", err)
            raise UpdateFailed(f"Unexpected error: {err}") from err


async def async_setup_coordinator(
    hass: HomeAssistant, entry
) -> YunoHeatCoordinator:
    """Set up the data coordinator."""
    # Create token store
    token_store = HAConfigEntryTokenStore(hass, entry)
    
    # Create client with HA's session
    client = await YunoHeatClient.from_saved_tokens(
        username=entry.data.get("username"),
        password=entry.data.get("password"),
        token_store=token_store,
    )
    
    # Create coordinator
    coordinator = YunoHeatCoordinator(hass, client)
    
    # Perform initial data fetch
    await coordinator.async_config_entry_first_refresh()
    
    return coordinator
```

## 5. Setup (`__init__.py`)

```python
"""Yuno Heat integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .coordinator import async_setup_coordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "number"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    try:
        coordinator = await async_setup_coordinator(hass, entry)
    except Exception as err:
        _LOGGER.error("Failed to set up coordinator: %s", err)
        return False
    
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
    }
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    entry.async_on_unload(entry.add_update_listener(async_update_entry))
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    ):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_update_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
```

## 6. Entity Implementation (`sensor.py`)

```python
"""Sensors for Yuno Heat integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfVolume
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import YunoHeatCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = [
        YunoHeatBalanceSensor(coordinator, entry),
        YunoHeatUsageKwhSensor(coordinator, entry),
    ]
    
    async_add_entities(entities)


class YunoHeatBalanceSensor(CoordinatorEntity, SensorEntity):
    """Sensor for current balance."""

    _attr_name = "Balance"
    _attr_native_unit_of_measurement = "EUR"

    def __init__(
        self, coordinator: YunoHeatCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_balance"

    @property
    def native_value(self) -> float | None:
        """Return the current balance in EUR."""
        if not self.coordinator.data:
            return None
        balance = self.coordinator.data.get("balance")
        return balance.outstanding_amount if balance else None


class YunoHeatUsageKwhSensor(CoordinatorEntity, SensorEntity):
    """Sensor for current usage in kWh."""

    _attr_name = "Usage Today"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(
        self, coordinator: YunoHeatCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_usage_kwh"

    @property
    def native_value(self) -> float | None:
        """Return today's usage in kWh."""
        if not self.coordinator.data:
            return None
        report = self.coordinator.data.get("usage_report")
        if not report or not report.readings:
            return None
        # Return total kWh from latest reading
        return sum(reading.kwh for reading in report.readings)
```

## 7. Error Handling Best Practices

```python
# When catching exceptions:

try:
    await client.get_usage_report(...)

except ConfigEntryAuthFailed:
    # User must log in again - invalidate config entry
    raise ConfigEntryAuthFailed("Invalid credentials") from exc

except TokenExpiredError:
    # Refresh token expired - user must log in
    raise UpdateFailed("Refresh token expired") from exc

except AuthError:
    # Session-level auth failure (HTTP 401) - will auto-refresh
    raise UpdateFailed("Auth error, will retry") from exc

except (APIConnectionError, APIError):
    # Network or API errors - trigger standard retry logic
    raise UpdateFailed(f"API error: {exc}") from exc
```

## 8. Testing

```python
"""Test the coordinator."""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from yunoheat import InMemoryTokenStore, TokenData, YunoHeatClient

@pytest.mark.asyncio
async def test_coordinator_fetch_data():
    """Test coordinator data update."""
    # Mock the client
    mock_client = MagicMock(spec=YunoHeatClient)
    mock_client.get_usage_report = AsyncMock()
    mock_client.get_open_bill_due = AsyncMock()
    
    # Create coordinator
    coordinator = YunoHeatCoordinator(hass, mock_client)
    
    # Update data
    data = await coordinator._async_update_data()
    
    # Verify data structure
    assert "usage_report" in data
    assert "balance" in data
```

## Summary

This example shows how to:

1. ✅ Use `pyyunoheat` in a HA config flow
2. ✅ Implement a token store wrapping HA's config entry
3. ✅ Set up a data coordinator with proper error handling
4. ✅ Create entities using coordinator data
5. ✅ Distinguish between permanent errors (reauth) and transient errors (retry)

The library now integrates seamlessly with Home Assistant's async architecture and error handling flows!
