from __future__ import annotations

from pathlib import Path

import pytest

from compiler.frontmatter import (
    FrontmatterParseError,
    parse_note,
    scan_frontmatter,
    validate_frontmatter,
)

VALID_NOTE = """---
title: サンプルタイトル
type: concept
created: 2026-04-28
updated: 2026-04-28
---

body
"""

# `title:` の値がバッククォートで始まる典型的な壊れ方（YAML 予約文字）。
# 実際に `wiki/concepts/room-model-migration.md` で発生した事故を再現する。
BROKEN_BACKTICK = """---
title: `/v1/chat/*` → `/v1/rooms/*` へのルームモデル移行
type: concept
---

body
"""

BROKEN_UNQUOTED_COLON = """---
title: foo: bar
type: concept
---

body
"""


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_parse_note_succeeds_for_valid_frontmatter(tmp_path: Path) -> None:
    path = _write(tmp_path, "ok.md", VALID_NOTE)
    note = parse_note(path)
    assert note.title == "サンプルタイトル"


def test_parse_note_raises_frontmatter_parse_error_with_path(tmp_path: Path) -> None:
    path = _write(tmp_path, "broken.md", BROKEN_BACKTICK)
    with pytest.raises(FrontmatterParseError) as excinfo:
        parse_note(path)
    assert excinfo.value.path == path
    # 原因トレースバックが保持されている（`from e` イディオム）。
    assert excinfo.value.__cause__ is not None


def test_validate_frontmatter_returns_issue_for_broken_file(tmp_path: Path) -> None:
    path = _write(tmp_path, "broken.md", BROKEN_BACKTICK)
    issue = validate_frontmatter(path)
    assert issue is not None
    assert issue.path == path
    assert issue.message


def test_validate_frontmatter_returns_none_for_valid_file(tmp_path: Path) -> None:
    path = _write(tmp_path, "ok.md", VALID_NOTE)
    assert validate_frontmatter(path) is None


def test_scan_frontmatter_collects_all_issues(tmp_path: Path) -> None:
    ok = _write(tmp_path, "ok.md", VALID_NOTE)
    bad1 = _write(tmp_path, "bad1.md", BROKEN_BACKTICK)
    bad2 = _write(tmp_path, "bad2.md", BROKEN_UNQUOTED_COLON)

    issues = scan_frontmatter([ok, bad1, bad2])
    issue_paths = {i.path for i in issues}
    assert issue_paths == {bad1, bad2}
