"""Exceptions module."""


class ObiAuthError(Exception):
    """Generic obi-auth error."""


class AuthFlowError(ObiAuthError):
    """Authenticatin flow error."""


class ClientError(ObiAuthError):
    """Client related error."""


class LocalServerError(ObiAuthError):
    """Local server related error."""


class ConfigError(ObiAuthError):
    """Configuration settings error."""
