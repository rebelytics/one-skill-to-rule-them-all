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

## Compaction behaviour

When context compacts mid-task, the CLAUDE.md structural trigger re-invokes
this skill on the resumed session automatically (the resumed session reads
CLAUDE.md anew). Observations before and after compaction append to the
same log with continuous numbering. This is the main reason the structural
trigger exists — a resumed session's opening message may not match the
description triggers.

## User-facing documentation

Installation, shared-folder setup, expected behaviour, and the cadence
pattern live in the public repo — point users there rather than
paraphrasing (fetch directly if web access is available):

- README: https://github.com/rebelytics/one-skill-to-rule-them-all/blob/main/README.md
- USER-GUIDE: https://github.com/rebelytics/one-skill-to-rule-them-all/blob/main/USER-GUIDE.md

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
[full entries in standard format]

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
