# The observation log — storage layout, scripts and rationale

The core skill carries the per-invocation rules: where the log is, how to
name and number a file, the frontmatter format, and the archival rule.
This file holds the layout in full, the helper snippets, and the reasoning
behind the rules. Load it when setting up the directory for the first
time, when archiving, when something about ids or frontmatter looks wrong,
and before changing how any other tool or skill reads the log.

## Layout

```
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
| `siblings_checked` | **Mandatory, never blank.** Records that the sibling check happened and what it concluded: the family name, the members evaluated, and the verdict (propagated / instance-specific). `none` only where the target belongs to no family. Missing or empty = logged without a sibling check, and reviews count it as such. |
| `area` | The part of the skill or workflow concerned. |
| `date` | Date logged, `YYYY-MM-DD`. |
| `session_context` | What was being worked on. |
| `resolved` | Resolution date; set only when status is `actioned` or `declined`. Archival is gated on it. |
| `resolution` | What was done, or why declined. |
| `reference` | Optional path to saved session-local evidence. |
| `skill_qualifiers` | Optional map: skill name → the section or part of that skill meant. |
| `migration_note` | Present only on files converted from a legacy log where the converter refused to guess; clear it once reviewed. |

## Scanning cheaply

Read only the frontmatter — the header block between the first two `---`
lines — never the bodies. This is what keeps the session-start scan and
the review's work-queue pass cheap once hundreds of observations exist:

```bash
d=skill-observations/observation-log                                # re-derive in EVERY call
n=$(ls skill-observations/observation-log/*.md 2>/dev/null | wc -l) # literal path: independent of $d
parsed=0
for f in "$d"/*.md; do
  [ -e "$f" ] || continue
  hdr=$(awk 'NR==1 && /^---[[:space:]]*$/ {fm=1; next}
             fm && /^---[[:space:]]*$/ {exit}
             fm' "$f")
  [ -n "$hdr" ] && parsed=$(( parsed + 1 ))
  printf '%s\n---\n' "$hdr"
done
[ "$n" -gt 0 ] && [ "$parsed" -eq 0 ] && \
  { echo "SCAN COMMAND BROKEN — $n files present, 0 headers parsed"; exit 1; }
```

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

**Snippets spanning several tool calls must re-derive their own paths.**
Shell state does not carry between tool calls in most harnesses, so a
variable defined in an earlier call is empty in the next one — and an
empty path variable does not error, it expands the glob to `/*.md` and
matches nothing. A filter silently becomes a match-nothing filter. Every
snippet here defines the paths it uses in the same invocation that uses
them; keep that property when adapting them.

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

The `skill:` field is already a list, so multi-skill observations are
expressible. The mechanism exists; the *check* does not — and a list field
with no rule to populate it collapses to a single value. Four parts, in
increasing cost:

**1. Declare the families —** `skill-observations/skill-families.md`. One
entry per family, with the members, and the load-bearing second column:
**what is shared versus what is legitimately member-specific.** Without
that column every observation looks like it might apply everywhere and the
check generates noise instead of signal. Record each family's *coherence
model* too, because it decides what "fixing drift" means:

| Coherence model | Meaning | Fixing drift means |
|---|---|---|
| `synced-duplicates` | each member is self-contained (e.g. published standalone) and shared sections are kept in sync | edit every member |
| `shared-core` | one skill holds the common material; the others load it as a companion | edit the core once, check the pointers |

```markdown
## [family name]
**Members:** skill-a, skill-b, skill-c
**Coherence model:** synced-duplicates | shared-core
**Shared:** [the material every member should carry]
**Member-specific:** [what legitimately differs, and why]
```

Duplication is sometimes correct and absence is not always drift — that is
exactly what the shared/member-specific split records.

**2. Logging-time check** (SKILL.md, "How to Log"). Before writing an
observation, resolve the target against the registry. If it belongs to a
family, evaluate each sibling and either add it to `skill:` or state in the
body why it does not apply. **No registry yet, or the target is not in
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
it whenever you issue an id above it.

```bash
d=skill-observations/observation-log
hi=$( { ls "$d" "$d/archive" 2>/dev/null | grep -oE '^[0-9]+'; cat "$d/archive/.id-floor" 2>/dev/null; } \
     | sort -n | tail -1); : "${hi:=0}"
[ "$hi" -eq 0 ] && [ -n "$(ls "$d"/*.md 2>/dev/null)" ] && { echo "ID COMMAND BROKEN — log is non-empty but no ids extracted"; exit 1; }
next_id=$(( hi + 1 )); echo "$next_id" > "$d/archive/.id-floor"
printf '%04d\n' "$next_id"     # filename prefix
```

`ls`, `grep -oE`, `sort -n` and `printf` are POSIX; the snippet runs
unchanged on macOS, Linux and Git Bash. A skill that hands the agent a
shell command owns that command's portability: lead with the portable
form, never offer it as a footnote the agent reaches for after the primary
has failed — and make any command that derives a number from a file fail
loudly on an empty result, because a command that fails to empty rather
than to error may never announce that it failed at all.

**Run the snippet once per file when writing a batch.** Appending several
observations in one session that may overlap a scheduled review or another
writer means N separate id races, not one. Pre-computing a base and
hardcoding sequential numbers (e.g. into a multi-entry heredoc) collapses
those N independent max-checks into a single stale read — a parallel
writer's id issued between the check and the write turns the whole batch
into duplicates. Resolve each entry's id against the live directory at the
moment of its own write, and run a post-write per-number count when
overlap is plausible.

**An empty probe over a populated log is a migration signal, not a zero.**
If a structure you wrote to earlier in the session has vanished — the
directory is missing, the id extraction returns empty where ids existed —
stop and re-probe the layout (`observation-log/` present? a
`log.md.migrated` tombstone?) before writing anything. A parallel session
may have migrated or reorganised the storage; a writer's model of shared
mutable state is only as fresh as its last read. Append paths must fail
loudly on a missing target, never silently create it — auto-creation
converts the signal into corruption (see `migration.md` on coexistence
with live sessions). **This rule covers reads as well as writes.** A
retrieval that comes back empty over content you know exists — the
session-start scan, a filter for observations naming the current skills, a
grep for a prior finding — is the same signal wearing different clothes,
and it is more dangerous, because a broken read produces no error and its
result ("nothing relevant") is a legitimate possible answer. Re-probe
before acting on it (see "Guard the read, not just the write" above).

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
number — harmless, distinct files, nothing lost; the next review renumbers
one and logs a meta-observation.

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

On every write, first move already-resolved files from `observation-log/`
to `observation-log/archive/`. "Already resolved" is decided by the file's
own frontmatter: `status: actioned`, `declined` or `superseded` AND a
`resolved:` date before today. Files resolved today stay until the next
day, no matter which session resolved them — the grace period lives in the
file, never in session memory, so it holds across parallel and subsequent
sessions. A resolved file with no readable `resolved:` date gets today's
date written to that field instead of being archived.

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
