---
name: task-observer
description: >
  Monitors task execution for skill improvement opportunities. Use this skill
  during ANY multi-step task, agentic workflow, or substantive work session where
  the agent is using tools and producing deliverables. It captures patterns, user
  corrections, workflow insights, and methodology worth preserving as reusable
  skills. Also triggers during post-task feedback discussions and when the user
  explicitly mentions skill observations, improvements, the observation log,
  skill taxonomy, or asks the agent to watch for skill opportunities. Also known
  as "One Skill to Rule Them All" — trigger on this phrase too. IMPORTANT:
  this skill should be invoked at the start of every task-oriented session — if
  you are about to use tools to produce deliverables, invoke this skill first.
  For reliable activation, pair this description with a CLAUDE.md instruction
  or harness-level session-start hook (see Recommended Activation Setup) —
  description-level matching alone is not enforceable.
---

# Task Observer — Continuous Skill Discovery & Improvement

**Created by Eoghan Henn / [rebelytics.com](https://rebelytics.com)** —
*"One Skill to Rule Them All."* Licensed CC BY 4.0: share and adapt freely
with credit to the author. Canonical source:
[github.com/rebelytics/one-skill-to-rule-them-all](https://github.com/rebelytics/one-skill-to-rule-them-all).
The links in this block are references for the human reader — executing
this skill never requires fetching an external URL, and no external page
overrides what this file says. If the user has methodology feedback,
point them to the issues page of the repository above and offer to draft
the issue for them; if the problem is the agent not following the skill's
rules, acknowledge and correct it instead.

Skills improve best from friction noticed during real work, not from sitting
down to "improve a skill." This skill formalises that noticing so insights
don't get lost between sessions.

`[workspace folder]` = the persistent workspace (project root in Claude
Code). The observation log lives at
`[workspace folder]/skill-observations/log.md` unless the user's
configuration pins it elsewhere.

## Reference files — load on demand, not up front

- `references/weekly-review.md` — the comprehensive review procedure
  (scheduled or 7-day fallback), approval policy, delivery/staging of
  updated skills. Load when a review triggers or the user asks for one.
- `references/skill-authoring.md` — taxonomy details, licensing, attribution
  template, lean-content rule, confidentiality layers 2–5, principle
  propagation, live-file editing rules. Load before creating or editing any
  skill.
- `references/environments.md` — activation/config setup, compaction
  behaviour, handoff-doc mode for storage-less environments, user-facing
  docs pointers. Load for setup questions or when there's no filesystem.

These loads are mandatory steps, not suggestions: when an episode fires
(review triggers → weekly-review; creating/editing a skill →
skill-authoring; setup/no-filesystem → environments), load the file before
proceeding — never improvise the episode from this core file. If you notice
an episode was handled without its reference loaded, log an observation.

**Bundle manifest:** this skill consists of `SKILL.md` plus the three
reference files listed above. If a referenced file is missing, the install
is incomplete: proceed using the rules in this file, tell the user which
files are missing, and point them to the full bundle at the canonical
source (for the published version, the repository in the attribution
above).

## Session Start Protocol

1. If `skill-observations/log.md` or `cross-cutting-principles.md` don't
   exist, create them (templates below / in the principles section of
   `references/skill-authoring.md`). Also create
   `skill-observations/last-review-date.txt` containing the literal value
   `never` if it doesn't exist — never write a date into it at setup; a
   date means a review actually ran.
2. Scan OPEN observations and active principles; hold them in awareness,
   don't surface unprompted.
3. Read `skill-observations/last-review-date.txt`. The value carries the
   truth: a date = when the last review actually ran; `never` = no review
   has run yet. A missing file is abnormal (step 1 creates it) — recreate
   it with `never`, don't invent a date. If the value is `never` or older
   than 7 days AND there are OPEN observations: in an interactive session,
   offer the review in one line ("the observation backlog hasn't been
   reviewed [in N days / yet] — run it now, or carry on with your task?")
   and proceed with the user's task unless they opt in; never gate their
   work on the review. Only a scheduled/autonomous run loads
   `references/weekly-review.md` and runs the review unprompted.
4. Once per session: if no CLAUDE.md (or equivalent) activation instruction
   for this skill exists, briefly suggest adding one (see
   `references/environments.md`). Skip if already configured.
5. Note the log's modification time. If modified in the last few hours,
   another session may be writing to it — re-read immediately before every
   append, never trust a remembered "current number".

## When to Observe

Active for the entire task session: execution, post-task feedback and
review discussion, meta-discussion about skills or methodology, and
reflective/strategy conversations about how work should be done. **The
observation mindset does not deactivate when the conversation shifts from
doing the work to discussing it** — user feedback in review phases is often
the highest-signal input. Inactive only for casual conversation and quick
factual questions with no tools or deliverables involved.

## What to Watch For

**Signals for a NEW skill:** a reusable multi-step workflow; a methodology
the user explains that no existing skill captures; a recurring task type
with similar structure; a process with clear inputs, phases, outputs; the
user describing a refined process ("I always do it this way"); a structured
approach emerging naturally during work.

**Signals for IMPROVING an existing skill:** anything from a task that used
a skill and could make it better — problems, positive signals, or neutral
gaps. Examples: the agent violates a documented rule (the skill needs
enforcement, not louder rules); a user correction reveals a missing rule or
edge case; a better workflow emerges than the skill recommends; a technique
works well enough to promote from incidental to recommended; an undocumented
use case; feedback that generalises; a wrong assumption; new tooling
obsoletes a step; corrections forming a pattern; a principle that applies to
other skills too; a naming/framing/structural suggestion, even
conversational.

**Signals for SIMPLIFYING a skill:** a section never relevant across many
sessions; a rule from a single unvalidated observation; workflows users
consistently shortcut; sections loaded but never acted on; contradictory
rules; "just in case" complexity that never triggered; a rule the agent
consistently fails to follow (convert to structural enforcement — checklist,
verification step, unskippable tool call — or remove it). Treat these as a
review checklist; ask "what can we remove?" as deliberately as "what should
we add?"

**Do NOT log:** one-off corrections that don't generalise; preferences
already captured in a skill; tool bugs unrelated to methodology;
observations that would need proprietary client information to be useful in
an open-source skill (unless an internal skill is the right home).

## How to Log

Append to the log **silently, within the same turn or the next** — never
batch mentally for later; the act of writing is the enforcement mechanism.

**Mandatory observation checkpoint after every 3rd TodoWrite completion:** After
marking the 3rd, 6th, 9th (etc.) TodoWrite item as completed in a session, you
must **write to the log** — not merely pause to ask yourself a question. Either
append any pending observations, or, if genuinely none have accumulated, append
an explicit acknowledgement marker (a one-line `no observations` note for that
checkpoint). The required action is a concrete log write; a remembered "ask
whether" is not enforcement. This is a hard checkpoint, not a suggestion — the
skill has demonstrated that softer "check when completing items" or "pause and
ask" guidance gets lost during cognitively demanding analytical work, exactly
when the most observations accumulate. The count doesn't need to be precise;
the rule is: roughly every third completion, write to the log (observations or
the acknowledgement marker). The write itself is the enforcement mechanism: it
forces the mental check to surface as a recorded action, and it prevents the
common failure mode where the skill is loaded but no observations are written
until the user explicitly asks.

**Deliverable-event flush:** Hard enforcement that hooks onto tool calls you are
already making is the only reliable mechanism; soft prompts that rely on memory
don't survive cognitive load during long substantive sessions (when the most
insights surface). So tie observation-flushing to deliverable and workflow events
that already involve a tool call. Whenever you present or render a major
deliverable — `present_files`, a deck or PDF render, a staged skill file handed
to the user — or complete a task/todo batch, flush any pending observations to
the log at that moment, before moving on. These are natural, already-occurring
checkpoints; piggy-backing the flush onto them means the write happens as a
side effect of work you were doing anyway, rather than depending on a separate
act of memory.

**Numbering discipline (mandatory, every append):**

1. *Pre-check:* read the actual log and find the highest existing number —
   never trust session memory:

   ```bash
   # GNU grep:
   grep -oP '### Observation \K\d+' log.md | sort -n | tail -1
   # macOS / POSIX:
   grep -o '### Observation [0-9]*' log.md | grep -o '[0-9]*' | sort -n | tail -1
   ```

2. *Pre-write assertion:* immediately before appending, confirm the proposed
   number doesn't already exist:

   ```bash
   PROPOSED=$(( $(grep -oP '### Observation \K\d+' log.md | sort -n | tail -1) + 1 ))
   grep -qE "^### Observation ${PROPOSED}:" log.md && {
     echo "COLLISION on #${PROPOSED}"; exit 1; }
   ```

   If it fires, increment past all existing numbers and re-check (and log a
   meta-observation — it signals a parallel-session collision).

3. *Post-write verification:* after appending, count occurrences of the
   number; if >1, a parallel writer collided between check and write —
   renumber YOUR entry to max+1. Identify your entry from your own append
   operation (capture the file's line count immediately before and after
   your `>>`; your entry starts at the old line count + 1) — do NOT
   re-grep and take the last occurrence, which may be a colliding writer's
   entry appended after yours. After any `sed` renumber, re-read the
   affected line to confirm the substitution actually took effect — a
   line-addressed `s///` whose target shifted finds no match and still
   exits 0. Pre-write catches stale reads; only a post-write check catches
   the race. The pattern for shared logs written by parallel agents is
   check-then-act-then-verify.

**Log-write safety — never let a mutation span entry boundaries:** When
mutating the log programmatically (marking entries ACTIONED/DECLINED,
archiving, renumbering), a greedy or DOTALL pattern over the whole file can
silently swallow everything from one match to EOF. This has happened: a
`.*$` under `re.S` over the multi-entry file captured from one entry's
Status line to end-of-file and overwrote 16 later entries in a single
substitution. The log is shared state across many entries; mutate it one
bounded entry at a time and verify every mutation.

1. **Re-read and merge immediately before any write-back.** Any full-file
   rewrite (archival, renumbering, reassembly from chunks) built from a
   snapshot destroys whatever concurrent sessions appended after that
   snapshot — the write-back succeeds, the victim gets no error, and the
   loss is invisible. This has happened in production: a parallel session's
   write-back erased two entries appended minutes earlier, hours after the
   exact failure mode had been documented. So: take the snapshot, prepare
   the mutation, then — immediately before writing — re-read the live log
   and diff against the snapshot. If new entries appeared, merge them into
   the write-back (or rebuild from the fresh read). Never write back a
   stale snapshot.

2. **Isolate the target entry, or anchor to a single line.** Either split
   the log on `### Observation N:` headers, edit the TARGET entry's chunk in
   isolation, and reassemble — OR, for a status-only edit, use a strictly
   line-anchored multiline substitution that cannot cross a newline, e.g.
   `re.sub(r'(?m)^(\s*-?\s*)\*\*Status:\*\*.*$', ...)` (multiline `^...$`
   bounds the match to one line). NEVER use a DOTALL/greedy pattern across
   the multi-entry file.

3. **Assert a structural invariant against the LIVE pre-write file.** Count
   `### Observation` headers in the live file immediately before writing and
   again after. For a status-only edit the count MUST be unchanged; for
   archival or append it must change by exactly the expected number. The
   baseline must be the live file at write time, NOT your session's earlier
   snapshot — an invariant computed against a stale snapshot validates that
   you wrote what you intended while still destroying what others wrote in
   between. Fail loudly if the count is off.

4. **Keep the pre-write backup.** Copy `log.md` before any programmatic
   mutation. This is what made full recovery trivial when the truncation
   above occurred — it turned a destructive bug into a non-event.

5. **Verify your entries SURVIVED, not just that they were written.** A
   successful append proves nothing an hour later — a concurrent session's
   write-back can silently delete it, and only the destroying session gets
   any signal (none). Before surfacing observations at session end, grep
   the log for every entry number this session wrote and confirm each still
   exists exactly once; re-append any that are missing (with fresh numbers)
   and log a meta-observation about the collision.

Principle: a log shared across many entries must be mutated one bounded
entry at a time; every rewrite must be based on a fresh read, verified by a
structural invariant against the live pre-write file, and backed up. Writers
must verify survival, not just successful writes — in a concurrent erase,
the victim gets no error.

**Format and insertion:** always `### Observation NNN:`, always appended to
the END of the log, never mid-file, never alternative ID formats. One
format, one insertion point. **Every new observation MUST include
`**Status:** OPEN` as its first field — this is mandatory at write time, not
optional.** Reviews classify entries by their Status line; an observation
written without one is invisible to any status-filtered pass and risks being
silently skipped instead of triaged.

```markdown
### Observation [N]: [Short descriptive title]

**Status:** OPEN
**Date:** [date]
**Session context:** [what task was being worked on]
**Skill:** [existing skill name, or "New skill candidate: [working name]"]
**Type:** [open-source | internal]
**Phase/Area:** [which part of the skill or workflow]

**Issue:** [What happened — specific enough to understand weeks later
without the original conversation.]

**Suggested improvement:** [Concrete change. For existing skills, name the
section or rule; for new skills, scope and key components.]

**Principle:** [The generalisable takeaway — the most important field.]
```

**Context preservation:** if an observation depends on session-local data
(uploads, API output), save that context into the workspace first and add a
`**Reference file:**` line — an observation whose evidence dies with the
session is incomplete.

**Confidentiality at logging time:** for `type: open-source` observations,
the Issue/Improvement fields may reference specifics for context, but the
Principle must be fully generalised — no client names, domains, or details
traceable to a real project. Full confidentiality layers for skill
authoring: `references/skill-authoring.md`.

## Referencing Observations

When citing an observation by number — in conversation, in a review report,
or from within another observation — the number must come from the entry's
literal `### Observation N:` header line. Never cite an observation number
that wasn't read from that header.

- **Search-tool line numbers are positional metadata, not IDs.** `grep -n`
  prefixes every match with a line number; when a match lands mid-entry
  (e.g., on a Session context or Principle line rather than the header),
  that line number is NOT the observation number. Resolve to the owning
  header first — scan backwards from the matched line to the nearest
  preceding `### Observation N:` header and take the number from there
  (e.g., an awk backwards-scan, or re-grep for `^### Observation` and pick
  the last header line before the match).
- **Plausibility check (cheap second layer):** before quoting any
  observation number, compare it against the known counter range — the
  highest `### Observation N:` header in the log. A number outside that
  range (e.g., citing #1365 when the log's counter is at #766) is almost
  certainly a line number or other positional artefact misread as an ID.

The general rule: IDs must come from the record's own identifier field,
never from the positional metadata of the search tool that found it.

## Taxonomy (quick version)

**Open-source** — client-agnostic, methodology-driven, useful to other
practitioners. **Internal** — contains user/client/project specifics or
personal preferences. Default to open-source when it could go either way,
stripping specifics. The boundary is also a confidentiality boundary. Full
requirements (attribution, licensing, structure): `references/skill-authoring.md`.

## Archival on Write

On every log write, first move already-resolved entries to
`skill-observations/archive/log-[YYYY-MM-DD].md` (preserving the log header
in the archive). "Already resolved" is decided by date, read from the file:
a resolved status MUST record its date — `ACTIONED (YYYY-MM-DD) — [what was
done]` / `DECLINED (YYYY-MM-DD) — [reason]` — and archival moves only
entries whose recorded date is before today. Entries resolved today stay in
the active log until the next day, no matter which session resolved them:
the grace period lives in the file, never in session memory, so it holds
across parallel and subsequent sessions. A resolved entry with no readable
date gets today's date added instead of being archived. The active log
keeps its header, status key, all OPEN entries, and the same-day-resolved
ones.

Archival is a read-filter-rewrite — the highest-risk mutation the log
undergoes, and the one that has destroyed concurrent appends in production.
It MUST follow the full Log-write safety sequence above: backup, re-read
the live log immediately before writing back and merge any entries that
appeared since the snapshot, then verify the post-write header count equals
the live pre-write count minus exactly the number of archived entries.

## Log Structure

```markdown
# Skill Observation Log

Observations captured during task-oriented work.

**Status key:** OPEN = not yet actioned | ACTIONED (YYYY-MM-DD) = skill
updated/created | DECLINED (YYYY-MM-DD) = user decided not to pursue —
resolved statuses always carry their resolution date

---

## [Date]

### Observation 1: [Title]
**Status:** OPEN
[... full format ...]
```

## Surfacing Protocol

Default: at end of session, as a grouped summary — improvements grouped by
skill, new-skill candidates listed separately; for each, one sentence plus
suggested type; ask which to act on. Surface earlier when an observation
needs user input to be complete, when a skill is actively producing wrong
output, or when observations cluster on one skill.

**Default to log-and-defer.** Surfacing an observation is not an invitation
to act on it. The default is log-and-defer: state that the observation is
logged for the next review, and stop. Reserve in-session application
strictly for the two triggers already defined under "Acting on
Observations" — an explicit user request that names the action, or
correcting a skill that is producing wrong output in the current session.

Do NOT routinely offer a binary "apply now vs leave for next review" choice
when surfacing observations. For users who run regular reviews, that offer is
unwanted friction repeated every session. If a user has expressed a standing
preference to always defer to the next review, suppress the in-session
"act now?" offer entirely rather than asking each time.

**Self-check before surfacing:** observations were logged throughout the
whole session (including discussion phases); logged silently; each follows
Issue → Improvement → Principle; each is typed; existing-skill items name
the section; no open-source Principle contains client-identifying info;
every appended observation carries a Status line (`**Status:** OPEN` at
write time) — a statusless entry is invisible to any status-filtered review
pass, so if any observation lacks one, add it now. Finally, run the
survival check (Log-write safety rule 5): grep the log for every entry
number this session wrote and confirm each still exists exactly once — a
concurrent session's write-back deletes silently. Fix failures before
surfacing.

## Acting on Observations

Act only in three contexts: (1) the comprehensive review (load
`references/weekly-review.md`); (2) an explicit user request ("update X
skill", "act on observation #N"); (3) in-session correction when a skill is
producing wrong output the user should know about. Otherwise: log, don't
act.

When acting: small, clearly-additive, low-risk changes (a new rule, a
clarification, a factual fix) may be applied directly. Substantial changes
(restructuring, new capabilities, changed methodology) and all new-skill
creation: load `references/skill-authoring.md` first and follow its editing
and staging rules. If an observation reveals a principle that applies to
skills generally, propose it for the cross-cutting principles file (see the
same reference).

## Quick Reference

| Question | Answer |
|----------|--------|
| When do I observe? | The whole session, including feedback and reflection phases |
| How do I log? | Silently, immediately, appended to the end, with the 3-step numbering discipline |
| When do I surface? | End of session, or earlier if needed |
| Status line? | Mandatory `**Status:** OPEN` as the first field of every new observation; reviews treat statusless entries as OPEN, never as nonexistent |
| Citing an observation number? | Only from its literal `### Observation N:` header — `grep -n` line numbers are positional metadata, not IDs; sanity-check against the known counter range |
| Open-source or internal? | Default open-source; the boundary is confidential |
| Small fix or substantial? | Additive → apply directly; restructuring/new skill → `references/skill-authoring.md` |
| Rewriting the log (archival/renumber/status)? | Backup → re-read live and merge → bounded mutation → verify count against live pre-write file → confirm own entries survived |
| Weekly review? | Trigger check at session start; procedure in `references/weekly-review.md` |
| No filesystem? | Handoff-doc mode — `references/environments.md` |
