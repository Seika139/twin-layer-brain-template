from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from compiler.config import BASE_DIR
from compiler.frontmatter import create_note_file, parse_note
from compiler.indexer import rebuild_index
from server.llm import summarize_page
from server.routes.notes import NoteResponse

router = APIRouter(prefix="/clip")


class ClipRequest(BaseModel):
    title: str
    url: str
    content: str | None = None
    tags: list[str] = []
    skip_llm: bool = False


@router.post("", status_code=201)
async def clip(req: ClipRequest) -> NoteResponse:
    page_content = req.content or ""

    if req.skip_llm:
        summary = ""
        llm_tags: list[str] = []
    else:
        result = await summarize_page(req.title, req.url, page_content)
        summary = result["summary"] or ""
        llm_tags = result["tags"] or []

    all_tags = list(dict.fromkeys(req.tags + llm_tags + ["web-clip"]))

    body_parts = []
    if summary:
        body_parts.append(summary)
    if page_content:
        body_parts.append(
            "\n---\n\n<details>\n<summary>Original Content</summary>\n\n"
            + page_content[:6000]
            + "\n\n</details>"
        )

    body = "\n\n".join(body_parts) if body_parts else None

    filepath = create_note_file(
        directory=BASE_DIR / "raw" / "clips",
        title=req.title,
        kind="raw",
        tags=all_tags,
        body=body,
        sources=[req.url],
    )
    note = parse_note(filepath)
    rebuild_index()
    return NoteResponse.from_note(note)
