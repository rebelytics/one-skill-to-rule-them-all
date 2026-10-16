# Migrating a pre-3.0 single-file log

Load triggers: the Session Start Protocol finds a pre-3.0 `log.md` — with no `observation-log/`, or beside one (a split store)

Upgrade-only. Versions before 3.0.0 kept every observation in one file,
`skill-observations/log.md`, with `### Observation N:` headers. Version
3.0.0 stores one file per observation under
`skill-observations/observation-log/`. This reference converts the former
into the latter, once, with the bundled script. Fresh 3.0 installs never
need it; the Session Start Protocol loads it when it finds a `log.md`
and no `observation-log/` directory — or a `log.md` beside a populated
one (a SPLIT STORE: an older installed copy of the skill kept writing
the legacy file after the migration; find and retire that copy first).

The conversion is a script rather than a procedure for one reason: a
script can be run in check-only mode over every log you have and its
output verified, and re-running it gives the same result. Prose
instructions executed by an agent cannot be verified the same way.

## What the script does

`scripts/migrate-log.py` parses each `### Observation N:` block and
writes `observation-log/NNNN-<slug>.md` with YAML frontmatter:

| Legacy field | Frontmatter |
|---|---|
| `### Observation N: Title` | `id`, `title`, and the filename prefix |
| `**Status:** OPEN` | `status: open`; any trailing text becomes `status_note` |
| `**Status:** ACTIONED (date) — note` | `status: actioned`, `resolved: date`, `resolution: note` (same for DECLINED) |
| `**Date:**` | `date` |
| `**Skill:** a; b (section)` | `skill: ["a", "b"]` — always a list; per-skill qualifiers go to `skill_qualifiers` |
| `**Skill:** New skill candidate: name` | `proposes_skill: ["name"]`; `skill` stays empty unless the entry also names an existing skill it could extend |
| `**Type:**`, `**Phase/Area:**`, `**Session context:**`, `**Reference file:**` | `type`, `area`, `session_context`, `reference` |
| Everything else | Stays in the body verbatim — only the labels above are lifted |

Two rules protect the fields the format exists to make reliable:

- **The resolution date is read only from the marker region before the
  em-dash**, never from the free text after it. Resolution notes routinely
  contain dates that are not the resolution date ("applied in review
  2026-03-04"); reading the whole line invented a wrong `resolved:` value
  for hundreds of archived entries in testing.
- **Ambiguity is flagged, never guessed.** Anything the parser is not
  confident about — a missing status, a skill name it cannot parse, a
  qualifier that could apply to one name or a whole group, a qualifier
  that names another known skill (`skill-in-qualifier`, with
  `--known-skills`) — is written
  into the file as `migration_note: "needs review: …"` and listed in the
  report. You resolve those by hand or, better, through an overrides file
  so the run stays reproducible.

It also writes `observation-log/archive/.id-floor` with the highest id it
saw (across the converted log and any `--id-floor-from` directories), so
the counter continues from where the single-file log left off.

## Procedure

Run from the workspace folder. Python 3.8+, no dependencies.
`<skill directory>` below is the installed skill's own directory (the one
holding `SKILL.md`); where `python3` is not a real interpreter (on Windows
it can be the Microsoft Store alias), use `py -3`.

1. **Make sure nothing else is writing.** Close parallel sessions and
   check for a scheduled review due in the next hour. The conversion
   reads `log.md` once; an entry appended after that moment would be
   lost from the new layout. Know this probe's limit: it catches sessions
   writing NOW, not sessions that will write LATER from a stale model of
   the layout — a long-running session that appended to `log.md` hours ago
   and is idle at migration time is invisible to any liveness check, and
   its next append can recreate the old file (`cat >>` creates missing
   targets). The rename in step 7 is therefore also a guard: it makes
   stale appends fail their numbering pre-check loudly — provided
   appenders treat an empty/missing probe as a stop signal rather than
   defaulting the counter (see the log-write safety rules in SKILL.md).
   After migrating, warn any known long-running session before it next
   writes.
2. **Back up.** `cp skill-observations/log.md skill-observations/log.md.bak`
3. **Check-only pass over everything you have**, including archived logs
   you do not intend to convert:

   ```bash
   python3 "<skill directory>/scripts/migrate-log.py" --check skill-observations/log.md
   find skill-observations/archive -maxdepth 1 -name '*.md' -exec \
     python3 "<skill directory>/scripts/migrate-log.py" --check {} +
   ```

   Two invocations rather than one glob: the archive directory may not
   exist, and an unmatched `*.md` is a hard error under zsh — which would
   take the live log's check down with it, for want of files that were
   only ever optional.

   The archives are free test coverage: they contain format drift that
   current entries no longer show, and they exercise parser paths the live
   log cannot. Read the flag counts. `needs human review` is the number
   of entries that will carry a `migration_note`.
4. **Write overrides for the flagged live entries**, if any. A JSON file
   keyed by id; each value lists the flags it resolves and the fields to
   set:

   ```json
   {
     "812": {
       "_resolves": ["skill-missing"],
       "_reason": "proposes a new skill and could extend an existing one",
       "skill": ["existing-skill"],
       "proposes_skill": ["candidate-name"]
     }
   }
   ```

   Keys starting with `_` are bookkeeping; every other key overwrites that
   frontmatter field. `_reason` is recorded in the file as
   `migration_override` so the decision survives. The fields an override
   can set are the ones the script writes: `skill`, `proposes_skill` and
   `target_file` (lists of strings); `title`, `status`, `type`, `area`,
   `date`, `session_context`, `resolved`, `resolution`, `status_note`,
   `reference`, `siblings_checked`, `parked_until` and
   `commands_verified` (strings); and `skill_qualifiers` (an object). Any
   other key, or a value of the wrong shape, stops the run with exit 2
   before a file is written, naming the entry and the key: an override
   that is accepted and never reaches the file is the one outcome the
   check exists to rule out.
5. **Convert the live log:**

   ```bash
   python3 "<skill directory>/scripts/migrate-log.py" --convert skill-observations/log.md \
     --out skill-observations/observation-log \
     --id-floor-from skill-observations/archive \
     --known-skills "<skills directory>" \
     --overrides overrides.json
   ```

   `<skills directory>` is the directory holding the installed skills,
   one folder each. Without it the script cannot tell a skill name from
   other words, so it can neither flag an unknown `skill:` entry nor a
   second skill named inside a qualifier; pass it to the step 3 check of
   the live log too.

   **A split store is never converted into the populated directory.** The
   converted files keep their legacy ids and the script overwrites a
   same-named file, so a `log.md` written beside an existing
   `observation-log/` is converted into a scratch `--out` directory, and
   each converted file is then created in the live one through
   `scripts/new-observation.sh --body <file> <slug>` with its `id:` line
   replaced by `__ID__` first — the id is re-issued from the directory's
   counter, never carried over, and the legacy number goes into the body
   as "migrated from log.md #N" so a citation of it can still be traced.

6. **Verify twice: source fidelity, then target conformance.** The
   report's file count must equal the number of `### Observation` headers
   in `log.md`:

   ```bash
   grep -c '^### Observation' skill-observations/log.md
   find skill-observations/observation-log -maxdepth 1 -name '*.md' | wc -l
   ```

   Spot-check three files against their originals, including one that was
   resolved and one that carried a qualifier, and compare every converted
   `skill:` line with its legacy `**Skill:**` header: a skill named only
   inside a qualifier is a target the scans, review buckets and family
   checks cannot see. Then read the report's
   `target conformance` block, and confirm it from the files: a converted
   set is faithful to a source that never had `siblings_checked`, so every
   file lacks it unless an override set it, and nothing but the next
   review's sibling backfill will add it. Enumerate the fields from the
   target's own definition (SKILL.md, File format), never from the mapping
   table above — a field absent from the table is indistinguishable from
   one absent from the schema:

   ```bash
   o="skill-observations/observation-log"
   n=$(find "$o" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')
   for field in status siblings_checked; do
     have=$(find "$o" -maxdepth 1 -name '*.md' -exec grep -l "^$field:" {} + | wc -l | tr -d ' ')
     echo "$field: $have/$n"
   done
   ```

   A count below `n` for `siblings_checked` is expected and is the state
   the first review clears; a count below `n` for `status` is a converter
   defect — report it.
7. **Move legacy archives under the new layout** so one directory holds
   the whole history, and retire the old file so nothing scans it:

   ```bash
   find skill-observations/archive -maxdepth 1 -name '*.md' \
     -exec mv {} skill-observations/observation-log/archive/ \;
   rmdir skill-observations/archive 2>/dev/null
   mv skill-observations/log.md skill-observations/log.md.migrated
   ```

   `find` again, for the same reason as step 6, plus one of its own: a
   bare `mv …/*.md` that matches nothing passes the literal pattern to
   `mv` under bash, which then fails with a confusing "No such file" —
   and under zsh it aborts before `mv` runs at all. The `rmdir` is
   allowed to fail: a directory that still holds something is a signal to
   look, not a reason to stop the migration.

   Legacy archives stay in their monolithic format. They were written
   under conventions that changed several times; converting them would
   fabricate precision the records never had, and nothing reads them on a
   normal turn.

8. **Enumerate the machine's other workspaces before recording the
   migration anywhere.** Everything above converts exactly one workspace
   folder. When the skill is installed at user/global scope, other
   workspaces may hold their own `skill-observations/` anchor still on
   the legacy layout. Search wherever your workspace folders anchor —
   both supported layouts, the identity root and a managed persistence
   directory under it (`references/environments.md`), which is why the
   search is not depth-bounded. In Claude Code, for example:

   ```bash
   find ~/.claude/projects -name log.md -path '*/skill-observations/*'
   ```

   **Ask the scope question before converting a hit.** Several legacy
   logs that observe the same globally installed skills are not several
   scopes; they are the silent fork this skill warns about ("globally
   installed skills need one path shared across projects, tools and
   agents"). Converting each in place preserves that fork, with two id
   spaces that already collide. Consolidate those onto one anchor first
   — per "Before creating a log, search for one" in
   `references/environments.md`, leaving a pointer file,
   `skill-observations/MOVED.md`, at each abandoned root — and run this
   procedure once, on the surviving log. Only genuinely distinct observed scopes migrate separately.

   **Every live `log.md` needs reconciling, including one that sits
   beside an `observation-log/`.** That pair is not a converted
   workspace: it is a conversion that stopped before step 7, or a stale
   pre-3.0 session that recreated the retired file. Nothing else catches
   it — the Session Start Protocol migrates only when `observation-log/`
   is absent — so entries unique to that file are never imported and
   never scanned. Run the check-only pass over it, convert what the
   directory is missing, and retire the file as in step 7; or list it
   explicitly as pending.

   A cleanly unconverted workspace (a `log.md` with no
   `observation-log/`) loses no data if you skip it — the Session Start
   Protocol still catches that case lazily, on its next session there —
   but "lazily" can be days, and nothing marks it as unconverted in the
   meantime.

   The same scope rule applies to the record of the migration: a
   completion note written into a document that reaches beyond one
   workspace — a machine-global CLAUDE.md, a team runbook — must name the
   workspace(s) it covers, because "migration done" in a global document
   reads as "done everywhere" to every future reader.

9. **Re-check anything that mentions the old path.** Other skills, a
   CLAUDE.md, a scheduled task or a review template may name
   `skill-observations/log.md`. Point them at the directory; "the
   observation log" as a phrase stays correct.

## Rollback

`mv skill-observations/log.md.migrated skill-observations/log.md` and
reinstall the previous skill version. The per-file directory can stay; a
pre-3.0 skill ignores it. Anything logged after the cutover exists only
as files, so append those to `log.md` by hand if you roll back after
real use.
