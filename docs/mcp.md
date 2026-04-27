# MCP

MCP server は、LLM client から Layer 1 の検索や Markdown note 操作を呼ぶための
入口です。実装は `server/mcp_server.py` にあります。

この repo には 2 つの MCP 起動経路があります。

| 経路            | 起動方法                            | プロセス管理                          | 向いている用途                     |
| --------------- | ----------------------------------- | ------------------------------------- | ---------------------------------- |
| stdio           | `uv run python -m server.mcp_stdio` | MCP client が子プロセスとして起動する | ローカル agent から 1 brain を使う |
| streamable HTTP | `mise run serve`                    | 常駐 HTTP server として起動する       | 複数 client / 常駐 service / proxy |

## Stdio vs Streamable HTTP

| 観点        | stdio                            | streamable HTTP                       |
| ----------- | -------------------------------- | ------------------------------------- |
| 通信        | 標準入力 / 標準出力              | HTTP                                  |
| 起動        | MCP client が command を起動     | `mise run serve` で server を起動     |
| port        | 不要                             | `BRAIN_HOST` / `BRAIN_PORT` が必要    |
| 公開範囲    | ローカル子プロセスに閉じる       | bind address と network 設定に依存    |
| 複数 client | client ごとに process を持つ運用 | 1 server に複数 client が接続しやすい |
| 推奨用途    | 手元の Codex / Claude から使う   | 常駐、複数 client、HTTP 経由接続      |

推奨は、**ローカル agent から使うなら stdio**、**常駐 service や複数 client から使うなら streamable HTTP** です。

## MCP と REST API の違い

| 観点       | MCP                                            | REST API                                           |
| ---------- | ---------------------------------------------- | -------------------------------------------------- |
| 主な利用者 | LLM client / agent                             | 人間、script、外部 app                             |
| 呼び方     | tool call                                      | HTTP request                                       |
| 代表入口   | `search_notes`, `read_note`, `rebuild_index`   | `GET /api/notes/search`, `POST /api/index/rebuild` |
| 目的       | agent が作業中に検索・読み取り・補助操作を行う | CLI 以外のプログラムから API として使う            |
| 認証       | 既定は token なし。`BRAIN_MCP_REQUIRE_TOKEN=true` で Bearer token 必須 | `/api/notes/*`, `/api/index/*`, `/api/clip` は Bearer token |

MCP は agent 向けの tool interface です。
REST API は HTTP client から直接呼ぶ programmatic interface です。
どちらも最終的には同じ `compiler.search` や `compiler.indexer` を使います。

## Streamable HTTP MCP

`mise run serve` で HTTP API と同時に起動します。

```bash
mise run serve
```

**接続先:**

```text
http://127.0.0.1:15200/mcp
```

`BRAIN_HOST` / `BRAIN_PORT` を `.env` で変えている場合は、その値に合わせます。

**注意:**

既定では `/mcp` は Bearer token を要求しません。基本運用は `BRAIN_HOST=127.0.0.1`
の localhost bind です。

HTTP MCP client が header を設定できる場合は、`.env` で以下を有効にできます。

```dotenv
BRAIN_MCP_REQUIRE_TOKEN=true
```

有効にすると `/mcp` も `BRAIN_API_TOKEN` の Bearer token が必要です。

```text
Authorization: Bearer <BRAIN_API_TOKEN>
```

外部公開する場合は、token 認証に加えて reverse proxy、firewall、VPN などでも守ってください。
stdio MCP は HTTP endpoint を使わないため、この設定の影響を受けません。

## Stdio MCP

stdio transport で起動する場合:

```bash
uv run python -m server.mcp_stdio
```

MCP client 側に command と working directory を設定して使います。
client の設定形式はツールごとに異なるため、基本的には以下の情報を登録します。

```text
command: uv
args: run python -m server.mcp_stdio
cwd: /path/to/twin-layer-brain-<topic>
```

JSON 形式で設定する client では、概ね次の形になります。

```json
{
  "mcpServers": {
    "twin-layer-brain-project-a": {
      "command": "uv",
      "args": ["run", "python", "-m", "server.mcp_stdio"],
      "cwd": "/path/to/twin-layer-brain-project-a"
    }
  }
}
```

`.env` は repo root のものが優先して読み込まれます。複数 brain instance を使う場合は、
client 設定の `cwd` を instance ごとに分けてください。

## Tools

### search_notes

FTS keyword search です。API key は不要です。

**入力:**

```text
query: string
limit: int = 20
```

**用途:**

- 固有名詞、コマンド名、エラー文、設定値などを探す
- LLM Wiki query の前段で候補 Markdown を絞る

### search_similar_notes

Semantic search です。`OPENAI_API_KEY` が必要です。

**入力:**

```text
query: string
limit: int = 10
```

**用途:**

- 言い換えや近い概念を拾う
- `wiki/index.md` だけでは見つけにくい関連ページを候補に出す

`OPENAI_API_KEY` が未設定、または embedding が作られていない場合は空結果になります。

### read_note

note id または path で note を読みます。

**入力:**

```text
id_or_path: string
```

**用途:**

- `search_notes` / `search_similar_notes` の結果から本文を読む
- query 時に候補ページを確認する

### suggest_related_notes

特定 note の embedding を起点に近い note を探します。`OPENAI_API_KEY` が必要です。

**入力:**

```text
id_or_path: string
limit: int = 5
```

**用途:**

- ある wiki page から近いテーマを横展開する
- topic / concept の関連候補を探す

### create_note

Markdown note を作成し、index を再構築します。

**入力:**

```text
title: string
kind: string = "note"
directory: string = "raw/notes"
tags: list[string] | null = null
```

**注意:**

- default は `raw/notes/` です。
- `raw/notes/` は人間所有の不変ソースという運用なので、agent が勝手に作る用途は
  慎重に扱います。
- agent に広い自動実行権限を与える場合、この tool は write-capable です。必要に応じて
  MCP client 側で確認付きにするか、運用ルールで使用範囲を限定してください。

### append_note

既存 note に本文を追記し、index を再構築します。

**入力:**

```text
id_or_path: string
content: string
```

**注意:**

- `raw/notes/` は原則として LLM が編集しない領域です。
- 恒久的な知識更新は通常 `wiki/` 側に行います。
- この tool も write-capable です。検索・読み取りだけをさせたい client では、
  `append_note` と `create_note` の利用を許可しない運用を検討してください。

### rebuild_index

Markdown から SQLite index を再構築します。

**入力:**

なし

**用途:**

- エディタや LLM が Markdown を直接編集した後に検索結果を更新する
- `kc index` の MCP tool 版として使う
- `ingest` / `query` / `sublime` / `dive` などで Markdown を更新した後、Layer 1 の
  検索結果を最新化する

## Query Skill との関係

MCP tool は高レベル skill の代替ではありません。
`query` skill は、必要に応じて`search_notes` や `search_similar_notes` で候補を絞り、その後 `wiki/index.md` と関連 Markdown を読んで回答します。

**原則:**

- MCP の検索結果だけで最終回答しない。
- 回答の根拠は `wiki/`、必要時は `raw/` に置く。
- SQL / MCP は候補発見の補助として使う。

## 実装場所

| ファイル               | 役割                                   |
| ---------------------- | -------------------------------------- |
| `server/mcp_server.py` | MCP tool 定義                          |
| `server/mcp_stdio.py`  | stdio transport 起動                   |
| `server/app.py`        | streamable HTTP MCP を `/mcp` に mount |
