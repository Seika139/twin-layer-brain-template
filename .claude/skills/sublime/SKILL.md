---
name: sublime
description: Promote scattered or snapshot-bound knowledge into canonical topic / concept / entity pages. Use when the user asks to "sublimate", "promote", "consolidate", or "turn this analysis into a topic"; when a valuable `wiki/analyses/<slug>.md` deserves a canonical home; when the same claim keeps appearing across 3+ pages; or when a dated query result is becoming the de-facto entry point for a theme.
---

# Skill: Sublime

Lift knowledge that is currently scattered, snapshot-bound, or implicit into a single canonical page that future queries can land on directly.

## Preconditions

- At least one of: (a) a non-trivial `wiki/analyses/<slug>.md` exists; (b) a recurring claim has been spotted across 3+ wiki pages; (c) the user identified a theme without a dedicated page.
- The user has invoked sublime explicitly, or a query has produced an analysis worth promoting.

## Recipe

### 1. Identify the sublimation target

Pick exactly one target per run. Examples:

- A specific `wiki/analyses/<YYYY-MM-DD-slug>.md` the user points at.
- A concept/entity page whose tail sections keep being duplicated in new sources.
- A `sources/` page whose "stable takeaway" paragraph is repeatedly quoted by other pages.

### 2. Classify the content

Split the target's content into three buckets. It is normal for a single analysis to contain all three.

| Bucket | Canonical home | Example |
|---|---|---|
| **Cross-cutting permanent claim** | new or updated `wiki/topics/<slug>.md` | "LLM Wiki compounds because synthesis is persisted, unlike RAG." |
| **Source- or entity-specific permanent fact** | backflow into existing `wiki/sources/<slug>.md` or `wiki/entities/<slug>.md` | "Obsidian Web Clipper saves images when Attachment folder points at `raw/assets/`." |
| **Time-bound / derivation artefact** | stays in the source analysis | "As of 2026-04-23 the wiki has 2 sources and 7 concepts, so qmd adoption is not yet warranted." |

### 3. Backflow source-specific facts first

Update each affected `sources/` or `entities/` page. Before adding a new paragraph, check whether the claim is already expressed — if yes, report "existing page absorbs the fact" and skip the edit. Duplication is worse than omission here.

### 4. Write or update the topic page

If the cross-cutting bucket is non-empty, create `wiki/topics/<slug>.md`. Slug rule:

- **First candidate:** the originating analysis filename with the date suffix stripped. `2026-04-23-rag-vs-wiki.md` → `topics/rag-vs-wiki.md`.
- If that slug collides with an existing topic, pick a name that preserves meaning (`topics/rag-vs-wiki-compounding.md`).
- Avoid splitting a single analysis into multiple topics unless two different sections each naturally belong to an existing topic.

Frontmatter:

```yaml
---
title: <日本語タイトル>
type: topic
created: <today>
updated: <today>
sources: [sources/<slug1>, sources/<slug2>]
tags: [tag1, tag2]
---
```

Body structure:

1. **概要** — one paragraph stating the thesis in plain terms.
2. **Core thesis / Stable takeaway** — 2-5 bullets that should survive most future ingests.
3. **Direct Citations** — flat list interleaving `[[sources/...]]`, `[[entities/...]]`, `[[concepts/...]]` wiki-links *and* direct raw-file links (`[source excerpt](../../raw/notes/2026-04-21-example.md)`). A reader should be able to verify the thesis without a 1-hop detour.
4. **Related** — outbound `[[wiki-links]]` to concept/entity pages the topic touches.
5. **Open questions** — what further ingest would sharpen this topic.

### 5. Demote the source analysis (if applicable)

If the sublime was triggered by a `wiki/analyses/<slug>.md`, do NOT delete it. Prepend a single line at the top (directly under the frontmatter):

```markdown
> **Canonical version:** [[topics/<slug>]] — this analysis is kept as derivation history.
```

This preserves the trail of how the canonical page was reached.

### 6. Update `wiki/index.md`

- Add the new topic one-liner under the `Topics` section with a short description and source count.
- If the analysis was listed as a main entry point anywhere in the index, demote the analysis line to a "derivation history" note or remove it from prominent entry-point lists (the index should route readers to canonical pages).
- Add reciprocal `Related` links on the concept/entity pages the topic touches.

### 7. Append to `wiki/log.md`

```markdown
## [YYYY-MM-DD] sublime | <short title>

- Promoted: [[topics/<slug>]] (new | updated)
- Backflowed: [[sources/<slug>]] #<section> — <one-line what>
- Demoted: [[analyses/<slug>]] — prepended canonical pointer
- Index routing: <which entry point changed>
- Notes: <anything surprising, or why some candidate was left as-is>
```

## Decision rules

- If the content is entirely source-specific, skip topic creation and just backflow.
- If the content is entirely time-bound (dated advice that will rot), do not sublimate — leave the analysis as-is.
- If an existing topic covers the same thesis, **update it** rather than create a new one. Duplicate topics are the main failure mode.
- If the analysis is tiny and would duplicate one sentence in an entity page, just backflow — no new topic.

## Report structure

Always report the following 4 things to the user at the end of the run:

- What was promoted to `topics/` (or "no new topic — content was entirely source-specific").
- What was backflowed into `sources/` / `entities/` (or "existing pages already covered the facts").
- Which `index.md` entry point changed direction.
- What the source analysis now looks like (demoted pointer added, or unchanged if non-analysis trigger).

## Anti-patterns

- ❌ Deleting the originating analysis. It is derivation history, keep it.
- ❌ Creating a topic that duplicates an existing one because the slug was different.
- ❌ Copy-pasting the analysis body into a topic page without classification — topics should be thesis-first, not a recap.
- ❌ Leaving the index pointing at the analysis as the main entry point after a topic has been created.
- ❌ Forgetting to append to `log.md`.

## Reference

- `../query/SKILL.md` — query produces the analyses that sublime often consumes.
- `../ingest/SKILL.md` — ingest also touches topics when a new source refines a thesis; sublime is for promoting knowledge that is already in the wiki but not canonical yet.
- `../../../CLAUDE.md` — topic page format and the `concept vs topic vs entity` taxonomy.
