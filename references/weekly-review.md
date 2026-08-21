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

**Offline-workspace policy for scheduled runs.** A scheduled or autonomous
session may fire while the workspace's persistence layer is unreachable —
the log can live on a machine that is asleep or offline at fire time.
Define the policy up front: (1) check workspace reachability before
anything else; (2) if unreachable, end gracefully with a one-line "review
skipped — workspace offline" note, no retries — the next firing or the
7-day in-session fallback catches up; (3) when setting up a scheduled
review, bake this policy into the scheduled task's prompt, so fresh
sessions inherit it without rediscovery. A permission failure mid-run is
handled the same way: skip the gated step, record it as a manual
follow-up, and still emit the final report — a blocked step N must never
cost the report for steps 1 through N-1.

## Approval policy

**Interactive (user present):** always present observations grouped by
skill (number, title, one-sentence summary), flag judgment calls as "needs
your input", and wait for blanket or selective approval before applying.
A declined or dismissed approval prompt is NOT approval — and it is not a
request to skip the asking and proceed either. Treat it as a stop signal
for the gated actions: halt, then ask in plain chat text what the user
wants. Only an explicit go (blanket or per-item) authorizes applying;
"apply the observations" as the review's trigger phrase still gates each
application on this policy, it does not pre-approve the changes.

**Scheduled autonomous (user absent):** apply non-escalated observations by
default — safety comes from the staging-plus-review pattern (nothing is
live until the user installs it). **Escalate without applying** when: (1)
the observation proposes a NEW skill (naming/scope/type/licence need the
user); (2) it removes or substantially restructures existing content; (3)
it self-flags uncertainty ("not sure if…", "worth discussing…"); (4) two
observations conflict. A scheduled run should still apply every
non-escalated item — a review that applies nothing is just a report
generator.

Escalate one DECISION per cluster, never the same decision twice — cluster
the OPEN entries before the escalation list is written (Step 3), and list
the member observation numbers under each decision.

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
offer to set one up. Yes → register it through whatever scheduler the
environment provides (see the environment table in
`references/environments.md`), name it
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
each file in `observation-log/` — not the bodies — to build the work queue;
load a body only when you actually action that observation in Step 5. This
frontmatter-first pass is what keeps the review cheap as the backlog grows.

Build the work queue from the files themselves, not from a status filter.
The OPEN set is defined as: **`status` is literally `open`, OR the file has
no `status` field at all.** Concretely:

1. Enumerate every file in `observation-log/` — the directory listing is the
   authoritative list of entries.
2. For each file, read the `status` field from its frontmatter. Treat a
   missing, blank, or any non-`actioned` / non-`declined` status as OPEN.
3. Never derive the work queue from a `grep 'status: open'` alone. Derive
   it from the file list minus the resolved (`actioned` / `declined`)
   files. A grep on an optional field silently drops every file missing
   that field — the review then confidently reports a clean backlog while
   untriaged observations are skipped.

**Reconciliation guard:** before proceeding, assert that
`count(files in observation-log/) == count(status-classified files)`. If the
counts differ, the delta is statusless files — surface and triage them (as
OPEN) rather than proceeding as if the backlog were clean.

Also read all active cross-cutting principles. If there are no OPEN
observations and no outstanding principles: report "no open observations
or outstanding principles", update the timestamp, and stop.

**Step 2 — inventory skills and classify each write target by whether
an edit SURVIVES, not by whether it succeeds.** List all skills (system
prompt `<available_skills>` or the skills directory) and put each into one
of three categories:

| Category | Detection | Action |
|---|---|---|
| (a) User-owned, no upstream | in the user's skills directory; not a git checkout; not refreshed from anywhere | normal staging flow |
| (b) Writable but volatile | path contains a plugin cache or version-pinned directory; or the skill is refreshed from an upstream by clone/copy or `git pull` | never edit in place — the next update silently discards it, and no permission error ever fires |
| (c) No on-disk file, or read-only | built-in / harness-provided skills (e.g. docx, pdf, xlsx, pptx, skill-creator); a mount that rejects writes | cannot be edited |

Observations targeting (b) or (c) are NOT skipped — the destination must
be one that survives and that something actually loads. Offer both routes
and let the user choose: a complementary user-owned `{skill}-extras` skill
holding only the delta **plus** a routing entry in the user's instruction
file (state plainly that without the routing entry nothing ever loads the
companion — a fix routed somewhere nothing loads is not a fix); or routing
the content straight into the instruction file, which loads
unconditionally. For (b) with an upstream, also offer an upstream issue or
PR per the attribution block. Grow the (c) list when an update fails for
permissions; grow the (b) list when a change you made has vanished.

**Step 3 — cross-check observations.** Evaluate every OPEN observation
against every skill — not just the skills named in its `skill:` list;
Principles often generalise. Build skill → [relevant observations], seeding
it from the frontmatter: every entry in an observation's `skill:` list puts
it in that skill's bucket (the first entry is primary), and every entry in
`proposes_skill:` puts it under a new-skill candidate of that name. An
observation may appear in both. Interactive:
present all of it and await approval. Autonomous: apply the approval policy
above and continue.

**Cluster by decision BEFORE the escalation list is written.** An
append-only log accumulates convergent entries by construction: the same
underlying problem is rediscovered from different task contexts and filed
against different skills, so grouping by filing category preserves that
duplication into the escalation list and the user is asked the same
question more than once. Group the OPEN entries by the DECISION they
require, not by the skill they are filed against; escalate one decision per
cluster with the member observation numbers listed under it; cross-reference
rather than separately escalate any entry whose decision duplicates
another's. Cheap first pass: scan the Principle lines — convergent
observations usually have near-identical principles even when their Issues
describe unrelated tasks. Corollary for in-session behaviour: if you notice
the overlap strongly enough to offer "this is the same as X" as an answer
option, that is the answer — take it and tell the user, rather than
spending a round-trip asking. **Across an ownership fence:** when the
backlog is split across parallel sessions and you defer an entry to a
cluster owned by the other session, the deferral is not complete until the
pointer exists on BOTH sides — relay it to that session directly, or
surface it to the user as a handoff item. A one-way note leaves the entry
pointing at a decision that may be settled without it.

**Step 4 — cross-check principles.** Flag every skill that doesn't yet
comply with each active cross-cutting principle.

**Step 5 — apply.** Begin with the copy, not the edit: for each skill
with approved/non-escalated items,

```bash
mkdir -p "[workspace folder]/skill-updates/[today]/[skill-name]"
cp "<live>/SKILL.md" "[workspace folder]/skill-updates/[today]/[skill-name]/SKILL.md"
diff -q "<live>/SKILL.md" "[workspace folder]/skill-updates/[today]/[skill-name]/SKILL.md"
# then make EVERY edit against the staged path
```

so the live path is never the target of an edit, the staged copy provably
starts from live, and a stale staged copy from an earlier date cannot be
picked up by accident. Then
produce an updated SKILL.md: integrate insights into the sections where
they belong (never append an observations list at the bottom); preserve
structure, voice, and attribution; place new rules where they logically
live. Follow the editing rules in `references/skill-authoring.md` (live
file as base, staging, diff-before-overwrite).

**Scaling note — fan out when the apply-phase is large.** When the
apply-phase spans more than ~3 skills or ~10 observations, delegate Step 5
to parallel subagents clustered by skill rather than applying everything
in the main session. Brief each subagent with: the observation ids (files) to
read, the live-mount path, the staging path, the
mkdir/per-file-cp/`chmod -R u+w` seeding sequence, the integration logic
for observation interdependencies (which observation supersedes, refines,
or folds into which — the parent must state this per cluster explicitly,
or subagents applying observations sequentially produce patch-on-patch
instead of coherent final state), the confidentiality rules for
open-source skills, and an explicit rule that subagents do not change any observation's
status. Reserve status marking and archival for the parent session. The principle: the apply-phase is embarrassingly parallel across
skills but the bookkeeping must have one owner — split the work along
that seam.

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
never SKILL.md alone — and present it for review and installation using
whatever file-presentation capability the environment offers (see the
environment table in `references/environments.md`); where there is none,
report the staged path and a change summary in chat and let the user
review and install from there.
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
the `.skill` bundle; (3) measure each staged skill's frontmatter
description (the folded value, not the raw YAML block) and fail the
delivery above 1024 characters, with a soft warning above ~900 —
measure every skill in the set, not just the one that failed; (4) `name`
is kebab-case, matches the directory, and the frontmatter parses; (5) the
bundle's member paths use `/`, checked on raw bytes (Windows packers write
`\`, and normalising readers hide it). `scripts/validate-skill-bundle.py`
asserts all five and packs a well-formed bundle — run it where Python is
available. Sweep build artefacts (`__pycache__/`, `*.pyc`, `.DS_Store`,
`.~lock.*`) before zipping and read the archive listing back after, for
leaked artefacts and for path separators. When seeding staged
copies from the read-only mount, `chmod -R u+w` the staged path first —
the mount's read-only mode travels with the copy, for directories as
well as files. Do not edit skill files in place — nothing goes live
until the user installs it. **Keep-two rule:** for any skill, keep only
the two most recent date directories under `skill-updates/`; delete
older ones.
