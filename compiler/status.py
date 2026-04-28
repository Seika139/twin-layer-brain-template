"""Report the current state of the SQLite index.

Used by `kc status` / `mise run status`. Human-readable summary of:
  - DB file size and last modification time
  - Note counts (total and by content directory)
  - Embedding coverage, only when `OPENAI_API_KEY` is set
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import sqlite_vec

from compiler.config import CONTENT_DIRS
from compiler.embedding import is_embedding_available
from compiler.paths import BASE_DIR, DB_PATH


@dataclass(frozen=True)
class IndexStatus:
    db_path: Path
    db_exists: bool
    size_bytes: int
    last_indexed: datetime | None
    total_notes: int
    notes_by_dir: dict[str, int] = field(default_factory=dict)
    embedding_available: bool = False
    embedded_notes: int | None = None  # None なら OPENAI_API_KEY 未設定で未計測


def collect_status() -> IndexStatus:
    """Read the current index state. Never raises if the DB is missing.

    The DB file may not exist yet (fresh instance that hasn't run
    `kc index`), in which case this returns a status with `db_exists=False`
    so the CLI can print a clear hint rather than crashing.
    """
    if not DB_PATH.exists():
        return IndexStatus(
            db_path=DB_PATH,
            db_exists=False,
            size_bytes=0,
            last_indexed=None,
            total_notes=0,
        )

    stat = DB_PATH.stat()
    last_indexed = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).astimezone()
    embedding_available = is_embedding_available()

    total = 0
    by_dir: dict[str, int] = {}
    embedded: int | None = None

    conn = sqlite3.connect(str(DB_PATH))
    # notes_vec は vec0 仮想テーブルで、select にも extension の load が必要。
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    try:
        total = _count(conn, "SELECT count(*) FROM notes")
        for dir_name in CONTENT_DIRS:
            # path は repo root 相対で "raw/notes/foo.md" のように格納される。
            prefix = dir_name.rstrip("/") + "/"
            count = _count(
                conn,
                "SELECT count(*) FROM notes WHERE path LIKE ?",
                (prefix + "%",),
            )
            if count > 0:
                by_dir[dir_name] = count
        if embedding_available:
            embedded = _count(conn, "SELECT count(*) FROM notes_vec")
    finally:
        conn.close()

    return IndexStatus(
        db_path=DB_PATH,
        db_exists=True,
        size_bytes=stat.st_size,
        last_indexed=last_indexed,
        total_notes=total,
        notes_by_dir=by_dir,
        embedding_available=embedding_available,
        embedded_notes=embedded,
    )


def format_human(status: IndexStatus) -> str:
    """Format status for human display. Japanese-leaning, monospace-friendly."""
    if not status.db_exists:
        return (
            f"Index: {_relativize(status.db_path)}\n"
            "Status: 未生成 (まだ `mise run index` が実行されていません)\n"
        )

    lines = [
        f"Index: {_relativize(status.db_path)}",
        f"Size:  {_format_size(status.size_bytes)}",
    ]
    if status.last_indexed is not None:
        lines.append(
            f"Last indexed: {status.last_indexed:%Y-%m-%d %H:%M:%S %z} "
            f"({_format_relative(status.last_indexed)})"
        )
    lines.append("")
    lines.append(f"Notes: {status.total_notes} total")
    if status.notes_by_dir:
        max_name = max(len(name) for name in status.notes_by_dir)
        for name, count in status.notes_by_dir.items():
            lines.append(f"  {name:<{max_name}}  {count}")
    lines.append("")

    if status.embedding_available and status.embedded_notes is not None:
        missing = max(status.total_notes - status.embedded_notes, 0)
        lines.append(
            f"Embeddings: {status.embedded_notes} / {status.total_notes} notes"
            + (f" ({missing} missing)" if missing else "")
        )
    else:
        lines.append(
            "Embeddings: 未計測 (OPENAI_API_KEY 未設定。semantic search は無効)"
        )

    return "\n".join(lines) + "\n"


def _count(conn: sqlite3.Connection, query: str, params: tuple = ()) -> int:
    row = conn.execute(query, params).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def _relativize(path: Path) -> str:
    try:
        return str(path.relative_to(BASE_DIR))
    except ValueError:
        return str(path)


def _format_size(size: int) -> str:
    units = ("B", "KiB", "MiB", "GiB")
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GiB"


def _format_relative(dt: datetime) -> str:
    now = datetime.now(tz=dt.tzinfo)
    delta = now - dt
    seconds = int(delta.total_seconds())
    if seconds < 0:
        return "未来の時刻"
    if seconds < 60:
        return f"{seconds} 秒前"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} 分前"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} 時間前"
    days = hours // 24
    return f"{days} 日前"
