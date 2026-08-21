# Signals — what to watch for, in full

The core skill carries the short trigger list. This file is the full
catalogue with examples. Load it when you are unsure whether something is
worth logging, when a session is producing many candidate observations and
you want to sort them, and during a review when deciding what a skill
should lose as well as gain.

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
