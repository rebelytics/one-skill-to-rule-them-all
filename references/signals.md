# Signals — what to watch for, in full

The core skill carries the short trigger list. This file is the full
catalogue with examples. Load it when you are unsure whether something is
worth logging, when a session is producing many candidate observations and
you want to sort them, and during a review when deciding what a skill
should lose as well as gain.
Also load it when a defect that is not the deliverable is consuming the
session, and before writing any "later" into a recommendation.

## Contents

- Signals for a NEW skill
- Signals for IMPROVING an existing skill
- Signals for SIMPLIFYING a skill
- The generalisability test
- An unresolved defect is an observation, at a bounded point
- Second violation — why a barrier, not a rewording
- Do NOT log
- Where the observation mindset stays on
- Deferral disguised as diligence
- Instructions handed across a boundary
- A command's risk is what it does, not what it was reached for

## Signals for a NEW skill

A reusable multi-step workflow; a methodology the user explains that no
existing skill captures; a recurring task type with similar structure; a
process with clear inputs, phases, outputs; the user describing a refined
process ("I always do it this way"); a structured approach emerging
naturally during work.

When one fires, the observation's `proposes_skill:` list names the
candidate by a working name. The observation may also list existing skills
under `skill:` if the same insight improves them.

## Signals for IMPROVING an existing skill

Anything from a task that used a skill and could make it better —
problems, positive signals, or neutral gaps. Examples:

- the agent violates a documented rule (the skill needs enforcement, not
  louder rules);
- a user correction reveals a missing rule or edge case;
- a better workflow emerges than the skill recommends;
- a technique works well enough to promote from incidental to recommended;
- an undocumented use case;
- feedback that generalises;
- a wrong assumption;
- new tooling obsoletes a step;
- corrections forming a pattern;
- a principle that applies to other skills too;
- a naming, framing or structural suggestion, even a conversational one.

## Signals for SIMPLIFYING a skill

A section never relevant across many sessions; a rule from a single
unvalidated observation; workflows users consistently shortcut; sections
loaded but never acted on; contradictory rules; "just in case" complexity
that never triggered; a rule the agent consistently fails to follow
(convert it to structural enforcement — a checklist, a verification step,
an unskippable tool call — or remove it). Treat these as a review
checklist; ask "what can we remove?" as deliberately as "what should we
add?"

## The generalisability test

Before recording a candidate improvement, ask: (1) would this correction
still make sense in another project? (2) would it apply to another task
using the same skill? (3) does it identify a missing rule, workflow step or
principle, rather than merely fix this task? (4) is there evidence the
issue is likely to recur? If the answers are mostly no, treat it as
task-specific context rather than an observation. A workaround that only
applies to one repository, a preference specific to one user, a decision
forced by a temporary constraint — these look like skill improvements
while the task is happening and are not. Instead of "the user preferred
modules in a single repository", log "the skill lacks guidance for
deciding when shared modules should be centralised". Knowing when *not*
to learn is as important as detecting signals: over-learning from isolated
examples is how a skill drifts into over-specific complexity.

## An unresolved defect is an observation, at a bounded point

**An unresolved defect is an observation, at a bounded point.** When a
defect that is not itself the deliverable is consuming the session — one
more hypothesis, one more root-cause probe — there is a point at which the
right output is a precise, evidenced problem report, logged as an
observation (or as an issue where the defect belongs to someone else's
code) and the deliverables resumed. Set that point before the second
hypothesis, not after the fifth: a report that names the symptom, what was
ruled out and the cheapest next test is a legitimate deliverable, and it
is what the next session or the upstream maintainer needs; the fix found
in a file the project's own rules protect from unapproved edits was never
going to ship from this session anyway. This skill does not carry
debugging methodology — only the observation-capture rule at the boundary.

## Second violation — why a barrier, not a rewording

The core carries the rule: from a rule's second failure onward, the proposed
improvement is a structural barrier, not better wording. This is why, and
what counts as a barrier.

The observed case: one documented rule broken three times in three separate
sessions. The rule lived in a project instruction file re-read at the start
of every session, so it was never "unloaded" — it was in context each time
it broke. Each occurrence was handled correctly by the text as it then
stood, and the first two produced only new wording:

| Occurrence | What was logged | What changed |
|---|---|---|
| 1st | rule broken, add a post-write check | wording |
| 2nd | rule broken *again*, same rule | wording, more emphatic |
| 3rd | "this needs a barrier, not a rule" | a pre-tool hook that refuses the call |

Only the third changed the outcome. The first two were not mistakes in
diligence — they were the natural output of a loop whose only available
lever is text.

**Why text loses.** A rule in context is re-interpreted on every run and
competes with everything else pulling at the same moment; a barrier at the
tool boundary does not compete, it refuses. Emphasis does not change that
asymmetry — an emphatic rule is still a rule, and the third rewrite reads as
diligence while changing nothing measurable.

**What counts as a barrier**, roughly in order of preference: a hook or
permission rule that refuses the call; a lint or gate check that fails the
artefact; a default or path layout that makes the wrong action unavailable;
a script that performs the step so it cannot be performed differently. What
does not count: a bolder warning, the same rule moved somewhere more
prominent, a checklist item, or a promise to be careful.

**A barrier counts once it is armed, not once it is written** — and a
change to an existing one, including a new branch added behind an entry
point that is already registered, is a new barrier for this purpose.
Arm it the way `observation-log.md` arms any enforcement trigger ("Two
gaps the checkpoint pairing still leaves — and the rule behind both"): the
real command it must refuse, and a legitimate one from the real tool
record, both run through it. Passing synthetic payloads are evidence about
the author's model of the input, not about the input, and the proof of the
other triggers in the same file says nothing about the added one. For a
barrier on shell commands, this skill's own snippets are legitimate
commands it will meet early — the id derivation is a compound script with
command substitution, the session-start scan a bundled script's
invocation — so include them.

**Where this matters most** is the class where the absence of an error is
not evidence of success — silent corruption, a command that exits 0 having
done the wrong thing, a check that cannot come out negative. There, a
missed rule produces no signal at all, so the loop that would eventually
catch a wording failure never starts.

## Do NOT log

One-off corrections that don't generalise; preferences already captured in
a skill; tool bugs unrelated to methodology; observations that would need
proprietary client information to be useful in an open-source skill
(unless an internal skill is the right home).

## Where the observation mindset stays on

Active for the entire task session: execution, post-task feedback and
review discussion, meta-discussion about skills or methodology, and
reflective or strategy conversations about how work should be done. The
observation mindset does not deactivate when the conversation shifts from
doing the work to discussing it — user feedback in review phases is often
the highest-signal input. Inactive only for casual conversation and quick
factual questions with no tools or deliverables involved.

## Deferral disguised as diligence

**Deferral wears a second disguise: not a promise, but an argument.** "Let's
wait until this has seen a few days of real use", "we should gather more data
first" — this reads as diligence, which is exactly why it goes unchallenged,
including by the person saying it. It is not an announcement, so a rule about
executing rather than announcing does not catch it. So before writing *any*
"later" into a recommendation, name two things: **which specific observation
would change the decision, and when it could realistically arrive.** If you
cannot name one, the evidence is either already conclusive (act now) or waiting
adds nothing (act now). A criterion you *can* name must also be able to occur:
ask who or what would have to act for it to fire, and whether that party has a
reason to do exactly the opposite — a deferral whose criterion cannot occur is
indistinguishable from a silent drop, only more expensive, and it looks better
than a vague one because it is precisely phrased. Then ask what the delay
costs — if a known-defective
state stays live meanwhile, the burden of proof is on deferring, not on acting.
A deferral is a decision and needs the same justification as acting; "more
evidence would be better" is not one, because the question is whether more
evidence could change the OUTCOME.

## Instructions handed across a boundary

A command block, a procedure or a checklist handed to a human is executed
in an environment the author has not tested: the author's shell, flags and
assumptions do not travel with the text. Anything optional in that text — a
trailing comment, a line break between two steps that only make sense
together, an implied ordering — is a place where the receiving environment
gets to decide, and it decides differently from the author at least once.
(Observed: a `# comment` trailing a command in a paste-able block was passed
to the tool as arguments by an interactive shell that has comments off by
default; the step silently failed and the next line acted on a state that
had never arrived.) So: explanation goes in the prose around a block, never
on a command line; steps whose order matters are chained so a failure stops
the sequence; and the check that settles whether the step worked tests the
PROPERTY the step exists for, not the command's exit. A handover whose
failure was detected by the recipient reading output is an observation, and
its second occurrence is a barrier (above), not a rewording.
A path is the commonest such instruction: one that resolves inside the
agent's execution context can point at nothing from the user's shell,
packaging or synced folders (`environments.md`, "Paths handed across a
boundary are resolved from the far side").

## A command's risk is what it does, not what it was reached for

Classify a command by its EFFECT before running it — does it write, and
where? — never by the intent it was reached for. A verb chosen for its read
half performs its write half regardless, in whatever repository, branch,
index or account it is pointed at, and the blast radius is set by the
target, not by the intent. (Observed: a version-control "checkout <ref> --
<path>" run to copy files OUT of a branch wrote that branch's whole tree
into the current branch's index; the next routine commit-and-push
published untested content on a public default branch, and every content
gate passed because none of them looks at what is staged in a different
repository.) The tell is a convenience shortcut taken in a location the
process reserves for something else — a read-only clone, a production
branch, a shared log — "just this once". Log it when caught; the fix is a
rule stated as a property of the LOCATION ("this repository is read-and-push
only"), because a rule stated as a property of the task does not feel like
it covers the task that was not the task.
