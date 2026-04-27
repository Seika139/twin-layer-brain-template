# HTTP API

HTTP API は `server/` にある FastAPI アプリです。`mise run serve` を実行すると、
同じプロセス内で REST API と MCP streamable HTTP の両方が起動します。

```text
http://<BRAIN_HOST>:<BRAIN_PORT>/api  -> REST API
http://<BRAIN_HOST>:<BRAIN_PORT>/mcp  -> MCP streamable HTTP
```

既定値は `127.0.0.1:15200` です。

## 起動

開発時:

```bash
mise run serve
```

内部では次を実行します。

```bash
uv run python -m server.run
```

`BRAIN_HOST` と `BRAIN_PORT` は repo root の `.env` を優先して読みます。
複数のbrain instance を同じ PC で起動する場合は、instance ごとに `BRAIN_PORT` を変えます。

```dotenv
BRAIN_HOST=127.0.0.1
BRAIN_PORT=15201
```

常駐 service として登録する場合:

```bash
mise run serve-install
mise run serve-status
```

`serve-install` は OS を自動判定します。macOS では launchd、Linux では systemd --user を使います。
Linux / WSL で `systemd --user` が使えない場合、`serve-systemd-*` は設定案内を出して終了します。
VPS で root 管理の system service として登録する場合は、既存の `deploy/setup.sh` を使います。

```bash
sudo ./deploy/setup.sh /opt/brain
sudo systemctl start brain
sudo systemctl status brain
```

macOS / Linux の詳しい常駐運用は [server-management.md](server-management.md) を参照してください。

複数 instance を同じ Linux host に置く場合は、`SERVICE_NAME` と `.env` の `BRAIN_PORT` を
instance ごとに分けます。

```bash
sudo SERVICE_NAME=brain-project-a ./deploy/setup.sh /opt/brain-project-a
sudo systemctl restart brain-project-a
```

## 認証

`/api/notes/*`、`/api/index/*`、`/api/clip` は `BRAIN_API_TOKEN` の Bearer token が
必要です。

```bash
curl -H "Authorization: Bearer $BRAIN_API_TOKEN" \
  "http://127.0.0.1:15200/api/notes/search?q=Docker"
```

`BRAIN_API_TOKEN` が未設定の場合、token 保護された endpoint は 503 を返します。
token は `mise run reset-token` で `.env` に作成・更新できます。更新後は起動中の
server を再起動し、Chrome extension など client 側に設定した token も更新してください。

現状の認証状態:

| endpoint                 | 認証                                                                    |
| ------------------------ | ----------------------------------------------------------------------- |
| `GET /api/health`        | 不要                                                                    |
| `GET /api/auth/check`    | `BRAIN_API_TOKEN` 必須                                                  |
| `/api/notes/*`           | `BRAIN_API_TOKEN` 必須                                                  |
| `/api/index/*`           | `BRAIN_API_TOKEN` 必須                                                  |
| `POST /api/clip`         | `BRAIN_API_TOKEN` 必須                                                  |
| `POST /api/sync/webhook` | GitHub webhook signature 必須                                           |
| `/mcp`                   | 既定は不要。`BRAIN_MCP_REQUIRE_TOKEN=true` で `BRAIN_API_TOKEN` 必須    |

外部公開する場合は、`BRAIN_MCP_REQUIRE_TOKEN=true` にした上で、reverse proxy や network 制限でも守ってください。

## Auth Check

Chrome extension や curl から、server 接続と Bearer token の一致だけを確認する endpoint です。
DB や index の状態には依存しません。

```bash
curl -H "Authorization: Bearer $BRAIN_API_TOKEN" \
  "http://127.0.0.1:15200/api/auth/check"
```

応答:

```json
{ "status": "ok" }
```

## Health Check

```bash
curl "http://127.0.0.1:15200/api/health"
```

応答:

```json
{ "status": "ok" }
```

## Notes API

### Search

FTS keyword search です。API key は不要です。

```bash
curl -H "Authorization: Bearer $BRAIN_API_TOKEN" \
  "http://127.0.0.1:15200/api/notes/search?q=Docker&limit=20"
```

### Similar

Semantic search です。`OPENAI_API_KEY` が必要です。未設定時は空結果になります。

```bash
curl -H "Authorization: Bearer $BRAIN_API_TOKEN" \
  "http://127.0.0.1:15200/api/notes/similar?q=コンテナ運用&limit=10"
```

### Suggest Related

特定 note に近い note を embedding で探します。`OPENAI_API_KEY` が必要です。

```bash
curl -H "Authorization: Bearer $BRAIN_API_TOKEN" \
  "http://127.0.0.1:15200/api/notes/<note-id>/suggest-related?limit=5"
```

### Read

note id または path で note を読みます。

```bash
curl -H "Authorization: Bearer $BRAIN_API_TOKEN" \
  "http://127.0.0.1:15200/api/notes/<id-or-path>"
```

### List

kind / tag で絞り込めます。

```bash
curl -H "Authorization: Bearer $BRAIN_API_TOKEN" \
  "http://127.0.0.1:15200/api/notes?kind=concept&limit=50"
```

### Create

Markdown note を作成し、index を再構築します。

```bash
curl -X POST "http://127.0.0.1:15200/api/notes" \
  -H "Authorization: Bearer $BRAIN_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "新しいメモ",
    "kind": "note",
    "directory": "raw/notes",
    "tags": ["memo"],
    "body": "# 新しいメモ\n"
  }'
```

### Update

既存 note の body / tags / status を更新し、index を再構築します。

```bash
curl -X PUT "http://127.0.0.1:15200/api/notes/<id-or-path>" \
  -H "Authorization: Bearer $BRAIN_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tags": ["updated"]}'
```

## Index API

Markdown から SQLite index を再構築します。

```bash
curl -X POST "http://127.0.0.1:15200/api/index/rebuild" \
  -H "Authorization: Bearer $BRAIN_API_TOKEN"
```

エディタや LLM が Markdown を直接編集した後、HTTP 経由で再 index したい時に使います。

## Clip API

Web ページ内容を `raw/articles/` に保存し、index を再構築します。`skip_llm=false` の
場合、利用可能な LLM provider で要約と tag 生成を試みます。LLM が使えない場合は、
送信された本文を機械的に保存します。
保存時は URL を identity として扱います。同じ URL の clip は同じ Markdown ファイルを更新し、
別 URL であれば title が同じでも別ファイルに保存します。
`canonical_url` を送った場合は、同一ページ判定で `canonical_url` を優先します。

```bash
curl -X POST "http://127.0.0.1:15200/api/clip" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BRAIN_API_TOKEN" \
  -d '{
    "title": "Example Article",
    "url": "https://example.com/article",
    "canonical_url": "https://example.com/article",
    "content": "本文...",
    "tags": ["example"],
    "skip_llm": false
  }'
```

レスポンスには通常の note 情報に加えて、`capture_mode` と `llm_used` が含まれます。
`capture_mode=ai` は LLM 要約または tag 生成を使った保存、`mechanical` は抽出本文を
そのまま保存した fallback です。
保存された `raw/articles/*.md` の frontmatter にも `capture_mode`, `llm_used`, `llm_requested`
が残ります。`llm_requested=true` かつ `llm_used=false` の場合は、AI を試したが fallback した
ことを意味します。
同じファイルへ更新するための `url_hash` と、本文差分を見分けるための `content_hash` も
frontmatter に残ります。

## Sync Webhook

GitHub webhook から `git pull --ff-only` を実行し、index を再構築します。

```text
POST /api/sync/webhook
```

`GITHUB_WEBHOOK_SECRET` と `X-Hub-Signature-256` が必要です。
未設定なら 503、署名なしなら 400、不一致なら 403 を返します。

## 実装場所

| ファイル                 | 役割                             |
| ------------------------ | -------------------------------- |
| `server/run.py`          | `.env` を読み、uvicorn を起動    |
| `server/app.py`          | `/api` と `/mcp` を mount        |
| `server/routes/notes.py` | notes API                        |
| `server/routes/index.py` | index rebuild API                |
| `server/routes/clip.py`  | Web clip API                     |
| `server/routes/sync.py`  | GitHub webhook                   |
| `server/auth.py`         | Bearer token / webhook signature |
