---
title: twin-layer-brain のアーキテクチャ本質
updated: 2026-04-25
---

時間が経っても変わらない設計思想を記録する。具体的な実装は `compiler/` `server/`
に、運用手順は `README.md` / `docs/` に書かれているが、「**なぜそうなのか**」
の根本は本ファイルに集約する。

本ファイルは `twin-layer-brain-template` の不変な設計論であり、派生インスタンス
(`twin-layer-brain-<topic>`) も同じ思想を継承する。インスタンス固有の判断は
各 repo の `development/decisions/` に記録する。

## 正本と派生物

twin-layer-brain は「**Markdown + Git が正本、それ以外は全て派生物**」という
原則を貫く。

```text
┌───────── 正本 (source of truth) ─────────┐
│  raw/ (人間所有)                          │
│    notes / articles / assets / repos     │
│  wiki/ (LLM 所有)                         │
│    index.md / log.md / sources / ...     │
│  ↓ git で追跡、GitHub で管理              │
└──────────────────────────────────────────┘
                  ↓ 生成
┌──────── 派生物 (derived) ───────────────┐
│  index/knowledge.db (SQLite FTS5 + vec)  │
│  ↓ `kc index` で再生成可能、Git 管理外    │
└──────────────────────────────────────────┘
```

### なぜこの分離が重要か

- **DB が壊れても正本は無事**: SQLite が破損しても `kc index` で作り直せる。
- **外部ツールでも読める**: Markdown はエディタ / Foam / Obsidian でそのまま読める。
- **バージョン管理が自然**: 知識の変遷が `git log` で辿れる。
- **LLM が読み書きしやすい**: 人間用のフォーマットがそのまま LLM にも適する。

## compound（複利合成）とは何か

[Karpathy の LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
の核心概念。同じトピックについて新しい情報が入るたびに、**既存の理解が更新されて
深化する**性質。

### compound しない例

```text
Article A を raw/ に保存 → wiki の既存ページは変わらず
Article B を raw/ に保存 → wiki の既存ページは変わらず
...
N 件溜まる → ソースは増えるが理解は育たない (バラバラな情報が分散)
```

検索精度は上がるが、「理解」そのものは育たない。これは RAG 型のシステムの限界。

### compound する例 (ingest skill の契約)

```text
Article A を ingest → sources/A.md 作成 + concepts/<topic>.md を更新
Article B を ingest → sources/B.md 作成 + concepts/<topic>.md を再更新
                      (前回の内容に B を統合、矛盾は Superseded by で残す)
```

N 件 ingest するほど `concepts/<topic>.md` や `topics/<theme>.md` が賢くなる。
これが compound。

### compound はデータ構造では実現しない

関係テーブルを SQL に追加したり、グラフ可視化を作っても、上記の compound は
起きない。compound を生むのは LLM の**規律**:

- 「1 ソース取り込み = 10〜15 ページ更新」という数量規範
- 「矛盾は両方残して `Superseded by` を付ける」という履歴規範
- 「重複は #1 failure mode」という guardrail

これらは `CLAUDE.md` / skill contract に書かれた**振る舞いの制約**であって、
SQL スキーマでは表現できない。

## 二層アーキテクチャ

twin-layer-brain は同じ Markdown 正本に対して**2 つの検索能力の層**を提供する:

| 層 | 実装 | 強み | 用途 |
|----|------|------|------|
| **Layer 1** | SQLite (FTS5 + sqlite-vec) | 網羅性、低レイテンシ | 「X について何か書いたっけ」 |
| **Layer 2** | LLM が育てる `[[wiki-link]]` グラフ | 合成知識、解釈の深さ | 「X と Y の関係を整理して」 |

`layer` は**物理ディレクトリの層ではなく capability の層**。両層とも同じ Markdown
を対象に、違うアクセスパターンを提供する。ディレクトリは `raw/` + `wiki/` の 1 層。

### 単方向データフロー

```text
          正本 (Markdown: raw/ + wiki/)
               │
               ├── 書き込み
               │      └── `kc index` / API 経由の rebuild
               │             ↓
               └── 参照 ←── 検索補助 ─── SQLite
```

- **書き込みは Markdown 側のみ**: LLM / 人間が Markdown を書く。SQL への直接
  書き込み API は公開しない。
- **再索引は明示または API 経由**: API 経由の作成・更新・clip・webhook では
  `rebuild_index()` が走る。Markdown を直接編集した場合は `kc index` で再生成する。
- **検索補助は双方向**: query 時に LLM が SQL 検索結果を**ヒント**として受け取り、
  Markdown を読みに行く。

この原則を守れば「両層を同期更新する複雑さ」は発生しない。両層は独立ではなく、
**SQL は Markdown の派生物**として扱う。

### 5 operation と 2 層の協調

| Skill | 主な Layer | Layer 1 の補助 |
|-------|-----------|---------------|
| `ingest` | Layer 2 (raw 読取 → wiki 書込) | 書込後に `kc index` で再索引 |
| `query` | Layer 2 (wiki/index.md → page) | **冒頭で FTS / embedding 検索、候補を絞り込む** |
| `sublime` | Layer 2 (analyses → topic) | 再索引 |
| `dive` | Layer 2 (raw 直読) | 候補 raw ファイルの FTS 検索 |
| `lint` | Layer 2 (wiki 通読) | orphan 検出、被参照数集計 |

### MCP のツール構成 (2 階層)

```text
┌─────── Skill 発動 (高レベル) ────────┐
│  ingest | query | sublime | dive | lint │
│  (`/` コマンドで Claude Code が発動)    │
└──────────────────┬──────────────────┘
                   │ 内部で委譲
                   ▼
┌─────── Layer 1 直接アクセス (低レベル) ────┐
│  search_notes | search_similar_notes |    │
│  read_note | suggest_related_notes |      │
│  create_note | append_note | rebuild_index│
└───────────────────────────────────────────┘
```

外部からは両階層とも呼べる。LLM は状況に応じて使い分ける (単純な検索は Layer 1
直叩き、複雑な問いは skill)。

## 設計の階層

```text
┌──────────────────────────────────────┐
│ 規律層 (CLAUDE.md / skill contract)  │ ← compound を生む
├──────────────────────────────────────┤
│ データ層 (Markdown + frontmatter)     │ ← 正本
├──────────────────────────────────────┤
│ 索引層 (SQLite FTS5 + embedding)      │ ← 派生物、検索高速化
├──────────────────────────────────────┤
│ API 層 (MCP / REST / CLI)             │ ← アクセス経路
└──────────────────────────────────────┘
```

**どの層の変更が "本質的" か**:

- **規律層**を変えると compound の仕方が変わる (最も影響大)。
- **データ層**の schema を変えると既存コンテンツの互換性に影響。
- **索引層**は作り直せるので気軽に変えられる。
- **API 層**はアクセス経路の追加 / 削除で、上の層には波及しにくい。

## 境界

### twin-layer-brain 個別インスタンスの責務

- そのブレインの scope (`README.md` / `CLAUDE.md` 冒頭で宣言) 内の知識を扱う。
- 自分の `raw/` `wiki/` `index/` を self-contained に持ち、他ブレインに依存しない。
- Layer 1 の MCP / REST は**そのブレイン用のみ**に公開する (per-brain port)。

### twin-layer-brain の非責務 (= 別ブレインで)

- 異なるトピックの知識 → 別 repo (別インスタンス)。混在は graph 密度を下げる。
- ブレイン横断の検索 → 将来的に `brain-hub` 的 dispatcher を建てる (投機的には
  作らない。3〜5 ブレイン溜まってから判断)。

## 参考

- [Karpathy, "LLM Wiki"](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
  — compound の元ネタ。
- `CLAUDE.md` — LLM agent 向けの運用規約 (本ファイルの実装版)。
- `AGENTS.md` — Codex 向けの同等物。
- 上流: [`brain-accelerator_1`](https://github.com/Seika139/brain-accelerator)
  (Layer 2 の規律の原典), [`second-brain`](https://github.com/Seika139/second-brain)
  (Layer 1 インフラの原典)。
