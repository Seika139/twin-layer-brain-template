#!/usr/bin/env python3
"""repos.json マニフェストを操作する helper。

clone-repo.sh / update-repos.sh から呼ばれる想定。stdlib のみで書かれており、
外部依存はない。

Commands:
  add <spec> [--branch BRANCH] [--name NAME]
      エントリを追加する。同名のエントリが既にあれば spec / branch を更新する。

  list
      全エントリを一行ずつ tab 区切りで出力する: <name>\t<spec>\t<branch>
      branch 未指定のエントリでは 3 列目が空文字になる。

  orphans
      raw/repos/ に物理的に存在するがマニフェストに載っていない repo の名前を
      一行ずつ出力する。

  derive-name <spec>
      spec から repo 名を導出する shell 向けの補助コマンド。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, cast


def _brain_root() -> Path:
    env = os.environ.get("BRAIN_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[3]


def _manifest_path() -> Path:
    return _brain_root() / "repos.json"


def _repos_dir() -> Path:
    return _brain_root() / "raw" / "repos"


def _derive_name(spec: str) -> str:
    s = spec.strip()
    if s.endswith(".git"):
        s = s[: -len(".git")]
    if s.startswith("git@"):
        # git@host:owner/repo
        _, _, path = s.partition(":")
        return path.rsplit("/", 1)[-1]
    if s.startswith(("http://", "https://", "ssh://")):
        return s.rsplit("/", 1)[-1]
    # owner/repo
    return s.rsplit("/", 1)[-1]


def _load() -> dict[str, Any]:
    path = _manifest_path()
    if not path.exists():
        return {"repos": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"[error] repos.json が壊れています: {exc}\n")
        sys.exit(2)
    if not isinstance(data, dict) or not isinstance(data.get("repos"), list):
        sys.stderr.write(
            "[error] repos.json の形式が想定と異なります（{'repos': [...]} を想定）\n"
        )
        sys.exit(2)
    return data


def _save(data: dict[str, Any]) -> None:
    path = _manifest_path()
    tmp = path.with_suffix(".json.tmp")
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def cmd_add(args: argparse.Namespace) -> int:
    spec = args.spec.strip()
    name = args.name or _derive_name(spec)
    data = _load()
    entry: dict[str, str] = {"spec": spec}
    if args.branch:
        entry["branch"] = args.branch
    if args.name:
        entry["name"] = args.name
    repos: list[dict[str, Any]] = data["repos"]
    for i, existing in enumerate(repos):
        existing_name = existing.get("name") or _derive_name(existing.get("spec", ""))
        if existing_name == name:
            repos[i] = entry
            _save(data)
            print(f"[update] {name}: spec={spec} branch={args.branch or '-'}")
            return 0
    repos.append(entry)
    _save(data)
    print(f"[add] {name}: spec={spec} branch={args.branch or '-'}")
    return 0


def cmd_list(_: argparse.Namespace) -> int:
    data = _load()
    for entry in data["repos"]:
        spec = entry.get("spec", "")
        name = entry.get("name") or _derive_name(spec)
        branch = entry.get("branch", "")
        print(f"{name}\t{spec}\t{branch}")
    return 0


def cmd_orphans(_: argparse.Namespace) -> int:
    data = _load()
    tracked = {
        (entry.get("name") or _derive_name(entry.get("spec", "")))
        for entry in data["repos"]
    }
    repos_dir = _repos_dir()
    if not repos_dir.exists():
        return 0
    for child in sorted(repos_dir.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith("."):
            # .trash/ など。管理対象外として除外。
            continue
        if not (child / ".git").exists():
            continue
        if child.name not in tracked:
            print(child.name)
    return 0


def cmd_derive_name(args: argparse.Namespace) -> int:
    print(_derive_name(args.spec))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="repos.json manifest helper")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="エントリ追加 / 更新")
    p_add.add_argument("spec")
    p_add.add_argument("--branch", default=None)
    p_add.add_argument("--name", default=None)
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="全エントリを出力")
    p_list.set_defaults(func=cmd_list)

    p_orphans = sub.add_parser("orphans", help="マニフェスト外の clone を列挙")
    p_orphans.set_defaults(func=cmd_orphans)

    p_dn = sub.add_parser("derive-name", help="spec から repo 名を導出")
    p_dn.add_argument("spec")
    p_dn.set_defaults(func=cmd_derive_name)

    args = parser.parse_args(argv)
    return cast(int, args.func(args))


if __name__ == "__main__":
    sys.exit(main())
