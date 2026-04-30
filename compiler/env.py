from __future__ import annotations

import os as os

from compiler.paths import BASE_DIR


def use_system_trust_store() -> None:
    """Use the OS trust store (macOS Keychain, Windows cert store, Linux openssl)
    for TLS verification instead of Python's bundled certifi CA list.

    Required under MITM proxies (Netskope, Zscaler, Blue Coat, ...) whose CA
    certificates are trusted by the OS but not by certifi, and whose older
    non-critical Basic Constraints fail OpenSSL 3.x's strict RFC 5280 check
    when fed via SSL_CERT_FILE. Platforms without a MITM proxy behave
    equivalently to certifi, so it is safe to call unconditionally.
    """
    import truststore

    truststore.inject_into_ssl()


def load_dotenv() -> None:
    """Load repo-root .env into os.environ, preferring repo-local values.

    Shared by `server/run.py` (HTTP server) and `compiler/cli.py` (kc CLI)
    so both see the same keys.
    """
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        if key and value:
            os.environ[key.strip()] = value.strip()
