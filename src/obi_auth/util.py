"""Utilities."""

import base64
import hashlib
import platform
import socket
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def get_machine_salt():
    """Get machine specific salt."""
    hostname = socket.gethostname()
    system = platform.uname().system
    node = platform.uname().node
    raw = f"{hostname}-{system}-{node}"
    return hashlib.sha256(raw.encode()).digest()


def derive_fernet_key() -> bytes:
    """Create Fernet key from unique machine salt."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        backend=default_backend(),
        salt=None,  # Optional: use one if you want context separation
        info=b"machine-specific-fernet-key",  # Application-specific context
    )
    key = hkdf.derive(get_machine_salt())
    return base64.urlsafe_b64encode(key)  # Fernet requires base64 encoding


def get_config_path() -> Path:
    """Get config file path."""
    file_name = f"{get_machine_salt().hex()}.json"
    directory = Path.home() / ".config" / "obi-auth"
    directory.mkdir(exist_ok=True, parents=True)
    directory.chmod(0o700)
    return directory / file_name
