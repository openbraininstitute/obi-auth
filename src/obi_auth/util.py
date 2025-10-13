"""Utilities."""

import base64
import getpass
import hashlib
import platform
import sys
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


def is_running_in_notebook() -> bool:
    """Check if code is running in a Jupyter notebook environment."""
    try:
        # Check for IPython
        if "IPython" in sys.modules:
            from IPython import get_ipython

            ipython = get_ipython()
            if ipython is not None:
                # Check if it's running in a notebook
                return ipython.__class__.__name__ == "ZMQInteractiveShell"

        # Alternative check for notebook environment
        if "jupyter" in sys.modules or "notebook" in sys.modules:
            return True

        # Check for common notebook-related modules
        notebook_modules = ["ipykernel", "ipywidgets", "notebook"]
        return any(module in sys.modules for module in notebook_modules)

    except (ImportError, AttributeError):
        pass

    return False
