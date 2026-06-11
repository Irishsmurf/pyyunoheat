# PyYunoHeat API Reference — Production Refactoring

## Quick Migration Guide

### For Existing Users (Backward Compatible)

Your existing code **works unchanged**:

```python
# These still work exactly as before (file-based tokens)
client = await YunoHeatClient.login(username, password)
client = await YunoHeatClient.from_saved_tokens()
```

### For Home Assistant Integrations (New)

Use the new pluggable architecture:

```python
from pyyunoheat import YunoHeatClient, TokenData

# 1. Create a token store (HA wraps config entry)
class HATokenStore:
    async def load(self) -> TokenData | None: ...
    async def save(self, tokens: TokenData) -> None: ...

store = HATokenStore(hass, config_entry)

# 2. Login with custom store + HA's session
client = await YunoHeatClient.login(
    username="user@example.com",
    password="password",
    token_store=store,
    session=async_get_clientsession(hass),
)

# 3. Handle HA-specific exceptions
try:
    data = await client.get_usage_report(...)
except ConfigEntryAuthFailed:
    # User must re-authenticate
    raise
except (APIConnectionError, APIError):
    # Transient error; HA retries
    raise UpdateFailed(...) from exc
```

---

## Exception Hierarchy

```
YunoHeatError (base)
├── AuthError
│   └── Transient session-level auth failure (HTTP 401)
│       → HA UpdateFailed (auto-refresh will be attempted)
│
├── ConfigEntryAuthFailed
│   └── Invalid credentials or permanent auth failure
│       → HA ConfigEntryAuthFailed (user must re-authenticate)
│
├── TokenExpiredError
│   └── Refresh token expired (subclass of AuthError)
│       → HA UpdateFailed (attempt auto-refresh with credentials)
│
├── APIError
│   └── API returned non-2xx error (other than 401)
│       → HA UpdateFailed (standard retry logic)
│
├── APIConnectionError
│   └── Network failure (timeout, connection refused, etc.)
│       → HA UpdateFailed (exponential backoff retry)
│
└── EntityDiscoveryError
    └── Bootstrap flow failed (entity IDs not found)
        → Likely ConfigEntryAuthFailed or API issue
```

---

## Token Store Protocol

```python
from typing import Protocol
from pyyunoheat import TokenData

class TokenStore(Protocol):
    """Pluggable token storage."""
    
    async def load(self) -> TokenData | None:
        """Load persisted tokens. Return None if not found."""
        ...
    
    async def save(self, tokens: TokenData) -> None:
        """Persist tokens."""
        ...

# Built-in implementations
from pyyunoheat import FileTokenStore, InMemoryTokenStore

# File-based (default, backward-compatible)
store = FileTokenStore()  # Uses ~/.config/yunoheat/tokens.json
store = FileTokenStore(path)  # Custom path

# In-memory (testing, ephemeral)
store = InMemoryTokenStore()

# Custom (wrap HA config entry, database, etc.)
class CustomStore:
    async def load(self) -> TokenData | None:
        # Your logic here
        pass
    
    async def save(self, tokens: TokenData) -> None:
        # Your logic here
        pass
```

---

## TokenData Structure

```python
from pyyunoheat import TokenData
from dataclasses import asdict

tokens = TokenData(
    access_token="eyJ...",
    refresh_token="eyJ...",
    access_expires_at=1234567890.0,    # Unix timestamp
    refresh_expires_at=1234567890.0,   # Unix timestamp
)

# Check validity
if tokens.access_is_valid():
    print("Access token is valid")

if not tokens.refresh_is_valid():
    print("Refresh token expired")

# Serialize to dict (for storage)
data = tokens.to_dict()

# Deserialize from dict
tokens = TokenData.from_dict(data)

# Or use dataclass methods
data = asdict(tokens)
```

---

## Client Factory Methods

### `YunoHeatClient.login()`

```python
from pyyunoheat import YunoHeatClient, TokenStore
import aiohttp

client = await YunoHeatClient.login(
    username: str,
    password: str,
    *,
    session: aiohttp.ClientSession | None = None,
    token_store: TokenStore | None = None,
) -> YunoHeatClient
```

**Behavior:**
- Authenticates with Keycloak
- Saves tokens via `token_store.save()` (file-based if None)
- Creates internal session if `session=None` (auto-closed on `.close()`)
- Never closes externally-provided sessions

**Raises:**
- `ConfigEntryAuthFailed`: Invalid credentials
- `AuthError`: Network or Keycloak failures

**Example:**
```python
client = await YunoHeatClient.login(
    "user@example.com",
    "password",
    session=my_session,
    token_store=my_store,
)
```

### `YunoHeatClient.from_saved_tokens()`

```python
client = await YunoHeatClient.from_saved_tokens(
    username: str | None = None,
    password: str | None = None,
    token_store: TokenStore | None = None,
) -> YunoHeatClient
```

**Behavior:**
- Loads tokens from `token_store.load()` (file-based if None)
- Stores username/password for auto-refresh if provided
- Defers bootstrap until first API call

**Raises:**
- `AuthError`: No tokens found in store

**Example:**
```python
client = await YunoHeatClient.from_saved_tokens(
    username="user@example.com",
    password="password",
    token_store=my_store,
)
```

---

## Connection Lifecycle

```python
from pyyunoheat import YunoHeatClient

# Automatic cleanup with context manager
async with await YunoHeatClient.login(...) as client:
    data = await client.get_usage_report(...)
    # Session automatically closed on exit

# Manual cleanup
client = await YunoHeatClient.login(...)
try:
    data = await client.get_usage_report(...)
finally:
    await client.close()  # Only closes sessions we created
```

**Important:** If you pass an external `session`:

```python
import aiohttp

session = aiohttp.ClientSession()
client = await YunoHeatClient.login(..., session=session)

await client.close()  # Does NOT close the session
await session.close()  # You must close it
```

---

## Bootstrap & Entity Context

```python
from pyyunoheat import EntityContext

# Automatic on first API call
ctx = await client._ctx()  # Triggers bootstrap if needed

# Manual bootstrap
ctx = await client._bootstrap()

# EntityContext is cached
ctx_again = await client._bootstrap()  # Returns cached result

# Serialize to dict (for HA config entry caching)
data = ctx.model_dump()

# Deserialize from dict
ctx = EntityContext.model_validate(data)

# Typical structure
ctx.person_customer_id        # Account ID
ctx.person_customer_code      # UUID
ctx.payment_group_id          # Billing group
ctx.property_customer_id      # Property/meter ID
ctx.property_subscription_id  # Subscription ID
ctx.meter_identifier          # Meter serial number
```

---

## API Methods

All methods accept optional `timeout` parameter (default: 30 seconds):

```python
from datetime import datetime

# Account info
person = await client.get_person_customer()

# Balance
balance = await client.get_open_bill_due()

# Usage events (paginated)
events = await client.get_usage_events(
    date_from=datetime(...),
    date_to=datetime(...),
    page=1,
    count=50,
    order="desc",  # or "asc"
)

# Usage report (aggregated)
report = await client.get_usage_report(
    date_from=datetime(...),
    date_to=datetime(...),
    interval="day",  # "week", "month", "quarter", "year"
)

# Credit balances
balances = await client.get_credit_balances()

# Bills
bills = await client.get_invoices(
    date_from=datetime(...),
    date_to=datetime(...),
    page=1,
    count=10,
)
bill = await client.get_bill(bill_id=123)
```

---

## Testing with Token Stores

```python
import pytest
from pyyunoheat import InMemoryTokenStore, TokenData, YunoHeatClient

@pytest.mark.asyncio
async def test_client_with_custom_store():
    """Test using in-memory store."""
    store = InMemoryTokenStore()
    
    # Save tokens manually (simulating login)
    tokens = TokenData(
        access_token="mock_token",
        refresh_token="mock_refresh",
        access_expires_at=time.time() + 1800,
        refresh_expires_at=time.time() + 2100,
    )
    await store.save(tokens)
    
    # Load via client
    client = await YunoHeatClient.from_saved_tokens(token_store=store)
    
    # Use client
    # (In real tests, you'd mock the HTTP layer with aioresponses)
```

---

## Home Assistant Integration Checklist

- [ ] Implement `TokenStore` wrapping config entry data
- [ ] Pass `token_store` to `YunoHeatClient` factory methods
- [ ] Use HA's `async_get_clientsession(hass)` for the session
- [ ] Catch `ConfigEntryAuthFailed` → trigger reauth flow
- [ ] Catch `TokenExpiredError` → log and let coordinator retry
- [ ] Catch `(APIConnectionError, APIError)` → `raise UpdateFailed()`
- [ ] Cache `EntityContext` in config entry to skip bootstrap on restart
- [ ] Use `async with` context manager or explicit `.close()`
- [ ] Test with mocked `aioresponses` (use `InMemoryTokenStore`)

---

## Performance Notes

- **Bootstrap caching**: `EntityContext` cached after first fetch (~3-4s saved on HA restart)
- **Session reuse**: Single session for all requests (use HA's shared session)
- **Timeout protection**: Configurable per-request; prevents indefinite hangs
- **Memory**: `TokenData` as `@dataclass` uses ~100KB less than Pydantic
- **Concurrency**: Safe for concurrent HA updates; no global state

---

## Common Patterns

### HA Config Flow Validation

```python
try:
    client = await YunoHeatClient.login(
        username,
        password,
        token_store=InMemoryTokenStore(),  # Don't persist yet
    )
    # Verify bootstrap works
    await client._bootstrap()
    await client.close()
    return True
except ConfigEntryAuthFailed:
    errors["base"] = "invalid_credentials"
    return False
except Exception as err:
    _LOGGER.error("Login failed: %s", err)
    errors["base"] = "unknown"
    return False
```

### HA Coordinator Update

```python
async def _async_update_data(self):
    try:
        return await self.client.get_usage_report(...)
    except ConfigEntryAuthFailed:
        raise ConfigEntryAuthFailed("Invalid credentials") from exc
    except (APIConnectionError, APIError) as exc:
        raise UpdateFailed(f"API error: {exc}") from exc
```

### Token Store from Config Entry

```python
class HATokenStore:
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
    
    async def load(self):
        data = self.entry.data.get("tokens")
        return TokenData.from_dict(data) if data else None
    
    async def save(self, tokens):
        self.hass.config_entries.async_update_entry(
            self.entry,
            data={**self.entry.data, "tokens": tokens.to_dict()},
        )
```

---

## Migration Checklist (Existing Codebases)

- [ ] Update `pyyunoheat` to latest version
- [ ] Replace file system token management with `TokenStore` injection
- [ ] Update tests to use `InMemoryTokenStore`
- [ ] Handle `ConfigEntryAuthFailed` separately from `AuthError`
- [ ] Add timeouts to long-running operations
- [ ] Test session cleanup with external sessions
- [ ] Cache `EntityContext` where applicable

---

**For detailed examples, see [HA_INTEGRATION_EXAMPLE.md](HA_INTEGRATION_EXAMPLE.md)**
