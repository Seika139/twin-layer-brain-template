import os

# Re-exported from `compiler.paths` so existing `from compiler.config import BASE_DIR`
# call sites keep working. The split exists to let `compiler.env.load_dotenv()`
# resolve paths without triggering this module's env-dependent values.
from compiler.paths import BASE_DIR, DB_PATH, INDEX_DIR

__all__ = [
    "BASE_DIR",
    "INDEX_DIR",
    "DB_PATH",
    "CONTENT_DIRS",
    "SERVER_HOST",
    "SERVER_PORT",
    "OPENAI_MODEL",
    "EMBEDDING_DIM",
]

# twin-layer-brain は raw/ (人間所有) と wiki/ (LLM 所有) を Layer 1 索引の対象にする。
# raw/repos は巨大・gitignored なので索引しない。
CONTENT_DIRS = [
    "raw/notes",
    "raw/articles",
    "wiki/sources",
    "wiki/entities",
    "wiki/concepts",
    "wiki/topics",
]

SERVER_HOST = os.environ.get("BRAIN_HOST", "127.0.0.1")
SERVER_PORT = int(os.environ.get("BRAIN_PORT", "15200"))

OPENAI_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
