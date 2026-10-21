"""This module provides a config for the obi_auth service."""

import os
from pathlib import Path
from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from obi_auth.exception import ConfigError
from obi_auth.typedef import DeploymentEnvironment, KeycloakRealm
from obi_auth.util import get_config_dir

_DEFAULT_WIDGET_REDIRECT_URI = "http://localhost:8888/callback/"
# OAuth2 scopes for the notebook sign-in widget. Not deployment-specific, so it
# is a constant rather than a configurable setting.
_WIDGET_SCOPE = "openid profile"


class Settings(BaseSettings):
    """Environment settings for this library."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="OBI_AUTH_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        validate_default=False,
        extra="ignore",
    )

    config_dir: Annotated[
        Path,
        Field(
            description="Directory to store the token.",
            default_factory=get_config_dir,
        ),
    ]

    KEYCLOAK_ENV: DeploymentEnvironment = DeploymentEnvironment.staging
    KEYCLOAK_REALM: KeycloakRealm = KeycloakRealm.sbo
    KEYCLOAK_CLIENT_ID: str = "obi-entitysdk-auth"

    EPSILON_TOKEN_TTL_SECONDS: int = 60

    LOCAL_SERVER_TIMEOUT: int = 60

    # Notebook widget (auth_mode="widget") settings. Redirect URI resolution is
    # documented on resolve_widget_redirect_uri below.
    WIDGET_REDIRECT_URI: str | None = None
    # JupyterHub public host (e.g. https://jupyterhub.staging.openbrainplatform.com).
    # When set, the per-user redirect is derived as
    # {WIDGET_PUBLIC_HOST}{JUPYTERHUB_SERVICE_PREFIX}callback/.
    WIDGET_PUBLIC_HOST: str | None = None
    WIDGET_CLIENT_ID: str = "obi-entitysdk-auth"
    WIDGET_TIMEOUT_SECONDS: int = 300

    def resolve_widget_redirect_uri(self, redirect_uri: str | None = None) -> str:
        """Resolve the OAuth2 redirect uri for the notebook sign-in widget.

        Resolution order:

        1. ``redirect_uri`` argument if provided.
        2. ``WIDGET_REDIRECT_URI`` if explicitly configured.
        3. Derived per-user URI from the running Jupyter server's service prefix
           (``JUPYTERHUB_SERVICE_PREFIX``) combined with ``WIDGET_PUBLIC_HOST``.
           This yields e.g.
           ``https://jupyterhub.example.org/user/<username>/<server>/callback/``.
        4. The local development default ``http://localhost:8888/callback/``.
        """
        if redirect_uri:
            return redirect_uri
        if self.WIDGET_REDIRECT_URI:
            return self.WIDGET_REDIRECT_URI

        public_host = self.WIDGET_PUBLIC_HOST
        service_prefix = os.environ.get("JUPYTERHUB_SERVICE_PREFIX")
        if public_host and service_prefix:
            # service_prefix is like "/user/<username>/<server>/" (trailing slash).
            base = public_host.rstrip("/")
            prefix = "/" + service_prefix.strip("/") + "/"
            return f"{base}{prefix}callback/"

        return _DEFAULT_WIDGET_REDIRECT_URI

    def _get_domain_url(self, override_env: DeploymentEnvironment) -> str:
        """Return domain url based on environment."""
        match env := override_env or self.KEYCLOAK_ENV:
            case DeploymentEnvironment.staging:
                return "https://staging.cell-a.openbraininstitute.org"
            case DeploymentEnvironment.production:
                return "https://cell-a.openbraininstitute.org"
            case _:
                raise ConfigError(f"Unknown deployment environment {env}")

    def get_keycloak_base_url(self, override_env: DeploymentEnvironment | None = None) -> str:
        """Return the Keycloak base url (``{domain}/auth``).

        This is the ``base_url`` expected by ``ipyauth_pkce.ParamsKeycloak``, which
        appends ``/realms/{realm}/...`` itself.
        """
        url = self._get_domain_url(override_env or self.KEYCLOAK_ENV)
        return f"{url}/auth"

    def get_keycloak_url(self, override_env: DeploymentEnvironment | None = None):
        """Return keycloak url."""
        base_url = self.get_keycloak_base_url(override_env=override_env)
        return f"{base_url}/realms/{self.KEYCLOAK_REALM}"

    def get_keycloak_token_endpoint(self, override_env: DeploymentEnvironment | None = None) -> str:
        """Return keycloak token endpoint."""
        base_url = self.get_keycloak_url(override_env=override_env)
        return f"{base_url}/protocol/openid-connect/token"

    def get_keycloak_auth_endpoint(self, override_env: DeploymentEnvironment | None = None) -> str:
        """Return keycloak auth endpoint."""
        base_url = self.get_keycloak_url(override_env=override_env)
        return f"{base_url}/protocol/openid-connect/auth"

    def get_keycloak_device_auth_endpoint(
        self, override_env: DeploymentEnvironment | None = None
    ) -> str:
        """Return keycloack device auth endpoint."""
        base_url = self.get_keycloak_url(override_env=override_env)
        return f"{base_url}/protocol/openid-connect/auth/device"

    def get_keycloak_user_info_endpoint(
        self, override_env: DeploymentEnvironment | None = None
    ) -> str:
        """Return keycloak user info endpoint."""
        base_url = self.get_keycloak_url(override_env=override_env)
        return f"{base_url}/protocol/openid-connect/userinfo"

    def get_auth_manager_url(self, override_env: DeploymentEnvironment | None = None) -> str:
        """Return auth manager url."""
        url = self._get_domain_url(override_env or self.KEYCLOAK_ENV)
        return f"{url}/api/auth-manager/v1"

    def get_auth_manager_access_token_endpoint(
        self, override_env: DeploymentEnvironment | None = None
    ) -> str:
        """Return auth-manager token endpoint."""
        base_url = self.get_auth_manager_url(override_env=override_env)
        return f"{base_url}/access-token"

    def get_auth_manager_token_exchange_endpoint(
        self, override_env: DeploymentEnvironment | None = None
    ) -> str:
        """Return auth-manager token exchange endpoint."""
        base_url = self.get_auth_manager_url(override_env=override_env)
        return f"{base_url}/token-exchange"


settings = Settings()
