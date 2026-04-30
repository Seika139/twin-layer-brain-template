# Template Repo の運用

このファイルは、コピー元である `twin-layer-brain-template` 自体を保守するための手順です。
プロジェクトや作業領域ごとの知識運用は [instance-setup.md](instance-setup.md) 以降を参照してください。

## template repo の役割

template repo は、複数の brain instance が共有する土台です。

- LLM agent の規約: `CLAUDE.md`, `AGENTS.md`
- Skill: `.agents/skills/{ingest,query,lint,sublime,dive}/`
- Layer 1 実装: `compiler/`
- API / MCP: `server/`
- デプロイ補助: `deploy/`
- 定型タスク: `mise.toml`, `mise/tasks/*.sh`
- 人間向けドキュメント: `README.md`, `docs/`

template repo には、実運用の知識を入れません。`raw/` と `wiki/` は skeleton として保ちます。

## template 側で変更してよいもの

通常変更してよいもの:

- ドキュメント
- skill の運用手順
- `compiler/` / `server/` の実装
- `mise` task（長い処理や引数処理は `mise/tasks/*.sh` に置く）
- lint / editor / deploy 設定

注意が必要なもの:

- `CLAUDE.md` / `AGENTS.md` の operation contract
- frontmatter schema
- `wiki/` のディレクトリ構造
- `raw/` と `index/` の所有境界

これらを変える場合は、README と `docs/`、必要なら
[development/architecture.md](../development/architecture.md) も同時に更新します。

## template で実行する確認

変更後の基本確認:

```bash
mise run test
mise run lint --all
```

Markdown を大きく編集した場合:

```bash
mise run format
mise run lint
```

Python / shell script も含めて整えたい場合:

```bash
mise run format --all
mise run lint --all
```

Layer 1 の動作確認:

```bash
mise run index
mise run kc -- search "test"
```

## scaffold-brain は通常実行しない

`mise run scaffold-brain` は、コピー後の brain instance を空にするためのタスクです。
template repo のディレクトリ名が `twin-layer-brain-template` の場合は安全装置で拒否されます。

template 自体を意図的に初期化する場合だけ、理由を確認してから実行します。

```bash
FORCE=1 mise run scaffold-brain
```

通常は使いません。

## 変更を instance に反映する

> この節は **instance 側の repo で作業する**手順です。template repo 内で実行するものではありません。
> instance のセットアップ時に remote 登録だけ済ませる場合は [instance-setup.md](instance-setup.md) の「template からの更新を取り込む準備」節も参照してください。

template を更新しても、既にコピー済みの brain instance には自動反映されません。
template と instance は `cp -r` または `gh repo create --template` で作られるため git history が切れており、単純な merge はできません。

反映は **instance 側から template を remote として取り込んで差分を確認し、ファイル単位で選んで適用する** ワークフローで行います。

### 初回: template remote を登録する

instance の repo で 1 回だけ実行します。

```bash
cd ~/programs/brains/twin-layer-brain-<topic>
git remote add template git@github.com:<owner>/twin-layer-brain-template.git
```

remote 名は `template` を既定にしています。

### 差分を見る

`mise run diff-template` が template remote から fetch し、自 instance との差分を表示します。自動で merge はしません。

```bash
mise run diff-template          # 変更のあったファイル一覧 (既定)
mise run diff-template --diff   # 差分の中身まで表示
mise run diff-template --all    # raw/ wiki/ repos.json などの instance 固有 path も含める
```

既定では instance 固有の path を除外します。除外対象:

- `raw/**` / `wiki/sources|entities|concepts|topics|analyses/**` / `wiki/index.md` / `wiki/log.md`
- `index/**` / `repos.json` / `.env`

### 一括で取り込む

差分をすべて template 側に揃えたい場合は `--apply` を使います。
確認プロンプトの前に差分の中身が全件表示されるので、独自に編集した箇所が template に戻ってしまわないか目視で確認できます。

```bash
mise run diff-template --apply         # 差分表示 → 確認 → 一括上書き
mise run diff-template --apply --yes   # 確認をスキップして一括上書き (CI 向け)
```

適用の挙動:

- **M** (両方にあり内容が異なる): template の内容で上書き
- **D** (template のみ存在 = instance で削除済み): template から復元
- **A** (instance のみ存在): **スキップ**。instance 固有の拡張を破壊しないため

`--apply` は `--all` と**排他**です。`--all` は `raw/` / `wiki/` / `repos.json` /
`.env` を比較対象に含めるため、`--apply` と併用すると instance の知識データを
破壊する恐れがあります。`--all` は `--list` / `--diff` でだけ使ってください。

### ファイル単位で取り込む

「全部は要らないが一部だけ反映したい」場合は、差分を見た上で `git checkout` を直接叩きます。`--apply` より細かく制御できます。

```bash
git fetch template main
git checkout template/main -- mise/tasks/update-repos.sh    # 例: 1 ファイルだけ
git checkout template/main -- compiler/ server/             # 例: ディレクトリごと
```

ファイルの種類ごとに扱いが変わります。

- **Infrastructure** (`compiler/` / `server/` / `mise/tasks/` / `.agents/skills/` / `.claude/skills/`):
  基本的に template を信頼して上書きして問題ありません。instance 側で意図的に分岐させていない限り、最新を取り込む判断が素直です。
  `.agents/skills/` と `.claude/skills/` は **同じ内容の 2 コピー** として管理します (以前は symlink でしたが、macOS `cp -r` が symlink を follow して実ファイル化する事故があったため廃止)。`.agents/` が正本で、編集後に `mise run skills -- sync` を走らせて `.claude/` に伝搬させます。`diff-template --apply` は両 tree を一括で上書きするので、取り込み後の追加 sync は不要です。
- **Scope-bearing config** (`CLAUDE.md` / `AGENTS.md` / `README.md` /
  `pyproject.toml` の name・version): instance ごとに書き換え済みの箇所があります。`git diff template/main -- <file>` で部分的に確認し、必要な箇所だけ手で反映してください。
- **Content** (`raw/` / `wiki/` / `repos.json` / `.env`): **触らない**。
  `mise run diff-template` の既定除外もそのためです。

### 取り込み後

反映が大きい場合はテストを走らせて壊れていないか確認します。

```bash
mise run test
mise run lint --all
```

問題なければ commit します。

```bash
git add -A
git commit -m "template の更新を取り込み"
```

作業領域ごとの知識は instance 側の `raw/` / `wiki/` にだけ置きます。template 側に実データを戻さないでください。
