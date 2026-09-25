# Comprehensive Review (scheduled or fallback)

Cross-checks all OPEN observations against all skills, propagates
cross-cutting principles, and applies improvements that don't need user
input. Two modes:

- **Scheduled autonomous review (preferred):** a recurring task (e.g.
  Mon/Wed/Fri mornings) via the platform's scheduler. Runs without the user
  present and applies non-escalated observations autonomously.
- **In-session 7-day fallback:** pending at session start when BOTH are
  true: no scheduled review is registered (or none has written
  `last-review-date.txt` in 7+ days — a scheduler's "succeeded" says the
  job launched, never that the review ran), AND
  `skill-observations/last-review-date.txt` contains `never` or a date
  7 or more days old — the same boundary SKILL.md step 3 uses, stated the
  same way on purpose: at exactly seven days the two files must agree, or
  whether a review runs depends on which one the session consulted
  (a missing file is recreated with `never` — see
  Session Start steps 1 and 3; the file's value is authoritative, a date
  means a review actually ran). In an interactive session a pending
  fallback surfaces as a one-line offer and runs only if the user opts in
  (SKILL.md, Session Start step 3) — it never gates the user's task.
  Its content scales with the backlog and its frequency never does,
  because a backlog that is never drained fails quietly, by becoming too
  expensive to drain: the per-session behaviour that is correct (never
  block the user) sums to a review nobody accepts. A bounded slice keeps
  the unit of work constant as the backlog grows.

## Contents

- Approval policy
- Steps
  - Step 0 — recommend scheduled setup (fallback mode only)
  - Step 1 — load
  - Staged-work reconciliation gate
  - Step 2 — inventory skills and classify each write target
  - Step 3 — cross-check observations
  - Step 4 — cross-check principles, and audit the families for drift
  - Step 5 — apply
  - Step 6 — re-scan, then mark ACTIONED
  - Step 7 — timestamp
  - Step 8 — deliver and summarise
- Constraints
- Delivering updated skills

The material between this index and Approval policy is preamble the whole
file depends on: reachability regimes, the offline-workspace policy, and
how an aggregate review over several observation logs is scoped.

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
7-day in-session fallback catches up — where "unreachable" means the
probe found nothing there: a mount absent, a host asleep. A probe that
fails with a permission or sandbox error on a path that exists is a
third state, and it is not transient: the scheduled session's own
sandbox denies the workspace, every later firing skips the same way,
and nothing heals. Its note names the owner — "review skipped —
workspace denied by the session sandbox; grant [ABSOLUTE PATH] in the
task definition" (`references/environments.md`, "The access grant is
part of the task definition") — because an offline note for a policy
denial sends the reader to wait for a machine that is already on; (3)
when setting up a scheduled
review, bake this policy into the scheduled task's prompt, so fresh
sessions inherit it without rediscovery. A permission failure mid-run —
after the probe has succeeded — is handled the same way: skip the gated
step, record it as a manual
follow-up, and still emit the final report — a blocked step N must never
cost the report for steps 1 through N-1. None of this covers a run that
stops before Step 1: a session that goes idle after its first call
writes no timestamp, stages nothing, emits no summary, and the scheduler
records it as "succeeded" — its honest answer to the wrong question,
since a scheduler reports whether it launched the job, never whether the
job did its work. The review's completion signal is its own artefact,
the Step 7 timestamp; a scheduler's run status is evidence about the
scheduler only, and the consumer of a schedule compares the artefact's
date against the scheduler's last-run date rather than trusting either
alone.

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
  the workspace key alongside the number. **The key is an identifier:** it
  is derived from a path, and the path carries the project's name. When a
  cross-log reference leaves the machine — an upstream report, a shared
  summary — re-key the workspaces neutrally (`root`, `p1`, `p2`) and say so
  once at the top.
- **Stage each affected skill ONCE, and publish the anchor workspace
  everywhere.** One participant is the **anchor workspace**: its
  `skill-updates/` holds the staged copy, and it supplies
  `[workspace folder]` for the Step 5 seed — which then picks its
  **anchor directory** (`[today]/[skill-name]`, or a discriminated one
  under the same-day rule) exactly as in a single-log run. The two
  senses are separate axes and are always named in full: *anchor
  workspace* = which log's `skill-updates/` tree, *anchor directory* =
  which dated directory inside it. Append the manifest entry in the
  anchor workspace AND a pointer entry in every *other* participating
  workspace's `PENDING.md` — never in the anchor's own, because the
  anchor already holds the manifest entry itself, and a pointer there is
  a self-reference its own reconciliation gate would double-count —
  **creating that manifest where it does not
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
inventing anything — apply it, and always flag it as the FIRST diff in the
summary for the user to read. Where the spec is partial ("something
like…", "the old rules should probably go"), criterion (3) applies and
it stays escalated. An escalation rule guards against the agent's own
judgement, not against change as such: escalating a decision the user
already made returns their answer to them as a question, buys no safety,
and costs a cycle in which the skill stays knowingly wrong.

**The published case is applied too, with its ceremony attached.** A
restructure of a published skill needs a release branch, a test plan and
a version bump, which an unattended run cannot decide alone — but
"escalate without applying" is the wrong shape for that protection,
because staging is not publishing: nothing reaches the repository until
the publishing run, which already holds on `under_test` and on its
freshness gate. So a user-decided, fully specified restructure of a
published skill IS applied by the scheduled run, as a staged copy that
(a) bumps the version by at least a minor; (b) is flagged as the first
diff in the summary with the explicit line "published skill — install and
the release are your call"; (c) carries a manifest entry that names it as
a restructure, so the publishing run routes it to a release branch with a
test plan under the standing rule for branches (Step 5); and (d) leaves
the observation `open`, with the staged path in a `reference:` note, so
the next review's presence check closes it once the copy is installed
rather than re-applying it. What stays escalated is the decision the run
cannot make — cut a branch or ship from main, and when — never the
mechanical work. (Observed: read literally, the old proviso would have
returned a maintainer's own "priority" decision to him as a question and
left the published skill in the shape he had decided against for another
cycle; the run staged it anyway, and this paragraph makes that the rule.)

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
page in Cowork); if found, check that it covers **this** workspace before
skipping: compare the workspace the task was registered for (recorded in
`scheduler-registered.txt`, or read from the task definition) with the
`[workspace folder]` this session resolved. Same path → check its last
run as well, where the scheduler reports one: a last-run date later than
`last-review-date.txt` is a run that fired and completed no review. Say
so in one line — "fired YYYY-MM-DD, no review recorded" — as a scheduler
defect, never as a review that happened, and do **not** skip: the
fallback stays armed. Same path and no such run → skip, as before.
Different path, or the task's workspace cannot be determined → do **not**
skip. A registered scheduler that reads another workspace is not coverage
for this one; it is the fork reporting itself healthy. Say so in one line,
naming both paths and this log's open count, and route to "Several
observation logs on one machine": logs over the same globally installed
skills are a fork to consolidate, not a second queue to schedule.
"No scheduler available" means the
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
platform confirmed creation) BEFORE writing today's date **and the absolute
workspace path the task was registered for** to `scheduler-registered.txt` —
a marker holding only a date cannot answer the coverage question above, so
the next session has to go and parse the task definition instead of running
a comparison. If registration fails or can't be verified, do
NOT write the marker — the marker would permanently suppress the fallback
while no review ever runs. Tell the user registration failed and leave the
fallback active. A listed task is a registration, not a working setup:
the registration carries whatever allowed-directory grant the harness's
sandbox needs for the workspace root, the first firing's own report is
the completion check, and a first run that ends with a denial note — the
workspace exists, the task's sandbox cannot reach it — is a missing grant
on the task definition, never an outage the next firing catches up on
(`references/environments.md`, "The access grant is part of the task
definition"). No → write today's date to
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
*previous* sessions — with the sweep as shipped (the sweep block of the id
snippet, run on its own; see Archival on Write in SKILL.md), never an
improvised bulk move; where one is unavoidable, read the set once and
verify by conservation (`observation-log.md`, Archival). Read only the frontmatter of
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
the run. Keep the Step 1 file list ON DISK — never in a shell variable,
which does not survive the next tool call and is not word-split under zsh
(`observation-log.md`, "Under zsh…") — so Step 6 can re-scan against it
before anything is marked:

```bash
d="[ABSOLUTE PATH]/skill-observations/observation-log"
l="[ABSOLUTE PATH]/skill-observations/review-step1-list.txt"
find "$d" -maxdepth 1 -name '*.md' | sed 's|.*/||' | LC_ALL=C sort > "$l"
```

Both list files are overwritten by the next review's Steps 1 and 6 and
need no cleanup at Step 7; a Step 6 run against a list Step 1 failed to
refresh shows as a delta of dozens, not as a quiet pass.

**Duplicate-id check — nothing else in the process looks for one.** The id
rules say a collision is "left for the next review to renumber", and until
now no review step went looking, so a duplicate could sit indefinitely.
Worse, it is silently destructive to the review itself: any pass that
merges per-entry results **keyed by id** — the common shape when the
reading is fanned out to helpers — collapses the pair into one, and the
entry that loses is dropped from the review it was waiting for, with no
error. The collision surfaced, once, only because someone compared a
merged count against a file count.

```bash
d="[ABSOLUTE PATH]/skill-observations/observation-log"
find "$d" "$d/archive" -maxdepth 1 -name '*.md' | sed 's|.*/||' \
  | grep -oE '^[0-9]+' | sed 's/^0*\([0-9]\)/\1/' | sort -n | uniq -d
```

`grep -oE '^[0-9]+'`, not `sed 's/-.*//'`: the archive may hold legacy
`log-YYYY-MM-DD.md` files from a pre-3.0 migration, and stripping at the
first hyphen turns every one of them into `log`, which then reports as a
duplicate id. Any install that migrated — the ones most likely to have a
real collision — would have been sent chasing a phantom. The
zero-padding strip is the same one the id snippet uses, so `0091` and `91`
are recognised as the same number.

Any output is a duplicate id across the active set and the archive. Fix it
now, before the work queue is built: keep the number on the **earlier**
entry (by `date`, then by the lower `.id-floor` era), renumber the later
one to a fresh id from the snippet, update its filename and its `id:`
field together, and note the renumber in its body so a citation of the old
number can still be traced. Then re-run the check until it prints nothing.

**Per-entry header conformance — a count, not a gate.** The scan's
suspect count catches YAML that will not parse; it cannot see a header
that parses and is still wrong: an `id` that disagrees with the filename
prefix, a `status` outside the five values, a missing or blank
`siblings_checked`, or a near-miss field name (`skills:`,
`proposed_skill:`, `sibling_checked:`) that every consumer silently
ignores. Run it after the duplicate-id check, over the active directory:

```bash
d="[ABSOLUTE PATH]/skill-observations/observation-log"
nonconf=$(find "$d" -maxdepth 1 -name '*.md' -exec awk '
  FNR==1 { fm=0; bad=""; idv=""; st=""; sc=""; f=FILENAME; sub(/.*\//,"",f); pre=(match(f,/^[0-9]+/) ? substr(f,1,RLENGTH)+0 : -1) }
  FNR==1 && /^---[[:space:]]*$/ { fm=1; next }
  fm && /^---[[:space:]]*$/ { fm=0
    if (idv !~ /^[1-9][0-9]*$/ || idv+0 != pre) bad=bad " id"
    if (st !~ /^(open|actioned|declined|superseded|parked)$/) bad=bad " status"
    if (sc == "") bad=bad " siblings_checked"
    if (bad != "") print FILENAME ":" bad; nextfile }
  fm && /^id:/ { idv=$2 }
  fm && /^status:/ { st=$2 }
  fm && /^siblings_checked:/ { sc=$0; sub(/^siblings_checked:[[:space:]]*/, "", sc) }
  fm && /^(skills|proposed_skill|proposed_skills|proposes_skills|sibling_checked|siblings_check|target_files|skill_qualifier):/ { bad=bad " near-miss:" $1 }
' {} +)
n_nc=$(printf '%s' "$nonconf" | grep -c .)
if [ "$n_nc" -gt 0 ]; then printf 'NOTE: %s non-conforming headers (id / status / siblings_checked / near-miss field):\n%s\n' "$n_nc" "$nonconf"; fi
```

It reports; it does not block the review. Its false-positive rate on a
real corpus is unmeasured, so record three numbers the first time it runs
over a live log — hits, true defects among them, and how many were
normalised — and decide from those whether it stays a report or becomes
a gate (`skill-authoring.md`, "a recommended check carries three
measured numbers"). A header with no closing `---` is not reported here;
the scan's `parsed` count is the instrument for that. Fix a hit the way
the duplicate-id check fixes a renumber: one field in one file, with the
filename left alone unless the id is the field at fault.

**And key the merge on the filename, not the id**, wherever a review fans
reading out and merges results. The filename is unique by construction —
the noclobber create guarantees it — and the id is exactly the field a
collision has made ambiguous. A merge keyed on the one field that can
collide has no way to notice that it did.

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
backlog stays visible without re-entering the work queue. A condition
phrased on the state of a vehicle — a PR merged or closed, a ticket
resolved — is re-checked on the result it was meant to deliver, the text
of the target artefact, because the result routinely arrives by another
path (`observation-log.md`, "A park condition names the result, never
your own vehicle"); a refresh of an upstream-maintained skill is that
check for every entry parked on it.

### Staged-work reconciliation gate

Installation is a manual, per-item
act that happens outside any session, so no session observes it and
nothing fires at install time: a ledger whose removal trigger is an event
no session observes only ever grows. Bind the cleanup to the moment the
ledger is read — reading is the only reliably recurring event, so the
reading session owns it. First hold the tree against the manifest,
every time: list the top-level entries of `skill-updates/` (everything
but `PENDING.md`) and report, in one line, every entry no manifest
entry names — "N staging directories without a manifest entry: …".
Enumerate the listing rather than matching a date-shaped name:
discriminated anchors (`<date>-<slug>`, `<date>.2`) and hand-over
material are valid names, and an index shows only what someone entered,
so a check that reads only the index reports every unentered item as
absent — the cost is not lost work but the same work done again by a
less informed session (observed: an inventory and a diff proposal
staged for the next session's documentation pass, no entry written; the
next session inventoried the same places from scratch and missed one
the staged inventory covered). Then, for each entry in
`skill-updates/PENDING.md`
AND each skill directory under `skill-updates/<date>/` — always both,
never the manifest alone: it may be missing entries, or missing
entirely, and an absent manifest reads exactly like an empty one
(observed: eight staged skills across three dated folders, invisible for
ten days, because no session had ever created the file) — run `diff -rq`
of the staged copy
against the live skill and classify FOUR ways — because live
legitimately moves on, so a bare "differs" is not a verdict:

- **(a) identical** → installed; remove the manifest entry.
- **(b) live strictly newer / a superset of the staged copy** →
  superseded; remove the entry with a note.
- **(c) the staged copy carries content absent from live, and live
  carries nothing absent from the staged copy** → NOT installed; surface
  it, and treat the staged copy — not live — as the base for any new
  staging of that skill in this review. Also list, in
  the summary, the observations whose `resolution:` names that staged
  path (`find observation-log -name '*.md' -exec grep -l
  "skill-updates/<anchor>/<skill>" {} +` — `find`, never a bare glob, which
  zsh treats as an error when it matches nothing, and which would also miss
  `archive/`): they were marked `actioned` at staging
  and their work has not landed. They stay `actioned` — the status
  describes the review's act, and re-opening would re-queue work already
  done — but the summary carries them under "actioned, awaiting install",
  and a staged copy that reaches its SECOND review un-installed is
  escalated as a decision (install it, or discard it and re-open its
  observations) rather than carried forward a third time.
- **(d) each side carries content the other lacks** → diverged; the
  action is a MERGE — live as the base, the staged-only content folded
  back in — never a wholesale substitution of either side. After the
  merge, assert that every heading from BOTH inputs is present in the
  result and none is duplicated; the merged copy then takes (c)'s
  bookkeeping (surface it, list its observations, count its reviews).

**(b) against (c) is decided per differing hunk, never per file.**
`diff -rq` settles only (a). For every line present only in the staged
copy, ask whether live *supersedes* it — carries a line that contains
it, or evidently replaces it — or *lacks* it: every such line
superseded → (b); any one genuinely absent → (c). The file-level test
that reads naturally, "any staged-only line means (c)", misclassifies
every superseded copy, because a modified line appears on both sides of
a diff — and it errs in the harmful direction, since (c) is the branch
that makes the staged copy the base for the next staging, so the next
edit silently reverts what live gained since (observed: a copy staged
in the morning, installed, and superseded by a second same-day staging
was classified (c) on a file-level test; per hunk, both staged-only
lines had been replaced by supersets in live). The same-day second
staging under Delivery is where this arises — that rule says where the
second copy is written, this one says how the first is then classified.
A procedure that mandates an N-way classification owes the reader the
discriminating test, not only the N labels; left to invent one, each
implementer separates the first case and merges the rest.

**(c) against (d) needs the other difference set.** The per-hunk test
reads only what the staged copy has that live lacks; compute what live
has that the staged copy lacks too, before naming the case — a non-empty
first set with an empty second is (c), both non-empty is (d). Compare
heading sets in each direction (`grep '^#'` over each file, each list
checked against the other) rather than reading an interleaved line diff,
which is what invites the shortcut. Categories ordered by "which side is
ahead" are exhaustive only while exactly one side has moved, and a dated
staging folder is multi-writer by construction, so both having moved is
the normal case, not the exotic one. Size does not order them either:
the larger file is the one that grew, which says nothing about what it
lost. (Observed: a staged copy three weeks old with four sections only
it carried, against a live file with seven only it carried; (c) as then
written would have discarded live's seven, and the file-size reading
argued for (b), which would have discarded the staged four. The merge
kept all eleven.)

Reconcile in BOTH directions every time: lingering-done (installed but
still listed) and missing-done (staged but never installed) fail
differently, and only the diff sees both. Completion of a manual batch is
a claim, not a state; the check is one `diff -rq` per skill and runs in
seconds over a 20-skill batch. The Session Start Protocol (step 6) runs
the same gate whenever it announces staged updates.

**Read the ledger whole before reporting a difference.** An excerpt — the
list lines, the headings, the hits of a pattern — is a valid way to FIND
an entry and never a valid input for a verdict about one. A
hand-maintained file records its exceptions as prose that deliberately
does not look like an entry: a prune, a resolution, the line that says
nothing is pending. So a pattern excerpt drops exactly the content that
would refute a drift and keeps the content that suggests one, and its
confidence is highest where its input is thinnest. (Observed: a session
read the manifest as headings and list items, reported a round staged for
two skills and present for one, and told the user the manifest needed
clearing — twenty lines further down, in prose, it recorded the prune
that had removed the copy and the statement that no entries were open.)
Excerpt to search, full text to judge.

**A `release/`-shaped staging with no manifest entry is a GATE FAILURE,
surfaced in the summary's first line — never a copy to reconstruct
silently.** The fallback sweep over recent date directories exists to catch
a missing entry, but catching it is a finding, not a repair: a
release-branch staging is cut together with its manifest entry, its hold
and its test plan (Step 5, standing rule), and the entry's absence means the
cutting act skipped its writes, so the hold and the test plan are suspect
too. Observed, twice: a branch staged for install with no manifest entry
and the publishing registry's hold still naming the previous, abandoned
branch — found only because this sweep diffs every recent directory, and
repaired by a later interactive session a day after the cut, so the
reconstruction left no trace that the mechanism had failed. Name the
directory, name the missing writes, and treat the copy as state (c); if
the run reconstructs the entry so the rest of the gate can proceed, the
first line says so and says what was written — a repair the summary does
not mention is the silent reconstruction this rule forbids.

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
| (b) Writable but volatile, or foreign-maintained | path contains a plugin cache or version-pinned directory; or the skill is refreshed from an upstream by clone/copy or `git pull`; or **the file's own content declares a maintainer other than the user** — an attribution block naming another author, a canonical repository the user does not commit to, a `source:`/`upstream:` frontmatter field — wherever it is installed and however it got there, a hand-copied and hand-updated file included | never edit in place — the next update silently discards it, and no permission error ever fires; for a declared upstream, the route is the upstream report |
| (c) No on-disk file, or read-only | built-in / harness-provided skills (e.g. docx, pdf, xlsx, pptx, skill-creator); a mount that rejects writes | cannot be edited |

Observations targeting (b) or (c) are NOT skipped — the destination must
be one that survives and that something actually loads. Offer both routes
and let the user choose: a complementary user-owned `{skill}-extras` skill
holding only the delta **plus** a routing entry in the user's instruction
file (state plainly that without the routing entry nothing ever loads the
companion — a fix routed somewhere nothing loads is not a fix); or routing
the content straight into the instruction file, which loads
unconditionally. For (b) with a declared upstream, the default route is
an upstream issue or PR per the attribution block — the feedback
pre-flight in `references/skill-authoring.md` runs at Step 5 — with a
`{skill}-extras` companion only for a delta specific to this install
that upstream would not take; editing the file in place is not on the
menu, however writable it is. Provenance is a property of the artefact
and is stated in its first lines; install location is a fact about this
machine and says nothing about who maintains the file, so read the block
before the path (observed: a hand-installed, hand-updated copy of this
very skill, byte-identical to its published HEAD, met every clause of
(a) literally, and a review staged ten observations' worth of local
edits to it — the correct output was upstream reports and no local
edit). This skill is the standing example: wherever the user is not its
maintainer, `task-observer` is (b). Choosing the companion route may mean
creating the `{skill}-extras` skill in this review, which the Constraints
allow as the one exception to "no new skills in a review". Grow the (c) list when an update fails for
permissions; grow the (b) list when a change you made has vanished — a
rule that fires after the damage, so it is the backstop for the
attribution read, never the test.

**Step 3 — cross-check observations.** Evaluate every OPEN observation
against every skill — not just the skills named in its `skill:` list;
Principles often generalise. Build skill → [relevant observations], seeding
it from the frontmatter: every entry in an observation's `skill:` list puts
it in that skill's bucket (the first entry is primary), every entry in
`proposes_skill:` puts it under a new-skill candidate of that name, and
every entry in `target_file:` puts it under that file — a bucket the review
applies to like a skill (staged, never edited in place), instead of
remapping the entry onto the nearest skill. An observation may appear in
more than one. Then, before anything is presented:

- **Presence check, here, against the real target — and against the
  Issue, not only the suggestion.** Step 5 greps the staged copy for
  each improvement before writing; run that same
  already-applied / partially-applied / outstanding classification here
  too, before anything is presented. In an interactive review the user
  approves at this step, so Step 5 never sees an entry the user was asked
  to approve twice. Run it against the file the observation actually
  targets — its `skill:` entries, its `target_file:` entries, the code or
  register it names — never a proxy such as a routine's own `SKILL.md`
  when the entry asks for the register that routine declares. Close what
  is already applied, with a resolution naming where it was found.

- **Fix the system that owns the problem.** Before adding a skill rule,
  check whether a code, configuration or CI change would remove the
  failure. If so, recommend that fix: name the file, the change and how to
  verify it. Keep a workaround instruction only while it is needed, and
  identify the fix that will let a later review remove it. Implementing
  that fix still follows the user's scope and the approval policy.

- **Consolidate new-skill candidates by the problem they solve, not by
  name.** Independently logged proposals for the same skill will not look
  alike, because each is named after the task that surfaced it; eleven
  working names have collapsed to four skills on reading. Present merged
  clusters with their constituent observation ids.
- **Existence check before any new-skill cluster is presented.** A
  `proposes_skill:` or a `siblings_checked: none` is an absence claim
  scoped to the session that wrote it. Search the scopes that session
  could not see — other projects' `.claude/skills/` and the generator
  sources they are rendered from — by the problem terms in the bodies,
  not only the proposed name, and run the presence check above against
  any skill found: an observation proposing a skill that already exists
  elsewhere is an improvement to that skill, and may already be applied
  there.
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
  nuisance. Count the `assumed` exclusions the same way, from the
  frontmatter alone, and open each such sibling before actioning the
  entry: an exclusion grounded on `assumed` is a review item, not a
  verdict (`observation-log.md`, "Record the verdict"). Check
  `commands_verified:` in the same pass: a body that quotes a command
  with the field missing or blank quotes a command nobody ran — run it
  now, or record `NOT RUN` with why, before the entry is actioned or
  cited.
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
principle. A missing `skill-observations/cross-cutting-principles.md` is
abnormal, not empty: Session Start step 1 creates it, and it is the one
artefact of that step nothing reads until this step, so its absence has
had no observable consequence until now — a step that runs without
leaving a trace is indistinguishable from a step that was skipped
(observed: months of daily use, a hundred logged observations, the file
never created). Create it from the template in
`references/skill-authoring.md` now, say so in the summary's first line,
and log the skipped step as an observation.

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

**Verify an observation's factual claims against the live system before
promoting them into a skill.** An observation records what one session
saw; a skill states what is true. Promoting the first into the second
verbatim launders a sample into a rule, and the rule then outlives every
chance to notice.

Observed: an entry stated as settled fact that a document's `balance`
field "is always 0 in this org", and therefore could not be used to detect
outstanding payments. It was about to be promoted verbatim. One query
against the live API showed the claim was false — `balance` is populated
correctly on documents in `pending` status. The original session had
sampled only `approved` documents, where the vendor's system reports a
full `amountPaid` and a zero `balance` regardless of actual payments. The
observation was honest and the sample was unrepresentative, which is the
normal relationship between the two.

So before a factual claim about an external system enters a skill — a
schema, an enum, a field's behaviour, a transition rule, "X is always Y" —
re-run the smallest query that would falsify it, and widen the sample past
whatever state the original session happened to be looking at. Where the
system is unreachable at review time, promote the claim **with its
provenance** ("observed on N documents, all in `approved` status") rather
than as a fact, so the next reader knows what would have to be re-checked.
The cost is one query; the alternative is a rule that is wrong in exactly
the cases nobody sampled.
A command the entry quotes is a claim of this kind; its `commands_verified:`
clause (`observation-log.md`) says whether anyone has run it.

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
   the include-now set to the staged copy — **folding in the class, not
   the line numbers.** A report lists the instances its author happened
   to hit, which is the only thing a reporter can measure; completeness
   is a property of the class, visible only to whoever holds the whole
   tree. Before editing, grep the class the report describes across the
   whole bundle and fix every hit: the report supplies the diagnosis, the
   tree supplies the extent (three reports folded into one release named
   one, two and eight sites; the classes had four, three and eleven). A
   completeness claim in a report — "exactly those two", "the one site
   the earlier fix missed" — is the reporter's scope, not a finding, and
   the more carefully it is argued the more it discourages the one grep
   that would settle it, so treat the phrase as the prompt to run it.
   Record the class and the count in the commit and in the reply
   ("replaced at 4 sites; the report named 1"): it tells the reporter the
   report was read as a class, and gives the next person a search term
   that matches reality — a partial fix under a closed issue leaves the
   rest live and removes the search term that would have found it. Where
   the class is mechanically checkable, leave a check behind — a gate
   line, a lint rule — rather than only a fixed file, so the next instance
   fails at the gate instead of being reported again. When the review REWORDS a
   contribution rather than merging its diff verbatim, the merge report
   lists each reworded point beside the original bullet — the same
   point-by-point relocation verification as a moved file, because a
   rewording is a relocation with a change of words, and "the substance
   was kept" is a feeling, not a check (one such rewording dropped a
   single qualifier and was caught by the contributor, not the review).
   Record in the staging
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

**Standing rule — the review that changes a published skill bumps its
version.** When the staged skill is published, or built and awaiting its
first push (however your publication process records that state), the
review bumps the version as part of the
staging: patch for wording, minor for new rules or sections, major for
restructures. Where the skill carries a `version:` in its frontmatter,
the bump goes into the staged frontmatter; where the version lives only
in the repo's manifest (a `plugin.json` or equivalent), the review
records the intended bump in the staging manifest entry (`PENDING.md`)
so the publishing sync applies it. Either way the manifest entry states
the bump. Whoever changes the content owns the bump; the publisher only
checks that it happened — the sync may not edit skill content, and a
review that grows a published skill by a hundred lines at an unchanged
version number ships a changed skill under the one promise a version
exists to keep.

**Standing rule — a branch is cut together with its test plan and its
hold, by one command.** The session that cuts a release/test branch
classifies every change on it as *exercised naturally by a week of use*
or *unlikely to happen naturally*, and for the second class writes a test
plan — fixture, procedure and pass criterion per change — as an
observation whose `skill:` list names the branch's skill, created `open`
and parked in the same turn. Filed that way, the plan reaches the merge
review by procedure rather than by anyone remembering, and the merge step
above has the evidence it requires. A test period tests what the period's
activity happens to touch; for everything else it is only a delay. **In
the same act, cutting the branch writes the hold into the publishing
process's registry** — the skill's row gets `under_test: release/vX.Y.Z`,
with the date and whatever value it replaced — and the merge in pass 1
clears it in the same act; the principle is the observation-status rule,
"set the status in the same turn you act", applied to a different state
file. The hold is what stops the publishing cycle syncing the branch line
onto `main` as a release; if the cut does not write it, nothing does, and
its absence is indistinguishable from "not under test".

Three writes, each specified as its own rule, is how the act gets
performed with the writes it happens to remember (observed twice: first a
branch cut with its test plan and no hold, the hold reconstructed at the
next run from the staging ledger and the parked observation with no trace
in the output that the mechanism had failed; then, two days later, the
next branch cut with its test plan and neither the hold nor the manifest
entry, the registry still naming the previous, abandoned branch, both
repaired by a different session a day later). Under the second-violation
rule the remedy is structural: **the cutting act is one scripted command
whose side effects are the three writes** — the staging anchor with its
manifest entry, the registry hold, and the parked test-plan observation —
and which refuses to run if any of the three targets is unwritable. The
script itself lives in the publishing process, which owns two of the three
targets; this skill states the contract its output must satisfy, and the
reader-side rules that give the contract teeth. **An absent hold field is
an assertion, not a default**: a row that has ever carried one records
when it was cleared and by which merge, so "no field" is distinguishable
from "nobody wrote the field". The cycle **cross-checks the skill's
staging directories** for a `release/` staging newer than the row's
last-cleared date and asks rather than assumes when it finds one. And this
review's reconciliation gate (Step 1) treats a `release/`-shaped staging
with no manifest entry as a gate failure in the summary's first line,
never as a copy to reconstruct silently.

**The merge review is a fixed weekday, anchored on the install, not the
cut.** The merge decision is taken in the publishing session, which runs
on a fixed weekday; the merge review is therefore the publishing session's
weekday that follows the INSTALL of the branch line by at least a few
working sessions (the maintainer's observed choice: a Monday install →
that same week's session, four days later) — not "cut date plus seven",
which is arithmetic on the wrong event and lands on whatever day of the
week the arithmetic says (observed: a test plan, a manifest entry, a
registry row and a summary all naming the same date, a Sunday, corrected
by the maintainer to the preceding publishing weekday). The test plan's
`parked_until:` names that weekday's date explicitly, and every other copy
of the date — manifest entry, registry row, summary — is derived the same
way, so they cannot disagree. Where the install lands late in the week
(fewer than three days before the weekday), the review runs to the second
such weekday; the cutter states which was chosen and why in the test-plan
observation, once, and the other copies follow it.

**Standing rule — a review opens a freeze on the artefact.** When the
user begins reviewing a staged skill, a release branch or a diff, stop
producing new state on it. Defects found during the review are reported,
not applied — "spotted X in what you are reading; fix now, or note for
after?" — because the cost of re-reviewing is the reviewer's, so the
choice is theirs. One artefact, one version, per review cycle: if
something must change, say explicitly that the previous version is
superseded and name what to re-read. Prefer an immutable review artefact
— a diff written to a file is reviewable at the reader's pace and cannot
be invalidated by later work — and offer it first, not as the recovery.
Batch corrections behind the review, never in front of it. (Observed: a
release branch cut, folded, merged, rebased twice, version-corrected and
message-rewritten across one afternoon while the maintainer was trying to
review it; every answer they received described a state that no longer
existed by the time they acted on it, and the branch was deleted unused —
the content survived only because it had been staged to the workspace
separately.) Work done while someone is reviewing is not parallelism; it
is contention for the same object, and every revision spends the
reviewer's attention again from the beginning.

**Enumerate every staged copy of the skill before seeding, whether or
not it exists live.** `find "[workspace folder]/skill-updates" -maxdepth 2
-name "[skill-name]" -type d` (`find`, never a bare glob) and `diff -rq`
every hit against live — not only today's anchor. The presence check
below is defined against a staged copy of the *live* file, so it is
structurally blind to a draft that never went live, and that is the work
most at risk of being lost. Two ways it bites: a skill authored "from
scratch" while an uninstalled draft of the same name already carried
rules the new file lacked; and a skill seeded from live while an older
staged draft held a whole section live never received — installing the
fresh copy would have dropped it. A hit in state (c) of the
reconciliation gate is the base for this staging, as the gate says; a
hit in state (d) is merged onto live first, and the merge is the base.

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
live=$(cd "$live" && pwd -P) || exit 1   # a symlinked skills entry: find descends nothing, cp -R copies the link
s="[workspace folder]/skill-updates/[today]/[skill-name]"
[ -e "$s" ] && { echo "anchor exists — apply the same-day rule (Delivery) before seeding"; exit 1; }
find "$live" -type d | while IFS= read -r d; do mkdir -p "$s/${d#$live}"; done
find "$live" -type f | while IFS= read -r f; do cp    "$f" "$s/${f#$live}"; done
chmod -R u+w "$s"
diff -rq "$live" "$s"      # must be identical before any edit
[ ! -L "$s" ] && [ "$(stat -c %i "$live/SKILL.md" 2>/dev/null || stat -f %i "$live/SKILL.md")" != "$(stat -c %i "$s/SKILL.md" 2>/dev/null || stat -f %i "$s/SKILL.md")" ] || { echo "staged path is live under another name — not a copy"; exit 1; }
# then make EVERY edit against the staged path
```

**Seed from the CURRENT state, which for a shared artefact is upstream —
not the local file.** That `diff` proves the staged copy started from live;
it is silent on whether live is current, and it passes trivially in exactly
the state it looks like it is guarding. "Edit a copy, not the original"
answers what you may damage, not what you are building on. For any skill
with an upstream — a repository it is installed or refreshed from,
including one the user themselves commits to from several machines or
sessions — the live directory is itself a copy that does not announce how
far behind it is, and a stale local file looks exactly like a fresh one.

So before seeding, fetch the upstream revision of every file about to be
edited and diff it against live: identical → seed from live and record the
revision; divergent → pull upstream first, seed from that, and re-check
whether the observation is already addressed there, because a maintainer
who fixed it differently and better is the common case. The session editing
a skill is a parallel writer like any other, so this is the write-time
state check the procedure already requires of shared logs, applied to the
agent's own tools. Name the revision staged from in the Step 8 summary.

Two things fall out of the same fetch. It settles **section-level
provenance** — whether the passage being edited is upstream content or a
local addition — which is what the Approval policy needs in order to route
between an upstream report and a fork-local edit. And **an unreachable
upstream needs a positive control before it is called unreachable**: fetch
a path known to exist (the repository README) before concluding the network
is the problem, because a 404 on a guessed skill path with a 200 on the
README means the path assumption is wrong. Without that control the
honest-looking conclusion is "upstream unreachable, seeding from live",
which is this same failure reached by a route that feels diligent.

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
condition (SKILL.md, Acting on Observations). Classify against the
**Issue** as well as the suggestion: `already-applied` needs both — the
suggestion's substance is present AND the failure the Issue describes
can no longer occur. Where the suggestion is present but the failure
can still occur, the entry is `partially-applied`, whatever the
suggestion asked for; for an observation about a manual step or a
missing automation the test is one question — after this change, does
anyone still have to do the step by hand, and if an automation exists,
what calls it? (Observed: a script that already did the step existed;
the observation asked only that it be documented; the paragraph was
written, the entry marked `actioned`, nothing called the script, and
the backlog it was meant to clear built up again until the user asked
why — the edited skill's own rule that a check started by hand is not a
check sat a few paragraphs from the edit.) An observation closes on its
problem, not on its proposal. Mark already-applied entries `actioned`
with a resolution noting that a prior session applied them, and leave
the section alone. A `partially-applied` entry names the remainder in
`resolution:` ("suggestion applied; issue still open: <what can still
happen>") and logs that remainder as its own observation in the same
turn — the carrier pattern in `observation-log.md` — so it stays in the
queue after this one archives. When this run applies the remainder
itself, it adds only the points without a line, never restates the ones
that have one — a second copy of a present rule drifts from the first —
and names both in the resolution: the points a prior session applied and
the ones added now. Then
produce an updated SKILL.md: integrate insights into the sections where
they belong (never append an observations list at the bottom); preserve
structure, voice, and attribution; place new rules where they logically
live. Follow the editing rules in `references/skill-authoring.md` (live
file as base, staging, diff-before-overwrite).

Rewrite additions for the skill's reader rather than copying observation
prose: put the rule first, use one idea per sentence and at most one example
per change (`references/skill-authoring.md`, Lean Content — the example
stays; bare rules get violated more than rules with context). Re-check the
draft against the observation so the shorter wording preserves every
required behaviour and verification step.

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
open-source skills, the rule **never introduce `: ` into an unquoted
frontmatter value** (a subagent extending a `description:` is the
common way a staged skill's frontmatter stops parsing — see
`references/skill-authoring.md`, pre-delivery gate item 4), the rule
that any Python check run inside the staged tree runs with
`PYTHONDONTWRITEBYTECODE=1` (a `py_compile` there leaves a `__pycache__/`
the pre-delivery gate rejects, on a mount that cannot unlink it without
the delete grant), whether the pass is a content pass or a reformat —
never both in one edit, and a snapshot of the staged directory taken
before it (Delivery) — and an explicit rule that subagents do not change
any observation's status and do not write observations: a finding worth
logging goes in the subagent's final report and the parent writes it,
because two writers watching one task from two vantages log one finding
twice, and merging two entries about one fact is not the renumbering the
duplicate-id check performs (Cross-slice duplicates, below). Reserve
status marking, archival and observation writes for the parent
session. The
parent runs `scripts/validate-skill-bundle.py` on EVERY staged skill
BEFORE any status bookkeeping — a subagent's "done" is a claim about its
own edits, and the validator is the one check that sees the file the
edits produced; run after the bookkeeping, a failure means unwinding
`actioned` marks. The principle: the apply-phase is embarrassingly parallel across
skills but the bookkeeping must have one owner — split the work along
that seam.

**A delegated adversarial review needs the unchanged files its central
claim depends on.** When a fix is sent to a second agent for review, the
natural brief is the changed files, the diff and a log. That is exactly
wrong when the fix's central claim is about something it did **not**
change: an assumption about how a caller behaves, what a default is, what
some other file guarantees.

Observed: a reviewer could not find the caller whose behaviour the fix
assumed, and had to return its single most important finding — whether the
central assumption held — as "not verifiable". The minor findings came back
fine. The review ran, produced output, and silently failed at the one thing
it was for.

So build the brief from **what the claim depends on**, not from what the
change touched: name the fix's load-bearing assumption in one line, and
include every file needed to confirm or refute it, changed or not. Ask the
reviewer to report an unverifiable central claim as a failure of the brief
rather than a finding — otherwise "not verifiable" is filed beside the
minor findings and reads as a completed review.

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
detection mechanism. The check is a line-oriented set difference against
the Step 1 list, with both paths re-derived in this call and a count
guard on the new listing:

```bash
d="[ABSOLUTE PATH]/skill-observations/observation-log"
l="[ABSOLUTE PATH]/skill-observations/review-step1-list.txt"
now="[ABSOLUTE PATH]/skill-observations/review-step6-list.txt"
find "$d" -maxdepth 1 -name '*.md' | sed 's|.*/||' | LC_ALL=C sort > "$now"
n_now=$(find "[ABSOLUTE PATH]/skill-observations/observation-log" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')
n_list=$(wc -l < "$now" | tr -d ' ')
[ "$n_now" -eq "$n_list" ] || { echo "RESCAN COMMAND BROKEN — $n_now files, $n_list listed"; exit 1; }
echo "arrived:"; LC_ALL=C comm -13 "$l" "$now"
echo "gone:";    LC_ALL=C comm -23 "$l" "$now"
```

Positive control before trusting it: create a throwaway `.md` in a copy of
the directory after the Step 1 list is written and confirm `comm -13`
names it — a broken comparison can invent or hide a delta without moving
any count. A file the review itself archived since Step 1 shows under
`gone:`; that is expected, and only an unexplained departure is a
finding.
Re-run the Step 1 duplicate-id check over the new listing as well: this
re-scan is not redundant with Step 1, because the collisions it exists to
catch are the ones created *during* the run (observed: Step 1 found and
renumbered one collision; Step 6's re-scan found a second, new one —
written mid-run by a parallel interactive session at an id the directory
and the floor had both passed an hour earlier — that no earlier step could
have seen). A run that trims this step as duplicate work removes the only
check positioned after the writes it is checking for.

Then, in each applied observation's frontmatter set
`status: actioned`, `resolved: YYYY-MM-DD` (today), and
`resolution: "Staged for [skill-name] at skill-updates/<anchor>/[skill-name] (weekly review)"`
— editing only those fields, in that one file. An entry Step 5 classed
`partially-applied` is marked the same way, with the remainder named in
`resolution:` and its carrier observation already written (Step 5): a
resolved entry is the one thing no later step re-reads, so the
remainder must live in the queue, never in the resolved file. The
resolution names the staged path deliberately: `actioned` at this point means "applied to a
staged copy", and handing an artefact over and having it taken up are two
different facts — the first must not close the status of the second. The
staged path is what lets the next review find every observation whose
work is sitting un-installed (below). The `resolved:` date is load-bearing: archival is
gated on it (files archive only when it's before today), so a dateless mark
breaks the cross-session grace period. Do NOT archive same-session — the
next write on a later day archives them.

**Step 7 — timestamp.** Write today's date to
`skill-observations/last-review-date.txt`, then overwrite
`skill-observations/review-started.txt` with `completed YYYY-MM-DD`.

**Step 8 — deliver and summarise.** Stage updated skills (see Delivery
below), then present:

```markdown
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
merge review date = the publishing weekday ≥ 7 days after INSTALL;
a user-decided restructure staged: listed FIRST, with the line
"published skill — install and the release are your call";
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

**Interactive mode only:** wait for the user to acknowledge before other
work. **In scheduled autonomous mode, do not wait** — there is no user to
acknowledge, and this is the step a scheduled run must always reach, since
it is where the run stages its output and records its summary. Finish after
staging the updated skills and recording the summary. A step that blocks on
an event that cannot occur turns the run's one deliverable into a hang.

## Constraints

- Don't modify observation files beyond their `status`, `parked_until`,
  `resolved`, and `resolution` frontmatter fields — plus `reference:` in the
  one case the Approval policy names (a user-decided restructure of a
  published skill, left `open` with its staged path recorded there) —
  **with one exception: correcting a target that was recorded wrongly.** `skill:` and
  `proposes_skill:` are validated at write time, and that validation can
  return the wrong answer: a session in a stale checkout, or one resolving
  against the wrong install, judges an existing skill absent and files the
  observation under `proposes_skill:` instead. Observed: seven entries
  logged with `skill: []` and `proposes_skill: [<name>]` on the honest
  judgement that the skill did not exist — it did, in commits the session's
  checkout was 160 behind. Left alone, they sit under a new-skill candidate
  for a skill that already exists, and every later review re-reads them the
  same way. A review that establishes the target does exist may correct
  those two fields, and records the correction in `resolution:`. Nothing
  else in the body changes.
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

**A message drafted ahead of a delayed send states status that has since
changed.** Where a delivery message, commit body or summary is composed now
and sent later — a run gated behind a waiting period, an automated send, a
queued handover — its *measured* values are usually filled in correctly at
send time from live output. The prose is not. A paragraph written at draft
time naming what some other branch or commit still needs will be sent
verbatim, and it reads with exactly the authority of the measured figures
beside it.

Observed: a template whose line counts, byte counts and evidence figures
were all correct at send time, alongside a fixed paragraph saying a
particular branch was still pending a change and describing what would have
to happen at merge. By the time the automated run sent it, that branch had
landed and the change was already present in the delivered result.

So in anything drafted for later sending: **state only what is measured at
send time, or nothing.** Claims about the state of other branches, commits,
tickets or sessions either come from a value the run computes as it sends,
or come out. A sentence that was true when written is not a safe default —
it is the one part of the message nothing re-checks.

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
available. It also enforces each skill's OWN declared core ceiling
(`core_max_lines:` in its frontmatter, or a `.core-ceiling` file —
`references/skill-authoring.md`, Lean Content), and **the pack step is
never bypassed for a ceiling failure**: a skill that fails its own declared
ceiling is trimmed back under it, moving content to a reference file, and
re-validated; a skill with no declared ceiling cannot fail it and is only
reported. Hand-packing a bundle to skirt the validator is the exact failure
the gate exists to prevent (observed: three skills packed by hand with a
mirror of `pack()` when a ceiling that was then a constant in the script
failed them — every other check passed, and the constant was the defect,
but the bypass was the wrong response to it). Where the bundle ships a public extract of a private file
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
the two most recent staged copies under `skill-updates/` **that have been
installed** — never prune an uninstalled one. The invariant two lines
above says nothing goes live until the user installs it; the prune
originally counted rounds regardless, so a user who received three staged
updates for one skill and installed none of them — a plausible run when
staging keeps happening and installation waits — lost the oldest, and the
reviewable work in it, to a rule that reads as tidying. Classify each
copy with the reconciliation gate's `diff -rq` first: prune only copies
that came back **(a) identical** or **(b) superseded**; a copy in state
(c) or (d) is uninstalled work and is kept whatever its age, and named
in the summary so it does not accumulate invisibly. For the prunable
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

**The previous staged state is part of the deliverable — snapshot
before any second pass, and never let a reflow ride along with
content.** The staging tree is not under version control and the seed
is the only baseline the procedure takes, so a second pass over a staged
copy — a follow-up apply round, a density pass, a correction the user
asked for — overwrites the one state the reviewer's diff needed; the
reconciliation gate compares staged against live, which answers "was
this installed?", never "what did this pass change?". Before any pass
that rewrites a staged skill, copy the directory beside itself as
`<anchor>/<skill-name>.pre-<passname>`, named so the gate's directory
sweep and the keep-two prune cannot mistake it for a staged copy; it
goes when its anchor goes. And keep whitespace passes out of content
passes: a re-wrap moves every line, so a plain diff reports total churn
and the few lines that actually changed are invisible in it (observed:
a delegated density pass cut ~4% of the words and re-wrapped every file
to a uniform width to make its line count honest — two files it changed
by 0% and 1.2% showed as fully rewritten, and no pre-pass baseline
existed). Content first, reviewed; reformat as a separate step whose
diff can be discarded wholesale; a brief that delegates one says which
of the two it is and forbids the other. Reviewability is a property of
the pair of states, not of the final artefact — a process that produces
a new state without preserving the old one has produced a replacement,
not a reviewable change.

**Staging manifest.** Every producer that writes under `skill-updates/`
— a review delivery, an in-session apply, or hand-over material staged
for another session (an inventory, a diff proposal, a brief) — appends
one entry to `[workspace folder]/skill-updates/PENDING.md` in the same
turn, creating the file when it
is absent, and never starting it at today: on creation, list every skill
directory already under `skill-updates/<date>/` that is not identical to
live, so the manifest's first state describes the tree it indexes rather
than the one delivery that happened to create it (an appender that
assumes the file is there writes nothing, as the aggregate-run rule
above already says of a participant workspace; an index whose absence is
indistinguishable from "nothing pending" cannot be the mechanism that
stops work being forgotten). For a delivery, the entry carries the skill, the date
directory, the producer (which session or scheduled run staged it), the
observation ids applied, and a per-change summary
(observation id → section touched → one-line rationale). The install
artefact is always the `.skill` bundle, so the entry never distinguishes
a single-file from a multi-file skill. For a published skill it also
carries the community-item classification from Step 5 (include now /
test branch / declined, with the reason), per included item the
reporter's GitHub login and numeric id, so the publishing run's commit
can write the crediting trailer without going back to the API, and the
version bump for published skills (the new version, or the intended
bump where the version lives only in the repo's manifest) — and, where
the staging is a user-decided restructure of a published skill (Approval
policy), the word `restructure`, so the publishing run routes it to a
release branch with a test plan rather than to `main`. The manifest is
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
was actually staged. Hand-over material takes a provenance entry — what
it is, who staged it, which session it is for, its status — with no
install instructions, since there is nothing to install; it is staged
work, and the gate's tree-against-manifest line is what finds it when
the entry is missing. The pointer is provenance for a staging that lives
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
