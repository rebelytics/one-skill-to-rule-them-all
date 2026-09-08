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
| *(always)* | `migrated_from: "<file>#<header number>"` — provenance, so a renumbered entry still says where it came from |
| *(resolved entries)* | `siblings_checked: "not checked — migrated from <file> …"` — the field 3.2.0 requires, stated as what it is; an OPEN entry keeps it absent so the review's sibling backfill still fires |

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
     --overrides overrides.json --archive-resolved
   ```

   `--archive-resolved` writes entries that are resolved with a date to
   `observation-log/archive/` directly, where the v3 layout keeps them;
   without it every entry lands in the active directory and the first
   archival sweep moves them. The script refuses to overwrite a file that
   already exists at the target id, and it never lowers an existing
   `.id-floor` — a second run into a populated log can only raise it.

6. **Verify.** The report's file count must equal the number of
   `### Observation` headers in `log.md`:

   ```bash
   grep -c '^### Observation' skill-observations/log.md
   ls skill-observations/observation-log/*.md skill-observations/observation-log/archive/[0-9]*.md | wc -l
   ```

   The second count spans both directories because `--archive-resolved`
   writes resolved entries under `archive/`; on a target that already held
   files, subtract what was there before the run.

   Spot-check three files against their originals, including one that was
   resolved and one that carried a qualifier.
7. **Convert the legacy archives too, then retire every converted file.**
   An archive that stays monolithic is not "history nobody reads": it is
   invisible to every mechanism the per-file layout exists for. The
   per-skill check greps `skill:` and sees `**Skill:**` as nothing; the
   restatement check reads titles from files and never meets a `###
   Observation` header; an audit that cites evidence by `NNNN` id cannot
   cite an entry that has none. Measured on one adopter's log: the first
   21 observations of a project — its canonical numbering, cited from its
   configuration — sat in two daily archives, and a rule audit that counted
   incidents by id could not see them; a second incident that would have
   kept a rule stayed uncounted until a reviewer read the archive by hand.
   Run the check-only pass over the archives (step 3 already does); convert
   the ones that parse losslessly, routing resolved entries to `archive/`:

   ```bash
   before=$(ls skill-observations/observation-log/*.md skill-observations/observation-log/archive/[0-9]*.md 2>/dev/null | wc -l)
   python3 scripts/migrate-log.py --convert skill-observations/archive/*.md \
     --out skill-observations/observation-log \
     --id-floor-from skill-observations/archive --archive-resolved \
   && after=$(ls skill-observations/observation-log/*.md skill-observations/observation-log/archive/[0-9]*.md 2>/dev/null | wc -l) \
   && [ $((after - before)) -eq "$(grep -ch '^### Observation' skill-observations/archive/*.md | awk '{s+=$1} END{print s+0}')" ] \
   && for f in skill-observations/archive/*.md; do mv "$f" "$f.migrated"; done \
   && mv skill-observations/log.md skill-observations/log.md.migrated
   ```

   The chain retires nothing unless the conversion exited 0 AND the file
   count grew by exactly the number of headers converted (counted per file
   and summed — a concatenation would glue the last line of a file without
   a final newline to the next file's header and miscount): a refused
   collision or a crash leaves every archive in place, unconverted and
   still named `.md`, instead of renaming history the new layout never
   received.

   Two cases need a decision first, not a guess. **An archive whose numbering
   collides with the canonical one** (an abandoned log anchor, consolidated
   into the archive with its own `### Observation 3`) is converted in a
   separate run with an `id` override per entry — new ids above the current
   floor — so its entries keep their content and gain an address; the
   `migrated_from` field records the original file and number. **An archive
   that does not parse losslessly** (formats that changed several times,
   entries without a status) stays monolithic under
   `observation-log/archive/` with a `migration_note` in the report; that is
   the case the "would fabricate precision" caution was written for, and it
   is decided per file by the check pass, not for archives as a class.
   Keep the retired originals beside the converted files (`.migrated`) until
   a review has spot-checked three converted entries against them, including
   one that was renumbered.

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
   `references/environments.md`, leaving a pointer file at each
   abandoned location — and run this procedure once, on the surviving
   log. Only genuinely distinct observed scopes migrate separately.

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
