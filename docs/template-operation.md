# Template Repo の運用

このファイルは、コピー元である `twin-layer-brain-template` 自体を保守するための
手順です。プロジェクトや作業領域ごとの知識運用は
[instance-setup.md](instance-setup.md) 以降を参照してください。

## template repo の役割

template repo は、複数の brain instance が共有する土台です。

- LLM agent の規約: `CLAUDE.md`, `AGENTS.md`
- Skill: `.agents/skills/{ingest,query,lint,sublime,dive}/`
- Layer 1 実装: `compiler/`
- API / MCP: `server/`
- デプロイ補助: `deploy/`
- 定型タスク: `mise.toml`, `mise/tasks/*.sh`
- 人間向けドキュメント: `README.md`, `docs/`

template repo には、実運用の知識を入れません。`raw/` と `wiki/` は skeleton として
保ちます。

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
uv run kc index
uv run kc search "test"
```

## scaffold-brain は通常実行しない

`mise run scaffold-brain` は、コピー後の brain instance を空にするためのタスクです。
template repo のディレクトリ名が `twin-layer-brain-template` の場合は安全装置で
拒否されます。

template 自体を意図的に初期化する場合だけ、理由を確認してから実行します。

```bash
FORCE=1 mise run scaffold-brain
```

通常は使いません。

## 変更を instance に反映する

template を更新しても、既にコピー済みの brain instance には自動反映されません。
反映方法は運用方針次第です。

- 小さなドキュメント修正: 必要なファイルだけ手で取り込む
- skill / schema 修正: instance 側の `CLAUDE.md`, `AGENTS.md`,
  `.agents/skills/` も差分確認して取り込む
- `compiler/` / `server/` 修正: instance 側で merge するか、新しい template から
  作り直す

作業領域ごとの知識は instance 側の `raw/` / `wiki/` にだけ置きます。template 側に
実データを戻さないでください。
