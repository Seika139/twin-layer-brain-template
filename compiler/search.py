from __future__ import annotations

import json

from compiler.embedding import generate_embedding, is_embedding_available
from compiler.indexer import ensure_db
from compiler.models import Note


def _normalize_fts_query(query: str) -> str:
    """Wrap user queries so FTS5 doesn't crash on operators or stray quotes."""
    stripped = query.strip()
    if stripped.startswith('"') and stripped.endswith('"') and stripped.count('"') == 2:
        return query
    sanitized = query.replace('"', "")
    if any(c in sanitized for c in "-+*()"):
        return f'"{sanitized}"'
    return sanitized


def search_fts(query: str, limit: int = 20) -> list[Note]:
    """Full-text search using FTS5 trigram."""
    conn = ensure_db()
    rows = conn.execute(
        """
        SELECT n.path, n.note_id, n.title, n.kind, n.tags,
               n.created_at, n.updated_at, n.body_text, n.raw_markdown
        FROM notes_fts f
        JOIN notes n ON n.rowid = f.rowid
        WHERE notes_fts MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (_normalize_fts_query(query), limit),
    ).fetchall()
    conn.close()
    return [_row_to_note(r) for r in rows]


def search_similar(query: str, limit: int = 10) -> list[tuple[Note, float]]:
    """Semantic search using embedding similarity."""
    if not is_embedding_available():
        return []

    vec = generate_embedding(query)
    if vec is None:
        return []

    conn = ensure_db()
    rows = conn.execute(
        """
        SELECT v.note_id, v.distance,
               n.path, n.title, n.kind, n.tags,
               n.created_at, n.updated_at, n.body_text, n.raw_markdown
        FROM notes_vec v
        JOIN notes n ON n.note_id = v.note_id
        WHERE v.embedding MATCH ?
        ORDER BY v.distance
        LIMIT ?
        """,
        (vec, limit),
    ).fetchall()
    conn.close()

    results = []
    for row in rows:
        distance = row[1]
        note = Note(
            path=row[2],
            note_id=row[0],
            title=row[3],
            kind=row[4],
            tags=json.loads(row[5]) if row[5] else [],
            body_text=row[8],
            raw_markdown=row[9],
        )
        results.append((note, distance))
    return results


def suggest_related(note_id: str, limit: int = 5) -> list[tuple[Note, float]]:
    """Find related notes based on embedding similarity."""
    if not is_embedding_available():
        return []

    conn = ensure_db()

    # Get the embedding for the target note
    row = conn.execute(
        "SELECT embedding FROM notes_vec WHERE note_id = ?",
        (note_id,),
    ).fetchone()
    if row is None:
        conn.close()
        return []

    target_vec = row[0]
    rows = conn.execute(
        """
        SELECT v.note_id, v.distance,
               n.path, n.title, n.kind, n.tags,
               n.created_at, n.updated_at, n.body_text, n.raw_markdown
        FROM notes_vec v
        JOIN notes n ON n.note_id = v.note_id
        WHERE v.embedding MATCH ?
          AND v.note_id != ?
        ORDER BY v.distance
        LIMIT ?
        """,
        (target_vec, note_id, limit),
    ).fetchall()
    conn.close()

    results = []
    for r in rows:
        note = Note(
            path=r[2],
            note_id=r[0],
            title=r[3],
            kind=r[4],
            tags=json.loads(r[5]) if r[5] else [],
            body_text=r[8],
            raw_markdown=r[9],
        )
        results.append((note, r[1]))
    return results


def read_note(id_or_path: str) -> Note | None:
    """Read a single note by ID or path."""
    conn = ensure_db()
    row = conn.execute(
        """
        SELECT path, note_id, title, kind, tags,
               created_at, updated_at, body_text, raw_markdown
        FROM notes
        WHERE note_id = ? OR path = ? OR path LIKE ?
        LIMIT 1
        """,
        (id_or_path, id_or_path, f"%{id_or_path}%"),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return _row_to_note(row)


def _row_to_note(row: tuple[str, ...]) -> Note:
    return Note(
        path=row[0],
        note_id=row[1],
        title=row[2],
        kind=row[3],
        tags=json.loads(row[4]) if row[4] else [],
        body_text=row[7],
        raw_markdown=row[8],
    )
