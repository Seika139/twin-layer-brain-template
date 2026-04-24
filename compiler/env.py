from __future__ import annotations

import os

from compiler.config import BASE_DIR


def load_dotenv() -> None:
    """Load repo-root .env into os.environ with setdefault semantics.

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
            os.environ.setdefault(key.strip(), value.strip())
