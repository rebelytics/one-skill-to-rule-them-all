# Migrating a pre-3.0 single-file log

Upgrade-only. Versions before 3.0.0 kept every observation in one file,
`skill-observations/log.md`, with `### Observation N:` headers. Version
3.0.0 stores one file per observation under
`skill-observations/observation-log/`. This reference converts the former
into the latter, once, with the bundled script. Fresh 3.0 installs never
need it; the Session Start Protocol loads it only when it finds a
`log.md` and no `observation-log/` directory.

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
  qualifier that could apply to one name or a whole group — is written
  into the file as `migration_note: "needs review: …"` and listed in the
  report. You resolve those by hand or, better, through an overrides file
  so the run stays reproducible.

It also writes `observation-log/archive/.id-floor` with the highest id it
saw (across the converted log and any `--id-floor-from` directories), so
the counter continues from where the single-file log left off.

## Procedure

Run from the workspace folder. Python 3.8+, no dependencies.

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
   python3 scripts/migrate-log.py --check \
     skill-observations/log.md skill-observations/archive/*.md
   ```

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
   `migration_override` so the decision survives.
5. **Convert the live log:**

   ```bash
   python3 scripts/migrate-log.py --convert skill-observations/log.md \
     --out skill-observations/observation-log \
     --id-floor-from skill-observations/archive \
     --overrides overrides.json
   ```

6. **Verify.** The report's file count must equal the number of
   `### Observation` headers in `log.md`:

   ```bash
   grep -c '^### Observation' skill-observations/log.md
   ls skill-observations/observation-log/*.md | wc -l
   ```

   Spot-check three files against their originals, including one that was
   resolved and one that carried a qualifier.
7. **Move legacy archives under the new layout** so one directory holds
   the whole history, and retire the old file so nothing scans it:

   ```bash
   mv skill-observations/archive/*.md skill-observations/observation-log/archive/
   rmdir skill-observations/archive
   mv skill-observations/log.md skill-observations/log.md.migrated
   ```

   Legacy archives stay in their monolithic format. They were written
   under conventions that changed several times; converting them would
   fabricate precision the records never had, and nothing reads them on a
   normal turn.

8. **Re-check anything that mentions the old path.** Other skills, a
   CLAUDE.md, a scheduled task or a review template may name
   `skill-observations/log.md`. Point them at the directory; "the
   observation log" as a phrase stays correct.

## Rollback

`mv skill-observations/log.md.migrated skill-observations/log.md` and
reinstall the previous skill version. The per-file directory can stay; a
pre-3.0 skill ignores it. Anything logged after the cutover exists only
as files, so append those to `log.md` by hand if you roll back after
real use.
