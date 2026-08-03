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

**Embedded commands are pre-flight items too — execute before you ship.**
Prose rules and command snippets fail differently: a prose rule is
re-interpreted in context on every run, so ambiguity can be caught at
execution time; an embedded command runs verbatim, unattended, forever —
and a subtly wrong command can read as correct on every re-read
(`git log -1 --format=%cI --reverse` returns the NEWEST commit, because
`-1` applies before `--reverse`, while the plausible reading is "oldest").
Any command embedded in a skill must be executed once against real data,
with its output inspected for plausibility, before the skill file is
saved. An unverified snippet is among the highest-risk lines in a skill:
it ships bugs that no re-read can catch.

**A verification command that AGREES with you is the one to distrust.**
Executing a snippet once, as above, does not catch this class: the command
runs cleanly and returns a plausible number. A check that contradicts a
strong prior gets investigated; a check that confirms one never does, so a
right answer from a wrong instrument teaches you to trust the instrument.
The usual form is an aggregated count, because a count is not a listing and
a tool that collapses output for readability under-reports without saying
so: `git status --porcelain --ignored` prints one line for an ignored
DIRECTORY, so a `grep -c` over it reports "1" where five files are ignored,
and only `--untracked-files=all` expands it. Before shipping a verification
step that reports a number, confirm what the number's unit is, and
enumerate and read the set whenever enumeration is cheap.

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

**Private client sharing** is a third channel with its own rights framing:
a client-agnostic skill shared privately with one client is NOT open source
and NOT internal. Keep the attribution block; replace the licence statement
with a short usage notice (e.g., "shared privately for internal use; please
don't redistribute without checking with the author"); no LICENSE file
needed. All confidentiality sweeps still apply — other-client information
must not leak even when the recipient is a known client. Do not treat "not
internal" as "therefore open source": distribution channel determines the
rights framing, not just the feedback routing (see the distribution-channel
note below).

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

**Distribution-channel note:** the template's feedback routing assumes
public-repo distribution. Only reference a repository URL once that
repository actually exists — never write a reference to an artefact before
the artefact exists. Until publication, route feedback to direct author
contact only; when the skill is published, inject the repo URL at publish
time. When an open-source skill is distributed privately (shared directly
with a client rather than published), keep the direct-author-contact
routing — a public-repo reference is wrong for that channel.

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
   `~/.claude/skills/{skill}/SKILL.md`; in Cowork, a read-only mount at
   `.claude/skills/{skill}/SKILL.md` (writes fail with EROFS by design).
   Do not edit skill files in place, in any environment — staging-only is
   what keeps the autonomous review safe.
2. Always base edits on a fresh read of the live file — never a workspace
   copy, prior draft, or memory.
3. Before overwriting any staged/workspace copy, diff it against the live
   file; if they differ, rebase your edits on the live version. (Observed
   failure: an update built on a stale snapshot silently dropped two
   sections added to the live skill the same day; only a pre-merge diff
   caught it.)
4. Stage every update to
   `[workspace folder]/skill-updates/[date]/[skill-name]/` — the FULL
   skill directory (SKILL.md plus references/, scripts/, assets/ where
   present), never SKILL.md alone — and present it for review and
   installation; nothing goes live until the user installs it. Where no
   presentation/upload tool exists (e.g. Claude Code CLI), present the
   staged path and a change summary in chat instead; staging-only applies
   in every environment — it's the review loop's safety property, not a
   filesystem constraint. For any
   skill with supporting files, zip the staged directory into a `.skill`
   bundle and present the bundle, never the bare SKILL.md: a single-file
   delivery convention applied to a multi-file skill truncates it
   silently (the install succeeds, the skill loads, and the missing
   pieces only surface when a reference load or script call fails
   mid-task). **Pre-delivery gate — two items, checked at the moment of
   delivery, not just at drafting time:** (1) every `references/`,
   `scripts/`, `assets/` path in the staged SKILL.md body has its file in
   the staged set; (2) if the skill is multi-file, the delivery artefact
   is the `.skill` bundle — bare file links fail this gate even when all
   files are staged. (Reading this rule while drafting does not enforce
   it at delivery; run the gate as the last step before presenting.)
   Packaging hygiene: before zipping, sweep the staged tree for build
   artefacts (`__pycache__/`, `*.pyc`, `.DS_Store`, `.~lock.*`) left by
   in-session checks, and read the archive listing back after zipping —
   the listing is the cheap verification that catches leaked artefacts.
5. When seeding a staged copy by copying from the read-only mount, reset
   write permissions immediately (`chmod -R u+w` on the staged path, or
   `cp --no-preserve=mode`) — the mount's read-only mode travels with
   the copy, for directories as well as files, and the follow-up edit
   otherwise fails with a permission error.
6. Match process rigour to the change: complex/open-source/uncertain design
   → use the skill-creator if available; internal skills with requirements
   already established in conversation → write directly, flagging
   substantial changes for review.

## Verifying relocations and restructures

When content is relocated verbatim (splits into core + references, merges,
restructures), "nothing was lost" is checkable mechanically — but only with
a two-tier check:

1. Enumerate every added/moved line via `diff` of the old base vs the new
   base.
2. Exact-match each non-empty line against the restructured file set
   (`grep -F`).
3. For misses, substance-check via a distinctive mid-line substring before
   concluding loss — most misses are container artifacts (heading-level
   changes, list-to-prose adaptation, re-wrapped lines splitting a phrase
   across newlines), not real losses.
4. Word-count sanity check per file.

One tier alone either misses losses (substance-only) or cries wolf
(exact-only). Additionally, inventory the original's enforcement
mechanisms (checkpoints, assertions, invariants, mandatory-write rules,
defaults) as an explicit checklist — compression preferentially destroys
enforcement machinery because it reads as redundancy — and sweep any "pure
restructuring" change for net-new behaviour, which hides well in a large
rewording diff.

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
