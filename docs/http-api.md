# HTTP API reference (what obi-auth calls)

Base URL used by this library:

```text
{domain}/api/auth-manager/v1
```

| Environment | `{domain}` |
| --- | --- |
| staging | `https://staging.cell-a.openbraininstitute.org` |
| production | `https://cell-a.openbraininstitute.org` |

Keycloak base:

```text
{domain}/auth/realms/SBO
```

Success bodies from auth-manager are wrapped as `{ "data": … }`.

---

## Keycloak (public client)

### Authorization code + PKCE

1. Browser opens `{keycloak}/protocol/openid-connect/auth` with `client_id`, `redirect_uri` (local server), `code_challenge`, `state`, `scope=openid`, …
2. Local callback receives `?code=&state=`
3. `POST {keycloak}/protocol/openid-connect/token` with `grant_type=authorization_code`, `code_verifier`, …

### Device authorization (DAF)

1. `POST {keycloak}/protocol/openid-connect/auth/device` with `client_id`
2. Poll `POST {keycloak}/protocol/openid-connect/token` with `grant_type=urn:ietf:params:oauth:grant-type:device_code`

### User info

`GET {keycloak}/protocol/openid-connect/userinfo` with `Authorization: Bearer <access_token>` (used by `get_user_info`).

---

## auth-manager endpoints used by obi-auth

### `POST /token-exchange`

**When:** `token_provider=auth_manager` or `offline=True` (after Keycloak login).

| | |
| --- | --- |
| Auth | `Authorization: Bearer <public-client access token>` |
| Body | none |
| **200** | `{ "data": { "id": "<uuid>" } }` — REFRESH vault id (upsert for user+session) |
| Errors | 401 invalid Bearer; 502 Keycloak/DB failures |

Side effect: Keycloak standard token exchange as confidential client → encrypt/store **REFRESH**.

### `POST /access-token`

**When:** after exchange; after offline id; remint from cache; `auth_mode=persistent_token`.

| | |
| --- | --- |
| Auth | none (possession of id) |
| Headers | `id: <persistent-token-uuid>` |
| **200** | `{ "data": { "access_token": "<jwt>", "expires_in": <int> } }` |
| **404** | unknown id |

Side effect: decrypt vault row → Keycloak refresh/offline grant → return AT. May rotate stored REFRESH ciphertext when Keycloak returns a refresh-type RT.

obi-auth only keeps `data.access_token` (plus the id it already knows).

### `POST /offline-token-id`

**When:** offline upgrade after a session vault access token exists.

| | |
| --- | --- |
| Auth | `Authorization: Bearer <access token>` (session vault AT from mint) |
| Body | none |
| **200** | `{ "data": { "persistent_token_id": "<uuid>", "session_state_id": "…" } }` |
| **404** | no OFFLINE row for this Bearer’s Keycloak session yet |

Side effect: finds an existing OFFLINE for the session, asks Keycloak for an offline token (often the same material), **`store()` inserts a new OFFLINE row** with `attributes.from` pointing at the prior entry, returns the **new** uuid.

### `GET /offline-token`

**When:** `POST /offline-token-id` returned 404.

| | |
| --- | --- |
| Auth | `Authorization: Bearer <session access token>` |
| **200** | `{ "data": { "consent_url": "https://…", "session_state_id": "…", "message": "…" } }` |

Side effect: builds Keycloak auth URL with `scope` including `offline_access` and an ack-state JWT. obi-auth prints the URL (stderr), opens a browser, then polls `POST /offline-token-id`.

Consent completion is handled by auth-manager’s `GET /offline-token/callback` (not called by obi-auth directly): Keycloak redirects there with `code`/`state`; auth-manager stores the first OFFLINE row and redirects the browser to a client feedback page.

---

## Endpoints auth-manager exposes but obi-auth does not call

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/refresh-token` | Store a confidential-client refresh token directly |
| `POST` | `/refresh-token-id` | Resolve/rotate REFRESH id from Bearer session |
| `DELETE` | `/offline-token-id` | Revoke offline vault row (+ maybe KC offline session) |
| `GET` | `/validate-token` | Introspect Bearer |
| `GET` | `/offline-token/callback` | Keycloak redirect target after consent |

See the auth-manager service README for those flows (NextAuth / frontend).
