# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.2] - 2026-06-11

### Added

- `YunoHeatClient.get_context()`: Public method to expose the resolved `EntityContext` (customer IDs, meter IDs), enabling Home Assistant integrations to populate device registries without re-running discovery
- Added `session` parameter to `YunoHeatClient.from_saved_tokens()` to support external session injection when loading from a token store

## [0.2.1] - 2026-06-11

### Fixed

- Unit tests no longer write fake tokens to the real `~/.config/yunoheat/tokens.json`;
  test Connections now use `InMemoryTokenStore`
- Integration test fixture falls back to a fresh login when saved tokens are fully
  expired, and `test_from_saved_tokens` exercises the token refresh path instead of
  asserting on raw loaded state
- Capped `aiohttp<3.14` in the dev extra: aioresponses 0.7.8 cannot mock aiohttp
  3.14's `ClientResponse` (new required `stream_writer` argument). Runtime
  requirement remains `aiohttp>=3.9`

## [0.2.0] - 2026-06-11

### Major Changes (Production-Grade Refactoring for Home Assistant)

**⚠️ NOTE: This release is fully backward compatible. No breaking changes.**

#### Added

- **Pluggable Token Store Architecture** — Critical for Home Assistant integration
  - Introduced `TokenStore` protocol for abstract token storage
  - Implemented `FileTokenStore` (default, backward-compatible file-based storage)
  - Implemented `InMemoryTokenStore` (for testing and ephemeral sessions)
  - All token operations now async: `login()`, `refresh()`, `get_valid_tokens()`
  - Home Assistant integrations can now inject custom stores wrapping Config Entries

- **Refined Exception Hierarchy** — Clear semantics for Home Assistant error handling
  - `ConfigEntryAuthFailed` — Invalid credentials (permanent) → HA reauth UI flow
  - `APIConnectionError` — Network failures (timeout, connection refused) → HA retry with backoff
  - Split error handling to distinguish permanent auth failures from transient API errors
  - Each exception type now triggers appropriate HA flows (reauth vs. retry)

- **Session Ownership Safety** — Safe integration with Home Assistant's shared aiohttp session
  - Track whether sessions are externally provided (`_external_session`)
  - Never close externally-provided sessions
  - Prevents breaking HA's shared `aiohttp.ClientSession` architecture
  - Supports both library-managed and HA-managed session lifecycles

- **Bootstrap Resilience** — Robust entity discovery with timeout protection
  - Added configurable timeout support (15s total, 10s per-request)
  - JWT claim validation with graceful error handling
  - Proper exception propagation vs. transformation
  - Clear error messages with context
  - Handles partial failures cleanly

- **Timeout Support** — Connection-level timeout for all HTTP operations
  - `Connection.request()`, `.get()`, `.post()` accept optional `timeout` parameter
  - Default: 30-second timeout for regular requests
  - Bootstrap requests: 15s total, 10s per-request
  - Prevents indefinite hangs in async event loops

#### Changed

- **Dependency Optimization**
  - Migrated `TokenData` from Pydantic `BaseModel` to `@dataclass`
  - Reduces internal dependency footprint (~100KB savings)
  - Kept Pydantic for API responses (schema validation is critical)
  - Better performance for token handling

- **Token Data Structure**
  - `TokenData` now uses `@dataclass` (was Pydantic `BaseModel`)
  - Backward compatible: `to_dict()`, `from_dict()`, serialization unchanged
  - More lightweight and performant for internal state

- **Client Factory Methods**
  - `YunoHeatClient.login()` now accepts `token_store` parameter
  - `YunoHeatClient.from_saved_tokens()` now accepts `token_store` parameter
  - Both methods maintain backward compatibility (default to file-based storage)

- **Error Handling**
  - `APIConnectionError` raised for network-level failures (was grouped under `APIError`)
  - Better distinction between transient and permanent auth failures
  - Enhanced error context in exception messages

#### Documentation

- Added `REFACTORING_SUMMARY.md` — Comprehensive architectural overview
- Added `HA_INTEGRATION_EXAMPLE.md` — Complete practical Home Assistant integration example
- Added `API_REFERENCE.md` — Quick migration guide and API reference
- Added `IMPLEMENTATION_CHECKLIST.md` — Pre-release validation and testing guide

### Home Assistant Integration

This release is specifically designed for Home Assistant HACS integration:

1. **Token Management**: Integrations can wrap HA's config entry data in a `TokenStore`
2. **Session Sharing**: Safe to use HA's shared `async_get_clientsession(hass)`
3. **Error Handling**: Clear exception semantics for HA's internal flows
4. **Resilience**: Bootstrap timeout protection, proper error handling
5. **Performance**: Lightweight internals, EntityContext caching support

See [HA_INTEGRATION_EXAMPLE.md](HA_INTEGRATION_EXAMPLE.md) for complete integration guide.

### Backward Compatibility

✅ **100% backward compatible** — All existing code works unchanged:

```python
# Old code still works (file-based tokens by default)
client = await YunoHeatClient.login(username, password)
client = await YunoHeatClient.from_saved_tokens()
```

New code can leverage HA-friendly features:

```python
# New HA-friendly code
store = HATokenStore(hass, config_entry)
client = await YunoHeatClient.login(
    username, password,
    token_store=store,
    session=async_get_clientsession(hass)
)
```

### Testing

- Existing test suite requires minimal updates
- Replace file I/O mocking with `TokenStore` mocking
- Use `InMemoryTokenStore()` in unit tests for speed
- New tests for session ownership, timeout handling, and exception types

### Migration Guide

For users of previous versions:

1. Update to `pyyunoheat>=0.2.0`
2. No changes required (backward compatible)
3. Optional: Adopt new token store API for better testability
4. For HA integration: Follow [HA_INTEGRATION_EXAMPLE.md](HA_INTEGRATION_EXAMPLE.md)

---

## [0.1.1] - 2024-03-15

### Initial Release

- Async Python client for Yuno Energy Heat API
- Keycloak authentication (Authorization Code flow)
- Entity discovery (person → property customer mapping)
- Usage events and reports
- Billing and balance queries
- File-based token persistence
- Pydantic models for API responses
