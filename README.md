# obi-auth

obi-auth is a library for retrieving Keycloak access tokens interactively. It helps developers and testers quickly authenticate against Keycloak without writing scripts or configuring complex clients.


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
