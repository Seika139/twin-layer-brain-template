from __future__ import annotations

import argparse
import sys

from compiler.config import BASE_DIR
from compiler.env import load_dotenv


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(prog="kc", description="Knowledge Compiler CLI")
    sub = parser.add_subparsers(dest="command")

    # kc new <title>
    p_new = sub.add_parser("new", help="Create a new note")
    p_new.add_argument("title", help="Note title")
    p_new.add_argument("--kind", default="note", help="Note kind (default: note)")
    p_new.add_argument(
        "--dir", default="notes", help="Target directory (default: notes)"
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
    sub.add_parser("check-keys", help="Check availability of LLM API keys")

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
        _cmd_check_keys()


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


def _cmd_check_keys() -> None:
    import asyncio
    import json

    from compiler.config import INDEX_DIR
    from compiler.key_check import check_all_keys

    _BADGE = {
        "OK": "[ OK  ]",
        "RATE": "[RATE ]",
        "AUTH": "[AUTH ]",
        "NONE": "[NONE ]",
        "ERR": "[ERR  ]",
    }

    statuses = asyncio.run(check_all_keys())

    print("Chat LLM providers (server/llm.py):")
    for s in statuses:
        badge = _BADGE.get(s.status, f"[{s.status}]")
        print(f"  {badge}  {s.provider:<10} {s.env_var:<18}={s.prefix}  {s.detail}")

    openai_status = next((s for s in statuses if s.provider == "openai"), None)
    embedding_live = openai_status is not None and openai_status.status in (
        "OK",
        "RATE",
    )

    print()
    print("Embedding (compiler/embedding.py):")
    if openai_status is None or openai_status.status == "NONE":
        print("  [NONE ]  OPENAI_API_KEY not set -> semantic search disabled")
    elif embedding_live:
        print("  [ OK  ]  OPENAI_API_KEY usable -> semantic search enabled")
    else:
        st = openai_status.status
        print(f"  [WARN ]  OPENAI_API_KEY set but chat probe returned {st}")

    cache_file = INDEX_DIR / "llm_provider_cache.json"
    if cache_file.exists():
        try:
            cache = json.loads(cache_file.read_text())
            print()
            print(
                f"Cached active provider ({cache.get('date')}): {cache.get('provider')}"
            )
        except (json.JSONDecodeError, OSError):
            pass

    any_live = any(s.status in ("OK", "RATE") for s in statuses)
    if not any_live:
        sys.exit(1)


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
