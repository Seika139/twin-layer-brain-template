from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest
import sqlite_vec

from compiler import status as status_module


def _write_schema(db_path: Path) -> sqlite3.Connection:
    """Create a minimal notes + notes_vec schema compatible with the indexer."""
    conn = sqlite3.connect(str(db_path))
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.executescript(
        """
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
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE notes_vec USING vec0(
            note_id TEXT PRIMARY KEY,
            embedding FLOAT[1536]
        )
        """
    )
    return conn


def _patch_paths(
    monkeypatch: pytest.MonkeyPatch,
    base_dir: Path,
    db_path: Path,
) -> None:
    """Point status module at a per-test base dir and DB path."""
    monkeypatch.setattr(status_module, "BASE_DIR", base_dir)
    monkeypatch.setattr(status_module, "DB_PATH", db_path)
    monkeypatch.setattr(
        status_module,
        "CONTENT_DIRS",
        (
            "raw/notes",
            "raw/articles",
            "wiki/sources",
            "wiki/entities",
            "wiki/concepts",
            "wiki/topics",
        ),
    )


def test_collect_status_returns_db_exists_false_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "missing.db"
    _patch_paths(monkeypatch, tmp_path, db_path)

    status = status_module.collect_status()

    assert status.db_exists is False
    assert status.total_notes == 0
    assert status.size_bytes == 0
    assert status.last_indexed is None


def test_collect_status_counts_notes_by_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "knowledge.db"
    conn = _write_schema(db_path)
    conn.executemany(
        "INSERT INTO notes(path, note_id, title) VALUES (?, ?, ?)",
        [
            ("raw/notes/a.md", "a", "A"),
            ("raw/notes/b.md", "b", "B"),
            ("wiki/sources/c.md", "c", "C"),
        ],
    )
    conn.commit()
    conn.close()

    _patch_paths(monkeypatch, tmp_path, db_path)
    monkeypatch.setattr(status_module, "is_embedding_available", lambda: False)

    result = status_module.collect_status()

    assert result.db_exists is True
    assert result.total_notes == 3
    assert result.notes_by_dir == {"raw/notes": 2, "wiki/sources": 1}
    assert result.embedding_available is False
    assert result.embedded_notes is None


def test_collect_status_counts_embeddings_when_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "knowledge.db"
    conn = _write_schema(db_path)
    conn.executemany(
        "INSERT INTO notes(path, note_id, title) VALUES (?, ?, ?)",
        [
            ("raw/notes/a.md", "a", "A"),
            ("raw/notes/b.md", "b", "B"),
        ],
    )
    # 1 件だけ embedding あり → coverage 1/2
    conn.execute(
        "INSERT INTO notes_vec(note_id, embedding) VALUES (?, ?)",
        ("a", b"\x00" * 1536 * 4),
    )
    conn.commit()
    conn.close()

    _patch_paths(monkeypatch, tmp_path, db_path)
    monkeypatch.setattr(status_module, "is_embedding_available", lambda: True)

    result = status_module.collect_status()

    assert result.embedding_available is True
    assert result.embedded_notes == 1
    assert result.total_notes == 2


def test_format_human_prints_missing_hint_when_db_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "missing.db"
    _patch_paths(monkeypatch, tmp_path, db_path)

    status = status_module.collect_status()
    output = status_module.format_human(status)

    assert "未生成" in output
    assert "mise run index" in output


def test_format_human_shows_embedding_note_when_key_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "knowledge.db"
    conn = _write_schema(db_path)
    conn.execute(
        "INSERT INTO notes(path, note_id, title) VALUES ('raw/notes/a.md', 'a', 'A')"
    )
    conn.commit()
    conn.close()

    _patch_paths(monkeypatch, tmp_path, db_path)
    monkeypatch.setattr(status_module, "is_embedding_available", lambda: False)

    status = status_module.collect_status()
    output = status_module.format_human(status)

    # OPENAI_API_KEY 未設定時は "未計測" を明示
    assert "未計測" in output
    assert "OPENAI_API_KEY" in output


def test_format_size_rounds_to_human_units() -> None:
    assert status_module._format_size(0) == "0 B"
    assert status_module._format_size(512) == "512 B"
    assert status_module._format_size(1024) == "1.0 KiB"
    assert status_module._format_size(1024 * 1024) == "1.0 MiB"
    assert status_module._format_size(2 * 1024 * 1024 * 1024) == "2.0 GiB"


def test_format_relative_handles_various_offsets() -> None:
    now = datetime.now(tz=timezone.utc)
    assert "秒前" in status_module._format_relative(now)
    assert "分前" in status_module._format_relative(
        datetime.fromtimestamp(now.timestamp() - 120, tz=timezone.utc)
    )
    assert "時間前" in status_module._format_relative(
        datetime.fromtimestamp(now.timestamp() - 7200, tz=timezone.utc)
    )
    assert "日前" in status_module._format_relative(
        datetime.fromtimestamp(now.timestamp() - 86400 * 3, tz=timezone.utc)
    )
