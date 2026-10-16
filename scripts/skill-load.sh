#!/usr/bin/env bash
# skill-load.sh — the last step of loading a skill, as one command: the
# per-skill lookup of OPEN observations and the checkpoint line that records
# it.
#
# Usage:
#   bash scripts/skill-load.sh <workspace-root> <skill-name>
#
#   <workspace-root>  the pinned absolute workspace path — the directory that
#                     holds skill-observations/. Never resolved from the cwd;
#                     the path may contain spaces.
#   <skill-name>      the skill whose Skill invocation rides in THIS batch, as
#                     the listing shows it (`plugin:name` allowed), OR the
#                     file name of an agent definition or instructions file
#                     a delegate is about to be briefed under (`reviewer.md`;
#                     a path is reduced to its file name). The match is on
#                     the bare name — the part after the last `:` and the
#                     last `/` — on both sides, against the `skill:` AND
#                     `target_file:` fields, so a plugin-qualified listing
#                     finds entries that name the bare skill and vice versa,
#                     and a file name finds the entries filed under that
#                     file by any path; never on a prefix: `foo` does not
#                     match `foo-extras`, and `reviewer` does not match
#                     `reviewer.md`.
#
# Prints, on stdout: one line `<skill-name>: N open observations`, then the
# matching file names, one per line (read their bodies next). Appends one
# line to skill-observations/checkpoints.log:
#   YYYY-MM-DD HH:MM loaded <skill-name> — N open observations
#
# Exit status:
#   0  the lookup ran (N may be 0) — or no log exists yet under an existing
#      root (a first run: the load batch precedes Session Start step 1,
#      which creates the log). That case prints one NOTE line naming the
#      missing log, writes nothing (there is no checkpoints.log to write
#      to) and is not "0 open": re-run the lookup once for each skill
#      loaded in that batch after the Workspace creation command has run
#   1  LOOKUP BROKEN — entries exist but no header parsed, or the lookup
#      stage itself exited with an error; nothing is written to
#      checkpoints.log, because "0 open" from a command that read nothing
#      is the one result nobody questions
#   2  refused: missing arguments, a relative root, a root that does not
#      exist, a pre-3.0 log.md with no observation-log/ beside it, or a
#      skill name with characters outside [A-Za-z0-9:._/-]
#
# Why a script: a rule about what a tool batch must CONTAIN cannot be
# enforced by prose inside the thing the batch loads — the agent reads the
# prose only after the batch is committed. One call carrying both the lookup
# and the checkpoint line, emitted beside the Skill invocation, leaves a
# record a review can match against the invocation afterwards.
#
# Why no grep | xargs: file names are handed from find to awk with
# `-exec … {} +`, never through a pipe, so a spaced path cannot split. (The
# null-delimited `grep -Z | xargs -0` form is not portable: BSD grep, as on
# macOS, reads -Z as "decompress", and the pipe then splits on newlines
# again.) awk reads only the frontmatter, so a body that mentions a skill
# name is not a match.
#
# bash 3.2-compatible (stock macOS): case patterns are parenthesised, no
# bash-4 expansions.

set -u

root="${1:-}"
name="${2:-}"

if [ -z "$root" ] || [ -z "$name" ]; then
  echo "usage: bash skill-load.sh <workspace-root> <skill-name>" >&2; exit 2
fi
case "$root" in
  (/*|[A-Za-z]:[/\\]*) ;;
  (*) echo "workspace root must be an ABSOLUTE path, never relative to the cwd: got '$root'" >&2; exit 2 ;;
esac
case "$name" in
  (*[!A-Za-z0-9:._/-]*) echo "skill name may hold only [A-Za-z0-9:._/-]: got '$name'" >&2; exit 2 ;;
esac

# Every expansion of $root and $d stays double-quoted: the pinned path
# routinely contains a space.
d="$root/skill-observations/observation-log"
if [ ! -d "$d" ]; then
  # A missing log under a missing root is a wrong pin; under a pre-3.0
  # log.md it is an unmigrated install; under an existing root it is the
  # first run, where this call rides in the batch BEFORE step 1 creates
  # the log — reported, not refused, so the first load is not a failure
  # and the re-run after step 1 writes the checkpoint line.
  if [ ! -d "$root" ]; then
    echo "workspace root does not exist: '$root' — check the pinned path" >&2; exit 2
  fi
  if [ -e "$root/skill-observations/log.md" ]; then
    echo "LEGACY log.md under '$root/skill-observations' and no observation-log/ — run the migration (references/migration.md) first" >&2; exit 2
  fi
  echo "NOTE: $name: no observation log yet at '$d' — a first run, before Session Start step 1 creates it; not 0 open. Re-run this lookup once for each skill loaded in this batch after the Workspace creation command"
  exit 0
fi

# One awk over every entry. Per file: H <file> when the header closes (the
# parse count), M <file> when the header names the skill AND is open — the
# review's OPEN set: any status other than actioned, declined, superseded or
# parked, a missing status included. `skill:` and `target_file:` are read in
# all three shapes the log uses: an inline [a, "b"] list, a plain scalar,
# and a block list of `- a` lines below it. bare() strips a plugin
# qualifier and a path, so both fields compare on the last segment.
prog='function bare(t) { sub(/.*:/, "", t); sub(/.*\//, "", t); return t }
  function tok(t) {
    gsub(/^[[:space:]"\047]+|[[:space:]"\047]+$/, "", t)
    return t != "" && bare(t) == bare(want)
  }
  FNR == 1 { fm = 0; sk = 0; rs = 0; inl = 0; sub(/^\357\273\277/, "")
             if ($0 ~ /^---[[:space:]]*$/) { fm = 1; next } else nextfile }
  fm && /^---[[:space:]]*$/ { print "H " FILENAME; if (sk && !rs) print "M " FILENAME; nextfile }
  fm && /^(skill|target_file):/ { v = $0; sub(/^(skill|target_file):[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v)
                    inl = (v ~ /^[[:space:]]*$/); gsub(/[][]/, "", v)
                    n = split(v, a, ","); for (i = 1; i <= n; i++) if (tok(a[i])) sk = 1
                    next }
  fm && inl && /^[[:space:]]+-[[:space:]]/ { v = $0; sub(/^[[:space:]]+-[[:space:]]*/, "", v); if (tok(v)) sk = 1; next }
  fm && /^[A-Za-z_]/ { inl = 0 }
  fm && /^status:[[:space:]]*["\047]?(actioned|declined|superseded|parked)["\047]?[[:space:]]*(#.*)?$/ { rs = 1 }'

out=$(LC_ALL=C find "$d" -maxdepth 1 -name '*.md' -exec awk -v want="$name" "$prog" {} +)
stage=$?
files=$(find "$d" -maxdepth 1 -name '*.md' ! -empty | wc -l | tr -d ' ')
parsed=$(printf '%s\n' "$out" | grep -c '^H ')
matches=$(printf '%s\n' "$out" | sed -n 's|^M .*/||p' | LC_ALL=C sort)
count=0; [ -n "$matches" ] && count=$(printf '%s\n' "$matches" | wc -l | tr -d ' ')

# The guard: entries present and nothing parsed is a broken command, not an
# empty backlog.
if [ "$stage" -ne 0 ]; then
  echo "LOOKUP BROKEN — the lookup stage exited $stage (errors above); nothing written to checkpoints.log"; exit 1
fi
if [ "$files" -gt 0 ] && [ "$parsed" -eq 0 ]; then
  echo "LOOKUP BROKEN — $files entries present, 0 headers parsed; nothing written to checkpoints.log"; exit 1
fi

printf '%s: %s open observations\n' "$name" "$count"
[ -n "$matches" ] && printf '%s\n' "$matches"

printf '%s loaded %s — %s open observations\n' "$(date '+%F %H:%M')" "$name" "$count" \
  >> "$root/skill-observations/checkpoints.log"
exit 0
