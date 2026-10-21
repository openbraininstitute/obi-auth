[![Build status][build_status_badge]][build_status_target]
[![License][license_badge]][license_target]
[![Code coverage][coverage_badge]][coverage_target]
[![CodeQL][codeql_badge]][codeql_target]
[![PyPI][pypi_badge]][pypi_target]

# obi-auth

obi-auth is a library for retrieving Keycloak access tokens interactively. It helps developers and testers quickly authenticate against Keycloak without writing scripts or configuring complex clients.

> [!CAUTION]
> obi-auth is designed to be used interactively and should not be used within a service or application.

## Installation

### Basic Installation

```sh
pip install obi-auth
```

### CLI Support

To use the `obi-auth` command-line interface:

```sh
pip install obi-auth[cli]
```

This installs `click` which is required by the CLI.

### Notebook Support

For enhanced Jupyter notebook support with Rich display integration:

```sh
pip install obi-auth[notebook]
```

This installs `rich` (better rendering in Jupyter notebooks) and the
dependencies for the interactive sign-in widget (`ipyauth-pkce` and
`jupyter-ui-poll`), enabling `auth_mode="widget"` (see Examples).

## Examples

```python
from obi_auth import get_token

access_token = get_token(environment="staging")
access_token = get_token(environment="staging", token_provider="auth_manager")

# Interactive sign-in from a Jupyter notebook cell (requires the `notebook`
# extra and JupyterLab). Renders a "Sign In" widget, blocks until you sign in,
# then returns the token string -- a drop-in change from auth_mode="daf":
access_token = get_token(environment="staging", auth_mode="widget")

# Mint from an existing auth-manager persistent id (e.g. obi-one launch scripts):
access_token = get_token(
    environment="staging",
    auth_mode="persistent_token",
    persistent_token_id="<uuid>",
)
```

> [!NOTE]
> `auth_mode="widget"` only works inside JupyterLab (>= 4) with a running
> kernel. The Jupyter server must be started with `IPYAUTH_TOKEN_ENDPOINT` set
> to the OBI token endpoint for your environment (ipyauth-pkce performs the
> token exchange server-side against that endpoint).
>
> The OAuth redirect URI is resolved automatically: when
> `OBI_AUTH_WIDGET_PUBLIC_HOST` is set (e.g. your JupyterHub host), obi-auth
> derives the per-user callback from the running server prefix
> (`JUPYTERHUB_SERVICE_PREFIX`), e.g.
> `https://<host>/user/<username>/<server>/callback/`. You can override it with
> `OBI_AUTH_WIDGET_REDIRECT_URI`; otherwise it falls back to
> `http://localhost:8888/callback/` for local use.
>
> The Keycloak client used by the widget (`OBI_AUTH_KEYCLOAK_CLIENT_ID`,
> default `obi-entitysdk-auth`) must be a public client with the
> authorization-code + PKCE flow enabled, and must allow the callback redirect
> URI (on JupyterHub a wildcard such as `https://<host>/user/*` is required
> because the per-user path is dynamic).


## CLI

After installing with the `cli` extra, the `obi-auth` command is available. Run `obi-auth --help` for the full list of commands and options.

### `get-token`

Authenticate and print the access token to stdout. Output is a single token string, suitable for piping into other commands.

```sh
obi-auth get-token
obi-auth get-token -e production -m daf
obi-auth get-token -p auth_manager
obi-auth get-token -m persistent_token --persistent-token-id <uuid>
obi-auth get-token --force-refresh
```

| Option | Description |
| --- | --- |
| `-e`, `--environment` | Target environment: `staging` (default) or `production` |
| `-m`, `--auth-mode` | Authentication method: `pkce` (default), `daf`, or `persistent_token` |
| `-p`, `--token-provider` | Token issuer: `keycloak` (default) or `auth_manager` |
| `--persistent-token-id` | Persistent token id (required when `--auth-mode persistent_token`) |
| `--force-refresh` | Clear the cached token and authenticate again |

### `decode-token`

Decode a JWT and print the payload as indented JSON. Pass the token as an argument or via stdin.

```sh
obi-auth decode-token eyJhbGciOi...
obi-auth get-token | obi-auth decode-token
obi-auth get-token | obi-auth decode-token | jq -r '.sub'
```

### `get-user-info`

Authenticate, fetch user info from Keycloak, and print the result as indented JSON.

```sh
obi-auth get-user-info
obi-auth get-user-info -e production -m daf
obi-auth get-user-info -p auth_manager
obi-auth get-user-info --force-refresh
obi-auth get-user-info | jq -r '.sub'
```

| Option | Description |
| --- | --- |
| `-e`, `--environment` | Target environment: `staging` (default) or `production` |
| `-m`, `--auth-mode` | Authentication method: `pkce` (default), `daf`, or `persistent_token` |
| `-p`, `--token-provider` | Token issuer: `keycloak` (default) or `auth_manager` |
| `--persistent-token-id` | Persistent token id (required when `--auth-mode persistent_token`) |
| `--force-refresh` | Clear the cached token and authenticate again |

### Global options

| Option | Description |
| --- | --- |
| `--log-level` | Logging level: `DEBUG`, `INFO`, `WARNING` (default), `ERROR`, `CRITICAL` |

## License

Copyright (c) 2025 Open Brain Institute

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

[build_status_badge]: https://github.com/openbraininstitute/obi-auth/actions/workflows/tox.yml/badge.svg
[build_status_target]: https://github.com/openbraininstitute/obi-auth/actions
[license_badge]: https://img.shields.io/pypi/l/obi-auth
[license_target]: https://github.com/openbraininstitute/obi-auth/blob/main/LICENSE.txt
[coverage_badge]: https://codecov.io/github/openbraininstitute/obi-auth/coverage.svg?branch=main
[coverage_target]: https://codecov.io/github/openbraininstitute/obi-auth?branch=main
[codeql_badge]: https://github.com/openbraininstitute/obi-auth/actions/workflows/github-code-scanning/codeql/badge.svg
[codeql_target]: https://github.com/openbraininstitute/obi-auth/actions/workflows/github-code-scanning/codeql
[pypi_badge]: https://github.com/openbraininstitute/obi-auth/actions/workflows/sdist.yml/badge.svg
[pypi_target]: https://pypi.org/project/obi-auth/

