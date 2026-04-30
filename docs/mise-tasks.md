# mise tasks

この repo の定型作業は `mise.toml` と `mise/tasks/*.sh` に分かれています。
短い task は `mise.toml` に置き、引数処理を含む task は `mise/tasks/*.sh` の standalone task にします。
`mise run init` は `chmod +x mise/tasks/*.sh` を実行するため、script task は実行権限が付いていれば `mise` に自動認識されます。

タスク一覧:

```bash
mise tasks
```

実行:

```bash
mise run <task>
```

## Template / instance lifecycle

| タスク           | 用途                                                                 | 主に使う場所        |
| ---------------- | -------------------------------------------------------------------- | ------------------- |
| `scaffold-brain` | コピー後の brain instance を空の状態に初期化する                     | instance            |
| `clone-repo`     | GitHub repo を `raw/repos/` に clone し、`repos.json` に記録する     | instance            |
| `update-repos`   | `repos.json` に従って `raw/repos/` を同期する                        | instance            |
| `diff-template`  | template remote との差分表示 / 一括適用（instance への更新取り込み） | instance            |
| `skills`         | `.agents/skills/` と `.claude/skills/` の差分確認 / mtime ベース同期 | template / instance |
| `reset-token`    | `.env` の `BRAIN_API_TOKEN` を作成または更新する                     | instance            |
| `init`           | 必要ディレクトリ作成、依存同期、初期 index 作成                      | instance            |

### scaffold-brain

```bash
mise run scaffold-brain
```

やること:

- `raw/{notes,articles,assets}/` の inherited content を消す。
- `wiki/{sources,entities,concepts,topics,analyses}/` の inherited content を消す。
- `wiki/index.md` と `wiki/log.md` を skeleton に戻す。

template repo 自体では通常実行しません。ディレクトリ名が `twin-layer-brain-template` の場合は拒否されます。

### clone-repo

```bash
mise run clone-repo owner/repo
mise run clone-repo owner/repo main
```

GitHub repo を `raw/repos/<repo>` に clone します。`owner/repo` 形式または full URL を
受け付けます。clone 成功後に repo root の `repos.json` にエントリを追記します
（既に同名エントリがあれば spec / branch を更新）。`repos.json` は tracked なので、
commit して push すれば別 PC でも同じ repo を再現できます。

### update-repos

```bash
mise run update-repos           # 同期のみ
mise run update-repos --prune   # 孤立 repo を .trash/ に退避
```

`repos.json` を正本として `raw/repos/` 配下を同期します。

- マニフェストにあるが未 clone の repo を clone する。
- 既存 repo は `git pull --ff-only` で更新する。
- マニフェストに載っていない repo (orphan) を検出して一覧表示する。
- `--prune` を付けると orphan を `raw/repos/.trash/<name>-<timestamp>/` に `mv` で
  退避し、最終削除用の `rm` コマンドを stdout に表示する（自動では完全削除しない）。

出力例:

```text
=== update-repos ===
clone 済み: 1 (foam)
更新あり:   0
更新なし:   2
失敗:       0
孤立 repo:  1 (legacy-repo)
```

変更があった repo は再 ingest の候補です。

### diff-template

```bash
mise run diff-template                 # 変更ファイル一覧 (既定)
mise run diff-template --diff          # 差分内容まで表示
mise run diff-template --all           # instance 固有 path も含めて比較 (--apply と排他)
mise run diff-template --apply         # 差分確認 → プロンプト → 一括上書き
mise run diff-template --apply --yes   # 確認スキップで一括上書き (CI 向け)
```

`template` remote と自 instance の差分を表示、または一括適用します。

- `--list` (既定) / `--diff` / `--all` は **見るだけ** (既存挙動)。
- `--apply` は **差分の中身を全件表示 → 確認プロンプト → `git checkout template/main -- <path>` を一括実行** します。独自変更があれば目視で気付けるよう、差分表示の後に確認を取ります。`--yes` / `-y` で確認をスキップできます。
- `--apply --all` は instance 固有 path (`raw/`, `wiki/`, `repos.json`, `.env`) を破壊する恐れがあるため**排他**です。

適用時の挙動:

- **M** (両方にあり内容が異なる): template の内容で上書き
- **D** (template のみ存在): template から復元
- **A** (instance のみ存在): スキップ (instance 固有の拡張として保護)

前提として remote が登録されている必要があります:

```bash
git remote add template git@github.com:<owner>/twin-layer-brain-template.git
```

既定では `raw/`, `wiki/sources|entities|concepts|topics|analyses/`, `wiki/index.md`,
`wiki/log.md`, `index/`, `repos.json`, `.env` を比較対象から除外します。これらは
instance ごとに内容が異なるため、template とは比較しないのが既定です。運用手順は
[template-operation.md](template-operation.md) の「変更を instance に反映する」節を
参照してください。

### skills

```bash
mise run skills                     # TTY なら fzf で subcommand を選択
mise run skills -- diff             # .agents/skills と .claude/skills の差分を表示
mise run skills -- sync             # mtime が新しい方を優先して揃える
mise run skills -- sync --dry-run   # 適用せず予定だけ表示
```

`.agents/skills/` が skill の正本、`.claude/skills/` は Claude Code が参照する
実ファイルコピー (symlink ではない) で、両 tree を同じ内容に保つためのユーティリティです。
symlink をやめた経緯は [template-operation.md](template-operation.md) の
Infrastructure 節を参照してください。

- `diff`: `diff -rq` で一覧、`diff -ruN` で詳細差分を表示します。
- `sync`: 同名ファイルは mtime が新しい方で上書き、片側にしか無いファイルはその側からコピーします。
  TTY 時は fzf で Yes/No 確認、非 TTY 時 (CI / hook) は無確認で即適用します。
  mtime が一致しているのに内容が異なるケースは自動判定できないため、`diff` で確認して
  手で解消してください。

`mise run diff-template --apply` は両 tree を一括で上書きするため、template の更新を
instance に取り込んだ直後に追加の `skills sync` は必要ありません。

### reset-token

```bash
mise run reset-token
```

REST API と Chrome extension で使う `BRAIN_API_TOKEN` を `.env` に作成または更新します。
`.env` がない場合は `.env.example` から作成します。
既に `BRAIN_API_TOKEN=` がある場合は新しい token に置き換え、ない場合は追記します。

このコマンドは生成した token を stdout に表示します。実行すると token は必ず新しい値に更新されます。実行後は以下を行ってください。

- `mise run serve` が起動中なら再起動する。
- Chrome extension を使っている場合は、Settings に保存済みの token を stdout に表示された値へ更新する。

Chrome extension は token を `chrome.storage.local` に保存するため、通常の clip ごとに毎回貼り直す必要はありません。

### init

```bash
mise run init
```

やること:

- `raw/`, `wiki/`, `index/` の必要ディレクトリを作る。
- `mise/tasks/*.sh` に実行権限を付ける。
- `pnpm install`
- `uv sync`
- `uv run kc index`

## Layer 1

| タスク            | 用途                                                            |
| ----------------- | --------------------------------------------------------------- |
| `index`           | 検索 index (SQLite FTS5 + vec) を再構築する                     |
| `validate`        | 索引対象の Markdown frontmatter を機械的にチェックする          |
| `status`          | index DB のサイズ / note 件数 / embedding カバレッジを表示する  |
| `check-keys`      | LLM provider key と embedding 設定状態を確認する                |
| `check-keys-live` | embedding の実生成 probe まで確認する（API 使用量が発生）       |
| `kc`              | `kc` CLI を呼び出す。引数なし + TTY なら fzf で subcommand 選択 |

`compiler/` の `kc` CLI には他にも `new` / `search` / `show` / `suggest-related` といった subcommand がありますが、
**人間が直接叩く機会ほぼない**（LLM agent や server が内部で呼ぶ用途が主）ため、個別の mise wrapper は用意していません。
手動で叩く場合は `mise run kc` の fzf 選択か、`--` で passthrough します:

```bash
mise run kc                         # fzf で subcommand を選択 (TTY 必須)
mise run kc -- search "Docker"      # passthrough で任意 subcommand を実行
mise run kc -- new "title" --kind topic  # kc CLI のフラグはそのまま渡せる
```

`mise run check-keys -- --json` のように mise 経由で wrapper task にフラグを渡したい場合も `--` を挟みます（`--json` のような dash-flag は mise 自身が食ってしまうため）。
位置引数は `--` なしで素通しできます。

非 TTY 環境（CI / hooks / スクリプト内）で `mise run kc` を引数なしで呼ぶと、fzf は起動せず、エラーメッセージと `mise tasks` の案内を出して終了します。

### kc

```bash
mise run kc                              # fzf 選択 (TTY)
mise run kc -- <subcommand> [args...]    # passthrough
```

実装は [../mise/tasks/kc.sh](../mise/tasks/kc.sh) です。

- 引数あり: そのまま `uv run kc <args>` に渡します。
- 引数なし + TTY: fzf で `new` / `index` / `validate` / `status` / `search` / `show` / `suggest-related` / `check-keys` から選択します。
  - `index` / `validate` / `status` / `check-keys` を選んだ場合は、専用の mise wrapper が存在する旨を案内してから実行します。
- 引数なし + 非 TTY: `mise tasks` を参照するよう案内してエラー終了します。

### status

```bash
mise run status
```

`index/knowledge.db` の現状サマリを出力します。

- DB ファイルのサイズと最終更新時刻（最後に `mise run index` を回した時刻）
- note 件数（全体 + 索引対象ディレクトリ別）
- embedding カバレッジ（`OPENAI_API_KEY` 設定時のみ計測）

DB がまだ生成されていない場合 (`mise run index` を 1 度も実行していない instance) は、そのことを明示して案内します。

複数 brain instance を横断して「どれが一番大きい」「どれが古い」を手早く確認したい時に便利です。

### check-keys

```bash
mise run check-keys
mise run check-keys -- --json
mise run check-keys -- --color
```

`.env` / 環境変数の `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY` を確認します。
FTS 検索は key なしで動きます。semantic search は `OPENAI_API_KEY` が必要です。
出力は chat LLM provider の疎通確認と embedding の設定確認に分かれます。
通常の `check-keys` は有料になり得る Embeddings API への実リクエストを投げません。
`--json` は機械処理用の JSON を stdout に出します。`--color` は人間向け表示の badge に色を付けます。
`--json` と併用した場合、JSON には色を付けません。

embedding の実生成まで切り分けたい時だけ、次を実行します。

```bash
mise run check-keys-live
mise run check-keys-live -- --json
```

`check-keys-live` は OpenAI Embeddings API に短い入力を送り、`text-embedding-3-small` が実際に使えるかを確認します。

## Server

| タスク            | 用途                                           | 注意         |
| ----------------- | ---------------------------------------------- | ------------ |
| `serve`           | HTTP server を foreground 起動する             | 全 OS / 開発 |
| `serve-install`   | OS に応じて常駐 service を登録する             | wrapper      |
| `serve-uninstall` | OS に応じて常駐 service 登録を削除する         | wrapper      |
| `serve-restart`   | OS に応じて常駐 service を再起動する           | wrapper      |
| `serve-status`    | OS に応じて service と health check を確認する | wrapper      |
| `serve-logs`      | OS に応じて service log を表示する             | wrapper      |

### serve

```bash
mise run serve
```

`uv run python -m server.run` を実行します。`BRAIN_HOST` と `BRAIN_PORT` は `.env` または環境変数から読みます。既定は `127.0.0.1:15200` です。
HTTP API の詳細は [http-api.md](http-api.md)、MCP の詳細は [mcp.md](mcp.md) を参照してください。

### serve-install / serve-uninstall / serve-restart / serve-status / serve-logs

OS を自動判定して、macOS では launchd、Linux では systemd --user を使います。
通常は wrapper task だけを使い、`serve-launchd-*` / `serve-systemd-*` は直接実行しません。

```bash
mise run serve-install
mise run serve-restart
mise run serve-status
mise run serve-logs
mise run serve-uninstall
```

`serve-status` はデフォルトで state / pid / restarts / last exit / port / `/api/health` の要約だけを表示します。`launchctl print` や `systemctl status` の生出力が必要な場合は `mise run serve-status -v` (または `--verbose`) で切り替えます。

明示的に OS 別 task を呼ぶこともできます。

macOS launchd:

```bash
mise run serve-launchd-install
mise run serve-launchd-restart
mise run serve-launchd-status
mise run serve-launchd-logs
mise run serve-launchd-uninstall
```

Linux systemd --user:

```bash
mise run serve-systemd-install
mise run serve-systemd-restart
mise run serve-systemd-status
mise run serve-systemd-logs
mise run serve-systemd-uninstall
```

Linux / WSL で `systemd --user` に接続できない場合は、systemd が有効ではありません。
WSL では `/etc/wsl.conf` に以下を設定して WSL を再起動してください。

```ini
[boot]
systemd=true
```

VPS で root 管理の system service として運用する場合は、`mise` task ではなく `deploy/setup.sh` と `deploy/brain.service` を使う想定です。
OS 別の詳しい手順は [server-management.md](server-management.md) を参照してください。

## Python / 品質確認

| タスク   | 用途                                                                |
| -------- | ------------------------------------------------------------------- |
| `test`   | Python test suite を実行する                                        |
| `lint`   | 既定は Markdown lint、`--all` / `-a` で ruff / shfmt / taplo も実行 |
| `format` | 既定は Markdown fix、`--all` / `-a` で ruff / shfmt / taplo も実行  |

### test

```bash
mise run test
```

`uv run pytest` を実行します。

### lint

```bash
mise run lint
mise run lint --all
mise run lint -a
```

引数なしでは `rumdl check .` と `markdownlint-cli2` だけを実行します。
`--all` / `-a` を付けると、追加で `uv run ruff check compiler server tests mise/tasks/lib`、`shfmt -d mise/tasks/*.sh mise/tasks/lib/*.sh`、`taplo fmt --check --diff` を実行します。
`taplo` は repo 内の `*.toml`（`pyproject.toml` / `mise.toml` / `.rumdl.toml` など）を対象に、整形済みでなければ diff を出して失敗します。
実装は [../mise/tasks/lint.sh](../mise/tasks/lint.sh) です。

未知の引数を渡した場合は usage を表示して終了します。

### format

```bash
mise run format
mise run format --all
mise run format -a
```

引数なしでは `rumdl check --fix .` と `markdownlint-cli2 --fix` だけを実行します。
`--all` / `-a` を付けると、追加で `uv run ruff format compiler server tests mise/tasks/lib`、`uv run ruff check --fix compiler server tests mise/tasks/lib`、`shfmt -w mise/tasks/*.sh mise/tasks/lib/*.sh`、`taplo fmt` を実行します。
`taplo fmt` は repo 内の `*.toml` を taplo 既定スタイルで上書き整形します（`reorder_keys` は無効なのでキー順は保持）。
実装は [../mise/tasks/format.sh](../mise/tasks/format.sh) です。
自動修正後、差分を確認してから commit してください。
