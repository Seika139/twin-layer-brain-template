# Wiki Operations

LLM Wiki 側の主な操作は 5 つです。

| 操作 | 使う場面 | 主な出力 |
|---|---|---|
| `ingest` | 新しいソースを取り込む | `wiki/sources/` と関連ページ更新 |
| `query` | wiki に質問する | チャット回答、必要なら analysis / canonical page |
| `sublime` | 散在する知見を恒久ページへ昇華する | `wiki/topics/` など |
| `dive` | `raw/` を直接深掘りする | file:line citation 付き回答 |
| `lint` | wiki の健康診断をする | 5 セクションの診断 |

## Query

```text
> Karpathy の LLM Wiki と RAG の違いは？
> このプロジェクトで認証に関係する設計メモは？
```

query は `wiki/index.md` を入口にして関連ページを読みます。必要なら Layer 1 の
SQLite 検索を候補絞り込みに使います。

保存に値する回答は、以下のどちらかにします。

- `wiki/analyses/`: 速い snapshot。gitignored、鮮度保証なし。
- `wiki/topics/`, `wiki/concepts/`, `wiki/entities/`: 恒久的な canonical ページ。

## Sublime

```text
> sublime the analysis about rag-vs-wiki into a topic
```

analysis や重複した主張を、canonical な topic / concept / entity に移します。
topic には Core thesis と Direct Citations を置きます。

## Dive

```text
> dive raw/repos/framework の retry 判断を追って
> /dive raw/articles/2026-04-20-rfc-draft.md の error handling を詳しく
```

dive は「wiki では足りない」と分かっている時の例外レーンです。

基本の流れ:

1. 焦点を 1 行で確認する。
2. `wiki/index.md` と既存 source page を短く scan する。
3. `raw/` を階層的に読む。
4. file:line citation で回答する。
5. 保存する場合は通常 `wiki/analyses/` に置く。

恒久事実が見つかった時だけ、ユーザー確認のうえ source / concept / entity を更新します。

## Lint

```text
> lint
```

出力は常に 5 セクションです。

1. Auto-fixable
2. Needs review
3. Missing pages
4. Unsourced claims
5. Follow-up questions

lint は自動修正しません。修正する場合はユーザー判断を挟みます。

## 手動編集

LLM を介さず `wiki/` を直接編集しても構いません。ただし以下を守ります。

1. frontmatter の `updated` を当日にする。
2. 新規ページなら `wiki/index.md` に追加する。
3. `wiki/log.md` に `refactor` entry を追加する。
4. ファイル名変更時は `rg "\\[\\[old-slug\\]\\]" wiki` で参照を直す。
5. 編集後に `mise run index` を実行する。

frontmatter 例:

```yaml
---
title: ページタイトル
type: source | entity | concept | topic | analysis | index | log
created: 2026-04-27
updated: 2026-04-27
sources: []
tags: []
---
```
