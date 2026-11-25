# Acting on observations — using one in this task, the skill-save control, and acting in-session

Load triggers: an open observation changes what you are about to do in this task, or its rule is about to be written where a later run reads it; the harness offers to save or propose a skill from the conversation; acting on an observation in-session (the staged edit, the status in the same turn)

The core skill carries the three contexts in which to act, the
outcome-level-ask test (Acting on Observations) and the log-and-defer
default (Surfacing Protocol), with a one-line statement of each rule below.
This file holds those rules in full. Reading an entry's body before a
resolve is in `observation-log.md`; the carrier pattern for a partial
action is in `observation-families.md`.

## Contents

- Using an open observation in this task
- The skill-save control
- When acting

## Using an open observation in this task

**Log-and-defer means the observation is the sole carrier of the change**,
and applying an insight to the work in front of you is not the same act.
Letting an open observation change what you do in THIS task is the point of
the log, with the user's consent at the point of use: when a loaded open
observation actually changes what you are about to do, surface it once per
session, at a natural break (never mid-task), in one line with accept /
opt-out — follow it in this task or not, never an offer to edit the skill —
and append the answer to its `use_evidence:` (How to Log). An opt-out
records its context and never closes the entry, since a rejection in one
context can be right in another; an unattended run appends `used` without
asking; an entry with no evidence line 30 days after its `date:` is offered
with the note that it has not been needed since it was logged. Writing the
rule anywhere a later run reads it — a state file the skill loads (registry,
dossier, config note), a prompt, a handoff doc, a project instruction file —
is acting on it. The test: **does it leave a durable change outside the
observation log?** The bridge disguise — "the rule has to live somewhere
until the review runs" — is answered by the observation itself; a parked
copy has no update path, so the next run reads both. A state file that
must point at the rule gets one line naming the owner and the pending
change, never a restatement (SKILL.md, "Acting on Observations").

## The skill-save control

**A harness's own skill-proposal or skill-save control is an install path,
not a staging path.** Where the environment offers to save or propose a
skill from inside the conversation — and its tool description may well say
that is how a skill change is delivered — that control writes the installed
copy; it produces nothing under `skill-updates/`. Never use it in a
workspace that stages there, unless the harness's own instructions name it
as the install route and forbid handing over a package: then stage first and
follow `references/skill-authoring.md` (editing rule 5, "the skill-card
route"). And before any in-session skill change, check
the staging manifest (`skill-updates/PENDING.md`) and today's
`skill-updates/<date>/` for the same skill: a review running in parallel
may already have staged it, built on the live file plus other changes.
Installing a conversation-side copy over that drops those changes, and
installing the review's copy afterwards silently reverts the control's —
a one-line rule turned into a merge conflict the user has to catch.

## When acting

When acting: small, clearly-additive, low-risk changes (a new rule, a
clarification, a factual fix) may be applied without waiting for the next
review — "directly" means *now*, not *in place*: the edit is still made on
a staged copy based on a fresh read of the live file and handed to the user
to install, in every environment and every context — staging-only has no
interactive exception, since a gate the user has to remember gets left
open. Substantial changes (restructuring, new
capabilities, changed methodology) and all new-skill creation: load
`references/skill-authoring.md` first and follow its editing and staging
rules. A principle that applies to skills generally goes to the
cross-cutting principles file (same reference).

**Set the status in the same turn you act.** An observation acted on
in-session must have its frontmatter updated — `status: actioned`,
`resolved: YYYY-MM-DD`, `resolution: what was done, and where it now lives`
— before the turn ends. The bookkeeping is the act that gets dropped, and
a stale `open` entry invites redoing finished work over a section that has
moved on; the write is the enforcement. **"Acted on" includes a fix
that lands as ordinary work** — the rule written into the instructions file,
the code corrected — with the observation not in mind; and a later session
finding the remedy already in place closes the entry the same way. Neither
looks like acting on an observation, which is why both are missed.
**Where the act also names the ids somewhere else** — a staging manifest
entry, a commit plan, a build's release notes — one command writes both:
`bash scripts/set-fields.sh <root> <plan> && <append the entry>`, never two
steps, since the second place is read as proof the work is done and the
field is what the queue reads.
