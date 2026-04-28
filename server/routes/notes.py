from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from compiler.frontmatter import create_note_file, parse_note
from compiler.indexer import ensure_db, rebuild_index
from compiler.models import Note
from compiler.paths import BASE_DIR
from compiler.search import read_note, search_fts, search_similar, suggest_related
from server.auth import require_token

router = APIRouter(prefix="/notes", dependencies=[Depends(require_token)])


# --- Response models ---


class NoteResponse(BaseModel):
    path: str
    note_id: str
    title: str
    kind: str
    tags: list[str]
    status: str
    body_text: str

    @classmethod
    def from_note(cls, note: Note) -> NoteResponse:
        return cls(
            path=note.path,
            note_id=note.note_id,
            title=note.title,
            kind=note.kind,
            tags=note.tags,
            status=note.status,
            body_text=note.body_text,
        )


class ScoredNoteResponse(BaseModel):
    note: NoteResponse
    distance: float


class CreateNoteRequest(BaseModel):
    title: str
    kind: str = "raw"
    directory: str = "raw"
    tags: list[str] = []
    body: str | None = None
    sources: list[str] = []


class UpdateNoteRequest(BaseModel):
    body: str | None = None
    tags: list[str] | None = None
    status: str | None = None


# --- Endpoints ---


@router.get("/search")
async def search(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
) -> list[NoteResponse]:
    results = search_fts(q, limit=limit)
    return [NoteResponse.from_note(n) for n in results]


@router.get("/similar")
async def similar(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=100),
) -> list[ScoredNoteResponse]:
    results = search_similar(q, limit=limit)
    return [
        ScoredNoteResponse(note=NoteResponse.from_note(n), distance=d)
        for n, d in results
    ]


@router.get("/{note_id}/suggest-related")
async def get_suggest_related(
    note_id: str,
    limit: int = Query(5, ge=1, le=50),
) -> list[ScoredNoteResponse]:
    results = suggest_related(note_id, limit=limit)
    return [
        ScoredNoteResponse(note=NoteResponse.from_note(n), distance=d)
        for n, d in results
    ]


@router.get("")
async def list_notes(
    kind: str | None = None,
    tag: str | None = None,
    limit: int = Query(50, ge=1, le=500),
) -> list[NoteResponse]:
    conn = ensure_db()
    query = "SELECT path, note_id, title, kind, tags, body_text FROM notes WHERE 1=1"
    params: list[Any] = []
    if kind:
        query += " AND kind = ?"
        params.append(kind)
    if tag:
        query += " AND tags LIKE ?"
        params.append(f"%{tag}%")
    query += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [
        NoteResponse(
            path=r[0],
            note_id=r[1],
            title=r[2],
            kind=r[3],
            tags=json.loads(r[4]) if r[4] else [],
            status="active",
            body_text=r[5] or "",
        )
        for r in rows
    ]


@router.get("/{id_or_path:path}")
async def get_note(id_or_path: str) -> NoteResponse:
    note = read_note(id_or_path)
    if note is None:
        raise HTTPException(404, f"Note not found: {id_or_path}")
    return NoteResponse.from_note(note)


@router.post("", status_code=201)
async def create(req: CreateNoteRequest) -> NoteResponse:
    target_dir = BASE_DIR / req.directory
    filepath = create_note_file(
        directory=target_dir,
        title=req.title,
        kind=req.kind,
        tags=req.tags,
        body=req.body,
        sources=req.sources,
    )
    note = parse_note(filepath)
    rebuild_index()
    return NoteResponse.from_note(note)


@router.put("/{id_or_path:path}")
async def update(id_or_path: str, req: UpdateNoteRequest) -> NoteResponse:
    from pathlib import Path

    import frontmatter

    note = read_note(id_or_path)
    if note is None:
        raise HTTPException(404, f"Note not found: {id_or_path}")

    path = Path(note.path)
    post = frontmatter.loads(path.read_text(encoding="utf-8"))

    if req.body is not None:
        post.content = req.body
    if req.tags is not None:
        post.metadata["tags"] = req.tags
    if req.status is not None:
        post.metadata["status"] = req.status

    path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")
    updated = parse_note(path)
    rebuild_index()
    return NoteResponse.from_note(updated)
