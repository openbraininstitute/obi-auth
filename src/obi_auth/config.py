"""This module provides a config for the obi_auth service."""

from pydantic_settings import BaseSettings, SettingsConfigDict

from obi_auth.typedef import DeploymentEnvironment, KeycloakRealm


class Settings(BaseSettings):
    """Environment settings for this library."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="OBI_AUTH_",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    KEYCLOAK_ENV: DeploymentEnvironment = DeploymentEnvironment.staging
    KEYCLOAK_REALM: KeycloakRealm = KeycloakRealm.sbo
    KEYCLOAK_CLIENT_ID: str = "obi-entitysdk-auth"

    LOCAL_SERVER_TIMEOUT: int = 60

    def get_keycloak_url(self, override_env: str | None = None):
        """Return keycloak url."""
        env = override_env or self.KEYCLOAK_ENV
        return f"https://{env}.openbraininstitute.org/auth/realms/{self.KEYCLOAK_REALM}"

    def get_keycloak_token_endpoint(self, override_env: str | None = None) -> str:
        """Return keycloak token endpoint."""
        base_url = self.get_keycloak_url(override_env=override_env)
        return f"{base_url}/protocol/openid-connect/token"

    def get_keycloak_auth_endpoint(self, override_env: str | None = None) -> str:
        """Return keycloak auth endpoint."""
        base_url = self.get_keycloak_url(override_env=override_env)
        return f"{base_url}/protocol/openid-connect/auth"


settings = Settings()
