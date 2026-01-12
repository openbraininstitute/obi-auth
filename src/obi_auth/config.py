"""This module provides a config for the obi_auth service."""

from pathlib import Path
from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from obi_auth.exception import ConfigError
from obi_auth.typedef import DeploymentEnvironment, KeycloakRealm
from obi_auth.util import get_config_dir


class Settings(BaseSettings):
    """Environment settings for this library."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="OBI_AUTH_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        validate_default=False,
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

    def _get_domain_url(self, override_env: DeploymentEnvironment) -> str:
        """Return domain url based on environment."""
        match env := override_env or self.KEYCLOAK_ENV:
            case DeploymentEnvironment.staging:
                return "https://staging.cell-a.openbraininstitute.org"
            case DeploymentEnvironment.production:
                return "https://cell-a.openbraininstitute.org"
            case _:
                raise ConfigError(f"Unknown deployment environment {env}")

    def get_keycloak_url(self, override_env: DeploymentEnvironment | None = None):
        """Return keycloak url."""
        url = self._get_domain_url(override_env or self.KEYCLOAK_ENV)
        return f"{url}/auth/realms/{self.KEYCLOAK_REALM}"

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


settings = Settings()
