import os
import functools
from typing import Tuple

from .config import settings


@functools.lru_cache(maxsize=1)
def load_keypair() -> Tuple[str, str]:
    """
    Load RS256 key pair (private, public) from PEM files defined by environment variables.
    Returns PEM contents as strings. Results are cached in memory.
    """
    # Derive paths from env via settings
    private_path = os.getenv("JWT_PRIVATE_KEY_PATH", "secrets/jwt_private.pem")
    public_path = os.getenv("JWT_PUBLIC_KEY_PATH", "secrets/jwt_public.pem")

    # Keep compatibility with future settings.security extension if needed
    try:
        if getattr(settings, "security", None):
            # Accept overrides from env; presence of settings ensures initialization
            private_path = os.getenv("JWT_PRIVATE_KEY_PATH", private_path)
            public_path = os.getenv("JWT_PUBLIC_KEY_PATH", public_path)
    except Exception:
        # In case settings are not fully initialized at import time
        pass

    if not os.path.exists(private_path):
        raise FileNotFoundError(f"JWT private key not found at path: {private_path}")
    if not os.path.exists(public_path):
        raise FileNotFoundError(f"JWT public key not found at path: {public_path}")

    with open(private_path, "r", encoding="utf-8") as f:
        private_key = f.read()
    with open(public_path, "r", encoding="utf-8") as f:
        public_key = f.read()

    if (
        "BEGIN RSA PRIVATE KEY" not in private_key
        and "BEGIN PRIVATE KEY" not in private_key
    ):
        raise ValueError("Invalid private key PEM content")
    if "BEGIN PUBLIC KEY" not in public_key:
        raise ValueError("Invalid public key PEM content")

    return private_key, public_key
