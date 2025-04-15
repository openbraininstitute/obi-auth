"""Utilities."""

import base64
import getpass
import hashlib
import platform
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def get_machine_salt():
    """Get machine specific salt."""
    uname = platform.uname()
    network_name = platform.node()
    user = getpass.getuser()
    raw = f"{uname.system}-{uname.release}-{uname.version}-{uname.machine}-{network_name}-{user}"
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


def get_config_dir() -> Path:
    """Get config file path."""
    return Path.home() / ".config" / "obi-auth"
