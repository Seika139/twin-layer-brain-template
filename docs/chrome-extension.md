# Chrome Extension

`chrome-extension/` は、Chrome の「パッケージ化されていない拡張機能」としてローカル追加する前提の Web clipper です。
配布や Chrome Web Store 公開は想定していません。

## 役割

現在開いている Web ページから title / URL / 本文候補を取り出し、ローカルの brain HTTP server に `POST /api/clip` します。保存先は `raw/articles/` です。

`raw/articles/` は一時ディレクトリではなく、Web ページ由来の source material の置き場です。
保存後は Layer 1 index が更新されます。LLM Wiki への本格的な統合は、必要に応じて `ingest raw/articles/<file>.md` で行います。

保存時は URL を identity として扱います。ページに `<link rel="canonical">` がある場合はその canonical URL を優先します。
同じ URL のページをもう一度 clip した場合は同じ Markdown ファイルを更新します。
別 URL であれば、ページ title が同じでも別ファイルとして保存します。
新規ファイル名は `<title-slug>-<url_hash>.md` です。

## セットアップ

1. brain instance の `.env` に `BRAIN_API_TOKEN` を作成する。
2. server を起動する。

```bash
mise run reset-token
mise run serve
```

1. Chrome で `chrome://extensions` を開く。
2. Developer mode を有効にする。
3. Load unpacked で repo root の `chrome-extension/` を選ぶ。
4. extension の Settings で以下を設定する。

```text
API Endpoint: http://localhost:15200
Bearer Token: .env の BRAIN_API_TOKEN
```

`BRAIN_PORT` を変えている場合は、endpoint の port も合わせます。manifest はローカル利用前提で
`localhost` と `127.0.0.1` だけを許可しています。

## アイコンの色を brain ごとに分ける

複数 brain を Chrome に同時 load する場合、toolbar でどの brain か見分けにくくなります。
`scaffold-brain` 時に `SCAFFOLD_ICON_COLOR=#RRGGBB` を渡すと、`icon48.png` / `icon128.png` のティール面だけを指定色に差し替えます (白文字と黒輪郭は保たれる)。

```bash
SCAFFOLD_ICON_COLOR=#7b1fa2 mise run scaffold-brain
```

scaffold 後に色だけ変えたい場合は `mise run recolor-icon` を使います。

```bash
mise run recolor-icon                      # ランダム色を生成して適用
mise run recolor-icon -- '#ef6c00'         # 色を明示
```

ランダム生成時は HSV 空間で S=[0.65, 0.90] / V=[0.50, 0.75] に絞った範囲から選び、現在のアイコンが持つ accent hue とは被らない色を選びます。結果の hex は `[recolor-icon] random target color: #XXXXXX` として表示されます。

accent hue はアイコンから自動検出するので、**連続して何度塗り直しても動きます** (前回塗った色が次の accent として検出される)。
ログにも `(accent hue: 175°)` のように検出値が表示されます。

細かい tuning が必要な場合は `recolor-icon.py` を直接呼び、
`--hue-center` (accent hue を手動指定) や `--sat-min` (default 0.3) を
上書きできます。

```bash
uv run --with pillow python mise/tasks/lib/recolor-icon.py \
  --target '#ef6c00' --hue-center 180 --sat-min 0.3 \
  chrome-extension/icon48.png chrome-extension/icon128.png
```

アイコンを変更したら Chrome で「拡張機能の再読み込み」を実行すると反映されます。

## 取り込みモード

popup の「AI 要約・タグ生成を試す」を有効にしている場合、server は利用可能な LLM provider で要約と tag 生成を試します。
利用可能な provider がない、または API 呼び出しが失敗した場合は、ブラウザ側で機械的に抽出した本文をそのまま保存します。

「AI 要約・タグ生成を試す」を無効にした場合は、LLM provider key が設定されていても LLM を呼びません。保存時は `skip_llm=true` として `/api/clip` に送信されます。

`/api/clip` のレスポンスには `capture_mode` が入ります。
保存された `raw/articles/*.md` の frontmatter にも同じ判定情報が残ります。

| `capture_mode` | 意味                                     |
| -------------- | ---------------------------------------- |
| `ai`           | LLM 要約または tag 生成が使われた        |
| `mechanical`   | LLM を使わず、抽出本文をそのまま保存した |

frontmatter の見方:

```yaml
source_url: https://example.com/page
canonical_url: https://example.com/page
browser_canonical_url: https://example.com/page
url_hash: 012345abcdef
content_hash: 0123456789abcdef
clipped_at: "2026-04-27T18:00:00+09:00"
capture_mode: ai
llm_used: true
llm_requested: true
```

- `source_url`: browser tab の URL。
- `browser_canonical_url`: page 内の `<link rel="canonical">` から抽出した URL。ない場合は null。
- `canonical_url`: `browser_canonical_url` があればそれを、なければ `source_url` を正規化した URL identity。
- `url_hash`: 同じ Web ページを同じファイルへ更新するための URL identity hash。
- `content_hash`: clip 時にブラウザから送られた本文の hash。ページ内容の変化を後から見分ける補助。
- `llm_used: true`: AI API を使って要約または tag 生成ができた。
- `llm_requested: false`: popup で「AI 要約・タグ生成を試す」を off にしていた。
- `llm_requested: true` かつ `llm_used: false`: AI を試したが、API key 未設定、認証失敗、通信失敗などで mechanical fallback した。

## 認証

`POST /api/clip` は `BRAIN_API_TOKEN` の Bearer token が必要です。
extension 側の token は Chrome local storage に保存されます。
ローカル利用前提でも、token は repo に commit しません。
`mise run reset-token` で token を更新した場合は、起動中の server を再起動し、extension の Settings に貼った token も更新してください。
通常の clip ごとに token を貼り直す必要はありません。

Settings の「接続と token を確認」は `GET /api/auth/check` を呼びます。
これは `BRAIN_API_TOKEN` だけを確認する軽量 endpoint で、index や note の状態には依存しません。

確認結果の見方:

- 成功: server に接続でき、token が一致しています。
- 403: extension に保存した token と server 側の `BRAIN_API_TOKEN` が一致していません。
- 503: server 側で `BRAIN_API_TOKEN` が未設定です。
- 接続失敗: server が起動していない、endpoint / port が違う、または WSL と Chrome の接続経路に問題があります。# Chrome Extension

`chrome-extension/` は、Chrome の「パッケージ化されていない拡張機能」としてローカル追加する前提の Web clipper です。
配布や Chrome Web Store 公開は想定していません。

## 役割

現在開いている Web ページから title / URL / 本文候補を取り出し、ローカルの brain HTTP server に `POST /api/clip` します。保存先は `raw/articles/` です。

`raw/articles/` は一時ディレクトリではなく、Web ページ由来の source material の置き場です。
保存後は Layer 1 index が更新されます。LLM Wiki への本格的な統合は、必要に応じて `ingest raw/articles/<file>.md` で行います。

保存時は URL を identity として扱います。ページに `<link rel="canonical">` がある場合はその canonical URL を優先します。
同じ URL のページをもう一度 clip した場合は同じ Markdown ファイルを更新します。
別 URL であれば、ページ title が同じでも別ファイルとして保存します。
新規ファイル名は `<title-slug>-<url_hash>.md` です。

## セットアップ

1. brain instance の `.env` に `BRAIN_API_TOKEN` を作成する。
2. server を起動する。

```bash
mise run reset-token
mise run serve
```

1. Chrome で `chrome://extensions` を開く。
2. Developer mode を有効にする。
3. Load unpacked で repo root の `chrome-extension/` を選ぶ。
4. extension の Settings で以下を設定する。

```text
API Endpoint: http://localhost:15200
Bearer Token: .env の BRAIN_API_TOKEN
```

`BRAIN_PORT` を変えている場合は、endpoint の port も合わせます。manifest はローカル利用前提で
`localhost` と `127.0.0.1` だけを許可しています。

## アイコンの色を brain ごとに分ける

複数 brain を Chrome に同時 load する場合、toolbar でどの brain か見分けにくくなります。
`scaffold-brain` 時に `SCAFFOLD_ICON_COLOR=#RRGGBB` を渡すと、`icon48.png` / `icon128.png` のティール面だけを指定色に差し替えます (白文字と黒輪郭は保たれる)。

```bash
SCAFFOLD_ICON_COLOR=#7b1fa2 mise run scaffold-brain
```

scaffold 後に色だけ変えたい場合は `mise run recolor-icon` を使います。

```bash
mise run recolor-icon                      # ランダム色を生成して適用
mise run recolor-icon -- '#ef6c00'         # 色を明示
```

ランダム生成時は HSV 空間で S=[0.65, 0.90] / V=[0.50, 0.75] に絞った範囲から選び、現在のアイコンが持つ accent hue とは被らない色を選びます。結果の hex は `[recolor-icon] random target color: #XXXXXX` として表示されます。

accent hue はアイコンから自動検出するので、**連続して何度塗り直しても動きます** (前回塗った色が次の accent として検出される)。
ログにも `(accent hue: 175°)` のように検出値が表示されます。

細かい tuning が必要な場合は `recolor-icon.py` を直接呼び、
`--hue-center` (accent hue を手動指定) や `--sat-min` (default 0.3) を
上書きできます。

```bash
uv run --with pillow python mise/tasks/lib/recolor-icon.py \
  --target '#ef6c00' --hue-center 180 --sat-min 0.3 \
  chrome-extension/icon48.png chrome-extension/icon128.png
```

アイコンを変更したら Chrome で「拡張機能の再読み込み」を実行すると反映されます。

## 取り込みモード

popup の「AI 要約・タグ生成を試す」を有効にしている場合、server は利用可能な LLM provider で要約と tag 生成を試します。
利用可能な provider がない、または API 呼び出しが失敗した場合は、ブラウザ側で機械的に抽出した本文をそのまま保存します。

「AI 要約・タグ生成を試す」を無効にした場合は、LLM provider key が設定されていても LLM を呼びません。保存時は `skip_llm=true` として `/api/clip` に送信されます。

`/api/clip` のレスポンスには `capture_mode` が入ります。
保存された `raw/articles/*.md` の frontmatter にも同じ判定情報が残ります。

| `capture_mode` | 意味                                     |
| -------------- | ---------------------------------------- |
| `ai`           | LLM 要約または tag 生成が使われた        |
| `mechanical`   | LLM を使わず、抽出本文をそのまま保存した |

frontmatter の見方:

```yaml
source_url: https://example.com/page
canonical_url: https://example.com/page
browser_canonical_url: https://example.com/page
url_hash: 012345abcdef
content_hash: 0123456789abcdef
clipped_at: "2026-04-27T18:00:00+09:00"
capture_mode: ai
llm_used: true
llm_requested: true
```

- `source_url`: browser tab の URL。
- `browser_canonical_url`: page 内の `<link rel="canonical">` から抽出した URL。ない場合は null。
- `canonical_url`: `browser_canonical_url` があればそれを、なければ `source_url` を正規化した URL identity。
- `url_hash`: 同じ Web ページを同じファイルへ更新するための URL identity hash。
- `content_hash`: clip 時にブラウザから送られた本文の hash。ページ内容の変化を後から見分ける補助。
- `llm_used: true`: AI API を使って要約または tag 生成ができた。
- `llm_requested: false`: popup で「AI 要約・タグ生成を試す」を off にしていた。
- `llm_requested: true` かつ `llm_used: false`: AI を試したが、API key 未設定、認証失敗、通信失敗などで mechanical fallback した。

## 認証

`POST /api/clip` は `BRAIN_API_TOKEN` の Bearer token が必要です。
extension 側の token は Chrome local storage に保存されます。
ローカル利用前提でも、token は repo に commit しません。
`mise run reset-token` で token を更新した場合は、起動中の server を再起動し、extension の Settings に貼った token も更新してください。
通常の clip ごとに token を貼り直す必要はありません。

Settings の「接続と token を確認」は `GET /api/auth/check` を呼びます。
これは `BRAIN_API_TOKEN` だけを確認する軽量 endpoint で、index や note の状態には依存しません。

確認結果の見方:

- 成功: server に接続でき、token が一致しています。
- 403: extension に保存した token と server 側の `BRAIN_API_TOKEN` が一致していません。
- 503: server 側で `BRAIN_API_TOKEN` が未設定です。
- 接続失敗: server が起動していない、endpoint / port が違う、または WSL と Chrome の接続経路に問題があります。
