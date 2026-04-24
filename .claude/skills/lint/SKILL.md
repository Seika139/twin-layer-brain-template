---
name: lint
description: Audit the wiki's health. Produce a five-section fixed-format report (auto-fixable / needs review / missing pages / unsourced claims / follow-up questions). Do not auto-fix. Use when the user says "lint" or periodically (~every 10 ingests).
---

# Skill: Lint

Diagnose what's broken in the wiki *and* where it should grow.

## Preconditions

- `wiki/` populated with some content (a totally empty wiki can't be lint'd).

## Recipe

### 1. Enumerate the wiki

- List all pages under `wiki/{entities,concepts,sources}/`.
- Build a link graph: for each page, which `[[wiki-links]]` does it contain, and which pages link back?

### 2. Run the five checks

Run all five, always, even if some return zero findings.

#### 1. Auto-fixable

Issues that are trivially correctable but still need user confirmation:

- Broken `[[wiki-links]]` — target file doesn't exist.
- Frontmatter drift — missing required fields (`title`, `type`, `created`, `updated`), wrong `type` values, bad date format.
- Typo-level inconsistency — `[[entities/Foam]]` vs `[[entities/foam]]`.
- Orphan pages listed in `index.md` but file missing, or file present but not in index.

#### 2. Needs review

Issues requiring the user's judgment:

- Contradictions between pages (conflicting claims with different citations).
- Stale pages — all cited sources older than 6 months *and* newer sources on overlapping topics exist.
- Pages whose content disagrees with a newer source that was ingested after.
- Pages that exist but have no outbound links (dead-end in the graph).
- **Sublime candidates** — a dated analysis that is now cited by 3+ other pages, or a recurring claim repeated across multiple concept/entity pages without a corresponding topic. Flag these as "candidate for sublime: ..." so the user can run the sublime skill.

#### 3. Missing pages

- Concepts / entities referenced by name 3+ times across the wiki but without their own page.
- `[[wiki-links]]` targeting a path that has never been created.

List as: `<term>` — referenced in `[[page1]]`, `[[page2]]`, `[[page3]]`.

#### 4. Unsourced claims

- Assertions in `entities/` or `concepts/` pages that have no `[[sources/...]]` citation.
- Pages with empty `sources:` frontmatter array when their body makes factual claims.

Format: `[[pages/<slug>]]#<section>` — claim: "<snippet>".

#### 5. Follow-up questions

- Open questions listed in pages but not investigated.
- Implied questions — relationships hinted but not explored.
- **Specific new sources worth ingesting** — URL-level suggestions filling data gaps. For example: "No page covers how Foam's graph view differs from Obsidian's in 2026 — suggest ingesting <https://foambubble.github.io/foam/...>."

### 3. Output format

Fixed five-section checklist, in this order:

```markdown
# Lint report — YYYY-MM-DD

## 1. Auto-fixable (N findings)

- [ ] Broken link `[[concepts/foo]]` in [[sources/2026-04-21-bar]] — target missing. Create `concepts/foo.md` or remove the link?
- [ ] ...

## 2. Needs review (N findings)

- [ ] Contradiction: [[entities/x]] claims A (cites [[sources/old]]), but [[sources/new]] claims ¬A.
- [ ] ...

## 3. Missing pages (N findings)

- [ ] `CQRS` — referenced in [[concepts/event-sourcing]], [[sources/2026-04-10-martin-fowler]], [[sources/2026-04-15-gregory-young]].
- [ ] ...

## 4. Unsourced claims (N findings)

- [ ] [[entities/foam]] §features claim: "has the best graph view of any editor" — no citation.
- [ ] ...

## 5. Follow-up questions (N findings)

- [ ] Does [[concepts/llm-wiki-pattern]] reconcile with Retrieval-Augmented Generation? Suggested ingest: <https://arxiv.org/abs/2005.11401>.
- [ ] ...
```

### 4. Append to `wiki/log.md`

```markdown
## [YYYY-MM-DD] lint | <one-line summary>

- Auto-fixable: N
- Needs review: N
- Missing pages: N
- Unsourced claims: N
- Follow-up questions: N
- Report: filed as <wiki/analyses/YYYY-MM-DD-lint.md | inline only>
```

### 5. Optionally file the report

If the user wants the report persisted, file it at `wiki/analyses/YYYY-MM-DD-lint.md` (gitignored by default — lint reports are snapshots). Do *not* promote lint reports into `wiki/concepts/` or `wiki/entities/` unless they're a curated retrospective.

## Do not auto-fix

Even "auto-fixable" issues go through user review. The whole point of the diagnostic/generative split is that the user sets direction — the agent surfaces, doesn't decide.

## Recommended cadence

- After ~10 ingests.
- Monthly.
- When the user says "the wiki feels stale".
- Before deciding to refactor the schema.

## Anti-patterns

- ❌ Auto-fixing.
- ❌ Skipping sections when they're empty (always output all 5 with `(0 findings)`).
- ❌ Only reporting diagnostic findings (sections 1–4) without generative (section 5).
- ❌ Forgetting to append to `log.md`.

## Reference

- 詳細方針: `references/karpathy-llm-wiki.md`
