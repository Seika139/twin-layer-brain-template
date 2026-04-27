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

| タスク           | 用途                                                  | 主に使う場所 |
| ---------------- | ----------------------------------------------------- | ------------ |
| `scaffold-brain` | コピー後の brain instance を空の状態に初期化する      | instance     |
| `clone-repo`     | GitHub repo を `raw/repos/` に clone する             | instance     |
| `update-repos`   | `raw/repos/` 配下の repo を `git pull --ff-only` する | instance     |
| `reset-token`    | `.env` の `BRAIN_API_TOKEN` を作成または更新する       | instance     |
| `init`           | 必要ディレクトリ作成、依存同期、初期 index 作成       | instance     |

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

GitHub repo を `raw/repos/<repo>` に clone します。`owner/repo` 形式または full URL を受け付けます。

### update-repos

```bash
mise run update-repos
```

`raw/repos/` 配下の clone 済み repo を更新し、変更あり / なし / 失敗を集計します。
変更があった repo は再 ingest の候補です。

### reset-token

```bash
mise run reset-token
```

REST API と Chrome extension で使う `BRAIN_API_TOKEN` を `.env` に作成または更新します。
`.env` がない場合は `.env.example` から作成します。既に `BRAIN_API_TOKEN=` がある場合は
新しい token に置き換え、ない場合は追記します。

このコマンドは生成した token を stdout に表示します。実行すると token は必ず新しい値に
更新されます。実行後は以下を行ってください。

- `mise run serve` が起動中なら再起動する。
- Chrome extension を使っている場合は、Settings に保存済みの token を stdout に表示された値へ更新する。

Chrome extension は token を `chrome.storage.local` に保存するため、通常の clip ごとに
毎回貼り直す必要はありません。

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

| タスク            | 用途                                                      |
| ----------------- | --------------------------------------------------------- |
| `check-keys`      | LLM provider key と embedding 設定状態を確認する          |
| `check-keys-live` | embedding の実生成 probe まで確認する（API 使用量が発生） |

### check-keys

```bash
mise run check-keys
mise run check-keys --json
mise run check-keys --color
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
mise run check-keys-live --json
```

`check-keys-live` は OpenAI Embeddings API に短い入力を送り、`text-embedding-3-small` が実際に使えるかを確認します。

## Server

| タスク            | 用途                                             | 注意        |
| ----------------- | ------------------------------------------------ | ----------- |
| `serve`           | HTTP server を foreground 起動する               | 全 OS / 開発 |
| `serve-install`   | OS に応じて常駐 service を登録する               | wrapper     |
| `serve-uninstall` | OS に応じて常駐 service 登録を削除する           | wrapper     |
| `serve-restart`   | OS に応じて常駐 service を再起動する             | wrapper     |
| `serve-status`    | OS に応じて service と health check を確認する   | wrapper     |
| `serve-logs`      | OS に応じて service log を表示する               | wrapper     |

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

`serve-status` はデフォルトで state / pid / restarts / last exit / port / `/api/health` の要約だけを表示します。`launchctl print` や `systemctl status` の生出力が必要な場合は `VERBOSE=1 mise run serve-status` で切り替えます。

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

VPS で root 管理の system service として運用する場合は、`mise` task ではなく
`deploy/setup.sh` と `deploy/brain.service` を使う想定です。
OS 別の詳しい手順は [server-management.md](server-management.md) を参照してください。

## Python / 品質確認

| タスク   | 用途                                                         |
| -------- | ------------------------------------------------------------ |
| `test`   | Python test suite を実行する                                 |
| `lint`   | 既定は Markdown lint、`--all` / `-a` で ruff と shfmt も実行 |
| `format` | 既定は Markdown fix、`--all` / `-a` で ruff と shfmt も実行  |

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
`--all` / `-a` を付けると、追加で `uv run ruff check compiler server tests` と `shfmt -d mise/tasks/*.sh mise/tasks/lib/*.sh` を実行します。
実装は [../mise/tasks/lint.sh](../mise/tasks/lint.sh) です。

未知の引数を渡した場合は usage を表示して終了します。

### format

```bash
mise run format
mise run format --all
mise run format -a
```

引数なしでは `rumdl check --fix .` と `markdownlint-cli2 --fix` だけを実行します。
`--all` / `-a` を付けると、追加で `uv run ruff format compiler server tests` と `shfmt -w mise/tasks/*.sh mise/tasks/lib/*.sh` を実行します。
実装は [../mise/tasks/format.sh](../mise/tasks/format.sh) です。
自動修正後、差分を確認してから commit してください。
