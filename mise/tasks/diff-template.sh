#!/usr/bin/env bash

#MISE description="template remote と自 instance の差分を表示 / 適用する（--list: 一覧、--diff: 中身、--apply: 上書き適用、--all: instance 固有も含める）"
#MISE quiet=true

# template repo の更新を、コピー先の brain instance に取り込みたい時に使うタスク。
# template/main を remote から fetch して、いま HEAD と何が違うかを可視化し、
# 必要なら `git checkout template/main -- <path>` を一括で実行する。
#
# 使い方:
#   mise run diff-template                 # 変更ファイル一覧 (既定)
#   mise run diff-template --list          # 同上
#   mise run diff-template --diff          # 差分の中身まで表示
#   mise run diff-template --all           # instance 固有 path も含めて比較
#   mise run diff-template --apply         # 差分を表示した上で確認プロンプト → 一括上書き
#   mise run diff-template --apply --yes   # 確認プロンプトをスキップして一括上書き
#
# 前提: `template` という remote が追加されていること。
#   git remote add template git@github.com:<owner>/twin-layer-brain-template.git

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

# shellcheck disable=SC1091
source "$ROOT_DIR/mise/tasks/common.sh"

REMOTE_NAME="template"
REMOTE_BRANCH="main"

MODE="list"
INCLUDE_INSTANCE=0
SKIP_CONFIRM=0

for arg in "$@"; do
  case "$arg" in
  --list)
    MODE="list"
    ;;
  --diff)
    MODE="diff"
    ;;
  --apply)
    MODE="apply"
    ;;
  --all)
    INCLUDE_INSTANCE=1
    ;;
  --yes | -y)
    SKIP_CONFIRM=1
    ;;
  -h | --help)
    cat <<'EOF'
使い方: mise run diff-template [--list|--diff|--apply] [--all] [--yes|-y]

template remote と自 instance の差分を表示 / 適用します。

モード:
  --list (既定)  変更のあったファイル一覧だけを表示
  --diff         ファイルごとの差分内容まで表示
  --apply        差分を表示した上で、確認を取って一括上書きする

オプション:
  --all          instance 固有 path (raw/ wiki/ index/ repos.json など) も含める(--apply とは排他。instance の知識を破壊しないため)
  --yes, -y      --apply 時の確認プロンプトをスキップする (CI 向け)

前提:
  git remote add template git@github.com:<owner>/twin-layer-brain-template.git

適用時の挙動:
  M (両方に存在し内容が異なる): template の内容で上書き
  D (template のみに存在):      template から復元
  A (instance のみに存在):      スキップ (instance 固有の拡張として保護)
EOF
    exit 0
    ;;
  *)
    echo "未知の引数: $arg" >&2
    echo "使い方: mise run diff-template [--list|--diff|--apply] [--all] [--yes|-y]" >&2
    exit 2
    ;;
  esac
done

# --apply と --all の排他チェック。
# --all は raw/ wiki/ repos.json など instance の知識ファイルを含んでしまうため、
# --apply と組み合わせると instance のデータを破壊する恐れがある。
if [[ "$MODE" == "apply" && "$INCLUDE_INSTANCE" -eq 1 ]]; then
  print_red "[error] " >&2
  print_orange "--apply と --all は同時に指定できません。" >&2
  cat >&2 <<'EOF'

--all は raw/ / wiki/ / repos.json / .env など instance 固有の知識データを差分対象に含めるため、
--apply と組み合わせると instance のデータを破壊する恐れがあります。

instance 固有 path を含めて確認したい場合は --list / --diff のみで使ってください:

  mise run diff-template --list --all
  mise run diff-template --diff --all
EOF
  exit 2
fi

# この repo が git 管理下にあるか。
# `cp -r` + `rm -rf .git` だけで `git init` を忘れているケースを先に弾く。
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  print_red "[error] " >&2
  print_orange "このディレクトリは git 管理されていません。" >&2
  cat >&2 <<'EOF'

diff-template は git の fetch / diff / checkout を使うため、instance が git 管理下である必要があります。

  git init
  git add -A
  git commit -m "ブレインの初期スコープを設定"

詳しくは docs/instance-setup.md の「初回 commit」節を参照してください。
EOF
  exit 2
fi

# 初回 commit が打たれているか。
# git init 直後で HEAD が存在しない状態で diff を叩くと英語の raw エラーが出るので先に弾く。
if ! git rev-parse --verify HEAD >/dev/null 2>&1; then
  print_red "[error] " >&2
  print_orange "この repo にはまだ commit がありません。" >&2
  cat >&2 <<'EOF'

diff-template は HEAD と template/main の差分を見るため、初回 commit が必要です。

  git add -A
  git commit -m "ブレインの初期スコープを設定"

詳しくは docs/instance-setup.md の「初回 commit」節を参照してください。
EOF
  exit 2
fi

# template remote が登録されていなければ案内して終了する。
if ! git remote get-url "$REMOTE_NAME" >/dev/null 2>&1; then
  print_red "[error] " >&2
  print_orange "remote $REMOTE_NAME が登録されていません。" >&2
  cat >&2 <<EOF

template repo を remote として追加してから再実行してください。例:

  git remote add $REMOTE_NAME git@github.com:<owner>/twin-layer-brain-template.git

詳しくは docs/instance-setup.md の「template からの更新を取り込む準備」節を参照してください。
EOF
  exit 2
fi

print_blue "[fetch] "
echo "$REMOTE_NAME/$REMOTE_BRANCH を取得中..."
if ! git fetch --quiet "$REMOTE_NAME" "$REMOTE_BRANCH"; then
  print_red "[error] " >&2
  print_orange "$REMOTE_NAME/$REMOTE_BRANCH の fetch に失敗しました" >&2
  exit 2
fi

BASE_REF="$REMOTE_NAME/$REMOTE_BRANCH"
HEAD_REF="HEAD"

# instance 固有 path (既定では除外)。
# --all を付けると比較対象に含める。
INSTANCE_PATHSPEC=(
  ':(exclude)raw/**'
  ':(exclude)wiki/sources/**'
  ':(exclude)wiki/entities/**'
  ':(exclude)wiki/concepts/**'
  ':(exclude)wiki/topics/**'
  ':(exclude)wiki/analyses/**'
  ':(exclude)wiki/index.md'
  ':(exclude)wiki/log.md'
  ':(exclude)index/**'
  ':(exclude)repos.json'
  ':(exclude).env'
  ':(exclude)pyproject.toml'
  ':(exclude)uv.lock'
  ':(exclude)AGENTS.md'
  ':(exclude)CLAUDE.md'
  ':(exclude)README.md'
)

PATHSPEC=()
if [[ "$INCLUDE_INSTANCE" -eq 0 ]]; then
  PATHSPEC=("${INSTANCE_PATHSPEC[@]}")
fi

echo ""
print_blue "=== diff-template ($BASE_REF..$HEAD_REF) ==="$'\n'
if [[ "$INCLUDE_INSTANCE" -eq 0 ]]; then
  echo "(instance 固有 path は除外。--all で含める)"
fi
echo ""

# 変更ファイルを `A`, `M`, `D`, `R...` 別に集計する共通関数。
# git diff BASE..HEAD の方向に注意:
#   A = HEAD (instance) で追加 → instance にのみ存在
#   M = 両方に存在、内容が異なる
#   D = HEAD (instance) で削除 → template にのみ存在 (= apply で復元対象)
collect_changed_files() {
  git diff --name-status "$BASE_REF".."$HEAD_REF" -- "${PATHSPEC[@]}" || true
}

print_list() {
  local changed="$1"
  local added modified deleted renamed
  added=$(echo "$changed" | awk '$1=="A"{print $2}')
  modified=$(echo "$changed" | awk '$1=="M"{print $2}')
  deleted=$(echo "$changed" | awk '$1=="D"{print $2}')
  renamed=$(echo "$changed" | awk '$1 ~ /^R/{print $2" -> "$3}')

  if [[ -n "$added" ]]; then
    print_blue "追加 (instance のみ存在 / 適用時は保護されスキップ):"$'\n'
    echo "$added" | sed 's/^/  /'
    echo ""
  fi
  if [[ -n "$modified" ]]; then
    print_blue "変更 (両方にあり内容が異なる / 適用時は template で上書き):"$'\n'
    echo "$modified" | sed 's/^/  /'
    echo ""
  fi
  if [[ -n "$deleted" ]]; then
    print_blue "削除 (template のみ存在 = instance で削除済み / 適用時は template から復元):"$'\n'
    echo "$deleted" | sed 's/^/  /'
    echo ""
  fi
  if [[ -n "$renamed" ]]; then
    print_blue "リネーム:"$'\n'
    echo "$renamed" | sed 's/^/  /'
    echo ""
  fi
}

case "$MODE" in
list)
  CHANGED_FILES="$(collect_changed_files)"
  if [[ -z "$CHANGED_FILES" ]]; then
    echo "差分はありません。"
    exit 0
  fi
  print_list "$CHANGED_FILES"

  print_blue "次のステップ:"$'\n'
  cat <<EOF
  mise run diff-template --diff      # 差分の中身を確認する
  mise run diff-template --apply     # 確認を取って一括上書きする
  git checkout $BASE_REF -- <path>   # 個別に template 側の内容で上書きする
EOF
  ;;
diff)
  git --no-pager diff "$BASE_REF".."$HEAD_REF" -- "${PATHSPEC[@]}"
  ;;
apply)
  CHANGED_FILES="$(collect_changed_files)"
  if [[ -z "$CHANGED_FILES" ]]; then
    print_blue "差分はありません。適用する変更はありません。"$'\n'
    exit 0
  fi

  # 適用対象 (M + D)、保護対象 (A)、手動対象 (R) を分離する。
  # R は rename 検出ヒューリスティックで出るため、どちらの側が rename したかを
  # 機械的に判別できない（template が改名したのか instance が改名したのか不明）。
  # 自動 apply は事故源になりうるので一覧で警告し、人間に判断を委ねる。
  to_overwrite=()
  to_skip_rename=()
  while IFS=$'\t' read -r status path rest; do
    case "$status" in
    M | D) to_overwrite+=("$path") ;;
    R*) to_skip_rename+=("$path"$'\t'"$rest") ;;
    esac
  done <<<"$CHANGED_FILES"

  # 一覧を表示して全体感を見せる。
  print_list "$CHANGED_FILES"

  if [[ ${#to_overwrite[@]} -eq 0 ]]; then
    print_blue "適用対象の変更 (M / D) はありません。A (instance のみ存在) は保護されます。"$'\n'
    if [[ ${#to_skip_rename[@]} -gt 0 ]]; then
      print_orange "rename は自動 apply 対象外です。必要に応じて手動で取り込んでください:"$'\n'
      for entry in "${to_skip_rename[@]}"; do
        IFS=$'\t' read -r tmpl_path inst_path <<<"$entry"
        echo "  $tmpl_path -> $inst_path"
        echo "    git rm -- '$inst_path'"
        echo "    git checkout $BASE_REF -- '$tmpl_path'"
      done
    fi
    exit 0
  fi

  # 上書き対象 path に未コミットの変更があると `git checkout` で静かに失われる。
  # working tree の編集は reflog に残らず復旧手段が無いため、apply 前にブロックする。
  dirty=()
  for path in "${to_overwrite[@]}"; do
    if ! git diff --quiet -- "$path" 2>/dev/null ||
      ! git diff --cached --quiet -- "$path" 2>/dev/null; then
      dirty+=("$path")
    fi
  done

  if [[ ${#dirty[@]} -gt 0 ]]; then
    print_red "[error] " >&2
    print_orange "上書き対象に未コミットの変更があります。失われる前に中断します:"$'\n' >&2
    for path in "${dirty[@]}"; do
      echo "  $path" >&2
    done
    cat >&2 <<'EOF'

未コミットの working tree 編集は git checkout -- <path> で消えると reflog では復旧できません。
事前に対処してから再実行してください:

  git stash push -- <path>...     # 退避してから apply、後で git stash pop
  git add <path> && git commit    # コミット済みにすれば reflog で復旧可能
  git checkout -- <path>          # WIP を捨てる (要確認)

それから再度 mise run diff-template --apply を実行してください。
EOF
    exit 2
  fi

  # 差分の中身を全部見せる (--yes の時は省略)。ユーザーが独自変更に気付く導線。
  if [[ "$SKIP_CONFIRM" -eq 0 ]]; then
    echo "--- 以下の差分を template の内容で上書きします ---"
    echo ""
    git --no-pager diff "$BASE_REF".."$HEAD_REF" -- "${to_overwrite[@]}"
    echo ""
    print_blue "コミット済みの独自編集は git reflog で復旧可能ですが、未コミットの WIP は復旧できません。"$'\n'
    echo ""

    if ! is_tty; then
      print_red "[error] " >&2
      print_orange "非 TTY 環境では確認プロンプトを表示できません。"$'\n' >&2
      cat >&2 <<'EOF'
--yes / -y を付けて明示的に確認をスキップするか、対話 shell から実行してください。
EOF
      exit 2
    fi

    if ! require_fzf; then
      exit 2
    fi

    if ! binary_choice "これらを適用しますか？"; then
      print_blue "キャンセルしました。"$'\n'
      exit 0
    fi
  fi

  # 各 path を template の内容で上書きする。
  # git checkout <ref> -- <path> は存在しないファイルも復元するため、
  # M (変更) と D (削除) を同じ操作で処理できる。
  failed=()
  for path in "${to_overwrite[@]}"; do
    if git checkout "$BASE_REF" -- "$path" 2>/dev/null; then
      print_blue "  [適用] $path"$'\n'
    else
      print_red "  [失敗] $path"$'\n'
      failed+=("$path")
    fi
  done

  echo ""
  if [[ ${#failed[@]} -gt 0 ]]; then
    print_red "[warn] ${#failed[@]} 件の適用に失敗しました。手動で確認してください。"$'\n'
  else
    print_blue "${#to_overwrite[@]} 件を適用しました。"$'\n'
  fi

  if [[ ${#to_skip_rename[@]} -gt 0 ]]; then
    echo ""
    print_orange "[skip] rename ${#to_skip_rename[@]} 件は自動 apply 対象外です。必要なら以下を手動で実行してください:"$'\n'
    for entry in "${to_skip_rename[@]}"; do
      IFS=$'\t' read -r tmpl_path inst_path <<<"$entry"
      echo "  $tmpl_path -> $inst_path"
      echo "    git rm -- '$inst_path'"
      echo "    git checkout $BASE_REF -- '$tmpl_path'"
    done
  fi

  cat <<'EOF'

次のステップ:
  mise run test
  mise run lint --all
  git add -A && git commit -m "template の更新を取り込み"
EOF
  ;;
esac
