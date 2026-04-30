---
name: dive
description: Read deeply into `raw/` (typically `raw/repos/<repo>/`) to answer a specific question that the wiki cannot — either because the wiki is silent, or because the user already knows the wiki summary is insufficient, or because a recently updated repo carries information not yet ingested. Use when the user explicitly invokes `/dive` or says "dive into X", "read the source of X directly", "the wiki summary isn't enough — check the actual code", or similar. This is the exception lane to the wiki-first principle; prefer `query` if the wiki might already answer.
---

# Skill: Dive

Read the primary source (`raw/`) directly for a focused, structural deep-read. Unlike `query`, which consults `raw/` only as a fallback after the wiki fails, `dive` starts from `raw/` on purpose — because the user has already decided the wiki is not enough.

## When to dive (vs query / ingest)

| Situation | Use |
|---|---|
| "What does [[concepts/foo]] say about X?" | `query` |
| "Summarise this new repo into the wiki" | `ingest` |
| "The wiki summary of `foo` is shallow — show me exactly how the auth flow works in code" | **`dive`** |
| "This repo was updated yesterday; what changed in the retry logic?" | **`dive`** |
| "I know the wiki won't cover this detail, just read `raw/repos/foo/pkg/x.go`" | **`dive`** |

Anti-trigger: if the user has not signalled that the wiki is insufficient, prefer `query` first.

## Preconditions

- The user has either (a) explicitly invoked `/dive` or written "dive into ..." / "read the source of ..." / "check raw/ directly", or (b) stated that the wiki summary is insufficient.
- A concrete focus exists: a repo, a file range, a function name, a behaviour to trace. "Just dive into the codebase" without a focus is too broad — ask the user to narrow first.

## Recipe

### 1. Confirm the focus in one sentence

Before touching files, write a one-line focus to chat and wait for the user's steer (unless they already provided one). Examples:

- "Focus: trace how `framework`'s `TransactionAwareRetry` decides to retry vs. fail, starting from the call site in `Builder.php`."
- "Focus: read `raw/articles/2026-04-20-rfc-draft.md` end-to-end and summarise the proposed error-handling contract."

A bad focus ("read the whole repo") gets rejected with a narrower alternative.

### 2. Scan (not read) the relevant wiki pages — 60 seconds cap

- Check `wiki/index.md` for any page covering this source.
- If `wiki/sources/<slug>.md` exists, skim the Summary and Confirmed Facts only. **Do not deep-read the whole page.**
- Goal: avoid rediscovering what the wiki already states; start the raw read from a known baseline.
- Record mentally: "wiki says X, Y, Z — I will focus on what's beyond this."

This step is short on purpose. If you spend more than a minute here, you are doing `query`, not `dive`.

### 3. Hierarchical raw read

Reuse `ingest`'s *Large codebase* ordering but target-scoped:

1. **Anchor** — start from the entry point the focus names (a file, function, route, test).
2. **Immediate neighbours** — callers, callees, the types touched by the anchor.
3. **Cross-cutting context** — config loaders, middleware, retry/error paths when the focus involves runtime behaviour.
4. **Stop condition** — you can answer the focus question with concrete file:line citations. Do not keep reading "just in case".

For non-repo raw (articles / PDFs / notes), read fully — they are bounded in length.

### 4. Synthesize with line-level citations

Every claim cites a specific file and line range. The citation format is a markdown link:

```markdown
"`Builder::insert()` commits and then fires the post-commit hook at
[`raw/repos/framework/src/.../Builder.php:128-134`](../../raw/repos/framework/src/.../Builder.php)."
```

Put the line range inside the descriptor; the URL points at the file. Line numbers matter — this is the whole point of diving. If you cannot pin a claim to a file and line range, the dive is not complete.

Use response formats from `query`'s menu when they fit (comparison table, mermaid, decision tree).

### 5. Save the findings (default = analysis)

**Default: automatically file `wiki/analyses/YYYY-MM-DD-dive-<slug>.md`** with this frontmatter:

```yaml
---
title: <日本語タイトル or 英語 slug>
type: analysis
created: <today>
updated: <today>
sources: []            # dive reads raw directly, not via a source-summary
tags: [dive]
dive_focus: <one-line focus from step 1>
dive_target: raw/repos/<repo>/ | raw/articles/<file> | ...
---
```

Body = the synthesis from step 4, with all citations preserved.

**Exceptions that override the default:**

- **(c) source page update** — if the dive uncovers a **permanent fact** that the corresponding `wiki/sources/<slug>.md` or `wiki/entities/<slug>.md` is missing, **ask the user** before choosing this path: "The dive found that <X>. This looks like a permanent fact about `<repo>`, not a time-bound observation — update `wiki/sources/<repo>.md` directly instead of filing an analysis?" Wait for the user's yes/no.
- **(a) chat only** — if the user said "just tell me, don't save" or the finding is trivial (single line lookup, obvious answer), skip the file write. Mention in chat that nothing was saved.

The three paths differ in persistence: (a) chat = session only; (b) analysis = local machine, gitignored, snapshot; (c) source page = git tracked, shared, compound.

### 6. Append to `wiki/log.md`

```markdown
## [YYYY-MM-DD] dive | <short focus>

- Target: `raw/repos/<repo>/` | `raw/articles/<file>`
- Focus: <one-line>
- Files read: <N>, key citations: `<path>:<line>`, `<path>:<line>`, ...
- Outcome: <chat only | filed as [[analyses/<slug>]] | updated [[<source-page>]]>
- Wiki-scan baseline: <which wiki pages were skimmed before diving, if any>
- Follow-up: <if the dive raised questions worth a full ingest or a sublime pass, list them>
```

## Decision rules

- If the user's focus is genuinely answerable from the wiki — stop diving, suggest `query` instead.
- If the dive uncovers enough to rewrite the whole `wiki/sources/<slug>.md`, suggest a full `ingest` re-run rather than a patch update.
- If multiple dives on the same target are piling up as analyses, flag the user to consider `sublime` — the repeated deep-reads suggest a missing canonical hub (topic page or richer source page).
- Line-level citations are the contract; if you can't point to files/lines, the dive is not complete.

## Output expectations

Each dive ends with user-visible:

- The direct answer to the focus question, with file:line citations.
- Where the findings were saved (or why they weren't).
- One bullet listing any follow-up questions the dive *could not* answer (to avoid pretending the dive was exhaustive).

## Anti-patterns

- ❌ Reading the whole repo tree when the focus names a specific function.
- ❌ Skipping the 60-second wiki scan and rediscovering what `wiki/sources/<repo>.md` already says.
- ❌ Writing findings to a source page without asking (it is a tracked canonical page, not a scratchpad).
- ❌ Citations without line numbers (`raw/repos/foo/main.go` is insufficient; `main.go:42-56` is the minimum).
- ❌ Forgetting to append to `wiki/log.md` — the log is how future sessions learn that a dive happened.
- ❌ Treating `dive` as a general-purpose codebase Q&A skill. It is the exception lane, not the default lane.

## Reference

- `../query/SKILL.md` — default lane for wiki-first answers; dive is its complement.
- `../ingest/SKILL.md` — full-source summarisation; dive is focused and does not rewrite wiki pages by default.
- `../sublime/SKILL.md` — run after repeated dives on the same target to consolidate them into a canonical page.
- `../../../CLAUDE.md` — overall schema and the wiki-first principle that dive intentionally excepts.
