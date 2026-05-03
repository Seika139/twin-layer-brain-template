#!/usr/bin/env bash

#MISE hide=true

# 色付けヘルパー関数
# 基本色（ANSI 16色）
print_red() { printf '\e[31m%s\e[0m' "$*"; }
print_green() { printf '\e[32m%s\e[0m' "$*"; }
print_yellow() { printf '\e[33m%s\e[0m' "$*"; }
print_blue() { printf '\e[34m%s\e[0m' "$*"; }
print_magenta() { printf '\e[35m%s\e[0m' "$*"; }
print_cyan() { printf '\e[36m%s\e[0m' "$*"; }
# スタイル
print_dim() { printf '\e[2m%s\e[0m' "$*"; }
print_bold() { printf '\e[1m%s\e[0m' "$*"; }
# RGB カスタムカラー（引数: R G B テキスト）
print_rgb() {
  local r=$1 g=$2 b=$3
  shift 3
  printf '\e[38;2;%d;%d;%dm%s\e[0m' "$r" "$g" "$b" "$*"
}
# よく使うカスタムカラー
print_orange() { print_rgb 250 180 100 "$*"; }
print_soft_green() { print_rgb 150 255 200 "$*"; }
print_soft_blue() { print_rgb 160 190 255 "$*"; }
print_pink() { print_rgb 255 150 200 "$*"; }

# ─── TTY / fzf 補助 ─────────────────────────────────

# stdin と stdout の両方が端末に接続されているかを判定する。
# fzf のようなインタラクティブ UI を起動してよいかの判定に使う。
is_tty() {
  [ -t 0 ] && [ -t 1 ]
}

# fzf が利用可能かを確認する。なければ案内を stderr に出して非ゼロで終了する。
require_fzf() {
  if ! command -v fzf >/dev/null 2>&1; then
    echo "fzf が見つかりません。サブコマンドを引数で指定してください。" >&2
    return 1
  fi
}

# Yes/No を fzf で選ばせる。選択されなければ非ゼロで終了（キャンセル扱い）。
# 使い方: if binary_choice "本当に実行しますか？"; then ...
binary_choice() {
  local res
  res=$(printf "Yes\nNo\n" | fzf --height 6 --border --prompt "${1:-選択}: ")
  if [ -z "$res" ]; then
    return 1
  fi
  echo "$res" | grep -iq "^yes$"
}

# ─── .env パース ────────────────────────────────────
# `source .env` を避けるのは、.env がシェル特殊文字を含んでも安全に値だけ
# 取り出すため。コメント行（`# KEY=...`）はマッチしない。前後空白と外側の
# 引用符（' / "）は剥がして返す。値が見つからない場合は空文字列（exit 0）。
# 使い方: value="$(read_env_value KEY "$ROOT_DIR/.env")"
read_env_value() {
  local key="$1" file="$2"
  [[ -f "$file" ]] || return 0
  awk -F= -v key="$key" '
    $0 ~ "^[[:space:]]*"key"[[:space:]]*=" {
      sub("^[[:space:]]*"key"[[:space:]]*=[[:space:]]*", "")
      sub(/[[:space:]]+$/, "")
      gsub(/^["'\'']|["'\'']$/, "")
      print
      exit
    }
  ' "$file"
}
