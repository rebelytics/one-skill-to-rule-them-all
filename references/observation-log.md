# The observation log — storage layout, scripts and rationale

Load triggers: creating the workspace or setting up the log; archiving, or verifying a bulk move; an id or a frontmatter field looks wrong or drifts; writing or changing any instrument that reads the log; why snippets take a spaced path and run under bash; the per-skill check feels redundant after the session-start scan; the scan's guard fires or the scan is being adapted; moving the scan's print; resolving an observation's siblings (skill families); why the checkpoints are writes; adding or changing an enforcement trigger; editing an existing observation's body; the id guard, the sweep's count or the noclobber create fires; skipping the id snippet feels reasonable or two files share an id; batching or parallelising observation writes; writing after a structural probe came back empty; setting, reviewing or unparking a parked status; setting `reference:`; resolving, dismissing, fixing or citing an observation; partially actioning a multi-skill observation (carrier pattern)

The core skill carries the per-invocation rules: where the log is, how to
name and number a file, the frontmatter format, and the archival rule.
This file holds the layout in full, the helper snippets, and the reasoning
behind the rules; the load triggers above say when to open it.

## Contents

- Layout
  - Workspace creation
  - Snippets take a spaced path and run under bash
- Frontmatter fields
  - Unquoted `: ` in a prose value — how far it drifts before anyone notices
  - A list entry holding a colon is not portable
  - A park condition names the result, never your own vehicle
  - Context preservation — the `reference:` field
  - Commands inside an observation — run before the file is written
- Scanning cheaply
  - Why the session-start scan does not satisfy the per-skill check
  - An empty scan over a non-empty log is a broken command
  - A refused print is not an empty log
  - Every instrument gets the same guard
  - A refused snippet is a degraded path, never a skipped step
- Skill families and the sibling check
- Assigning an id
  - Shell portability — bash 3.2: the `case` pattern inside `$( )` and the empty array under `set -u`
  - The guard line, the sweep's count and the noclobber create
  - Run the snippet immediately before every write
  - Resolve each id at its own write time
  - Floor staleness — the floor below the highest active prefix
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
  forked-skills.txt      # vendored skills the user adopted on purpose, one line each
                         #   (weekly-review.md Step 2; created on the first fork)
  reviews/               # one record per review run: reviews/YYYY-MM-DD/REVIEW.md
                         #   (weekly-review.md Step 7; kept, never pruned by a step)
  checkpoints.log        # append-only acknowledgement markers (optional)
  MOVED.md               # only at an abandoned root: line 1 names the new root
                         #   (environments.md, "Before creating a log, search for one")
```

Each file follows the core frontmatter format (How to Log); the listing
is the index.

### Workspace creation

One idempotent command, then an assertion. Session Start step 1 points
here: run this, do not work down the tree above by hand.

```bash
d="[ABSOLUTE PATH]/skill-observations"   # the pinned path, quoted: it may contain a space; bash, not sh
[ -e "$d/log.md" ] && [ ! -d "$d/observation-log" ] && { echo "LEGACY log.md — run the migration (references/migration.md) before creating anything"; exit 1; }
[ -e "$d/log.md" ] && [ -d "$d/observation-log" ] && { echo "SPLIT STORE — log.md holds $(grep -c '^### Observation ' "$d/log.md") observations not in observation-log/ (an older installed copy still writes the legacy file); migrate the remainder (references/migration.md), re-issuing ids from the directory's counter"; exit 1; }
c=; for x in observation-log observation-log/archive last-review-date.txt cross-cutting-principles.md; do [ -e "$d/$x" ] || c="$c${c:+,}$x"; done   # what this run creates
mkdir -p "$d/observation-log/archive"
[ -e "$d/last-review-date.txt" ] || printf 'never\n' > "$d/last-review-date.txt"   # the literal `never`, never a date: a date means a review actually ran
[ -e "$d/cross-cutting-principles.md" ] || printf '# Cross-Cutting Principles\n\nPrinciples that apply to all skills. Read as a mandatory checklist during\nany skill creation or regeneration.\n\n---\n\n## Active Principles\n' > "$d/cross-cutting-principles.md"
for x in observation-log observation-log/archive last-review-date.txt cross-cutting-principles.md; do
  [ -e "$d/$x" ] || { echo "WORKSPACE SETUP INCOMPLETE: $x"; exit 1; }
done
printf '%s [%s] workspace: created=%s\n' "$(date '+%F %H:%M')" "${PWD##*/}" "${c:-none}" >> "$d/checkpoints.log"   # step 1's trace
```

`mkdir -p` creates the parent, so `observation-log/` needs no separate line;
the `[ -e ]` guards make the command safe to re-run on an existing
workspace, which is what lets step 1 run it unconditionally rather than
deciding first whether setup is needed. The legacy guard runs first
because a created `observation-log/` would hide the one condition that
identifies a pre-3.0 install; the split-store guard beside it catches the
install that was migrated and then kept writing `log.md` through an older
copy the host still loads, which the first guard alone can never see
again once the directory exists. The principles stub is the header of the
template in `skill-authoring.md` ("Principle Propagation"); change the two
together.

**Step 1 leaves a trace.** The last line appends what this run created to
`checkpoints.log` — `created=none` on an ordinary session, the artefact
names on a fresh install or a repaired one. Creation is otherwise the one
session-start action nothing records: when a review finds the principles
file missing, a step 1 that never ran and a file deleted later look the
same, and only the trace tells them apart.
Other files created at session start on the same terms, for a test plan
rather than this command: `starter-principles-reviewed.txt` (starter-set
reconciliation) and `skill-families.md` (created when the first family
is named).

**A read-only or permission error on an allowlisted path is a missing
path, not an unwritable log.** When this command fails with `Read-only
file system` or a permission error on a workspace path the harness's
write allowlist names, the likely cause is that the path does not exist
yet and the sandbox cannot create it (`environments.md`, "Anchoring the
workspace", "A grant names a path"). Say that to the user in one line and
hand them the fix — create `skill-observations/` and `skill-updates/`
under the pinned root from outside the sandbox — instead of retrying
through another interface or falling through to the unwritable-log or
no-filesystem branches.

The assertion loop is the half that matters, because the four artefacts
fail differently and only one of them complains:

| Missing | How it surfaces |
|---|---|
| `observation-log/` | immediately, at the first scan |
| `archive/` | at the first write, when the id snippet reads `.id-floor` or `mv`s into it |
| `cross-cutting-principles.md` | at the first review |
| `last-review-date.txt` | only if step 3 applies its own recreate rule — otherwise the review trigger never fires, and nothing says so |

### Snippets take a spaced path and run under bash

**The substituted path routinely contains a space** — the default
shared-folder name on at least one common install does — so every
expansion of it stays double-quoted, and no snippet may feed it through
word splitting (`for f in $(find …)`): a sweep that splits its own path at
the space examines zero files, prints errors nobody reads, and lets the
command it rides inside succeed.

**Every snippet in this skill is bash, not POSIX `sh`** — the id snippet's
`10#` arithmetic is a bash extension `dash` and `ash` reject, so under `sh`
the derivation stops before any file exists, and an adapted snippet may
fail more quietly than that. A `bash` code fence states that to a human
reader and to nothing else, so invoke the snippets with bash explicitly; a
block that happens to be POSIX-safe too (the sweep) is incidental, not a
promise about the rest.

## Frontmatter fields

| Field | Meaning |
|---|---|
| `id` | Integer: the number the snippet printed, equal to the `NNNN-` filename prefix read as a number. The prefix is four digits, zero-padded (`printf '%04d'`, as the snippet and the script write it), so a listing sorts numerically and a clash is visible in it; `63-` beside `0063-` is one id written by something other than the snippet. The field is written unpadded (`id: 63`); a padded copy of the prefix (`id: 0063`) reads as the same number and is not a defect — every check compares numerically — while a value that reads as another number is. Never reused. |
| `title` | Short descriptive title. It is the summary every restatement check and frontmatter scan matches against, and an edit to the body does not update it: when an appended instance widens the finding, rewrite the title in the same edit, or the next restatement of the wider finding misses it and is filed as new. |
| `status` | `open`, `actioned`, `declined`, `superseded` (a later observation found this one's mitigation does not work; `resolution` names it) or `parked`. A missing status is read as `open`, never as nonexistent. |
| `parked` (status value) | Decided, but blocked on an external precondition: the entry is sound and no longer awaiting a judgement, so reviews drop it from the work queue and never re-escalate it. It is not resolved, so it does not archive — see Archival below. It stays in `observation-log/` until its `parked_until:` condition is met (set it back to `open`) or it is genuinely resolved. Recording a park as free text while leaving `status: open` does not work: nothing classifies on prose, so the entry stays in the queue and is re-raised at every review. |
| `parked_until` | **Mandatory whenever status is `parked`**, empty otherwise. One line naming the condition that unparks the entry ("the X scheduled task is re-enabled"), phrased so a later review can answer yes or no without reopening the original decision. |
| `type` | `open-source` or `internal` (see Taxonomy in the core skill). |
| `skill` | **Always a list**, even with one entry, so no consumer ever branches on string-vs-list. First entry is primary. May be empty. Write each name in its bare form — the part after the last colon of the listed name — and qualify it as `plugin:skill` only where two installed skills share that bare name; a qualified entry is quoted: `["plugin:skill", other-skill]` (below). Bare is the canonical form because it is what writers produce in practice (0 of 40 entries were qualified when the two rules were compared) and one skill in two spellings is two review buckets. Every lookup BY skill name — a grep with a skill-name slot, `scripts/skill-load.sh` — reduces a `plugin:name` to the part after the last colon before matching: the bare pattern matches both spellings, while a qualified one misses every entry filed under the bare name and returns a clean zero. |
| `proposes_skill` | List of new-skill candidates by working name. Independent of `skill`; either may be empty, both may be filled. |
| `target_file` | List of paths, for observations whose right home is not a skill: an instructions file, a memory note, an agent brief, the register a routine reads. Name the file the fix will actually be written to, so a review can go there instead of remapping the entry onto the nearest skill. Every lookup by name reads this field beside `skill:` and matches on the last path segment, so `scripts/skill-load.sh reviewer.md` (and the activation grep) finds an entry filed under that file by any path. Measured on a first review of 27 legacy entries: 15 named a non-skill in `skill:` ("browser verification protocol", "documentation hygiene") and every one had to be resolved to a path by hand before the review could start. |
| `siblings_checked` | **Mandatory, never blank.** Records that the sibling check happened and what it concluded: the family name, the members evaluated, and the verdict per member (propagated / excluded). Every **exclusion** carries its ground — the file and section (or line) read in that sibling showing it does not apply — or the literal token `assumed`; inclusions need no ground, because including a sibling is the safe error. An `assumed` exclusion is a review item, not a settled verdict. `none` only where the target belongs to no family. Missing or empty = logged without a sibling check, and reviews count it as such. |
| `area` | The part of the skill or workflow concerned. |
| `date` | Date logged, `YYYY-MM-DD`. |
| `session_context` | What was being worked on. |
| `resolved` | Resolution date; set only when status is `actioned`, `declined` or `superseded`. Archival is gated on it. |
| `resolution` | What was done, or why declined. When the fix is a prescription (a rule, a check, a form to use), an `actioned` resolution names where it now lives — a file and section, a staged skill copy, or a registered backlog entry. If no such place can be named, the prescription has been described, not applied: leave the entry `open`, or resolve the part that landed and carry the rest in a carrier observation (below). A review's own resolution already names the staged copy (`weekly-review.md`, Step 6); this is the rule for a resolution set outside a review. |
| `reference` | Optional path to saved session-local evidence. |
| `commands_verified` | One clause per executable command, and per predicate (a regex, a search pattern, a hook or check condition), the body quotes: `run`, with what it returned — for a predicate, whether it matched the positive case and the negative — or `NOT RUN` with why; the literal `none` where the body quotes neither. Blank on a body that quotes a command or predicate means it was never run. See "Commands inside an observation" below. |
| `skill_qualifiers` | Optional map: skill name → the section or part of that skill meant. |
| `migration_note` | Present only on files converted from a legacy log where the converter refused to guess; clear it once reviewed. |

**Field names and status values are exact.** `skills:`, `proposed_skill:`
and `sibling_checked:` are read by nothing: an entry carrying one of them
sits under no skill at all, indistinguishable from `skill: []`, and a
review bucketing by target routes it nowhere. `status: OPEN` is not one of
the five values — a reader that happens to case-fold hides the defect, it
does not license it. `id:` is the number the snippet printed, and a check
that rejects its zero-padded form rejects a live log's own entries (measured
on one: 4 hits, 0 defects, 0 normalised). A scan that parses every header and checks
none of them against this table touches such an entry on schedule and
reports a clean count. The failure produces a smaller number, never an error, which is
why a near-miss name is flagged rather than skipped wherever a check runs.

**An entry is UTF-8 without a byte order mark.** Every header reader tests
line 1 for `---`, and a BOM in front of it hides the header: the scan
skips the entry with `parsed` one below `files`, and the archival sweep
never moves it (`environments.md`, "Windows hosts: what reaches the shell
and the file").

### Unquoted `: ` in a prose value — how far it drifts before anyone notices

The core states the rule (quote every prose value); this is the measurement
behind it, because the failure is unusually quiet. An unquoted `: ` in a
free-text value is invalid YAML, yet the frontmatter still *extracts* (a
regex slicing between the two `---` lines is happy), so the session-start
scan reports the file parsed while every consumer that actually **parses**
— a review reading `status`, a hook counting `skill:`, a validator checking
the header — throws on the file, and a thrown file is usually skipped
rather than reported. Measured on one live log: about one header in ten
unparseable, most in `resolution:` (the field most likely to hold a colon),
each written by following a template that carried the value unquoted.

The scan's `suspect` count is the early warning: it reports headers that
look invalid by shape — an unquoted `: `, text after a closing quote
(either style), a value opening with a backtick, `@` or `%`, an escape a
double-quoted YAML string does not define (`\x`, `\u`, `\U` need 2, 4
and 8 hex digits) — beside the file count, for the active directory and
for `archive/`, so a log drifting into this state announces itself at
session start rather than at the review that trips over it. The awk
program resets its state on each file's first line, so an unterminated
header cannot leak into the next file under `find -exec … {} +`; it
allows any number of spaces after the colon and an `&anchor` or `!tag`
before the value, and it never treats a value opening with `{` or `#`
as prose, which is what kept the template's own `reference:` comment
line from being flagged. It is a floor, not a parse: a `[…]` list is
checked only for a colon in an unquoted entry, a `{…}` mapping not at all,
and a plain value followed by a `# comment: x` still counts. It also misses an unterminated quote, a tab in
place of the space after a colon, a value ending in a colon or opening
with `: `, a `: ` on a continuation line, a key outside `[a-z_]+`, and an
empty value under a typed tag (`!!int`). Re-verify by running a real YAML parse over the
frontmatter of every file, not by re-reading the template.

The typographic quote is the other common break, and it is quieter. A
value that opens with „ or “ is a plain scalar: the quote characters
become part of the text, an unquoted `: ` inside it still breaks the
file, and nothing looks wrong in an editor. A value that opens with an
ASCII `"` and closes with a typographic one never closes. Inside an
ASCII-quoted value, a „…" closed with an ASCII `"` ends the value at that
`"`, and the rest of the line is text after a closing quote, which the
scan flags. Quote with the
ASCII pair; for a quotation inside the value use »…« or `\"`.

### A list entry holding a colon is not portable

The frontmatter names no single parser, so "valid" means: loads under
every YAML parser a consumer of this log is likely to use. Under the YAML
1.2 reading, a `:` inside a plain scalar in flow context is part of the
scalar when the next character is not a space, so `skill: [plugin:name]`
is the list of one string it looks like; under the older rule, which
libyaml-backed parsers (Ruby's Psych, Go, `yq`) have applied in some
versions, a `:` ends the plain scalar and the line raises `found
unexpected ':' while scanning a plain scalar`. Both are correct
implementations of different specifications, so the header is not
portable — and the failure is invisible from either side: a Python
consumer (`migrate-log.py`, `validate-skill-bundle.py`, most hooks) sees a
clean log forever; a consumer on the other rule sees most of it fail to
load (one 202-file log: 8 suspect by the shipped scan, 0 invalid under
PyYAML, 127 under Psych, all three right about the same corpus). So the
rule is the intersection: **quote any list entry that contains a colon**
— `skill: ["superpowers:test-driven-development", task-observer]` — or
use a block list, where the colon is legal unquoted. Both forms parse
identically under both rules (a plugin-scoped name is not a bare
kebab-case name). `scripts/migrate-log.py` already writes the quoted form,
so a migrated log is portable; entries written by hand from the template
are the ones to check.

The scan's `suspect` count sees this class through one rule of its own:
in a value opening with `[`, it drops every quoted string and any
trailing comment and flags what is left if it still holds a colon. So
`[plugin:name]` counts and `["plugin:name"]` does not. The rule has one
accepted false positive, `[a: b]` — valid YAML under both readings, a
one-entry mapping — which the template never produces. The count is
labelled `suspect (awk, a floor)` because it is a shape check by one
instrument and a lower bound: "8 suspect" never means "8 invalid", and
zero says nothing about a parser on the other rule. Re-verify with two
parsers, not one: a check that agrees
with the parser you already trust is the one to distrust
(`skill-authoring.md`, "A verification command that AGREES with you").

### A park condition names the result, never your own vehicle

`parked_until:` must name a condition that can occur — and pass a second,
sharper test: **can the result arrive without the condition firing?** "PR
#N is merged or closed" waits on a path the other party need not take: a
maintainer folds the change into a commit of their own, cherry-picks it or
rewrites it, the PR stays open or is closed as overtaken, and **the result
the entry was waiting for has fully arrived** while the condition never
fires — the normal case for a contribution to a repository someone else
maintains. For anything depending on another party's process the answer
is yes, so phrase the condition on the **text of the target artefact** —
"rule X is present in `main`'s SKILL.md" — which is answered by reading
the target, whatever route the change took. The same applies to any
vehicle standing in for a result: a ticket resolved, a build green, a
message replied to. Park on what you actually need to be true.

A condition phrased as text in the target is checked by a phrase search,
and hard-wrapped Markdown breaks a line-oriented one: the phrase spans a
line break and `grep` reports no match. Search within a Markdown block with
whitespace normalised (join the lines of a paragraph, collapse runs of
spaces), and test the search once against a known wrapped hit and a known
cross-block non-match before trusting a "not present".

For a skill the user does not maintain, the target artefact is the LOCAL
INSTALL, not the upstream tree. An upstream report is not resolved when it
is accepted, merged or released — none of those changes the copy that is
running — and nothing observes a re-install. So the entry stays `parked`
on a condition read from the installed copy ("the installed `task-observer`
carries rule X", or names the version that carries it), and is resolved
when that copy carries the fix.

### Context preservation — the `reference:` field

Rule: core, How to Log ("Context preservation"). `reference:` — like any
pointer that hands work to a later session — names a durable path, one
that outlives the session and a reboot and that a session other than this
one can resolve. A session-scoped temp directory fails both tests, and a
role name ("the scratchpad", "my notes") is not a path at all. Such a
pointer cannot fail at write time, only at read time, when its author is
no longer there to repair it — a pointer a fresh session cannot follow is
not preservation.

### Commands inside an observation — run before the file is written

An observation that quotes an executable command carries it onward with a
first-hand observation's authority, and what was witnessed was the
experience — the command is usually reconstructed from memory, after the
fact. Nothing downstream can tell the two apart. The authoring pre-flight
in `skill-authoring.md` runs when a skill is written, often on another
machine, another day, without the system the command refers to; at
logging time the session is standing in front of that system and running
it costs seconds. So before the file is written, run every command the
body quotes — literally, and look at its output — and where that is not
possible, mark the command unverified in the body. Record the outcome in
`commands_verified:`, one clause per command, and the literal `none` where
the body quotes no command, for the same reason `siblings_checked:` never
stays blank: a body with an unrun command is byte-identical whether it was
checked and trusted or never considered, and only the field makes the
absence visible. Where the run shows the remembered form is wrong, the
body quotes the form that ran, never the one it was reconstructed from.

**A predicate the Suggested improvement proposes — a regex, a search
pattern, a condition for a hook or check — is run the same way, against
the positive case the Issue describes and one negative, before the file
is written; record both results in `commands_verified:`.** A predicate is
not a command, so "run every command" does not reach it, the field
honestly says `none`, and the entry carries the detector onward with a
first-hand observation's authority. The input matters as much as the
run: a detector run over a repository returns some output whether or not
it catches the case in hand, so the informative run is on the known
positive — the literal failing string the Issue already holds — and on
one string that must not match. A predicate that misses its positive or
matches its negative is corrected in the body before the file is written.

**A sweep the Suggested improvement prescribes names the behaviour, not
the pattern that found the first instance.** When the improvement tells a
later session to look for the same defect elsewhere, the search string
inherits the grammar of the place the defect was first seen — a filename
glob, a heading, a config key — and the same test written in another
layer's grammar (a method call in code, an assertion in a test) is missed
in silence, while the empty result reads as "there are no others". Name
the concept, list the layers it can live in (docs, code, tests, config),
and give the search in at least two grammars. If every hit is the same
file type, the search covered a grammar, not the concept.

**An observation about a recurring act names the check that catches a
violation, at first logging.** A retrieved observation supplies
knowledge, not compliance: its body is read when the skill loads, and the
act it describes happens many tool calls later, where nothing re-reads
it. So where the Issue is an act a session repeats — a write, a send, a
status edit, a call made without its precondition — the Suggested
improvement names the check that would have caught this instance (a grep
over the artefact, a validator line, a hook condition, one count held
against another), where it runs, and what it prints on a violation; the
check is then run on this instance like any other predicate and recorded
in `commands_verified:`. An entry that names no check proposes a
sentence, and the second-violation rule (core) reaches it only after the
next failure; a check named now makes that escalation a promotion of
something already written and tested, not a design started from scratch.

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
inside `( cd "$d" && … )`, never `for f in $(find …)`: the unquoted
command substitution word-splits any path containing a space, a live
hazard on every workspace whose folder name has one, while a glob in the
directory itself hands `awk` bare file names that nothing splits. It
prints each header followed by one `---` line, the output the earlier
per-file loop produced, with one process for the whole set instead of
one per file; `LC_ALL=C` inside the subshell sorts the glob the way the
loop's `sort` did. Do not rebuild the file list with `$(ls … | xargs …)`:
that reintroduces the word split.

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

**Under zsh, an unquoted `$var` is not split into words, and a word that
begins with `=` is expanded as a command path.** Both run correctly under
bash, so a snippet pre-flighted there ships them. A list carried in a
variable and looped over (`for f in $names`) runs its body once, over the
whole string, so a membership test built that way is always false or
always true — and moves no count, because a count guard counts files while
the defect is in the names. A bare `echo ====` inside a compound command
aborts it with `=== not found`, and everything after it is lost. Never
carry a list in a variable: write it to a file under the workspace and
read it back with `while IFS= read -r`, or compare two such files with
`comm`; quote any word that starts with `=`.

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
tell: nothing is broken, so no
`BROKEN` guard fires, and the refusal message is easy to summarise away as
"nothing found". Where a command can be refused by a policy layer above the
shell — see "A refused print is not an empty log" — the guard covers the
refusal too, and the refusal is reported in its own words.

**The guard is scoped by what a command IS, not by what it looks like.**
Both named instances above — `SCAN COMMAND BROKEN`, `ID COMMAND BROKEN` —
are log-reading snippets shipped inside this skill, so the rule reads, in
practice, as being about *those*. It is not, and the gap is where it costs
most: the one-line environment probes run ad hoc mid-investigation, whose
empty result goes straight into a runbook or an observation body as a fact
(`ls /usr/bin/*askpass* …` in an interactive zsh prints `no matches found`
— a glob error, not an answer — and "no askpass helper present" gets
written down). Apply it to **any command whose empty or zero output is
about to become a claim**: pair it with a second probe by different means,
or state the result as "the probe returned nothing" rather than "there is
nothing".

**When the instrument is an external process, the independent probe
exercises the same code path.** For a literal path the second count is
another read of the same directory by other means. For a CLI invoked
from a non-interactive shell, "different means" is satisfied to the
letter by a sibling subcommand — `--version` prints, so the binary
works — and that proves nothing about whether the subcommand under test
can report to a pipe at all: a subcommand that renders only through an
interactive terminal UI prints nothing and exits 0 when piped, for a
valid result, an invalid one and no result alike, byte-identical to a
genuine empty answer. So the probe is the same subcommand with a
known-bad argument. If that also returns empty with a success exit, the
path is TTY-gated (or otherwise silent under this invocation), the
instrument cannot answer the question, and the correct output is to
hand the command to an interactive terminal rather than report "none
found".

**A number read from a file another process is still writing is
provisional until that process is known to have exited.** This is the
fourth state, and a second count by different means reads the same
unfinished source and is just as empty, so two independent probes agree on
a false negative with full confidence. The partial file is not visibly
partial: `grep`, `awk` and `sed` flush per line to a terminal and per
block to a file or pipe, so a producer still running that has found
nothing *yet* is byte-identical to one that finished and found nothing,
and a harness's interim-read affordance for a backgrounded command is not
a completeness signal. So for this class the guard is a liveness-and-exit
check — the producer's exit status, or `pgrep` on its pattern — run before
the interim output is interpreted at all, never as a cross-check after a
plausible-looking empty result.

**When the instrument is code written in this session, its input coverage
is unverified by construction — print what it ingested, not only what it
found.** A shipped snippet has at least been run against the population
it is meant to read; a throwaway parser has been run against whatever its
author's heuristic happened to match. So the guard's form for
session-written code is a **coverage assertion before any result**: print
the count of terms, rows or files the instrument read and assert it
against the canonical source's own count (the block's line count, the
directory's file count, the table's row count) — a mismatch fails the step
rather than degrading to a heuristic. The count is the guard; the hits are
the finding, green or empty: "0 hits" is a claim about the corpus only
once the instrument is known to see the corpus (the timelessness scan in
`skill-authoring.md` records which patterns ran for exactly this reason).

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
inside a string that also runs a command substitution: in
`echo "$(basename "$d") exit=$?"` bash reports the substitution's
status, not the command's, and other shells differ. And for a new alarm
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
rather than after being challenged. The tell that separates this from ordinary uncertainty is
**repetition**: a first confident answer is a guess; repeating it under
implicit doubt without going to look is the moment the guard should fire,
because repetition feels like consistency and is entrenchment. Being
accidentally right is not being reliable, and the user cannot tell the
two apart from outside.

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
is unavailable in this environment and proceeds with the user's task,
having activated nothing. A skipped protocol leaves exactly the artefact
a protocol that found nothing leaves.

**The snippet is one implementation of the step; the STEP is the
requirement.** When the harness declines a command as unverifiable, do
not rewrite it into a cleverer compound — the refusal is about shape, and
a cleverer compound is the same shape. This ladder answers a refusal of a
command's *shape* only, where the flat form is exactly what the policy
layer can check. A refusal that names the content or the target — the
print refusal above, a denied path — is a denial: report it in its own
words and do not fetch the same content another way. Degrade to flat,
single-purpose
commands over the absolute path, one per call, and do the combining
yourself: list the directory and the archive, extract the frontmatter
fields with one `grep`, read `.id-floor`, and take the maximum by hand
where a maximum is needed. The guard still applies — a non-empty listing
with no ids extracted is a broken read, not an empty log — and the
`checkpoints.log` line is still written. State in the session which form
ran, so a later reader can tell a degraded run from a skipped one. For a
write, the flat form already exists: `scripts/new-observation.sh`,
invoked by absolute path, is one command with no shell operators, and it
is the only write path wherever it can run. The scan has the same flat
form, `scripts/session-start-scan.sh` invoked by absolute path, so it is
the ladder's first rung; the flat reads follow it, for when it is refused
too or cannot run. Every mandatory step that
ships a command owns a sentence saying what remains mandatory when the
command is unavailable; this is that sentence for the scan.

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

## Skill families and the sibling check

Where several skills implement one idea — the same methodology for
different tools, the same structure for different subjects, the same
companion pattern for different base skills — the shared part drifts by
default, because each member is maintained only in the sessions that use
it and nobody looks at the set (measured in real libraries: a rule
applicable to every member of a five-skill family present in one; a rule
whose own text says it "applies to any file-writing script" present in
one of four, while two of the other three break the same way). Nobody
removed anything; some members grew and others did not.

**Why the check has to be a write-time step rather than a habit.** An
insight found while using one member usually applies to the rest, and
nothing in the ordinary workflow asks — so `skill:` collapses to the one
skill in front of you, and the divergence has no symptom until someone
reads two members side by side at a drift audit, months later. The
`skill:` field is already a list, so multi-skill observations are
expressible; the mechanism exists, the *check* does not, and a list field
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

**An absence claim inherits the scope of the search that produced it.**
The installed names a session can see are the user scope plus the
project it runs in. A skill scoped to another project, and the generator
source a project copy is rendered from (a tool-owned directory rendered
into `.claude/skills/`), are invisible from here, so "no installed skill
covers this" is a blind spot until those scopes have been searched — and
a narrow scope never invents a skill, it only misses real ones. Before
writing `proposes_skill:`, a `none` in `siblings_checked:`, or a target as
missing, search the other scopes by the problem as well as by the name —
a proposal is named after the task that surfaced it, and the skill that
already solves it rarely shares the name — and record in
`siblings_checked:` which scopes were searched: "not found" is a finding
only together with where you looked (Session Start step 6). Enumerate the
scopes by glob rather than a recursive `find`, which over a projects root
full of worktrees runs for minutes, and guard the enumeration: an empty
result tells you about the instrument before the library.

```bash
root="[PROJECTS ROOT]"   # absolute path of the directory holding the user's repositories
[ -d "$root" ] || { echo "SWEEP BROKEN — projects root $root does not exist"; exit 1; }
list=$(for d in "$root"/*/.claude/skills/*/ "$root"/*/*/.claude/skills/*/; do [ -f "$d/SKILL.md" ] && echo "${d%/}"; done)
n=$(printf '%s\n' "$list" | grep -c .); p=$(for d in "$root"/*/ "$root"/*/*/; do [ -d "$d" ] && echo; done | wc -l | tr -d ' ')
echo "project skills: $n (in $p directories under $root, two levels deep)"
printf '%s\n' "$list" | grep "/<skill-name>$"                                            # by name: the bare name, any plugin: prefix dropped
printf '%s\n' "$list" | while IFS= read -r d; do if [ -n "$d" ]; then grep -Il -i -- "<term from the body>" "$d/SKILL.md" || :; fi; done   # by problem; a non-match is not an error
```

Globs two levels under the root, one `grep` per project skill — bounded
by the skills found, never by the tree beneath them. `project skills: 0`
over a root that holds directories is an answer about this machine only
if those directories are the repositories you meant; `0 directories` is
a wrong root. Add the equivalent directory of any other tool the user
runs skills from (its project-level skills directory, in place of
`.claude/skills`); the activation block pins the root as
`[PROJECTS ROOT]`, substituted at install like `[ABSOLUTE PATH]`. Run the
sweep before a `proposes_skill:` write, and name its root and count in
`siblings_checked:`.

**3. Record the verdict** in `siblings_checked:` — the field makes an
absent judgement visible (core, How to Log). Because the
field is frontmatter, the cheap scan above can report "N observations
logged without a sibling check" without reading a single body. Where a
skill already relies on "the write is the enforcement", a new rule that
writes nothing is the odd one out and should be suspected on that basis.

**Recording the verdict is not recording its evidence.** The field makes
the absence of the *ritual* visible, not the absence of the *grounds*, and
once the ritual is habitual a specific-sounding verdict can be an
assumption that reads like a checked one. The asymmetry decides where the
ground goes: a sibling wrongly included costs one redundant paragraph at
the next review; a sibling wrongly excluded leaves the family silently and
for good, because nothing downstream ever acts on a negative verdict. So
every exclusion names what it rests on — the file and section read in that
sibling — or says `assumed`, and the review opens an `assumed` sibling
before accepting the exclusion. Example:
`siblings_checked: "list-commands: render, pick, close — render added; pick excluded (pick.md §2, selects by stable id); close excluded (assumed)"`.

**4. Propagation and drift audit at review time** — `weekly-review.md`,
Steps 3 and 4.

## Assigning an id

Rules: core, How to Log. The snippet lives in the core; the notes below
explain its lines.

The snippet leaves the derived number in `$next_id` and the target path in
`$f`; append `printf '%04d\n' "$next_id"` if you also want the filename
prefix echoed.

**`bash scripts/new-observation.sh [--body <file>] <slug> [workspace-root]`
is this snippet as one command.** It performs the same steps in the same
order — sweep, id, prefix guard, noclobber create, floor write — plus one
the inline snippet lacks: before the prefix guard it claims the number
with a noclobber create of an empty marker in `archive/.id-claims/`,
moving up one when the claim is taken, so two runs at the same moment
never share an id. Markers are never removed (no delete permission
needed); one left by an interrupted run only leaves a gap. Its create is
never an empty file: it writes the frontmatter skeleton — `id:` (the
number, unpadded), `date:`, `status: open`, every other field present and
empty — so the id is on disk before anything can retype it and a scan
that meets the file mid-write reports it UNFILLED (a header with an empty
`title:`), never LOST; `--body <file>` builds the filled copy beside it
and renames it into place, so the file holds the skeleton or the whole
body, never a part, and a `NOTE:` on stderr names a body whose `id:` is
not the one issued. It takes the pinned workspace root as its second
argument or from `TASK_OBSERVER_WORKSPACE`, refuses a relative root, a
malformed slug or a missing `observation-log/archive/` (halt and
re-probe; never recreate from a writer), and prints the created path on
stdout. Where it can run, it is the only write path: an id that exists
only as the script's output cannot be carried in memory from an earlier
read to a later write, which is the drift every rule in this section is
trying to prevent. The inline snippet remains for harnesses where a
script cannot be invoked.

The `10#` prefix in the arithmetic is load-bearing, not cosmetic: shell
arithmetic reads a leading-zero number as octal, so `$(( 0105 + 1 ))`
yields 70 — a silently wrong id — and a prefix containing an 8 or 9
(e.g. `0108`) is an invalid octal constant and errors the whole
derivation. `sort -n` needs no stripping; the arithmetic does. The floor
is read as digits only, so a floor file written with a CRLF, padding or
spaces still reads as its number instead of as nothing.

A skill that hands the agent a shell command owns that command's
portability: lead with the portable form, never offer it as a footnote the
agent reaches for after the primary has failed — and make any command that
derives a number from a file fail loudly on an empty result, because a
command that fails to empty rather than to error may never announce that
it failed at all. A snippet meant to run in an agent harness calls core
utilities by names a profile cannot rebind — the harness commonly
initialises its shell from the user's profile, and an alias or function
named `ls` (`eza`, `lsd`, a wrapper with default flags) changes what that
word runs while the snippet reports nothing wrong. Prefer shell globbing
and builtins; where a utility is unavoidable, it is `find`, or `command
<name>`. A guard tests its own inputs: the listing is asserted against a
file count before the floor is merged in, because a cached counter must
never be able to satisfy a check whose purpose is to prove the log was
read. And a snippet that spawns one process per file carries an undeclared
upper bound on the log it can read: per-file spawning degrades linearly
with a large constant (seconds for a hundred files on Linux, past a
two-minute tool timeout on Windows), so it never warns, it stops
completing. The session-start scan's counts are batched (`-exec … {} +`),
the content print and the archival sweep are one `awk` each over the
directory's glob, and the only per-file process left is the `mv` of a file
due for archival, bounded by the files due rather than by the log. Treat a
scan that does not return as a broken instrument, never as a slow one to
wait on — the BROKEN guard cannot fire for a command that never finished.

### Shell portability — bash 3.2: the `case` pattern inside `$( )` and the empty array under `set -u`

A `case` pattern inside `$( )` is written `(pattern)`, not `pattern)`:
bash 3.2 (`/bin/bash` on stock macOS) ends the substitution at the
unbalanced `)`, the block fails at parse time with `syntax error near
unexpected token ';;'`, and no guard inside it can fire. The parenthesised
form is valid in every POSIX shell and bash version; the scripts keep it.

**If you are porting the snippet or writing a new one:** run it once under
`/bin/bash` on macOS, not only under the shell your session happens to have.
`bash -n <file>` proves parsing only (safe against a snippet that would
write to the log); a `set -u` script on bash 3.2 also dies at run time on
`"${arr[@]}"` of an EMPTY array, which bash 4.4+ passes silently, and it
dies on the success path — the empty "conflicts" list a green run reports
unattended. So write every possibly-empty expansion as
`${arr[@]+"${arr[@]}"}`, wrap a command that must not receive zero
arguments in `[ ${#arr[@]} -gt 0 ]` (`git reset -q HEAD --` with no paths
resets everything), and dry-run the empty-array path before the populated
one. The shipped scripts use no arrays; the rule binds snippets written
against this skill's guidance.

### The guard line, the sweep's count and the noclobber create

The listing guard tells "the log says zero" from "I could not read the
log" (core): a command that fails to empty rather than to error would
otherwise propose id 1 in a populated log. It compares the number of ids
the glob listed with `find`'s count of prefixed files in the same two
directories, so it fires on a partial listing as well as an empty one,
and it runs on the listing alone, before the floor enters — merged into
the maximum first, the floor would let a listing broken to nothing pass.
The highest file id is kept apart from the floor for the same reason: the
new id is the larger of the two plus one, and a file maximum below the
floor is a NOTE (ids issued without a file), not a halt, because older
snippets left exactly that state behind on every run that stopped after
its floor write. The floor is written last, after the create, so a run
that creates no file — a check, a collision, a failed create — never
moves it. The sweep carries the same guard in its own right: a separate
`awk` counts the files the sweep's glob reaches, and the block halts if
that count is zero while `find` reports files present, because an
archival loop that never enters its body moves nothing and exits
successfully — without the count, "nothing was due" and "the loop never
ran" are the same output. The `noclobber` create covers the one case
per-file isolation does not ("Why this is the entire concurrency story"
below): two sessions that pick the same id *and* the same slug resolve to
one identical path, where the second writer would silently replace the
first — so write the body only after that create succeeds.

**The collision guard is keyed on the id prefix, not on the path.** A test
of `[ -e "$f" ]` — the full path, slug included — cannot catch the
collision that actually happens: two writers deriving the same number with
*different* slugs produce two different paths, both creates succeed, and
two files share one id with no error anywhere. A guard is keyed on the
invariant it protects; noclobber protects a path, the invariant is a
unique number, and a guard on the path passes every violation of the
number that uses a different slug — which is all of them. So the guard
asks whether any file with the derived prefix exists in `observation-log/`
or `archive/` (`find … -name 'NNNN-*.md'`, never a bare glob), and halts
if one does. It fires when the derivation is stale — the id came from
somewhere other than a snippet run immediately before this write — and
cannot see a writer running at the same moment, whose file does not exist
yet; the script closes that window with its number claim, the inline
snippet does not, and the review's duplicate-id check catches what slips
through. Re-run the snippet; never adjust the number by hand.

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
three inputs and the reason the command exists. If a collision happens anyway it is harmless — distinct files,
nothing lost — but should be fixed on discovery rather than left for a
review to notice: derive a correct id with the snippet, `mv` the newer file
to that prefix, and edit its `id:` frontmatter field to match. Both are
ordinary single-file operations; no other entry is touched.

**The id printed by the session-start scan is never an input to a write.**
Awareness is the wrong source for a maximum; the script (core) is the
barrier, the prefix guard the backstop where it cannot run.

### Resolve each id at its own write time

**Write the value the snippet printed.** The failure lives in the gap
between deriving the id and typing it, not in the derivation.
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
of collision, alongside a parallel session and a subagent of this session
— which inherits the same activation instruction and the same log —
and it is the only one that lives entirely inside a single agent's own
turn — which makes it the one no amount of caution about "other writers"
prevents. When several observations are due, write them one at a time, each
after the previous write has completed.

### Floor staleness — the floor below the highest active prefix

`.id-floor` is only a safety net if every issuer updates it. The
max-of-three derivation absorbs a lagging floor without a collision, so the
lag is invisible in ordinary use — until the active directory is archived
down, when a floor that lags is exactly the precondition for the counter
restarting over ids already issued. The lag is detectable: **floor < highest
active prefix means an issuer skipped the floor write**, and whatever wrote
those files did not run the snippet. The scan may assert it; the check is one
line, and it belongs after the scan's counts, before the content print:

```bash
floor=$(sed '1!d; s/[^0-9]//g' "$d/archive/.id-floor" 2>/dev/null)
top=$(for p in "$d"/[0-9]*.md; do [ -e "$p" ] && printf '%s\n' "${p##*/}"; done | grep -oE '^[0-9]+' | sort -n | tail -1)
[ -n "${floor:-}" ] && [ -n "${top:-}" ] && [ "$((10#$floor))" -lt "$((10#$top))" ] && echo "NOTE: .id-floor ($floor) below highest active id ($top) — an issuer skipped the floor write"
```

`scripts/session-start-scan.sh` does not run it (the line is optional
there); `scripts/new-observation.sh` runs the same check on every write
and corrects the floor as its own floor write. A NOTE here is evidence that
some writer bypassed the snippet — log that as the observation, not the
number.

### A structural probe that comes back empty is a stop signal

**A structural probe that comes back empty where content existed before is
a stop signal, not a create.** If the directory or file you logged to
earlier in the session is suddenly missing, or the id check returns empty
in a log you know is populated, HALT and re-probe the structure (is there
an `observation-log/`? a `log.md.migrated`?) — a parallel session may have
migrated or reorganised the storage. Never let an append silently recreate
a missing target: that converts a migration signal into corruption (see
`migration.md` on coexistence with live sessions). A writer's model of
shared mutable state is only as fresh as its last read. An empty read
over content you know exists is the same signal ("An empty scan over a
non-empty log is a broken command", above).

### Why this is the entire concurrency story

Because every observation lives in its own file, a new observation never
touches another entry's bytes, so it cannot truncate, overwrite or renumber
anyone else's work: per-file isolation removes the overwrite and
lost-write failure modes of a shared file. In the rare case two
parallel sessions pick the same id, the result is two files sharing a
number — harmless, distinct files, nothing lost, as long as the slugs
differ; the script's number claim prevents it for runs at the same moment,
the snippet's prefix guard catches it at write time when the
derivation is stale, an identical id AND slug is one path, which is what the
`noclobber` create guards against, and the review's duplicate-id check (Step
1, re-run at Step 6) renumbers whatever slips past both and logs a
meta-observation.

**The bounded-mutation discipline outlived the single-file log.** It was
written for `log.md` and it applies to every deletion or replacement the
agent makes in any multi-entry text file — a handoff document, a numbered
list, a review report, a manifest. Locate the target by its own boundaries
(the item's first line and the next item's first line), never by
surrounding whitespace or a greedy pattern: a `\n\n` "paragraph" boundary
around one item of a numbered list ran to the end of the list and deleted
every item after it.
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
The same holds for a hand-maintained ledger or manifest read to judge an
artefact against it — excerpt to find an entry, full text to judge one
(`weekly-review.md`, "Staged-work reconciliation gate").

**A change you did not make resolves an observation point by point,
never title against title** (core, Acting on Observations). A point
that joins several conditions (A and B) counts as one point per
condition — a line that matches the second half does not cover the
first. Holding the fix's title against the observation's title measures
the overlap of two headings, not coverage of the content, and the
uncovered remainder leaves every queue, because the entry is marked
resolved.

## Editing an existing observation

Core rule (How to Log); re-read first — a parallel review may have
resolved it — and never rewrite a file you don't own.

**An appended instance is a test input for the entry's predicate.** The
restatement path (core, "Check for a restatement before writing") is the
one moment a session holds the literal failing string together with the
fix the entry proposes; nothing else puts the two against each other, so
each appended instance re-cites the fix with the weight of one more
confirmation while the number of times it was run stays at zero. When
you append an instance and the entry proposes a predicate, or quotes a
command, run it on the new instance's literal string and note in the
appended text whether it matched. A miss is the finding: correct the
Suggested improvement in the same edit, and add the run to
`commands_verified:`. Repeating a prescription is not testing it.

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
editing tool everywhere else. Where the editing tool refuses to write a
file it has not read in the session, read the skeleton the create just
made before writing the body: the refusal is keyed on that state, and it
reads like a harness fault rather than a consequence of the create. A quoted heredoc is exact only where the
shell receives the command as typed; on a host whose shell tool rewrites
it in transit (`environments.md`, "Windows hosts: what reaches the shell
and the file"), the body goes through the editing tool. Where the shell is that only path, write the
whole file with a QUOTED heredoc: quoting the delimiter disables every
substitution, so the body cannot carry variables — the id and the date go in as
the literal placeholders `__ID__` and `__DATE__`, which `scripts/new-observation.sh --body <file>` replaces everywhere on its create (the body file is read as data, so a backticked path survives); with the inline snippet and no helper, `printf` the frontmatter and append a quoted-heredoc body —

```bash
cat > "$tmp/body.md" <<'OBS'    # frontmatter and body; __ID__ / __DATE__ where the id and date belong
**Issue:** … `find -exec` … $(date) … written literally, none of it run; #__ID__ on __DATE__
OBS
bash "<skill directory>/scripts/new-observation.sh" --body "$tmp/body.md" <slug> "[ABSOLUTE PATH]"
```

The same rule covers `echo -e` and any `"$(cat <<…)"` form. Exit code 0
is not evidence: the unquoted form creates the file, produces valid
Markdown with a parsing header, and the scan reports it healthy, so the
damage is in the body that nothing reads until a review opens it.

If a shell write happened anyway, **verify the file in the same turn,
before doing anything else**: `file "$f"` or a `grep -c ''` that does not
answer "Binary file matches", and a re-read of the body — one that came
out shorter than you wrote, or that contains a command's output where
the explanation was, is the heredoc failure. Checking later means
checking never.

**A declined entry records a verdict; without its premise the verdict
cannot be revisited.** `declined` means someone judged an alternative
unworkable, and that judgement is a factual claim which can be wrong — in
which case it silently vetoes the better solution forever, because every
later reader finds the decision already made. So a `resolution:` on a
declined entry carries **the evidence, not only the verdict**: what was
examined (file, line, command, output), and what would have to be true for
the decline to be wrong. And re-reading a declined entry obliges you to
check that its premise still holds before relying on it — a decline is the
one status whose correctness nothing downstream ever tests.

## The `parked` status — decided, not pending

**`parked` means decided, not pending.** Use it when an observation is
sound but cannot be acted on until an external precondition is met — the
scheduled task that produced it is disabled, the tool it describes is out
of use, a dependency has not landed. What a parked entry is (out of the
work queue, never re-escalated, never archived, back to `open` and queued
when its `parked_until:` condition is met) and why the decision belongs in
`status:` rather than a free-text note: Frontmatter fields, `parked` and
`parked_until`, above. Before parking, check the condition for whether it
can happen at all: ask who or what would have to act to meet it, and
whether that party has a reason to do exactly the opposite (sometimes as
the intended effect of the very thing the entry is waiting to observe).
If the condition cannot occur, the entry is not waiting: close it on the
substitute evidence available today, or park it on a trigger that can
actually fire — phrased on the result in the target, never on the state
of a vehicle ("A park condition names the result, never your own
vehicle", above).

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
observation is an *untracked* file until someone commits it, and `git
clean` exists to delete exactly those — and these commands get run
reflexively as housekeeping, when a continuously written log is almost
always what makes the tree dirty. Rules: before any git operation that can
discard working-tree state, copy `observation-log/` somewhere outside the
repository, and afterwards confirm every file this session wrote still
exists, re-creating from the copy if not. **Prefer committing pending
observations over reverting them** — when the dirt in the tree is the
log, a commit is always the cheaper way to get clean. Scope any dirty-tree
guard to exclude `skill-observations/` rather than teaching sessions to
clear it, and never run `git clean` with that directory in scope.

**A log synced between two installs is a multi-writer log with no shared
read.** The id snippet takes the maximum over the files this install can
see; ids another install has minted and not yet pushed are not unread,
they are absent, so both mint from their own maximum and every guard on
either side passes honestly. And
`.id-floor` is one file recording a per-writer fact, so it merges as a
conflict between two correct values: resolve it upward, never by picking
a side. Two installs sharing a log through a repository serialise their
writes through it — pull before every write, push after it — and treat
a collision found at the next review as the expected cost of a missed
pull, renumbered exactly as Step 1 says; ownership of the file is not a
condition.

## Archival

Rules: core, Archival on Write. The sweep's date check fails closed, so a
resolved file with no readable `resolved:` date is skipped; the one-field
repair is a separate edit.

**`parked` never archives**: it is not resolved and carries no `resolved:`
date — never stamp one on it to tidy it away (The `parked` status, above).

Archival is a set of plain `mv` operations, one file at a time. Moving one
resolved file cannot affect any other observation. The safe form is the
sweep as shipped — one `awk` pass over the directory's `*.md` names the
stale resolved files, and the loop behind it moves only the name it was
just handed; a moved file lands in `archive/`, which the glob never
descends into. To archive without writing an observation (the review's
Step 1), run that sweep block on its own, from `today=` through the `mv`
loop. A header with no closing `---` is never archived: the pass decides
at the closing line, which such a file does not have. Do not
improvise a bulk move; where one is unavoidable, two rules:

**Read the set once.** Either a single enumeration drives the moves, as
the sweep does, or the full candidate list is written to a file or a
variable before the first `mv`. Never run a second read of the directory
— a `grep` over its files, a separate glob expansion, a listing — while
the move is in progress: whether that reader hits files the mover has
already moved depends on which stage is ahead, and its "No such file or
directory" errors have the same shape as data loss.

**Verify a bulk move by conservation**, not by an existence probe: the
total across `observation-log/` and `archive/` is unchanged by a move.
`ls` with several arguments aggregates its exit code — it exits non-zero
if ANY argument is missing, and after a move the active copies are
missing by design — so "each file exists in active OR archive" tested
with one `ls` reports every file missing. If an existence probe is
needed, make one call per path.

```bash
d="[ABSOLUTE PATH]/skill-observations/observation-log"
total() { echo $(( $(find "$d" -maxdepth 1 -name '[0-9]*.md' | wc -l) + $(find "$d/archive" -maxdepth 1 -name '[0-9]*.md' | wc -l) )); }
before=$(total)
# ... the moves ...
after=$(total)
if [ "$before" -ne "$after" ]; then echo "ARCHIVAL CONSERVATION BROKEN: $before -> $after"; exit 1; fi
```

Compare a `resolved:` date to today portably (ISO dates sort lexically):

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

Rules: core, Referencing Observations. In chat, every surfaced id reads
`observation NNNN` — in a review offer, a checkpoint summary, a status
line — never a bare number, which the user cannot tell from a count.

**Cite the id where the fix lands.** A commit message or code comment that
applies an observation names its id (`observation #<id>`, qualified by
workspace where several logs exist). The fix is then findable without
guessing its wording: it is the second surface the review's presence check
searches (`weekly-review.md`, Step 3).

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
separate act of memory.

**A claimed write is not a write.** Every rule above binds on the write;
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
load leaves an artefact in the transcript — which discharges the felt
obligation, so a session that loaded and then ran nothing looks from
outside exactly like one that did both. The appended `checkpoints.log`
line is the protocol's own trace, for the same reason the checkpoint rule
is a write: a step whose value lies in happening at a specific moment needs
its own entry in the tool record. (Where the workspace prices every write —
the exception under "How to Log" — fold this line into the session's first
write instead.) Read the scan's output whole. Its finding lines (NOTE,
LOST ENTRIES, UNFILLED, GAP) and counts come first and the entry headers last, with
one `end of scan` line closing it that repeats the counts and the number
of finding lines; `tail`, `head` or a `grep` hides exactly the lines that
matter while the checkpoint line still lands and the log looks
compliant. A truncated scan is a skipped one.

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
