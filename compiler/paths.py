"""Env-independent filesystem paths.

Kept separate from `compiler.config` so that `compiler.env.load_dotenv()`
can resolve `BASE_DIR` without triggering evaluation of env-dependent
values like `BRAIN_PORT` at module-load time.

`BASE_DIR` resolution order:

1. `BRAIN_ROOT` environment variable, if set. Used when the compiler is
    installed as a package (site-packages) and must be told where the
    brain instance's `raw/`, `wiki/`, `index/` live.
2. Fallback: two levels up from this file. Correct for the in-repo
    layout where `compiler/paths.py` sits under the brain root.
"""

from __future__ import annotations

import os
from pathlib import Path


def _resolve_base_dir() -> Path:
    env = os.environ.get("BRAIN_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parent.parent


BASE_DIR = _resolve_base_dir()
INDEX_DIR = BASE_DIR / "index"
DB_PATH = INDEX_DIR / "knowledge.db"
