# The observation log — storage layout, scripts and rationale

The core skill carries the per-invocation rules: where the log is, how to
name and number a file, the frontmatter format, and the archival rule.
This file holds the layout in full, the helper snippets, and the reasoning
behind the rules. Load it when setting up the directory for the first
time, when archiving, when something about ids or frontmatter looks wrong,
and before changing how any other tool or skill reads the log.
Also load it, as the core skill's pointers direct, before resolving,
dismissing or citing an observation, when setting `parked` or `reference:`,
before adding or changing an enforcement trigger or writing a new
instrument over the log, and whenever a scan, sweep or id probe comes back
empty.

## Contents

- Layout
  - Workspace creation
- Frontmatter fields
  - Unquoted `: ` in a prose value — how far it drifts before anyone notices
  - A park condition names the result, never your own vehicle
  - Context preservation — the `reference:` field
- Scanning cheaply
  - Why the session-start scan does not satisfy the per-skill check
  - An empty scan over a non-empty log is a broken command
  - Every instrument gets the same guard
- Skill families and the sibling check
- Assigning an id
  - Shell portability of the id snippet — why the case patterns are parenthesised
  - The guard line, the sweep's count and the noclobber create
  - Run the snippet immediately before every write
  - Resolve each id at its own write time
  - A structural probe that comes back empty is a stop signal
  - Why this is the entire concurrency story
- Read the full body before resolving, dismissing, fixing or citing
- Editing an existing observation
- The `parked` status — decided, not pending
- Partially actioning a multi-skill observation — the carrier pattern
- When the workspace is under version control
- Archival
- Referencing observations
- Why the checkpoints are writes, not questions
  - The scan ends in a write, not only a print
  - Two gaps the checkpoint pairing still leaves — and the rule behind both

## Layout

```text
skill-observations/
  observation-log/       # the log IS this directory: one file per observation
    0001-short-slug.md
    0002-short-slug.md
    archive/             # resolved observations, moved here after the grace period
      .id-floor          # highest id ever issued; the counter never drops below it
      log-YYYY-MM-DD.md  # legacy monolithic archives from pre-3.0 installs, if any
  cross-cutting-principles.md
  skill-families.md      # declared families: members, shared vs member-specific,
                         #   coherence model (created when the first family is named)
  last-review-date.txt
  checkpoints.log        # append-only acknowledgement markers (optional)
```

Each file in `observation-log/` follows the frontmatter format in the core
skill (How to Log). There is no central index to keep in sync: the
directory listing is the index, and the frontmatter is the metadata.
"The observation log", wherever this skill or any other skill says it,
means this directory.

### Workspace creation

One idempotent command, then an assertion. Session Start step 1 points
here: run this, do not work down the tree above by hand.

```bash
d="[ABSOLUTE PATH]/skill-observations"   # the pinned path, quoted: it may contain a space; bash, not sh
mkdir -p "$d/observation-log/archive"
# the literal `never`, never a date — a date means a review actually ran
[ -e "$d/last-review-date.txt" ] || printf 'never\n' > "$d/last-review-date.txt"
[ -e "$d/cross-cutting-principles.md" ] || printf '# Cross-Cutting Principles\n\n## Active Principles\n' > "$d/cross-cutting-principles.md"
for f in observation-log observation-log/archive last-review-date.txt cross-cutting-principles.md; do
  [ -e "$d/$f" ] || { echo "WORKSPACE SETUP INCOMPLETE: $f"; exit 1; }
done
```

`mkdir -p` creates the parent, so `observation-log/` needs no separate line;
both `[ -e ]` guards make the command safe to re-run on an existing
workspace, which is what lets step 1 run it unconditionally rather than
deciding first whether setup is needed.

**Why a command and not the prose list it replaces.** Observed on a fresh
user-scope install: a session created `skill-observations/` and
`observation-log/` and nothing else. The next session could not tell —
step 1's probe is an `ls` of the pinned path, the path resolved,
`observation-log/` was there, and nothing re-checks the siblings. The
workspace looked set up from outside for as long as nobody looked closer.

The assertion loop is the half that matters, because the four artefacts
fail differently and only one of them complains:

| Missing | How it surfaces |
|---|---|
| `observation-log/` | immediately, at the first scan |
| `archive/` | at the first write, when the id snippet reads `.id-floor` or `mv`s into it |
| `cross-cutting-principles.md` | at the first review |
| `last-review-date.txt` | **never** — step 3 silently skips the review trigger |

The last row is the reason the guard is worth its lines: the failure mode
of the one step whose whole job is to fire periodically is that it never
fires and nothing says so.

This is the same shape the skill already solved for archival, and solved
the same way — a duty written as prose next to another action inherits none
of that action's enforcement, so the archival sweep was folded *into* the
id-derivation snippet ("If a step must always accompany a tool call, put it
inside the same command", Archival on Write). Step 1's creation is the
remaining place where that reasoning had not been applied.

## Frontmatter fields

| Field | Meaning |
|---|---|
| `id` | Integer; matches the `NNNN-` filename prefix. Never reused. |
| `title` | Short descriptive title. |
| `status` | `open`, `actioned`, `declined`, `superseded` (a later observation found this one's mitigation does not work; `resolution` names it) or `parked`. A missing status is read as `open`, never as nonexistent. |
| `parked` (status value) | Decided, but blocked on an external precondition: the entry is sound and no longer awaiting a judgement, so reviews drop it from the work queue and never re-escalate it. It is not resolved, so it does not archive — see Archival below. It stays in `observation-log/` until its `parked_until:` condition is met (set it back to `open`) or it is genuinely resolved. Recording a park as free text while leaving `status: open` does not work: nothing classifies on prose, so the entry stays in the queue and is re-raised at every review. |
| `parked_until` | **Mandatory whenever status is `parked`**, empty otherwise. One line naming the condition that unparks the entry ("the X scheduled task is re-enabled"), phrased so a later review can answer yes or no without reopening the original decision. |
| `type` | `open-source` or `internal` (see Taxonomy in the core skill). |
| `skill` | **Always a list**, even with one entry, so no consumer ever branches on string-vs-list. First entry is primary. May be empty. |
| `proposes_skill` | List of new-skill candidates by working name. Independent of `skill`; either may be empty, both may be filled. |
| `target_file` | List of paths, for observations whose right home is not a skill: an instructions file, a memory note, an agent brief, the register a routine reads. Name the file the fix will actually be written to, so a review can go there instead of remapping the entry onto the nearest skill. Measured on a first review of 27 legacy entries: 15 named a non-skill in `skill:` ("browser verification protocol", "documentation hygiene") and every one had to be resolved to a path by hand before the review could start. |
| `siblings_checked` | **Mandatory, never blank.** Records that the sibling check happened and what it concluded: the family name, the members evaluated, and the verdict (propagated / instance-specific). `none` only where the target belongs to no family. Missing or empty = logged without a sibling check, and reviews count it as such. |
| `area` | The part of the skill or workflow concerned. |
| `date` | Date logged, `YYYY-MM-DD`. |
| `session_context` | What was being worked on. |
| `resolved` | Resolution date; set only when status is `actioned` or `declined`. Archival is gated on it. |
| `resolution` | What was done, or why declined. |
| `reference` | Optional path to saved session-local evidence. |
| `skill_qualifiers` | Optional map: skill name → the section or part of that skill meant. |
| `migration_note` | Present only on files converted from a legacy log where the converter refused to guess; clear it once reviewed. |

### Unquoted `: ` in a prose value — how far it drifts before anyone notices

The core states the rule (quote every prose value). This is the measurement
behind it, because the failure is unusually quiet and the scale surprises
people.

An unquoted `: ` inside a free-text value is invalid YAML. The frontmatter
still *extracts* — a regex that slices between the two `---` lines is happy —
so the session-start scan reports the file as parsed and the log looks
healthy. What breaks is every consumer that actually **parses**: a review
reading `status`, a hook counting `skill:`, a validator checking the header.
Those throw on the file, and a thrown file is usually skipped rather than
reported.

Measured on one live log at last verification: **27 of 292 files
unreadable**, 25 of them in `resolution:` — which is the field most likely
to contain a colon, because a resolution naturally reads "Actioned:
principle #8 extended…". Every one of the 27 had been written by following
the template as it then stood, which carried the value unquoted. The
template taught the defect, and each author complied with it.

The scan's `suspect` count is the early warning: it reports headers whose
value contains an unquoted `: ` beside the file count, so a log drifting
into this state announces itself at session start rather than at the review
that trips over it. Re-verify by running a real YAML parse over the
frontmatter of every file, not by re-reading the template.

### A park condition names the result, never your own vehicle

`parked_until:` must name a condition that can occur — but there is a
second, sharper test that the first one passes right past.

"PR #N is merged or closed" waits on a path the other party need not take.
A maintainer folds the change into a commit of their own with a co-author
trailer, cherry-picks it, or rewrites it; the PR stays open or is closed as
overtaken, while **the result the entry was waiting for has fully
arrived**. The condition never fires. Observed twice in the same
repository, which suggests it is the normal case for a contribution to a
repository someone else maintains, not the exception.

So the test is not only *can this condition occur at all* but **can the
result arrive without the condition firing?** For anything depending on
another party's process the answer is yes, so phrase the condition on the
**text of the target artefact** — "rule X is present in `main`'s
SKILL.md" — which is answered by reading the target, whatever route the
change took to get there.

The same applies to any vehicle standing in for a result: a ticket
resolved, a build green, a message replied to. Park on what you actually
need to be true.

### Context preservation — the `reference:` field

**Context preservation:** if an observation depends on session-local data
(uploads, API output), save that context into the workspace first and set
`reference:` to its path — an observation whose evidence dies with the
session is incomplete. The pointer must survive the handoff too:
`reference:` — like any pointer that hands work to a later session — must
name a durable path, one that outlives the session and a reboot and that
a session other than this one can resolve. A session-scoped temp
directory fails both tests, and a role name ("the scratchpad", "my
notes") is not a path at all. Such a pointer cannot fail at write time,
only at read time, when its author is no longer there to repair it — a
pointer a fresh session cannot follow is not preservation.

## Scanning cheaply

Read only the frontmatter — the header block between the first two `---`
lines — never the bodies. This is what keeps the session-start scan and
the review's work-queue pass cheap once hundreds of observations exist.
The core skill's Session Start Protocol holds the authoritative copy of
this snippet; the copy below is reproduced for reading in context, and if
the two ever disagree, the core wins:

```bash
d="[ABSOLUTE PATH]/skill-observations/observation-log"   # the pinned workspace path — re-derive in EVERY call, never relative to the cwd; run under bash, not sh
n=$(find "[ABSOLUTE PATH]/skill-observations/observation-log" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')  # literal path: independent of $d
parsed=$(find "$d" -maxdepth 1 -name '*.md' -exec awk 'FNR==1 {if (/^---[[:space:]]*$/) print FILENAME; nextfile}' {} + | wc -l | tr -d ' ')
suspect=$(find "$d" -maxdepth 1 -name '*.md' -exec awk 'FNR==1 && /^---[[:space:]]*$/ {fm=1; next}
  fm && /^---[[:space:]]*$/ {fm=0; nextfile}
  fm && /^[a-z_]+: [^"\047[|>].*: / {print FILENAME; nextfile}' {} + | wc -l | tr -d ' ')   # values with an unquoted ": " — invalid YAML
find "$d" -maxdepth 1 -name '*.md' | LC_ALL=C sort | while IFS= read -r f; do  # quote + IFS=: never word-split a path containing a space
  awk 'NR==1 && /^---[[:space:]]*$/ {fm=1; next}
       fm && /^---[[:space:]]*$/ {exit}
       fm' "$f"
  printf -- '---\n'
done
if [ "$n" -gt 0 ] && [ "$parsed" -eq 0 ]; then
  echo "SCAN COMMAND BROKEN — $n files present, 0 headers parsed"; exit 1
fi
[ "$suspect" -gt 0 ] && echo "NOTE: $suspect of $n headers carry an unquoted ': ' in a value — quote those values (File format)"
printf 'files: %s  parsed: %s  suspect: %s\n' "$n" "$parsed" "$suspect"
printf '%s [%s] session-start scan: files=%s parsed=%s\n' "$(date '+%F %H:%M')" "${PWD##*/}" "$n" "$parsed" \
  >> "[ABSOLUTE PATH]/skill-observations/checkpoints.log"   # date+time+source: one line per session, not per day
```

**Why the line carries a time and a source, not just a date.** The
workspace is deliberately shared across every project that observes the
same globally installed skill — that is the anchoring rule — so
`checkpoints.log` is a multi-project, multi-session file by design. A line
carrying only `YYYY-MM-DD` cannot distinguish two sessions that ran the
same day, which is the common case and precisely the case the file exists
to adjudicate: the whole point of the trace is to show that *this* session
ran the protocol, as opposed to the skill having been loaded and the
protocol skipped. Two same-day lines with identical text prove that one
session did, not which. The time disambiguates the session; the bracketed
source (the working directory's last segment, or any equally cheap
per-project token the harness exposes) disambiguates the project.

The final append is the session-start run's own trace (see "The scan ends
in a write, not only a print"); a review's work-queue pass over the same
frontmatter can drop it. The enumeration is a `find | sort | while IFS=
read -r` loop rather than `for f in $(find …)`: the unquoted command
substitution word-splits any path containing a space, which is a live
hazard on every workspace whose folder name has one.

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

Three properties of the snippet's form are load-bearing, and each was
learned from a report. The guard's `parsed` count is derived by its own
command, never by a counter incremented inside the printing loop: a
counter that rides the output stream lives in a subshell the moment the
loop is piped (`done | grep …`), and the guard then fires "0 headers
parsed" directly under a screen of correctly printed headers. Files are
enumerated with `find`, not a glob: under zsh's default `nomatch` an
unmatched `"$d"/*.md` aborts the whole `for` before its first iteration,
so a fresh install's empty log produced an error where the answer was
"no observations", and the `[ -e "$f" ] || continue` line meant to catch
the literal glob was dead code there. And the guard is an `if` block, not
a trailing `&&` chain: a chain whose last test is false leaves the block
with exit status 1 on every healthy scan, so a harness that surfaces exit
codes reported failure at exactly the step whose job is to say whether
the log could be read. When adapting a snippet, keep the guard out of
the stream it guards, enumerate without globs, and end on a statement
whose status is 0 when nothing is wrong.

**Snippets spanning several tool calls must re-derive their own paths.**
Shell state does not carry between tool calls in most harnesses, so a
variable defined in an earlier call is empty in the next one. With a
glob, an empty path variable does not error — it expands to `/*.md` and
matches nothing, and a filter silently becomes a match-nothing filter;
`find ""` at least errors, which is one reason the snippets enumerate
with `find`. Every snippet here defines the paths it uses in the same
invocation that uses them; keep that property when adapting them.

### Why the session-start scan does not satisfy the per-skill check

**This scan does not satisfy the per-skill check** (the grep run each time a
skill loads — `references/environments.md`, activation block). Different
scope (every skill vs one), different depth (frontmatter vs body),
different moment (session start vs the point the skill's rules are
applied). Both answer "have I looked at the log?", so running this one
discharges the felt obligation and makes the targeted one feel redundant
while leaving its function unperformed — awareness of a hundred titles does
not survive as recall of the one relevant body twenty tool calls later.
Retrieval has to happen where the decision is made.

### An empty scan over a non-empty log is a broken command

**An empty scan in a log known to be non-empty is a broken command until
proven otherwise**, never the finding "no relevant observations". The
snippet's guard is what settles which of the two it is, and both halves of
its independence are load-bearing: the file count comes from a literal
path rather than from the variable the parse loop uses, and the assertion
compares two numbers derived by different means — halt if files exist and
nothing parsed. Keep that independence when adapting the snippet, and keep
every path re-derived inside the same tool call. The reasoning and the
reports each rule came from are in "Guard the read, not just the write"
and "Snippets spanning several tool calls must re-derive their own paths"
above.

### Every instrument gets the same guard

**Every instrument gets the same guard: an empty or zero result is a
claim about the instrument until an independent probe shows the
population is empty.** `SCAN COMMAND BROKEN` and `ID COMMAND BROKEN` are
two instances of one rule, not two rules — a frontmatter scan, an id
derivation, a status grep, a count in a hook, a query in a script all
report on the same two possibilities as the scan above, and only the
second of them is a defect that a "0" conceals.
So the guard is a property every new instrument arrives with, never a
line added after its first silent failure: pair each number-or-list
producing command with a second count derived by a different means from
a literal path, and halt on the disagreement. A guard enumerated per
snippet is unguarded for the next snippet by construction; a guard stated
as a property of instruments covers the one nobody has written yet.

**The guard is scoped by what a command IS, not by what it looks like.**
Both named instances above — `SCAN COMMAND BROKEN`, `ID COMMAND BROKEN` —
are log-reading snippets shipped inside this skill, so the rule reads, in
practice, as being about *those*. It is not, and the gap is precisely where
it costs most: the one-line environment probes run ad hoc mid-investigation,
whose empty result goes straight into a runbook or an observation body as a
fact.

Two observed shapes, both recorded as findings that were not there:

- `ls /usr/bin/*askpass* /usr/lib/ssh/*askpass* …` in an interactive zsh
  printed `no matches found` — a glob error, not an answer — and "no
  askpass helper present" was written down.
- A presence listing over a directory the session lacked permission to read
  returned nothing, and the absence was reported as the state of the system.

Neither command was a "log instrument", so neither attracted the guard.
Apply it to **any command whose empty or zero output is about to become a
claim**: pair it with a second probe by different means, or state the
result as "the probe returned nothing" rather than "there is nothing".

## Skill families and the sibling check

Where several skills implement one idea — the same methodology for
different tools, the same structure for different subjects, the same
companion pattern for different base skills — the shared part drifts by
default, because each member is maintained only in the sessions that use
it and nobody looks at the set. Measured in real libraries: a rule that is
pure epistemics, applicable to every member of a five-skill family,
present in one of five; a rule whose own text says it "applies to any
file-writing script, not specific to this one", present in one of four,
while two of the other three break the same way. Nobody removed anything;
some members simply grew and others did not.

**Why the check has to be a write-time step rather than a habit.** An
insight found while using one member usually applies to the rest, and
nothing in the ordinary workflow asks — so `skill:` collapses to the one
skill in front of you and the family diverges quietly. The divergence has
no symptom until someone reads two members side by side, which happens at
a drift audit, months later.

**The cheapest propagation signal is a phrase.** A rule that declares
itself generic *inside one artefact* — "this applies to any file-writing
script, not just X", "true of every companion in this family" — has
already told you it belongs to every sibling. Treat that phrasing as an
automatic multi-skill flag; it costs nothing to notice and it catches the
case the name-removal test is only a proxy for.

The `skill:` field is already a list, so multi-skill observations are
expressible. The mechanism exists; the *check* does not — and a list field
with no rule to populate it collapses to a single value. Four parts, in
increasing cost:

**1. Declare the families and the pattern groups —**
`skill-observations/skill-families.md`. The registry holds two kinds of
grouping, and conflating them is what makes it either block publication
or ship references nobody can use:

| Kind | Defined by | Members may cross-reference? | Shared rules live |
|---|---|---|---|
| **Family** | the same tool, or a core skill and its companions | yes — a user of one has reason to load the others | in the members (per the coherence model) |
| **Pattern group** | the same shape — one companion per tool, one dossier per subject — with no reason for a user of one to have another | **never** — a sibling paragraph naming the others is a defect, published or not | in cross-cutting principles |

Group skills by what a user of one would also need, not by what they
look alike. Propagation of insights and cross-referencing are different
relationships: a pattern group earns the sibling check at write time
(the "could this sentence survive removing the tool name?" test is
exactly what such a group is good for) and earns no cross-references at
all. A family earns both.

**A skill can belong to more than one grouping** — typically a per-tool
family and a core/companion family at once — and the registry records
each membership separately rather than forcing a single home. The
sibling check (part 2) runs against **every** family and every pattern
group the target belongs to, not just the first one it resolves to.

Each entry carries the members and the load-bearing second column:
**what is shared versus what is legitimately member-specific.** Without
that column every observation looks like it might apply everywhere and the
check generates noise instead of signal. Record the *coherence model* for
each FAMILY too, because it decides what "fixing drift" means (a pattern
group has no coherence model — there is no shared text to keep in sync):

| Coherence model | Meaning | Fixing drift means |
|---|---|---|
| `synced-duplicates` | each member is self-contained (e.g. published standalone) and shared sections are kept in sync | edit every member |
| `shared-core` | one skill holds the common material; the others load it as a companion | edit the core once, check the pointers |

```markdown
## [group name]
**Kind:** family | pattern group
**Members:** skill-a, skill-b, skill-c
**Coherence model:** synced-duplicates | shared-core   # families only
**Shared:** [the material every member should carry]
**Member-specific:** [what legitimately differs, and why]
```

Duplication is sometimes correct and absence is not always drift — that is
exactly what the shared/member-specific split records.

**2. Logging-time check** (SKILL.md, "How to Log"). Before writing an
observation, resolve the target against the registry — against every
family and every pattern group it appears in, since membership is
plural. For each sibling in each of them, either add it to `skill:` or
state in the body why it does not apply. Where the insight is shared
across a PATTERN group, the destination is usually a cross-cutting
principle rather than the same paragraph copied into each member.
**No registry yet, or the target is not in
it?** The check is still required: scan the installed skill names for a
shared prefix, suffix or subject (`*-extras` companions, per-tool
implementations of one method, per-subject dossiers), do the evaluation
against whatever set that yields, and propose the registry entry. Two
cheap tests decide the verdict:

- Could this sentence survive having the tool's, client's or subject's
  name removed? If yes it belongs to every sibling.
- Does the rule declare its own generality ("this applies more broadly",
  "not specific to X")? That phrasing is the cheapest possible propagation
  signal and needs a mechanism that notices it — treat it as an automatic
  multi-skill flag rather than a stylistic aside.

**3. Record the verdict** in `siblings_checked:`. The field exists because
the two states of a one-entry `skill:` list — siblings evaluated and
correctly excluded, versus siblings never considered — are byte-identical,
so nothing downstream can distinguish them: a review cannot flag
under-scoped entries and a drift audit cannot tell a decision from an
oversight. Recording the judgement does not make the judgement better; it
makes its *absence* visible, which is the only property that lets anything
enforce it. The instruction alone is demonstrably not enough — four
observations in one session were logged under-scoped by an author who had
written the propagation rule earlier in that same session. Because the
field is frontmatter, the cheap scan above can report "N observations
logged without a sibling check" without reading a single body. Where a
skill already relies on "the write is the enforcement", a new rule that
writes nothing is the odd one out and should be suspected on that basis.

**4. Propagation and drift audit at review time** — see
`weekly-review.md` (Steps 3 and 4). The first three parts only cover what
happens from now on; the mechanical audit is the only one that catches
drift predating the rule or introduced by a skill authored outside the
log. A registry can go stale; a grep cannot.

## Assigning an id

The id is the highest of three values, plus one: the highest numeric
filename prefix in `observation-log/`, the highest in
`observation-log/archive/`, and the number in
`observation-log/archive/.id-floor`. The floor file holds the highest id
ever issued, so the counter cannot restart from 1 when the active directory
is empty (every file archived) and nothing else remembers the range. Update
it whenever you issue an id above it. The archival sweep (see Archival
below) is folded into this same command: every id derivation first moves
stale resolved files to `archive/`, so archival happens as a side effect
of a step no write can skip.

The core skill's "How to Log" section holds the authoritative copy of this
snippet; the copy below is reproduced for reading in context, and if the
two ever disagree, the core wins:

```bash
d="[ABSOLUTE PATH]/skill-observations/observation-log"   # the pinned workspace path, never relative to the cwd; it may contain a space, so keep it quoted; bash, not sh
today=$(date +%F)          # archival rides inside this command (see below):
n_files=$(find "$d" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')
seen=$(find "$d" -maxdepth 1 -name '*.md' -print0 | { n=0   # -print0/-d '': never word-split a path containing a space — `read -d` is a bash extension, so this loop requires bash
  while IFS= read -r -d '' f; do   # stale resolved files move before the id is read
    n=$(( n + 1 ))
    hdr=$(awk 'NR==1 && /^---[[:space:]]*$/ {fm=1; next}
               fm && /^---[[:space:]]*$/ {exit} fm' "$f")
    case $hdr in   # patterns parenthesised: required inside $( ) on bash 3.2
      (*"status: actioned"*|*"status: declined"*|*"status: superseded"*) ;;
      (*) continue ;;
    esac
    r=$(printf '%s\n' "$hdr" | sed -n 's/^resolved:[[:space:]]*//p' | head -1)
    case $r in ([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) ;; (*) continue ;; esac
    [ "$r" != "$today" ] && \
      [ "$(printf '%s\n%s\n' "$r" "$today" | sort | head -1)" = "$r" ] && \
      mv "$f" "$d/archive/"
  done; printf %s "$n"; })
[ "$n_files" -gt 0 ] && [ "${seen:-0}" -eq 0 ] && { echo "ARCHIVAL SWEEP BROKEN — $n_files files present, 0 examined"; exit 1; }
hi=$( { ls "$d" "$d/archive" 2>/dev/null | grep -oE '^[0-9]+'; cat "$d/archive/.id-floor" 2>/dev/null; } \
     | sed 's/^0*\([0-9]\)/\1/' | sort -n | tail -1); : "${hi:=0}"
[ "$hi" -eq 0 ] && [ -n "$(find "$d" -maxdepth 1 -name '*.md')" ] && { echo "ID COMMAND BROKEN — log is non-empty but no ids extracted"; exit 1; }
next_id=$(( hi + 1 )); echo "$next_id" > "$d/archive/.id-floor"
f="$d/$(printf '%04d' "$next_id")-<slug>.md"      # the target path, built from the id just derived
[ -e "$f" ] && { echo "COLLISION — $f exists; re-derive the id"; exit 1; }
(set -C; : > "$f") || exit 1                        # noclobber: create, never truncate an existing file
```

The snippet leaves the derived number in `$next_id` and the target path in
`$f`; append `printf '%04d\n' "$next_id"` if you also want the filename
prefix echoed.

The `sed` strips the filename prefixes' zero-padding before the
arithmetic. It is load-bearing, not cosmetic: shell arithmetic reads a
leading-zero number as octal, so `$(( 0105 + 1 ))` yields 70 — a silently
wrong id — and a prefix containing an 8 or 9 (e.g. `0108`) is an invalid
octal constant and errors the whole derivation.

`ls`, `awk`, `sed -n`, `grep -oE`, `sort -n`, `mv` and `printf` are POSIX,
and the one non-POSIX construct is deliberate: `read -r -d ''` over
`find -print0` is a bash extension, taken because it is the only form that
cannot word-split a path containing a space — so run the snippet under
`bash`, not `sh`. It runs unchanged on macOS, Linux and Git Bash. The date
comparison relies on ISO dates sorting lexically, so it needs no `date`
arithmetic. A skill that hands the agent a
shell command owns that command's portability: lead with the portable
form, never offer it as a footnote the agent reaches for after the primary
has failed — and make any command that derives a number from a file fail
loudly on an empty result, because a command that fails to empty rather
than to error may never announce that it failed at all.

### Shell portability of the id snippet — why the case patterns are parenthesised

Both `case` statements in the snippet sit inside the command substitution
`seen=$( … )`, and both are written `(pattern)` rather than `pattern)`. The
leading parenthesis is not style.

Bash 3.2 — which is what `/bin/bash` still is on a stock macOS install — ends
a command substitution at the first unbalanced `)`, and an unparenthesised
case pattern supplies exactly that. The whole block then fails at **parse**
time with `syntax error near unexpected token ';;'` and exits 2. Nothing
inside it runs: no archival sweep, no id, no file, and — the part that makes
it hard to diagnose — neither `ARCHIVAL SWEEP BROKEN` nor `ID COMMAND BROKEN`
can fire, because those guards are inside the block that never started. A
guard cannot report a failure that happens before it exists.

Parenthesised patterns are valid in every POSIX shell and in every bash
version, so the portable form costs nothing. Keep it in every copy of the
snippet, here and in SKILL.md.

**If you are porting the snippet or writing a new one:** run it once under
`/bin/bash` on macOS, not only under the shell your session happens to have.
`bash -n <file>` is enough — it parses without executing, so it is safe to
run against a snippet that would otherwise write to the log.

### The guard line, the sweep's count and the noclobber create

The guard line distinguishes "the log says zero" from "I could not read
the log": a command that fails to empty rather than to error would
otherwise propose id 1 in a populated log. The sweep carries the same
guard in its own right — it counts the files it actually examined and
halts if that count is zero while `find` reports files present. An
archival loop that never enters its body moves nothing and exits
successfully, so without the count "nothing was due for archival" and
"the loop never ran" are the same output. The `noclobber` create covers
the one case per-file isolation does not ("Why this is the entire
concurrency story" below): two sessions that pick the same id *and* the
same slug resolve to one identical path, where the second writer would
silently replace the first. So the snippet refuses an existing path and
creates the file under `noclobber` — write the body only after that create
succeeds, and on a collision re-derive the id rather than overwrite.

### Run the snippet immediately before every write

**Run the snippet immediately before EVERY write, including the first and
only one of a session.** Having already read the log directory earlier for
some other reason — the session-start frontmatter scan, a grep for
observations naming the skills in use, a status check — does not substitute
for it, and is the state in which skipping feels most reasonable. Those are
*relevance* queries; the id is a *maximum*, and the answer to one is never
evidence about the other: a relevance grep returns its highest **matching**
entry, not the highest entry, and neither it nor any plain listing of
`observation-log/` reads `archive/` or `.id-floor`, which are two of the
three inputs and the reason the command exists. (Observed: a relevance grep
whose top hit was id N was read as meaning the next id was N+1, over an id
already in use, while the true maximum, sitting in the archive, was twenty
higher.) If a collision happens anyway it is harmless — distinct files,
nothing lost — but should be fixed on discovery rather than left for a
review to notice: derive a correct id with the snippet, `mv` the newer file
to that prefix, and edit its `id:` frontmatter field to match. Both are
ordinary single-file operations; no other entry is touched.

### Resolve each id at its own write time

**Every write, not just batched ones.** An earlier version of this rule
opened "when logging more than one observation in a session that may
overlap a scheduled review or another writer" — two scope conditions, and a
single write in a session that looks like it overlaps nothing satisfies
neither. The reported failure was exactly that shape: one observation, the
snippet run in the same shell call printing `next_id=92`, and the heredoc
that followed carrying `91` in both the filename and the `id:` field. A
parallel session had written `0091` in between. The scope conditions are
gone: run the snippet before **each** write, including the first and only
one of a session.

**Write the value the snippet printed.** This is the step the rule never
stated, and it is where that failure actually happened — not in deriving
the id, which was correct, but in the gap between deriving it and typing it.
The number the snippet prints goes into the filename **and** the `id:`
field, copied, not retyped from memory of what you expected it to be. If
the two disagree, the file is the one every later scan believes.

**Never pre-compute a range.** A batch append is N separate races, not one;
pre-baked sequential numbers collapse N independent max-checks into a
single stale read. Resolve each entry's id against the live directory at
the moment of its own write, and run a post-write per-number count when
overlap is plausible.

**Observation writes are not independent calls — do not parallelise them.**
Harnesses commonly instruct the agent to issue independent tool calls in
one block, for latency. Observation writes look independent (different
files, no shared variable) and are not: each one's id depends on the state
the previous one leaves behind, so two writes dispatched in the same block
both read the same maximum and mint the same number. This is a third source
of collision, alongside a parallel session and a subagent of this session,
and it is the only one that lives entirely inside a single agent's own
turn — which makes it the one no amount of caution about "other writers"
prevents. When several observations are due, write them one at a time, each
after the previous write has completed.

### A structural probe that comes back empty is a stop signal

**A structural probe that comes back empty where content existed before is
a stop signal, not a create.** If the directory or file you logged to
earlier in the session is suddenly missing, or the id check returns empty
in a log you know is populated, HALT and re-probe the structure (is there
an `observation-log/`? a `log.md.migrated`?) — a parallel session may have
migrated or reorganised the storage. Never let an append silently recreate
a missing target: that converts a migration signal into corruption
(observed: a stale session recreated the retired `log.md` with a fresh
"Observation 1" after the per-file migration renamed it; see
`migration.md` on coexistence with live sessions). A writer's model of
shared mutable state is only as fresh as its last read.

**This covers reads as well as writes.** A retrieval that comes back empty
over content you know exists — the session-start scan, a filter for
observations naming the current skills, a grep for a prior finding — is the
same signal wearing different clothes, and it is the more dangerous half,
because a broken read produces no error and its result ("nothing relevant")
is a legitimate possible answer. Re-probe before acting on it (see "Guard
the read, not just the write" above).

### Why this is the entire concurrency story

Because every observation lives in its own file, a new observation never
touches another entry's bytes, so it cannot truncate, overwrite or renumber
anyone else's work. The single-file log needed a check-then-act-then-verify
numbering ritual, bounded-mutation rules, a structural-invariant check and a
survival check, because one greedy substitution once overwrote sixteen
entries from a Status line to end-of-file, and because a parallel session's
write-back once silently erased entries appended minutes earlier. None of
those failure modes exist when each file is isolated. In the rare case two
parallel sessions pick the same id, the result is two files sharing a
number — harmless, distinct files, nothing lost, as long as the slugs
differ; an identical id AND slug is one path, which is what the snippet's
existence check and `noclobber` create guard against; the next review renumbers
one and logs a meta-observation.

**The bounded-mutation discipline outlived the single-file log.** It was
written for `log.md` and it applies to every deletion or replacement the
agent makes in any multi-entry text file — a handoff document, a numbered
list, a review report, a manifest. Locate the target by its own boundaries
(the item's first line and the next item's first line), never by
surrounding whitespace or a greedy pattern: a `\n\n` "paragraph" boundary
around one item of a numbered list ran to the end of the list and deleted
every item after it, exactly the shape of the sixteen-entry loss above.
Re-read the region after the edit and count what survived against what
was meant to survive.

## Read the full body before resolving, dismissing, fixing or citing

**Read the full body before resolving, dismissing, fixing, or citing.** A
tracked item's title (observation, GitHub issue, ticket) is an index entry,
not its content — it compresses away the failure story, the reporter's
context, and often the proposed fix. Dismissal is the path with no
downstream checkpoint: a resolved or cited item gets reviewed later, a
dismissed one silently disappears. Harvest fix designs from issue bodies —
reporters frequently include the correct solution, which also settles
attribution. When a parallel agent logs a finding that appears to duplicate
your own, diff the two bodies, not the titles: two entries about the same
mechanism can carry opposite operational conclusions, and the second is
often the refinement, not the echo. Apparent agreement suppresses
verification more effectively than disagreement does, so this rule binds
hardest exactly where it feels least necessary.

## Editing an existing observation

Status changes and archival touch exactly one file. Re-read that file
immediately before editing it (a parallel review may have resolved it),
then edit only the frontmatter fields you are changing (`status`,
`resolved`, `resolution`). Never rewrite a file you don't own, and never
batch-rewrite the whole directory — it is not needed, and it reintroduces
the multi-entry hazard the layout exists to remove.

When a backlog is split between parallel sessions, the mechanical safety
above cannot stop two sessions legitimately resolving the *same* file in
different ways. A handoff that splits work must therefore carry an
ownership fence: an explicit in-scope list by id, an explicit out-of-scope
list, and the instruction that each session edits status only on its own
ids.

**Re-check ownership immediately before the first write, not at planning
time.** "Is anyone else working on this?" is answered from two sources that
are both honest and both stale the moment they are read: a handoff or
manifest state, and a session listing. A **paused** session has not released
its task — it is idle, it reads as idle, and it can resume at any moment
with its own decisions intact.

Observed: a long multi-step review was left paused partway through, its
state saying "waiting on the user's decisions" and the listing showing it
not running. A second session checked both at planning time, correctly
concluded the first was idle, and planned to take over. Before it made its
first write the user resumed the first session, which then recorded its
decisions and completed most of the work. Had the second session written,
it would have re-asked the user decisions they had already made.

So the check belongs immediately before the first write, in the same turn —
the same rule as re-reading a file before editing it, for the same reason.
Planning-time evidence of idleness has a shelf life of exactly as long as
the planning takes. And prefer a check on **the result** — has the work
already landed in the target? — over a check on the vehicle, since a paused
session's state says nothing about what it is about to do.

**Edit log files with the editing tool — never `sed -i`, `perl -pi`, or a
redirection over the file.** No exception for a quick fix or a temporary
negative test; the temptation peaks exactly on a file with uncommitted work
and nothing to fall back to.

Rewriting a text file from the shell passes the replacement through the
shell's quoting first, and what arrives is not always what was typed. An
unescaped `$` inside a double-quoted replacement has landed in a source
file as a NUL byte, turning the file binary — and **the command exited 0**.
The damage surfaced later and by accident, when a `grep` answered "Binary
file matches" instead of the expected line.

Observation bodies make this sharply worse than it sounds. They are full of
backticks, `$`, quotes and braces, because they quote commands and
frontmatter for a living. A heredoc is the natural way to write one from a
shell, and an **unquoted** heredoc executes every backticked span inside
it: the file is created, it looks superficially right, and parts of its
content have been replaced by the output of commands. Quote the delimiter
(`<<'OBS'`) whenever a shell write is genuinely the only path — a
`set -C` noclobber create has no editing-tool equivalent — and prefer the
editing tool everywhere else.

If a shell write happened anyway, **verify the file is still text before
doing anything else**: `file "$f"` or a `grep -c ''` that does not answer
"Binary file matches".

**A declined entry records a verdict; without its premise the verdict
cannot be revisited.** `declined` means someone judged an alternative
unworkable, and that judgement is a factual claim which can be wrong — in
which case it silently vetoes the better solution forever, because every
later reader finds the decision already made.

Observed: an entry recorded that a helper had been rejected because it
"would die hard inside a nonfatal wrapper and leak the session it had
started". Plausible, specific, and completely unfalsifiable from the entry
itself — no file, no line, no command. A later session read the helper's
source: it uses the library's return-instead-of-exit form under exactly
that wrapper, so the stated failure could not occur. The premise was simply
false. The helper was adopted and improved both call paths. Between those
two sessions the entry did its job perfectly — it was read, believed, and
honoured.

So a `resolution:` on a declined entry carries **the evidence, not only the
verdict**: what was examined (file, line, command, output), and what would
have to be true for the decline to be wrong. And re-reading a declined
entry obliges you to check that its premise still holds before relying on
it — a decline is the one status whose correctness nothing downstream ever
tests.

## The `parked` status — decided, not pending

**`parked` means decided, not pending.** Use it when an observation is sound
but cannot be acted on until an external precondition is met — the scheduled
task that produced it is disabled, the tool it describes is out of use, a
dependency has not landed. A parked entry is OUT of the work queue: reviews
must not re-escalate it, and the decision belongs in `status:`, not in a
free-text note beside a `status: open` (a note nothing classifies on leaves
the entry in the queue and it gets re-raised at every review). It is not
resolved either, so it never archives — archival needs a resolved status plus
a `resolved:` date. It stays in `observation-log/` indefinitely until either
its `parked_until:` condition is met — set it back to `open` and queue it — or
it is genuinely resolved. `parked_until:` is mandatory whenever status is
`parked`: one line stating the condition, phrased so a later session can
actually answer whether it has happened — and checked, before parking, for
whether it can happen at all: ask who or what would have to act to meet the
condition, and whether that party has a reason to do exactly the opposite
(sometimes as the intended effect of the very thing the entry is waiting to
observe). If the condition cannot occur, the entry is not waiting: close it on
the substitute evidence available today, or park it on a trigger that can
actually fire.

## Partially actioning a multi-skill observation — the carrier pattern

`status:` is per-observation, but `skill:` is a list, so the lifecycle
field is coarser than the work it tracks. When one session legitimately
acts on only a subset of the listed skills — a release session owning one
skill while a parallel review owns the rest — both plain moves are wrong:
left `open`, another session may re-apply the finished portion; marked
`actioned`, the unfinished portions silently leave every future review
queue. Split the record along the work's seams instead:

1. **While the partial work is in progress**, note the claim in the body:
   "portion X being applied by session Y — do not re-apply." The claim is
   what protects the in-flight portion from a parallel session.
2. **On completion**, mark the observation `actioned` with a `resolution:`
   naming exactly which portions were applied.
3. **In the same turn**, log a carrier observation holding the remaining
   portions: only the outstanding skills in its `skill:` list, a body
   stating it carries the unapplied remainder of the original (cite the
   original's id), and the substance the outstanding portions need —
   never just a pointer, since the original is about to archive.
4. **Reviews treat carriers as first-class.** A carrier enters the work
   queue like any other open observation; nothing about its provenance
   defers or demotes it.

Principle: when a record's lifecycle field is coarser than the work it
tracks, every state transition tells some consumer a lie — split the
record along the work's seams rather than overloading the status.

## When the workspace is under version control

Versioning the workspace folder is good practice — it gives the rollback
the skill cares about — and it adds a mutation surface that does not look
like one. `git checkout -- <path>`, `git stash`, `git reset --hard`, a
branch switch carrying local modifications, a rebase that drops a hunk,
and above all `git clean -fd` destroy observation files as thoroughly as
any edit; the newest files are the most exposed, because a just-written
observation is an *untracked* file until someone commits it, and
`git clean` exists to delete exactly those. These commands get run
reflexively as housekeeping ("make the tree clean enough to switch
branches"), and a continuously written log is almost always what makes the
tree dirty.

Rules: before any git operation that can discard working-tree state, copy
`observation-log/` somewhere outside the repository, and afterwards
confirm every file this session wrote still exists, re-creating from the
copy if not. **Prefer committing pending observations over reverting
them** — when the dirt in the tree is the log, a commit is always the
cheaper way to get clean. Scope any dirty-tree guard to exclude
`skill-observations/` rather than teaching sessions to clear it, and never
run `git clean` with that directory in scope.

## Archival

Archival is bound structurally to the id derivation (Assigning an id,
above): the same command that computes the next id first moves
already-resolved files from `observation-log/` to
`observation-log/archive/`, so every write triggers the sweep as a side
effect of a step it cannot skip. The prose form of the rule — "on every
write, first archive" — under-fires in practice: a duty attached as a
preamble to another action inherits none of that action's enforcement,
so if a step must always accompany a tool call, it belongs inside the
same command, not beside it in prose. The scheduled review archives
independently at its Step 1, as a backstop for logging-quiet weeks.
"Already resolved" is decided by the file's
own frontmatter: `status: actioned`, `declined` or `superseded` AND a
`resolved:` date before today. Files resolved today stay until the next
day, no matter which session resolved them — the grace period lives in the
file, never in session memory, so it holds across parallel and subsequent
sessions. A resolved file with no readable `resolved:` date gets today's
date written to that field instead of being archived; the embedded sweep
deliberately skips such files (its date check fails closed), so that
one-field repair is a separate, careful edit of that file alone.

**`parked` is exempt from archival — deliberately.** It is the one status
that means "decided" without meaning "resolved", so it satisfies neither half
of the gate: not in the resolved set, and it carries no `resolved:` date. Do
not infer from "it has left the work queue" that it should be archived, and do
not stamp it with a `resolved:` date to tidy it away — a parked entry has to
stay in `observation-log/` for the review to re-check its `parked_until:`
condition (`weekly-review.md`, Step 1). It archives only once it is actually
actioned, declined or superseded.

Archival is a set of plain `mv` operations, one file at a time. Moving one
resolved file cannot affect any other observation. Compare a `resolved:`
date to today portably (ISO dates sort lexically):

```bash
older_than_today() {   # $1 = a YYYY-MM-DD date
  today=$(date +%F)
  [ "$(printf '%s\n%s\n' "$1" "$today" | sort | head -1)" = "$1" ] \
    && [ "$1" != "$today" ]
}
```

The archive is flat: the resolution date lives in each file, so no dated
archive filename is needed. Legacy `log-YYYY-MM-DD.md` files from a
pre-3.0 install sit beside the per-file archive untouched; they are not
converted (see `migration.md`) and are not scanned.

## Referencing observations

Cite an observation by the `id` field in its frontmatter, which matches the
`NNNN-` prefix of its filename. Never cite a `grep -n` line number as if it
were the id — search-tool line numbers are positional metadata, not
identifiers. Cheap plausibility check: a cited id should fall within the
range of ids that actually exist across `observation-log/`, its `archive/`
and `.id-floor`; a number far outside that range (citing #1365 when the
highest id is #766) is almost certainly a line number misread as an id.
IDs come from the record's own identifier field, never from the positional
metadata of the tool that found it.

## Why the checkpoints are writes, not questions

The core skill requires a write to disk at every third completed todo item
and at every deliverable event — an observation file, or a one-line
acknowledgement in `checkpoints.log` when nothing has accumulated. The
reason is that a remembered "ask whether anything is worth logging" is not
enforcement: softer "check when completing items" guidance has been shown,
repeatedly, to get lost during cognitively demanding analytical work —
exactly when the most observations accumulate. A concrete write forces the
mental check to surface as a recorded action, and it prevents the common
failure where the skill is loaded but nothing is written until the user
asks. Hooking the flush onto tool calls you are already making (presenting
a file, rendering a deck, completing a todo batch) means the write happens
as a side effect of work you were doing anyway, rather than depending on a
separate act of memory. The count need not be precise; roughly every third
completion is the rule.

### The scan ends in a write, not only a print

Loading this skill and executing this protocol are two acts, and only the
load leaves an artefact in the transcript — which discharges the felt
obligation, so a session that loaded and then ran nothing looks from
outside exactly like one that did both. The appended `checkpoints.log`
line is the protocol's own trace, for the same reason the checkpoint rule
is a write: a step whose value lies in happening at a specific moment needs
its own entry in the tool record. (Where the workspace prices every write —
the exception under "How to Log" — fold this line into the session's first
write instead.)

### Two gaps the checkpoint pairing still leaves — and the rule behind both

**Two gaps this pairing still leaves — both observed across full working days
in which nothing was logged at all.**

1. *A session can contain no todo items whatsoever.* The 3rd-completion
   checkpoint is bound to ONE tool; work driven entirely through direct tool
   calls and shell commands never trips it. It is armed only in sessions that
   happen to use todos, so it is not a safety net that is always present. When
   a session runs without them, the deliverable flush is the only enforcement
   left and must be applied deliberately.
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
the gap. Record both results next to the trigger. (Observed: a reminder hook
whose six patterns were derived from what the deploy script does internally
never matched the command the project actually types to run it, and had been
inert on its own target since installation; the same day it fired on a
read-only command whose test string merely contained a signal word.)
And a counter bound to a single tool is silently inert in every session that does
not use it — such triggers always need a second, independent path. Nor may a
trigger pre-empt a delivery decision a later layer already owns ("the recipient
is right there, no need to send"): fire the action and let the owning layer
suppress it — a suppressed send leaves a trace in the tool record, an unsent one
leaves nothing.
