# Brain Instance のセットアップ

このファイルは、`twin-layer-brain-template` をコピーして、作業領域やプロジェクト
ごとの brain instance を作る手順です。

## 前提

- 1 brain = 1 作業領域または 1 トピック
- 複数プロジェクトを扱う場合は、PC 上にコピーを複数置く
- 公開 / 非公開の境界は repo 単位で分ける
- `raw/` と `wiki/` が正本、`index/` は再生成可能な派生物

## ローカルの twin-layer-brain-template をコピーで作る

```bash
copy_repo_name="twin-layer-brain-topic" # 新しいリポジトリの名前にする
brains_root_dir=~/programs/brains # 親ディレクトリ（クォートしない / 末尾スラッシュなし）
mkdir -p "${brains_root_dir}"
cp -r "${brains_root_dir}/twin-layer-brain-template" "${brains_root_dir}/${copy_repo_name}"
cd "${brains_root_dir}/${copy_repo_name}"
rm -rf .git node_modules .venv .pytest_cache .ruff_cache .rumdl_cache
git init
```

## GitHub template repo から作る

事前に `.env` の `COPY_REPO_OWNER` と `BRAINS_ROOT_DIR` を設定しておきます（`.env.example` 参照）。

```bash
mise run copy-from-template                            # TTY: 対話で repo 名を入力
mise run copy-from-template -- --name=twin-layer-brain-<topic>
```

## 依存を入れる

```bash
mise trust -a
mise install
mise run init
```

`mise` が Python / Node / uv / pnpm / rumdl などを揃えます。
`init` はさらに必要ディレクトリを作り、依存同期と `kc index` を実行します。

## instance を空の brain として初期化する

```bash
mise run scaffold-brain                    # 対話で brain name を聞く
# あるいは
mise run scaffold-brain -- -n my-brain     # name を明示
```

`scaffold-brain` は inherited content を消し、`wiki/index.md` と `wiki/log.md` を初期化します。
加えて brain name を受け取り、**`pyproject.toml` の `project.name` と `chrome-extension/manifest.json` の `"name"` に代入、`version` は両方とも `0.0.0`** にリセットします。

例外として、`raw/articles/2026-04-04-karpathy-llm-wiki.md` は **template seed** として保護されます。これは LLM Wiki パターンの founding document（karpathy の gist）の verbatim snapshot で、source ページ書式の worked example および link rot 対策のリファレンスとして残してあります。

- そのまま keep: clone した brain の topic が knowledge engineering 系なら `/ingest` で wiki/sources/ に展開できる
- 不要なら削除: `rm raw/articles/2026-04-04-karpathy-llm-wiki.md` の 1 行で消える（他に依存ファイルなし）

引数なしで実行した場合、TTY では repo dir 名をデフォルト値としてプロンプトを出します。
非対話 (CI / pipe) では `-n <name>` 必須でエラーにします。name に使える文字は `A-Z a-z 0-9 . _ -` だけです (PEP 508 project.name と同じ制約)。

`scaffold-brain` は `.env` が無ければ `.env.example` から生成し、`15200` から順に **OS 上で未使用の port を探して `BRAIN_PORT`** に設定します (同一 PC に複数 brain を置いても衝突しない)。手動で変更したい場合は `.env` を直接編集します。

chrome-extension のアイコン色を brain ごとに分けたい場合は、scaffold 時に `SCAFFOLD_ICON_COLOR=#RRGGBB` を渡します。ティール面だけが指定色に差し替わり、白文字と黒輪郭は保たれます。

```bash
SCAFFOLD_ICON_COLOR=#7b1fa2 mise run scaffold-brain
```

未指定ならテンプレのティールのままです。
後からアイコンだけ塗り直したい場合は `mise run recolor-icon` を使います。
引数なしで実行すると鮮やかな色を自動生成します(元のティールには被らない)。

```bash
mise run recolor-icon                      # ランダム色を生成して適用
mise run recolor-icon -- '#ef6c00'         # 色を明示
```

ランダム生成時は `[recolor-icon] random target color: #XXXXXX` が表示されるので、気に入った色はメモしておくと別 brain にも再利用できます。

## Scope を書く

以下の Scope 行を、その brain の作業領域に合わせて書き換えます。

- `README.md`
- `CLAUDE.md`
- `AGENTS.md`

良い例:

```text
This brain covers: 決済基盤プロジェクトの設計・運用・障害対応
```

悪い例:

```text
This brain covers: 仕事全般
```

範囲が広すぎると `[[wiki-link]]` のグラフが薄くなり、query の精度も落ちます。

## .env を設定する

必要に応じて `.env.example` をコピーします。REST API や Chrome extension を使う場合は、`reset-token` で `BRAIN_API_TOKEN` を作成します。

```bash
cp .env.example .env
mise run reset-token
```

環境変数は repo root の `.env` が優先されます。
`~/.bashrc` など親プロセス側に同名の値があっても、`.env` に書いた値で上書きされます。
詳細な用途、既定値、未設定時の挙動は [environment.md](environment.md) を参照してください。

キーの状態確認:

```bash
mise run check-keys
```

FTS5 のキーワード検索は API key なしで動きます。
semantic search と Web clip の LLM 要約には provider key が必要です。

## MITM プロキシ環境の TLS 設定

PC に Netskope / Zscaler / Blue Coat などの MITM プロキシが入っている場合でも、brain 側の特別な設定は不要です。`compiler.env.use_system_trust_store()` が CLI と server の起動時に [`truststore`](https://truststore.readthedocs.io/) を注入し、**OS の信頼ストア** (macOS Keychain / Linux openssl / Windows SChannel) 経由で TLS を検証します。プロキシ Agent が OS ストアに登録した社内 CA がそのまま有効になります。

### なぜ certifi + `SSL_CERT_FILE` ではダメなのか

- `certifi` の CA bundle には社内 CA が含まれない
- 社内 CA を連結しても、**OpenSSL 3.x (Python 3.12+) が Basic Constraints の critical フラグを要求**するため、古めの社内 CA (Netskope 等) は `Basic Constraints of CA cert not marked critical` で弾かれる
- OS ストア経由の検証 (macOS なら SecTrust) はこの制約が緩く、プロキシ Agent 配布の CA をそのまま使える

### 確認

```bash
mise run check-keys-live
```

`Chat LLM providers` と `Embedding` がそれぞれ `OK` になれば成功です。

### まだ失敗する場合の切り分け

OS ストアに社内 CA が入っていないとエラーが続きます。macOS の場合:

```bash
security find-certificate -a -c Netskope /Library/Keychains/System.keychain | head
```

エントリが 0 件の場合は、プロキシ Agent (Netskope Client など) の再インストールか、情シスに連絡してください。

MITM の有無は以下で確認できます。

```bash
echo | openssl s_client -connect api.openai.com:443 2>/dev/null \
  | openssl x509 -noout -issuer
```

`issuer` が `Netskope` / 自社名なら MITM 経由、`Google Trust Services` など公的 CA ならそのホストは bypass 対象です。

## 初回 commit

```bash
git add -A
git commit -m "ブレインの初期スコープを設定"
```

GitHub を使う場合は push します。

## サーバーを起動する

開発時:

```bash
mise run serve
```

常駐 service として登録したい場合:

```bash
mise run serve-install
mise run serve-status
```

`serve-install` は OS を自動判定します。macOS では launchd、Linux / WSL では systemd --user を使います。
詳しい常駐運用は [server-management.md](server-management.md) を参照してください。

`BRAIN_PORT` は `scaffold-brain` 時点で空き port が自動割り当て済みです (前節参照)。
衝突した場合は `mise run serve-status` が占有プロセスの pid と cwd を表示します。
必要に応じて `.env` を編集してから `mise run serve-restart` を実行してください。

VPS で root 管理の system service として運用する場合は、`sudo ./deploy/setup.sh <install-dir>` で
systemd unit を作り、`systemctl start/restart/status <service-name>` を使います。

## 次にやること

1. `raw/notes/` に最初のメモを置く、または `mise run clone-repo owner/repo` で repo を取得する。
2. Claude Code / Codex で `ingest raw/...` を実行する。
3. `mise run index` で検索 index を更新する。
4. `query` で wiki に質問する。

`raw/repos/` は gitignored ですが、clone した repo は `repos.json` に記録されます。
別 PC で同じ brain を触る場合は `git pull` の後に `mise run update-repos` を実行すると
マニフェストに基づいて `raw/repos/` 配下を再構築できます。

詳細は [knowledge-ingest.md](knowledge-ingest.md) と [search.md](search.md) を参照してください。

## template からの更新を取り込む準備

この instance は `twin-layer-brain-template` からコピーされています。
template 側で `compiler/` / `server/` / `.agents/skills/` / `mise/tasks/` / `docs/` などが更新されたとき、自動では反映されません。
後から差分を取り込めるように、**初回セットアップ時に一度だけ** template を remote として登録しておきます。

前提:

1. この instance が git 管理下にあること (`git init` 済み)
2. 少なくとも 1 件は commit が打たれていること (「初回 commit」節で実施済み)
3. template repo の URL が分かること (GitHub か、別の git host / ローカル path)

`diff-template` は `origin` とは独立です。
ローカル完結で運用していて `origin` を登録していない instance でも、`template` だけ登録すれば機能します。

```bash
git remote add template git@github.com:<owner>/twin-layer-brain-template.git
```

登録後は、必要なタイミングで差分を確認したり一括取り込みできます。

```bash
mise run diff-template          # 変更ファイル一覧 (既定)
mise run diff-template --diff   # 差分の中身まで表示
mise run diff-template --apply  # 差分表示 → 確認 → 一括上書き
```

`--apply` は差分の中身を全件見せた上で確認プロンプトを出します。独自に編集した箇所があれば目視で気付けます。
一部だけ反映したい場合は `git checkout template/main -- <path>` を個別に使います。
運用手順の詳細（ファイル種別ごとの扱い、取り込み後のテスト実行など）は [template-operation.md](template-operation.md) の「変更を instance に反映する」節を参照してください。

> remote を登録していない状態で `mise run diff-template` を実行すると、登録方法を案内するエラーが出て終了します。
