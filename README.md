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

### Notebook Support

For enhanced Jupyter notebook support with Rich display integration:

```sh
pip install obi-auth[notebook]
```

This installs `rich` which provides better rendering in Jupyter notebooks.

## Examples

```python
from obi_auth import get_token

access_token = get_token(environment="staging")
access_token = get_token(environment="staging", token_provider="auth_manager")
```

## CLI

After installation, the `obi-auth` command is available. Run `obi-auth --help` for the full list of commands and options.

### `get-token`

Authenticate and print the access token to stdout. Output is a single token string, suitable for piping into other commands.

```sh
obi-auth get-token
obi-auth get-token -e production -m daf
obi-auth get-token -p auth_manager
obi-auth get-token --force-refresh
```

| Option | Description |
| --- | --- |
| `-e`, `--environment` | Target environment: `staging` (default) or `production` |
| `-m`, `--auth-mode` | Authentication method: `pkce` (default) or `daf` |
| `-p`, `--token-provider` | Token issuer: `keycloak` (default) or `auth_manager` |
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
| `-m`, `--auth-mode` | Authentication method: `pkce` (default) or `daf` |
| `-p`, `--token-provider` | Token issuer: `keycloak` (default) or `auth_manager` |
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

