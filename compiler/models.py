from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Note:
    path: str
    note_id: str
    title: str
    kind: str
    tags: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    sources: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    status: str = "active"
    body_text: str = ""
    raw_markdown: str = ""
