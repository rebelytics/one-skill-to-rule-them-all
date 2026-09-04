# Environments, Activation Setup, and Handoff-Doc Mode

Load this for setup questions, compaction/resume behaviour, or when running
in an environment without filesystem access.

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
   probe-then-request trigger — "before any other tool call, `ls` the
   workspace path; if it fails, call the folder-picker tool; never state
   whether the folder is connected without that probe" — because a config
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

### The activation block

```
Before the first tool call of any session — and before writing or
proposing a plan, not merely before executing one — invoke the
task-observer skill AND execute its Session Start Protocol (storage
check, frontmatter scan, review trigger). Loading the skill and running
the protocol are separate steps; a session that loads the file and stops
has activated nothing. Any turn that will involve a tool call counts; do
not classify the session as "too simple" from its opening message.

After completing each task, check the observation records written this
session and report a one-line summary (ids and titles, or "none logged
and why"). This is the activation backstop: it forces a look at the log,
so a session that silently skipped the protocol is discovered at the
first task boundary instead of never.

Loading a skill is not complete until you have queried the observation
log for OPEN observations naming it and read their bodies:
  grep -l "skill:.*<skill-name>" \
    [ABSOLUTE PATH]/skill-observations/observation-log/*.md
Apply their insights to the current work, even if the skill file hasn't
been updated yet. Run this at every skill load, however many skills load
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
```

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
scope once, at install, and pin it.

**Before creating a log, search for one.** Check the plausible anchor
candidates — the pinned path, the project identity root, the
environment-managed persistence directory, the shared folder, the other
agent's equivalent — for an existing `skill-observations/` workspace. If
one exists, adopt it, or consolidate deliberately with the user. A fresh
empty log beside a populated one is a silent fork: both grow
independently, ids collide, and each session sees only half the history.
When consolidating, leave a pointer file at the abandoned location so
sessions anchored there get redirected instead of re-creating the fork.

**Config detection (once per session):** with filesystem access, check the
workspace root's CLAUDE.md (or equivalent) for a task-observer activation
instruction — suggest adding it if absent, creating the file if none
exists. Without filesystem access, check the system prompt / project
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

**Anti-pattern:** don't chain activation through another skill — load
task-observer and related skills independently from configuration; a broken
chain silences all observation activity.

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
msg="Invoke the task-observer skill before the first tool call."
if [ "$open" -gt 0 ]; then
  msg="$msg $open open observations; last review: $last."
  case "$last" in never) msg="$msg Offer the review." ;; esac
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
| Scheduled review | the app's scheduled tasks (cloud-default: run remotely; legacy local mode: run on the user's machine, only while it is on — see the execution-mode note above) | cron / a harness `SessionStart` hook / an account-level scheduler that can reach the workspace | calendar reminder + manual trigger |
| Session-start hook | none | `SessionStart` hook (`hookSpecificOutput.additionalContext`) | none |
| Local-vs-cloud tell | `allow_cowork_file_delete` present ⇒ local session | n/a | n/a |

Grow the table when a new environment appears; do not scatter its tool
names through the procedure files.

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
directory.

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
Backfilled entries cite the durable artefact; the pass runs once.

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
`starter-principles.md`) and `scripts/migrate-log.py`. If a referenced
file is missing, the install is
incomplete: proceed using the rules in `SKILL.md`, tell the user which
files are missing, and point them to the full bundle at the canonical
source (for the published version, the repository named in the attribution
block).

## Compaction behaviour

When context compacts mid-task, the CLAUDE.md structural trigger re-invokes
this skill on the resumed session automatically (the resumed session reads
CLAUDE.md anew). Observations before and after compaction are written as
separate files under the same `observation-log/` directory, each with its own
id (the id counter is derived from existing filenames, so it continues
seamlessly across the compaction boundary). This is the main reason the
structural trigger exists — a resumed session's opening message may not
match the description triggers.

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
