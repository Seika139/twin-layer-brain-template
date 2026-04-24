---
name: ingest
description: Read a new source (repo, article, PDF, note) end-to-end, create a sources/ summary page, propagate updates across entities/ and concepts/, update index.md and log.md. Use when the user says "ingest <path>" or drops a new file into raw/ and asks for processing.
---

# Skill: Ingest

Bring a new source into the wiki following the karpathy pattern.

## Preconditions

- A source exists at a path the user provides (under `raw/notes/`, `raw/articles/`, `raw/assets/`, or `raw/repos/`).
- The user has invoked ingest explicitly — don't ingest unprompted.

## Recipe

### 1. Read the source

- **Note / article / PDF:** read end-to-end.
- **Repository:** follow the *Large codebase ingest strategy* below.
- If the source is in a language the user doesn't speak fluently, translate key claims into Japanese in chat before writing.

### 2. Discuss 2–3 key takeaways in chat

Before writing *any* file, present to the user:

- "This source's core claims are: [a], [b], [c]."
- "Related existing pages I'd update: [[page1]], [[page2]]."
- "Should I emphasize anything specific?"

Wait for the user's steer. **Do not start writing after listing takeaways without confirmation** unless the user has pre-authorized.

### 3. Write `wiki/sources/YYYY-MM-DD-<slug>.md`

Kebab-case English filename. Japanese body. Frontmatter:

```yaml
---
title: <日本語タイトル>
type: source
created: <today, YYYY-MM-DD>
updated: <today>
sources: []     # a source page does not cite other sources in this slot
tags: [<tag1>, <tag2>]
---
```

Body structure:

1. **概要** — one paragraph: what this is, why it matters.
2. **主要な主張 / 論点** — bulleted, each with a pointer back to the source (file path, section, URL, page number).
3. **既存 Wiki との関係** — which entities / concepts this touches, and how.
4. **未解決の問い** — open questions surfaced by this source.

### 4. Propagate outward (the critical step)

For each entity/concept/topic the source touches substantively:

- If an `entities/<slug>.md`, `concepts/<slug>.md`, or `topics/<slug>.md` already exists — **update it**. Add the new source to its `sources:` frontmatter, add claims with `[[sources/<slug>]]` citations, add cross-references. For topics, refine the Core thesis and Direct Citations if the new source sharpens the claim.
- If it doesn't — **create it** following the frontmatter template above with the appropriate `type`.
- Do **not** create a new topic during ingest unless a single source alone establishes a cross-cutting claim. Topic creation is usually the sublime skill's job. Ingest updates existing topics and flags topic candidates in the log.
- Add bidirectional cross-references: source ↔ entity/concept/topic, entity ↔ related entity, concept ↔ related concept, topic ↔ its supporting pages.

**Scale check:** a substantive source typically touches **10–15 pages**. If you've only touched 1–2, go back and look for what else should have updated.

### 5. Handle contradictions explicitly

If the new source contradicts an existing page:

- **Do not silently overwrite.**
- Keep the old claim, mark it with `> **Superseded by [[sources/<new>]]:** <one-line reason>`.
- Add a `> **Contradiction:**` block to both pages pointing at each other.
- Surface this to the user in chat: "Found a contradiction between [[A]] and [[B]] — flagged both, needs your judgment."

### 6. Update `wiki/index.md`

Add / update one-liners for every page created or substantively updated. Keep the source count (`(N sources)`) current.

### 7. Append to `wiki/log.md`

```markdown
## [YYYY-MM-DD] ingest | <source short title>

- Added: [[sources/<slug>]], [[entities/<new-slug>]], ...
- Updated: [[concepts/<slug>]], [[index]]
- Contradictions: <if any, or "none">
- Notes: <what the user emphasized, unusual choices made>
```

## Large codebase ingest strategy

For repos with hundreds of files, full read-through is infeasible.

1. **Inventory** — `ls` root, read `README.md`, manifest (`package.json` / `pyproject.toml` / etc.), any `docs/` or `ARCHITECTURE.md`.
2. **Entry points** — `main.*`, `index.*`, `app.*`, CLI definitions, server bootstrap.
3. **Directory map** — one representative file per top-level directory.
4. **Cross-cutting** — config loading, auth, logging, error handling, data layer.
5. **Skip** — generated code, lockfiles, vendored deps, tests (unless testing is the subject).
6. **Numbered claims** — the source page should make claims like "1. The CLI is defined in `cmd/main.go`" so the user can spot-check.

Target: 500–1000 Japanese characters summarizing structure and responsibility, not a line-by-line summary.

## Anti-patterns

- ❌ Writing `wiki/sources/...` and stopping — the propagation step is the whole point.
- ❌ Creating a new page when an existing one covers the same topic.
- ❌ Silent overwrite on contradiction.
- ❌ Citing a source URL that isn't under `raw/`.
- ❌ Skipping the "discuss takeaways" step — the user's steer reshapes emphasis.

## Done

Report to the user:

- Pages created: N
- Pages updated: N
- Contradictions flagged: N
- Questions surfaced (for follow-up): N

## Reference

- 詳細方針: `references/karpathy-llm-wiki.md`
