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
**Classify before you ask.** Any *disposition* option offered to the user
(fold in, decline, revive, route to skill X) must be derived from the
entries' bodies, never from their titles and `skill:` fields — a
title-level summary is exactly what can be produced without reading, and
it licenses the wrong split. Read and bucket first, then present the
routing decision with the real counts attached ("15 → skill A, 25 → skill
B, 2 dead"). The trigger to watch for is a target skill that no longer
exists: "revive / fold in / decline" looks like a disposition question and
is really a classification task, because a corpus filed against one dead
skill routinely splits across several live ones. Where a bulk question
genuinely must come first (very large backlog, a session budget that will
not cover reading everything), say so in the question, mark the proposed
split as provisional, and re-present it if the contents disagree. The
order is `read → bucket → present counts → ask`, never `ask → read`.
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
   missing, blank, or any status other than `actioned`, `declined`,
   `superseded` or `parked` as OPEN.
3. Never derive the work queue from a `grep 'status: open'` alone. Derive
   it from the file list minus the resolved (`actioned` / `declined` /
   `superseded`) and the `parked` files. A grep on an optional field
   silently drops every file missing
   that field — the review then confidently reports a clean backlog while
   untriaged observations are skipped.

**Reconciliation guard:** before proceeding, assert that
`count(files in observation-log/) == count(status-classified files)`. If the
counts differ, the delta is statusless files — surface and triage them (as
OPEN) rather than proceeding as if the backlog were clean.

**Parked entries: excluded from the queue, not from view.** `status: parked`
means the observation was judged sound but is blocked on an external
precondition recorded in `parked_until:` (SKILL.md, How to Log). It is a
decision, so it must NOT be re-escalated — but it is not resolved, so it also
never archives and stays in `observation-log/`. Two things happen to it in
every review, while the frontmatter is already in hand: (a) re-check each
`parked_until:` condition against the current state of the world, and where it
has been met, set the entry back to `status: open`, clear `parked_until:`, and
carry it into this review's queue; (b) list every still-parked entry in the
Step 8 summary in ONE LINE each — id, title, unpark condition — so a parked
backlog stays visible without re-entering the work queue.

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
observation may appear in both. Then, before anything is presented:

- **Consolidate new-skill candidates by the problem they solve, not by
  name.** Independently logged proposals for the same skill will not look
  alike, because each is named after the task that surfaced it; eleven
  working names have collapsed to four skills on reading. Present merged
  clusters with their constituent observation ids.
- **Supersession check.** Where a later observation's finding is that an
  earlier one's mitigation does not work, mark the earlier one
  `status: superseded`, `resolution: "by #N"`, and carry only the later
  one forward.
- **Family propagation.** An observation whose `skill:` list carries more
  than one entry is not actioned until every listed skill has been updated
  or explicitly dispositioned — partial application is the default failure
  and it is silent, because the observation gets marked `actioned` on the
  strength of the first skill it touched. Record the per-skill disposition
  in `resolution:` and carry it into the Family coherence block of the
  summary. Also check `siblings_checked:` while the frontmatter is in
  hand: an entry with the field missing or blank was logged without the
  check, so before actioning it, do the check now (registry, tests and
  fallback in `observation-log.md`) and widen `skill:` if it was
  under-scoped. Count these — "N observations logged without a sibling
  check" is a health metric of the logging practice, not a per-entry
  nuisance.
- **Confidentiality pass over the log itself.** For every OPEN
  `open-source` observation, check the Issue and Improvement fields for
  client-identifying specifics no longer needed for context and strip
  them. The log is the artefact most likely to be shared casually, and
  the authoring-time sweeps never see it.

Interactive: present all of it and await approval. Autonomous: apply the
approval policy above and continue.

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

**Step 4 — cross-check principles, and audit the families for drift.**
Flag every skill that doesn't yet comply with each active cross-cutting
principle.

Then run the **family drift audit**: for each family in
`skill-observations/skill-families.md`, grep every member for each rule
listed as shared and surface the gaps. It is mechanical and takes minutes,
and it is the only part of the family mechanism that catches drift
predating the rule or introduced by a skill authored outside the log — a
registry can go stale, a grep cannot. Two disciplines make the output
usable: judge each gap against the family's `Member-specific` column
before calling it drift (absence is sometimes correct), and resolve it
according to the family's coherence model — `synced-duplicates` means
editing every member, `shared-core` means editing the core and checking
the pointers. Where the audit finds a rule missing from members that need
it, log it as an observation naming all of them rather than fixing it
silently, so the correction is visible to the next review. If no registry
exists yet, build one from this pass: the audit's grouping IS the first
draft of the registry. Cadence is monthly rather than every review unless
the library has grown or a new family member was authored since the last
audit — a new member always warrants one (see `skill-authoring.md`, New
skills).

**Step 5 — apply.** Begin with the copy, not the edit: for each skill
with approved/non-escalated items,

```bash
# Stage the FULL skill directory (SKILL.md + references/, scripts/, assets/),
# not SKILL.md alone. From a read-only mount, mkdir + per-file cp + chmod is
# the only verified sequence for trees (cp -R and cp --no-preserve=mode both
# fail creating files inside copied subdirectories — see skill-authoring.md
# editing rule 6):
live="<absolute path to the live skill directory, no trailing slash>"
s="[workspace folder]/skill-updates/[today]/[skill-name]"
find "$live" -type d | while IFS= read -r d; do mkdir -p "$s/${d#$live}"; done
find "$live" -type f | while IFS= read -r f; do cp    "$f" "$s/${f#$live}"; done
chmod -R u+w "$s"
diff -rq "$live" "$s"      # must be identical before any edit
# then make EVERY edit against the staged path
```

Two details in that snippet are load-bearing and were both wrong in an
earlier version. Strip the prefix **without** a trailing slash — `${d#$live}`,
not `${d#$live/}`. The pattern with the slash strips correctly for every
subdirectory and fails on the one path that has no trailing slash to match:
the top-level directory itself. `mkdir -p` then rebuilds the entire absolute
live path *inside* the staged directory, once per skill. And keep `IFS=` on
both `read` loops — workspace paths routinely contain spaces, and without it
the loop mangles them.

**If the `diff` reports anything, do not edit and do not delete.** On a mount
that denies `unlink`, `rm -rf` and `rmdir` both fail on the unwanted paths, so
the obvious cleanup is unavailable and the step stalls. Rename them into a
holding folder instead — the mount permits rename — then re-run the diff:

```bash
mkdir -p "[workspace folder]/_to_delete/<date>-staging-artefacts"
mv "<unwanted path>" "[workspace folder]/_to_delete/<date>-staging-artefacts/<name>"
```

Requesting the delete permission for the workspace folder also works where
that tool exists, and is worth doing anyway before the prune in Delivery.

The sequence exists so the live path is never the target of an edit, the
staged copy provably starts from live, and a stale staged copy from an earlier
date cannot be picked up by accident. **Presence check before writing anything:** grep
the staged copy for the substance of each suggested improvement and
classify it as already-applied / partially-applied / outstanding — an
`open` status is not evidence the work is outstanding, and applying an
already-applied observation over a section that has since been refined
regresses the skill in the name of improving it. Mark already-applied
entries `actioned` with a resolution noting that a prior session applied
them, and leave the section alone. Then
produce an updated SKILL.md: integrate insights into the sections where
they belong (never append an observations list at the bottom); preserve
structure, voice, and attribution; place new rules where they logically
live. Follow the editing rules in `references/skill-authoring.md` (live
file as base, staging, diff-before-overwrite).

**Scaling note — fan out when the apply-phase is large.** When the
apply-phase spans more than ~3 skills or ~10 observations, delegate Step 5
to parallel subagents clustered by skill rather than applying everything
in the main session. Brief each subagent with: the observation ids (files) to
read, the live-mount path, the staging path, the seeding sequence **as the
verbatim snippet from the Step 5 block above** (never described in prose —
its two failure modes are both reconstruction errors), the integration logic
for observation interdependencies (which observation supersedes, refines,
or folds into which — the parent must state this per cluster explicitly,
or subagents applying observations sequentially produce patch-on-patch
instead of coherent final state), the confidentiality rules for
open-source skills, and an explicit rule that subagents do not change any observation's
status. Reserve status marking and archival for the parent session. The principle: the apply-phase is embarrassingly parallel across
skills but the bookkeeping must have one owner — split the work along
that seam.

**The orchestrator owns a merge-time validation pass.** Splitting work
across parallel workers splits the verification surface with it, and the
split is not clean: local checks partition neatly, global invariants do
not partition at all. Any property defined over the whole deliverable
becomes unverifiable the moment the work is divided, and stays
unverifiable no matter how rigorous each worker is — every subagent can
return a provably clean batch and the merged artefact still be wrong.
Assume that everything the workers could not see is exactly where the
defects are. So after the returns are in, and before anything is marked
actioned or delivered, re-verify globally over the combined result. Three
checks, at minimum:

1. **Cross-slice duplicates and collisions** — two subagents handed the
   same source signal will independently produce near-identical output,
   and neither self-check can fire because neither can see the other.
   Here that includes the same rule landing in two skills' sections with
   divergent wording, and two staged copies of one skill in the same
   day's folder.
2. **Vocabulary and convention consistency across slices** — where the
   brief was under-specified, each worker resolved it locally,
   defensibly, and differently. The inconsistency is invisible inside any
   one slice and obvious across the set.
3. **Conformance of the combined totals to the plan** — every observation
   routed, every skill in the plan staged, counts matching, no
   multi-skill observation applied to only some of its listed skills
   (Step 3, Family propagation).

4. **Characterisations, not just values** — the verification pass reads
   naturally as a rule about values (counts, fields, totals), and holds
   least where outputs are stated as judgements: a reported conflict,
   defect, risk or readiness verdict carries no unit to check against,
   and a wrong characterisation is consumed by being *agreed with*,
   leaving no trace — where a wrong value tends to fail loudly when
   something computes with it. Any subagent claim that will reach the
   user as a finding must be spot-checked against the source by the
   parent before it leaves the session, at whatever granularity makes
   the claim falsifiable — one grep is usually enough. The structural
   trigger: the moment you are about to write a sentence attributing a
   problem to something you did not read yourself. Require subagents to
   return the evidence alongside the claim (the file, the line, the
   matched string) so the check is cheap; a claim returned without
   locatable evidence is a claim to verify, not to relay.

Corollary for the brief: require every delegated agent to close with a
"decisions the brief did not cover" section. That section is how brief
defects are discovered — an agent that silently resolves an ambiguity
converts a fixable specification bug into an invisible inconsistency. And
when two independent agents flag the same ambiguity, the brief is the
defect, not the agents: fix the brief and re-issue rather than
adjudicating the two outputs.

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

### Family coherence
[each multi-skill observation: applied to all listed skills, or partially
applied with the outstanding skill named — never left implicit]
[drift audit: gaps found per family, and how each was resolved]
[N observations logged without a sibling check]

### Parked
[one line each: #id — title — unparks when: [condition]; plus any entry
whose condition has been met and was returned to the queue this review]

### Skipped (needs manual review)
[items with reasons]
```

Wait for the user to acknowledge before other work.

## Constraints

- Don't modify observation files beyond their `status`, `parked_until`,
  `resolved`, and `resolution` frontmatter fields.
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

**The dated staging folder is multi-writer.** `skill-updates/<date>/` is
a namespace keyed only by date, so a manual session and a scheduled run
can both write into the same day's folder (observed minutes apart). Any
producer should assume it is not the only writer that day: before staging
a skill, check whether that day's folder already holds a staged copy of
the same skill — if it does, diff and integrate rather than overwrite,
and say so in the manifest. Any consumer choosing the "newest staged
version" (e.g. the publishing pipeline's freshness gate) must resolve it
by content, not by assuming a single authoritative producer — if two
same-day copies of one skill diverge, surface the conflict rather than
letting mtime decide. The manifest entry (below) is the provenance
marker: who staged it, from which run, applying what.

**Staging manifest.** Every delivery appends one entry to
`[workspace folder]/skill-updates/PENDING.md`: the skill, the date
directory, the producer (which session or scheduled run staged it), the
observation ids applied, and a per-change summary
(observation id → section touched → one-line rationale). The manifest is
what the Session Start Protocol reads to announce "N staged updates
awaiting review", so staged work is never quietly forgotten; the
per-change summary is what lets the user review a full-file diff
quickly, which is what raises the install rate. Remove an entry when the
user installs the update or when the keep-two rule prunes its directory.
The gate stays absolute — the fix for a safety gate people are tempted to
bypass is reducing the friction that creates the temptation, not
loosening the gate. An optional git-based staging medium is described in
`references/environments.md`.
