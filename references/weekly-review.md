# Comprehensive Review (scheduled or fallback)

Cross-checks all OPEN observations against all skills, propagates
cross-cutting principles, and applies improvements that don't need user
input. Two modes:

- **Scheduled autonomous review (preferred):** a recurring task (e.g.
  Mon/Wed/Fri mornings) via the platform's scheduler. Runs without the user
  present and applies non-escalated observations autonomously.
- **In-session 7-day fallback:** fires at session start when BOTH are true:
  no scheduled review is registered (or none succeeded in 7+ days), AND
  `skill-observations/last-review-date.txt` is missing or >7 days old.
  Inform the user it's running; do Step 0 first.

## Approval policy

**Interactive (user present):** always present observations grouped by
skill (number, title, one-sentence summary), flag judgment calls as "needs
your input", and wait for blanket or selective approval before applying.

**Scheduled autonomous (user absent):** apply non-escalated observations by
default — safety comes from the staging-plus-review pattern (nothing is
live until the user installs it). **Escalate without applying** when: (1)
the observation proposes a NEW skill (naming/scope/type/licence need the
user); (2) it removes or substantially restructures existing content; (3)
it self-flags uncertainty ("not sure if…", "worth discussing…"); (4) two
observations conflict. A scheduled run should still apply every
non-escalated item — a review that applies nothing is just a report
generator.

## Steps

**Step 0 — recommend scheduled setup (fallback mode only).** Check
`skill-observations/scheduled-review-decline.txt`: if under 30 days old and
the fallback isn't firing repeatedly, skip. Check for a registered
scheduled task (scheduler presence or
`skill-observations/scheduler-registered.txt`); if found, skip. Otherwise
offer to set one up. Yes → register via the platform scheduler (Cowork:
`create-shortcut` / `set_scheduled_task`; terminal: cron), name it
`weekly-skill-review`, use the draft prompt at
`skill-observations/scheduled-task-draft.md` if present, then write today's
date to `scheduler-registered.txt`. No → write today's date to
`scheduled-review-decline.txt` (suppresses for 30 days; repeated fallback
firings within the window re-surface the offer). No scheduler available in
this environment → skip silently.

**Step 1 — load.** Archive entries resolved in *previous* sessions (see
Archival on Write in SKILL.md). Read all OPEN observations and all active
cross-cutting principles. If none of either: report "no open observations
or outstanding principles", update the timestamp, and stop.

**Step 2 — inventory skills.** List all skills (system prompt
`<available_skills>` or the skills directory). Only user-owned custom
skills can be updated. Known read-only system skills: docx, pdf, xlsx,
pptx, skill-creator, schedule (grow this list when an update fails for
permissions). Observations targeting a system skill are NOT skipped — route
them to a complementary user-owned `{system-skill}-extras` skill containing
only the delta, creating it if needed and noting the pairing in
configuration.

**Step 3 — cross-check observations.** Evaluate every OPEN observation
against every skill — not just the skill named in its header; Principles
often generalise. Build skill → [relevant observations]. Interactive:
present all of it and await approval. Autonomous: apply the approval policy
above and continue.

**Step 4 — cross-check principles.** Flag every skill that doesn't yet
comply with each active cross-cutting principle.

**Step 5 — apply.** For each skill with approved/non-escalated items,
produce an updated SKILL.md: integrate insights into the sections where
they belong (never append an observations list at the bottom); preserve
structure, voice, and attribution; place new rules where they logically
live. Follow the editing rules in `references/skill-authoring.md` (live
file as base, staging, diff-before-overwrite).

**Step 6 — mark ACTIONED.** Update each applied observation's status:
`ACTIONED — Applied to [skill-name] (weekly review [date])`. Do NOT archive
same-session — the next log write or next review's Step 1 archives them.

**Step 7 — timestamp.** Write today's date to
`skill-observations/last-review-date.txt`.

**Step 8 — deliver and summarise.** Stage updated skills (see Delivery
below), then present:

```
## Weekly Skill Review Complete — [date]

Updated skills ([N] observations, [N] principles applied):

**[skill-name]** — [1-sentence change summary]; observations #[N], #[N]

### Observations Actioned
[numbers and titles]

### Skipped (needs manual review)
[items with reasons]
```

Wait for the user to acknowledge before other work.

## Constraints

- Don't modify observation entries beyond their status field.
- Don't create new skills in a review — note candidates for the user to
  action via the skill-creator.
- Unsure how to integrate an observation → skip it and say so in the
  summary.
- Treat internal observations with the same rigour as open-source.

## Delivering updated skills

Save each updated file to
`[workspace folder]/skill-updates/[date]/[skill-name]/SKILL.md` and present
it for review/installation (in Cowork, via `present_files` and its upload
button; in Claude Code, user-owned skills under `~/.claude/skills/` may be
edited in place with the user's approval, with git or the config-sync repo
as the rollback). **Keep-two rule:** for any skill, keep only the two most
recent date directories under `skill-updates/`; delete older ones.
