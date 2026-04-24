# development/

設計判断・議論の経緯・方針をまとめるディレクトリ。

`docs/` が「運用者向けの手順書」なのに対し、`development/` は「なぜそう作ったか」
を記録する。コードや Issue では捕捉しきれない以下の情報を保存する:

- アーキテクチャの本質と設計思想（時間によって変わらないもの）
- 戦略的判断の ADR（Architecture Decision Record）
- セッションログ（Claude / Codex 等と議論した経緯）

## 構成

```text
development/
├── README.md             # このファイル
├── architecture.md       # 時間不変の設計思想
├── decisions/            # 日付付き ADR (本ブレインの重要判断)
│   └── YYYY-MM-DD-<slug>.md
└── sessions/             # 日付付き議論ログ
    └── YYYY-MM-DD-<slug>.md
```

## 使い分け

| ファイル種別 | 用途 | 具体例 |
|---|---|---|
| `architecture.md` | リポジトリの本質・役割・境界 | 「Markdown が正本、SQLite は派生物」 |
| `decisions/` | 重要な分岐点の判断記録 | 「この機能を採用 / 却下した理由」 |
| `sessions/` | 議論の流れや検討した代替案 | 「ある日 AI と議論してこの機能を実装した」 |

## 命名規則

- 日付は `YYYY-MM-DD`
- slug は kebab-case 英語
- タイトルは frontmatter `title:` に日本語で書く（任意）

## このディレクトリを読むべきタイミング

- 新しい AI セッション / 開発者がプロジェクトに触れる時 → `architecture.md`
- 「なぜこの設計？」と疑問が出た時 → `decisions/` を slug で検索
- 実装中に「あの時どう決めたっけ」と思い出したい時 → `sessions/`

## テンプレートからの派生ブレインの場合

`twin-layer-brain-template` から `mise run scaffold-brain` で派生したブレインは、
template の `architecture.md` (本 repo の不変な設計論) を継承しつつ、自分の
`decisions/` と `sessions/` に固有の判断・履歴を書き溜めていく。
