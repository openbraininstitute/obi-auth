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

    LOCAL_SERVER_TIMEOUT: int = 60

    def get_keycloak_url(self, override_env: DeploymentEnvironment | None = None):
        """Return keycloak url."""
        match env := override_env or self.KEYCLOAK_ENV:
            case DeploymentEnvironment.staging:
                return f"https://staging.openbraininstitute.org/auth/realms/{self.KEYCLOAK_REALM}"
            case DeploymentEnvironment.production:
                return f"https://www.openbraininstitute.org/auth/realms/{self.KEYCLOAK_REALM}"
        raise ConfigError(f"Unknown deployment environment {env}")

    def get_keycloak_token_endpoint(self, override_env: DeploymentEnvironment | None = None) -> str:
        """Return keycloak token endpoint."""
        base_url = self.get_keycloak_url(override_env=override_env)
        return f"{base_url}/protocol/openid-connect/token"

    def get_keycloak_auth_endpoint(self, override_env: DeploymentEnvironment | None = None) -> str:
        """Return keycloak auth endpoint."""
        base_url = self.get_keycloak_url(override_env=override_env)
        return f"{base_url}/protocol/openid-connect/auth"


settings = Settings()
