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
| `status` | `open`, `actioned`, `declined` or `superseded` (a later observation found this one's mitigation does not work; `resolution` names it). A missing status is read as `open`, never as nonexistent. |
| `type` | `open-source` or `internal` (see Taxonomy in the core skill). |
| `skill` | **Always a list**, even with one entry, so no consumer ever branches on string-vs-list. First entry is primary. May be empty. |
| `proposes_skill` | List of new-skill candidates by working name. Independent of `skill`; either may be empty, both may be filled. |
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
for f in skill-observations/observation-log/*.md; do
  awk 'NR==1 && /^---[[:space:]]*$/ {fm=1; next}
       fm && /^---[[:space:]]*$/ {print "---"; exit}
       fm' "$f"
done
```

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
