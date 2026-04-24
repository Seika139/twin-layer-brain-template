import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_DIR = BASE_DIR / "index"
DB_PATH = INDEX_DIR / "knowledge.db"

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
