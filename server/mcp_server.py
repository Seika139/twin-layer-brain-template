from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from compiler.frontmatter import create_note_file, parse_note
from compiler.indexer import rebuild_index as _rebuild_index
from compiler.models import Note
from compiler.paths import BASE_DIR
from compiler.search import read_note as _read_note
from compiler.search import search_fts, search_similar, suggest_related

mcp = FastMCP(
    "TwinLayerBrain",
    stateless_http=False,
    json_response=False,
    streamable_http_path="/",
)


def _note_to_dict(note: Note) -> dict[str, object]:
    return {
        "note_id": note.note_id,
        "title": note.title,
        "kind": note.kind,
        "tags": note.tags,
        "path": note.path,
        "body_text": note.body_text,
    }


@mcp.tool()
def search_notes(query: str, limit: int = 20) -> str:
    """Full-text search across all notes using FTS5 trigram matching."""
    results = search_fts(query, limit=limit)
    return json.dumps([_note_to_dict(n) for n in results], ensure_ascii=False, indent=2)


@mcp.tool()
def search_similar_notes(query: str, limit: int = 10) -> str:
    """Semantic search using embedding similarity. Requires OPENAI_API_KEY."""
    results = search_similar(query, limit=limit)
    return json.dumps(
        [{"note": _note_to_dict(n), "distance": d} for n, d in results],
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def read_note(id_or_path: str) -> str:
    """Read a note by its ID or file path."""
    note = _read_note(id_or_path)
    if note is None:
        return json.dumps({"error": f"Note not found: {id_or_path}"})
    return json.dumps(_note_to_dict(note), ensure_ascii=False, indent=2)


@mcp.tool()
def suggest_related_notes(id_or_path: str, limit: int = 5) -> str:
    """Suggest related notes based on embedding similarity."""
    note = _read_note(id_or_path)
    if note is None:
        return json.dumps({"error": f"Note not found: {id_or_path}"})
    results = suggest_related(note.note_id, limit=limit)
    return json.dumps(
        [{"note": _note_to_dict(n), "distance": d} for n, d in results],
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def create_note(
    title: str,
    kind: str = "note",
    directory: str = "raw/notes",
    tags: list[str] | None = None,
) -> str:
    """Create a Markdown note. Defaults to `raw/notes/` user notes."""
    target_dir = BASE_DIR / directory
    filepath = create_note_file(directory=target_dir, title=title, kind=kind, tags=tags)
    note = parse_note(filepath)
    _rebuild_index()
    return json.dumps(_note_to_dict(note), ensure_ascii=False, indent=2)


@mcp.tool()
def append_note(id_or_path: str, content: str) -> str:
    """Append content to an existing note."""
    from pathlib import Path

    note = _read_note(id_or_path)
    if note is None:
        return json.dumps({"error": f"Note not found: {id_or_path}"})

    path = Path(note.path)
    current = path.read_text(encoding="utf-8")
    path.write_text(current.rstrip() + "\n\n" + content + "\n", encoding="utf-8")

    updated = parse_note(path)
    _rebuild_index()
    return json.dumps(_note_to_dict(updated), ensure_ascii=False, indent=2)


@mcp.tool()
def rebuild_index() -> str:
    """Rebuild the full search index from all Markdown files."""
    count = _rebuild_index()
    return json.dumps({"count": count, "message": f"Indexed {count} notes"})
