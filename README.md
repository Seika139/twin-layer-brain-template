# twin-layer-brain-template

Template for personal Second Brain repos that combine two search layers:

- **Layer 1 (SQLite)** — FTS5 + `sqlite-vec` embedding-based fast search, exposed via MCP, REST API, `kc` CLI, and a Chrome extension.
- **Layer 2 (LLM graph)** — LLM-maintained interlinked Markdown wiki following [karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Both layers read from the same Markdown source of truth under `raw/` and `wiki/`. Layer 1 is a derived index (regenerable from Markdown via `kc index`); Layer 2 is where LLM-synthesized understanding compounds over time.

This template derives from two upstream projects:

- [`brain-accelerator_1`](https://github.com/Seika139/brain-accelerator) — template pattern, skill packages, wiki structure, Obsidian integration.
- [`second-brain`](https://github.com/Seika139/second-brain) — Python FTS5 + embedding infra, MCP server, Chrome extension.

> **Scope of this brain:** <ここにこのブレインが扱う範囲を 1 行で書き換える>
>
> One brain = one topic. For a different topic, spin up another brain from this template (see below).

## Why two layers

| | Layer 1 (SQLite) | Layer 2 (LLM wiki) |
|---|---|---|
| 得意 | 素早い検索、具体的な語の突合 | 既存知識の再解釈・統合、compound |
| 書き込み | 自動（Markdown 変更で再索引） | LLM / 人間が Markdown を直接 |
| 参照先 | 全 Markdown | `wiki/index.md` 起点のグラフ |
| 典型用途 | 「X について何か書いたっけ」 | 「X と Y の関係を整理して」 |

Single-direction data flow: **writes happen on Markdown, SQL re-indexes automatically**. You never write to SQL directly.

## Why one brain per topic

- **Dense wiki graph.** `[[wiki-link]]` density comes from keeping the ingested material within a single domain. Mixing unrelated topics produces two weak clusters, not one strong one.
- **Physical confidentiality boundary.** Public wikis and private wikis live in different repositories. There is no in-repo `shared/` vs `local/` split to misjudge — publish / keep-private is decided at the repository level.
- **Narrow schema.** Each brain can tune `CLAUDE.md` for its own vocabulary (microservice dependency graph vs personal knowledge management vs reading notes).

## Spin up a new brain

```bash
# 1. Create an instance from the template.
#    (a) GitHub Template Repository route
gh repo create Seika139/twin-layer-brain-<topic> --private \
    --template=Seika139/twin-layer-brain-template
mkdir -p ~/programs/brains
git -C ~/programs/brains clone git@github.com:Seika139/twin-layer-brain-<topic>.git
cd ~/programs/brains/twin-layer-brain-<topic>
#    (b) Or a local-only copy without GitHub
cp -r ~/programs/brains/twin-layer-brain-template ~/programs/brains/twin-layer-brain-<topic>
cd ~/programs/brains/twin-layer-brain-<topic>
rm -rf .git && git init

# 2. Install tools and dependencies.
mise install
uv sync
pnpm install

# 3. Empty the inherited content and reset index.md / log.md to skeletons.
mise run scaffold-brain

# 4. Rewrite the Scope line in CLAUDE.md, AGENTS.md, and README.md to
#    describe what this brain covers. Starting with a one-line scope keeps
#    ingest decisions sharp ("does this source fit this brain?").

# 5. Commit and push.
git add -A
git commit -m "ブレインの初期スコープを設定"
git push   # if using the GitHub route

# 6. (Optional) Build the initial index and start the server.
mise run init
mise run serve:install   # macOS launchd auto-start

# 7. Drop the first source into raw/ (or `mise run clone-repo <owner>/<repo>`)
#    and ingest it.
cd ~/programs/brains/twin-layer-brain-<topic> && claude
> ingest raw/notes/<source>
```

`mise run scaffold-brain` refuses to run inside `twin-layer-brain-template` itself (the template). Override with `FORCE=1 mise run scaffold-brain` only if you really mean to nuke the template's own content.

## Layout

```text
twin-layer-brain-<topic>/
├── CLAUDE.md           # LLM schema (Claude Code)
├── AGENTS.md           # Codex-facing schema companion
├── GUIDE.md            # human operation manual
├── README.md           # you are here
├── mise.toml           # task runner (`mise run ...`)
├── pyproject.toml      # Python deps and `kc` CLI entry point
├── package.json        # Node deps (Chrome extension etc.)
├── .agents/skills/     # source-of-truth skill packages for both LLM agents
├── .claude/skills/     # mirror of .agents/skills for Claude Code
├── compiler/           # Python package: FTS5 + embedding + `kc` CLI
├── server/             # FastAPI + MCP server
├── deploy/             # systemd unit, Caddyfile, launchd plist, setup.sh
├── raw/                # source material (Layer 2 input)
│   ├── notes/          # user-written notes (immutable — LLM never edits)
│   ├── articles/       # web clippings, PDFs
│   ├── assets/         # images, diagrams
│   └── repos/          # cloned source repos (gitignored — nested .git)
├── wiki/               # LLM-owned pages (Layer 2 output)
│   ├── index.md        # catalog — start here
│   ├── log.md          # append-only activity log
│   ├── sources/        # one page per ingested source
│   ├── entities/       # concrete things (people, services, tools)
│   ├── concepts/       # abstract things (patterns, workflows)
│   ├── topics/         # cross-cutting permanent theses (sublime output)
│   └── analyses/       # query snapshots (gitignored by default)
└── index/              # SQLite DB (Layer 1, gitignored — regenerable)
```

Public/private is a repository-level decision. The default `.gitignore` only carves out paths that either can't be tracked (`raw/repos/` — nested `.git`, large, reproducible) or are best kept out of public history regardless of the brain's status (`wiki/analyses/` — snapshots, private introspection). If the repo is private and you want analyses versioned, delete the `/wiki/analyses/*` line from `.gitignore`.

## Usage

### Layer 1 — fast search (`kc` CLI, MCP, REST)

```bash
# CLI
uv run kc new "タイトル"                # create a new note skeleton
uv run kc index                         # rebuild SQLite index from Markdown
uv run kc search "Docker"               # FTS keyword search
uv run kc suggest-related note-id       # semantic neighbours (needs OPENAI_API_KEY)
uv run kc check-keys                    # diagnose LLM API key availability

# mise shortcuts
mise run check-keys
mise run serve                          # foreground (dev)
mise run serve:install                  # launchd auto-start (macOS)
```

`OPENAI_API_KEY` (or Gemini / Anthropic / Ollama as configured) enables embedding-based semantic search. FTS5 keyword search works without any key.

REST endpoints (see `server/routes/`):

```text
GET  /api/notes/search?q=keyword     # FTS search
GET  /api/notes/similar?q=文章       # semantic search
GET  /api/notes/{id}                 # read a note
POST /api/notes                      # create
POST /api/sync/webhook               # GitHub webhook re-index trigger
GET  /api/health                     # liveness
```

### Layer 2 — read the wiki

- Start at `wiki/index.md`. Links use Foam/Obsidian `[[wiki-link]]` syntax — VS Code with the Foam extension (or Obsidian) resolves them.
- Mermaid diagrams render in VS Code preview (`bierner.markdown-mermaid`) and natively in Obsidian.

### Open the repo as an Obsidian vault (optional)

VS Code + Foam and Obsidian share the same `[[wiki-link]]` + YAML-frontmatter format, so either works. Shared Obsidian settings live in `.obsidian/{app,core-plugins,community-plugins}.json` (tracked); per-machine workspace state (`workspace.json`, installed plugin binaries, hotkeys) is gitignored.

1. Open the repo root as an Obsidian vault.
2. Obsidian will read `.obsidian/app.json` and honour the tracked link/attachment policy (`newLinkFormat: relative`, `attachmentFolderPath: raw/assets`, `useMarkdownLinks: false`).
3. On first open, Obsidian will list the community plugins declared in `.obsidian/community-plugins.json`. Install them from Community plugins → Browse:
   - **Dataview** — frontmatter queries over `wiki/`. Example: `TABLE created, updated FROM "wiki/topics"` renders a live topic index.
   - **PDF Plus** — improved PDF reading inside `raw/articles/`.
   - **Extract PDF Highlights** — turn PDF highlights into markdown for `raw/notes/` ingest.
4. Keep the core Obsidian Linter **disabled** — the repo uses `rumdl` (auto-run on edit via the Claude Code `PostToolUse` hook) and `markdownlint-cli2`. Running Obsidian Linter in parallel causes format thrash.

The wiki is fully readable without any plugin; the list above is the authors' recommendation, not a requirement.

### Read on mobile (iOS / Android)

The `.obsidian/*.json` shared settings work on mobile Obsidian unchanged — `[[wiki-link]]` resolution, graph view, backlinks, tag pane, Dataview, and PDF Plus all run. **Extract PDF Highlights is desktop-only** and will be skipped silently on mobile; that's expected.

**Sync path: Git/GitHub.** Mobile Obsidian has no built-in git, so the vault lives in a git client that Obsidian reads from via iOS Files.app or Android's filesystem. This aligns with the repo's git-is-source-of-truth design and doesn't require paid Obsidian Sync.

| Platform | Recommended flow |
|---|---|
| iOS | **Working Copy** (App Store) — clone the repo into Working Copy, enable File Provider so Obsidian can open the vault via Files.app. Manual `pull` / `commit` / `push` in Working Copy before and after editing. |
| Android | **Obsidian Git** community plugin (not in the Tier 1 list by default — opt in if needed) clones directly into the vault. Slower on large repos but avoids a separate app. |

Caveats of the mobile flow:

- **LLM operations (`ingest`, `query`, `sublime`, `dive`, `lint`) and Layer 1 indexing are desktop-only.** Claude Code / Codex / `mise` / Python / Node do not run on mobile; mobile use is read-first, with light frontmatter edits and ad-hoc additions to `raw/notes/` at most.
- **`raw/repos/` is gitignored** and will not sync to mobile. Cloned source repos only exist on the desktop that ran `mise run clone-repo`.
- **Commit from mobile sparingly.** Always pull first. If you push mobile edits, run `mise run lint` on desktop before the next ingest so markdown format stays consistent.
- **macOS/iOS AppleDouble files** (`._foo`) can leak into the repo if the vault moves across SMB / iCloud / exFAT. `.gitignore` blocks them, but check with `git status` after syncing.

### Ingest a source

```bash
# Put the source somewhere under raw/:
#   - user-owned notes → raw/notes/
#   - cloned repos     → raw/repos/  (use `mise run clone-repo`)
#   - clippings, PDFs  → raw/articles/
#   - images           → raw/assets/
mise run clone-repo <owner>/<repo>     # clones into raw/repos/<repo>

# Then in Claude Code or Codex:
> ingest raw/repos/<repo>
```

The agent reads the source, writes / updates pages under `wiki/`, updates `wiki/index.md`, and appends to `wiki/log.md`. Layer 1 is re-indexed automatically after the write (incremental).

### Ask a question (Query)

Open the repo in Claude Code / Codex and ask. The agent uses both layers:

1. Layer 1 (`search_notes` / `search_similar` via MCP) to shortlist candidate pages.
2. Layer 2 (`wiki/index.md` → relevant pages → `[[wiki-link]]` neighbours) to synthesize an answer with citations.

If the answer is worth keeping, the agent either files it as an analysis (`wiki/analyses/<slug>.md`, gitignored by default) or promotes it to canonical (`wiki/topics/`, `wiki/concepts/`, or `wiki/entities/`).

### Sublime — promote scattered knowledge into a canonical topic

```text
> sublime the analysis about rag-vs-wiki into a topic
```

The agent lifts recurring claims or valuable analyses into `wiki/topics/<slug>.md` with a Core thesis and Direct Citations (wiki-links + raw-file links side by side), routes the index entry point to the new canonical page, and demotes the analysis to derivation history. Run this when a snapshot analysis has proven its worth, or when the same claim keeps appearing across 3+ pages.

### Dive — deep-read `raw/` when the wiki is insufficient

```text
> dive into raw/repos/framework to trace how retry-on-conflict is decided
> /dive raw/articles/2026-04-20-rfc-draft.md の error handling 提案を詳しく
```

Exception lane to the wiki-first principle. Use when you already know the wiki summary isn't enough — for instance, a recently updated `raw/repos/<repo>/` with changes not yet re-ingested, or an implementation-level question that needs line-by-line citations. The agent confirms the focus, does a 60-second wiki scan to avoid rediscovering known facts, reads `raw/` hierarchically, and cites every claim with `file:line` markdown links. Results default to `wiki/analyses/` as a gitignored snapshot; a source page is updated only after you confirm a permanent fact.

### Lint the wiki

```text
> lint the wiki
```

Produces five fixed sections: auto-fixable / needs review / missing pages / unsourced claims / follow-up questions. No auto-fix — changes go through review.

See **`GUIDE.md`** for the long-form human operation manual with step-by-step scenarios.

## Why not a chatbot with RAG?

RAG re-retrieves sources on every query. This wiki **compounds** — prior synthesis is persistent, cross-referenced, and read before answering, so the system gets smarter over time. The persistence is the crux (karpathy's framing). Layer 1's fast search accelerates the retrieval step; Layer 2 is where the compounding happens.

## Not for

- **Topics outside this brain's Scope.** Spin up another repo instead. Keep the `[[wiki-link]]` graph dense and the confidentiality boundary clean.
