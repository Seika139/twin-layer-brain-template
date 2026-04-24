# GUIDE — twin-layer-brain 利用ガイド

個人用 Second Brain の運用マニュアル。日常的な使い方を**人間の目線**でまとめたもの。LLM 向けのスキーマは `CLAUDE.md` / `AGENTS.md` を参照。

## 目次

1. [このリポジトリは何か](#このリポジトリは何か)
2. [前提と環境](#前提と環境)
3. [Wiki を読む](#wiki-を読む)
4. [質問する（Query）](#質問するquery)
5. [知見を昇華する（Sublime）](#知見を昇華するsublime)
6. [深く調査する（Dive）](#深く調査するdive)
7. [ソースを取り込む（Ingest）](#ソースを取り込むingest)
8. [Wiki を点検する（Lint）](#wiki-を点検するlint)
9. [手動で Wiki を編集する](#手動で-wiki-を編集する)
10. [活用シナリオ集](#活用シナリオ集)
11. [トラブルシューティング](#トラブルシューティング)

---

## このリポジトリは何か

`twin-layer-brain-template` は**個人用の Second Brain**を立ち上げるためのテンプレート。記事・書籍・リポジトリ・自分のメモを LLM に読ませ、相互リンクされた Markdown Wiki として育てていく仕組みに、**SQLite による高速検索層 (Layer 1)** を加えた二層構成。`brain-accelerator_1` の wiki / skill 構造に `second-brain` の FTS5 + MCP + Chrome 拡張連携を統合している。

Karpathy の [LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) を下敷きにしている。RAG との違いは**知識が蓄積する**こと — 同じ質問を繰り返すほどに、LLM は過去の統合結果を読んで答えるため、Wiki が賢くなる。

### 1 トピック = 1 リポジトリ

このブレインが扱う範囲は `README.md` と `CLAUDE.md` の冒頭「Scope」宣言で限定する。別トピックを扱いたくなったらこのリポジトリをテンプレートとして新しいリポジトリを立ち上げる（手順は `README.md` → **Spin up a new brain**）。

境界をリポジトリ単位で物理的に引くことで、公開ブレインと非公開ブレイン、仕事と個人、プロジェクト A と B を `.gitignore` ではなく「別リポジトリ」で分ける。混入事故がそもそも起こらない構造になる。

### ディレクトリ構造（1 層）

| パス | Git | 役割 |
|------|-----|------|
| `raw/notes/` | 追跡 | 自筆メモ、議事録、音声書き起こし。不変。 |
| `raw/articles/` | 追跡 | Web クリップ、PDF。 |
| `raw/assets/` | 追跡 | 画像・図版。 |
| `raw/repos/` | **除外** | `mise run clone-repo` で clone された外部 repo。ネスト `.git` あり。再取得可。 |
| `wiki/index.md` | 追跡 | 全ページの目次（最初に開く）。 |
| `wiki/log.md` | 追跡 | 操作ログ（append-only）。 |
| `wiki/{sources,entities,concepts,topics}/` | 追跡 | 1 ソース / 1 エンティティ / 1 概念 / 1 topic = 1 ファイル。 |
| `wiki/analyses/` | **除外（デフォルト）** | query の回答スナップショット。鮮度保証なし。 |

### ページ型の使い分け (type)

- **`entity`** — 固有物（ツール、人、サービス、プロダクト）。ページはその対象自体について書く。
- **`concept`** — 抽象的パターン・技術・テーマ。複数の entity によってインスタンス化される概念。
- **`topic`** — 複数 source / entity / concept を束ねる**恒久論点**。具体的な thesis を持ち、Core thesis + Direct Citations を含む。`sublime` スキルが主な生産経路。
- **`analysis`** — query snapshot。gitignored、鮮度保証なし。

目安: 同じ主張が 3 ページ以上で繰り返されたら、または dated analysis が de-facto 入口化しつつあったら、`sublime` を使って `topic` 化する。

公開・非公開は**リポジトリ全体の可視性**で決める。`.gitignore` のデフォルトは「どちらでも破綻しない安全側」になっており、private リポジトリで analyses も追跡したければ `/wiki/analyses/` 行を削除する。

---

## 前提と環境

- macOS + VS Code
- [Claude Code](https://claude.ai/code) または [Codex](https://openai.com/codex/) CLI
- [mise](https://mise.jdx.dev/) — `mise run <task>` で定形作業を実行
- Git（リモートはブレインごとに別運用）

### 推奨 VS Code 拡張

`.vscode/extensions.json` に列挙されている拡張を入れると快適：

- **Foam** — `[[wiki-link]]` の解決、バックリンク、graph view
- **Markdown Preview Mermaid** — Mermaid 図の inline プレビュー
- **markdownlint** + **rumdl** — Markdown の linter 2 種（同じ設定を同期）
- **Code Spell Checker** — スペルチェック

### セットアップ

```bash
# このテンプレートから派生ブレインを立てる例
gh repo create Seika139/twin-layer-brain-<topic> --private \
    --template=Seika139/twin-layer-brain-template
mkdir -p ~/programs/brains
git -C ~/programs/brains clone git@github.com:Seika139/twin-layer-brain-<topic>.git
cd ~/programs/brains/twin-layer-brain-<topic>

# ツール・依存をインストール
mise install
uv sync
pnpm install

# VS Code で開く
code .
```

`raw/repos/` と `wiki/analyses/` は `.gitignore` で除外されているので、必要になったら中身を埋める。

---

## Wiki を読む

### VS Code + Foam（推奨）

1. `wiki/index.md` を開く
2. `[[link]]` を `Cmd+Click` でたどる
3. サイドバーの **Foam: Graph** で関連性を可視化

### Obsidian

repo root を Obsidian vault として開けば、Foam と**両対応**で運用できる。`.obsidian/{app,core-plugins,community-plugins}.json` が tracked されており、clone 後に初めて Obsidian を起動すると共有設定が自動で適用される:

- **リンク解決** — `newLinkFormat: relative`, `useMarkdownLinks: false`（Foam の `noteIdentifiers: relative` と同じ解決）
- **添付先** — `attachmentFolderPath: raw/assets`（画像ペーストが自動で `raw/assets/` へ）
- **Daily notes** — 無効（本 repo は `wiki/log.md` が時系列ログ）
- **Graph / Backlinks / Outgoing links / Tag pane / Outline** — core plugin として有効化

推奨する Community plugins（`.obsidian/community-plugins.json` に ID 登録済み、install 自体は user 作業）:

| Plugin | 効能 |
|--------|------|
| **Dataview** | frontmatter クエリで topic / source 一覧を動的生成。`TABLE created, updated FROM "wiki/topics"` 等 |
| **PDF Plus** | `raw/articles/` に置いた PDF の閲覧強化 |
| **Extract PDF Highlights** | PDF ハイライトを markdown 化し `raw/notes/` に手動 ingest 前段で使う |

**Obsidian Linter は入れない**。本 repo の lint は `rumdl` + `markdownlint-cli2` が担当しており、Claude Code 側で edit 後に自動実行される PostToolUse hook が既に動いている。Obsidian Linter を入れると両者で format 判断が衝突する。

ローカルの workspace 状態（`workspace.json`, `hotkeys.json`, `plugins/` 実体, snippets, themes）は `.gitignore` で除外されるので、個人の UI 好みは各人の machine に閉じる。

### モバイル Obsidian (iOS / Android) で開く

`.obsidian/*.json` の共有設定はモバイル Obsidian でもそのまま読まれる。閲覧・リンク追跡・graph view・Dataview / PDF Plus は動作する。ただし **Extract PDF Highlights はデスクトップ専用** なのでモバイルでは自動的にスキップされる（エラーにはならない）。

**同期経路: Git/GitHub 前提**。Obsidian Sync は使わず、本 repo の git 設計と整合させる運用:

| 端末 | 推奨フロー |
|------|-----------|
| **iOS** | **Working Copy** (App Store) で repo を clone → File Provider 機能を有効化 → Obsidian が iOS Files.app 経由で vault として開く。編集前後に Working Copy で手動 `pull` / `commit` / `push` |
| **Android** | **Obsidian Git** community plugin を user 側で install（Tier 1 リストには入れていない）→ vault 内で直接 `pull` / `commit` / `push`。大きな repo では遅いが別アプリ不要 |

モバイル運用の制約:

- **LLM オペレーション（ingest / query / sublime / dive / lint）はデスクトップのみ**。Claude Code / Codex / mise はモバイル非対応なので、モバイルは「閲覧と軽微な編集（frontmatter 修正、`raw/notes/` への追記）」に閉じる
- **`raw/repos/` はモバイルに同期されない**（gitignored）。clone した外部 repo はデスクトップ側にしか存在しない
- **モバイルから commit する時は必ず先に `pull`**。モバイル編集を push した後は、次回デスクトップで ingest する前に `mise run lint` を通す
- **AppleDouble ファイル**（`._foo`）が iCloud / SMB / exFAT 経由で混入することがある。`.gitignore` で除外してあるので push には乗らないが、モバイル同期後に `git status` で確認推奨

### 典型的な非対称運用

karpathy pattern の精神そのままで、**デスクトップが「書き手」、モバイルが「読み手」**になる:

- デスクトップ: `ingest` / `query` / `sublime` / `dive` / `lint` を走らせて wiki を育てる
- モバイル: 通勤中に `wiki/topics/*.md` と `wiki/concepts/*.md` を読む、気づいたら `raw/notes/` に音声メモの書き起こしを追加する、Properties パネルで `tags` を微修正する程度

「wiki を育てる」のはデスクトップ、「育てた wiki を消費する」のはモバイル、という分担が自然。

### GitHub / ブラウザ

GitHub 上でも読めるが、`[[wiki-link]]` は GitHub では解決されないため、Foam / Obsidian / VS Code 上で読むのを推奨。

### 読み方のコツ

- **`index.md`** から入る — 全ページを俯瞰できる
- **Sources** は 1 ソース要約（repo・記事 1 本 = 1 ページ）
- **Concepts** は横断的パターン・ワークフロー
- **Entities** は人・サービス・ツール等の固有物
- **Analyses** は query の回答スナップショット（デフォルト gitignored、**鮮度保証なし**）

---

## 質問する（Query）

Claude Code または Codex をこのディレクトリで起動し、普通に質問するだけ。

```text
> Karpathy の LLM Wiki と RAG の違いは？
> Foam と Obsidian の比較して
> 先月取り込んだ記事のうち、CQRS に関連するものを教えて
```

### 回答形式

`CLAUDE.md` の Query 契約に従い、質問の形に応じて：

- **散文** — 既定
- **比較表** — 「X と Y の違いは？」
- **Mermaid 図** — 関係性・フロー
- **決定木** — 「どっちを使うべき？」
- **Marp スライド** — 「このトピックを一通り解説して」

### 回答の保存

「保存に値する」と思った回答は、以下のどちらかに行く先を聞かれる：

- **Analysis（速い・局所的）** — `wiki/analyses/<slug>.md` に書く。デフォルト gitignored なので自分だけが見る。時間が経つと実装とズレる。
- **昇格（遅い・恒久的）** — `wiki/topics/`, `wiki/concepts/`, `wiki/entities/` のいずれかを更新。`wiki/index.md` にも追加される。

> **Analyses の位置づけ:** 分析ページは「その時点の Wiki を元にしたスナップショット」で、鮮度保証ができない。価値ある発見は後述の `sublime` で canonical ページへ昇華させる。

---

## 知見を昇華する（Sublime）

`sublime` は「散在する知見」「鮮度保証がない analysis」を canonical な `topic` / `concept` / `entity` ページに昇華する 4 番目のオペレーション。

```text
> sublime the analysis about rag-vs-wiki into a topic
> sublime: consolidate the sharding claims scattered in framework.md and related pages
```

### 何をするか

1. 対象コンテンツを 3 分類する
   - **横断恒久知識** → `wiki/topics/<slug>.md` を新規 or 更新
   - **source/entity 固有の恒久事実** → 該当ページに還流（既に書かれていれば no-op）
   - **時点依存・導出履歴** → 元 analysis に残す

2. topic ページには **Core thesis（2–5 行の恒久主張）** と **Direct Citations**（wiki-link と raw-file link を直接並記して検証を 1 hop で済ませる）を必ず書く

3. 元 analysis は削除せず、冒頭に `> **Canonical version:** [[topics/<slug>]]` を追記して導出履歴として残す

4. `wiki/index.md` の代表導線を日付付き analysis → canonical page へ付け替える

### いつ使うか

- query で作った analysis が繰り返し参照される手応えがあった時
- 同じ主張が 3 ページ以上で重複している兆候を lint が「Sublime candidates」で報告した時
- dated ページ（`2026-04-23-foo.md`）が de-facto 入口化している時

---

## 深く調査する（Dive）

`dive` は「wiki では足りない」と**自分で分かっている時**に使う例外レーン。query が wiki 優先なのに対し、dive は `raw/` を最初から読みに行く。

```text
> dive raw/repos/framework の TransactionAwareRetry で何を retry するか
> /dive raw/articles/2026-04-20-rfc-draft.md の error handling 提案を詳しく
> 昨日 update した raw/repos/sso-client の PKCE まわりを読んで
```

### 何をするか

1. **焦点を 1 行で確認** — 「どこの何を調べるか」を LLM が言語化してユーザに確認
2. **wiki 側を 60 秒 scan** — 既知事実の再発見を避けるため、`wiki/index.md` と該当 source ページの Summary / Confirmed Facts だけ目を通す
3. **raw/ を階層的に読む** — anchor（起点ファイル）→ neighbours（呼び出し元・呼び出し先）→ cross-cutting（config、auth、middleware）の順。焦点質問に答えられる citation が揃ったら止まる
4. **file:line citation で回答** — `[descriptor](../../raw/repos/<repo>/path/to/file.ext)` 形式で行番号まで指す
5. **保存はデフォルトで analysis** — `wiki/analyses/YYYY-MM-DD-dive-<slug>.md` に自動保存（`type: analysis` + `dive_focus:` / `dive_target:` frontmatter 付き、gitignored）。**恒久事実が見つかった時だけ** ユーザ確認のうえ source ページ直接更新、「保存不要」と言われたら chat のみ

### いつ使うか

- wiki の要約が薄い・該当エンティティページが未整備と分かっている時
- `mise run update-repos` 直後に、変更が入った repo の挙動を確認したい時
- 実装の特定関数・クラス・設定を line 単位で追いたい時

### query との違い

| 目的 | 使うスキル |
|------|-----------|
| wiki で答えられる質問 | **query** |
| wiki 要約では不十分と自分で判断済み | **dive** |
| 新しいソースを wiki に取り込みたい | **ingest** |
| 散在する知見を canonical に昇華したい | **sublime** |

dive の出力を sublime で topic に昇華する連携も可能。同じ target に対する dive が重なり始めたら「wiki に正本を作るタイミング」のシグナル。

---

## ソースを取り込む（Ingest）

### GitHub リポジトリ

```bash
# 1. clone（mise タスクが raw/repos/ に入れる）
mise run clone-repo cyg-idpf/wiki

# 2. Claude Code で取り込み指示
> ingest raw/repos/wiki
```

### 記事・PDF

```bash
# 1. raw/articles/ に置く（Markdown 推奨）
cp ~/Downloads/interesting-paper.pdf raw/articles/

# 2. 取り込み指示
> ingest raw/articles/interesting-paper.pdf
```

### 自分のメモ

```bash
# 1. raw/notes/ に Markdown で書く（日付スラグ形式）
vim raw/notes/2026-04-21-idea-foo.md

# 2. 取り込み指示
> ingest raw/notes/2026-04-21-idea-foo.md
```

### Ingest 処理で何が起こるか

1. ソースを通読
2. 要点 2–3 個をチャットで提示（書く前に合意を取る）
3. `wiki/sources/YYYY-MM-DD-<slug>.md` 作成
4. 関連する `entities/` / `concepts/` を更新 or 新規作成（**1 ソースで 10〜15 ページ触る想定**）
5. 矛盾発見時は「Superseded by」注記を付けて両方残す
6. `wiki/index.md` を更新
7. `wiki/log.md` に追記

### 更新反映（再 ingest）

元リポジトリが更新された場合：

```bash
mise run update-repos                     # 全 repo を git pull
> 変更があった repo のうち <repo-name> を再 ingest して
```

---

## Wiki を点検する（Lint）

```text
> lint
```

5 セクション固定の出力：

1. **Auto-fixable** — リンク切れ、frontmatter ドリフト
2. **Needs review** — 矛盾、古い情報、新ソースと食い違うページ
3. **Missing pages** — 3 回以上言及されているが専用ページがない概念・エンティティ
4. **Unsourced claims** — 出典のない主張
5. **Follow-up questions** — 深掘りすべき問い、取り込むべき追加ソース候補

**自動修正しない**。ユーザが一件ずつ判断する。

### 推奨実行タイミング

- 10 件程度 ingest した後
- 月 1 回の定期メンテ
- 「情報が古い気がする」と感じた時

---

## 手動で Wiki を編集する

LLM を介さず直接編集することも可能。以下のルールを守る：

1. frontmatter の `updated` を当日日付に変更
2. 新規ページなら `wiki/index.md` に 1 行追加
3. `wiki/log.md` に refactor エントリを追加：

   ```markdown
   ## [YYYY-MM-DD] refactor | <要約>

   - 手動で <理由> により <何を> した
   ```

4. ファイル名を変更したら参照元も修正（`rg "\[\[old-slug\]\]" wiki`）
5. 既存ページ更新を優先 — 同じトピックの新規ページは作らない

### frontmatter テンプレート

```yaml
---
title: ページタイトル（日本語可）
type: source | concept | entity | analysis
created: 2026-04-21
updated: 2026-04-21
sources: []
tags: []
---
```

---

## 活用シナリオ集

### シナリオ 1: 技術記事を読んで知識として定着させる

```bash
# 1. Web クリッパーで Markdown 保存
cp ~/Downloads/foo-article.md raw/articles/

# 2. 取り込み
> ingest raw/articles/foo-article.md

# LLM は sources/ に要約、関連 entities / concepts を更新
```

### シナリオ 2: 興味のある repo を分析

```bash
mise run clone-repo karpathy/nanoGPT
> ingest raw/repos/nanoGPT
```

大規模 repo は `CLAUDE.md` の **Large codebase ingest strategy** に従って階層的に読む。

### シナリオ 3: 横断的な問いを投げる

```text
> ここ 3 ヶ月で取り込んだソースのうち、「分散システムでの整合性」に触れているものは？
```

`wiki/index.md` + 関連 `concepts/` ページを読んで合成。

### シナリオ 4: 自分のアイデアを育てる

```bash
# 1. 思いつきを raw/notes/ に書く
vim raw/notes/2026-04-21-idea-llm-agents.md

# 2. LLM に取り込ませて Wiki と接続
> ingest raw/notes/2026-04-21-idea-llm-agents.md

# LLM は既存 Wiki との関連を見つけて sources/ + 関連 concepts を更新
# → 既存の知識と自分のアイデアがリンクされる
```

### シナリオ 5: 何を次に読むべきか LLM に聞く

```text
> lint して、follow-up questions セクションで次に取り込むべきソース候補を挙げて
```

### シナリオ 6: 新しいブレインを立ち上げる

別トピック（新プロジェクト、新領域）を扱いたくなったら、このリポジトリをテンプレートとしてコピーして新ブレインを作る。詳細は `README.md` → **Spin up a new brain**。

---

## トラブルシューティング

### Q. VS Code で `[[wiki-link]]` が解決されない

Foam 拡張が入っていないか、`.vscode/settings.json` の `foam.files.noteIdentifiers: relative` が効いていない可能性。VS Code を reload。

### Q. `raw/repos/` に clone した repo が git に出てくる

`.gitignore` の `/raw/repos/` 行が効いているか確認。もし既に追跡済みなら `git rm --cached -r raw/repos/` で追跡解除。

### Q. `wiki/analyses/` を git 管理したい

private リポジトリ運用なら `.gitignore` から `/wiki/analyses/` 行を削除すれば追跡対象になる。ただし「鮮度保証なし」の位置づけは変わらないため、重要な発見は `wiki/concepts/` への昇格を優先する。

### Q. Lint が「矛盾あり」と言うが、どちらが正しいか分からない

双方の citation を辿って元ソースに当たる。新しい方 / より権威あるソースに従い、古い方に `> **Superseded by [[source]]**` を追記。

### Q. `wiki/` を LLM が上書きしてしまった

Git の履歴から復元：

```bash
git log --oneline wiki/
git diff HEAD~1 wiki/<file>.md
git checkout HEAD~1 -- wiki/<file>.md
```

`CLAUDE.md` を変更して再発防止（例: そのページを「更新禁止」とマーク）。

### Q. `CLAUDE.md` / `AGENTS.md` を変更して良いか

**スキーマの中核ルール（operation contract、lint の 5 セクション構成）は変えない**。用語・表現・例示は自由に更新してよいが、変更は `log.md` に refactor として記録する。ブレイン固有の scope 宣言（冒頭「Scope」）は各ブレインで書き換える前提。
