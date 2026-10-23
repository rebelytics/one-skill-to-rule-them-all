# The session-start scan — the scan, its guards and the checkpoint pairing

Load triggers: writing or changing any instrument that reads the log; the per-skill check feels redundant after the session-start scan; the scan's guard fires or the scan is being adapted; moving the scan's print; why the checkpoints are writes; adding or changing an enforcement trigger

The core skill carries the scan's invocation (Session Start step 2) and
the checkpoint rules (How to Log). This file holds the reasoning behind
the scan's form, the guard every instrument over the log carries, what a
refusal means, and why the checkpoints are writes. The log's layout, the
id snippet and archival are in `observation-log.md`.

## Contents

- Scanning cheaply
  - Why the session-start scan does not satisfy the per-skill check
  - An empty scan over a non-empty log is a broken command
  - Every instrument gets the same guard
  - A refused print is not an empty log
  - A refused snippet is a degraded path, never a skipped step
- Why the checkpoints are writes, not questions
  - The scan ends in a write, not only a print
  - Two gaps the checkpoint pairing still leaves — and the rule behind both

## Scanning cheaply

Read only the frontmatter — the header block between the first two `---`
lines — never the bodies. This is what keeps the session-start scan and
the review's work-queue pass cheap once hundreds of observations exist.
The scan is `scripts/session-start-scan.sh`, the one copy: SKILL.md's
Session Start Protocol (step 2) runs it, and a reader reviews it there.
The notes below explain its parts.

**Why the line carries a time and a source, not just a date.** The
workspace is shared across every project that observes the same globally
installed skill (the anchoring rule), so `checkpoints.log` is a
multi-project, multi-session file by design, and the trace exists to show
that *this* session ran the protocol rather than loading the skill and
skipping it. Two same-day lines with identical text prove that one session
did, not which: the time disambiguates the session, the bracketed source
(the working directory's last segment, or any equally cheap per-project
token the harness exposes) the project.

The final append is the session-start run's own trace (see "The scan ends
in a write, not only a print"); a review's work-queue pass over the same
frontmatter can drop it. The content print is one `awk` over `*.md`
inside `( cd "$d" && … )`, never `for f in $(find …)` or `$(ls … | xargs
…)` — both word-split a spaced path (`observation-log.md`, "Snippets take a
spaced path"), while a glob in the directory hands `awk` bare names that nothing
splits; one process for the whole set, not one per file.

**Guard the read, not just the write.** A query that returns nothing is
reporting on two possibilities at once — the data is absent, or the
question never got asked — and only one of them is a finding. Guard every
retrieval whose purpose is to prevent duplicate work with an independent
existence check, because that failure is silent, self-confirming, and
costs exactly the work the retrieval existed to avoid: a scan that
produced no output has been read as "no relevant observations" while the
log held dozens, and the same finding was then rediscovered and presented
as new. Two properties make the check independent rather than decorative:
the file count comes from a literal path, not from the variable the parse
loop uses, and the assertion compares two numbers derived by different
means. Empty output has to earn the status of evidence.

Three properties of the scan's form are load-bearing, and each was
learned from a report. The guard's `parsed` count is derived by its own
command, never by a counter incremented inside the printing loop: a
counter riding the output stream lives in a subshell the moment the loop
is piped, and the guard then fires "0 headers parsed" under a screen of
correctly printed headers. Files are enumerated with `find`, not a glob:
under zsh's default `nomatch` an unmatched `"$d"/*.md` aborts the whole
`for` before its first iteration (a fresh install's empty log errored
where the answer was "no observations"). And the guard is an `if` block,
not a trailing `&&` chain, whose false last test exits 1 on every healthy
scan. When adapting a snippet, keep the guard out of the stream it
guards, enumerate without globs, and end on a statement whose status is 0
when nothing is wrong.

**Snippets spanning several tool calls must re-derive their own paths.**
Shell state does not carry between tool calls in most harnesses, so a
variable defined in an earlier call is empty in the next one. With a
glob, an empty path variable does not error — it expands to `/*.md` and
matches nothing, and a filter silently becomes a match-nothing filter;
`find ""` at least errors, which is one reason the snippets enumerate
with `find`. Every snippet here defines the paths it uses in the same
invocation that uses them; keep that property when adapting them.

**Under zsh, an unquoted `$var` is not split into words, and a word that
begins with `=` is expanded as a command path.** Both run correctly under
bash, so a snippet pre-flighted there ships them. A list carried in a
variable and looped over (`for f in $names`) runs its body once, over the
whole string, so a membership test built that way is always false or
always true, and no count guard sees it, because the defect is in the
names. A bare `echo ====` inside a compound command aborts it with `===
not found`. Never carry a list in a variable: write it to a file under
the workspace and read it back with `while IFS= read -r`, or compare two
such files with `comm`; quote any word that starts with `=`.

### Why the session-start scan does not satisfy the per-skill check

**This scan does not satisfy the per-skill check** (the grep run each time a
skill loads — `references/environments.md`, activation block). Different
scope (every skill vs one), different depth (frontmatter vs body),
different moment (session start vs the point the skill's rules are
applied). Both answer "have I looked at the log?", so running this one
discharges the felt obligation and makes the targeted one feel redundant
while leaving its function unperformed: awareness of a hundred titles is
not recall of the one relevant body twenty tool calls later.

### An empty scan over a non-empty log is a broken command

**An empty scan in a log known to be non-empty is a broken command until
proven otherwise**, never the finding "no relevant observations": halt if
files exist and nothing parsed, and keep the two counts independent and
every path re-derived inside the same tool call ("Guard the read, not
just the write"; "Snippets spanning several tool calls must re-derive
their own paths", above).

**A partial parse is lost entries, not a smaller log.** The guard halts
only when nothing parsed. A numbered file with no header — zero bytes,
or text with no opening `---` — is named on the scan's `LOST ENTRIES`
line instead: it is the trace of a write interrupted between the
`noclobber` create and the body (a denied write, a context cut, a session
ending), and it holds an id nobody may reuse. Report each in the start-up
lines. A header whose `title:` is empty is the helper's skeleton and goes
on the `UNFILLED` line instead — a write in progress (another session's,
or this one's a moment ago) or an abandoned one; it already holds its id,
so it is filled or declined the same way, never reused or deleted. A
header whose `id:` does not read as the filename prefix is named on its
own `NOTE:` line: fix the field after reading the body, never the name. If the observation can be reconstructed — this session wrote it,
or the slug and the session record say enough — write the body into
that file now; otherwise give it a minimal header (`id` from the prefix,
a `title` naming the slug, `status: declined`, `resolved:` today,
`resolution: "write interrupted; body lost"`, `siblings_checked:
"none — lost entry"`) so the archival sweep closes it. Never delete it:
the id stays issued, and the floor already sits above it.

### Every instrument gets the same guard

**Every instrument gets the same guard: an empty or zero result is a
claim about the instrument until an independent probe shows the
population is empty** (core, verbatim). `SCAN COMMAND BROKEN` and `ID
COMMAND BROKEN` are two instances of one rule, not two rules: a
frontmatter scan, an id derivation, a status grep, a count in a hook, a
query in a script all report on the same two possibilities as the scan
above, and only the second is a defect that a "0" conceals. So the guard
is a property every new instrument arrives with, never a line added after
its first silent failure — pair each number-or-list producing command
with a second count derived by a different means from a literal path, and
halt on the disagreement; a guard enumerated per snippet is unguarded for
the next snippet by construction.

**A guard that separates "empty" from "non-empty" cannot catch a
partial read, and partial reads are the common failure of text-shaped
tool output.** A listing that returns some of the directory passes every
zero-check and yields a plausible, wrong maximum. Assert the listing
against a second count of the same population taken by different means
— the id snippet counts the prefixes it listed against `find`'s count of
prefixed files — rather than against a sentinel. A monotonic invariant
already in the computation is a weaker check: a floor file is never above
the highest id *issued*, but an id can be issued without its file ever
being created (an older snippet wrote the floor before the create, and a
legacy monolithic archive holds ids no filename carries), so a computed
maximum below the floor is reported, and the id taken above the floor,
rather than halted on. And never write a
suspect reading back into the persistent source it came from; a guard
placed after that write has protected nothing, and the floor that exists
to stop the counter rewinding becomes the thing that rewinds it.

**Four states, one empty result.** An instrument that *ran and found
nothing*, one that *ran and broke*, one that *was never permitted to
run* and one that *has not finished* (below) all return the same thing,
and only the first is a fact about the world. The third has no natural
tell: nothing is broken, so no `BROKEN` guard fires, and the refusal is
easy to summarise away as "nothing found". Where a policy layer above the
shell can refuse a command — "A refused print is not an empty log" — the
guard covers the refusal too, reported in its own words.

**The guard is scoped by what a command IS, not by what it looks like.**
Both named instances above are log-reading snippets shipped inside this
skill, so the rule reads, in practice, as being about *those*. It is not,
and the gap is where it costs most: the one-line environment probes run
ad hoc mid-investigation, whose empty result goes straight into a runbook
or an observation body as a fact (`ls /usr/bin/*askpass* …` in an
interactive zsh prints `no matches found` — a glob error, not an answer —
and "no askpass helper present" gets written down). Apply it to **any
command whose empty or zero output is about to become a claim**: pair it
with a second probe by different means, or state "the probe returned
nothing" rather than "there is nothing".

**When the instrument is an external process, the independent probe
exercises the same code path.** For a literal path the second count is
another read of the same directory by other means. For a CLI invoked
from a non-interactive shell, a sibling subcommand (`--version` prints,
so the binary works) proves nothing about whether the subcommand under
test can report to a pipe at all: one that renders only through an
interactive terminal UI prints nothing and exits 0 when piped, for a
valid result, an invalid one and no result alike. So the probe is the
same subcommand with a known-bad argument. If that also returns empty
with a success exit, the path is TTY-gated, the instrument cannot answer
the question, and the correct output is to hand the command to an
interactive terminal rather than report "none found".

**A number read from a file another process is still writing is
provisional until that process is known to have exited.** This is the
fourth state, and a second count by different means reads the same
unfinished source and is just as empty, so two independent probes agree on
a false negative with full confidence. The partial file is not visibly
partial: `grep`, `awk` and `sed` flush per block to a file or pipe, so a
producer still running that has found nothing *yet* is byte-identical to
one that finished and found nothing, and a harness's interim read of a
backgrounded command is not a completeness signal. So for this class the
guard is a liveness-and-exit check — the producer's exit status, or
`pgrep` on its pattern — run before the interim output is interpreted at
all, never as a cross-check after a plausible-looking empty result.

**When the instrument is code written in this session, its input coverage
is unverified by construction — print what it ingested, not only what it
found.** A shipped snippet has at least been run against the population
it is meant to read; a throwaway parser has been run against whatever its
author's heuristic happened to match. So the guard's form for
session-written code is a **coverage assertion before any result**: print
the count of terms, rows or files the instrument read and assert it
against the canonical source's own count (the block's line count, the
directory's file count, the table's row count) — a mismatch fails the step
rather than degrading to a heuristic. "0 hits" is a claim about the
corpus only once the instrument is known to see the corpus (the
timelessness scan in `skill-authoring.md` records which patterns ran).

**A populated result gets the guard too, and is questioned less than a
zero because it looks like evidence.** Five shapes pass every
empty-result check above: a verdict identical for the whole population
(every expected file reported `MISSING`, because a path-conversion step
failed to an empty string on every iteration and turned the later
`[ -f ]` test into a constant); a small, plausible minority of findings
that are all false positives of the instrument itself; two instruments
over one population that disagree, hidden by a third "any left?" check
that validates neither; a complete-looking response whose termination
metadata says it was cut off; and an exit status read from the wrong
command. So: a verdict that is uniform across the population is a claim
about the instrument, probed like an empty one, with one element whose
answer is known by other means. Where a check transforms its input
(parse, path conversion, decode), print the transformed value before
judging it. Where two instruments measure one population, assert
`before - fixed = after` rather than checking only the final state.
Before reporting a list of findings, open one of them in its original
context. Read termination metadata (`finish_reason`, `done_reason`,
`truncated`, an exit code) next to the content it qualifies, because
looking complete is exactly what truncated output does. Capture an exit
status in the statement right after the command (`cmd; rc=$?`), never
inside a string that also runs a command substitution (`echo "$(basename
"$d") exit=$?"` reports the substitution's status). And for a new alarm
or error branch, count the real inputs that reach it today: zero means
the input is missing or the branch is unnecessary, and a green unit test
does not tell the two apart.

**A claim about how an external system behaves is an instrument reading,
and gets the same guard — whatever produced it.** Whether it comes from a
delegated agent's report, from a tool written this session, or from the
agent's own reasoning, it is unverified until something outside that
inference returns it. State the mechanism as a hypothesis, name the
observation that would settle it, and when the check costs minutes and
being wrong costs an irreversible action, run the check before answering
rather than after being challenged. The tell is **repetition**: a first
confident answer is a guess; repeating it under implicit doubt without
going to look is entrenchment, and being accidentally right is not being
reliable.

### A refused print is not an empty log

The session-start scan does two different jobs in one script, with
different appetites. Everything up to and including the `checkpoints.log`
write asks only for *facts about* the files: how many exist, how many have
a parseable header, how many — in the directory and in `archive/` — look
like invalid YAML. The trailing loop asks for the **contents** — it reads
instruction-shaped text out of files into the agent's context, which is
what builds awareness of the backlog — and that half is subject to
whatever governs context, not only to whatever governs the filesystem.
Under a permission mode with an automated content classifier it can be
refused outright (seen as `Instruction Poisoning`, on a command that had
run minutes earlier against an empty directory). The property is inherent
to the step, so it does not go away with rewording, and it gets **more**
likely as the log grows. This is why the counts and the trace run first.
Three consequences:

- **A refusal is not an empty log, and is never reported as one.** "The
  scan found nothing" is the exact failure the log is meant to prevent.
  Say that the print was refused, name the reason the classifier gave, and
  give the counts.
- **The counts-only form is the documented fallback**, not a degraded
  improvisation. It still satisfies the `SCAN COMMAND BROKEN` guard,
  because `n` and `parsed` both come from the half that ran; ordered the
  other way round, the guard's own inputs would sit downstream of the half
  that can be refused, and it would go quiet exactly when it is needed.
- **Awareness is genuinely reduced, and that is worth one line to the user.**
  The session proceeds without the backlog in context; it is not equivalent
  to a scan that ran.

### A refused snippet is a degraded path, never a skipped step

The refusal above is of the print alone; a harness that vets command
*shape* can refuse the whole block. A policy layer that classifies
commands rather than executing them declines a multi-line compound — a
`for` with an embedded `awk`, a command substitution wrapping a brace
group and a pipe — as unverifiable: it cannot be matched against an
allowlist, so it never runs. Two failure shapes follow, and neither is
visible afterwards: the agent rewrites the snippet into a subtler
compound, is refused again, and gives up; or it concludes the protocol
is unavailable here and proceeds, having activated nothing — the artefact
a protocol that found nothing leaves.

**The snippet is one implementation of the step; the STEP is the
requirement.** When the harness declines a command as unverifiable, do
not rewrite it into a cleverer compound — the refusal is about shape, and
a cleverer compound is the same shape. This ladder answers a refusal of a
command's *shape* only. A refusal that names the content or the target —
the print refusal above, a denied path — is a denial: report it in its
own words and do not fetch the same content another way. Degrade to flat,
single-purpose commands over the absolute path, one per call, and do the
combining yourself: list the directory and the archive, extract the
frontmatter fields with one `grep`, read `.id-floor`, and take the
maximum by hand where one is needed. The guard still applies — a
non-empty listing with no ids extracted is a broken read, not an empty
log — and the `checkpoints.log` line is still written. State in the
session which form ran, so a later reader can tell a degraded run from a
skipped one. For a write, the flat form already exists:
`scripts/new-observation.sh`, invoked by absolute path, is one command
with no shell operators, and the only write path wherever it can run.
The scan's flat form, `scripts/session-start-scan.sh` by absolute path,
is the ladder's first rung; the flat reads follow it, for when it is
refused too or cannot run. Every mandatory step that ships a command owns
a sentence saying what remains mandatory when the command is unavailable;
this is that sentence for the scan.

The ladder, one command per call, each with no shell operator a shape
classifier could decline:

```bash
bash "<skill directory>/scripts/session-start-scan.sh" "[ABSOLUTE PATH]"
find "[ABSOLUTE PATH]/skill-observations/observation-log" -maxdepth 1 -name '*.md' -exec grep -H -E '^(id|title|status|skill|proposes_skill|siblings_checked):' {} +
ls "[ABSOLUTE PATH]/skill-observations/observation-log"
ls "[ABSOLUTE PATH]/skill-observations/observation-log/archive"
cat "[ABSOLUTE PATH]/skill-observations/observation-log/archive/.id-floor"
```

From the flat reads, combine by hand: `files` is the number of `.md`
names in the first listing, `parsed` the number of distinct files the
`grep` printed an `id:` line for, and the id maximum the largest prefix
across both listings and the floor. Then write the `checkpoints.log` line, and say
"degraded form" in the session. If `-exec … +` is itself refused as a
compound, the fallback is
`grep -H -E '…' "[ABSOLUTE PATH]/skill-observations/observation-log"/*.md`
under bash — the one glob this tree tolerates, and only here, because
the command it replaces was refused. On an empty log that `grep` reports
"No such file" beside an empty `ls`, and on a log that has never issued
an id the `cat` reports the same: each pair is the expected answer, not
a broken read. The
`ls` in this ladder is a read for a human-combined count, not an input
to a snippet, so a rebound `ls` shows itself in the listing.

## Why the checkpoints are writes, not questions

The core requires a write to disk at every third completed todo item and
at every deliverable event (an observation file, or a one-line
acknowledgement in `checkpoints.log`) because a remembered "ask whether
anything is worth logging" is not enforcement: softer "check when
completing items" guidance has been shown, repeatedly, to get lost during
cognitively demanding analytical work — exactly when the most observations
accumulate — and the skill is then loaded with nothing written until the
user asks. A concrete write surfaces the mental check as a recorded
action, and riding it on a tool call already being made (presenting a
file, rendering a deck, completing a todo batch) removes the separate act
of memory.

**A finding met while resolving or discussing another observation gets
its own file in the same turn.** A `resolution:` field, a summary line or
a chat aside is never its carrier: nothing scans a resolution for new
findings, so "worth a look later" written there is a write to the log
directory that no reader of the log reaches — the rule a fan-out brief
imposes on delegates ("findings for the parent to log") applies to the
parent itself.

**A claimed write is not a write.** Every write-path rule (`observation-log.md`) binds on the write;
the summary that reports it needs its own rule, because a closing line
can name ids and titles in exactly the form a true one takes, discharge
the felt obligation, and leave nothing on disk. That is worse than
forgetting: a forgotten write leaves a gap the next checkpoint catches,
a narrated one reads as a checkpoint already passed, and an invented id
can later coincide with a real one and become indistinguishable from it
on audit. So the Surfacing
self-check binds on the narration: each id a summary names is one the
snippet or `scripts/new-observation.sh` printed in this session's tool
record, and the summary is rendered from a listing of `observation-log/`
taken in the same turn, never from memory of having written it.

### The scan ends in a write, not only a print

Loading this skill and executing this protocol are two acts, and only the
load leaves an artefact in the transcript, so a session that loaded and
then ran nothing looks from outside exactly like one that did both. The
appended `checkpoints.log` line is the protocol's own trace, for the same
reason the checkpoint rule is a write: a step whose value lies in happening
at a specific moment needs its own entry in the tool record. (Where the
workspace prices every write — the exception under "How to Log" — fold
this line into the session's first write instead.) Read the scan's output
whole. Its finding lines (NOTE, LOST ENTRIES, UNFILLED, GAP) and counts
come first and the entry headers last, with one `end of scan` line closing
it that repeats the counts and the number of finding lines; `tail`, `head`
or a `grep` hides exactly the lines that matter while the checkpoint line
still lands and the log looks compliant. A truncated scan is a skipped one.

### Two gaps the checkpoint pairing still leaves — and the rule behind both

1. *A session can contain no todo items.* The 3rd-completion checkpoint is
   bound to one tool (core). When
   a session runs without them, the deliverable flush is the only enforcement
   left and must be applied deliberately — and in a chat-only session, whose
   output never looks like a handover, it does not fire at all (observed: four
   observations written only after the user asked "any observations?"). The
   barrier for that shape is a harness hook at the turn boundary: in Claude
   Code the stop-hook recipe (`references/environments.md`, "A stop hook — the
   per-task backstop as a harness event"); where the harness offers plugin
   hooks on turn completion, a hook that notes a turn which used tools and
   wrote nothing to `observation-log/` or `checkpoints.log`.
2. *"Is this a major deliverable?" is a self-assessment, and self-assessment is
   what fails under load.* Prefer triggers unmistakable in the tool record over
   ones needing a judgement call. The flush point is a **property, not a
   command list**: any action by which a unit of work is declared complete to
   a human. A deploy, release, publish, or push qualifies — but so does a
   completion notification, a final report, or a status file set to "done".
   Each is a concrete tool call, as hard a trigger as a completed todo, and it
   reliably marks the end of a unit of work where insights have accumulated.
   A command list cannot be the definition: it inherits the shape of the
   sessions it was derived from and is silently inert in any session that
   declares completion through other tools — no deploy and no version control
   does not mean no completions.

The rule behind both: an enforcement trigger must hang on an event objectively
visible in the tool record, never on the agent noticing that a moment qualifies. Visibility is
necessary, not sufficient: a trigger's pattern is a claim about the future tool
record, so before it counts as armed, run the literal event string the project
actually produces through it as a positive control, and one known non-event
from the real tool record as a negative control — never invented examples,
which sample the author's model of the input, the same model that produced
the gap. Record both results next to the trigger.
And a counter bound to a single tool is silently inert in every session that does
not use it — such triggers always need a second, independent path. Nor may a
trigger pre-empt a delivery decision a later layer already owns ("the recipient
is right there, no need to send"): fire the action and let the owning layer
suppress it — a suppressed send leaves a trace in the tool record, an unsent one
leaves nothing.
