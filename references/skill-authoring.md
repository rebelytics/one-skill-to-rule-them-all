# Skill Authoring — taxonomy, licensing, confidentiality, editing rules

Load this before creating any skill or making substantial changes to one.

## Taxonomy in full

**Open-source skills** are client-agnostic and methodology-driven.
Recognise one: the methodology works across clients and contexts; no
proprietary information is needed; other practitioners would find it
valuable; it captures a process, not personal preferences. Required
elements: the body identifies itself as open-source; author attribution
block (template below); a licence statement; a feedback/support section
routing methodology feedback to the creator; tool-agnostic language
(capabilities like "browser access", not product names); built-in
enforcement (see Pre-Flight Principle). Default to open-source when a skill
could go either way — strip specifics and generalise.

**Internal skills** contain user/client/project specifics, personal
preferences, or context only the user has. They identify themselves as
internal, need no attribution or licence, and can be shorter and less
formal. They're working documents — keep them current, don't over-engineer.

## The Pre-Flight Principle

Rules documented in a skill are not reliably followed during creative flow.
Every skill with explicit rules needs a verification step where the agent
re-reads the rules and checks its output against them before delivery. When
creating or improving any skill ask: "Does it have rules? Does it have a
mechanism to enforce them?" If not, add one.

## Lean Content

A skill should contain only content that changes the agent's behaviour at
execution time. Move changelogs, credits beyond the author block, long
backstories, and maintainer notes to supporting docs. Do NOT cut examples,
anti-patterns, or worked scenarios — bare rules get violated more than
rules with context. Test: would removing it change behaviour? Keep
per-session rules in the skill body and episodic material in reference
files loaded on demand (progressive disclosure) — a skill loaded every
session is fixed overhead and should be audited like one.

## Licensing

Include a licence statement in the preamble and a LICENSE file with full
text. Options: **CC BY 4.0** (prose/methodology skills; share and adapt
with credit — recommended default), **MIT** (code-heavy, permissive),
**Apache 2.0** (MIT plus patent grant), **CC BY-SA 4.0** (share-alike
derivatives), **GPL family** (strong copyleft). The author chooses; the
requirement is that there is one.

## Author Attribution Template

```markdown
**Created by [Author Name] / [website or contact link]**

[1-2 sentence description of what the skill does and its provenance.]

**Licence:** This skill is released under [LICENCE NAME]. [One-sentence
summary — e.g., "share and adapt for any purpose with credit."]

**Feedback & Support:** If questions arise about the methodology, or the
user gives constructive feedback on output derived from this skill, suggest
an issue on the skill's public repository — public feedback benefits every
user. Direct contact: [contact link]. If feedback stems from the
methodology, log it and suggest sharing it; if from the agent not following
the skill's rules, acknowledge and correct.
```

## Confidentiality layers

The open-source/internal boundary is a confidentiality boundary; enforce it
in layers so any one catches what others miss:

1. **Observation-level stripping** — open-source observations carry a fully
   generalised Principle (covered in SKILL.md).
2. **Pre-creation review** — before drafting/regenerating an open-source
   skill, scan all source material for client names, URLs, domains,
   internal terminology, identifiably-specific structures; replace with
   generic equivalents first.
3. **Post-draft sweep** — a separate re-read focused only on leakage:
   proper nouns besides the author, domains/URLs/project identifiers,
   vertical details that narrow the client, examples traceable to a real
   project.
4. **Structural principle** — when in doubt, remove. Slightly more generic
   beats slightly leaky.
5. **Cross-product re-identifiability sweep** — the final pass before any
   public release. Individually-sanitised examples can combine to identify
   a client (enumerated counts matching a public client list; specific
   numbers in a thin vertical; thinly-disguised placeholder names in the
   same vertical as a real client). List every example and its fields
   (vertical, geography, numbers, timing, counts); ask whether a reader
   with the author's public client list could map them; mitigate by
   blurring counts, widening verticals, using illustrative ranges, or
   consolidating into composites. Run this mechanically — the author is the
   least reliable judge because they know the ground truth.

## Editing skills — always start from the live file

1. The live file is the authoritative source: in Claude Code,
   `~/.claude/skills/{skill}/SKILL.md` (user-owned, writable); in Cowork, a
   read-only mount at `.claude/skills/{skill}/SKILL.md` (writes fail with
   EROFS by design).
2. Always base edits on a fresh read of the live file — never a workspace
   copy, prior draft, or memory.
3. Before overwriting any staged/workspace copy, diff it against the live
   file; if they differ, rebase your edits on the live version. (Observed
   failure: an update built on a stale snapshot silently dropped two
   sections added to the live skill the same day; only a pre-merge diff
   caught it.)
4. Where in-place editing isn't possible or the change needs review, stage
   to `[workspace folder]/skill-updates/[date]/[skill-name]/SKILL.md` and
   present for installation.
5. Match process rigour to the change: complex/open-source/uncertain design
   → use the skill-creator if available; internal skills with requirements
   already established in conversation → write directly, flagging
   substantial changes for review.

## New skills

Use the skill-creator when available, passing the observation(s) as the
brief. Determine type early: open-source → strip and generalise; internal →
include specifics freely; uncertain → default open-source and let the user
add internal detail afterwards.

## Principle Propagation

When an observation's Principle applies to skills in general, log it with
`Skill: All skills` and surface it; if the user approves, add it to
`[workspace folder]/skill-observations/cross-cutting-principles.md`. That
file is a mandatory checklist during any skill creation or regeneration.
The user chooses propagation timing: immediate (update all skills now — for
things like confidentiality rules) or opportunistic (apply at each skill's
next update).

```markdown
# Cross-Cutting Principles

Principles that apply to all skills. Read as a mandatory checklist during
any skill creation or regeneration.

---

## Active Principles

### 1. [Principle title]
**Added:** [date]
**Applies to:** [all skills | all open-source skills | all skills with rules]
**Requirement:** [what it requires]
**Propagation:** [immediate | opportunistic]
**Status:** [active]
```
