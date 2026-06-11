# Yuno Energy Heat API Documentation

> Reverse-engineered from the Tridens Monetization self-care web portal at
> `kaizen-energy.tridenstechnology.com`. The mobile app (Android package
> `com.tridenstechnology.monetization.kaizen`) is a webview wrapper around this
> same SPA, so all endpoints documented here apply to both.

---

## Architecture overview

The system has two main components:

| Component | Host | Purpose |
|-----------|------|---------|
| **Keycloak (auth)** | `app.tridenstechnology.com/auth` | OpenID Connect identity provider |
| **Monetization API** | `app.tridenstechnology.com/monetization/api/v1` | All data endpoints |

The backend is Elasticsearch-powered (the `/reports/usage` endpoint accepts raw
Elasticsearch DSL queries). All timestamps are **milliseconds since Unix epoch**.
All monetary values are in **EUR**. All energy values are in **kWh**.

---

## 1. Authentication

Authentication uses **Keycloak** with a standard OpenID Connect Authorization
Code flow. The public client `mobile-yuno` is used — no client secret required.

### 1.1 Keycloak realm details

```
Realm:      kaizen-energy-sandbox
Issuer:     https://app.tridenstechnology.com/auth/realms/kaizen-energy-sandbox
Client ID:  mobile-yuno
Scopes:     openid kaizen-energy
```

#### Key endpoints

| Endpoint | URL |
|----------|-----|
| Well-known config | `{issuer}/.well-known/openid-configuration` |
| Authorization | `{issuer}/protocol/openid-connect/auth` |
| Token | `{issuer}/protocol/openid-connect/token` |
| Userinfo | `{issuer}/protocol/openid-connect/userinfo` |
| Logout | `{issuer}/protocol/openid-connect/logout` |

### 1.2 Authorization Code flow (browser)

**Step 1 — Redirect to Keycloak login:**

```
GET {issuer}/protocol/openid-connect/auth
  ?client_id=mobile-yuno
  &redirect_uri=https://kaizen-energy.tridenstechnology.com/monetization/self-care/account
  &response_mode=fragment
  &response_type=code
  &scope=openid kaizen-energy
  &nonce={random-uuid}
  &state={random-uuid}
```

**Step 2 — User submits credentials:**

```
POST {issuer}/login-actions/authenticate?session_code=...&execution=...&client_id=mobile-yuno&tab_id=...
Content-Type: application/x-www-form-urlencoded

username={email}&password={password}&rememberMe=on
```

Returns a **302 redirect** back to `redirect_uri` with a `code` in the fragment.

**Step 3 — Exchange code for tokens:**

```
POST {issuer}/protocol/openid-connect/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code
&code={authorization_code}
&client_id=mobile-yuno
&redirect_uri={same_redirect_uri}
```

### 1.3 Token refresh

```
POST {issuer}/protocol/openid-connect/token
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token
&refresh_token={refresh_token}
&client_id=mobile-yuno
```

### 1.4 Token response

```json
{
  "access_token": "eyJhbG...",
  "expires_in": 1800,
  "refresh_expires_in": 2100,
  "refresh_token": "eyJhbG...",
  "token_type": "Bearer",
  "id_token": "eyJhbG...",
  "session_state": "...",
  "scope": "openid profile userinfo email compat-nonce kaizen-energy"
}
```

- **Access token lifetime:** 1800 seconds (30 minutes)
- **Refresh token lifetime:** 2100 seconds (35 minutes)

### 1.5 JWT access token claims

The access token is a signed JWT (RS256). Key claims:

| Claim | Description | Example |
|-------|-------------|---------|
| `sub` | Keycloak user UUID | `a4b3f7fd-94cc-42c8-b717-dc39207f40d2` |
| `customer_id` | Tridens numeric customer ID | `232971` |
| `customer_code` | Tridens customer UUID | `b21afb1f-1e10-4d17-bf8a-cebd07daf40a` |
| `preferred_username` | Login email | `user@example.com` |
| `sites` | Authorized sites | `["/kaizen-energy"]` |
| `roles` | Realm roles | `["customer", "offline_access", ...]` |
| `azp` | Authorized party (client) | `mobile-yuno` |

### 1.6 Resource Owner Password Credentials (direct grant)

Keycloak may support `grant_type=password` for programmatic access without a
browser (needs testing — the client may not have this flow enabled):

```
POST {issuer}/protocol/openid-connect/token
Content-Type: application/x-www-form-urlencoded

grant_type=password
&client_id=mobile-yuno
&username={email}
&password={password}
&scope=openid kaizen-energy
```

If this works, it's the simplest path for a Python library. If not, use the
authorization code flow with PKCE or automate the browser-based login.

---

## 2. API endpoints

**Base URL:** `https://app.tridenstechnology.com/monetization/api/v1`

**Authentication:** All endpoints require:
```
Authorization: Bearer {access_token}
```

### 2.1 Entity model

The Tridens data model uses a two-tier customer structure:

```
Customer (person)        id=232971, code=b21afb1f-...
  ├── Subscription       id=48770 ("David Kernan Platform")
  │   └── Balance Group  id=48759
  │       └── Billing Profile  id=47891
  │           ├── current_bill
  │           ├── previous_bill
  │           └── next_bill
  └── Payment Group      id=32762
      └── Property (customer) id=201411 ("Apt 020 Chambers Sq")
          └── Subscription   id=14582 (heat meter)
              ├── Balance Group  id=14583
              ├── Service        id=8466, identifier="04801107"
              └── service_type: HEAT_METER_READ_SERVICE
```

**Important:** The "property" is itself a customer entity (id=201411) linked via
a payment group. Usage events are recorded against the **property customer**,
not the person customer. The person customer is the **payment responsible** for
the property.

### 2.2 Site info

```
GET /site
```

Returns site-wide configuration for the Kaizen Energy tenant.

**Response (key fields):**

```json
{
  "id": 142,
  "code": "kaizen-energy",
  "name": "Kaizen Energy",
  "status": "active",
  "timezone": "Europe/Dublin",
  "currency": { "code": "EUR", "symbol": "€" },
  "environment": "production",
  "payment_gateway_profile": { "provider": "stripe" }
}
```

### 2.3 Customer (person)

```
GET /customers/{customer_code}
```

Where `customer_code` is the UUID from the JWT `customer_code` claim.

**Response (key fields):**

```json
{
  "id": 232971,
  "code": "b21afb1f-...",
  "status": "active",
  "contact_infos": [{
    "email": "...",
    "first_name": "...",
    "last_name": "...",
    "address": "Apartment 020 Chambers Square",
    "city": "Griffith Wood",
    "zip": "D09 HW1H",
    "phone": "+353..."
  }],
  "pay_info": {
    "method": "credit_card",
    "default_credit_card": {
      "card_type": "visa",
      "last_4": "6461",
      "expiration_month": 2,
      "expiration_year": 2030
    }
  },
  "subscriptions": [{ "id": 48770, "status": "active", ... }],
  "custom_attributes": {
    "customer_billing_type": "bill-pay",
    "customer_site_code": "GFW",
    "customer_supply_status": "ON"
  }
}
```

### 2.4 Subscription details

```
GET /customers/{customer_id}/subscriptions/{subscription_id}
```

Where `customer_id` is the **numeric** ID (e.g. `232971`).

Returns the full subscription tree including balance group, billing profile,
current/previous/next bills, purchased plan, and pricing.

### 2.5 Payment groups (links person → property)

```
GET /customers/{customer_id}/groups?type=payment
```

Returns the payment group linking the person customer to their property
customer(s). The response contains:

```json
{
  "objects": [{
    "id": 32762,
    "type": "payment",
    "strategy": "owner-first",
    "name": "Payment Responsible Properties - ...",
    "owner": { "id": 232971 },
    "owner_billing_profile": { "id": 47891 }
  }]
}
```

### 2.6 Property customers (via group)

```
GET /customers?parent-group={group_id}
```

Returns the property customer(s) linked to the payment group. This is the
**property customer** (id=201411) whose subscriptions hold the heat meter
service. Key fields in the property customer:

```json
{
  "id": 201411,
  "subscriptions": [{
    "id": 14582,
    "code": "SUB_APARTMENT020CHAMBERSSQUARE_04801107_heat_GFW_730827456",
    "name": "Apartment 020 Chambers Square - 04801107 - heat",
    "balance_group": { "id": 14583 }
  }],
  "services": [{
    "id": 8466,
    "identifier": "04801107",
    "service_type": {
      "code": "HEAT_METER_READ_SERVICE",
      "mandatory_fields": "identifier;time_of_read;meter_value_unit;reading_type;meter_value;session_id"
    }
  }]
}
```

The `identifier` field (`04801107`) is your heat meter serial number.

### 2.7 Usage events (meter readings)

```
GET /customers/{property_customer_id}/usage-events
  ?order-dir=desc
  &balance-group={balance_group_id}
  &time-from={epoch_ms}
  &time-to={epoch_ms}
  &service-type=HEAT_METER_READ_SERVICE
  &identifier={meter_serial}
  &page=1
  &count=5
```

**Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `order-dir` | No | `asc` or `desc` |
| `subscription` | No | Subscription ID (e.g. `14582`) |
| `balance-group` | No | Balance group ID (e.g. `14583`) |
| `time-from` | Yes | Start time (epoch ms) |
| `time-to` | Yes | End time (epoch ms) |
| `service-type` | Yes | `HEAT_METER_READ_SERVICE` |
| `identifier` | No | Heat meter serial number |
| `page` | Yes | Page number (1-indexed) |
| `count` | Yes | Results per page |

**Response:**

```json
{
  "objects": [
    {
      "event_id": 17886462,
      "event_code": "71006d18-...",
      "amount_with_discount": 1.306,
      "quantity": 5.0,
      "identifier": "04801107",
      "created_at": 1773538684938,
      "service_type": "HEAT_METER_READ_SERVICE",
      "fields": {
        "property": "GFW296",
        "identifier": "04801107",
        "session_id": "04801107-1773532800000",
        "meter_value": "9809",
        "reading_type": "A",
        "time_of_read": "1773532800000",
        "meter_value_unit": "kWh"
      }
    }
  ],
  "total_num": 15
}
```

**Usage event fields explained:**

| Field | Description |
|-------|-------------|
| `quantity` | kWh consumed in this reading period |
| `amount_with_discount` | EUR cost for this reading |
| `fields.meter_value` | Cumulative meter reading (kWh) |
| `fields.time_of_read` | Epoch ms of the reading |
| `fields.reading_type` | `A` = actual reading |
| `fields.session_id` | Format: `{meter_serial}-{epoch_ms}` |
| `fields.property` | Internal property code |

### 2.8 Usage reports (Elasticsearch aggregation)

```
POST /reports/usage
Content-Type: application/json
```

This endpoint accepts an **Elasticsearch Query DSL** body and returns raw ES
results including aggregations. The self-care portal uses this for chart data.

**Request body for daily kWh + EUR breakdown:**

```json
{
  "size": 5,
  "query": {
    "bool": {
      "filter": {
        "nested": {
          "path": "event_fields",
          "query": {
            "range": {
              "event_fields.time_of_read.date": {
                "gte": "2026-03-01T00:00:00.000Z",
                "lte": "2026-03-15T23:59:59.999Z"
              }
            }
          }
        }
      },
      "must": [
        {
          "query_string": {
            "query": "(HEAT_METER_READ_SERVICE)",
            "analyze_wildcard": true,
            "fields": ["service_type"]
          }
        },
        {
          "query_string": {
            "query": "{property_customer_id}",
            "analyze_wildcard": true,
            "fields": ["customer_id"]
          }
        },
        {
          "terms": {
            "resource_name": ["Heat - Meter Value", "Euro"]
          }
        }
      ]
    }
  },
  "aggs": {
    "chart": {
      "terms": { "field": "resource_name" },
      "aggs": {
        "by_amount": {
          "nested": { "path": "event_fields" },
          "aggs": {
            "history": {
              "date_histogram": {
                "field": "event_fields.time_of_read.date",
                "interval": "day",
                "min_doc_count": 0,
                "time_zone": "+00:00",
                "extended_bounds": {
                  "min": "2026-03-01T00:00:00.000Z",
                  "max": "2026-03-15T23:59:59.999Z"
                }
              },
              "aggs": {
                "reverse": {
                  "reverse_nested": {},
                  "aggs": {
                    "sum_amount": { "sum": { "field": "amount" } }
                  }
                }
              }
            }
          }
        },
        "by_quantity": {
          "nested": { "path": "event_fields" },
          "aggs": {
            "history": {
              "date_histogram": {
                "field": "event_fields.time_of_read.date",
                "interval": "day",
                "min_doc_count": 0,
                "time_zone": "+00:00",
                "extended_bounds": {
                  "min": "2026-03-01T00:00:00.000Z",
                  "max": "2026-03-15T23:59:59.999Z"
                }
              },
              "aggs": {
                "reverse": {
                  "reverse_nested": {},
                  "aggs": {
                    "sum_quantity": { "sum": { "field": "quantity" } }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

**Response structure:**

```json
{
  "aggregations": {
    "chart": {
      "buckets": [
        {
          "key": "Euro",
          "doc_count": 28,
          "by_amount": {
            "history": {
              "buckets": [
                {
                  "key_as_string": "2026-03-02 00:00:00.000",
                  "key": 1772409600000,
                  "reverse": {
                    "sum_amount": { "value": 1.182 }
                  }
                }
              ]
            }
          },
          "by_quantity": {
            "history": {
              "buckets": [
                {
                  "key_as_string": "2026-03-02 00:00:00.000",
                  "key": 1772409600000,
                  "reverse": {
                    "sum_quantity": { "value": 4.0 }
                  }
                }
              ]
            }
          }
        },
        {
          "key": "Heat - Meter Value",
          "doc_count": 14,
          "by_amount": { "..." : "..." },
          "by_quantity": { "..." : "..." }
        }
      ]
    }
  }
}
```

**Resource buckets explained:**

| Resource name | `by_amount` (sum_amount) | `by_quantity` (sum_quantity) |
|---------------|--------------------------|------------------------------|
| **Euro** | EUR cost per day | kWh per day (seems identical to Heat) |
| **Heat - Meter Value** | kWh (raw number, not EUR) | kWh per day |

The `interval` parameter supports: `day`, `week`, `month`, `quarter`, `year`.

### 2.9 Bills

```
GET /customers/{property_customer_id}/bills/{bill_id}
```

**Response (key fields):**

```json
{
  "id": 791134,
  "status": "active",
  "valid_from": 1773269943547,
  "valid_to": 253370764800000,
  "due_amount": 5.224,
  "total_amount": 5.224,
  "customer": { "id": 201411 },
  "billing_profile": { "id": 14284 }
}
```

Bill statuses observed: `active` (current), `billing` (finalized, awaiting
payment), `closed` (paid), `inactive` (future placeholder).

### 2.10 Open bill due (balance owed)

```
GET /customers/{customer_id}/open-bill-due
```

```json
{ "open_bill_due": 87.83 }
```

### 2.11 Credit balances

```
GET /credit-balances?customer={customer_id}&billing-profile={billing_profile_id}
```

```json
{
  "objects": [{ "id": 47891, "amount": 0 }],
  "total_num": 1
}
```

### 2.12 Invoices

```
GET /invoices
  ?page=1
  &count=10
  &customerId={customer_id}
  &time-from={epoch_ms}
  &time-to={epoch_ms}
  &billing-profile={billing_profile_id}
  &invoice-status=invoice
```

Returns paginated invoice list. Each invoice links to a bill with
`start_time`, `end_time`, `due_amount`, `total_amount`, and `payment_due` date.

### 2.13 Payments

```
GET /payments
  ?page=1
  &count=10
  &customerId={customer_id}
  &time-from={epoch_ms}
  &time-to={epoch_ms}
  &billing-profile={billing_profile_id}
```

### 2.14 Group memberships

```
GET /customers/{property_customer_id}/group-memberships
```

Returns the full group membership chain linking the property back to the
payment responsible person.

### 2.15 Site info (property parent)

```
GET /customers?id-from={site_customer_id}&id-to={site_customer_id}
```

Returns the site-level customer (e.g. "Griffith Wood") with metadata like
letting agent info and contract type.

---

## 3. ID reference (from captured session)

These are the IDs needed to navigate the entity graph. In a Python library, the
discovery flow would be:

```
1. Decode JWT → customer_id (232971), customer_code (b21afb1f-...)
2. GET /customers/{customer_code} → subscriptions, billing_profile
3. GET /customers/{customer_id}/groups?type=payment → group_id (32762)
4. GET /customers?parent-group={group_id} → property customer (201411)
   → subscription_id (14582), balance_group_id (14583), meter identifier (04801107)
5. GET /customers/{property_id}/usage-events?... → daily readings
6. POST /reports/usage → aggregated chart data
```

| Entity | ID | Notes |
|--------|----|-------|
| Person customer (numeric) | `232971` | From JWT `customer_id` |
| Person customer (UUID) | `b21afb1f-1e10-4d17-bf8a-cebd07daf40a` | From JWT `customer_code` |
| Person subscription | `48770` | Platform subscription |
| Person billing profile | `47891` | For invoices/payments |
| Payment group | `32762` | Links person → property |
| Property customer | `201411` | **Usage events live here** |
| Property subscription | `14582` | Heat meter subscription |
| Property balance group | `14583` | For usage-events queries |
| Heat meter serial | `04801107` | Physical meter identifier |
| Property code | `GFW296` | Internal property ref |
| Site code | `GFW` | Griffith Wood |
| Site customer | `201115` | Site-level entity |

---

## 4. Pricing

From the captured usage events, the tariff appears to be:

| kWh consumed | Cost (EUR) | Rate (EUR/kWh) |
|-------------|------------|----------------|
| 1 | 0.810 | 0.810 |
| 3 | 0.372 | 0.124 |
| 4 | 1.182 | 0.296 |
| 5 | 1.306 | 0.261 |
| 6 | 1.430 | 0.238 |
| 7 | 1.554 | 0.222 |
| 8 | 1.678 | 0.210 |
| 9 | 1.802 | 0.200 |

The pricing appears to be a fixed **€0.124/kWh** usage rate plus a
**€0.686/day** standing charge (visible where 1 kWh costs €0.81 = 0.124 +
0.686). This should be verified against an actual invoice.

---

## 5. External dependencies

| Service | URL | Purpose |
|---------|-----|---------|
| Stripe | via `payment_gateway_profile` | Card payments |
| AWS S3 | `self-care-app-data.s3.eu-west-1.amazonaws.com` | Consent documents |
| Google Fonts | `fonts.googleapis.com` | UI fonts (Dosis, Open Sans) |

---

## 6. Python library auth strategy

The recommended approach for `pyyunoheat`:

1. **Try direct grant first** — `grant_type=password` with `client_id=mobile-yuno`.
   This is the cleanest path and avoids browser automation entirely.

2. **If direct grant is disabled**, implement the Authorization Code flow with
   PKCE: start a local HTTP server on a random port, open the Keycloak auth URL
   in the user's browser, capture the redirect with the auth code, exchange it
   for tokens.

3. **Token management** — persist the refresh token to disk
   (`~/.config/yunoheat/tokens.json`), refresh automatically before expiry
   (access token TTL is 30 min, refresh is 35 min). The short refresh window
   means sessions can't survive overnight; re-authentication will be needed.

4. **Session bootstrap** — on first API call:
   - Decode JWT to extract `customer_id` and `customer_code`
   - Call `/customers/{customer_code}` to get person details
   - Call `/customers/{customer_id}/groups?type=payment` to find payment group
   - Call `/customers?parent-group={group_id}` to discover property customer
   - Cache the property customer ID, subscription ID, balance group ID, and
     meter identifier for subsequent usage data queries
