import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_DIR = BASE_DIR / "index"
DB_PATH = INDEX_DIR / "knowledge.db"

CONTENT_DIRS = ["inbox", "raw", "notes", "projects", "daily"]

SERVER_HOST = os.environ.get("SECOND_BRAIN_HOST", "127.0.0.1")
SERVER_PORT = int(os.environ.get("SECOND_BRAIN_PORT", "15200"))

OPENAI_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
