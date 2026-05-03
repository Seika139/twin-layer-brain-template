#!/usr/bin/env bash

#MISE description="GitHub の template repo から新しい brain instance を作成する"
#MISE quiet=true

# Usage:
#   mise run copy-from-template                       # TTY: 対話で repo 名を入力
#   mise run copy-from-template -- --name=my-brain    # 明示指定
#
# Defaults (read from .env):
#   COPY_REPO_OWNER : GitHub owner (user / org)。`gh repo create` の前置と
#                     `--template` 元の owner として使う。
#   BRAINS_ROOT_DIR : ローカルで brain を並べる親ディレクトリ。
#                     ここに `git clone` する。
#
# Flags:
#   --name=<name>   作成する repo 名（owner は別。例: twin-layer-brain-foo）。
#                   未指定かつ TTY は read で対話入力、非対話は exit 2。

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

# shellcheck disable=SC1091
source "$ROOT_DIR/mise/tasks/common.sh"

# --- Load defaults from .env --------------------------------------------------
# read_env_value は common.sh で定義。
ENV_FILE="$ROOT_DIR/.env"
COPY_REPO_OWNER="$(read_env_value COPY_REPO_OWNER "$ENV_FILE")"
BRAINS_ROOT_DIR="$(read_env_value BRAINS_ROOT_DIR "$ENV_FILE")"

# --- Parse CLI: --name=<name> / --name <name> ---------------------------------
COPY_REPO_NAME=""
while [[ $# -gt 0 ]]; do
  case "$1" in
  --name=*)
    COPY_REPO_NAME="${1#--name=}"
    shift
    ;;
  --name)
    if [[ $# -lt 2 ]]; then
      echo "[copy-from-template] $1 に値がありません" >&2
      exit 2
    fi
    COPY_REPO_NAME="$2"
    shift 2
    ;;
  -h | --help)
    sed -n '6,18p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    exit 0
    ;;
  *)
    echo "[copy-from-template] unknown argument: $1" >&2
    echo "usage: mise run copy-from-template -- [--name=<name>]" >&2
    exit 2
    ;;
  esac
done

# --- Validate defaults --------------------------------------------------------
if [[ -z "$COPY_REPO_OWNER" ]]; then
  echo "[copy-from-template] COPY_REPO_OWNER が未設定です。" >&2
  echo "                     .env に COPY_REPO_OWNER=<github-owner> を追加してください。" >&2
  exit 2
fi

if [[ -z "$BRAINS_ROOT_DIR" ]]; then
  echo "[copy-from-template] BRAINS_ROOT_DIR が未設定です。" >&2
  echo "                     .env に BRAINS_ROOT_DIR=<path> を追加してください（例: ~/programs/brains）。" >&2
  exit 2
fi

# tilde 展開: `~/programs/brains` のような値を絶対パスにする。
# bash の word splitting に頼らず明示置換することで、空白を含むパスでも壊れない。
BRAINS_ROOT_DIR="${BRAINS_ROOT_DIR/#\~/$HOME}"

if [[ ! -d "$BRAINS_ROOT_DIR" ]]; then
  echo "[copy-from-template] BRAINS_ROOT_DIR が存在しません: $BRAINS_ROOT_DIR" >&2
  echo "                     先に \`mkdir -p $BRAINS_ROOT_DIR\` してください。" >&2
  exit 2
fi

# --- Resolve copy repo name: --name=<name> > stdin prompt > error -------------
if [[ -z "$COPY_REPO_NAME" ]]; then
  if [[ -t 0 ]]; then
    read -r -p "copy repo name (例: twin-layer-brain-<topic>): " COPY_REPO_NAME
  else
    echo "[copy-from-template] copy repo name が指定されていません。" >&2
    echo "                     対話実行するか、--name=<name> で明示してください。" >&2
    exit 2
  fi
fi

if [[ -z "$COPY_REPO_NAME" ]]; then
  echo "[copy-from-template] 空の repo 名は使えません。" >&2
  exit 2
fi

# GitHub の repo 名と systemd / launchd の unit 名で安全な文字集合に絞る。
if [[ ! "$COPY_REPO_NAME" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "[copy-from-template] 不正な repo 名: ${COPY_REPO_NAME}" >&2
  echo "                     使用可能な文字: A-Z a-z 0-9 . _ -" >&2
  exit 2
fi

TARGET_DIR="${BRAINS_ROOT_DIR}/${COPY_REPO_NAME}"
if [[ -e "$TARGET_DIR" ]]; then
  echo "[copy-from-template] 既に存在します: $TARGET_DIR" >&2
  echo "                     別の名前を指定するか、既存ディレクトリを退避してください。" >&2
  exit 2
fi

# --- Execute -------------------------------------------------------------------
print_blue "[create] "
echo "${COPY_REPO_OWNER}/${COPY_REPO_NAME} (private, from ${COPY_REPO_OWNER}/twin-layer-brain-template)"
gh repo create "${COPY_REPO_OWNER}/${COPY_REPO_NAME}" --private \
  --template="${COPY_REPO_OWNER}/twin-layer-brain-template"

print_blue "[clone] "
echo "git@github.com:${COPY_REPO_OWNER}/${COPY_REPO_NAME}.git -> ${TARGET_DIR}"
git -C "${BRAINS_ROOT_DIR}" clone "git@github.com:${COPY_REPO_OWNER}/${COPY_REPO_NAME}.git"

echo ""
echo "次のステップ:"
echo "  cd ${TARGET_DIR}"
echo "  mise install"
echo "  mise run init"
echo "  mise run scaffold-brain -- --name ${COPY_REPO_NAME}"
