from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import frontmatter

from compiler.models import Note


def parse_note(path: Path) -> Note:
    """Parse a Markdown file into a Note, handling missing frontmatter."""
    raw = path.read_text(encoding="utf-8")
    post = frontmatter.loads(raw)
    meta = post.metadata

    note_id = meta.get("id", path.stem)
    title = meta.get("title", path.stem)
    kind = meta.get("kind", _guess_kind(path))
    tags = meta.get("tags", []) or []
    created_at = _parse_datetime(meta.get("created_at"))
    updated_at = _parse_datetime(meta.get("updated_at"))
    sources = meta.get("sources", []) or []
    related = meta.get("related", []) or []
    status = meta.get("status", "active")

    return Note(
        path=str(path),
        note_id=note_id,
        title=title,
        kind=kind,
        tags=tags,
        created_at=created_at,
        updated_at=updated_at,
        sources=sources,
        related=related,
        status=status,
        body_text=post.content,
        raw_markdown=raw,
    )


def create_note_file(
    directory: Path,
    title: str,
    kind: str = "note",
    tags: list[str] | None = None,
    body: str | None = None,
    sources: list[str] | None = None,
) -> Path:
    """Create a new Markdown file with frontmatter template."""
    note_id = f"{kind}-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).astimezone().isoformat()
    slug = title.lower().replace(" ", "-")
    filename = f"{slug}.md"
    filepath = directory / filename

    body_text = body if body is not None else f"# {title}\n"

    content = frontmatter.Post(
        content=body_text,
        handler=frontmatter.YAMLHandler(),
        id=note_id,
        title=title,
        kind=kind,
        tags=tags or [],
        created_at=now,
        updated_at=now,
        sources=sources or [],
        related=[],
        status="active",
    )

    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(frontmatter.dumps(content) + "\n", encoding="utf-8")
    return filepath


def _guess_kind(path: Path) -> str:
    """Guess the kind based on directory."""
    parts = path.parts
    for part in parts:
        if part == "daily":
            return "log"
        if part == "projects":
            return "project"
        if part == "raw":
            return "raw"
        if part == "inbox":
            return "inbox"
        if part == "people":
            return "person"
    return "note"


def _parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None
