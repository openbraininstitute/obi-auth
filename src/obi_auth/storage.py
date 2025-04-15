"""Storage module."""

from pathlib import Path

from obi_auth.typedef import DeploymentEnvironment, TokenInfo

FILE_MODE = 0o600  # user only read/write
DIRECTORY_MODE = 0o700
ENV_TO_FILE_NAME = {
    DeploymentEnvironment.staging: "token-staging.json",
    DeploymentEnvironment.production: "token-production.json",
}


class Storage:
    """Storage class."""

    def __init__(self, config_dir: Path, environment: DeploymentEnvironment) -> None:
        """Initialize storage file from config dir and environment flag."""
        config_dir.mkdir(exist_ok=True, parents=True)
        config_dir.chmod(mode=DIRECTORY_MODE)
        self._file_path = config_dir / ENV_TO_FILE_NAME[environment]

    def write(self, data: TokenInfo):
        """Write token info to file."""
        self._ensure_file_mode()
        self._file_path.write_text(data.model_dump_json())

    def read(self) -> TokenInfo | None:
        """Read token info from file."""
        if not self.exists():
            return None
        data = self._file_path.read_bytes()
        return TokenInfo.model_validate_json(data)

    def clear(self) -> None:
        """Delete file."""
        self._file_path.unlink(missing_ok=True)

    def exists(self) -> bool:
        """Return True if file does not exist."""
        return self._file_path.exists()

    def _ensure_file_mode(self) -> None:
        if self.exists():
            self._file_path.chmod(mode=FILE_MODE)
        else:
            self._file_path.touch(mode=FILE_MODE)
