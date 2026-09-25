# Environments, Activation Setup, and Handoff-Doc Mode

Load this for setup questions, compaction/resume behaviour, or when running
in an environment without filesystem access.

## Contents

- Recommended activation setup
  - The activation block
  - Anchoring the workspace
  - A session-start hook (Claude Code and similar harnesses)
  - A stop hook — the per-task backstop as a harness event
  - Verify activation in a NEW session — the installing session cannot prove it
  - Activation config — late, intermittent, and why the guard cannot live inside it
  - The probe rides inside the first batched call
  - Install-layout hazards — three ways a skill silently stops existing
  - Two harness behaviours that block the protocol rather than break it
  - If CLAUDE.md (or the equivalent config) is governance-protected
  - A third denial class: an automated content classifier
  - A mode that forbids every write by design
  - A delegated setup step is not done until you have observed it
  - Paths handed across a boundary are resolved from the far side
- Environment mappings
- Git as an optional staging medium
- Claude Code Projects — disposable threads, no local skills, no pinned
  path (based on the platform's documentation, not yet field-tested)
- Sessions whose output channel is owned by a caller
- First-run backfill
- Storage regimes
- Bundle manifest
- Compaction behaviour
- User-facing documentation
- Repo/maintainer sessions — verify commit identity before writing
- Handoff-doc mode (no persistent storage)
- Handoff-doc analysis (when one arrives)

## Recommended activation setup

Four activation tiers exist, and only the strongest is enforced. Pick
knowingly; do not assume any of the middle ones is a guarantee.

1. **Description matching** (weakest). The skill's frontmatter description
   competes with every other skill's for relevance to the opening message.
   It loses most often on short, tool-using requests that read like
   questions ("list the files in this repo"), on sessions that open with a
   small well-scoped request and grow, and whenever a domain skill matches
   the opening message strongly — topically matched skills have loaded in
   the same turn that the always-load ones were skipped. On platforms with
   no hook mechanism this is the only tier that survives an unmounted or
   unreachable config file, which is why the description itself carries a
   session-start trigger.
2. **User-level preferences** (folder-independent, still probabilistic).
   Agent settings the user controls that are injected into every session's
   system prompt regardless of which folder, if any, is connected (in
   Cowork, the personal-preferences field in the app settings; other
   agents' equivalents). This is the right home for a one-line
   probe-then-request trigger — "the session's first tool call is one
   batched call that contains an `ls` of the workspace path, with any
   session-start skill loads in that same batch; if the `ls` fails, call
   the folder-picker tool; never state whether the folder is connected
   without that probe" (why the wording is about the call's content, not
   its order: "The probe rides inside the first batched call" below) —
   because a config
   file inside the workspace folder cannot fire in the very case it
   targets: when no folder is connected, there is no config file. Verify
   the channel once by asking a folder-less session to quote its
   preferences block; a line that does not reach the agent is not a tier.
3. **Configuration instruction** (better, still probabilistic). A CLAUDE.md
   or project-instruction block, shown below. Empirically skippable under
   the same conditions as tier 1, and silently absent when the file it
   lives in is not in context (no workspace folder mounted, a session
   started outside the project). An unmounted workspace is recoverable,
   not terminal: where the environment offers a folder-picker tool
   (Cowork's `request_cowork_directory`), the folder can still be
   attached mid-session on request, and the Session Start Protocol should
   be run the moment it is — only the part of the session before the
   mount is lost. Ask early, but do not treat a declined or skipped
   folder selection as irreversible. If `allow_cowork_file_delete` or a similar
   local-filesystem permission tool is present in the tool surface, the
   session runs on the user's machine and the config is reachable; treat
   "this session runs in the cloud, so the config was not loaded" as
   unverified until the tool surface has been inventoried — and treat the
   converse the same way: an environment flag saying a folder is selected
   is a hint, and only a probe of the path in the same turn is evidence.
4. **Harness hook** (the only enforced option). A session-start hook that
   injects the instruction — and ideally the log state — into context on
   every session, e.g. Claude Code's `SessionStart` hook returning
   `hookSpecificOutput.additionalContext`. Even a hook can only inject a
   prompt; choosing to invoke a skill remains a model decision. Cowork has
   no hook mechanism; there, tiers 1 to 3 are all there is.

**Word the trigger mechanically, not judgementally.** "Task-oriented
session" asks the agent to classify the session at its first turn, before
it knows how the session will develop, and short factual-looking requests
get classified out. The block below keys on tool use instead: any turn
that will involve a tool call counts. And activation must precede
*planning*, not merely execution — where a workflow proposes a plan for
approval first, a plan written without the relevant skills carries
uninformed decisions past the review gate, and approval locks them in.
Load skills before exploring, researching or drafting the plan: both,
skill first.

**Select on the decision, not on the artefact.** Selection and loading are
separate steps, and the selection step fails in its own way: it runs
against what the user handed over — files to read, a link, a screenshot —
so every skill whose description names a *subject* is missed whenever the
request's surface form is an activity no skill claims. Before answering,
name the DECISION the user is making and match the installed descriptions
against that ("the deliverable is advice about X" → load the skill whose
description names X), even though the request arrived as a document to
review. The high-risk shape is an attachment plus an open question — "here
are two files, what do you think?" — which presents as a reading task and
hides its own domain; observed, it ran for four substantive turns of
domain advice with the domain skill unloaded, while the session-start
skills had loaded correctly. That is what makes this distinct from an
activation-config failure: the mechanism worked and still selected the
wrong set. The failure is silent by construction, because a skill that
never loads cannot announce that it was relevant, so the check belongs in
the checklist rather than in a disposition.

### The activation block

```text
Before the first tool call of any session — and before writing or
proposing a plan, not merely before executing one — invoke the
task-observer skill AND execute its Session Start Protocol (storage
check, frontmatter scan, review trigger). Loading the skill and running
the protocol are separate steps; a session that loads the file and stops
has activated nothing. Any turn that will involve a tool call counts; do
not classify the session as "too simple" from its opening message.
A step you did not run is reported before the answer, in one line — never
after it, where it reads as a suggestion. If the skill does not resolve on
this turn, say which probe told you so (the skill listing, or the skill
directory on disk), re-check the listing on every later turn that makes a
tool call, and run the protocol the first time it resolves — a "not
installed" verdict holds for one turn.

Select skills on the DECISION the request is about, not on the artefact it
arrived as. Name what the user is deciding, then match the installed skill
descriptions against that — a request handed over as a file to review
still needs the skill whose description names its subject.

After completing each task, check the observation records written this
session and report a one-line summary (ids and titles, or "none logged
and why"). This is the activation backstop: it forces a look at the log,
so a session that silently skipped the protocol is discovered at the
first task boundary instead of never.

Loading a skill is not complete until you have queried the observation
log for OPEN observations naming it and read their bodies:
  find "[ABSOLUTE PATH]/skill-observations/observation-log" -maxdepth 1 \
    -name '*.md' -exec grep -l "skill:.*<skill-name>" {} +
(Use find, not a bare *.md glob. Under zsh an unmatched glob is an error,
so on an empty log the command never runs and the enclosing block aborts —
and 2>/dev/null does not help, because the redirection belongs to a
command that never starts. This is the first thing that fires on a fresh
install, in every session, for as long as the log is empty.)
Apply their insights to the current work — meaning: let them change what
you do in THIS task. Editing the skill file, or writing the rule into any
other file a later session reads, is acting on the observation and waits
for the review. See "Log, don't act" in SKILL.md: the test is whether the
action leaves a durable change outside the observation log. Run this at every skill load, however many skills load
in one session. The session-start scan does not cover it: that is a
frontmatter sweep over every observation at session start, this is a
body-level lookup for one skill at the moment its rules are applied.

The task-observer workspace for this project is:
  [ABSOLUTE PATH]
Every path the skill uses derives from that root and nothing else:
  [ABSOLUTE PATH]/skill-observations/observation-log/   (the log)
  [ABSOLUTE PATH]/skill-observations/cross-cutting-principles.md
  [ABSOLUTE PATH]/skill-updates/                        (staging root)
  [ABSOLUTE PATH]/skill-updates/PENDING.md              (staging manifest)
Never resolve any of them from the current working
directory — a cwd inside an ephemeral checkout (a git worktree, a temporary
clone) is torn down and takes the log with it. Never place the workspace
inside a skills-discovery directory or any path linked into one. If this
environment mints a separate project identity per checkout, or more than
one agent works this project, the pinned path above is the single shared
location; do not derive one per session, tool or project.

A subagent dispatched by a session that already runs this protocol does
not run it again and does not write to the log. The controller observes,
because only it sees the whole task and its review; a subagent that
notices something worth logging says so in its final report, and the
controller writes it, running the id snippet per write. A start-up rule
in a project file reaches every agent the project ever dispatches.

An observation file comes into being only through
  bash "<skill directory>/scripts/new-observation.sh" <slug> "[ABSOLUTE PATH]"
which prints the path to write into. Never by copying another file's
header or counting a listing — including on the turn after a
compaction, when the skill body is out of context.
```

`<skill directory>` is the installed skill's own directory (the one
holding `SKILL.md`), substituted at install exactly like
`[ABSOLUTE PATH]`; where the harness cannot run a script, drop the
paragraph and keep the rest — the inline id snippet in SKILL.md is then
the write path.

### Anchoring the workspace

SKILL.md's `[workspace folder]` definition states the rule; this is where
to pin it, how a stable anchor still goes plural, and which plural case is
legitimate.

Fill in the path when installing. Pinning turns anchoring into a one-time
decision instead of one the agent re-litigates every session with a fresh
chance to get it wrong. Pin the ROOT, and list the derived paths: a pin
that names only the observation-log directory — the place split-brain was
first noticed — leaves the staging root, the manifest and the principles
file to be re-derived by every session, and parallel sessions resolve
them plausibly and differently (observed: two sessions staged under
`skill-observations/skill-updates/`, beside the log, while a third staged
under `skill-updates/` at the root — three writers, two staging roots,
one manifest that saw half the work). Scope the workspace to what is being observed:
skills installed globally are observed from every project, so their log
must be one absolute path shared across projects and tools — a per-project
or per-tool workspace scatters observations about global skills across
every project the user touches, and a review run in one never sees the
others. Where the environment provides a managed persistence directory
under the project identity (a memory directory it loads every session),
that directory and the identity root are both "stable"; anchor inside the
managed directory when one exists, otherwise on the identity root — never
both.

**Scope matches installation scope.** Skills installed at user or global
scope are observed from every project, so their log is one user-scope
path shared by every project, tool and agent; a per-project anchor is
right only for skills that exist in one project. A stable anchor can
still be plural — in Claude Code the identity is derived from the
directory the session starts in, so per-subfolder habits shard the log
into several stable anchors that each look like the only one. Decide the
scope once, at install, and pin it. **One plural case is legitimate and
is not a shard:** logs deliberately kept apart because their observation
bodies carry task context that does not travel, over skills that are
nonetheless installed globally and therefore shared. Read the multi-log
block in `weekly-review.md` before consolidating anything — it defines
that case and the aggregate review that serves it. A reader who stops at
this paragraph consolidates a set that was meant to stay separate.

**The fork rule as usually stated describes the harmless case.** "A second
**empty** log beside a populated one is a silent fork" — but an empty log
announces itself: the first scan returns nothing, and nobody trusts a
backlog of zero. The damaging fork is the one that has accumulated its own
entries. From inside it looks exactly like a working log: the scan returns
files, the review finds work, every instrument reports health. Nothing in
it can reveal that it is a shard.

And pinning does not settle it. Observed: a workspace pinned in a wired
session-start hook, correctly configured, running beside a second populated
workspace for three days and producing colliding ids. The pin governs the
sessions that read it; it does nothing about a session that resolved its
anchor before the pin, or by another route.

So the detection has to be positive, and it is nearly free: at the end of
the session-start scan the agent is already holding the `skill:` values of
every entry. A log whose targets are overwhelmingly **user-scope** skills,
while the log itself sits under a **per-project** path, has already
declared the mismatch — two `ls` and a comparison. Run it when the anchor
is per-project and the targets are not; report the candidate shard rather
than consolidating on your own judgement, because one plural case is
legitimate (see the multi-log block in `weekly-review.md`).

**The session-start scan lists the neighbours on every run.** One line of
the scan snippet finds every `skill-observations/observation-log/` up to
three levels under the pinned root's parent and prints each with its file
count — `logs under the parent (…): /a/proj=157  /a/other=19`. One entry
is the ordinary case. Several are either shards or the legitimate plural
case, and the line cannot tell which: report it in one line, route to
"Several observation logs on one machine" in `weekly-review.md`, and never
consolidate from the scan. The probe is bounded by the parent's depth-3
tree, not by any log's size; an empty line means the probe could not read
the parent, since the pinned log itself is always under it.

**Before creating a log, search for one.** Check the plausible anchor
candidates — the pinned path, the project identity root, the
environment-managed persistence directory, the shared folder, the other
agent's equivalent — for an existing `skill-observations/` workspace.
"The pinned path" has more than one source: the instruction file, and
any registered session-start hook. Grep the harness settings and the
installed plugins' hook manifests for the skill's name, then read the
path each hook script derives — a hook that counts observations
somewhere is a pin whether or not the instruction file names it
(observed: the instruction file had no pin, a user-scope hook derived
the workspace from the home directory, the probe checked only the
documented defaults and created a second workspace fifteen minutes
after the real one; the hook kept counting the original, so every
observation written to the new path was invisible to it). Where a
system already reads or writes state, that location is authoritative
and the documented defaults are the fallback; an existence probe over
the defaults alone reports "not found" for every install that deviated
from them. Never create a workspace while a hook or config names a
different root: reconcile first. If one exists, adopt it, or
consolidate deliberately with the user. A fresh
empty log beside a populated one is a silent fork: both grow
independently, ids collide, and each session sees only half the history.
Consolidating a shard is mechanical: carry over only the entries still
`open` — its already-actioned entries re-import as duplicates of work
the target may hold too — re-issue each id from the target log's own
counter (the snippet, one write at a time, never a pre-computed range),
mark each source entry `actioned` with a resolution naming the target
id, and then leave a pointer file at the abandoned location so sessions
anchored there get redirected instead of re-creating the fork.

**Report-back mode — when no pinned path resolves.** The Session Start
guard warns and re-anchors when the resolved workspace sits under an
ephemeral checkout. That assumes a stable path exists to re-anchor on. In
a disposable worker — a Claude Code Projects thread, any agent whose only
writable location is a clone torn down at the end of its task — there is
none, and writing into the clone anyway produces observations that vanish
with it while every write reports success. So the branch is: do not write
into the clone; carry each observation in full in the final report to
whatever coordinates the work, or commit it to a dedicated observations
repository via PR, and say in the report which route was taken. See
"Claude Code Projects" below for the install, activation and log-route
consequences.

**Config detection (once per session):** with filesystem access, check the
workspace root's CLAUDE.md (or equivalent) for a task-observer activation
instruction — suggest adding it if absent. **Suggest; do not create.** If
no config file exists at all, offer to add one and let the user say yes:
creating a tracked project file changes every future session's behaviour,
and the governance-protected fallback below exists precisely because
writing to a shared config is not a free action. SKILL.md step 4 says
"suggest" and these two are read in sequence, so they must not disagree.
Without filesystem access, check the system prompt / project
instructions and suggest the user add the instruction there. Keep the
suggestion to a sentence or two. The block above is the propagated
artefact: suggest it whole, including the anchoring paragraph, because
constraints that live only in SKILL.md arrive after the decision they were
meant to govern.

**Load is not activation.** The failure the block's wording guards
against, reported from real use: the agent loads the skill per the
config instruction, then stops — the Session Start Protocol (log files,
scan, review trigger) never runs, and nothing surfaces the omission
because a loaded-but-inert skill looks identical to an active one from
the user's side. It moves only when the user explicitly asks "have you
executed the session start protocol?". Hence the two belts above: the
instruction demands the protocol by name, not just the load, and the
post-task summary line makes silent inactivity visible at the first
task boundary. If you adopt only one line of the block, adopt the
post-task check — in field use it turned an intermittently-activating
install into a stably-recording one.

That check is prose in the same file as the rule it guards, and it fails
with it: whatever made a session skip the block's first paragraph makes it
skip the third (observed: seven task boundaries and over a hundred tool
calls with both configured tiers fired, neither the protocol nor the
backstop run, and activation only when a different model read the same
block mid-session). A backstop written in the medium of the rule it
guards is one layer, not two. The second layer has to hang on an event
the harness raises, not on the agent re-reading its instructions: where
the harness offers a stop or turn-end hook, the objective check is cheap —
the session used tools, and nothing under `observation-log/` or
`checkpoints.log` has been written since it started — block once, with a
one-line instruction, and stay silent otherwise. Classify each
enforcement layer by what it needs in order to function: a filesystem
write survives into any session type, a prose reminder survives only
while the prose is being acted on.

A third belt sits inside the protocol itself: its scan appends a dated
line to `checkpoints.log` (SKILL.md, Session Start Protocol step 2), so
the protocol leaves its own trace and a session that skipped it is
detectable afterwards rather than only noticeable in the moment. That is
the missing half of the diagnosis above — the load produces a visible
artefact in the transcript and the protocol produces none, so having
loaded the skill feels like having done the thing the skill asks for.
Treat *loaded but not run* as a distinct failure cause, alongside the
skill being absent, truncated, or present and skipped: it is the likeliest
of the four, precisely because the load's visible success stands in for
the protocol's invisible omission, and the aggravating condition is the
same one that produces a skipped load — an opening message small enough
that a full startup protocol feels disproportionate to it.

**Anti-pattern:** don't chain activation through another skill — load
task-observer and related skills independently from configuration; a broken
chain silences all observation activity.
A start-up rule written into a project file reaches every agent the
project dispatches, so a controller and its workers are concurrent writers
of one log unless the block above stops the workers.

### A session-start hook (Claude Code and similar harnesses)

Capture is hard-enforced by checkpoints hooked onto tool calls; the review
trigger in the Session Start Protocol is a soft step — read a file, compare
a date — and it is skipped the same way activation is. The failure is
self-concealing: capture keeps producing, the log looks healthy and
growing, and the only artefact recording the miss is a file reading
`never` that nobody reads. Treat "is the review trigger structurally
enforced?" as an install-completeness check, and where the harness offers
a session-start hook, have it compute the state and inject it rather than
asking the agent to go and look:

```bash
#!/bin/sh
# SessionStart hook: inject activation + review state as additionalContext.
d="$OBS_WORKSPACE/skill-observations"      # the pinned absolute path
open=$(find "$d/observation-log" -maxdepth 1 -name '*.md' -exec grep -l '^status: open$' {} + 2>/dev/null | wc -l | tr -d ' ')
last=$(cat "$d/last-review-date.txt" 2>/dev/null || echo never)
msg="Invoke the task-observer skill before the first tool call. Observation files are created only by scripts/new-observation.sh in the skill directory, never by copying a header."
if [ "$open" -gt 0 ]; then
  msg="$msg $open open observations; last review: $last."
  case "$last" in (never) msg="$msg Offer the review." ;; esac
fi
printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$msg"
```

The count is of files whose `status` field reads `open` — not of files
in the directory. Resolved entries deliberately stay in `observation-log/`
until the day after they were resolved (the grace period lives in the
file, not in session memory), and parked entries are decided and out of
the work queue, so a raw file count overstates the backlog by every entry
the last review just closed, for a day, in every session. Compare dates
without `<` in `[ ]`: ISO dates sort lexically, so
`[ "$(printf '%s\n%s\n' "$last" "$cutoff" | sort | head -1)" = "$last" ]`
is true when `$last` is not later than `$cutoff`, in every POSIX shell
(`\<` is a bash/ksh extension that zsh rejects and `sh` does not know).
Two details that matter when building one: `grep -c` exits 1
on zero matches while still printing `0`, so `$(grep -c … || echo 0)`
yields two values — capture the output and ignore the exit code; and prove
the reminder branch fires by running the hook against fixtures at `never`,
30 days stale and 2 days stale, confirming the third stays silent. A nag
that never fires and a nag that is correctly silent look identical from a
passing run.

### A stop hook — the per-task backstop as a harness event

The per-task backstop in the activation block is prose in the same file as
the rule it guards, so it fails together with it: a session that skipped
the protocol skipped the backstop at every task boundary too. Where the
harness has a stop event, run the check there instead: *has this session
used tools, and has anything under `observation-log/` or `checkpoints.log`
been written since it started?* If not, block the stop once per session
with a one-line instruction; stay silent for conversation, for a session
that already wrote, for a second block in a row, and when the log cannot
be read. Node, no dependencies; substitute `[ABSOLUTE PATH]` as elsewhere:

```js
// Stop hook: the per-task backstop as a harness event instead of prose.
const fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const MIN_TOOL_USES = 3; // below this the turn is conversation, not work
const base = path.join('[ABSOLUTE PATH]', 'skill-observations'); // the pinned workspace
const block = (reason) => { fs.writeFileSync(marker, new Date().toISOString()); console.log(JSON.stringify({ decision: 'block', reason })); process.exit(0); };

let input = {};
try { input = JSON.parse(fs.readFileSync(0, 'utf8') || '{}'); } catch { process.exit(0); }
if (input.stop_hook_active) process.exit(0);            // never chain a second block
const session = String(input.session_id || '').replace(/[^A-Za-z0-9_-]/g, '');
const transcript = input.transcript_path;
if (!session || !transcript) process.exit(0);

const marker = path.join(os.tmpdir(), `task-observer-backstop-${session}`);
if (fs.existsSync(marker)) process.exit(0);             // once per session

let started = 0, toolUses;
try {
  const st = fs.statSync(transcript), text = fs.readFileSync(transcript, 'utf8');
  toolUses = (text.match(/"type":\s*"tool_use"/g) || []).length;
  // Birth time is 0 where the filesystem has none and equals ctime where the
  // platform substitutes it; either would make every file read as untouched
  // or touched. Fall back to the transcript's first timestamp.
  if (st.birthtimeMs > 0 && st.birthtimeMs < st.ctimeMs) started = st.birthtimeMs;
  else { const m = text.match(/"timestamp":\s*"([^"]+)"/); if (m) started = Date.parse(m[1]) || 0; }
} catch { process.exit(0); }
if (toolUses < MIN_TOOL_USES) process.exit(0);

if (!(started > 0)) block('task-observer backstop: cannot tell when this session started (no birth time, no ' +
  'transcript timestamp), so it cannot check the log. Check by hand that this session wrote an observation ' +
  'or a checkpoints.log line, and report the one-line summary. Fires once per session.');

const files = [path.join(base, 'checkpoints.log')];
try {
  for (const n of fs.readdirSync(path.join(base, 'observation-log')))
    if (n.endsWith('.md')) files.push(path.join(base, 'observation-log', n));
} catch { process.exit(0); }                             // unreachable log: stay silent
const touched = files.some((f) => { try { return fs.statSync(f).mtimeMs > started; } catch { return false; } });
if (touched) process.exit(0);

block('task-observer backstop: this session used tools but wrote no observation file and no checkpoint line. ' +
  'If the skill was never invoked, invoke it now; then write pending observations or append a ' +
  '"no observations" line to checkpoints.log, and report the one-line summary. Fires once per session.');
```

**The session's start time is the fragile input.** A transcript's birth
time is `0` on filesystems that do not record one, and some platforms
return the change time in its place, which moves on every append; either
makes the comparison meaningless, and the first makes the hook
permanently silent. So birth time counts only when it is non-zero and
earlier than the change time; otherwise the hook reads the first
`"timestamp"` in the transcript, and where neither exists it blocks once
with a request to check by hand rather than falling silent.

Its known limits: it compares modification times, so a parallel session
writing to the same log reads as this session's write (a missed block,
never a false one); it fires for the main agent only, so a subagent —
which by the activation block writes nothing — is never blocked, and a
harness that runs the hook for a subagent whose caller owns its output
must not wire it there ("Sessions whose output channel is owned by a
caller"); and like every trigger, it is armed only once it has matched the
real event — run it against a transcript with tool calls and no write,
then against the same with a checkpoint line appended, before trusting
either outcome.

### Verify activation in a NEW session — the installing session cannot prove it

The config file is read at session start, so an instruction written
mid-session takes effect only on the next one; and in a harness that
hot-loads a newly installed skill, the skill being callable right after
install proves nothing about activation — it was invoked by hand. The
installing session therefore sees everything pass (bundle complete, skill
listed, protocol ran, hook emits valid JSON) while the one thing that
matters is untested, and the tempting close is "installed and tested".
Report the install as **activation unverified** until a fresh session has
been seen invoking the skill on its own, and name the check: in the next
session, before any work, confirm the skill was invoked (not merely
listed) and that the Session Start Protocol ran — verify by evidence of
invocation, not by a side effect that a hand invocation would also
produce. If the environment offers no way to start a fresh session from
the installing one (a GUI-only harness, no CLI), hand the check to the
user as the first item of their next session; an unverifiable step never
closes silently as "tested".

The runtime cannot diagnose its own absence — Session Start step 4 only
runs once activation has already succeeded — so the external diagnostic
is the one that catches a skipped install step: **if
`skill-observations/observation-log/` does not exist after a few sessions
of tool-using work, activation never happened**; check the activation
block in the config, or install the hook. The README carries the same
diagnostic for users who never read this file.

### Activation config — late, intermittent, and why the guard cannot live inside it

SKILL.md step 1 carries the instruction (on turn 1, load the session-start
skills directly rather than assuming the config did, and read the config
yourself if the mount resolves but its content is not in context). This is
the reasoning behind it, and the reason that instruction is only the backup.

In some hosted or bridged session types the activation config — a project
instruction file, a session-start hook's context — does not reach context
until the **second** user turn, while the workspace it lives in is already
mounted and probes clean. From inside turn 1 a config that is merely late is
indistinguishable from one that is absent, so a whole substantive turn can
run with no session-start skill loaded. **A config delivered on a later turn
than the work it governs is equivalent to an absent one for that work.**

It has also been seen **intermittent** rather than merely late: present for
turns 2 and 3 of a bridged session, then reported as no longer present at
turn 4, with no change in the workspace link and nothing the session did to
cause it. So a rule anchored on "once it arrives it stays" fails the same way
a rule anchored on "it arrives first" does. Do not treat an earlier turn's
config as still in force.

**The skill listing lags the same way, and an absence verdict expires the
same way.** The instruction can be present and fire on a turn where the
skill it names does not yet resolve against the harness's own listing of
invocable skills — right after the instruction was added mid-session, or
in a harness that builds its available-skill list once near session
start. The honest response on that turn is a disk check and "not
installed", and that verdict is true only for the turn it was made on;
nothing revisits it, so when the listing catches up every tool call in
between went unobserved and the earlier claim stands uncorrected
(observed: the skill appeared in the listing four turns after the
verdict, and the protocol first ran then). So a "not installed" verdict
names the probe it came from — the listing lookup, or a disk check of the
skill directory — because the two disagree exactly here, and it holds for
one turn: re-check the listing on each later turn that makes a tool call,
and run the Session Start Protocol in full the first time the skill
resolves. Like the guard below, this rule cannot live only in the skill
that failed to resolve; the line that carries it is in the activation
block.

The durable form: **a guard against an activation config failing to load
cannot live inside the thing that config loads.** The guard in SKILL.md step
1 is in `task-observer`, which is loaded *because* the config says to load
it — so on the turn where the config is missing, nothing puts that guard in
context either. By construction it cannot fire on turn 1.

The primary guard therefore belongs in the earliest channel verified present
on turn 1 — in most harnesses the user-level preferences or system-prompt
block, which is where the line

> then read the workspace config and follow it before any other work

goes. See the activation tiers above: that channel is tier 0, and the step-1
guard is the backup for turns 2+ and for sessions where the skill happens to
be loaded directly.

**Log the cause, not just the miss.** When a session-start load is skipped,
the fix depends on which of these it was: *absent* (config unreachable),
*present-but-not-yet-injected* (late — record the turn it arrived),
*present-but-not-yet-resolving* (the instruction fired and the skill was
not in the listing — record the turn it appeared), *present and skipped*
(attention), or *loaded-but-not-run* (the invocation succeeded and the
protocol inside it never executed). Only the first two are fixed by
changing the channel, and the third by re-checking the listing; the last
two are not environmental, and an environmental cause found first will
otherwise absorb the whole explanation.

### The probe rides inside the first batched call

The probe line can be present and correct on turn 1 and still not fire
first. Observed twice in one day, in two sessions: the preferences block
carried "before any other tool call, `ls` the workspace path" verbatim, and
the session's first tool call was a batch of `Skill` invocations; the probe
rode in the second batch. No harm either time — the folder was mounted —
which is the point: the failure is only ever detectable in the sessions
where it costs nothing, and it costs everything in the session where the
folder is not there and the agent asserts that it is.

The cause is a contest for one slot. Loading the session-start skills is
the one action that genuinely *is* prior to the work, so it recruits the
same "before anything else" position the probe needs, and it arrives as an
activation of the agent's own setup rather than as an instruction — which
feels like preparation, not action, and wins. Stating the precedence more
firmly does not change that; in the second instance the agent had loaded
the skill carrying the rule in that same first batch and the rule still
did not register as violated, because the load had discharged the felt
obligation.

So the rule is about the **content of the first call, not its order**: the
session's first tool call is a single batched call that contains the probe,
and any session-start skill loads ride in that same batch — never in an
earlier one. That removes the contest instead of adjudicating it, the
harness's parallel-call guidance already permits it, and it is checkable
after the fact from the transcript (an ordering rule between two "first"
actions is not). SKILL.md step 1 states it that way; the tier-2 preferences
line above is worded to match; the activation block's "before the first
tool call" is satisfied by the load riding *in* that call.

### Install-layout hazards — three ways a skill silently stops existing

Each of these leaves no error. The skill simply stops being offered, or an
activation tier stops firing, and the only symptom is that the Session Start
Protocol no longer runs — which is indistinguishable from a session where it
ran and found nothing.

**Skill discovery is exactly one level deep.** The host reads the skills
directory and looks for `<entry>/SKILL.md`. There is no recursive lookup. On
a library of any size the natural organising instinct is to group skills into
category folders — `skills/seo/`, `skills/clients/`, `skills/writing/` — and
doing so makes **every skill inside them cease to exist**: no error, no
warning, no change in behaviour except that the skills stop being offered.
There is nothing to debug, because "not found" has no error to report. The
layout is not merely the happy path; it is the rule, and it does not travel
with the maintainer who reorganises six months later. Keep every skill
directly under the skills directory.

**A backup inside the skills directory registers as a rival skill.** The
obvious way to back a skill up before overwriting it —
`cp -r ~/.claude/skills/task-observer ~/.claude/skills/.task-observer-backup`
— puts a second copy where the host is looking. The leading dot does not
exclude it from discovery. The available-skills list then holds two entries
with near-identical descriptions, and the backup still advertises the OLD
version's trigger, including its session-start instruction. That defeats the
upgrade at the one activation tier that survives an unreachable config:
description matching now has two candidates competing for the same trigger,
one of them the file the upgrade just replaced. Back up **outside** the
skills directory.

**A hook registered by script path dies when the exec bit goes.** The
docs' example reads most naturally as naming the script directly:

```json
{ "type": "command", "command": "'/path/to/hooks/task-observer-activation.sh'" }
```

Anything that rewrites file modes — a cloud-drive resync switching between
stream and mirror mode, a restore from an archive, a checkout on a
filesystem without permission bits — returns the file as mode 600, and the
hook then fails with "permission denied" on every session start with
nothing surfacing the error. Observed: the enforced activation tier was
dead for days. Register the interpreter instead
(`"command": "bash '/path/to/hooks/…'"`), which does not depend on the exec
bit, and treat "the Session Start Protocol stopped running" as a prompt to
check the hook rather than the skill.

### Two harness behaviours that block the protocol rather than break it

**A command-shape guard can refuse a read-only call.** Some setups run a
pre-tool hook that inspects the literal command text for governed path
segments combined with a write indicator (`=`, `>`, `cp`, `mv`) and denies
the whole call when both appear anywhere in the string — regardless of
whether the path is actually being written to. Two consequences worth
knowing before diagnosing: a `cd` into a governed directory followed by a
read-only script call is denied even though nothing is written; and a
**blocked command merely quoted inside an observation body** can trip the
same guard when that body is written through a shell. Neither is a
permission problem with the destination. Where this bites, invoke the
script with an absolute path and no `cd`, and write observation bodies with
the editing tool rather than through a shell. A guard that refuses the
session-start scan itself is handled the same way — degrade to flat
commands, never skip the step (`observation-log.md`, "A refused snippet is
a degraded path, never a skipped step").

**Staging a harness configuration change is not like staging a skill.** A
skill's `SKILL.md` is read by itself; a corrupted staged copy fails to parse
and nothing else is affected. A harness config file — `settings.json` with
its hook entries, deny-lists and protection rules — is read by the harness,
and it commonly carries **other protections alongside** the thing being
changed. The natural delivery shape for a config change is a fragment:
"here's the new key, add it under `hooks`". A hand-merge that goes wrong
there does not fail loudly; it produces a valid file with the other
protections missing.

So: deliver a config change as a **complete replacement file** built from
the user's current one, never as a fragment to splice in; state in one line
what else that file was carrying, so the user can verify it survived; and
where the harness supports it, prefer a separate file over editing a shared
one.

### If CLAUDE.md (or the equivalent config) is governance-protected

Some setups guard shared config files with hooks or file-protection rules
that deny agent edits. If an edit to the config is denied, never retry the
same edit blindly and never attempt to bypass the guard — a denial is the
governance system working as intended, and a silent skip is just as bad
(the user believes activation is set up when only description-level
matching is active). Surface the denial to the user and offer these
fallbacks, lightest first: (a) if the denial came from an interactive
permission system rather than a hard guard — the denial message offers an
approval path, names a permission rule, or otherwise indicates consent
would clear it — ask the user to approve a retry of the same edit; one
confirmation resolves it, and escalating past this step spends user effort
on something already recoverable; (b) ask the user to paste the activation
block into the file themselves; (c) if the user's environment provides its
own temporary-authorization mechanism (a marker file, an environment
variable, or similar), ask the user to authorize the edit through that
mechanism and revoke it afterwards; (d) where the platform supports
unguarded project-level instruction files, add the activation instruction
there instead. Branch on whether the denial is retryable-with-consent or
categorical: an interactive permission prompt is cleared by asking, a hook
or file-protection rule is not, and collapsing both into "hand the task
back to the user" is safe but consistently over-escalates. Never assume
unrestricted edit access to shared or governance-tracked config — many
setups gate exactly those files.

**The same shape applies to a blocked hook installation.** The hook
option from the same paragraph writes to the harness's settings file or
hooks directory, and those are gated at least as often as the config
file. A denied hook install follows the rules above unchanged: never
retry the same install through a different tool or path, never bypass,
surface the refusal, then fall back lightest first — ask for a retry if
the denial is retryable-with-consent; ask the user to add the hook entry
themselves (hand them the exact JSON or script); use a temporary
authorization mechanism if one exists; and if the hook cannot be
installed at all, fall back to the declarative config instruction, saying
plainly that the enforced tier is not in place and the probabilistic one
is. A hook that silently failed to install is worse than none: the user
believes the strongest tier is active.

### A third denial class: an automated content classifier

The fallbacks above branch on two kinds of denial: a hard guard (a
governance hook, a file-protection rule) and an interactive permission
prompt that one user approval clears. There is a third, and it behaves like
neither.

An automated content classifier can refuse the edit on the grounds that the
activation block is **third-party instruction text being written into a
user-scope config**, where it will steer every future session. Reported in
the field as `Instruction Poisoning`, on a fresh install into a global
Claude Code skills directory.

What follows from that:

- **Rewording does not help.** The objection is to provenance and always-on
  scope, not to the phrasing, so there is no lighter version to retry.
  Shortening the block and trying again is the obvious move and it fails —
  make that attempt at most once, then stop.
- **The cheapest remaining fallback is not in the list above.** Ask the user
  to change permission mode, then retry the *same* tier. In the reported
  case the wall was the permission mode rather than a policy: once the user
  switched out of auto mode, the hook tier installed with no friction at
  all. Try this before handing the block over for pasting.

**The ladder is not monotonic.** Tier 4 — the session-start hook, which this
file elsewhere calls the only enforced option — can be blocked *harder* than
tier 3, and for an unrelated reason. In the same install the hook was
refused as `Auto-Mode Bypass`: configuring a hook changes what the harness
executes automatically, which that permission mode withholds categorically
rather than on content. Writing the hook *script file* alone, wired to
nothing, was refused on the same grounds. So tiers 3 and 4 failed for
different reasons that happened to coincide, and the tier presented as the
robust fallback for a blocked config edit was the one held furthest out of
reach. Do not present the ladder to the user as "if 3 fails, 4 will work".

### A mode that forbids every write by design

Some modes — Claude Code's plan mode, any propose-only mode — permit
every read and refuse every write for the whole turn. That is not a
denied write: retrying and switching tools are wasted calls, the log is
not unwritable, and "failed N times" is the wrong report when the
environment is telling the truth. A gatekeeper and a mode are opposite
failures — one is retried, the other accepted and deferred.

1. Run the read steps normally: the scan, the review-date check, the
   per-skill lookup. A read-only session is fully observant.
2. Defer, never skip, the writes: storage creation, `.id-floor`,
   archival, the `checkpoints.log` line. Ids are resolved at flush
   time, never now.
3. Queue pending observations where the turn cannot eat them: a
   numbered list in the plan or handover text itself. A rejected plan
   still leaves its text in the transcript; working memory does not
   survive the turn.
4. Flush in the first write-capable turn, before other work, running
   the id snippet (or the helper) before each write.

Tell the two apart by the refusal's own words: a mode names itself and
refuses every write, a gatekeeper names a classifier or a rule and
refuses one call. Unconfirmed: whether every harness's plan mode refuses
an append to an existing file as well as a create; defer both either way,
so the flush turn is the only one that writes.

### A delegated setup step is not done until you have observed it

Every fallback above ends by handing something to the user: paste this
block, add this hook entry, authorize this edit. The instruction is where
the hand-off ends today, and that is one step short.

In the reported case the user was given the block, said they had pasted it,
and had not. The file's mtime was unchanged and `task-observer` appeared
nowhere outside the session's own transcript. It surfaced only because the
Session Start Protocol was being run by hand to verify the install —
otherwise the install would have looked complete to both parties, with no
activation layer in place. That is precisely the never-activated install
that step 4 structurally cannot detect.

**So pair every handoff with a check you run yourself**, in the same
session, and report the result:

- `grep` the config file for the skill name;
- compare the file's mtime against the moment you handed the block over;
- for a hook, confirm the harness lists it, not merely that the file exists.

"The user says they pasted it" is a claim about the world. An install can
check it, cheaply, and should before declaring itself configured.

**The principle.** When a setup step is delegated to a human because the
agent is not permitted to perform it, the delegation is not complete when
the instructions are handed over — it is complete when the agent has
independently observed the resulting state. An unverified handoff and a
silently skipped step produce the same artefact: a setup both parties
believe is done.

### Paths handed across a boundary are resolved from the far side

A path the agent has verified from inside its own execution context proves
nothing about the same string in the user's hands. Three boundaries, each
observed in one install. **Packaging:** inside a Store-packaged (MSIX)
desktop app on Windows, `%APPDATA%\<App>` is transparently redirected to
`%LOCALAPPDATA%\Packages\<App>_<id>\LocalCache\Roaming\<App>`, so every
check the agent runs — bash, PowerShell, Python — finds the config file
there, and a script the user starts from Explorer, outside the package,
finds nothing; processes started from the app's own terminal die with the
app, so "run it after quitting the app" cannot be done from inside either.
**Sync redirection:** `%USERPROFILE%\Documents` is not the Documents
folder Explorer opens once a cloud drive has redirected the known folder;
resolve user folders with the shell's known-folder lookup
(`[Environment]::GetFolderPath('MyDocuments')`), never by composing them
from the profile path. **Shell dialect:** a Git Bash drive path
(`/c/dev/<repo>`) passes every pre-flight in Git Bash and fails in the
PowerShell the user opens (`fatal: cannot change to '/c/dev/<repo>'`);
`"C:/dev/<repo>"` works in PowerShell, cmd and Git Bash alike. The same
shape at the plugin boundary: `python plugins/<p>/scripts/x.py` and "show
`docs/<file>.md` from this repo" are correct in the author's checkout and
absent for every consumer, because installation copies only the plugin's
own directory. So: on a packaged host keep the workspace and any hook
script outside `AppData`; resolve every path handed to the user — hook
script, config, workspace — once from the user's side of the boundary
before handing it over; and make that resolution a step bound to the
hand-off, not a principle consulted while authoring. The third instance
above happened in the same session that had written the principle down,
which is what a rule without a step looks like.

## Environment mappings

The procedures in this skill are written as capabilities. This table is
the only place product-specific names live; when a step says "present the
staged file" or "register the review", look up the current environment
here rather than guessing a tool name.

**Cowork execution mode — cloud vs local is a user setting.** Cowork can
run a session in two modes with materially different tool surfaces, and
the platform's default moved to cloud (so installs upgraded from earlier
versions may silently change mode — users experience that as the tool
losing abilities). The switch: Settings → Cowork → "Run new tasks in the
cloud" (plus a "Beta" button at session start). The tell: the
local-filesystem permission tool (`allow_cowork_file_delete`) present in
the tool surface ⇒ local session; absent ⇒ cloud. What differs:

| Capability | Local session | Cloud session |
|---|---|---|
| Scheduled-task editing | desktop scheduled-task tools | draft instructions only; the user applies them on the Scheduled tasks page |
| Deleting workspace files | permission gate (`allow_cowork_file_delete`) | no delete tool; rename-away only |
| Git on the mounted workspace | with the delete grant | never — use a sandbox clone |
| Locally-installed MCP servers | reachable | unreachable unless proxied via the desktop app |
| Working-file persistence | workspace folder persists | files not handed back are not kept |
| Runs while the computer is off | no | yes |

Steps that must edit scheduled tasks, delete workspace files (review
cleanup, keep-two pruning), or run git in the shared folder need a local
session — treat that as a one-line precondition on those steps, and when
reporting a mode-conditional limit, name the mode and the switch in the
same breath.

| Capability | Claude Cowork | Claude Code | Web chat / no filesystem |
|---|---|---|---|
| Persistent workspace | the shared folder | pinned absolute path (see activation block) | none — handoff-doc mode below |
| Live skill files | `.claude/skills/{skill}/` on a read-only mount (writes fail with EROFS) | `~/.claude/skills/{skill}/`, ordinary writable files — no guard | n/a |
| Present a staged file for install | the file-presentation tool (`present_files`) with its upload button | none — report the staged path and a change summary in chat | paste into the handoff doc |
| Scheduled review | the app's scheduled tasks (cloud-default: run remotely; legacy local mode: run on the user's machine, only while it is on — see the execution-mode note above) | cron / a harness `SessionStart` hook / an account-level scheduler that can reach the workspace — headless invocations carry the workspace grant (`--add-dir`) in the task definition | calendar reminder + manual trigger |
| Session-start hook | none | `SessionStart` hook (`hookSpecificOutput.additionalContext`) | none |
| Local-vs-cloud tell | `allow_cowork_file_delete` present ⇒ local session | n/a | n/a |

Grow the table when a new environment appears; do not scatter its tool
names through the procedure files.

**A scheduled-task prompt's first listed action is its first tool call.**
The Session Start Protocol wants the workspace probe (step 1) before any
skill invocation, and a scheduled prompt that opens with "invoke, in this
order: …" makes the first invocation the first call — observed: a scheduled
run loaded every skill it was told to, with the probe-first rule loaded and
correct, and ran the probe third. A rule that wants something before the
first listed action has to appear in that list, not in the text the list
loads: write the activation pointer in every scheduled prompt as "probe the
workspace folder (one `ls` of its absolute path), then invoke <skills>",
and keep the probe's procedure and failure handling in the skill.

**The second listed action leaves a started marker.** After the probe,
every scheduled review prompt writes the date and time to
`skill-observations/review-started.txt`, and the review's Step 7
overwrites it with `completed <date>`:

```bash
printf '%s\n' "$(date '+%F %H:%M')" > "[ABSOLUTE PATH]/skill-observations/review-started.txt"
```

A scheduler's "succeeded" says the job launched; the marker says how far
it got. At the next session start, a marker that does not read
`completed` is a run that died mid-way, and a scheduler last run later
than `last-review-date.txt` with the marker untouched is a run that fired
and never reached its second action — two different defects, and neither
is a review that happened. The marker is judged by its content, never by
its mtime: Step 7 writes it after the date file, so a completed run's
marker is always the newer of the two. Session Start step 3 reports either as "fired YYYY-MM-DD,
no review recorded" and treats the review as due.

**The access grant is part of the task definition, not of the path.** A
scheduled session runs in the sandbox the scheduler creates, and that
sandbox can deny a path that exists and is online (observed: a headless
run launched by the OS scheduler was confined to the user profile, the
pinned workspace lived on another drive, and every interface was denied
— file tools, both shells, and a junction inside the profile, because
the sandbox canonicalises the target — down to the skill's own reference
files; the run ended with the offline policy's one-line skip, a config
gap wearing the costume of a transient outage). Registering a scheduled
review therefore includes whatever allowed-directory configuration the
harness needs for the workspace root — for Claude Code headless,
`--add-dir "[ABSOLUTE PATH]"` on the invocation, or the equivalent
permissions rule — and the setup is not done until one firing has
reached the workspace **from inside the task's own execution context**:
an interactive test proves nothing about the sandbox the scheduler
creates, and a task the scheduler lists is not a run that succeeded. The
probe separates the two failures: a path that is not there is the
offline-workspace policy's case (`references/weekly-review.md`); a
permission or sandbox error on a path that exists is a configuration
gap no later firing heals, and its skip note names the missing grant.

**Managed skills directories (dotfile managers, sync tools).** Where the
skills directory is generated by chezmoi, GNU Stow, yadm, a symlinked
dotfiles repo or any sync tool, the live path is not the source of truth:
copying a staged update onto it succeeds, looks installed, and is
silently reverted at the next `apply` — "I installed it" and "it is still
in effect" become indistinguishable. Detect the manager at install (a
symlink into a dotfiles checkout, a `.chezmoi*` marker, the directory
listed in a Stow package) and record it in the activation config. Then
install into the manager's SOURCE, not the live path, and let the manager
apply it; or exclude the skills directory from management. "Always start
from the live file" (`references/skill-authoring.md`) still holds for
READING — the live file is what the loader loads — but the WRITE-BACK
path is the manager's source. The weekly review's staged-work
reconciliation (`diff -rq` staged vs live) is the check that catches a
reverted install: run it at the session after any install on a managed
directory. Where the entry is a symlink, resolve it before staging as
well (`skill-authoring.md`, editing rule 1): a link copied as a link
makes the staged path the live one.

## Git as an optional staging medium

Staging a skill update as a branch or commit the user merges gives the
same guarantee as the `skill-updates/` directory — nothing goes live
without a user action — plus diffs, history and rollback, and it suits a
multi-device setup that syncs skills through a private repository. It is
an option, not a change to the default: the review still writes the
staging manifest, still never edits the live install, and still presents
the change for a decision. Treat the version-control commands as a
mutation surface for the observation log (see
`references/observation-log.md`).

## Claude Code Projects

*Based on the platform's documentation, not yet field-tested — reports
welcome.* Re-verify each claim below against the current Claude Code
documentation before relying on it.

Claude Code Projects run work as parallel cloud "threads" under one
coordinating conversation. Per the documentation, a thread picks up
nothing from the Claude Code setup on the user's own machine: skills load
only from `.claude/skills/` in a repository added to the project, or from
skills enabled on the account; CLAUDE.md loads only from the project's
repositories; standing rules go in the project instructions, which every
new thread receives. Each thread works in its own clone on its own
branch, and the coordinator sees what threads report back, not every
step they take. That breaks three install assumptions at once:

- **Install.** A user-scope install is invisible to threads. Commit the
  skill — with its `references/` and `scripts/` — to a repository added
  to the project, or enable it as an account skill.
- **Activation.** A user-level activation line never loads. Put the
  activation block's instruction in the project instructions (preferred:
  it reaches every thread and the coordinator, and survives multi-repo
  projects where per-repo settings are not read) or in the repository's
  CLAUDE.md.
- **Log route.** No pinned shared path exists: the only writes that
  outlive a thread are a pushed branch or PR, a project Library file, or
  project memory. So either (a) threads carry every observation **in
  full** in their final report to the coordinator, and the coordinator
  or a scheduled project routine writes them to the real log; or (b)
  observations are committed to a dedicated observations repository via
  PR — the "Git as an optional staging medium" path above — and never
  left only on a working branch, because an unmerged branch is torn down
  with its thread. In a non-code project, a Library file is the carrier.
  Per-observation files still prevent write collisions between parallel
  threads; the problem here is survival, not concurrency.

The Session Start guard warns and re-anchors when the resolved workspace
is ephemeral; in a thread there is nothing stable to re-anchor on, so the
branch is **report-back mode** ("Anchoring the workspace" above): the
durable route is the channel the surface guarantees survives — the
worker's report to its coordinator, a merged commit — not a location the
worker can reach and hope outlives it.

The characteristic failure is silent: a never-activated install and
observations stranded on an unmerged branch both produce no error, so
issue reports will under-represent it. The external diagnostic: **no
observations arriving at the coordinator after several threads of real
work means the skill is not activated, or the log route is not wired.**
Check the project instructions for the activation line and the added
repository for the skill directory, then report what was found — that
report is the field test this section is waiting for.

## Sessions whose output channel is owned by a caller

A subagent, a non-interactive run, a tool-shaped invocation with a
declared result schema: the session has a filesystem and no reader.
Detect it from the session's own contract — a single required result
call, a ban on free-text answers — never from a flag. Every step that
needs a free-text reply to a person has no recipient there: the review
offer (Session Start step 3), the activation suggestion (step 4), the
end-of-session summary (Surfacing Protocol) and the per-task summary line
in the activation block. Skip them silently, and never count an
unanswerable offer as surfaced. Never run the review unprompted either:
"autonomous" in step 3 means a scheduled run whose prompt asks for the
review, not a worker whose caller asked for something else.

What happens to logging depends on who the caller is. Where the caller
is itself a session running this protocol, the activation block's
subagent rule applies: the worker writes nothing, and a finding worth
logging goes into its result, in whatever field the schema leaves for
notes, for the controller to write. Where the caller runs no protocol —
a script, a CI job, another tool — logging stays fully in force, because
the write is the only report there is: anything that would have been
surfaced becomes an observation file naming the condition that fired, so
the next interactive session inherits it; name the caller in
`session_context`, and log only what the caller cannot see. Handoff-doc
mode is the opposite case (a reader, nowhere to write); report-back mode
("Anchoring the workspace") is the case with neither a stable path nor a
reader. (Observed from both sides: a subagent with a fixed output schema
ran the protocol correctly and then had nowhere to put four reporting
steps; an orchestrator dispatching eight subagents in a day found each
had resolved the same conflict on its own, differently, in its
"decisions the brief did not cover" section.)

## First-run backfill

The skill is least valuable at the moment it is adopted: the log is empty,
a review correctly reports nothing to do, and the largest pile of
uncaptured insight — the project's own history — is never touched because
no procedure says to touch it. Session Start step 7 offers a one-off
mining pass over handover, architecture and decision docs, commit history
since the last release, test and verification scripts (which encode
hard-won discipline densely), and existing agent-instruction files, which
are largely a record of corrections the user already had to make. One
such pass over seven weeks of history produced twenty-three actionable
observations, eleven of them factual corrections to an existing skill.
Backfilled entries cite the durable artefact, and one batched write
satisfies the same-turn rule; the pass runs once, and the scheduled
review takes over afterwards.

**The same pass, scoped to one named session.** "Review today's session
retrospectively" and "the one where we did X" name a finished session,
not the project's history, and the session that hears the request holds
no transcript of it. That is not a live observation and not a first-run
backfill; it is the backfill pass with its sources bounded to one
timeframe. The sources are whatever durable per-session record the
project keeps — the kinds above are examples, not the list: commit
history and diffs within the session's window, a memory or notes system
the project already maintains across sessions (a directory of dated
files indexed apart from the instructions file is common), handover docs
written at its end. Each is cited in `session_context` exactly as a
backfilled entry cites CLAUDE.md — the artefact and the section, never a
session id, because there is no session to point at. Say which sources
were read and which were unavailable, so a later reader can tell a thin
session from a thin record. (Observed: a fresh install, the log empty,
the user asking for a retrospective of that day; the agent rebuilt the
day from `git log` and the project's notes directory and logged three
evidenced observations — the right move, improvised because nothing said
where to look.)

## Storage regimes

Persistence is one axis; the *price* of a write is another. Three
regimes:

1. **Local filesystem** — appends are free. Write the checkpoint markers
   exactly as SKILL.md specifies; they are the only evidence the check
   happened.
2. **Shared or hosted document store** (the workspace resolves to a
   hosted knowledge base or project, where each "file" is a document and
   every write is a mutation that invalidates cached context for every
   other session in that workspace). Keep the mandatory *check* at every
   checkpoint but suppress *empty* markers: enforce the check by hanging
   it on writes that were going to happen anyway — deliverable events and
   task completions — and write only when there is an observation to
   record. An enforcement mechanism has to be priced against its
   environment; a rule that makes writes mandatory-even-when-empty is
   only free where writes are free.
3. **No persistence** — handoff-doc mode, below.

## Bundle manifest

This skill consists of `SKILL.md`, the reference files it lists
(`weekly-review.md`, `skill-authoring.md`, `environments.md`,
`observation-log.md`, `signals.md`, `migration.md`,
`starter-principles.md`) and `scripts/migrate-log.py`,
`scripts/new-observation.sh` and `scripts/validate-skill-bundle.py`. If a referenced
file is missing, the install is
incomplete: proceed using the rules in `SKILL.md`, tell the user which
files are missing, and point them to the full bundle at the canonical
source (for the published version, the repository named in the attribution
block).

## Compaction behaviour

**A compaction is a session start.** So is a handoff-doc resume and a
re-invoked scheduled run. Each is a new context with old work in it, which
is exactly the condition the Session Start Protocol exists for, and on the
first turn after any of them the protocol runs again in full — storage
probe, frontmatter scan, review trigger, and the per-skill grep for every
skill the task in front of you needs. Where the CLAUDE.md structural
trigger reaches the resumed context it re-invokes the skill; do not rely on
it having done so — observed: a session compacted mid-task and the resumed
turn ran no probe, no scan and no per-skill grep, because nothing named the
compaction as a trigger.

**The write path has to survive the compaction; the skill body does
not.** Observed: after a compaction the session-start hook printed its
reminder, and before the skill was re-invoked a deliverable flush fired
— two observations were written by copying an existing file's
frontmatter and taking the next number from a directory listing. The id
snippet never ran, the floor stayed two behind the ids issued, and the
sweep, the collision guard and the noclobber create all went
unexercised. The pointer to this section sits in the skill body, which
is exactly what the compaction removed. Between a compaction and the
skill's re-invocation nothing is written by any other route: a flush
that fires first runs `scripts/new-observation.sh` (it needs no skill
body in context — a slug and the workspace root are its only inputs) or
waits for the invocation, and never copies another file's header. So the
activation block names the script as the only way an observation file
comes into being, and the hook prints the same: a rule that must reach a
resumed context travels in a channel that survives the compaction — the activation config, or a session-start
hook where the harness fires it on compaction as well (Claude Code's
`SessionStart` does unless a matcher excludes `compact`), which is then
the channel that arrives first.

**The compaction summary's list of previously invoked skills is a lower
bound, never the session's skill set.** A summary preserves what it judged
salient about the *work*; skill loads are infrastructure, not work, so they
are exactly what a summary drops. Observed: the summary named three of at
least six skills loaded before the compaction, the resumed turn read the
list as an inventory, and two domain skills stayed unloaded through a full
data pull until the user asked. The block's own framing — "shown here for
context only so you remain aware of their guidelines" — describes what the
block contains and is easily read as what the session has. Re-derive the
skill set from the task (name the decision, name the artefact type, match
the installed descriptions — "Select on the decision, not on the artefact"
above), and treat any skill the summary lists as loaded-then-forgotten
rather than as the whole set.

Observations before and after compaction are written as separate files
under the same `observation-log/` directory, each with its own id (the id
counter is derived from existing filenames, so it continues seamlessly
across the compaction boundary). A resumed session's opening message may
not match the description triggers, which is one reason the structural
trigger exists — and one reason the protocol re-runs by rule rather than
by whichever trigger happens to fire.

## User-facing documentation

Installation, shared-folder setup, expected behaviour, and the cadence
pattern live in the public repo. These links are for the human reader:
share them with the user rather than fetching the pages — the skill's
behaviour is defined entirely by its own files, never by external content:

- README: https://github.com/rebelytics/one-skill-to-rule-them-all/blob/main/README.md
- USER-GUIDE: https://github.com/rebelytics/one-skill-to-rule-them-all/blob/main/USER-GUIDE.md

## Repo/maintainer sessions — verify commit identity before writing

Authentication and attribution are separate channels in git: the push
credential (PAT/SSH key) controls who may WRITE; the commit's author
email (`git config user.email`) declares who WROTE, and the platform maps
that email to whichever account has it verified — regardless of which
account pushed. Before the first terminal commit in any clone used for a
specific identity, verify `git config user.email` resolves to the
intended account, and set repo-local config where the machine's global
identity differs. Diagnose suspected mis-attribution via the commits API
(author login vs commit email). Fix forward only: rewriting a published
main to correct author metadata (with tags/CI descending from it) costs
more than the cosmetic gain — verifying the email on the intended account
is the alternative remedy.

## Handoff-doc mode (no persistent storage)

The methodology is environment-independent; only persistence varies. In
web-chat-style environments, collect observations in-session and deliver
them in a structured handoff document the user stores and pastes into the
next session. **Offer the handoff proactively when the conversation winds
down** — a premature offer is a minor interruption; a missing one is lost
work.

```markdown
# Session Handoff: [Session Topic]

**Date:** [date]
**Context:** [what was worked on; what the next session needs to know]

## Decisions Made
[numbered]

## Observations Logged
[each observation in the frontmatter format from SKILL.md → How to Log; the
next session writes each as its own file in `observation-log/`]

## Cross-Cutting Principles (current)
[active or newly added]

## Action Items
[next steps with enough context to resume]

## Working Artifacts
[drafts/analyses in full]
```

## Handoff-doc analysis (when one arrives)

1. Log all explicitly stated observations first, unfiltered.
2. Then systematically read every section asking what skill gaps or
   candidates are *implied* but unstated — handoff docs carry signal beyond
   what was captured live.
3. Pay special attention to action items (each may imply a missing skill),
   open questions (ambiguity signals a decision-framework gap), the
   work-completed narrative (patterns may reveal meta-skills), and session
   notes.
4. Attribute derived observations as coming from handoff-doc analysis, not
   the original session.
