from __future__ import annotations

import os
import struct
import sys

from compiler.config import EMBEDDING_DIM, OPENAI_MODEL

_embedding_warned = False


def is_embedding_available() -> bool:
    """Check if OpenAI API key is configured."""
    return bool(os.environ.get("OPENAI_API_KEY"))


def generate_embedding(text: str) -> bytes | None:
    """Generate an embedding vector using OpenAI API.

    Returns serialized float vector for sqlite-vec, or None if unavailable.
    """
    global _embedding_warned

    if not is_embedding_available():
        return None

    try:
        from openai import OpenAI

        client = OpenAI()
        response = client.embeddings.create(
            model=OPENAI_MODEL,
            input=text[:8000],  # Truncate to stay within token limits
        )
        vec = response.data[0].embedding
        return _serialize_vec(vec)
    except Exception as e:
        if not _embedding_warned:
            print(f"Warning: embedding skipped: {e}", file=sys.stderr)
            _embedding_warned = True
        return None


def _serialize_vec(vec: list[float]) -> bytes:
    """Serialize a float list to bytes for sqlite-vec."""
    return struct.pack(f"{EMBEDDING_DIM}f", *vec)


def _deserialize_vec(data: bytes) -> list[float]:
    """Deserialize bytes back to float list."""
    return list(struct.unpack(f"{EMBEDDING_DIM}f", data))
