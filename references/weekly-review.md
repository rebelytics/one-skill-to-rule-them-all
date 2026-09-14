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

**Several observation logs on one machine — unify the review at the
integration point.** First check whether the logs should coexist at all:
`references/environments.md` requires one log per observed scope, and
two logs over the same globally installed skills are the silent fork it
warns about — consolidate those instead of reviewing them jointly. What
remains is the legitimate case: logs deliberately kept apart because
observation bodies carry non-portable task context, while the skills
they observe are installed globally and therefore shared. There, running
the per-workspace review once per log stages each shared skill several
times, each staged copy integrating only its own log's slice — by
construction the same-day multi-writer divergence the Delivery section
exists to detect — and convergent observations filed in different
projects are escalated as separate decisions, because no single run ever
sees them together (the ownership-fence rule in Step 3 covers a backlog
split across sessions, not across logs).

An aggregate review is therefore an explicitly invoked run over a named
set of workspace roots — not something a per-workspace scheduled task
discovers or starts. Those keep their per-log behaviour, which is what
stops two runs from draining the same queues at once. **The named set is
given as ABSOLUTE paths**, once, at the top of the run: roots enumerated
from a project identity commonly begin with `-` (Claude Code encodes the
directory path that way), and a leading `-` in a relative argument is
read as an option by `ls`, `grep` and `find` — the scan then returns
zero files with no error, which is indistinguishable from a clean log.
Given the roots:

- **Scope by what the logs observe, not by what they declare.** Logs
  whose workspaces observe the same installed skills are in scope. Do
  not gate on their `skill:` lists overlapping: Step 3 says convergent
  entries are routinely filed against *different* skills, so a
  declared-target gate skips exactly the clusters this exists for.
  Cluster across all logs first (Step 3's Principle-line pass), then
  decide.
- **Qualify every id that leaves its log.** Ids are allocated per log,
  so `#5` exists in each of them. Any cross-log reference — approval
  list, `resolution: "by #N"`, Step 8 summary, manifest entry — carries
  the workspace key alongside the number.
- **Stage each affected skill ONCE, and publish the anchor workspace
  everywhere.** One participant is the **anchor workspace**: its
  `skill-updates/` holds the staged copy, and it supplies
  `[workspace folder]` for the Step 5 seed — which then picks its
  **anchor directory** (`[today]/[skill-name]`, or a discriminated one
  under the same-day rule) exactly as in a single-log run. The two
  senses are separate axes and are always named in full: *anchor
  workspace* = which log's `skill-updates/` tree, *anchor directory* =
  which dated directory inside it. Append the manifest entry in the
  anchor workspace AND a pointer entry in every participating
  workspace's `PENDING.md`, **creating that manifest where it does not
  exist yet** — a participant that has never staged anything has no
  `PENDING.md`, and an appender that assumes the file is there writes
  nothing. A manifest is read only from its own workspace and its entry
  is removed on install, so an anchor named in one workspace alone is
  invisible from the others and gone after the first install.
- **Bookkeeping stays local.** Each log's work queue, status edits,
  archival, `last-review-date.txt` and `activation-tiers.txt` are read
  from and written back to its OWN workspace — the activation record in
  particular is a statement about that workspace's config, so an
  aggregate run writes one per participant and never a single copy at
  the anchor workspace. Integration and staging unify; bookkeeping does
  not.

The principle: when several append-only queues feed edits into shared
targets, the review that drains them must be unified at the integration
point even though the queues themselves stay separate — and unification
needs an identity per queue, or the merged references stop resolving.

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
Reading the bodies is necessary but not sufficient: a body can itself
assert a checkable premise ("the target is foreign-maintained, so an
upstream contribution is possible"), and an option built on it inherits
the claim unverified. Settle such a premise BEFORE presenting the
option, from what is already local — the checkout or copy the skill was
installed from, a stored baseline, the file's own attribution block.
Local provenance answers most of it, and it costs far less than a
decision made on a false premise plus the re-ask that follows. Where the
premise is genuinely remote (does the section still exist at upstream
HEAD, is the PR still open), the review must not depend on reaching the
network: present the option with that half named as unverified, and
leave the remote check to the feedback pre-flight in
`references/skill-authoring.md`, which runs once the user has chosen to
contribute. Forked files need the check at two levels: file-level
provenance ("this skill is foreign-maintained") and section-level
provenance ("the section this observation extends is a local addition")
are separate statements — both answerable from the local copy — and
routing to upstream-vs-fork depends on the second. (Observed: an
"upstream contribution" option was offered and chosen for three
observations extending a section that turned out to exist only in the
local fork — the decision had to be re-asked with the corrected facts.)
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
user); (2) the AGENT is proposing a removal or a substantial restructure
of existing content; (3) it self-flags uncertainty ("not sure if…",
"worth discussing…"); (4) two observations conflict. A scheduled run
should still apply every non-escalated item — a review that applies
nothing is just a report generator.

Criterion (2) is about whose judgement is driving the change, not about
the size of the diff. Where the observation records the removal or
restructure as DECIDED by the user AND carries a complete specification
— it names what replaces what, in enough detail to apply without
inventing anything — apply it, provided the target skill is not
published open-source, and always flag it as the FIRST diff in the
summary for the user to read. Where the spec is partial ("something
like…", "the old rules should probably go"), criterion (3) applies and
it stays escalated. An escalation rule guards against the agent's own
judgement, not against change as such: escalating a decision the user
already made returns their answer to them as a question, buys no safety,
and costs a cycle in which the skill stays knowingly wrong.

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
scheduled task (`skill-observations/scheduler-registered.txt`, or the
platform's scheduler queried directly: `crontab -l` on Unix; `launchctl
list` on macOS where launchd is used; `Get-ScheduledTask` in PowerShell
or `schtasks /Query` from any Windows shell; the app's Scheduled tasks
page in Cowork); if found, skip. "No scheduler available" means the
platform's own scheduler was queried and is absent — cron missing on
Windows is not that; Task Scheduler is the scheduler there, and a check
worded around cron alone marks every Windows install as schedulerless
and silently never offers the review. Before
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
this environment (per the definition above) → skip silently.

**Step 1 — load.** First, the activation regression check — the one
half of "is activation in place?" a review can reach: a review only runs
when the skill loaded, so it cannot detect an install that never
activated, but it can detect a tier that WAS in place and is no longer
(a rewritten CLAUDE.md, a hooks file replaced by a settings sync). Read
the activation config named in `references/environments.md` — the
instruction block in CLAUDE.md or its equivalent, and the session-start
hook where the harness has one — and if a tier that a previous review
recorded as present is missing, say so in the summary's first line and
re-suggest the block; record the tiers found in
`skill-observations/activation-tiers.txt` so the next review has a
baseline to compare against — in an aggregate run over several logs,
one such file per participating workspace, describing that workspace's
own config, never a single copy at the anchor workspace. Then archive observation files resolved in
*previous* sessions (see Archival on Write in SKILL.md). Read only the frontmatter of
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
OPEN) rather than proceeding as if the backlog were clean. **This is a
point-in-time assertion, not a standing guarantee.** It proves the scan was
complete when it ran; the log is multi-writer and a long review is exactly
when other sessions are logging, so the result decays for the duration of
the run. Keep the Step 1 file list — Step 6 re-scans against it before
anything is marked.

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

**Staged-work reconciliation gate.** Installation is a manual, per-item
act that happens outside any session, so no session observes it and
nothing fires at install time: a ledger whose removal trigger is an event
no session observes only ever grows. Bind the cleanup to the moment the
ledger is read — reading is the only reliably recurring event, so the
reading session owns it. For each entry in `skill-updates/PENDING.md`
(and, where the manifest may be missing entries, each skill directory
under recent `skill-updates/` dates), run `diff -rq` of the staged copy
against the live skill and classify THREE ways — three-way because live
legitimately moves on, so a bare "differs" is not a verdict:

- **(a) identical** → installed; remove the manifest entry.
- **(b) live strictly newer / a superset of the staged copy** →
  superseded; remove the entry with a note.
- **(c) the staged copy carries content absent from live** → NOT
  installed; surface it, and treat the staged copy — not live — as the
  base for any new staging of that skill in this review. Also list, in
  the summary, the observations whose `resolution:` names that staged
  path (`grep -l "skill-updates/<anchor>/<skill>" observation-log/*.md
  observation-log/archive/*.md`): they were marked `actioned` at staging
  and their work has not landed. They stay `actioned` — the status
  describes the review's act, and re-opening would re-queue work already
  done — but the summary carries them under "actioned, awaiting install",
  and a staged copy that reaches its SECOND review un-installed is
  escalated as a decision (install it, or discard it and re-open its
  observations) rather than carried forward a third time.

Reconcile in BOTH directions every time: lingering-done (installed but
still listed) and missing-done (staged but never installed) fail
differently, and only the diff sees both. Completion of a manual batch is
a claim, not a state; the check is one `diff -rq` per skill and runs in
seconds over a 20-skill batch. The Session Start Protocol (step 6) runs
the same gate whenever it announces staged updates.

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
PR per the attribution block. Choosing the companion route may mean
creating the `{skill}-extras` skill in this review, which the Constraints
allow as the one exception to "no new skills in a review". Grow the (c) list when an update fails for
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
  summary. Where a legitimate partial application exists (one session owns
  a subset of the listed skills), the carrier pattern in
  `observation-log.md` resolves it — and a carrier observation enters this
  queue as first-class, never deferred on account of its provenance. Also check `siblings_checked:` while the frontmatter is in
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

**Adding or materially editing a principle carries its starter-set
verdict in the same act.** Where a bundle ships a public,
provenance-stripped extract of the private principles file — this skill's
`references/starter-principles.md` — that extract is derived content, and
a one-off triage performed once at extraction time is a snapshot: the
extract starts drifting at the very next edit of the private file, and
nothing downstream would ever produce a verdict for the entries added
since. So the step that adds a principle, or changes an existing one
materially, classifies it in the same act: **`include verbatim`**,
**`include after scrub`** — naming exactly what to strip (provenance,
observation numbers, client or environment specifics) — or **`leave
out`** (personal strategy, or specific to one environment). Append the
verdict to the triage reference, keyed by principle number, so the
classification is per entry and dated by the edit that prompted it.
Then, for this skill, stage the starter-file change alongside the
principle change rather than as a follow-up: append the scrubbed entry,
bump the `Starter set version:` line at the top of the starter file
(every adopter's reconciliation offer is gated on that number, so an
unbumped version ships the new entry to nobody), and run the
confidentiality scan over the starter file in the pre-delivery gate.

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

Where an approved item's destination is an upstream report — an issue or
PR against a skill someone else maintains — drafting that report IS the
apply step for it, so the feedback pre-flight in
`references/skill-authoring.md` runs here, before the draft is written:
duplicate search across the upstream's issues and pull requests, the
maintainer's preferred channel, upstream-HEAD verification. A pre-flight
with no call site runs at send time, after the draft has been staged and
listed as an outstanding item, which is when finding the duplicate costs
the most. An empty duplicate search releases the draft only after a
positive control: search for a term you know an existing issue contains,
and if that returns nothing the search is broken, not clean.

**Published skills have more inputs than the log and more outputs than
one staged copy.** For any skill published to a public repository, run
these four passes before and while staging it; each produces something
the summary carries.

1. **Merge last cycle's release branch first.** If the previous review
   cut a `release/vX.Y.Z` branch and it has been installed locally for
   the week, this repo's first act is the merge decision — and it
   precedes the new staging, because everything staged this week is
   staged on top of the merged result. **A branch merges only when every
   change on it has either a week of natural exercise recorded or a
   synthetic check with a stated pass criterion run in this review.** The
   test week is the container; the checks are the evidence. A clean week
   is evidence about the changes the week's activity happened to touch
   and silence about the rest, so absence of complaints certifies
   nothing. The merge report lists each change with its evidence —
   exercised naturally (where), or check run (fixture and result) — and
   a change with neither does not merge; it stays on the branch for
   another cycle. The checks themselves come from the branch's test-plan
   observation, which is in this review's queue by procedure (below).
2. **Read the repo's open issues and pull requests.** They are review
   inputs alongside the observation log — the review is the only point
   at which including a contribution costs nothing extra, and a channel
   that is merely monitored is a backlog that collides with the next
   sync. List every open issue and PR and classify each: **include now**
   (doc-level fixes, bug fixes with a clear spec, changes consistent
   with the current rules), **test branch** (behavioural changes to
   snippets, procedures or activation, and anything that changes what an
   agent does at session start), or **decline, with the reason**. Apply
   the include-now set to the staged copy, and record in the staging
   manifest both the classification and, per include-now item, the
   reporter's **GitHub login and numeric user ID** — the publishing run
   needs both to write a trailer GitHub can resolve
   (`Co-authored-by: Name <ID+login@users.noreply.github.com>`, or
   `Reported-by:` for a bare report). Credit written as prose in a
   commit body is credit the platform cannot see, and the ids are cheap
   to collect here and awkward to collect at commit time.
3. **Re-derive every numeric and duration claim in the README and user
   guide.** Prose counts are derived content with no timestamp: they were
   true when written and drift with every week of use and every merged
   contribution, and nothing else in the pipeline re-checks them.
   Enumerate the claims, recompute each from its source — observations
   logged = the highest id ever issued; skills observed = the installed
   skill count; contributors, issues and PRs = the repo's ALL-TIME
   counts, not the open ones; months or years in use = from the date of
   the earliest observation in the log (the oldest file in
   `observation-log/archive/`), not from the install date or the repo's
   first commit — and update them in the same staging. Carry the new
   values into the review summary so the maintainer sees what changed.
   Anything of the same class the maintainer alone would notice (a
   "recommended by" list, a supported-platform list) is checked in the
   same pass.
4. **Classify every change, and stage twice.** Each change going into
   this week's version — community item or observation — is
   **safe-to-main** or **needs-test**, by the same test as pass 2. That
   produces two artefacts, not one: the **main staging** (safe changes
   only) and the **release-branch staging** (safe plus needs-test),
   named `release/vX.Y.Z` for the version the branch will become, and it
   is the release-branch staging that is installed locally for the test
   week. Both are staged copies under `skill-updates/` with their own
   manifest entries; neither is pushed by the review.

**Standing rule — a branch is cut together with its test plan.** The
session that cuts a release/test branch classifies every change on it as
*exercised naturally by a week of use* or *unlikely to happen
naturally*, and for the second class writes a test plan — fixture,
procedure and pass criterion per change — as an observation whose
`skill:` list names the branch's skill. Filed that way, the plan reaches
the next scheduled review by procedure rather than by anyone
remembering, and the merge step above has the evidence it requires. A
test period tests what the period's activity happens to touch; for
everything else it is only a delay.

Choose the anchor first: if `[today]/[skill-name]` already exists, apply the
same-day rule under Delivery — integrate another writer's pending copy, or give
a second round after an install a discriminated anchor — and put that path into
`s=` below; the guard line refuses to seed over an existing anchor.

```bash
# Stage the FULL skill directory (SKILL.md + references/, scripts/, assets/),
# not SKILL.md alone. From a read-only mount, mkdir + per-file cp + chmod is
# the only verified sequence for trees (cp -R and cp --no-preserve=mode both
# fail creating files inside copied subdirectories — see skill-authoring.md
# editing rule 6):
live="<absolute path to the live skill directory, no trailing slash>"
s="[workspace folder]/skill-updates/[today]/[skill-name]"
[ -e "$s" ] && { echo "anchor exists — apply the same-day rule (Delivery) before seeding"; exit 1; }
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

**If the `diff` reports anything, do not edit.** On a mount that denies
`unlink`, `rm -rf` and `rmdir` both fail on the unwanted paths, so the
cleanup needs the environment's delete grant: **request the delete grant
on the target directory (`allow_cowork_file_delete` or the equivalent),
then delete — never rename into a holding folder.** Then re-run the diff.
A holding folder converts one deletion into a second, deferred task the
user has to remember, and the queue grows silently with no consumer. In a
scheduled or autonomous run, request the grant the same way; if the
permission stream fails there, leave the files in place, name them in the
report as "pending deletion — grant needed", and still never rename them
into a holding folder.

The sequence exists so the live path is never the target of an edit, the
staged copy provably starts from live, and a stale staged copy from an earlier
date cannot be picked up by accident. **Presence check before writing anything:** grep
the staged copy for the substance of each suggested improvement and
classify it as already-applied / partially-applied / outstanding — an
`open` status is not evidence the work is outstanding, and applying an
already-applied observation over a section that has since been refined
regresses the skill in the name of improving it. The classification is
made per point of the body, naming the line that covers each: an entry
is already-applied only when every point has its line, and one point
without a line makes it partially-applied, whatever the title suggests;
a point that joins several conditions (A and B) counts as one point per
condition (SKILL.md, Acting on Observations). Mark already-applied
entries `actioned` with a resolution noting that a prior session applied
them, and leave the section alone. For a partially-applied entry, add
only the points without a line, never restate the ones that have one —
a second copy of a present rule drifts from the first — and name both
in the resolution: the points a prior session applied and the ones
added now. Then
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

**Step 6 — re-scan, then mark ACTIONED.** Before any status is written,
re-enumerate `observation-log/` and compare the listing against the file
list built at Step 1. The queue is a snapshot of a shared, append-only
store, and every downstream count and consistency check in this procedure
is computed against the queue rather than the directory — so a stale queue
produces a summary that is coherent, confident and incomplete, with no
internal contradiction to trip over. Files in the new listing that were
not in the Step 1 list arrived during the run: they are OPEN and were
never triaged. Classify each rather than merely counting them: (a) it
targets a skill whose staged copy from Step 5 is still open in this run →
fold it in and action it (this is the common case — a review that has just
touched a skill runs in the same window as the sessions most likely to be
using it, and it is the case where a miss costs most, because the next
review's base is then a staged copy whose provenance nobody re-derived);
(b) otherwise → leave it OPEN for the next review and list it under the
"arrived during this run" line of the Step 8 summary. Never let the delta
pass silently, and never infer it from an id counter — a monotonic id
surfacing a number above the scan's maximum is a side effect, not a
detection mechanism. The check is one `ls` against a list already in hand.

Then, in each applied observation's frontmatter set
`status: actioned`, `resolved: YYYY-MM-DD` (today), and
`resolution: "Staged for [skill-name] at skill-updates/<anchor>/[skill-name] (weekly review)"`
— editing only those fields, in that one file. The resolution names the
staged path deliberately: `actioned` at this point means "applied to a
staged copy", and handing an artefact over and having it taken up are two
different facts — the first must not close the status of the second. The
staged path is what lets the next review find every observation whose
work is sitting un-installed (below). The `resolved:` date is load-bearing: archival is
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

### Published skills
[per published skill: release branch merged / held, with each change on
it and its evidence (exercised naturally where, or check run and result);
community items included now, routed to the test branch, or declined
with the reason; README and user-guide counts re-derived, old → new]

### Parked
[one line each: #id — title — unparks when: [condition]; plus any entry
whose condition has been met and was returned to the queue this review]

### Arrived during this run
[from the Step 6 re-scan: #id — title — folded into [skill] / left OPEN
for the next review; or "none" — the line is never omitted]

### Skipped (needs manual review)
[items with reasons]
```

Wait for the user to acknowledge before other work.

## Constraints

- Don't modify observation files beyond their `status`, `parked_until`,
  `resolved`, and `resolution` frontmatter fields.
- Don't create new skills in a review — note candidates for the user to
  action via the skill-creator. The one exception is the `{skill}-extras`
  companion for a read-only or volatile target (Step 2): it is a routing
  container for approved deltas, not a candidate skill, and creating it
  when the user chooses that route is part of applying the observation.
  It is still staged, never installed, by the review; and it still needs
  the routing entry, or nothing loads it.
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
constraint. **Every** staged skill is packed into a `.skill` bundle and
presented as that bundle — one delivery format for all of them,
regardless of size or file count. A format that switches on the shape of
the artefact creates two conventions for one thing and a boundary every
consumer has to re-derive; one format costs nothing on a single-file
skill and removes the whole "a bare SKILL.md silently truncates a
multi-file skill" failure class at the other end.
Pre-delivery gate (run as the last step
before presenting): (1) grep the staged SKILL.md body for `references/`,
`scripts/`, `assets/` paths and fail the delivery if any referenced file
is missing from the staged set — a backticked path counts as this skill's
own only when it is UNQUALIFIED, so a file belonging to another skill is
cited as `<skill-name>/references/<file>` and passes untouched; that
qualification is the convention, and re-wording a genuine cross-reference
until the backtick no longer starts with the prefix is disguising a
reference to satisfy a linter, not fixing a defect; (2) the artefact presented is the
bundle — bare file links fail this gate; (3) measure each staged skill's frontmatter
description (the folded value, not the raw YAML block) and fail the
delivery above 1024 characters, with a soft warning above ~900 —
measure every skill in the set, not just the one that failed; (4) `name`
is kebab-case, matches the directory, and the frontmatter parses; (5) the
bundle's member paths use `/`, checked on raw bytes (Windows packers write
`\`, and normalising readers hide it); (6) exactly one frontmatter block
— a second `---` block or stray `name:`/`description:` lines directly
after the first is a duplicated header that every field check passes by
construction; (7) no edit residue in any text file of the bundle,
outside code: a literal regex backreference (`\1`) on its own line or in
prose, merge-conflict markers, unresolved `{{slot}}` placeholders — the
gate checks the form of a delivery, and this is the one content assertion,
because a failed replacement once passed apply, gate and install as a
literal `\1`. The unresolved-slot rule — and only that rule — is waived
for a file whose path contains `template` (case-insensitive) or whose
first line is the marker `<!-- template: slots intentional -->`: in a
reference file that IS a template for a delegate author, the slots are
the deliverable, not residue. Every other residue rule and every other
gate item still runs on such a file, so the exemption never becomes the
hand-zip that skips the checks nobody was questioning.
`scripts/validate-skill-bundle.py`
asserts all seven and packs a well-formed bundle — run it where Python is
available. Where the bundle ships a public extract of a private file
(this skill's `references/starter-principles.md`), run the
confidentiality scan over that extract here too: it is the one file in
the bundle whose content is copied from a private source, so the
authoring-time sweeps never see it. Sweep build artefacts (`__pycache__/`, `*.pyc`, `.DS_Store`,
`.~lock.*`) before zipping and read the archive listing back after, for
leaked artefacts and for path separators. When seeding staged
copies from the read-only mount, `chmod -R u+w` the staged path first —
the mount's read-only mode travels with the copy, for directories as
well as files. Do not edit skill files in place — nothing goes live
until the user installs it. **Keep-two rule:** for any skill, keep only
the two most recent staged copies under `skill-updates/`; for the older
ones, **request the delete grant on the target directory, then delete —
never rename into a holding folder** (if the permission stream fails in
an autonomous run, leave them in place and name them in the report as
"pending deletion — grant needed"). The rule is scoped to staged skill copies,
not to date directories: before pruning a directory, list what else is in
it — an assembly script, a verification script, working notes — and move
anything that is not a staged skill copy aside first, or leave the
directory and prune only the copies. A prune that fires correctly on the
oldest directory deletes everything in it, and a missing tool is noticed
the next time it is needed, never at the moment of deletion. Rounds, not
days, are what the rule counts (a same-day second round is its own
copy).

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
The same-day check has a third outcome: the day's folder already holds a copy
the user has INSTALLED — it diffs clean against live and has no manifest entry
left, because the install removed it (an entry still present means another
writer's pending copy: integrate, as above). Do not seed a second round into it: the seed would be
byte-identical to live, the `diff -rq` gate would pass trivially, and the
new round would inherit a manifest entry that claims it is installed. Give
the second round a discriminated anchor (`<date>-<slug>` or `<date>.2`)
with its own manifest entry, and count rounds rather than days when the
keep-two rule prunes. The anchor is chosen BEFORE the Step 5 seed — the
snippet's `s=` line takes the discriminated path — not discovered afterwards
from this paragraph. (Observed: a second apply round for one skill started
the same evening the first had been installed; the date-keyed anchor pointed
at the installed copy, and only a manual check of the manifest state
prevented seeding over it.)

**Staging manifest.** Every delivery appends one entry to
`[workspace folder]/skill-updates/PENDING.md`: the skill, the date
directory, the producer (which session or scheduled run staged it), the
observation ids applied, and a per-change summary
(observation id → section touched → one-line rationale). The install
artefact is always the `.skill` bundle, so the entry never distinguishes
a single-file from a multi-file skill. For a published skill it also
carries the community-item classification from Step 5 (include now /
test branch / declined, with the reason) and, per included item, the
reporter's GitHub login and numeric id, so the publishing run's commit
can write the crediting trailer without going back to the API. The manifest is
what the Session Start Protocol reads to announce "N staged updates
awaiting review", so staged work is never quietly forgotten; the
per-change summary is what lets the user review a full-file diff
quickly, which is what raises the install rate. Entries are removed by
the staged-work reconciliation gate (Step 1, mirrored in Session Start
step 6) when the staged copy proves identical to live or superseded by
it, or when the keep-two rule prunes the directory — never "at install
time", because no session observes the install; the session that reads
the manifest owns its cleanup.

The manifest carries three kinds of entry and no others: provenance,
install instructions, and — in an aggregate run over several logs — the
**cross-log pointer** naming the anchor workspace where a shared skill
was actually staged. The pointer is provenance for a staging that lives
elsewhere, so it belongs here; it is not follow-up work. Follow-up work
is what the manifest never carries. Anything a review recognises as
"check next time" — a sibling to
mirror, an audit to run once the staging is installed — is logged as its own
observation before the summary is written: created with `status: open`, as the
file-format rule requires of every new entry, and parked in the same turn —
`status: parked` plus a named `parked_until:` condition, the same two-field
edit a review makes on any parked entry. That puts it in the queue the next review
reads by procedure (Step 1 re-checks every parked condition; Step 8 lists
every parked entry), and it survives the reconciliation and the prune that remove
the manifest entry. In an aggregate run, that parked follow-up is written
to the log of the workspace whose work it concerns — the one whose next
review will need it — and to the anchor workspace's log only when the
follow-up is about the shared staging itself; bookkeeping stays local,
and an id is qualified with its workspace key wherever it is referenced
from another log. A note in an artefact whose lifetime ends at install
cannot carry a follow-up: nothing in the review reads manifest notes as a
queue, and the one place the review is guaranteed to delete is the one
place it is tempting to write the leftover backlog. (Observed: two sessions
on two days each wrote a follow-up into the manifest; the first was found
only because the manifest happened to be read before the next review, the
second was caught in the same turn and re-filed as a parked observation.)
The gate stays absolute — the fix for a safety gate people are tempted to
bypass is reducing the friction that creates the temptation, not
loosening the gate. An optional git-based staging medium is described in
`references/environments.md`.
