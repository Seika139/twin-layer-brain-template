from __future__ import annotations

from pathlib import Path

import frontmatter
from fastapi.testclient import TestClient

from compiler.frontmatter import parse_note
from server.app import fastapi_app
from server.routes import clip as clip_route


def _stub_indexer(monkeypatch) -> None:
    """Avoid touching the real SQLite DB during clip tests."""
    monkeypatch.setattr(clip_route, "upsert_note_index", parse_note)
    monkeypatch.setattr(clip_route, "update_note_embedding", lambda *a, **k: None)


def test_clip_requires_bearer_token(monkeypatch) -> None:
    monkeypatch.setenv("BRAIN_API_TOKEN", "secret")
    client = TestClient(fastapi_app)

    res = client.post(
        "/clip",
        json={
            "title": "Example",
            "url": "https://example.com",
            "content": "body",
        },
    )

    assert res.status_code == 401


def test_clip_uses_ai_summary_when_llm_returns_content(
    monkeypatch,
    tmp_path,
) -> None:
    async def fake_summarize_page(
        title: str,
        url: str,
        content: str,
    ) -> dict[str, object]:
        return {"summary": "AI summary", "tags": ["ai-tag"]}

    monkeypatch.setenv("BRAIN_API_TOKEN", "secret")
    monkeypatch.setattr(clip_route, "BASE_DIR", tmp_path)
    _stub_indexer(monkeypatch)
    monkeypatch.setattr(clip_route, "summarize_page", fake_summarize_page)

    client = TestClient(fastapi_app)
    res = client.post(
        "/clip",
        headers={"Authorization": "Bearer secret"},
        json={
            "title": "AI Page",
            "url": "https://example.com/ai",
            "content": "Extracted page text",
        },
    )

    assert res.status_code == 201
    payload = res.json()
    assert payload["capture_mode"] == "ai"
    assert payload["llm_used"] is True
    assert "ai-tag" in payload["tags"]
    assert "AI summary" in payload["body_text"]
    assert "Original Content" in payload["body_text"]

    post = frontmatter.loads(Path(payload["path"]).read_text(encoding="utf-8"))
    assert post.metadata["capture_mode"] == "ai"
    assert post.metadata["llm_used"] is True
    assert post.metadata["llm_requested"] is True


def test_clip_falls_back_to_mechanical_content(
    monkeypatch,
    tmp_path,
) -> None:
    async def fake_summarize_page(
        title: str,
        url: str,
        content: str,
    ) -> dict[str, object]:
        return {"summary": None, "tags": []}

    monkeypatch.setenv("BRAIN_API_TOKEN", "secret")
    monkeypatch.setattr(clip_route, "BASE_DIR", tmp_path)
    _stub_indexer(monkeypatch)
    monkeypatch.setattr(clip_route, "summarize_page", fake_summarize_page)

    client = TestClient(fastapi_app)
    res = client.post(
        "/clip",
        headers={"Authorization": "Bearer secret"},
        json={
            "title": "Fallback Page",
            "url": "https://example.com/fallback",
            "content": "Mechanically extracted text",
        },
    )

    assert res.status_code == 201
    payload = res.json()
    assert payload["capture_mode"] == "mechanical"
    assert payload["llm_used"] is False
    assert "## Extracted Content" in payload["body_text"]
    assert "Mechanically extracted text" in payload["body_text"]

    post = frontmatter.loads(Path(payload["path"]).read_text(encoding="utf-8"))
    assert post.metadata["capture_mode"] == "mechanical"
    assert post.metadata["llm_used"] is False
    assert post.metadata["llm_requested"] is True


def test_clip_falls_back_when_llm_raises(
    monkeypatch,
    tmp_path,
) -> None:
    async def fake_summarize_page(
        title: str,
        url: str,
        content: str,
    ) -> dict[str, object]:
        raise RuntimeError("openai unavailable")

    monkeypatch.setenv("BRAIN_API_TOKEN", "secret")
    monkeypatch.setattr(clip_route, "BASE_DIR", tmp_path)
    _stub_indexer(monkeypatch)
    monkeypatch.setattr(clip_route, "summarize_page", fake_summarize_page)

    client = TestClient(fastapi_app)
    res = client.post(
        "/clip",
        headers={"Authorization": "Bearer secret"},
        json={
            "title": "API Down Page",
            "url": "https://example.com/api-down",
            "content": "Mechanical fallback body",
        },
    )

    assert res.status_code == 201
    payload = res.json()
    assert payload["capture_mode"] == "mechanical"
    assert payload["llm_used"] is False
    assert "## Extracted Content" in payload["body_text"]
    assert "Mechanical fallback body" in payload["body_text"]

    post = frontmatter.loads(Path(payload["path"]).read_text(encoding="utf-8"))
    assert post.metadata["capture_mode"] == "mechanical"
    assert post.metadata["llm_used"] is False
    assert post.metadata["llm_requested"] is True


def test_clip_records_when_llm_is_skipped(
    monkeypatch,
    tmp_path,
) -> None:
    async def fake_summarize_page(
        title: str,
        url: str,
        content: str,
    ) -> dict[str, object]:
        raise AssertionError("summarize_page should not be called")

    monkeypatch.setenv("BRAIN_API_TOKEN", "secret")
    monkeypatch.setattr(clip_route, "BASE_DIR", tmp_path)
    _stub_indexer(monkeypatch)
    monkeypatch.setattr(clip_route, "summarize_page", fake_summarize_page)

    client = TestClient(fastapi_app)
    res = client.post(
        "/clip",
        headers={"Authorization": "Bearer secret"},
        json={
            "title": "Skipped LLM Page",
            "url": "https://example.com/skipped",
            "content": "Mechanical only body",
            "skip_llm": True,
        },
    )

    assert res.status_code == 201
    payload = res.json()
    assert payload["capture_mode"] == "mechanical"
    assert payload["llm_used"] is False

    post = frontmatter.loads(Path(payload["path"]).read_text(encoding="utf-8"))
    assert post.metadata["capture_mode"] == "mechanical"
    assert post.metadata["llm_used"] is False
    assert post.metadata["llm_requested"] is False


def test_clip_updates_same_url_file(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("BRAIN_API_TOKEN", "secret")
    monkeypatch.setattr(clip_route, "BASE_DIR", tmp_path)
    _stub_indexer(monkeypatch)

    client = TestClient(fastapi_app)
    first = client.post(
        "/clip",
        headers={"Authorization": "Bearer secret"},
        json={
            "title": "Same Page",
            "url": "https://example.com/articles/same?utm_source=newsletter",
            "content": "old body",
            "tags": ["manual-tag"],
            "skip_llm": True,
        },
    )
    second = client.post(
        "/clip",
        headers={"Authorization": "Bearer secret"},
        json={
            "title": "Same Page Updated",
            "url": "https://example.com/articles/same",
            "content": "new body",
            "skip_llm": True,
        },
    )

    assert first.status_code == 201
    assert second.status_code == 201

    first_payload = first.json()
    second_payload = second.json()
    assert second_payload["path"] == first_payload["path"]

    post = frontmatter.loads(Path(second_payload["path"]).read_text(encoding="utf-8"))
    assert post.metadata["id"] == first_payload["note_id"]
    assert post.metadata["title"] == "Same Page Updated"
    assert post.metadata["canonical_url"] == "https://example.com/articles/same"
    assert "manual-tag" in post.metadata["tags"]
    assert "new body" in post.content
    assert "old body" not in post.content


def test_clip_same_title_different_url_creates_different_files(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("BRAIN_API_TOKEN", "secret")
    monkeypatch.setattr(clip_route, "BASE_DIR", tmp_path)
    _stub_indexer(monkeypatch)

    client = TestClient(fastapi_app)
    first = client.post(
        "/clip",
        headers={"Authorization": "Bearer secret"},
        json={
            "title": "Overview",
            "url": "https://example.com/a",
            "content": "A body",
            "skip_llm": True,
        },
    )
    second = client.post(
        "/clip",
        headers={"Authorization": "Bearer secret"},
        json={
            "title": "Overview",
            "url": "https://example.com/b",
            "content": "B body",
            "skip_llm": True,
        },
    )

    assert first.status_code == 201
    assert second.status_code == 201

    first_payload = first.json()
    second_payload = second.json()
    assert second_payload["path"] != first_payload["path"]
    assert Path(first_payload["path"]).exists()
    assert Path(second_payload["path"]).exists()


def test_clip_uses_browser_canonical_url_as_identity(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("BRAIN_API_TOKEN", "secret")
    monkeypatch.setattr(clip_route, "BASE_DIR", tmp_path)
    _stub_indexer(monkeypatch)

    client = TestClient(fastapi_app)
    first = client.post(
        "/clip",
        headers={"Authorization": "Bearer secret"},
        json={
            "title": "Canonical Page",
            "url": "https://example.com/articles/canonical?ref=feed",
            "canonical_url": "https://example.com/articles/canonical",
            "content": "first canonical body",
            "skip_llm": True,
        },
    )
    second = client.post(
        "/clip",
        headers={"Authorization": "Bearer secret"},
        json={
            "title": "Canonical Page Updated",
            "url": "https://m.example.com/articles/canonical",
            "canonical_url": "https://example.com/articles/canonical/",
            "content": "second canonical body",
            "skip_llm": True,
        },
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["path"] == first.json()["path"]

    post = frontmatter.loads(Path(second.json()["path"]).read_text(encoding="utf-8"))
    assert post.metadata["canonical_url"] == "https://example.com/articles/canonical"
    assert (
        post.metadata["browser_canonical_url"]
        == "https://example.com/articles/canonical/"
    )
    assert post.metadata["sources"] == [
        "https://m.example.com/articles/canonical",
        "https://example.com/articles/canonical/",
    ]
    assert "second canonical body" in post.content
