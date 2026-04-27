# Karpathy LLM Wiki Pattern (要点)

参照: <https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>

## Core Idea

- RAG の都度再発見ではなく、LLM が永続 wiki を育てる。
- source を追加するたびに wiki を更新し、知識を累積させる。

## Architecture (brain-accelerator での対応)

- **Raw sources** — 一次ソース。immutable。`raw/notes/` / `raw/articles/` / `raw/assets/` / `raw/repos/`。
- **Wiki** — LLM が編集する markdown 知識ベース。`wiki/{sources,entities,concepts,topics}/`。
- **Schema** — 運用規約。`CLAUDE.md` / `AGENTS.md`。

## Operations

- **ingest** — source 要約、関連ページ更新、index/log 更新。
- **query** — index から探索し回答を合成。再利用価値のある回答は保存。
- **sublime** — 散在する知見や snapshot 止まりの analysis を canonical な topic / concept / entity へ昇華し、事実を source-summary / entity に還流する。
- **dive** — wiki が silent / stale / 更新遅れの時に raw/ を直接深く読み、特定の問いに答える例外レーン。
- **lint** — 矛盾、陳腐化、孤立、欠落リンク、データギャップを点検。

## Page types

- `source` — 1 ソース要約。immutable な `raw/` への citation を持つ。
- `entity` — 固有物（ツール、人、サービス）。
- `concept` — 抽象的パターン・テーマ。
- `topic` — 複数 source / entity / concept を束ねる横断恒久論点。Core thesis と Direct Citations を持つのが特徴。
- `analysis` — query / dive snapshot。gitignored、鮮度保証なし。
- `index`, `log` — 予約ページ。

## Sublime と Dive の位置づけ

karpathy gist には明示されていない拡張オペレーション。

- **Sublime** — llm-wiki が先行導入した knowledge promotion レーン。query で生まれた valuable analysis、複数 page に分散している recurring claim、dated page が de-facto 入口化する現象に対処する。
- **Dive** — 本 repo 独自の exception レーン。wiki 優先の原則を保ちつつ、user が「wiki では不十分」と判断している時 or 最新 repo 更新を直接読みたい時の明示的な抜け道。line-level citation が契約。
- **Direct Citations** — topic ページに wiki-link と raw-file link を並べて置き、thesis の検証を 1 hop で済ませる。

## Indexing and Logging

- `wiki/index.md` — 内容中心のカタログ。Topics / Entities / Concepts / Sources のセクションを持つ。
- `wiki/log.md` — 時系列の append-only 記録。
- ログ見出し: `## [YYYY-MM-DD] <operation> | <title>` （operation: ingest / query / sublime / dive / lint / refactor）

## brain-accelerator 固有の拡張

- **1 トピック = 1 リポジトリ** — 公開/非公開境界、schema 境界、機密境界はリポジトリ単位で引く。
- **回答の 2 つの行き先** — `wiki/analyses/` (snapshot, デフォルト gitignored) と `wiki/{topics,concepts,entities}/` への昇華 (canonical, tracked)。
- **固定 5 セクション lint** — Auto-fixable / Needs review / Missing pages / Unsourced claims / Follow-up questions。
- **gitignore デフォルト** — `raw/repos/` (nested .git・再取得可) と `wiki/analyses/` (スナップショット・鮮度保証なし) のみ除外。他は全て tracked。
