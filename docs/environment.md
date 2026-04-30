# 環境変数

このファイルは、`.env` と環境変数の優先順位、各変数の用途、未設定時の挙動をまとめます。

## 読み込みの優先順位

`compiler.env.load_dotenv()` は repo root の `.env` を読み、同名の環境変数が既に親プロセス側にあっても `.env` の値で上書きします。
これは、PC 上に複数の brain instance を置く前提で、instance ごとの設定を repo root の `.env` に閉じるためです。

優先順位:

1. repo root の `.env`
2. 親プロセスから渡された環境変数
3. コード側の default

親プロセスから渡される値の例:

- `~/.bashrc` / `~/.profile`
- shell での `export`
- systemd `EnvironmentFile`
- launchd の環境

例:

```bash
export OPENAI_API_KEY=sk-shell
```

この状態で `.env` に以下があっても:

```dotenv
OPENAI_API_KEY=sk-dotenv
```

実際に使われるのは `sk-dotenv` です。

この挙動は `mise run index` / `check-keys` などの `kc` 系 task、`mise run kc` 経由の任意 subcommand、
`uv run kc ...` を直接叩いた場合、および `mise run serve` のすべてに関係します。
`kc` CLI と server は起動時に `load_dotenv()` を呼び、repo root の `.env` を優先します。

`.env` には secret や instance 固有値を置くため、`/.env` は `.gitignore` で除外しています。共有するのは `.env.example` だけです。

## どのコマンドが .env を読む / 更新するか

| コマンド / 経路                                     | `.env` 扱い | 備考                                                    |
| --------------------------------------------------- | ----------- | ------------------------------------------------------- |
| `mise run index` / `check-keys` / `check-keys-live` | あり        | 実体は `uv run kc <subcommand>`                         |
| `mise run kc -- <subcommand>`                       | あり        | passthrough で `uv run kc <subcommand>` を呼ぶ          |
| `uv run kc ...` を直接叩いた場合                    | あり        | `compiler.cli.main()` が `load_dotenv()` を呼ぶ         |
| `mise run serve`                                    | あり        | `server.run` が `load_dotenv()` を呼ぶ                  |
| `mise run serve-install` で登録した常駐 service     | あり        | 起動後の Python process が repo root の `.env` を読む   |
| `deploy/setup.sh` で登録した system service         | あり        | `EnvironmentFile` より repo root の `.env` が優先される |
| `mise run reset-token`                              | 書き込み    | `.env` を作成し、`BRAIN_API_TOKEN` を作成または更新する |
| `mise run serve-status`                             | 一部あり    | health check 用 port は `.env` の `BRAIN_PORT` も見る   |

`serve-status` は Python server の設定値そのものを読み込むのではなく、shell script 側で
`.env` の `BRAIN_PORT` を簡易的に読みます。複雑な shell 展開を `.env` に書いた場合は解釈できません。

## 変数一覧

| 変数                      | default                   | 使う場所                         | 未設定時の挙動                                          |
| ------------------------- | ------------------------- | -------------------------------- | ------------------------------------------------------- |
| `BRAIN_API_TOKEN`         | なし                      | REST API 認証                    | token 保護された endpoint が 503 を返す                 |
| `GITHUB_WEBHOOK_SECRET`   | なし                      | GitHub webhook 署名検証          | `/api/sync/webhook` が 503 を返す                       |
| `BRAIN_HOST`              | `127.0.0.1`               | HTTP server bind host            | localhost からのみ待ち受ける                            |
| `BRAIN_PORT`              | `15200`                   | HTTP server port                 | port `15200` で起動する                                 |
| `BRAIN_MCP_REQUIRE_TOKEN` | `false`                   | HTTP MCP 認証                    | `/mcp` は token なしで接続可能                          |
| `OPENAI_API_KEY`          | なし                      | embedding、OpenAI LLM、key check | semantic search 無効、OpenAI は provider 候補から外れる |
| `GEMINI_API_KEY`          | なし                      | Web clip 要約用 LLM、key check   | Gemini は provider 候補から外れる                       |
| `ANTHROPIC_API_KEY`       | なし                      | Web clip 要約用 LLM、key check   | Anthropic は provider 候補から外れる                    |
| `BRAIN_LLM_PRIORITY`      | `openai,gemini,anthropic` | Web clip 要約 provider 選択      | default 順に利用可能 provider を探す                    |

## BRAIN_API_TOKEN

REST API の Bearer token です。

作成・更新:

```bash
mise run reset-token
```

`reset-token` は `.env` がない場合は `.env.example` から作成します。
既に `BRAIN_API_TOKEN=` があれば新しい token に置き換え、なければ追記します。
実行時に token が stdout に表示されるため、Chrome extension の Settings に同じ値を設定します。
起動中の `mise run serve` は古い環境変数を保持しているため、token 更新後は server を再起動してください。

使い方:

```bash
curl -H "Authorization: Bearer $BRAIN_API_TOKEN" "http://127.0.0.1:15200/api/notes/search?q=Docker"
```

未設定時:

- `/api/notes/*` は `503 API token not configured on server`
- `/api/index/*` も同様
- `/api/clip` も同様
- `/api/health` は token なしで使える

`BRAIN_MCP_REQUIRE_TOKEN=true` にすると `/mcp` も同じ Bearer token で保護します。
stdio MCP は HTTP を使わないため、この設定の影響を受けません。

## GITHUB_WEBHOOK_SECRET

GitHub webhook の `X-Hub-Signature-256` を検証する secret です。

未設定時:

- `POST /api/sync/webhook` は `503 Webhook secret not configured`

設定している場合でも、署名 header がないと 400、不一致なら 403 です。

## BRAIN_HOST / BRAIN_PORT

HTTP server の bind address と port です。

default:

```dotenv
BRAIN_HOST=127.0.0.1
BRAIN_PORT=15200
```

挙動:

- `BRAIN_HOST=127.0.0.1`: ローカルマシンからのみ接続
- `BRAIN_HOST=0.0.0.0`: LAN / 外部からも接続可能。公開時は認証と reverse proxy を確認
- `BRAIN_PORT` は同じ PC に複数 instance を置く場合、instance ごとに変える

例:

```dotenv
BRAIN_PORT=15201
```

## BRAIN_MCP_REQUIRE_TOKEN

HTTP MCP endpoint `/mcp` を `BRAIN_API_TOKEN` で保護するかどうかです。

default:

```dotenv
BRAIN_MCP_REQUIRE_TOKEN=false
```

ローカル agent から stdio MCP を使う場合、この設定は関係ありません。
streamable HTTP MCP を使い、client が `Authorization: Bearer ...` header を送れる場合だけ
`true` にします。

## OPENAI_API_KEY

2 つの用途があります。

1. `compiler/embedding.py` の embedding 生成
2. `server/llm.py` の Web clip 要約 provider

未設定時:

- `mise run index` は embedding を作らず、FTS5 index だけ作る
- `kc search` は keyword search のみ（`mise run kc -- search` / `uv run kc search` いずれも同じ）
- `kc suggest-related` は semantic search 不可として終了
- Web clip 要約では OpenAI が候補から外れる

FTS5 のキーワード検索は `OPENAI_API_KEY` なしで動きます。

## GEMINI_API_KEY / ANTHROPIC_API_KEY

Web clip の自動要約・タグ生成に使う LLM provider 候補です。semantic search には使いません。

未設定時:

- その provider は候補から外れる
- 他 provider が使える場合はそちらを試す
- 全 provider が使えない場合、Web clip は要約なし・追加 tag なしで保存する

## BRAIN_LLM_PRIORITY

Web clip 要約に使う provider の優先順です。

default:

```dotenv
BRAIN_LLM_PRIORITY=openai,gemini,anthropic
```

例:

```dotenv
BRAIN_LLM_PRIORITY=gemini,openai,anthropic
```

`server/llm.py` はこの順に provider を確認します。利用可能 provider は`index/llm_provider_cache.json` に日次 cache されます。
provider を切り替えたい時は、環境変数を変えたうえで cache file を削除すると確認が早いです。

## MITM プロキシ配下での TLS 検証

企業 MITM プロキシ (Netskope, Zscaler, Blue Coat など) が TLS を開いて自社 CA で署名し直す環境では、Python 標準の検証で `CERTIFICATE_VERIFY_FAILED` が出ます。原因は 2 層あります。

1. `certifi` の CA bundle には社内 CA が含まれない
2. 社内 CA を certifi に連結しても、**OpenSSL 3.x (Python 3.12+) が Basic Constraints の critical フラグを要求**するため、古めの社内 CA は `Basic Constraints of CA cert not marked critical` で弾かれる

このため brain では `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` 方式ではなく、[`truststore`](https://truststore.readthedocs.io/) で **OS の信頼ストア** (macOS Keychain / Linux openssl / Windows SChannel) を使います。`compiler.env.use_system_trust_store()` が CLI と server の起動時に呼ばれ、`ssl` モジュールに OS ストア経由の検証を注入します。

- MITM プロキシを使っていない環境: certifi と同等の挙動
- MITM プロキシ配下: プロキシ Agent (Netskope Client など) が OS ストアに登録した CA が自動で有効

特別な環境変数は不要です。プロキシ Agent が正しくインストールされていて、OS ストアに社内 CA が入っていれば動きます。うまくいかない場合は [instance-setup.md](instance-setup.md) の「MITM プロキシ環境の TLS 設定」節にある切り分けコマンドを参照してください。

## check-keys の見方

```bash
mise run check-keys
mise run check-keys -- --json
mise run check-keys -- --color
```

確認対象:

- Chat LLM provider: `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`
- Embedding: default では `OPENAI_API_KEY` の存在と OpenAI chat probe の結果から「設定済みか」を表示し、Embeddings API への実リクエストは投げない

表示の意味:

| 表示   | 意味                                               |
| ------ | -------------------------------------------------- |
| `OK`   | HTTP 200。利用可能                                 |
| `RATE` | HTTP 429。rate limited だが key 自体は有効とみなす |
| `AUTH` | HTTP 401 / 403。key が無効                         |
| `NONE` | 環境変数が未設定                                   |
| `ERR`  | ネットワークまたは想定外の HTTP status             |
| `SKIP` | 有料になり得る実 API probe を明示的に省略した      |

出力は `Chat LLM providers (server/llm.py)` と `Embedding (compiler/embedding.py)` に分かれます。
通常の `mise run check-keys` は OpenAI / Gemini / Anthropic の`/models` 系 endpoint を確認します。
これは key の未設定、認証失敗、rate limit、ネットワークエラーを切り分ける用途です。

`--json` を付けると、`chat_providers`, `embedding`, `live_embedding`, `cached_active_provider`, `any_usable` を含む JSON を stdout に出します。
shell script やCI から判定する場合はこの形式を使います。
`--color` を付けると、人間向け表示の status badge に色を付けます。`--json` と `--color` を併用した場合、JSON は常に色なしです。

embedding の実生成まで確認したい場合だけ、以下を実行します。

```bash
mise run check-keys-live
mise run check-keys-live --json
```

`check-keys-live` は OpenAI Embeddings API に短い input を送り、
semantic search で使う `text-embedding-3-small` の実生成を確認します。
この確認は小さいながら API 使用量を発生させるため、日常的な確認ではなく、原因切り分け時だけ使います。

`check-keys` は `load_dotenv()` 後の環境を見ます。
repo root に `.env` がある場合は`.env` の値が確認対象です。
`.env` に値がない場合だけ、`~/.bashrc` など親プロセス側の値が確認対象になります。
