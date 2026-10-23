# The observation log — storage layout, scripts and rationale

Load triggers: creating the workspace or setting up the log; archiving, or verifying a bulk move; an id or a frontmatter field looks wrong or drifts; why snippets take a spaced path and run under bash; the id snippet at write time — its guard, the sweep's count or the noclobber create fires, skipping it feels reasonable, two files share an id, writes are being batched or parallelised, or a structural probe came back empty; editing an existing observation's body; setting, reviewing or unparking a parked status, or setting `reference:`; resolving, dismissing, fixing or citing an observation

The core skill carries the per-invocation rules: where the log is, how to
name and number a file, the frontmatter format, and the archival rule.
This file holds the layout in full, the helper snippets, and the reasoning
behind the rules; the load triggers above say when to open it.
The session-start scan, its guards and the checkpoint pairing are in
`observation-scan.md`; skill families, the sibling check and the carrier
pattern in `observation-families.md`.

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
- When the workspace is under version control
- Archival
- Referencing observations

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
| `next_actor` | Optional, set in the edit that appends a decision to the body: `publishing-run`, `review` or `maintainer` — who executes it next. The same edit prefixes `title:` with `DECIDED:` (core, How to Log), so a title-only scan reads the entry as settled rather than as an open question. |
| `use_evidence` | Optional, append-only block list: one line per session in which the entry was NEEDED to decide the agent's behaviour, `- YYYY-MM-DD accepted\|declined\|used — short context`. `accepted` / `declined` is the user's answer in an interactive session (core, Surfacing Protocol); `used` is an unattended run that applied it without asking. Lines are appended by the command below and never removed; a `declined` line never closes the entry. The context is a plain scalar: no `: ` and no ` #` in it — the first turns the item into a mapping, the second cuts it. The review orders its queue by the count of these lines and flags an entry with none 30 days after its `date:` as unconfirmed (`weekly-review.md`, Step 3). |
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

**Appending a `use_evidence:` line is one insert inside the header, never
a rewrite of the file.** The line goes before the header's closing `---`,
under an existing `use_evidence:` key or a new one; the verdict and the
context travel as arguments, so no shell quoting touches them, and the
command refuses a context the header cannot carry:

```bash
python3 - "<observation file>" accepted "<short context, no colon-space>" <<'PY'   # accepted | declined | used
import sys, datetime, pathlib
p, v, c = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
assert v in ("accepted", "declined", "used") and ": " not in c and " #" not in c, "verdict or context not allowed"
t = p.read_text(encoding="utf-8").split("\n"); e = t.index("---", 1)
k = next((i for i in range(1, e) if t[i].startswith("use_evidence:")), None)
if k is None: t.insert(e, "use_evidence:"); k = e; e += 1
j = k + 1
while j < e and t[j].startswith("  - "): j += 1
t.insert(j, f"  - {datetime.date.today():%Y-%m-%d} {v} — {c}"); p.write_text("\n".join(t), encoding="utf-8")
PY
```

Where no Python runs, the editing tool inserts the same line at the same
place; either way the file is re-read first, as for any status edit.

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
unparseable, most in `resolution:`, each written from a template that
carried the value unquoted.

The scan's `suspect` count is the early warning: it reports headers that
look invalid by shape — an unquoted `: `, text after a closing quote
(either style), a value opening with a backtick, `@` or `%`, an escape a
double-quoted YAML string does not define (`\x`, `\u`, `\U` need 2, 4
and 8 hex digits) — beside the file count, for the active directory and
for `archive/`, so a log drifting into this state announces itself at
session start rather than at the review that trips over it (the rules,
one per line, are commented in `scripts/session-start-scan.sh`). It is a
floor, not a parse: a `[…]` list is checked only for a colon in an
unquoted entry, a `{…}` mapping not at all, and a plain value followed by
a `# comment: x` still counts. It also misses an unterminated quote, a tab
in place of the space after a colon, a value ending in a colon or opening
with `: `, a `: ` on a continuation line, a key outside `[a-z_]+`, and an
empty value under a typed tag (`!!int`). Re-verify by running a real YAML
parse over the frontmatter of every file, not by re-reading the template.

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
load (one log: 8 suspect by the shipped scan, 0 invalid under PyYAML, 127
under Psych, all three right about the same corpus). So the rule is the
intersection: **quote any list entry that contains a colon** — `skill:
["superpowers:test-driven-development", task-observer]` — or use a block
list, where the colon is legal unquoted. `scripts/migrate-log.py` writes
the quoted form; entries written by hand from the template are the ones
to check.

The scan's `suspect` count sees this class through one rule of its own:
in a value opening with `[`, it drops every quoted string and any
trailing comment and flags what is left if it still holds a colon, so
`[plugin:name]` counts and `["plugin:name"]` does not (one accepted false
positive, `[a: b]`, which the template never produces). The count is
labelled `suspect (awk, a floor)` because it is a shape check by one
instrument and a lower bound: "8 suspect" never means "8 invalid", and
zero says nothing about a parser on the other rule. Re-verify with two
parsers, not one: a check that agrees with the parser you already trust
is the one to distrust (`skill-authoring.md`, "A verification command
that AGREES with you").

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
first-hand observation's authority, while the command itself is usually
reconstructed from memory after the fact, and nothing downstream can tell
the two apart. At logging time the session is standing in front of the
system and running it costs seconds; the authoring pre-flight in
`skill-authoring.md` runs later, often without that system. So before the
file is written, run every command the body quotes — literally, and look
at its output — and where that is not possible, mark the command
unverified in the body. Record the outcome in `commands_verified:`, one
clause per command, and the literal `none` where the body quotes no
command, for the same reason `siblings_checked:` never stays blank: only
the field makes an unrun command visible. Where the run shows the
remembered form is wrong, the body quotes the form that ran.

**A predicate the Suggested improvement proposes — a regex, a search
pattern, a condition for a hook or check — is run the same way, against
the positive case the Issue describes and one negative, before the file
is written; record both results in `commands_verified:`.** A predicate is
not a command, so "run every command" does not reach it and the field
honestly says `none`. The input matters as much as the run: a detector
run over a repository returns some output whether or not it catches the
case in hand, so the informative run is on the known positive — the
literal failing string the Issue already holds — and on one string that
must not match. A predicate that misses its positive or matches its
negative is corrected in the body before the file is written.

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
sentence; a check named now makes the second-violation escalation (core)
a promotion of something already written and tested.

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
`"${arr[@]}"` of an EMPTY array, which bash 4.4+ passes silently — and it
dies on the success path, the empty list a green run reports unattended.
So write every possibly-empty expansion as `${arr[@]+"${arr[@]}"}`, wrap
a command that must not receive zero arguments in `[ ${#arr[@]} -gt 0 ]`
(`git reset -q HEAD --` with no paths resets everything), and dry-run the
empty-array path before the populated one. The shipped scripts use no
arrays; the rule binds snippets written against this skill's guidance.

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
invariant it protects, and the invariant is a unique number. So the guard
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
three inputs and the reason the command exists. A collision that happens
anyway is harmless — distinct files, nothing lost — and is fixed on
discovery: derive a correct id with the snippet, `mv` the newer file to
that prefix, and edit its `id:` field to match; no other entry is touched.

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
both read the same maximum and mint the same number — a third source of
collision beside a parallel session and a subagent, and the only one that
lives inside a single agent's own turn. When several observations are
due, write them one at a time, each after the previous write has completed.

### Floor staleness — the floor below the highest active prefix

`.id-floor` is only a safety net if every issuer updates it. The
max-of-three derivation absorbs a lagging floor without a collision, so the
lag is invisible in ordinary use — until the active directory is archived
down, when a lagging floor is the precondition for the counter restarting
over ids already issued. **Floor < highest active prefix means an issuer
skipped the floor write** and did not run the snippet. The check is one
line, after the scan's counts and before the content print:

```bash
floor=$(sed '1!d; s/[^0-9]//g' "$d/archive/.id-floor" 2>/dev/null)
top=$(for p in "$d"/[0-9]*.md; do [ -e "$p" ] && printf '%s\n' "${p##*/}"; done | grep -oE '^[0-9]+' | sort -n | tail -1)
[ -n "${floor:-}" ] && [ -n "${top:-}" ] && [ "$((10#$floor))" -lt "$((10#$top))" ] && echo "NOTE: .id-floor ($floor) below highest active id ($top) — an issuer skipped the floor write"
```

`scripts/session-start-scan.sh` does not run it (the line is optional
there); `scripts/new-observation.sh` runs the same check on every write
and corrects the floor as its own floor write. Log the NOTE's bypassing
writer as the observation, not the number.

### A structural probe that comes back empty is a stop signal

**A structural probe that comes back empty where content existed before is
a stop signal, not a create.** If the directory or file you logged to
earlier in the session is suddenly missing, or the id check returns empty
in a log you know is populated, HALT and re-probe the structure (is there
an `observation-log/`? a `log.md.migrated`?) — a parallel session may have
migrated or reorganised the storage. Never let an append silently recreate
a missing target: that converts a migration signal into corruption (see
`migration.md` on coexistence with live sessions). An empty read over
content you know exists is the same signal (`observation-scan.md`, "An empty
scan over a non-empty log is a broken command").

### Why this is the entire concurrency story

Because every observation lives in its own file, a new observation never
touches another entry's bytes, so it cannot truncate, overwrite or renumber
anyone else's work. Two parallel sessions picking the same id leave two
files sharing a number — harmless as long as the slugs differ ("Run the
snippet immediately before every write", above);
the script's number claim prevents it for runs at the same moment, the
prefix guard catches a stale derivation at write time, the `noclobber`
create refuses the one path an identical id AND slug resolve to, and the
review's duplicate-id check (Step 1, re-run at Step 6) renumbers whatever
slips past both and logs a meta-observation.

**The bounded-mutation discipline outlived the single-file log.** It was
written for `log.md` and it applies to every deletion or replacement the
agent makes in any multi-entry text file — a handoff document, a numbered
list, a review report, a manifest. Locate the target by its own boundaries
(the item's first line and the next item's first line), never by
surrounding whitespace or a greedy pattern: a `\n\n` "paragraph" boundary
around one item of a numbered list ran to the end of the list and deleted
every item after it. Re-read the region after the edit and count what
survived against what was meant to survive.

## Read the full body before resolving, dismissing, fixing or citing

Rule: core, Acting on Observations. A tracked item's title (observation,
GitHub issue, ticket) is an index entry, not its content — it compresses
away the failure story, the reporter's context, and often the proposed
fix. Dismissal is the path with no downstream checkpoint: a resolved or
cited item gets reviewed later, a dismissed one silently disappears.
Harvest fix designs from issue bodies — reporters frequently include the
correct solution, which also settles attribution. When a parallel agent
logs a finding that appears to duplicate your own, diff the two bodies,
not the titles: two entries about the same mechanism can carry opposite
operational conclusions, and the second is often the refinement, not the
echo. Apparent agreement suppresses verification more effectively than
disagreement does, so this rule binds hardest exactly where it feels
least necessary. The same holds for a hand-maintained ledger or manifest
read to judge an artefact against it — excerpt to find an entry, full
text to judge one (`weekly-review.md`, "Staged-work reconciliation gate").

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
manifest state, and a session listing — and a **paused** session has not
released its task; it reads as idle and can resume at any moment with its
own decisions intact. So the check belongs immediately before the first
write, in the same turn (the same rule as re-reading a file before editing
it): planning-time evidence of idleness has a shelf life of exactly as long
as the planning takes. And prefer a check on **the result** — has the work
already landed in the target? — over a check on the vehicle, since a paused
session's state says nothing about what it is about to do.

**Edit log files with the editing tool — never `sed -i`, `perl -pi`, or a
redirection over the file.** No exception for a quick fix or a temporary
negative test; the temptation peaks exactly on a file with uncommitted work
and nothing to fall back to.

Rewriting a text file from the shell passes the replacement through the
shell's quoting first, and what arrives is not always what was typed: an
unescaped `$` inside a double-quoted replacement has landed in a source
file as a NUL byte, turning the file binary, with **the command exiting
0** and a later `grep` answering "Binary file matches" as the first sign.

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
When the result depends on work tracked elsewhere — a ticket, issue or
PR — read it before parking: confirm its own text names the observation
or states its fix, and quote the matching line in `resolution:`;
otherwise add the observation to that ticket, or park on another trigger.
If the condition cannot occur, the entry is not waiting: close it on the
substitute evidence available today, or park it on a trigger that can
actually fire — phrased on the result in the target, never on the state
of a vehicle ("A park condition names the result, never your own
vehicle", above).

## When the workspace is under version control

Versioning the workspace folder is good practice — it gives the rollback
the skill cares about — and it adds a mutation surface that does not look
like one. `git checkout -- <path>`, `git stash`, `git reset --hard`, a
branch switch carrying local modifications, a rebase that drops a hunk,
and above all `git clean -fd` destroy observation files as thoroughly as
any edit; the newest files are the most exposed, because a just-written
observation is an *untracked* file until someone commits it, and these
commands get run reflexively as housekeeping, when a continuously written
log is what makes the tree dirty. Rules: before any git operation that can
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
either side passes honestly. And `.id-floor` is one file recording a
per-writer fact, so it merges as a conflict between two correct values:
resolve it upward, never by picking a side. Two installs sharing a log
through a repository serialise their writes through it — pull before
every write, push after it — and treat a collision found at the next
review as the expected cost of a missed pull, renumbered exactly as Step
1 says; ownership of the file is not a condition.

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
archive filename is needed. The directory has held three generations of
layout: entries archived before the dated rollups existed, which a review
cleared in one pass and no file now holds — unrecoverable, so the id
sequence starts at the first entry a rollup kept, a scar rather than an
offset; legacy `log-YYYY-MM-DD.md` rollups from a pre-3.0 install, left
beside the per-file archive untouched, not converted (see `migration.md`)
and not scanned; and the per-observation `NNNN-slug.md` files the sweep
writes. Any enumeration of "the whole log" covers BOTH file generations,
and its count is reconciled against an independent handle — the id range,
the date range, the directory's byte total — before anything is computed
over it: a walk keyed on the current filename pattern returns a clean,
plausible, silently partial set. The review's Step 1 asserts the id
sequence contiguous across both directories (`weekly-review.md`).

## Referencing observations

Rules: core, Referencing Observations. In chat, every surfaced id reads
`observation NNNN` — in a review offer, a checkpoint summary, a status
line — never a bare number, which the user cannot tell from a count.

**Cite the id where the fix lands.** A commit message or code comment that
applies an observation names its id (`observation #<id>`, qualified by
workspace where several logs exist). The fix is then findable without
guessing its wording: it is the second surface the review's presence check
searches (`weekly-review.md`, Step 3).
