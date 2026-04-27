import os

# Env-dependent values and tuning constants only.
# Pure filesystem paths live in `compiler.paths` so that `compiler.env.load_dotenv()`
# can resolve `BASE_DIR` without triggering evaluation of `os.environ.get(...)` here.

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
