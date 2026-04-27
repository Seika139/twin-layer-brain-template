# CLAUDE.md

Operating schema for the LLM agent maintaining this **twin-layer-brain**. Based on karpathy's "LLM Wiki" pattern (<https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>) with an added SQLite search layer.

## Scope

This brain covers: **<このブレインが扱う範囲を 1 行で書き換える>**

One brain = one topic. For a different topic — another work project, a side domain, a separate machine — spin up a new repo from this template. Keeping brains narrow keeps the `[[wiki-link]]` graph dense and prevents sensitive material from leaking across domains. See `README.md` and `docs/instance-setup.md` for the template workflow.

## Twin-layer architecture

This brain has two cooperating search layers over the same Markdown source of truth:

- **Layer 1 (SQLite)** — `compiler/` indexes configured Markdown directories into SQLite (FTS5 for keywords, `sqlite-vec` for embeddings). Exposed via `kc` CLI, REST API (`server/`), and MCP server. Derived and regenerable — `kc index` rebuilds from scratch.
- **Layer 2 (LLM wiki)** — `wiki/` is an LLM-maintained graph of interlinked Markdown pages. Grows by compound: each ingest updates 10–15 pages, not a single page.

**Single-direction data flow**: writes happen on Markdown (`raw/` by humans, `wiki/` by the LLM); Layer 1 is rebuilt from Markdown via `kc index` or API-triggered `rebuild_index()`. The LLM never writes to SQL directly. Layer 1 is consulted as a retrieval accelerator during `query` / `dive`, but synthesis is Layer 2's job.

## Layout and ownership

One flat tier. Public/private is decided per repository — this template stays agnostic and the `.gitignore` only carves out material that is either reconstructible (cloned repos) or private by nature (query-time analyses).

| Path             | Git (default) | Owner | Role                                                                                                                                                                                                          |
| ---------------- | ------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `raw/notes/`     | tracked       | user  | own notes, voice memo transcripts, meeting notes. Immutable — LLM never edits.                                                                                                                                |
| `raw/articles/`  | tracked       | user  | web clippings, downloaded PDFs, papers.                                                                                                                                                                       |
| `raw/assets/`    | tracked       | user  | images, diagrams, screenshots.                                                                                                                                                                                |
| `raw/repos/`     | **ignored**   | user  | cloned source repositories (nested `.git`, large, licensed separately, reproducible from upstream).                                                                                                           |
| `wiki/index.md`  | tracked       | LLM   | catalog of all wiki pages. Always kept current.                                                                                                                                                               |
| `wiki/log.md`    | tracked       | LLM   | chronological, append-only record of ingests / queries / lint passes / refactors.                                                                                                                             |
| `wiki/sources/`  | tracked       | LLM   | one file per ingested source, summarizing it and linking back to `raw/`.                                                                                                                                      |
| `wiki/entities/` | tracked       | LLM   | one file per concrete entity (person, company, service, repo, tool, product).                                                                                                                                 |
| `wiki/concepts/` | tracked       | LLM   | one file per abstract concept, pattern, technique, theme.                                                                                                                                                     |
| `wiki/topics/`   | tracked       | LLM   | one file per **cross-cutting permanent topic** — a claim, design decision, comparison axis, or adoption order that is referenced across multiple sources / entities / concepts. See `topic vs concept` below. |
| `wiki/analyses/` | **ignored**   | LLM   | query-time synthesis snapshots. Not canonical — do not promote in place; if an analysis has lasting value, distill it into `wiki/topics/`, `wiki/concepts/`, or `wiki/entities/`.                             |

### Concept vs topic vs entity

Three distinct roles for canonical knowledge pages. Pick the most specific type that fits:

- **`entity`** — a concrete thing with identity (a tool, a person, a service, a product). The page is about _the thing itself_.
- **`concept`** — an abstract pattern, technique, or theme. The page is about _an idea or category_ that can be instantiated by multiple entities.
- **`topic`** — a **cross-cutting permanent claim** that synthesises multiple sources / entities / concepts into a single stable takeaway. A topic page answers "given everything we know, what is the current best understanding of X?". Unlike `concept`, a topic carries a concrete thesis; unlike `analysis`, it is canonical and maintained.

Rule of thumb: if the same sentence keeps getting repeated across 3+ concept/entity pages, or a dated analysis would otherwise become the de-facto entry point, lift the common thesis into a `topic`.

### Public vs private

The gitignore defaults assume the repository can tolerate either public or private hosting. If this brain becomes public, audit `wiki/sources/` and `wiki/entities/` for any internal names that slipped in during ingest. If private, feel free to delete the `/wiki/analyses/` rule from `.gitignore` so analyses become versioned.

### Guardrails

- Never edit `raw/notes/` — it is user-owned. `raw/{articles,assets,repos}/` is also user-curated; LLM may read but should not rewrite.
- Treat `wiki/` as append/update-only in normal operation; deletion requires an explicit refactor and a log entry.
- If you clone a repo into `raw/repos/` manually, prefer `mise run clone-repo` (it normalises the target path).

## Citation style

Every non-trivial claim must cite a source or another wiki page. Use these exact forms:

- Attribution: `According to [[sources/2026-04-21-karpathy-llm-wiki]], the LLM maintains the wiki persistently across sessions.`
- Inline reference: `...persistence is the crux ([[sources/2026-04-21-karpathy-llm-wiki]]).`
- Contradiction: `> **Contradiction:** [[sources/A]] claims X, but [[sources/B]] claims Y. Needs resolution.`
- Raw file (outside the wiki graph): `[article](../../raw/notes/2026-04-21-example.md)` or `[repo README](../../raw/repos/foo/README.md)` — standard markdown with relative path.

Never cite a source that doesn't exist as a file under `raw/` or `wiki/sources/`.

## Filename convention

- **Kebab-case English** for all filenames, including Japanese-body pages: `oauth2-authentication.md`, `cognito-trigger-pipeline.md`.
- Rationale: stable URLs, grep-friendly, consistent across shell / editor / Git diff.
- Dated sources: `YYYY-MM-DD-<slug>.md` (e.g. `2026-04-21-karpathy-llm-wiki.md`).
- The human-readable Japanese title lives in frontmatter `title:`.

## Wiki-link convention

Inside `wiki/`, link between pages with `[[relative/path/without/extension|display]]` form:

- `[[entities/foam]]`
- `[[concepts/knowledge-graph|knowledge graphs]]`
- `[[sources/2026-04-21-karpathy-llm-wiki]]`

Foam (VS Code) and Obsidian both follow wiki-links; the editor resolves them even without an extension.

## Page format

Every wiki page starts with YAML frontmatter:

```yaml
---
title: <human-readable title, typically Japanese>
type: source | entity | concept | topic | analysis | index | log
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: [sources/2026-04-21-karpathy-llm-wiki] # which sources contributed
tags: [tag1, tag2] # free-form categorization
---
```

Body structure (guideline, adapt per page):

1. One-paragraph summary at the top — what this is, why it matters.
2. Key facts / claims, each with `[[sources/...]]` citation.
3. Related pages — outbound `[[wiki-links]]`.
4. Open questions — things to investigate next.

### Topic page extras

Topic pages are synthesis pages that will be consulted repeatedly, so readability-for-verification matters. Add these two sections in addition to the base structure:

- **Core thesis / Stable takeaway** — 2-5 bullets stating the permanent claim the topic holds. These should survive most future ingests.
- **Direct Citations** — a flat list of links, interleaving `[[sources/...]]`, `[[entities/...]]`, `[[concepts/...]]` wiki-links _and_ direct markdown links to raw files (`[source excerpt](../../raw/notes/2026-04-21-example.md)`, `[config](../../raw/repos/<repo>/src/.../Foo.php)`). The goal is that a future reader can verify the thesis without taking a 1-hop detour through a source-summary page. Include a raw-file link whenever a single line of code or a single paragraph is the decisive evidence.

Keep Direct Citations optional for other page types — they are worth the maintenance cost only when the page is a cross-referenced hub.

## Operations

Five canonical operations. Each has a dedicated skill package under `.agents/skills/<name>/`, with `.claude/skills` symlinked to that tree so Claude Code resolves the same source-of-truth files. The summaries below are the contract; the SKILL.md files contain the step-by-step recipe.

**Lane structure:** `ingest` grows the wiki from `raw/`. `query` answers from the wiki (wiki-first principle). `sublime` reorganises existing wiki content into canonical homes. `dive` is the deliberate exception lane — it re-reads `raw/` directly when the user already knows the wiki is insufficient, typically for recently updated repos or implementation-level questions. `lint` diagnoses the wiki's health.

### Ingest

Triggered when the user adds a source to `raw/` and asks to ingest.

**Contract:**

1. Read the source end-to-end. For repos: README → top-level entry points → sample important files.
2. Discuss 2-3 key takeaways with the user _in chat_ before writing.
3. Create `wiki/sources/YYYY-MM-DD-<slug>.md` with citations back to specific sections/files.
4. Propagate outward: update / create relevant `entities/`, `concepts/`, and `topics/` pages. Add cross-references. If a new source refines the stable takeaway of an existing topic, update that topic.
5. On contradiction with existing pages: do **not** silently overwrite. Keep both, mark the older as "Superseded by [[source]]", and surface to user.
6. Update `wiki/index.md` to list new/modified pages.
7. Append an entry to `wiki/log.md`.

**Scale expectation:** a single substantive source can touch **10–15 wiki pages** once cross-references, entity updates, and concept revisions are accounted for. If an ingest modifies only 1–2 pages, re-examine — something else probably should have changed.

### Large codebase ingest strategy

For repos with hundreds of files, full read-through is infeasible. Use this ordering:

1. **Inventory** — `ls` the root, read `README.md`, `package.json` / `pyproject.toml` / `Cargo.toml` / `go.mod`, any `docs/` or `ARCHITECTURE.md`. Identify: language, frameworks, top-level modules.
2. **Entry points** — `main.*`, `index.*`, `app.*`, CLI definitions, server bootstraps, exported public API.
3. **Directory map** — read one representative file per top-level directory to understand the responsibility split.
4. **Cross-cutting concerns** — config loading, auth, logging, error handling, data layer. Usually one file each.
5. **Skip** — generated code (`dist/`, `build/`, lockfiles), vendored dependencies, tests (unless testing strategy is the subject).
6. **Surface claims** — when the `wiki/sources/<slug>.md` page is ready, have numbered claims pointing to specific files / lines so the user can spot-check.

The source page should read as "what this repo does and how it's structured" in 500–1000 Japanese characters, not as a line-by-line summary.

### Query

Triggered when the user asks a question.

**Contract:**

1. Read `wiki/index.md` first to locate relevant pages.
2. Read those pages (and their linked pages as needed) rather than going back to `raw/`. Only consult `raw/` when the wiki is silent or seems stale.
3. Answer with citations: every non-trivial claim cites the wiki page it came from, which cites sources.
4. **Choose a response format that fits the question.** Plain prose is the default; when the shape of the answer warrants it use:
   - **Comparison table** — "how does X differ from Y" / "what are the options".
   - **Mermaid diagram** — relationship, dependency, or flow (graph, sequence, flowchart). VS Code previews inline.
   - **Bulleted decision tree** — "when should I use X vs Y".
   - **Marp slide outline** — "walk me through this topic".
   - **A new markdown page** — when the answer itself is the artifact.
5. If the answer is valuable, either:
   - **File it as an analysis** (fast): write `wiki/analyses/<slug>.md`. Gitignored by default, snapshot — will go stale.
   - **Promote to canonical** (slow): add / update the best-fit page — `wiki/topics/<slug>.md` (cross-cutting thesis), `wiki/concepts/<slug>.md` (abstract pattern), or `wiki/entities/<slug>.md` (concrete thing) — and update the index.
6. Append a query entry to `wiki/log.md`.

### Sublime

Triggered when the user asks to sublimate, promote, or consolidate scattered knowledge — or when an `analysis` has proven to have lasting value and needs to become canonical.

**Contract:**

1. Identify the scattered or snapshot-bound knowledge: a useful `wiki/analyses/<slug>.md`, a repeated claim across concept/entity pages, or a stable takeaway that never got its own page.
2. Classify the content into:
   - **Cross-cutting permanent claim** → `wiki/topics/<slug>.md` (create or update).
   - **Repo/source-specific permanent fact** → backflow into the relevant `wiki/sources/<slug>.md` or `wiki/entities/<slug>.md`.
   - **Time-bound or derivation artefact** → leave in place (if an analysis) and make sure it points at the canonical version.
3. When creating a topic, fill the Topic page extras (Core thesis + Direct Citations). Link the topic back to the originating pages in each page's `Related` section.
4. If an `analysis` was the trigger, do **not** delete it. Instead add a line at the top — `> **Canonical version:** [[topics/<slug>]]` — so future readers land on the maintained page.
5. Update `wiki/index.md` to route the main entry point through the new canonical page, not through the analysis.
6. Append a sublime entry to `wiki/log.md` stating: what was promoted, where the canonical home is, what was backflowed, which analysis (if any) was demoted to derivation history.

**When to use vs. Query:** Query creates a new answer from wiki content; Sublime reorganises existing wiki content so that repeated knowledge has a single canonical home. The two are often run back-to-back — a query that produces a valuable analysis may trigger a sublime run right after.

### Dive

Triggered when the user explicitly invokes `/dive`, says "dive into X", or otherwise signals that the wiki is insufficient for their question — typically because the wiki is silent on an implementation detail or because a recently updated `raw/repos/<repo>/` carries facts that haven't been re-ingested yet.

**Contract:**

1. Confirm the focus in one sentence (target + question) and wait for the user's steer unless the focus is already unambiguous.
2. **Scan — do not deep-read —** the relevant wiki pages for 60 seconds to establish a baseline ("the wiki already knows X, Y, Z"). This prevents rediscovering known facts.
3. Read `raw/` hierarchically, target-scoped: anchor → immediate neighbours → cross-cutting context. Stop as soon as the focus question is answerable with concrete file:line citations.
4. Synthesize with **line-level citations**: `[descriptor](../../raw/repos/<repo>/path/to/file.ext)` pointing to specific line ranges. Line numbers are the contract — without them the dive is not complete.
5. **Save the findings (default = analysis)**:
   - **Default:** automatically file to `wiki/analyses/YYYY-MM-DD-dive-<slug>.md` with `type: analysis` and extra `dive_focus:` / `dive_target:` frontmatter fields.
   - **Exception (c) — source page update:** if a permanent fact is uncovered that belongs on an existing `wiki/sources/<slug>.md` or `wiki/entities/<slug>.md`, **ask the user** before writing.
   - **Exception (a) — chat only:** if the user said "just tell me, don't save", skip the file write.
6. Append a `dive` entry to `wiki/log.md` with target, focus, key citations, and save outcome.

**Lane boundary with Query:** `query` starts from the wiki and falls back to `raw/` only when the wiki is silent/stale. `dive` starts from `raw/` on purpose because the user has already decided the wiki is insufficient. If the user hasn't signalled that, prefer `query` first.

**Stop condition:** once the focus question has a citation-backed answer, stop reading. Dive does not aim for coverage; it aims for a focused, verifiable answer.

### Lint

Triggered when the user asks for a lint pass, or suggested periodically (~every 10 ingests).

**Five fixed output sections** (always all five, even if empty):

1. **Auto-fixable** — broken `[[wiki-links]]`, typo-level inconsistency, frontmatter drift. _Do not auto-fix — list them for the user to confirm._
2. **Needs review** — contradictions between pages, stale pages whose cited sources are older than N months, pages whose content disagrees with a newer source.
3. **Missing pages** — concepts / entities mentioned 3+ times in body text across the wiki but never given their own page.
4. **Unsourced claims** — assertions in `entities/` or `concepts/` pages that have no `[[sources/...]]` citation.
5. **Follow-up questions** — open questions implied by existing pages but not yet investigated; specific sources worth ingesting next (URL-level suggestions).

**Output:** checklist, one item per finding, section by section. Do not auto-fix. Append a lint entry to `wiki/log.md`.

## `wiki/index.md` format

One section per category. Under each, one line per page:

```markdown
## Topics

- [[topics/knowledge-compounding]] — LLM Wiki が RAG と違って蓄積で賢くなる核心論点。(3 sources)

## Entities

- [[entities/foam]] — VS Code extension that turns markdown into a linked knowledge base. (2 sources)

## Concepts

- [[concepts/llm-wiki-pattern]] — karpathy-style persistent knowledge graph maintained by an LLM. (1 source)

## Sources

- [[sources/2026-04-21-karpathy-llm-wiki]] — gist outlining the LLM-wiki pattern. (2026-04-21)
```

The one-liner should help the user (and future-you) pick the right page without opening it. Update source counts when they change.

## `wiki/log.md` format

Append-only. Header format is machine-parseable — `grep "^## \[" log.md` lists all entries:

```markdown
## [2026-04-21] ingest | karpathy LLM Wiki gist

- Added: [[sources/2026-04-21-karpathy-llm-wiki]], [[concepts/llm-wiki-pattern]]
- Updated: [[entities/obsidian]], [[index]]
- Notes: user emphasized persistence and schema co-evolution as the crux.

## [2026-04-22] query | how does Foam differ from Obsidian?

- Read: [[entities/foam]], [[entities/obsidian]]
- Outcome: filed comparison as [[concepts/markdown-kb-tools]]
```

Entry types: `ingest`, `query`, `sublime`, `dive`, `lint`, `refactor` (schema change or structural move).

## Style

- **Language:** wiki body = Japanese (matches user's working language). Filenames = kebab-case English. Code / keyword references = English as-is.
- **Tone:** encyclopedic, concise, factual. No filler. Short is good.
- **Bold** key terms on first mention.
- **Citations:** every claim traceable to a source.
- **Dates:** `YYYY-MM-DD`, no timezone.

## Tools

- VS Code is the daily editor. Recommended extensions: `.vscode/extensions.json` (Foam, Mermaid preview, markdownlint, rumdl, Code Spell Checker).
- Lint: both `markdownlint-cli2` and `rumdl`. Configs kept in sync (`.markdownlint-cli2.jsonc`, `.rumdl.toml`).
- Repo management: `mise` (see `mise.toml`). `mise run clone-repo` / `mise run update-repos` for ingestable repo clones.
- Layer 1 (SQLite): `compiler/` provides the `kc` CLI (`kc new` / `kc index` / `kc search` / `kc suggest-related` / `kc check-keys`). `server/` provides FastAPI + MCP. `mise run serve` starts the HTTP server; `mise run serve-install` registers it as a launchd service on macOS.
- API keys: store provider keys in `.env` (template: `.env.example`). `mise run check-keys` diagnoses which providers are usable. FTS keyword search works without any key; semantic search needs an embedding provider.

## Guardrails (recap)

- **Never** edit `raw/notes/`. Never invent sources.
- **Prefer** updating an existing page over creating a new one when the topic already has a page. Duplicates are the #1 failure mode of this system.
- **Always** update both `wiki/index.md` and `wiki/log.md` after every operation — no exceptions.
- **Ask** when unsure: what to emphasize, new page vs update, whether to file a query answer as canonical vs analysis.
