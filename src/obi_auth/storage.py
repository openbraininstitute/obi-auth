"""Storage module."""

from dataclasses import dataclass
from pathlib import Path

from obi_auth.typedef import TokenInfo

FILE_MODE = 0o600  # user only read/write


@dataclass
class Storage:
    """Storage class."""

    file_path: Path

    def __post_init__(self):
        """Ensure file paht has correct permissions."""
        if self.exists():
            self.file_path.chmod(mode=FILE_MODE)

    def write(self, data: TokenInfo):
        """Write token info to file."""
        self.file_path.write_text(data.model_dump_json())
        self.file_path.chmod(mode=FILE_MODE)

    def read(self) -> TokenInfo:
        """Read token info from file."""
        data = self.file_path.read_bytes()
        return TokenInfo.model_validate_json(data)

    def clear(self) -> None:
        """Delete file."""
        self.file_path.unlink(missing_ok=True)

    def exists(self) -> bool:
        """Return True if file does not exist."""
        return self.file_path.exists()
