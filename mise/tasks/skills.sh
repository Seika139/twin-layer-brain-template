#!/usr/bin/env bash

#MISE description=".claude/skills と .agents/skills の差分確認 / mtime が新しい方を優先した双方向同期（サブコマンド: diff, sync）"
#MISE quiet=true

# `.agents/skills/` を正本としつつ、Claude Code が参照する `.claude/skills/` と
# 内容を揃えるためのユーティリティ。従来は `.claude/skills` を `.agents/skills` への
# symlink にしていたが、macOS BSD の `cp -r` が symlink を follow して実ファイル化して
# しまい、template をコピーした instance 側で 2 tree が drift する事故が発生した。
# そのため「symlink はやめて両方実ファイル、明示的に sync する」運用に切り替える。
#
# 呼び方:
#   mise run skills                     # fzf で subcommand 選択 (TTY 必須)
#   mise run skills -- diff             # 差分を表示
#   mise run skills -- sync             # mtime が新しい方を優先して揃える
#   mise run skills -- sync --dry-run   # 適用せず予定だけ表示
#   mise run skills -- --help

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

# shellcheck disable=SC1091
source "$ROOT_DIR/mise/tasks/common.sh"

AGENTS_DIR=".agents/skills"
CLAUDE_DIR=".claude/skills"

# fzf の候補（description は preview pane に出す）。kc.sh と同じ方式。
SUBCOMMANDS=(
  "diff:.claude/skills と .agents/skills の差分を表示する"
  "sync:mtime が新しい方を優先して両者を揃える（--dry-run で予定のみ表示）"
)

show_help() {
  cat <<'EOF'
使い方:
  mise run skills                     # TTY なら fzf で subcommand を選択
  mise run skills -- diff             # 差分を表示
  mise run skills -- sync             # mtime が新しい方を優先して揃える
  mise run skills -- sync --dry-run   # 適用せず予定だけ表示
  mise run skills -- --help

サブコマンド:
  diff   .claude/skills と .agents/skills のファイル差分を表示する。
         diff -ruq の一覧 + diff -ruN の詳細差分。
  sync   両ディレクトリを同期する。同名ファイルは mtime が新しい方で上書きし、
         片方にしか無いファイルは存在する方からコピーする。
         TTY 時は fzf で Yes/No 確認、非 TTY 時は無確認で即適用する（CI 向け）。

前提:
  .agents/skills/ が skill の正本。.claude/skills/ は Claude Code 用のコピー。
  symlink ではなく両方実ファイル tree として管理する（BSD cp の罠を避けるため）。
EOF
}

# BSD (macOS: stat -f %m) と GNU (stat -c %Y) の両対応で mtime (epoch sec) を返す。
file_mtime() {
  local f="$1"
  local m
  if m=$(stat -f %m "$f" 2>/dev/null); then
    printf '%s\n' "$m"
    return 0
  fi
  stat -c %Y "$f"
}

# base ディレクトリ配下の全ファイルを base からの相対 path で列挙する。
list_relative_files() {
  local base="$1"
  if [[ -d "$base" ]]; then
    (cd "$base" && find . -type f | sed 's|^\./||')
  fi
}

cmd_diff() {
  if [[ ! -d "$AGENTS_DIR" && ! -d "$CLAUDE_DIR" ]]; then
    print_red "[error] " >&2
    print_orange "$AGENTS_DIR も $CLAUDE_DIR も存在しません。"$'\n' >&2
    return 2
  fi
  if [[ ! -d "$AGENTS_DIR" || ! -d "$CLAUDE_DIR" ]]; then
    print_orange "[warn] 片方のディレクトリしか存在しません:"$'\n' >&2
    [[ -d "$AGENTS_DIR" ]] && echo "  found:   $AGENTS_DIR" >&2 || echo "  missing: $AGENTS_DIR" >&2
    [[ -d "$CLAUDE_DIR" ]] && echo "  found:   $CLAUDE_DIR" >&2 || echo "  missing: $CLAUDE_DIR" >&2
    echo "" >&2
    echo "sync を実行すると存在する方からコピーして揃えられます。" >&2
    return 2
  fi

  print_blue "=== diff ($AGENTS_DIR vs $CLAUDE_DIR) ==="$'\n'
  echo ""
  # BSD diff は `-u` と `-q` を同時指定できない（"conflicting output format"）。
  # 一覧用途は `-rq` (再帰 + brief)、詳細用途は `-ruN` (再帰 + unified + 片側欠落も出す) に分ける。
  print_blue "ファイル一覧の差分 (diff -rq):"$'\n'
  # diff はファイルが異なると exit 1 を返すので rc を退避して判定する。
  local rc=0
  diff -rq "$AGENTS_DIR" "$CLAUDE_DIR" || rc=$?
  if ((rc == 0)); then
    print_blue "  差分はありません。"$'\n'
    return 0
  fi
  echo ""
  print_blue "詳細差分 (diff -ruN):"$'\n'
  diff -ruN "$AGENTS_DIR" "$CLAUDE_DIR" || true
}

cmd_sync() {
  local dry_run=0
  for arg in "$@"; do
    case "$arg" in
    --dry-run | -n)
      dry_run=1
      ;;
    -h | --help)
      show_help
      return 0
      ;;
    *)
      echo "未知の引数: $arg" >&2
      return 2
      ;;
    esac
  done

  mkdir -p "$AGENTS_DIR" "$CLAUDE_DIR"

  # 両ディレクトリに含まれる相対 path の和集合を作る。
  local all_files
  all_files=$(
    {
      list_relative_files "$AGENTS_DIR"
      list_relative_files "$CLAUDE_DIR"
    } | sort -u
  )

  if [[ -z "$all_files" ]]; then
    print_blue "どちらのディレクトリにもファイルがありません。sync 対象なし。"$'\n'
    return 0
  fi

  # 方向ごとの更新対象を仕分けする:
  #   to_update_claude = .agents 側が新しい / .claude 側にしか無い path → .claude を更新
  #   to_update_agents = .claude 側が新しい / .agents 側にしか無い path → .agents を更新
  local to_update_claude=() to_update_agents=()
  while IFS= read -r rel; do
    [[ -z "$rel" ]] && continue
    local agents_path="$AGENTS_DIR/$rel"
    local claude_path="$CLAUDE_DIR/$rel"
    if [[ -f "$agents_path" && -f "$claude_path" ]]; then
      local a_mt c_mt
      a_mt=$(file_mtime "$agents_path")
      c_mt=$(file_mtime "$claude_path")
      if ((a_mt > c_mt)); then
        to_update_claude+=("$rel")
      elif ((c_mt > a_mt)); then
        to_update_agents+=("$rel")
      fi
      # 同じ mtime はスキップ（内容が異なっていてもタイブレークする手段がないので人間に委ねる）。
    elif [[ -f "$agents_path" ]]; then
      to_update_claude+=("$rel")
    elif [[ -f "$claude_path" ]]; then
      to_update_agents+=("$rel")
    fi
  done <<<"$all_files"

  if [[ ${#to_update_claude[@]} -eq 0 && ${#to_update_agents[@]} -eq 0 ]]; then
    print_blue "mtime ベースでの差分はありません。同期不要です。"$'\n'
    echo ""
    echo "(内容差分があるのに mtime が揃っているケースは自動判定できないため、"
    echo " mise run skills -- diff で確認して手動で解消してください)"
    return 0
  fi

  print_blue "=== sync plan ==="$'\n'
  echo ""
  if ((${#to_update_claude[@]} > 0)); then
    print_blue ".agents/skills → .claude/skills (${#to_update_claude[@]} 件):"$'\n'
    printf '  %s\n' "${to_update_claude[@]}"
    echo ""
  fi
  if ((${#to_update_agents[@]} > 0)); then
    print_orange ".claude/skills → .agents/skills (${#to_update_agents[@]} 件):"$'\n'
    printf '  %s\n' "${to_update_agents[@]}"
    echo ""
    print_dim "(※ 通常は .agents が正本です。.claude 側が新しいのは直前に Claude Code から編集した場合など。"$'\n'
    print_dim " 意図した更新方向かを確認してから apply してください。)"$'\n'
    echo ""
  fi

  if ((dry_run)); then
    print_blue "[dry-run] 実際の同期は行いませんでした。"$'\n'
    return 0
  fi

  # TTY 時のみ fzf で確認。非 TTY (CI / hook) は無確認で適用する。
  if is_tty; then
    if ! require_fzf; then
      return 2
    fi
    if ! binary_choice "上記の同期を適用しますか？"; then
      print_blue "キャンセルしました。"$'\n'
      return 0
    fi
  fi

  # cp -p で mtime を保存しないと、次回 sync で「同期したばかりの側が新しい」と
  # 誤判定してしまう。必ず -p を付ける。
  local rel src dst dst_dir
  for rel in "${to_update_claude[@]}"; do
    src="$AGENTS_DIR/$rel"
    dst="$CLAUDE_DIR/$rel"
    dst_dir="$(dirname "$dst")"
    mkdir -p "$dst_dir"
    cp -p "$src" "$dst"
    print_blue "  [.agents→.claude] $rel"$'\n'
  done
  for rel in "${to_update_agents[@]}"; do
    src="$CLAUDE_DIR/$rel"
    dst="$AGENTS_DIR/$rel"
    dst_dir="$(dirname "$dst")"
    mkdir -p "$dst_dir"
    cp -p "$src" "$dst"
    print_orange "  [.claude→.agents] $rel"$'\n'
  done

  echo ""
  print_blue "同期完了: .agents→.claude ${#to_update_claude[@]} 件 / .claude→.agents ${#to_update_agents[@]} 件"$'\n'
}

# ─── 引数なし: TTY なら fzf で選択、非 TTY ならエラー案内 ───
if [[ $# -eq 0 ]]; then
  if ! is_tty; then
    cat >&2 <<'EOF'
[error] skills のサブコマンドが指定されていません（非 TTY 環境）。

引数を付けて呼び出してください。フラグは mise に食われるため `--` を挟みます:

  mise run skills -- diff
  mise run skills -- sync
  mise run skills -- sync --dry-run
  mise run skills -- --help
EOF
    exit 2
  fi

  if ! require_fzf; then
    exit 2
  fi

  selected=$(
    printf '%s\n' "${SUBCOMMANDS[@]}" |
      fzf --height 10 --border \
        --delimiter=: \
        --with-nth=1 \
        --prompt "skills subcommand を選択: " \
        --preview 'echo {}' \
        --preview-window=down,3,wrap
  )
  if [[ -z "$selected" ]]; then
    echo "キャンセルしました。" >&2
    exit 0
  fi
  set -- "${selected%%:*}"
fi

case "$1" in
diff)
  shift
  cmd_diff "$@"
  ;;
sync)
  shift
  cmd_sync "$@"
  ;;
-h | --help | help)
  show_help
  ;;
*)
  echo "未知の subcommand: $1" >&2
  echo "" >&2
  show_help >&2
  exit 2
  ;;
esac
