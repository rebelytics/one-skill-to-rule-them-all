# Environments, Activation Setup, and Handoff-Doc Mode

Load this for setup questions, compaction/resume behaviour, or when running
in an environment without filesystem access.

## Recommended activation setup

Description-level matching alone can miss invocation when the agent is
focused on the task, so pair the skill with a configuration-level
instruction (CLAUDE.md, project instructions, or equivalent):

```
At the start of any task-oriented session — any interaction where you will
use tools and produce deliverables — invoke the task-observer skill before
beginning work. This ensures skill improvement opportunities are captured
throughout the session.

When loading any skill, check the observation log for OPEN observations
tagged to that skill. Apply their insights to the current work, even if
the skill file hasn't been updated yet. This enables immediate application
of observations before they're permanently integrated during the weekly
review.
```

**Config detection (once per session):** with filesystem access, check the
workspace root's CLAUDE.md (or equivalent) for a task-observer activation
instruction — suggest adding it if absent, creating the file if none
exists. Without filesystem access, check the system prompt / project
instructions and suggest the user add the instruction there. Keep the
suggestion to a sentence or two.

**Anti-pattern:** don't chain activation through another skill — load
task-observer and related skills independently from configuration; a broken
chain silences all observation activity.

**If CLAUDE.md (or the equivalent config) is governance-protected:** some
setups guard shared config files with hooks or file-protection rules that
deny agent edits. If an edit to the config is denied, never retry the same
edit blindly and never attempt to bypass the guard — a denial is the
governance system working as intended, and a silent skip is just as bad
(the user believes activation is set up when only description-level
matching is active). Surface the denial to the user and offer these
fallbacks: (a) ask the user to paste the activation block into the file
themselves; (b) if the user's environment provides its own
temporary-authorization mechanism (a marker file, an environment variable,
or similar), ask the user to authorize the edit through that mechanism and
revoke it afterwards; (c) where the platform supports unguarded
project-level instruction files, add the activation instruction there
instead. Never assume unrestricted edit access to shared or
governance-tracked config — many setups gate exactly those files.

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
