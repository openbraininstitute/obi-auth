"""Exceptions module."""


class ObiAuthError(Exception):
    """Generic obi-auth error."""


class AuthFlowError(ObiAuthError):
    """Authenticatin flow error."""


class AuthCancelledError(ObiAuthError):
    """Interactive sign-in did not complete (cancelled, failed, or timed out).

    Rendered in notebooks as a concise one-line message without a traceback,
    since it is an expected outcome the user can resolve by re-running the cell.
    """

    def _render_traceback_(self):
        # IPython renders this (a list of lines) instead of the full traceback.
        return [str(self)]


class ClientError(ObiAuthError):
    """Client related error."""


class LocalServerError(ObiAuthError):
    """Local server related error."""


class ConfigError(ObiAuthError):
    """Configuration settings error."""
