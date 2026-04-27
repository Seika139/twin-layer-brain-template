from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from compiler.paths import BASE_DIR
from compiler.env import load_dotenv
from compiler.key_check import KeyStatus

_BADGE = {
    "OK": "[ OK  ]",
    "RATE": "[RATE ]",
    "AUTH": "[AUTH ]",
    "NONE": "[NONE ]",
    "ERR": "[ERR  ]",
    "SKIP": "[SKIP ]",
}

_STATUS_COLORS = {
    "OK": "\033[32m",
    "RATE": "\033[33m",
    "AUTH": "\033[31m",
    "NONE": "\033[2m",
    "ERR": "\033[31m",
    "SKIP": "\033[36m",
}

_RESET = "\033[0m"


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(prog="kc", description="Knowledge Compiler CLI")
    sub = parser.add_subparsers(dest="command")

    # kc new <title>
    p_new = sub.add_parser("new", help="Create a new note")
    p_new.add_argument("title", help="Note title")
    p_new.add_argument("--kind", default="note", help="Note kind (default: note)")
    p_new.add_argument(
        "--dir",
        default="raw/notes",
        help="Target directory (default: raw/notes)",
    )
    p_new.add_argument("--tags", nargs="*", default=[], help="Tags")

    # kc index
    sub.add_parser("index", help="Rebuild the search index")

    # kc search <query>
    p_search = sub.add_parser("search", help="Search notes")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--semantic", action="store_true", help="Use semantic search")

    # kc show <id_or_path>
    p_show = sub.add_parser("show", help="Show a note")
    p_show.add_argument("id_or_path", help="Note ID or path")

    # kc suggest-related <id_or_path>
    p_related = sub.add_parser("suggest-related", help="Suggest related notes")
    p_related.add_argument("id_or_path", help="Note ID or path")

    # kc check-keys
    p_check = sub.add_parser("check-keys", help="Check availability of LLM API keys")
    p_check.add_argument(
        "--live-embedding",
        action="store_true",
        help="Probe the OpenAI Embeddings API. This sends a tiny billable request.",
    )
    p_check.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of human-readable text.",
    )
    p_check.add_argument(
        "--color",
        action="store_true",
        help="Colorize human-readable status badges.",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "new":
        _cmd_new(args)
    elif args.command == "index":
        _cmd_index()
    elif args.command == "search":
        _cmd_search(args)
    elif args.command == "show":
        _cmd_show(args)
    elif args.command == "suggest-related":
        _cmd_suggest_related(args)
    elif args.command == "check-keys":
        _cmd_check_keys(args)


def _cmd_new(args: argparse.Namespace) -> None:
    from compiler.frontmatter import create_note_file

    target_dir = BASE_DIR / args.dir
    filepath = create_note_file(
        directory=target_dir,
        title=args.title,
        kind=args.kind,
        tags=args.tags,
    )
    print(f"Created: {filepath}")


def _cmd_index() -> None:
    from compiler.indexer import rebuild_index

    count = rebuild_index()
    print(f"Indexed {count} notes")


def _cmd_search(args: argparse.Namespace) -> None:
    from compiler.embedding import is_embedding_available
    from compiler.search import search_fts, search_similar

    # FTS search
    fts_results = search_fts(args.query)

    # Semantic search (if available and requested or by default)
    from compiler.models import Note

    sem_results: list[tuple[Note, float]] = []
    if is_embedding_available():
        sem_results = search_similar(args.query, limit=5)

    if not fts_results and not sem_results:
        print("No results found.")
        return

    if fts_results:
        print("=== Keyword Search ===")
        for note in fts_results:
            print(f"  [{note.kind}] {note.title} ({note.note_id})")
            print(f"         {note.path}")

    if sem_results:
        print("\n=== Semantic Search ===")
        for sem_note, distance in sem_results:
            print(f"  [{sem_note.kind}] {sem_note.title} (distance: {distance:.4f})")
            print(f"         {sem_note.path}")


def _cmd_show(args: argparse.Namespace) -> None:
    from compiler.search import read_note

    note = read_note(args.id_or_path)
    if note is None:
        print(f"Note not found: {args.id_or_path}")
        sys.exit(1)

    print(f"ID: {note.note_id}")
    print(f"Title: {note.title}")
    print(f"Kind: {note.kind}")
    print(f"Tags: {', '.join(note.tags)}")
    print(f"Path: {note.path}")
    if note.related:
        print(f"Related: {', '.join(note.related)}")
    print("---")
    print(note.body_text)


def _cmd_check_keys(args: argparse.Namespace) -> None:
    import asyncio
    import json

    from compiler.key_check import check_all_keys, check_embedding
    from compiler.paths import INDEX_DIR

    def _skipped_embedding_status(openai_status: KeyStatus | None) -> KeyStatus:
        if openai_status is None or openai_status.status == "NONE":
            return KeyStatus(
                "openai-embed",
                "OPENAI_API_KEY",
                "NONE",
                "env var not set",
                "",
            )
        if openai_status.status in ("OK", "RATE"):
            return KeyStatus(
                "openai-embed",
                "OPENAI_API_KEY",
                "SKIP",
                "live embedding probe skipped",
                openai_status.prefix,
            )
        return KeyStatus(
            "openai-embed",
            "OPENAI_API_KEY",
            openai_status.status,
            f"OpenAI chat probe returned {openai_status.status}; live probe skipped",
            openai_status.prefix,
        )

    async def _check_statuses() -> tuple[list[KeyStatus], KeyStatus]:
        chat_task = asyncio.create_task(check_all_keys())
        if args.live_embedding:
            embedding_task = asyncio.create_task(check_embedding())
            return await chat_task, await embedding_task

        chat_statuses = await chat_task
        openai_status = next((s for s in chat_statuses if s.provider == "openai"), None)
        return chat_statuses, _skipped_embedding_status(openai_status)

    statuses, embedding_status = asyncio.run(_check_statuses())
    cache = _read_provider_cache(INDEX_DIR / "llm_provider_cache.json")
    any_live = any(s.is_usable() for s in [*statuses, embedding_status])

    if args.json:
        payload = {
            "chat_providers": [s.to_dict() for s in statuses],
            "embedding": embedding_status.to_dict(),
            "live_embedding": args.live_embedding,
            "cached_active_provider": cache,
            "any_usable": any_live,
        }
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        print(
            _format_check_keys_human(
                statuses,
                embedding_status,
                cache,
                use_color=args.color,
            )
        )

    if not any_live:
        sys.exit(1)


def _read_provider_cache(cache_file: Path) -> dict[str, Any] | None:
    import json

    if not cache_file.exists():
        return None
    try:
        cache = json.loads(cache_file.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if isinstance(cache, dict):
        return cache
    return None


def _format_check_keys_human(
    statuses: list[KeyStatus],
    embedding_status: KeyStatus,
    cache: dict[str, Any] | None,
    *,
    use_color: bool,
) -> str:
    active_chat = [s.provider for s in statuses if s.is_usable()]
    lines = [
        "API key check / APIキー確認",
        "",
        "Summary / 概要",
        f"  Chat LLM        : {_chat_summary(active_chat)}",
        f"  Semantic search : {_semantic_search_summary(embedding_status)}",
        f"  Embedding probe : {_embedding_probe_summary(embedding_status)}",
        "",
        "Chat providers",
        _format_key_status_header(),
    ]
    lines.extend(_format_key_status(s, use_color=use_color) for s in statuses)

    lines.append("")
    lines.append("Embedding")
    lines.append(_format_key_status_header())
    lines.append(_format_key_status(embedding_status, use_color=use_color))
    lines.extend(_embedding_help_lines(embedding_status))

    if cache is not None:
        lines.append("")
        lines.append(
            f"Cached active provider ({cache.get('date')}): {cache.get('provider')}"
        )

    return "\n".join(lines)


def _format_key_status(
    status: KeyStatus,
    *,
    suffix: str = "",
    use_color: bool,
) -> str:
    badge = _BADGE.get(status.status, f"[{status.status}]")
    if use_color:
        badge = _colorize(status.status, badge)
    key_prefix = status.prefix or "-"
    return (
        f"  {badge}  {status.provider:<12} "
        f"{status.env_var:<18} {key_prefix:<12} {status.detail}{suffix}"
    )


def _format_key_status_header() -> str:
    return f"  {'Status':<7}  {'Provider':<12} {'Env var':<18} {'Key':<12} Result"


def _chat_summary(active_chat: list[str]) -> str:
    if active_chat:
        return f"利用可能 ({', '.join(active_chat)})"
    return "利用可能な provider なし"


def _semantic_search_summary(status: KeyStatus) -> str:
    if status.status == "OK":
        return "利用可能 (Embedding API 検証済み)"
    if status.status == "RATE":
        return "key は有効だが rate limit の可能性あり"
    if status.status == "SKIP":
        return "設定済み。Embedding API の実生成は未確認"
    if status.status == "NONE":
        return "無効 (OPENAI_API_KEY 未設定)"
    if status.status == "AUTH":
        return "無効 (OPENAI_API_KEY 認証失敗)"
    return "無効"


def _embedding_probe_summary(status: KeyStatus) -> str:
    if status.status == "SKIP":
        return "未実行。必要時だけ mise run check-keys-live を実行"
    if status.status == "NONE":
        return "未実行。OPENAI_API_KEY 未設定"
    if status.status == "OK":
        return "成功"
    if status.status == "RATE":
        return "rate limit"
    return "失敗"


def _embedding_help_lines(status: KeyStatus) -> list[str]:
    if status.status == "SKIP":
        return [
            "        OPENAI_API_KEY は設定済みです。",
            "        今回は Embeddings API を呼んでいません。",
            "        semantic search は index/search 時に embedding 生成を試します。",
            "        endpoint まで確認する場合: mise run check-keys-live",
        ]
    if status.status == "NONE":
        return [
            "        API key がなくても keyword search は動きます。",
            "        semantic search を使う場合は OPENAI_API_KEY を設定してください。",
        ]
    if status.status == "AUTH":
        return [
            "        OPENAI_API_KEY は設定されていますが、認証に失敗しました。",
            "        .env を更新してから mise run check-keys を実行してください。",
        ]
    if status.status == "ERR":
        return [
            "        OpenAI probe に失敗しました。",
            "        ネットワークか provider status を確認してください。",
        ]
    if status.status == "RATE":
        return [
            "        key は有効そうですが、provider 側で rate limited です。",
        ]
    return []


def _colorize(status: str, value: str) -> str:
    color = _STATUS_COLORS.get(status)
    if color is None:
        return value
    return f"{color}{value}{_RESET}"


def _cmd_suggest_related(args: argparse.Namespace) -> None:
    from compiler.embedding import is_embedding_available
    from compiler.search import read_note, suggest_related

    if not is_embedding_available():
        print("Embedding is not available (OPENAI_API_KEY not set).")
        print("Set OPENAI_API_KEY to enable semantic search.")
        sys.exit(1)

    note = read_note(args.id_or_path)
    if note is None:
        print(f"Note not found: {args.id_or_path}")
        sys.exit(1)

    print(f"Related notes for: {note.title} ({note.note_id})")
    print("---")

    results = suggest_related(note.note_id)
    if not results:
        print("No related notes found.")
        return

    for related_note, distance in results:
        print(
            f"  [{related_note.kind}] {related_note.title} (distance: {distance:.4f})"
        )
        print(f"         {related_note.path}")
