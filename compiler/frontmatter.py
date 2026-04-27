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
    metadata: dict[str, object] | None = None,
) -> Path:
    """Create a new Markdown file with frontmatter template."""
    slug = title.lower().replace(" ", "-")
    filename = f"{slug}.md"
    filepath = directory / filename

    return write_note_file(
        filepath=filepath,
        title=title,
        kind=kind,
        tags=tags,
        body=body,
        sources=sources,
        metadata=metadata,
    )


def write_note_file(
    filepath: Path,
    title: str,
    kind: str = "note",
    tags: list[str] | None = None,
    body: str | None = None,
    sources: list[str] | None = None,
    metadata: dict[str, object] | None = None,
    note_id: str | None = None,
    created_at: object | None = None,
    related: list[str] | None = None,
    status: str = "active",
) -> Path:
    """Write a Markdown note file, preserving caller-provided identity fields."""
    now = datetime.now(timezone.utc).astimezone().isoformat()
    body_text = body if body is not None else f"# {title}\n"

    content = frontmatter.Post(
        content=body_text,
        handler=frontmatter.YAMLHandler(),
        id=note_id or f"{kind}-{uuid.uuid4().hex[:8]}",
        title=title,
        kind=kind,
        tags=tags or [],
        created_at=created_at or now,
        updated_at=now,
        sources=sources or [],
        related=related or [],
        status=status,
    )
    if metadata:
        content.metadata.update(metadata)

    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(frontmatter.dumps(content) + "\n", encoding="utf-8")
    return filepath


_BUCKET_TO_KIND = {
    # wiki/ 配下 (Layer 2 所有)
    "sources": "source",
    "entities": "entity",
    "concepts": "concept",
    "topics": "topic",
    "analyses": "analysis",
    # raw/ 配下 (人間所有)
    "notes": "note",
    "articles": "article",
    "assets": "asset",
    "repos": "repo",
}


def _guess_kind(path: Path) -> str:
    """Guess the kind from the repo-relative directory.

    twin-layer-brain のパスは `raw/<bucket>/` または `wiki/<bucket>/` の形式で、
    `<bucket>` が種別を示す (raw/notes, wiki/entities 等)。
    """
    parts = path.parts
    for anchor in ("wiki", "raw"):
        if anchor in parts:
            idx = parts.index(anchor)
            if idx + 1 < len(parts):
                return _BUCKET_TO_KIND.get(parts[idx + 1], "note")
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
