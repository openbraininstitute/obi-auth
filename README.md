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

```sh
pip install obi-auth
```

## Examples

```python
from obi_auth import get_token

access_token = get_token(environment="staging")
```

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

