# Comprehensive Review (scheduled or fallback)

Cross-checks all OPEN observations against all skills, propagates
cross-cutting principles, and applies improvements that don't need user
input. Two modes:

- **Scheduled autonomous review (preferred):** a recurring task (e.g.
  Mon/Wed/Fri mornings) via the platform's scheduler. Runs without the user
  present and applies non-escalated observations autonomously.
- **In-session 7-day fallback:** pending at session start when BOTH are
  true: no scheduled review is registered (or none succeeded in 7+ days),
  AND `skill-observations/last-review-date.txt` contains `never` or a date
  more than 7 days old (a missing file is recreated with `never` — see
  Session Start steps 1 and 3; the file's value is authoritative, a date
  means a review actually ran). In an interactive session a pending
  fallback surfaces as a one-line offer and runs only if the user opts in
  (SKILL.md, Session Start step 3) — it never gates the user's task.

**Reachability — where does scheduled work actually run?** Scheduled mode
requires the scheduling agent's execution environment to read and write
the workspace folder. Persistence and execution context are independent
axes: knowing where the state lives is not enough — check whether the
scheduler runs somewhere that can reach it. Three regimes:

1. **Shared filesystem** (e.g. Cowork's mounted folder): scheduled mode
   works as described.
2. **Local-only filesystem with a cloud scheduler** (e.g. remote routines
   that run on hosted infrastructure): scheduled mode is physically broken
   — the remote agent cannot read `skill-observations/` or stage updates
   to `skill-updates/`. Do not register a routine. Recommend a recurring
   calendar reminder plus a manual "run the skill review" trigger in a
   local session, or syncing the observation log to storage the scheduler
   can reach (e.g. a git repository it can clone).
3. **Local-only filesystem with a local scheduler** (cron, Task Scheduler,
   a terminal-resident loop): works, but the user must keep the local
   agent runnable.

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

**Step 0 — recommend scheduled setup (fallback mode only).** Ordering
guard: run Step 1's no-observations short-circuit FIRST — if there are no
OPEN observations and no outstanding principles, skip Step 0 entirely and
just update the timestamp. A brand-new install must never get a setup
prompt before it has done any work. Otherwise: check
`skill-observations/scheduled-review-decline.txt`: if under 30 days old and
the fallback isn't firing repeatedly, skip. Check for a registered
scheduled task (scheduler presence or
`skill-observations/scheduler-registered.txt`); if found, skip. Before
offering, check reachability (see the regimes above): if the platform's
scheduler runs where it cannot reach the workspace folder (regime 2), do
NOT offer registration — recommend the calendar-reminder-plus-manual-
trigger pattern instead, and skip the rest of this step. Otherwise
offer to set one up. Yes → register via the platform scheduler (Cowork:
`create-shortcut` / `set_scheduled_task`; terminal: cron), name it
`weekly-skill-review`, use the draft prompt at
`skill-observations/scheduled-task-draft.md` if present, then verify the
registration actually succeeded (the scheduler lists the task, or the
platform confirmed creation) BEFORE writing today's date to
`scheduler-registered.txt`. If registration fails or can't be verified, do
NOT write the marker — the marker would permanently suppress the fallback
while no review ever runs. Tell the user registration failed and leave the
fallback active. No → write today's date to
`scheduled-review-decline.txt` (suppresses for 30 days; repeated fallback
firings within the window re-surface the offer). No scheduler available in
this environment → skip silently.

**Step 1 — load.** Archive observation files resolved in *previous*
sessions (see Archival on Write in SKILL.md). Read only the frontmatter of
each file in `observations/` — not the bodies — to build the work queue;
load a body only when you actually action that observation in Step 5. This
frontmatter-first pass is what keeps the review cheap as the backlog grows.

Build the work queue from the files themselves, not from a status filter.
The OPEN set is defined as: **`status` is literally `open`, OR the file has
no `status` field at all.** Concretely:

1. Enumerate every file in `observations/` — the directory listing is the
   authoritative list of entries.
2. For each file, read the `status` field from its frontmatter. Treat a
   missing, blank, or any non-`actioned` / non-`declined` status as OPEN.
3. Never derive the work queue from a `grep 'status: open'` alone. Derive
   it from the file list minus the resolved (`actioned` / `declined`)
   files. A grep on an optional field silently drops every file missing
   that field — the review then confidently reports a clean backlog while
   untriaged observations are skipped.

**Reconciliation guard:** before proceeding, assert that
`count(files in observations/) == count(status-classified files)`. If the
counts differ, the delta is statusless files — surface and triage them (as
OPEN) rather than proceeding as if the backlog were clean.

Also read all active cross-cutting principles. If there are no OPEN
observations and no outstanding principles: report "no open observations
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

**Step 6 — mark ACTIONED.** In each applied observation's frontmatter set
`status: actioned`, `resolved: YYYY-MM-DD` (today), and
`resolution: Applied to [skill-name] (weekly review)` — editing only those
fields, in that one file. The `resolved:` date is load-bearing: archival is
gated on it (files archive only when it's before today), so a dateless mark
breaks the cross-session grace period. Do NOT archive same-session — the
next write on a later day archives them.

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

- Don't modify observation files beyond their `status`, `resolved`, and
  `resolution` frontmatter fields.
- Don't create new skills in a review — note candidates for the user to
  action via the skill-creator.
- Unsure how to integrate an observation → skip it and say so in the
  summary.
- Treat internal observations with the same rigour as open-source.

## Delivering updated skills

Save each updated skill to
`[workspace folder]/skill-updates/[date]/[skill-name]/` — the FULL skill
directory (SKILL.md plus references/, scripts/, assets/ where present),
never SKILL.md alone — and present it for review and installation. In
Cowork: via `present_files` and its upload button. In environments without
a presentation tool (e.g. Claude Code CLI): report the staged path and a
change summary in chat and let the user review and install from there.
Never write to the live skill directly, even where the skills directory is
writable — staging-only is a deliberate safety property of the review loop
(nothing goes live without the user's sign-off), not a filesystem
constraint. For any skill with
supporting files, zip the staged directory into a `.skill` bundle and
present the bundle; a bare SKILL.md install silently truncates a
multi-file skill. Pre-delivery gate (two items, run as the last step
before presenting): (1) grep the staged SKILL.md body for `references/`,
`scripts/`, `assets/` paths and fail the delivery if any referenced file
is missing from the staged set; (2) for multi-file skills, fail the
delivery if the artefact being presented is bare file links rather than
the `.skill` bundle. Sweep build artefacts (`__pycache__/`, `*.pyc`,
`.DS_Store`, `.~lock.*`) before zipping and read the archive listing back
after. When seeding staged
copies from the read-only mount, `chmod -R u+w` the staged path first —
the mount's read-only mode travels with the copy, for directories as
well as files. Do not edit skill files in place — nothing goes live
until the user installs it. **Keep-two rule:** for any skill, keep only
the two most recent date directories under `skill-updates/`; delete
older ones.
