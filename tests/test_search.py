from __future__ import annotations

import sqlite3

import pytest
import sqlite_vec

from compiler import search
from compiler.search import _normalize_fts_query


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        # Pass-through: no operators at all.
        ("foo bar", "foo bar"),
        ("", ""),
        ("   ", "   "),
        ("plain keyword", "plain keyword"),
        # FTS5 booleans are case-sensitive — lowercase variants stay searchable.
        ("foo and bar", "foo and bar"),
        ("And", "And"),
        # Operator characters: escape and wrap as a phrase.
        ("foo-bar", '"foo-bar"'),
        ("yt-dlp", '"yt-dlp"'),
        ("a+b*c", '"a+b*c"'),
        ("(group)", '"(group)"'),
        ("col:value", '"col:value"'),
        # FTS5 also rejects raw `^`, `/`, and `.` outside phrases (verified on SQLite).
        ("^foo", '"^foo"'),
        ("foo/bar", '"foo/bar"'),
        ("path/to/file", '"path/to/file"'),
        ("foo.bar", '"foo.bar"'),
        ("alpha.beta.gamma", '"alpha.beta.gamma"'),
        # Bareword operators (uppercase only): escape and wrap.
        ("foo AND bar", '"foo AND bar"'),
        ("apple OR juice", '"apple OR juice"'),
        ("a NOT b", '"a NOT b"'),
        ("apple NEAR juice", '"apple NEAR juice"'),
        ("AND", '"AND"'),
        # Mixed: operator chars + bareword operator together.
        ("foo-bar AND baz", '"foo-bar AND baz"'),
        # Variable whitespace around bareword operators is still detected.
        ("  foo  AND  bar  ", '"  foo  AND  bar  "'),
        # Balanced phrase passes through untouched (user-driven FTS5 syntax).
        ('"foo bar"', '"foo bar"'),
        ('  "foo bar"  ', '  "foo bar"  '),
        ('"foo AND bar"', '"foo AND bar"'),
        # Unbalanced quotes never satisfy the phrase guard — escape via doubling.
        ('foo"bar', '"foo""bar"'),
        ('"unclosed', '"""unclosed"'),
        ('unclosed"', '"unclosed"""'),
        ('"', '""""'),
        ('""', '""'),
        # Mixed phrase + extra operator: phrase guard rejects (count != 2),
        # crash avoidance wins over preserving boolean semantics.
        ('"foo bar" -baz', '"""foo bar"" -baz"'),
        ('yt-dlp "tutorial"', '"yt-dlp ""tutorial"""'),
    ],
)
def test_normalize_fts_query(query: str, expected: str) -> None:
    assert _normalize_fts_query(query) == expected


def _make_vec_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.executescript("""
        CREATE TABLE notes (
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
        CREATE VIRTUAL TABLE notes_vec USING vec0(
            note_id TEXT PRIMARY KEY,
            embedding FLOAT[3]
        );
    """)
    rows = [
        ("a.md", "a", "Alpha", "note", '["x"]', "Alpha body", [1.0, 0.0, 0.0]),
        ("b.md", "b", "Beta", "note", '["y"]', "Beta body", [0.0, 1.0, 0.0]),
        ("c.md", "c", "Gamma", "note", "[]", "Gamma body", [0.0, 0.0, 1.0]),
    ]
    for path, note_id, title, kind, tags, body, vec in rows:
        conn.execute(
            """
            INSERT INTO notes
            (path, note_id, title, kind, tags, body_text, raw_markdown)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (path, note_id, title, kind, tags, body, body),
        )
        conn.execute(
            "INSERT INTO notes_vec (note_id, embedding) VALUES (?, ?)",
            (note_id, sqlite_vec.serialize_float32(vec)),
        )
    return conn


def test_search_similar_uses_sqlite_vec_k_constraint(monkeypatch) -> None:
    conn = _make_vec_db()
    monkeypatch.setattr(search, "ensure_db", lambda: conn)
    monkeypatch.setattr(search, "is_embedding_available", lambda: True)
    monkeypatch.setattr(
        search,
        "generate_embedding",
        lambda query: sqlite_vec.serialize_float32([1.0, 0.0, 0.0]),
    )

    results = search.search_similar("alpha", limit=2)

    assert results[0][0].note_id == "a"
    assert {note.note_id for note, _distance in results} <= {"a", "b", "c"}
    assert len(results) == 2


def test_suggest_related_uses_sqlite_vec_k_constraint(monkeypatch) -> None:
    conn = _make_vec_db()
    monkeypatch.setattr(search, "ensure_db", lambda: conn)
    monkeypatch.setattr(search, "is_embedding_available", lambda: True)

    results = search.suggest_related("a", limit=2)

    assert {note.note_id for note, _distance in results} == {"b", "c"}
