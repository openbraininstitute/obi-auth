# `get_token()` reference

```python
from obi_auth import get_token

get_token(
    *,
    environment="staging",          # or "production"
    auth_mode="pkce",               # "pkce" | "daf" | "persistent_token"
    token_provider="keycloak",      # "keycloak" | "auth_manager"
    force_refresh=False,
    persistent_token_id=None,       # required for auth_mode="persistent_token"
    offline=False,                  # implies token_provider="auth_manager"
) -> str
```

Returns a single **access token** string.

## Decision matrix

| Call | Login | auth-manager | Vault id used | Local cache key (typical) |
| --- | --- | --- | --- | --- |
| `get_token()` | PKCE | no | — | `pkce_keycloak` |
| `get_token(auth_mode="daf")` | Device | no | — | `daf_keycloak` |
| `get_token(token_provider="auth_manager")` | PKCE | exchange + mint | **REFRESH** | `pkce_auth_manager` |
| `get_token(auth_mode="daf", token_provider="auth_manager")` | Device | exchange + mint | **REFRESH** | `daf_auth_manager` |
| `get_token(offline=True)` | PKCE | exchange → upgrade offline → mint | **OFFLINE** | `pkce_auth_manager_offline` |
| `get_token(auth_mode="daf", offline=True)` | Device | same as above | **OFFLINE** | `daf_auth_manager_offline` |
| `get_token(auth_mode="persistent_token", persistent_token_id=…)` | none | mint only | whatever that uuid is | keyed by the uuid |

Notes:

- `offline=True` forces `token_provider=auth_manager` even if you pass `keycloak`.
- `auth_mode="persistent_token"` ignores `token_provider` and `offline`.
- `force_refresh=True` clears the matching local cache entry, then runs the full flow again.

## Equivalent CLI

| Python | CLI |
| --- | --- |
| `get_token()` | `obi-auth get-token` |
| `get_token(token_provider="auth_manager")` | `obi-auth get-token -p auth_manager` |
| `get_token(offline=True)` | `obi-auth get-token --offline` |
| `get_token(auth_mode="daf")` | `obi-auth get-token -m daf` |
| `get_token(auth_mode="persistent_token", persistent_token_id=id)` | `obi-auth get-token -m persistent_token --persistent-token-id id` |

Stdout is **only** the access token (interactive prompts go to stderr), so piping works:

```sh
obi-auth get-token --offline | obi-auth decode-token
```

## Examples

### Keycloak only

```python
from obi_auth import get_token

# Browser PKCE → Keycloak access token
token = get_token(environment="staging")

# Device flow (good for SSH / headless with a second device)
token = get_token(environment="staging", auth_mode="daf")
```

### Session vault (auth-manager REFRESH)

```python
token = get_token(
    environment="staging",
    token_provider="auth_manager",
)
# Under the hood: PKCE → POST /token-exchange → POST /access-token
```

### Offline vault

```python
token = get_token(
    environment="staging",
    offline=True,
)
# Under the hood: PKCE → exchange → mint session AT →
#   POST /offline-token-id (or consent + poll) → POST /access-token
```

### Known vault id (e.g. launch scripts)

```python
token = get_token(
    environment="staging",
    auth_mode="persistent_token",
    persistent_token_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
)
# Under the hood: POST /access-token with header id=<uuid>
```

## Caching behaviour (all auth-manager paths)

1. If a non-expired access token is in the local cache → return it.
2. If the access token expired but a vault id is still stored → `POST /access-token` (remint).
3. If remint fails → clear local cache → run the full flow again (login / exchange / consent as needed).

Keycloak-only paths cache only the access token; when it expires you must log in again (no remint).
