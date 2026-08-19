# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Communication style
- Be concise. No preamble, no restating the task.
- Use ASCII visuals (boxes, arrows, trees) for architecture and flow explanations instead of paragraphs.
- ALWAYS end with a brief summary (2-3 bullet points max) of what changed and why.
- Maximum 400 words for plans or explanations.
- No verbose phrases like "Let me explain", "Here's what I'll do", "comprehensive review".

## Explainability (ChatGPT-style clarity)
- Prefer simple explanation before technical detail
- Always explain for mixed audience (PM + Engineer)
- Do not assume prior context — define key terms briefly
- Show cause -> effect (why something works or breaks)


## Response Structure (mandatory)
1. Summary (2–3 lines: what + why)
2. Simple explanation (plain English)
3. Breakdown (step-by-step or ASCII)
4. Problem / risks (if any)
5. Solution (clear, actionable)

Note:
- Stay within 400 words
- Keep structure, do not collapse into paragraphs

## Writing MD files with ASCII diagrams

When creating or editing any `.md` file that contains ASCII diagrams
(architecture, flows, boxes, trees), follow the rules in
[.claude/rules/md-diagrams.md](.claude/rules/md-diagrams.md).

Critical rules — apply always, even without re-reading the file:
- Wrap every diagram in a ```text fenced block
- NEVER use `--` inside diagrams (Word AutoCorrect turns it into `—` and breaks alignment)
- Use ASCII arrows (`->`, `<-`) not Unicode (`→`, `←`)
- Pick ONE char set per file: ASCII (`+ - |`) OR Box Drawing (`┌ ─ │`), never both
- Spaces only, no tabs

## Architecture Rules

Follow architecture and governance rules: [.claude/rules/architecture.md](.claude/rules/architecture.md)

## MVP Rules
- Every MVP must be a working vertical slice — one human-testable action proves it works.
- Never ship loose modules. If it can't be tested by hitting a URL, clicking a button, running a command, uploading a file, or any single human action, it's not done.
- Wire first, polish later. The wiring IS the MVP.

## Project Overview

This is a personal learning repository for Vishal Chaudhari — an experienced Product Manager (~12 years) building skills as an AI-Native PM. It contains learning materials, prototypes, and reference documents rather than a traditional application codebase.

## User Context

- **Domain:** Fintech — MSME lending, rural payments/banking, Account Aggregator ecosystem, risk/fraud/collections workflows.
- **Strengths:** PRD writing, cross-functional leadership, data/insights product building, rapid prototyping with AI tools (Claude Code as primary, Cursor as secondary, plus n8n, Replit).
- **Learning goal:** AI business transformation from a PM lens — opportunity identification, AI product design with measurable outcomes, evaluation literacy, and safe deployment in regulated fintech.

## How to Collaborate

- Default to crisp, actionable outputs: PRD sections, decision docs, experiment plans, metric trees, rollout plans.
- Ground AI concepts in fintech realities: compliance, risk, trust, explainability, auditability.
- Prefer "build-to-learn" with small prototypes and clear evaluation criteria over abstract theory.
- Use practical examples from fintech domains (lending journeys, underwriting, KYC, repayment/collections, agent/field workflows).


## Branch Strategy

Never commit directly to protected branches. Full workflow: [.claude/rules/git-workflow.md](.claude/rules/git-workflow.md)

**Environments:** `Local (laptop) -> Staging -> Prod`

| Branch      | Purpose                                   |
|-------------|-------------------------------------------|
| `prod`      | Production (live). Default. Protected.    |
| `staging`   | Integration + QA / UAT. Protected.        |
| `feature/*` | Local work in progress. Cut from staging. |

**Flow:** `feature/* -> staging -> prod`

No `dev` branch - your laptop is the dev environment, `staging` is the
integration branch where all PRs land.

## Commit Prefixes

`feat:` `fix:` `hotfix:` `wip:` `chore:` `docs:`