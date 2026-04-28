# Brain Instance のセットアップ

このファイルは、`twin-layer-brain-template` をコピーして、作業領域やプロジェクト
ごとの brain instance を作る手順です。

## 前提

- 1 brain = 1 作業領域または 1 トピック
- 複数プロジェクトを扱う場合は、PC 上にコピーを複数置く
- 公開 / 非公開の境界は repo 単位で分ける
- `raw/` と `wiki/` が正本、`index/` は再生成可能な派生物

## ローカルコピーで作る

```bash
mkdir -p ~/programs/brains
cp -r ~/programs/brains/twin-layer-brain-template \
  ~/programs/brains/twin-layer-brain-<topic>
cd ~/programs/brains/twin-layer-brain-<topic>
rm -rf .git
git init
```

## GitHub template repo から作る

```bash
gh repo create <owner>/twin-layer-brain-<topic> --private \
  --template=<owner>/twin-layer-brain-template
git -C ~/programs/brains clone git@github.com:<owner>/twin-layer-brain-<topic>.git
cd ~/programs/brains/twin-layer-brain-<topic>
```

## 依存を入れる

```bash
mise install
uv sync
pnpm install
```

`mise` が Python / Node / uv / pnpm / rumdl などを揃えます。

## instance を空の brain として初期化する

```bash
mise run scaffold-brain
mise run init
```

`scaffold-brain` は inherited content を消し、`wiki/index.md` と `wiki/log.md` を
初期化します。`init` は必要ディレクトリを作り、依存同期と `kc index` を実行します。

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

必要に応じて `.env.example` をコピーします。REST API や Chrome extension を使う場合は、
`reset-token` で `BRAIN_API_TOKEN` を作成します。

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
同じマシンに複数 instance を置く場合は、`.env` の `BRAIN_PORT` を instance ごとに変えてください。
詳しい常駐運用は [server-management.md](server-management.md) を参照してください。

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
