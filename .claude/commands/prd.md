---
description: Consolidate everything from the pipeline — /listen, /summary, /clarify, /assumptions, files, context — into a single clean PRD document.
allowed-tools: Read, Glob, Grep, Write
---

You are in PRD GENERATION MODE.

Your job: take everything from the pipeline so far — listen, summary, clarify, assumptions, files, conversations, corrections — and merge into one clean Product Requirements Document. Add nothing new. Remove nothing decided. Just organize.

## Step 1 — Gather input

Read EVERYTHING accumulated so far:
- Listen output (raw brain dump, context shared across messages)
- Summary output (structured understanding)
- Clarify summary (feature understanding, core decisions, constraints, parked threads)
- Assumptions summary (locked decisions, pre-resolved items, parked items)
- Any files the user referenced, attached, or pointed to (specs, docs, code, screenshots)
- $ARGUMENTS — if user passes a file path, read that as additional input
- CLAUDE.md and codebase context if relevant
- Any other conversation context — stray comments, corrections, side threads

Nothing gets dropped. If the user said it at any point, it's input.

## Step 2 — Check pipeline completeness

Before generating, check what's available and what's missing:

```
Pipeline check:
✅ Listen — [found / not found]
✅ Summary — [found / not found]
✅ Clarify — [found / not found]
✅ Assumptions — [found / not found]
✅ Files/context — [list what was found]

[If anything missing]: Missing [X] — the PRD will have gaps in [affected areas]. Run [missing step] first for a complete PRD, or say "go anyway".
[If all present]: Full pipeline available. Generating PRD.
```

## Step 3 — Generate PRD

Write to `docs/prd-[feature-name-slug].md`

Use the sections below as a menu — **include only sections that have actual input. Skip sections with nothing to say. Never write placeholder text like "[Not yet decided]" in the body — if a section is empty, drop it entirely.**

```markdown
# PRD: [Feature Name]

## Overview
[2-3 sentences — what this feature is, who it's for, what problem it solves]

## Background & Motivation
[Why this feature matters — user pain, business need, or technical necessity]

## User & Context
- **Primary user:** [who]
- **Environment/constraints:** [device, network, platform, anything relevant]
- **Key user goal:** [what the user is trying to accomplish]

## Functional Requirements
[Numbered list — each requirement is one clear statement]
[Group by flow or area if there are many]

## User Flows
[Core happy path step by step]
[Alternate flows — only if discussed]
[Edge cases — only if decided]

## Non-Functional Requirements
[Performance, security, scalability, offline behavior, etc.]

## Technical Constraints
[Stack, APIs, integrations, infra limits — only what's known]

## Out of Scope
[Anything explicitly parked, removed, or deferred]

## Open Items
[Parked assumptions still needing decisions]
[Skipped questions from clarify]
[Anything marked "decide later"]
[If pipeline steps were missing — note what sections are thin because of it]

## Decisions Log
| # | Decision | What was decided |
|---|----------|-----------------|
| 1 | [topic] | [decision] |
...
```

## Rules

1. **Add nothing new.** Every line must trace back to something shared or decided. If you can't source it, don't include it.
2. **Remove nothing decided.** Every locked assumption and clarify decision must appear somewhere in the PRD.
3. **Skip empty sections.** Don't include a section just because the template has it. No placeholders.
4. **Use the user's language.** Don't rephrase their decisions into corporate-speak.
5. **Parked items go to Open Items.** Don't silently drop them.
6. **Decisions Log is mandatory.** Every decision from the pipeline gets a row. This is the audit trail.
7. **Write the file.** Don't just print to chat — save to `docs/prd-[feature-name-slug].md`.

## After generating

Save the file, then say:

```
PRD saved to docs/prd-[feature-name-slug].md

Built from: [list which pipeline steps were available]
Sections included: [count]
Sections skipped (no input): [list]
Decisions logged: [count]
Open items: [count]

Next: run /chunk to review this section by section, or edit anything above first.
```

## If the user asks to edit

Apply their edit directly to the file. Confirm: "✓ Updated [file]: [what changed]". Don't regenerate — just patch.