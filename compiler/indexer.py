from __future__ import annotations

import json
import sqlite3

import sqlite_vec

from pathlib import Path

from compiler.config import CONTENT_DIRS
from compiler.paths import BASE_DIR, DB_PATH, INDEX_DIR
from compiler.embedding import generate_embedding, is_embedding_available
from compiler.frontmatter import parse_note
from compiler.models import Note


def ensure_db() -> sqlite3.Connection:
    """Create or open the SQLite database with FTS5 and vec tables."""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.execute("PRAGMA journal_mode=WAL")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS notes (
            path TEXT PRIMARY KEY,
            note_id TEXT,
            title TEXT,
            kind TEXT,
            tags TEXT,
            created_at TEXT,
            updated_at TEXT,
            body_text TEXT,
            raw_markdown TEXT
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
            title, body_text,
            content='notes',
            content_rowid='rowid',
            tokenize='trigram'
        );

        CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
            INSERT INTO notes_fts(rowid, title, body_text)
            VALUES (new.rowid, new.title, new.body_text);
        END;

        CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
            INSERT INTO notes_fts(notes_fts, rowid, title, body_text)
            VALUES ('delete', old.rowid, old.title, old.body_text);
        END;

        CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
            INSERT INTO notes_fts(notes_fts, rowid, title, body_text)
            VALUES ('delete', old.rowid, old.title, old.body_text);
            INSERT INTO notes_fts(rowid, title, body_text)
            VALUES (new.rowid, new.title, new.body_text);
        END;
    """)

    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS notes_vec USING vec0(
            note_id TEXT PRIMARY KEY,
            embedding FLOAT[1536]
        )
    """)

    conn.commit()
    return conn


def rebuild_index() -> int:
    """Scan all content directories and rebuild the full index."""
    conn = ensure_db()
    conn.execute("DELETE FROM notes")
    conn.execute("DELETE FROM notes_vec")
    conn.execute("INSERT INTO notes_fts(notes_fts) VALUES ('delete-all')")
    conn.commit()

    count = 0
    for dir_name in CONTENT_DIRS:
        dir_path = BASE_DIR / dir_name
        if not dir_path.exists():
            continue
        for md_file in sorted(dir_path.rglob("*.md")):
            note = parse_note(md_file)
            _upsert_note(conn, note)
            count += 1

    conn.commit()

    if is_embedding_available():
        _rebuild_embeddings(conn)

    conn.close()
    return count


def _upsert_note(conn: sqlite3.Connection, note: Note) -> None:
    """Insert or replace a note in the database."""
    conn.execute(
        """
        INSERT OR REPLACE INTO notes
        (path, note_id, title, kind, tags, created_at, updated_at,
         body_text, raw_markdown)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            note.path,
            note.note_id,
            note.title,
            note.kind,
            json.dumps(note.tags, ensure_ascii=False),
            note.created_at.isoformat() if note.created_at else None,
            note.updated_at.isoformat() if note.updated_at else None,
            note.body_text,
            note.raw_markdown,
        ),
    )


def upsert_note_index(filepath: Path) -> Note:
    """Index a single note in place without rebuilding the entire DB.

    FTS5 stays consistent via the `notes_au` trigger. Embeddings are not
    touched here — call `update_note_embedding` (typically in a background
    task) so the slow API round-trip does not block the response.
    """
    conn = ensure_db()
    note = parse_note(filepath)
    _upsert_note(conn, note)
    conn.commit()
    conn.close()
    return note


def update_note_embedding(note_id: str, title: str, body_text: str) -> None:
    """Generate and store the embedding for a single note, if a provider is set."""
    if not is_embedding_available():
        return
    text = f"{title}\n{body_text}".strip()
    if not text:
        return
    vec = generate_embedding(text)
    if vec is None:
        return
    conn = ensure_db()
    conn.execute(
        "INSERT OR REPLACE INTO notes_vec (note_id, embedding) VALUES (?, ?)",
        (note_id, vec),
    )
    conn.commit()
    conn.close()


def _rebuild_embeddings(conn: sqlite3.Connection) -> None:
    """Generate embeddings for all notes."""
    rows = conn.execute("SELECT note_id, title, body_text FROM notes").fetchall()
    success = 0
    failed = False
    for note_id, title, body_text in rows:
        text = f"{title}\n{body_text}".strip()
        if not text:
            continue
        vec = generate_embedding(text)
        if vec is not None:
            conn.execute(
                "INSERT OR REPLACE INTO notes_vec (note_id, embedding) VALUES (?, ?)",
                (note_id, vec),
            )
            success += 1
        elif not failed:
            failed = True  # Warning is printed by generate_embedding on first failure
    conn.commit()
    if success > 0:
        print(f"Generated {success} embeddings")
