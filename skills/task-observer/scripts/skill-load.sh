#!/usr/bin/env bash
# skill-load.sh — the last step of loading a skill, as one command: the
# per-skill lookup of OPEN observations and the checkpoint line that records
# it.
#
# Usage:
#   bash scripts/skill-load.sh <workspace-root> <skill-name>
#   bash scripts/skill-load.sh <workspace-root> <skill-name> --correct "<reason>"
#   bash scripts/skill-load.sh <workspace-root> <skill-name> --query-only
#
#   <workspace-root>  the pinned absolute workspace path — the directory that
#                     holds skill-observations/. Never resolved from the cwd;
#                     the path may contain spaces.
#   <skill-name>      ONE skill: the one whose Skill invocation rides in THIS batch, as
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
# --query-only: the same lookup and the same stdout, and nothing appended —
# for a lookup no Skill call rides with (the restatement check before
# logging, the lookup before briefing a delegate), where a `loaded` line
# would record a load that never happened.
#
# --correct: the Skill call in that batch was refused or errored, so the
# `loaded` line above it is false. Run in the NEXT call, it appends
#   YYYY-MM-DD HH:MM NOT loaded <skill-name> — <reason>
# runs no lookup and prints nothing. It writes the line even with no
# `loaded` line before it (a refusal is a fact); with no
# skill-observations/ yet it prints one NOTE line and writes nothing.
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
#      is the one result nobody questions; or LOOKUP TOOLS MISSING — a
#      command the script runs is not on PATH, named before anything runs
#   2  refused: missing arguments, a relative root, a root that does not
#      exist, a pre-3.0 log.md with no observation-log/ beside it, or a
#      skill name with characters outside [A-Za-z0-9:._/-], an unknown
#      option, or --correct with no reason, or an argument after --query-only,
#      or more than one skill name (a second name, or a list in one
#      argument): one call per Skill invocation, in that invocation's batch
#
# Why a script: a rule about what a tool batch must CONTAIN cannot be
# enforced by prose inside the thing the batch loads — the agent reads the
# prose only after the batch is committed. One call carrying both the lookup
# and the checkpoint line, emitted beside the Skill invocation, leaves a
# record a review can match against the invocation afterwards. The script
# takes one name and refuses a second, so a list of skills about to be
# loaded cannot be recorded in one call; a shell loop of single-name calls
# looks the same from inside, so the one-call-per-invocation rule still
# rests on the caller.
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
mode="${3:-}"
reason="${4:-}"

if [ -z "$root" ] || [ -z "$name" ]; then
  echo "usage: bash skill-load.sh <workspace-root> <skill-name> [--correct \"<reason>\" | --query-only]" >&2; exit 2
fi
if [ $# -gt 4 ]; then
  echo "one skill name per call: got $# arguments — run one call per Skill invocation, in that invocation's batch" >&2; exit 2
fi
case "$mode" in
  ("") ;;
  ([!-]*) echo "one skill name per call: got a second name '$mode' — run one call per Skill invocation, in that invocation's batch; a lookup no Skill call rides with takes --query-only" >&2; exit 2 ;;
  (--correct) [ -n "$reason" ] || { echo "--correct needs a reason: the refusal or error text" >&2; exit 2; } ;;
  (--query-only) [ -z "$reason" ] || { echo "--query-only takes no argument: got '$reason'" >&2; exit 2; } ;;
  (*) echo "unknown option '$mode' — the options are --correct \"<reason>\" and --query-only" >&2; exit 2 ;;
esac
case "$root" in
  (/*|[A-Za-z]:[/\\]*) ;;
  (*) echo "workspace root must be an ABSOLUTE path, never relative to the cwd: got '$root'" >&2; exit 2 ;;
esac
case "$name" in
  (*[,\ ]*) echo "one skill name per call: '$name' is a list — run one call per Skill invocation, in that invocation's batch" >&2; exit 2 ;;
  (*[!A-Za-z0-9:._/-]*) echo "skill name may hold only [A-Za-z0-9:._/-]: got '$name'" >&2; exit 2 ;;
esac

# --- the tools: a missing command is named once, before anything runs -------
miss=
for t in find awk sed grep wc tr date; do
  command -v "$t" >/dev/null 2>&1 || miss="$miss $t"
done
if [ -n "$miss" ]; then
  printf 'LOOKUP TOOLS MISSING —%s not on PATH; nothing looked up, nothing written to checkpoints.log\n' "$miss"; exit 1
fi

# Every expansion of $root and $d stays double-quoted: the pinned path
# routinely contains a space.
if [ "$mode" = "--correct" ]; then
  [ -d "$root" ] || { echo "workspace root does not exist: '$root' — check the pinned path" >&2; exit 2; }
  if [ ! -d "$root/skill-observations" ]; then
    echo "NOTE: $name: no skill-observations/ yet under '$root' — nothing to correct"; exit 0
  fi
  # One line, whatever the refusal text held.
  reason=$(printf '%s' "$reason" | tr '\r\n' '  ')
  printf '%s NOT loaded %s — %s\n' "$(date '+%F %H:%M')" "$name" "$reason" \
    >> "$root/skill-observations/checkpoints.log"
  exit 0
fi
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
[ "$mode" = "--query-only" ] && exit 0

printf '%s loaded %s — %s open observations\n' "$(date '+%F %H:%M')" "$name" "$count" \
  >> "$root/skill-observations/checkpoints.log"
exit 0
