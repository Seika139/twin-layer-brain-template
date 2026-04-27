# 検索

検索は 2 段階です。

1. Layer 1: SQLite で候補 Markdown を絞る。
2. Layer 2: LLM が `wiki/index.md` と関連 Markdown を読んで回答する。

SQLite の検索結果だけで答える運用ではありません。Layer 1 は候補発見のための
補助です。

## Layer 1 の対象

通常 index されるのは以下です。

- `raw/notes/`
- `raw/articles/`
- `wiki/sources/`
- `wiki/entities/`
- `wiki/concepts/`
- `wiki/topics/`

`raw/repos/` は大きく、nested `.git` を持つため通常 index から外します。repo の
詳細調査は `ingest` または `dive` で行います。

## 検索の種類と必要な API key

### FTS keyword search

SQLite FTS5 の全文検索です。入力した語句や記号列に近い文字列を含む Markdown を探します。
`uv run kc search`, `GET /api/notes/search`,`search_notes` から使えます。API key は不要です。
固有名詞、コマンド名、ファイル名、エラー文、設定値など「文字としてそこに書いてあるもの」を探す時に向いています。

### Semantic search

query 文と Markdown 本文の embedding 距離で近いページを探す検索です。
`uv run kc search`, `GET /api/notes/similar`, `search_similar_notes` から使えます。
`OPENAI_API_KEY` が必要です。
言い換え、類似概念、同じ意味だが違う単語で書かれたメモを拾いたい時に向いています。
未設定時は semantic 結果は出ませんが、FTS keyword search はそのまま使えます。

### Related notes

特定 note の embedding を起点に、近い note を探す検索です。
`uv run kc suggest-related`, `GET /api/notes/{id}/suggest-related`, `suggest_related_notes` から使えます。
`OPENAI_API_KEY` が必要です。
あるページを読んだあとに、近いテーマのメモや wiki ページを横に広げたい時に向いています。
未設定時、CLI は semantic search 不可として終了し、API / MCP は空結果になります。

### LLM Wiki query

Claude Code / Codex の通常質問や `query` skill による読み取りです。
Layer 1 の検索結果は候補を絞るための補助で、最終的には LLM が `wiki/index.md` と関連 Markdown を読んで回答します。
必要な API key は agent 側の実行環境に依存します。
Layer 1 の semantic 補助がなくても、`wiki/` 読みによる回答は可能です。

まとめると、必要な API key は次の通りです。

| 検索               | 必要な API key           |
| ------------------ | ------------------------ |
| FTS keyword search | なし                     |
| Semantic search    | `OPENAI_API_KEY`         |
| Related notes      | `OPENAI_API_KEY`         |
| LLM Wiki query     | agent 側の実行環境に依存 |

`OPENAI_API_KEY` は embedding 生成に使います。Gemini / Anthropic の key は semantic
search には使いません。Web clip の要約 provider としてだけ使います。

環境変数の優先順位や未設定時の詳細は [environment.md](environment.md) を参照してください。

## index を作る

```bash
uv run kc index
```

`OPENAI_API_KEY` があれば embedding も作られ、semantic search が使えます。キーがない場合でも FTS5 のキーワード検索は使えます。
embedding が作れない場合、index 作成は FTS5 だけで継続します。原因を切り分けるには
まず `mise run check-keys` を実行し、`Embedding (compiler/embedding.py)` の結果を
確認してください。Embeddings API の実生成まで確認したい場合だけ、
`mise run check-keys-live` を実行します。

## CLI 検索

```bash
uv run kc search "Docker"
uv run kc show <id-or-path>
uv run kc suggest-related <note-id>
uv run kc check-keys
uv run kc check-keys --json
```

`kc search` は FTS 結果を出し、embedding が有効なら semantic search も併せて出します。

## REST API

HTTP API の詳しい使い方は [http-api.md](http-api.md) を参照してください。

server 起動:

```bash
mise run serve
```

主な endpoint:

```text
GET  /api/health
GET  /api/notes/search?q=keyword
GET  /api/notes/similar?q=文章
GET  /api/notes/{id}
POST /api/notes
PUT  /api/notes/{id}
POST /api/index/rebuild
```

`/api/notes/*`、`/api/index/*`、`/api/clip` は `BRAIN_API_TOKEN` の Bearer token が
必要です。

## MCP

MCP の詳しい使い方は [mcp.md](mcp.md) を参照してください。MCP server は
`server/mcp_server.py` にあります。

主な tool:

- `search_notes`
- `search_similar_notes`
- `read_note`
- `suggest_related_notes`
- `create_note`
- `append_note`
- `rebuild_index`

LLM agent は query の前段で `search_notes` / `search_similar_notes` を使い、候補を
絞れます。ただし最終的な回答では `wiki/` のページを読んで citation を付けます。

## Query skill との関係

通常の質問:

```text
> この brain に Docker の運用メモはある？
```

query skill はまず `wiki/index.md` を読みます。必要なら Layer 1 の検索で候補を
増やし、関連ページと `[[wiki-link]]` を辿って回答します。

## 2 段階検索が有効な場面

- ページ数が増え、`wiki/index.md` だけでは候補を見落としやすい。
- exact keyword で探したい。
- `raw/articles/` や `raw/notes/` の未整理情報も拾いたい。
- REST / MCP / CLI から LLM 外でも検索したい。

小さい brain では、Markdown Wiki だけでも十分な場合があります。Layer 1 は
複雑さも増やすので、検索結果が古くならないよう `uv run kc index` を運用に入れます。
