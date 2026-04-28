# twin-layer-brain-template

`twin-layer-brain-template` は、作業領域やプロジェクトごとにコピーして使う個人用 Second Brain テンプレートです。
1 つのコピーを 1 つのトピックに割り当て、`raw/` と `wiki/` の Markdown を正本として育てます。

> **Scope of this brain:** <ここにこのブレインが扱う範囲を 1 行で書き換える>
>
> One brain = one topic. 別の作業領域やプロジェクトは、別コピーとして運用します。

この repo には 2 つの役割があります。

- **template repo**: コピー元。スキーマ、skill、ドキュメント、検索/API実装を保守する場所。
- **brain instance**: template を PC 上の作業領域ごとにコピーしたもの。実際の知識を保存し、 `ingest` / `query` / `sublime` / `dive` / `lint` を運用する場所。

## 何を提供するか

| 層      | 実装                         | 主な用途                                  |
| ------- | ---------------------------- | ----------------------------------------- |
| Layer 1 | SQLite FTS5 + `sqlite-vec`   | 速い候補検索、CLI / REST / MCP からの参照 |
| Layer 2 | LLM が保守する Markdown Wiki | 知識の統合、解釈、長期的な compound       |

正本は常に Markdown です。SQLite の `index/knowledge.db` は `raw/` と `wiki/` から作る
派生物で、壊れても `mise run index` で再生成できます。

## ドキュメント

README は全体の入口です。詳細は `docs/` に分けています。

| ファイル                                                   | 内容                                          |
| ---------------------------------------------------------- | --------------------------------------------- |
| [docs/template-operation.md](docs/template-operation.md)   | template repo 自体の保守方法                  |
| [docs/instance-setup.md](docs/instance-setup.md)           | コピー後の brain instance セットアップ        |
| [docs/environment.md](docs/environment.md)                 | `.env` と環境変数の優先順位・用途・既定挙動   |
| [docs/knowledge-ingest.md](docs/knowledge-ingest.md)       | ソース取得、ingest、再 ingest、Web clip       |
| [docs/chrome-extension.md](docs/chrome-extension.md)       | Chrome extension からの Web clip              |
| [docs/search.md](docs/search.md)                           | Layer 1 / Layer 2 の検索の流れ                |
| [docs/http-api.md](docs/http-api.md)                       | HTTP server / REST API の起動・認証・endpoint |
| [docs/server-management.md](docs/server-management.md)     | macOS / Linux の HTTP server 常駐運用         |
| [docs/mcp.md](docs/mcp.md)                                 | MCP server の起動方法と tool                  |
| [docs/wiki-operations.md](docs/wiki-operations.md)         | query / sublime / dive / lint / 手動編集      |
| [docs/mise-tasks.md](docs/mise-tasks.md)                   | `mise` タスク一覧と使い分け                   |
| [development/architecture.md](development/architecture.md) | アーキテクチャの設計思想                      |

## コピーして使い始める

ローカルコピーで作る場合:

```bash
mkdir -p ~/programs/brains
cp -r ~/programs/brains/twin-layer-brain-template \
  ~/programs/brains/twin-layer-brain-<topic>
cd ~/programs/brains/twin-layer-brain-<topic>
rm -rf .git
git init
```

GitHub template repo から作る場合:

```bash
gh repo create <owner>/twin-layer-brain-<topic> --private \
  --template=<owner>/twin-layer-brain-template
git -C ~/programs/brains clone git@github.com:<owner>/twin-layer-brain-<topic>.git
cd ~/programs/brains/twin-layer-brain-<topic>
```

コピー後の初期化:

```bash
mise install
mise init
mise run scaffold-brain
```

`pyproject.toml` の name と version を書き換えます。
`README.md` / `CLAUDE.md` / `AGENTS.md` の Scope 行を、その brain が扱う作業領域に合わせて書き換えます。

詳しい手順は [docs/instance-setup.md](docs/instance-setup.md) を参照してください。

## template repo を保守する

この `twin-layer-brain-template` 自体には、プロジェクト固有の知識を入れません。template 側で変更する主なものは以下です。

- `CLAUDE.md` / `AGENTS.md`: LLM agent の運用規約
- `.agents/skills/`: ingest / query / lint / sublime / dive の skill
- `compiler/`: Layer 1 の index / search / CLI
- `server/`: REST API / MCP server
- `docs/`: 人間向け運用ドキュメント
- `mise.toml` / `mise/tasks/`: 定型タスク

template repo では `mise run scaffold-brain` は通常実行しません。
安全装置により拒否されます。
意図的に template の中身を初期化する場合だけ `FORCE=1` を使います。

詳しくは [docs/template-operation.md](docs/template-operation.md) を参照してください。

## データフロー

```text
raw/ と wiki/ の Markdown (正本)
        |
        | mise run index / API 経由の rebuild
        v
index/knowledge.db (SQLite FTS5 + vec, 派生物)
        |
        | CLI / REST / MCP / query の候補検索
        v
LLM が wiki/index.md と関連 Markdown を読んで回答
```

書き込みは Markdown 側だけに行います。SQL へ直接知識を書き込む運用はしません。

### 注意

API 経由の note 作成・更新、Web clip、GitHub webhook では `rebuild_index()` が呼ばれます。
一方で、エディタや LLM が Markdown を直接編集した場合は、検索結果を最新にするために `mise run index` または `mise run init` を実行してください。

## ディレクトリ構造

```text
twin-layer-brain-<topic>/
├── README.md
├── CLAUDE.md
├── AGENTS.md
├── docs/
├── development/
├── .agents/skills/
├── compiler/
├── server/
├── deploy/
├── mise.toml
├── repos.json          # raw/repos/ のマニフェスト（tracked）
├── raw/
│   ├── notes/
│   ├── articles/
│   ├── assets/
│   └── repos/          # gitignored（repos.json から再構築）
├── wiki/
│   ├── index.md
│   ├── log.md
│   ├── sources/
│   ├── entities/
│   ├── concepts/
│   ├── topics/
│   └── analyses/       # gitignored by default
└── index/              # gitignored, regenerable
```

## よく使うコマンド

```bash
mise tasks                 # タスク一覧
mise run init              # 依存を同期し、SQLite index を作る
mise run clone-repo owner/repo         # clone + repos.json に記録
mise run update-repos                  # repos.json に従って同期
mise run update-repos --prune          # 孤立 repo を .trash/ に退避
mise run diff-template                 # template remote との差分表示（要 remote 登録、docs/instance-setup.md 参照）
mise run diff-template --apply         # 差分を template の内容で一括上書き（確認プロンプトあり）
mise run reset-token      # BRAIN_API_TOKEN を .env に作成・更新
mise run check-keys       # API key 状態確認（embedding 実生成はしない）
mise run check-keys -- --json
mise run check-keys -- --color
mise run check-keys-live  # embedding 実生成 probe（原因切り分け時のみ）
mise run serve
mise run serve-install    # 常駐 service 登録（macOS: launchd / Linux: systemd --user）
mise run serve-status
mise run serve-logs
mise run test
mise run lint             # Markdown のみ
mise run lint --all       # Markdown + ruff + shfmt
mise run format           # Markdown のみ
mise run format --all     # Markdown + ruff + shfmt

mise run index            # 検索 index を再構築
mise run status           # index DB のサイズ / note 件数 / embedding カバレッジ
mise run kc               # kc CLI の subcommand 一覧から fzf 選択（TTY 必須）
mise run kc -- search "Docker"    # kc の任意 subcommand を passthrough
```

`search` / `show` / `suggest-related` / `new` / `validate` は LLM agent や server が内部で呼ぶ kc subcommand です。
人間が手動で叩きたい時は `mise run kc` の fzf 選択か `mise run kc -- <subcommand>` を使います。

各タスクの意味は [docs/mise-tasks.md](docs/mise-tasks.md) にまとめています。

## 知識を入れて検索する

1. `raw/notes/`, `raw/articles/`, `raw/repos/` にソースを置く。
2. Claude Code / Codex で `ingest raw/...` を実行する。
3. LLM が `wiki/sources/` を作り、関連する `entities/` / `concepts/` / `topics/`
   を更新する。
4. `mise run index` で Layer 1 の検索 index を更新する。
5. 検索は `kc search` (CLI) / REST / MCP / 通常の `query` で行う。

Layer 1 は「読むべき Markdown 候補を絞る」ための補助です。
最終的な回答は Layer 2 の `wiki/index.md` と関連 Markdown を読んで作ります。

詳細:

- [docs/knowledge-ingest.md](docs/knowledge-ingest.md)
- [docs/search.md](docs/search.md)
- [docs/wiki-operations.md](docs/wiki-operations.md)

## API とサーバー

開発時は foreground で起動します。

```bash
mise run serve
```

主な endpoint:

```text
GET  /api/health
GET  /api/auth/check
GET  /api/notes/search?q=keyword
GET  /api/notes/similar?q=文章
GET  /api/notes/{id}
POST /api/notes
POST /api/clip
POST /api/sync/webhook
```

`/api/notes/*`、`/api/index/*`、`/api/clip` は `BRAIN_API_TOKEN` の Bearer token を使います。
`mise run reset-token` で `.env` に token を作成・更新できます。
更新した場合は、起動中の server を再起動し、Chrome extension 側の token 設定も同じ値に更新してください。
環境変数の優先順位と既定挙動は [docs/environment.md](docs/environment.md) にまとめています。

常駐 service として登録したい場合は `mise run serve-install` を使います。
macOS では launchd、Linux / WSL では systemd --user を使います。
VPS で root 管理の system service として運用する場合は `deploy/setup.sh` と `deploy/brain.service` を使います。

HTTP API の詳細は [docs/http-api.md](docs/http-api.md)、MCP の詳細は
[docs/mcp.md](docs/mcp.md) を参照してください。

## このテンプレートの非目的

- 複数トピックを 1 repo に混ぜること。別の作業領域は別コピーにします。
- SQLite を正本にすること。SQLite は常に Markdown から再生成します。
- `raw/repos/` の全コードを常時 index すること。大きな repo は `ingest` / `dive` の対象であり、通常の Layer 1 index からは外します。
