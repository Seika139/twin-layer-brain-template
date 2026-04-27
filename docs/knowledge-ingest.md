# 知識の取得と Ingest

このファイルは、ソースを `raw/` に置き、LLM Wiki に取り込む流れを説明します。

## 置き場所

| パス | 用途 | Git |
|---|---|---|
| `raw/notes/` | 自分のメモ、議事録、文字起こし | tracked |
| `raw/articles/` | Web clip、PDF、論文、記事 | tracked |
| `raw/assets/` | 画像、図版 | tracked |
| `raw/repos/` | 外部 repo の clone | ignored |

`raw/notes/` は人間所有の不変ソースです。LLM は原則として編集しません。

## 自分のメモを入れる

```bash
vim raw/notes/2026-04-27-topic-note.md
```

その後、Claude Code / Codex で:

```text
> ingest raw/notes/2026-04-27-topic-note.md
```

## 記事や PDF を入れる

```bash
cp ~/Downloads/article.md raw/articles/
cp ~/Downloads/paper.pdf raw/articles/
```

その後:

```text
> ingest raw/articles/article.md
```

PDF は LLM が読める形に変換してから置く方が安定します。Obsidian の PDF 系 plugin
や Web clipper を前処理として使えます。

## GitHub repo を取得する

```bash
mise run clone-repo owner/repo
```

branch を指定する場合:

```bash
mise run clone-repo owner/repo main
```

取得先は `raw/repos/<repo>` です。`raw/repos/` は gitignored なので、親 brain repo
には commit されません。

取り込み:

```text
> ingest raw/repos/<repo>
```

大規模 repo の ingest は、`CLAUDE.md` の Large codebase ingest strategy に従って
inventory から entry point、主要 module、横断関心事の順で読みます。

## Ingest で起きること

`ingest` skill の標準処理:

1. ソースを読む。
2. 2〜3 個の要点と、更新予定ページをチャットで提示する。
3. ユーザー確認後、`wiki/sources/YYYY-MM-DD-<slug>.md` を作る。
4. 関連する `wiki/entities/`, `wiki/concepts/`, `wiki/topics/` を更新する。
5. 矛盾は消さずに `Superseded by` や `Contradiction` として残す。
6. `wiki/index.md` を更新する。
7. `wiki/log.md` に追記する。

重要なのは 4 です。source page だけを作って終わると compound しません。実質的な
ソースなら、既存概念や entity にも波及させます。

## 再 ingest

clone 済み repo を更新する:

```bash
mise run update-repos
```

出力に変更があった repo が出たら:

```text
> 変更があった raw/repos/<repo> を再 ingest して
```

## Web clip API

server 起動中は `POST /api/clip` で Web ページ内容を `raw/articles/` に保存できます。
`BRAIN_API_TOKEN` の Bearer token が必要です。LLM provider key があれば要約と tag 付けも
行います。LLM が使えない場合は、ブラウザや client から送られた本文を機械的に保存します。
Chrome extension で「AI 要約・タグ生成を試す」を無効にした場合も、LLM を呼ばずに機械的に保存します。
保存された `raw/articles/*.md` の frontmatter には `capture_mode`, `llm_used`, `llm_requested`
が残るため、後から `.md` を見ても AI API が使われたか判定できます。

Web clip の保存は URL 単位です。Chrome extension はページの `<link rel="canonical">` を
抽出し、server は canonical URL があればそれを同一ページ判定に使います。同じ URL を再 clip
すると同じ `raw/articles/*.md` を更新し、別 URL であれば title が同じでも別ファイルにします。
これは、検索や ingest 時に同じページの重複を増やさず、別ページの同名タイトル衝突も避けるためです。

```bash
mise run serve
```

API は `server/routes/clip.py` に実装されています。保存後に `rebuild_index()` が
呼ばれます。

Chrome から保存する場合は [chrome-extension.md](chrome-extension.md) を参照してください。

## index 更新

Markdown を直接編集した後は、Layer 1 の検索 index を更新します。

```bash
uv run kc index
```

API 経由の note 作成・更新、Web clip、GitHub webhook は `rebuild_index()` を呼びます。
一方で、エディタや LLM が Markdown を直接編集した場合、自動ファイル監視は現在
ありません。検索結果を信用する前に `uv run kc index` を実行してください。
