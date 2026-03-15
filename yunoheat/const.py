"""Constants for the Yuno Energy Heat API and Keycloak auth."""

# Keycloak realm
KEYCLOAK_REALM = "kaizen-energy-sandbox"
KEYCLOAK_ISSUER = "https://app.tridenstechnology.com/auth/realms/kaizen-energy-sandbox"
KEYCLOAK_TOKEN_URL = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/token"
KEYCLOAK_CLIENT_ID = "mobile-yuno"
KEYCLOAK_SCOPES = "openid kaizen-energy"

# API
API_BASE_URL = "https://app.tridenstechnology.com/monetization/api/v1"

# Token persistence
DEFAULT_TOKEN_PATH_PARTS = ("~", ".config", "yunoheat", "tokens.json")

# TTLs (seconds). Refresh when remaining lifetime < TOKEN_REFRESH_MARGIN.
ACCESS_TOKEN_TTL = 1800  # 30 min
REFRESH_TOKEN_TTL = 2100  # 35 min
TOKEN_REFRESH_MARGIN = 60  # refresh if expiry is within 60 s

# Service type used in usage-event queries
HEAT_SERVICE_TYPE = "HEAT_METER_READ_SERVICE"

# Interval values accepted by POST /reports/usage
REPORT_INTERVAL_DAY = "day"
REPORT_INTERVAL_WEEK = "week"
REPORT_INTERVAL_MONTH = "month"
REPORT_INTERVAL_QUARTER = "quarter"
REPORT_INTERVAL_YEAR = "year"

# Elasticsearch resource_name bucket keys in /reports/usage
RESOURCE_EURO = "Euro"
RESOURCE_HEAT = "Heat - Meter Value"
