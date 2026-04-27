from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import frontmatter
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from compiler.paths import BASE_DIR
from compiler.frontmatter import parse_note, write_note_file
from compiler.indexer import rebuild_index
from server.auth import require_token
from server.llm import summarize_page
from server.routes.notes import NoteResponse

router = APIRouter(prefix="/clip", dependencies=[Depends(require_token)])
logger = logging.getLogger(__name__)


class ClipRequest(BaseModel):
    title: str
    url: str
    canonical_url: str | None = None
    content: str | None = None
    tags: list[str] = []
    skip_llm: bool = False


class ClipResponse(NoteResponse):
    capture_mode: Literal["ai", "mechanical"]
    llm_used: bool


_TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
}


@router.post("", status_code=201)
async def clip(req: ClipRequest) -> ClipResponse:
    page_content = req.content or ""
    llm_requested = not req.skip_llm
    identity_url = req.canonical_url or req.url
    canonical_url = _canonicalize_url(identity_url)
    url_hash = _short_hash(canonical_url, length=12)
    content_hash = _short_hash(page_content, length=16)
    clipped_at = datetime.now(timezone.utc).astimezone().isoformat()
    article_dir = BASE_DIR / "raw" / "articles"
    filepath = _resolve_clip_path(article_dir, req.title, canonical_url, url_hash)
    existing = _read_existing_metadata(filepath)

    if req.skip_llm:
        summary = ""
        llm_tags: list[str] = []
    else:
        try:
            result = await summarize_page(req.title, req.url, page_content)
            summary = result.get("summary") or ""
            llm_tags = result.get("tags") or []
        except Exception as exc:
            logger.warning("LLM summary failed; saving mechanical clip: %s", exc)
            summary = ""
            llm_tags = []

    llm_used = bool(summary or llm_tags)
    capture_mode: Literal["ai", "mechanical"] = "ai" if llm_used else "mechanical"
    existing_tags = (
        existing.get("tags") if isinstance(existing.get("tags"), list) else []
    )
    all_tags = list(dict.fromkeys(existing_tags + req.tags + llm_tags + ["web-clip"]))

    body_parts = []
    if summary:
        body_parts.append(summary)
    if page_content and llm_used:
        body_parts.append(
            "\n---\n\n<details>\n<summary>Original Content</summary>\n\n"
            + page_content[:6000]
            + "\n\n</details>"
        )
    elif page_content:
        body_parts.append("## Extracted Content\n\n" + page_content[:6000])

    body = "\n\n".join(body_parts) if body_parts else None

    filepath = write_note_file(
        filepath=filepath,
        title=req.title,
        kind="raw",
        tags=all_tags,
        body=body,
        sources=list(dict.fromkeys([u for u in [req.url, req.canonical_url] if u])),
        metadata={
            "source_url": req.url,
            "canonical_url": canonical_url,
            "browser_canonical_url": req.canonical_url,
            "url_hash": url_hash,
            "content_hash": content_hash,
            "clipped_at": clipped_at,
            "capture_mode": capture_mode,
            "llm_used": llm_used,
            "llm_requested": llm_requested,
        },
        note_id=existing.get("id"),
        created_at=existing.get("created_at"),
        related=existing.get("related") or [],
        status=existing.get("status", "active"),
    )
    note = parse_note(filepath)
    rebuild_index()
    base = NoteResponse.from_note(note)
    return ClipResponse(
        **base.model_dump(),
        capture_mode=capture_mode,
        llm_used=llm_used,
    )


def _canonicalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    path = re.sub(r"/+", "/", parts.path)
    if path != "/":
        path = path.rstrip("/")

    query_items = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        key_lower = key.lower()
        if key_lower.startswith("utm_") or key_lower in _TRACKING_QUERY_KEYS:
            continue
        query_items.append((key, value))

    query = urlencode(sorted(query_items), doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def _short_hash(value: str, length: int) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def _resolve_clip_path(
    article_dir: Path,
    title: str,
    canonical_url: str,
    url_hash: str,
) -> Path:
    existing = _find_existing_clip(article_dir, canonical_url, url_hash)
    if existing is not None:
        return existing
    return article_dir / f"{_slugify_filename(title)}-{url_hash}.md"


def _find_existing_clip(
    article_dir: Path,
    canonical_url: str,
    url_hash: str,
) -> Path | None:
    if not article_dir.exists():
        return None

    for path in sorted(article_dir.glob("*.md")):
        try:
            post = frontmatter.loads(path.read_text(encoding="utf-8"))
        except OSError:
            continue

        meta = post.metadata
        if meta.get("url_hash") == url_hash:
            return path

        urls = [meta.get("source_url"), meta.get("canonical_url")]
        sources = meta.get("sources") or []
        if isinstance(sources, list):
            urls.extend(sources)

        for candidate in urls:
            if (
                isinstance(candidate, str)
                and _canonicalize_url(candidate) == canonical_url
            ):
                return path

    return None


def _read_existing_metadata(filepath: Path) -> dict[str, object]:
    if not filepath.exists():
        return {}
    try:
        return dict(frontmatter.loads(filepath.read_text(encoding="utf-8")).metadata)
    except OSError:
        return {}


def _slugify_filename(title: str, max_length: int = 96) -> str:
    slug = unicodedata.normalize("NFKC", title).strip().lower()
    slug = re.sub(r'[\\/:*?"<>|#\[\]{}()\r\n\t]+', "-", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-. ")
    if not slug:
        return "untitled"
    return slug[:max_length].strip("-. ") or "untitled"
