#!/usr/bin/env bash

#MISE description="kc CLI を呼び出す（引数なし + TTY 時は fzf でサブコマンド選択）"
#MISE quiet=true

# `kc` CLI (Layer 1) へのエントリポイント。引数を素通しで `uv run kc <args>` に
# 渡す。引数が無い場合の挙動は端末かどうかで分岐する:
#
#   - TTY (人間から実行): fzf でサブコマンドを選択。選択された subcommand に
#     専用の mise wrapper (例: mise run index) があれば案内して終了し、
#     無ければ passthrough 実行する。
#   - 非 TTY (スクリプト / CI / hooks): サブコマンド未指定はエラーとし、
#     `mise tasks` の参照方法を案内して終了する。
#
# 呼び方:
#   mise run kc                     # fzf 選択 (TTY 必須)
#   mise run kc -- <subcommand>...  # 任意のサブコマンド (-- は mise のフラグ食いを回避)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# shellcheck disable=SC1091
source "$ROOT_DIR/mise/tasks/common.sh"

# 既存の mise wrapper がある subcommand は fzf 選択後に案内するために持っておく。
# (subcommand -> 対応する mise タスク名)
declare -A WRAPPED=(
  ["index"]="index"
  ["validate"]="validate"
  ["status"]="status"
  ["check-keys"]="check-keys"
)

# fzf の候補として出す kc subcommand 一覧。description は preview pane に出す。
# kc CLI の実装 (compiler/cli.py) と対応。
SUBCOMMANDS=(
  "new:新しい note を作成する"
  "index:検索 index (SQLite FTS5 + vec) を再構築する"
  "validate:索引対象の Markdown frontmatter を機械的にチェックする"
  "status:index DB のサイズ / note 件数 / embedding カバレッジを表示する"
  "search:notes を検索する（キーワード / semantic）"
  "show:note を ID または path で表示する"
  "suggest-related:指定 note の関連 note を semantic search で提案する"
  "check-keys:LLM API key と embedding 設定状態を確認する"
)

run_kc() {
  exec uv run kc "$@"
}

# ─── 引数あり: そのまま passthrough ─────────────────
if [[ $# -gt 0 ]]; then
  run_kc "$@"
fi

# ─── 引数なし + 非 TTY: エラー案内 ─────────────────
if ! is_tty; then
  cat >&2 <<'EOF'
[error] kc のサブコマンドが指定されていません（非 TTY 環境）。

引数を付けて呼び出してください。フラグは mise に食われるため `--` を挟みます:

  mise run kc -- <subcommand> [args...]    # 任意の subcommand
  mise run kc -- --help                     # subcommand 一覧

wrapper があるサブコマンドは直接 mise タスクとして呼べます:

  mise run index
  mise run validate
  mise run status
  mise run check-keys

全 mise タスクの一覧:

  mise tasks
EOF
  exit 2
fi

# ─── 引数なし + TTY: fzf で subcommand を選択 ─────
if ! require_fzf; then
  exit 2
fi

selected=$(
  printf '%s\n' "${SUBCOMMANDS[@]}" |
    fzf --height 18 --border \
      --delimiter=: \
      --with-nth=1 \
      --prompt "kc subcommand を選択: " \
      --preview 'echo {}' \
      --preview-window=down,3,wrap
)

if [ -z "$selected" ]; then
  echo "キャンセルしました。" >&2
  exit 0
fi

subcommand="${selected%%:*}"

# 専用 wrapper があれば教えて終了する（ユーザーにより短い入口を覚えてもらう）。
if [[ -n "${WRAPPED[$subcommand]:-}" ]]; then
  wrapper="${WRAPPED[$subcommand]}"
  cat <<EOF
この subcommand には専用の mise wrapper があります。次から直接呼べます:

  mise run ${wrapper}

今回はこのまま実行します...
EOF
  echo ""
fi

run_kc "$subcommand"
