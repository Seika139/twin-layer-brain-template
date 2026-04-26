"""Env-independent filesystem paths.

Kept separate from `compiler.config` so that `compiler.env.load_dotenv()`
can resolve `BASE_DIR` without triggering evaluation of env-dependent
values like `BRAIN_PORT` at module-load time.
"""

from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_DIR = BASE_DIR / "index"
DB_PATH = INDEX_DIR / "knowledge.db"
