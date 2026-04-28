# AGENTS.md

Operating schema for Codex (OpenAI) agents maintaining this **twin-layer-brain**. This file is the Codex-facing companion to `CLAUDE.md`; keep them aligned. If they diverge, `CLAUDE.md` is the source of truth and this file should be updated to match.

Based on karpathy's "LLM Wiki" pattern: <https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>. Extended with a Layer 1 SQLite search (FTS5 + embeddings) exposed via `compiler/` (`kc` CLI) and `server/` (FastAPI + MCP). Writes always land on Markdown; Layer 1 is rebuilt from Markdown via `kc index` or API-triggered `rebuild_index()`.

## Scope

This brain covers: **<このブレインが扱う範囲を 1 行で書き換える>**

One brain = one topic. Separate repos for separate concerns (work project / side domain / personal). See `README.md` and `docs/instance-setup.md` for the template workflow.

## Layout and ownership

One flat tier. The default `.gitignore` only carves out cloned source repos (nested `.git`, reconstructible from upstream) and query-time analyses (snapshots, rot fast). Everything else is tracked regardless of whether this brain is eventually public or private.

| Path                                                 | Git (default) | Owner | Role                                                    |
| ---------------------------------------------------- | ------------- | ----- | ------------------------------------------------------- |
| `raw/notes/`                                         | tracked       | user  | own notes / transcripts. Immutable — agent never edits. |
| `raw/articles/`                                      | tracked       | user  | web clippings, PDFs.                                    |
| `raw/assets/`                                        | tracked       | user  | images, diagrams.                                       |
| `raw/repos/`                                         | **ignored**   | user  | cloned source repositories (`mise run clone-repo`).     |
| `wiki/index.md`                                      | tracked       | agent | catalog.                                                |
| `wiki/log.md`                                        | tracked       | agent | append-only operation log.                              |
| `wiki/sources/`, `entities/`, `concepts/`, `topics/` | tracked       | agent | one file per item.                                      |
| `wiki/analyses/`                                     | **ignored**   | agent | query-time snapshots (not canonical).                   |

**Page type roles:**

- `entity` — concrete thing with identity (a tool, person, service).
- `concept` — abstract pattern, technique, or theme.
- `topic` — cross-cutting permanent claim synthesising multiple sources / entities / concepts. Carries a concrete thesis.
- `analysis` — query-time snapshot, gitignored by default, not canonical.

### Guardrails

- Never edit `raw/notes/`. `raw/{articles,assets,repos}/` is user-curated — agent may read, not rewrite.
- `wiki/` is append/update-only in normal operation; deletion requires explicit refactor + log entry.

## Citation style

- Attribution: `According to [[sources/2026-04-21-foo]], X.`
- Inline: `...X ([[sources/2026-04-21-foo]]).`
- Contradiction: `> **Contradiction:** [[sources/A]] claims X, but [[sources/B]] claims Y.`

Never cite a source that doesn't exist as a file.

## Filename convention

Kebab-case English for filenames. Dated sources: `YYYY-MM-DD-<slug>.md`. Japanese title in frontmatter `title:`.

## Wiki-links

`[[relative/path/without/extension|display]]` form inside `wiki/`. Links to `raw/` files use standard markdown with relative path.

## Page format

```yaml
---
title: <human-readable title>   # 値が ` / @ / : / [ / { / # 等で始まる場合はダブルクォートで囲む（YAML 予約文字）
type: source | entity | concept | topic | analysis | index | log
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: [sources/<slug>]
tags: [tag1, tag2]
---
```

> **YAML quoting**: タイトルに `` ` `` / `:` / `@` / `[` / `{` / `#` / `>` / `|` /
> `&` / `*` / `!` / `%` を含める場合、必ず値全体をダブルクォートで囲う
> （YAML プレーンスカラーの先頭で使えない予約文字）。
> 書いた後は `mise run validate` で機械的に検証できる。
> 違反すると `kc index` が該当ファイルをスキップし、Layer 1 の索引から漏れる。

Topic pages additionally carry **Core thesis / Stable takeaway** bullets and a **Direct Citations** section that interleaves `[[wiki-links]]` with raw-file links (`[excerpt](../../raw/notes/...)`, `[config](../../raw/repos/<repo>/...)`) so the thesis is verifiable without a 1-hop detour.

## Operations

Skill packages live in `.agents/skills/{ingest,query,lint}/` and are shared between agents:

- `SKILL.md` — prose recipe (used by both Claude Code and Codex).
- `agents/openai.yaml` — per-skill machine-readable `interface` manifest consumed by Codex (for example `.agents/skills/query/agents/openai.yaml`).
- `references/` — longer-form notes linked from `SKILL.md`.

Claude Code reaches the same tree via the `.claude/skills → ../.agents/skills` symlink, so changes made under `.agents/` propagate to both runtimes without duplication.

### Ingest

1. Read source end-to-end
2. Discuss 2–3 takeaways in chat
3. Write `wiki/sources/YYYY-MM-DD-<slug>.md`
4. Propagate to `entities/`, `concepts/`, `topics/` (expect 10–15 pages touched per substantive source); update existing topics when a new source refines their thesis
5. Handle contradictions by keeping both + "Superseded by" note
6. Update `index.md`, append to `log.md`

For large repos use the inventory → entry points → directory map → cross-cutting concerns ordering. See CLAUDE.md for the full recipe.

### Query

1. Read `wiki/index.md` first
2. Read relevant pages, synthesize
3. Pick format: prose / table / Mermaid / decision tree / Marp / new page
4. File as `wiki/analyses/` (snapshot, gitignored by default) or promote to `wiki/{topics,concepts,entities}/` (canonical)
5. Append to `log.md`

### Sublime

1. Identify scattered or snapshot-bound knowledge (useful `analysis`, claim repeated across pages, thesis without a page)
2. Classify: cross-cutting → `topics/`; repo/source-specific → backflow to existing `sources/` or `entities/`; time-bound → leave in place
3. Create / update the target canonical page with Core thesis + Direct Citations sections
4. If an analysis triggered this, prepend `> **Canonical version:** [[topics/<slug>]]` to it — never delete
5. Update `index.md` so the main entry routes through the canonical page, not the analysis
6. Append a `sublime` entry to `log.md`

### Dive

Exception lane to the wiki-first principle. Use when the user explicitly signals that the wiki summary is insufficient or invokes `/dive`.

1. Confirm the focus (target + question) in one sentence
2. Scan (not deep-read) the relevant wiki pages for ≤ 60 seconds to avoid rediscovering known facts
3. Read `raw/` hierarchically — anchor → neighbours → cross-cutting — and stop when the focus question is citation-answerable
4. Cite every claim with **file:line** markdown links: `[descriptor](../../raw/repos/<repo>/path/to/file:L42-L58)`
5. Save by default to `wiki/analyses/YYYY-MM-DD-dive-<slug>.md` with `type: analysis` + `dive_focus:` / `dive_target:` frontmatter. Update a source page only after the user confirms a permanent fact. Skip the write if the user asks not to save.
6. Append a `dive` entry to `log.md`

### Lint

Five fixed sections, always all five:

1. Auto-fixable
2. Needs review
3. Missing pages
4. Unsourced claims
5. Follow-up questions

No auto-fix. Append lint entry to `log.md`.

## Log format

Append-only, grep-parseable header:

```markdown
## [2026-04-21] ingest | karpathy LLM Wiki gist

- Added: [[sources/2026-04-21-karpathy-llm-wiki]]
- Updated: [[entities/obsidian]]
```

Types: `ingest`, `query`, `sublime`, `dive`, `lint`, `refactor`.

## Style

Japanese body, kebab-case English filenames. Concise, encyclopedic. Cite aggressively. `YYYY-MM-DD` dates, no timezone.

## Guardrails (recap)

- Never edit `raw/notes/`.
- Prefer updating existing pages over creating new ones.
- Always update both `index.md` and `log.md`.
- Ask when unsure.

## Lint hook (Codex-side)

Codex does not yet have an equivalent to Claude Code's `.claude/settings.json` `PostToolUse` mechanism. Until it does, manually keep lint drift from accumulating:

1. Save the edited `*.md` file.
2. Run `rumdl check --fix <file>` on the saved path.
3. Run `markdownlint-cli2 <file>` to confirm nothing remains.
4. If auto-fix can't resolve an issue, surface it to the user before continuing.

For a session that has touched many files, run the project-wide task instead:

```bash
mise run format
mise run lint
mise run validate   # wiki/raw の frontmatter が壊れていないか機械的にチェック
```

Use `mise run format --all` and `mise run lint --all` when Python or shell task files were also touched.

`mise run validate` は `.agents/skills/ingest/SKILL.md` に従って frontmatter を書いた直後、あるいは `sublime` で topic を作った直後に実行するのが望ましい。parse できないファイルは `kc index` から弾かれるため、Layer 1 検索から見えなくなる。

This is the Codex-side counterpart to the Claude Code hook configured in `.claude/settings.json`.
