#!/usr/bin/env bash
# new-observation.sh — derive the next observation id AND create the file,
# as one command that cannot be split.
#
# Usage:
#   scripts/new-observation.sh <slug> [workspace-root]
#
#   <slug>            kebab-case, no id prefix, no extension ("short-slug")
#   [workspace-root]  the pinned absolute workspace path — the directory that
#                     holds skill-observations/. Defaults to the environment
#                     variable TASK_OBSERVER_WORKSPACE. One of the two is
#                     required; the log is never resolved from the cwd.
#
# Prints the created file's absolute path on stdout (one line) and exits 0.
# Any guard firing prints its message on stderr and exits 1 with NO file
# created. Write the observation body into the printed path, with the id
# from its NNNN- prefix in the `id:` field — copied, never retyped.
#
# This is the id-derivation snippet from SKILL.md "How to Log", unchanged in
# substance, packaged so that the moment of derivation cannot drift away
# from the moment of writing: an id derived at session start and carried in
# memory to a later write is the collision the snippet's rules forbid, and
# a rule that has failed twice while loaded needs the write path itself to
# enforce it. Where this script can run, it is the only write path.
#
# Steps, in order: archival sweep of stale resolved files (a side effect of
# deriving the id, never a separate duty) → id = max(active prefixes,
# archive prefixes, .id-floor) + 1, the listing guarded against find's
# count before the floor enters → PREFIX collision guard across active and
# archive (two slugs sharing one number is the failure; a path check cannot
# see it) → noclobber create → floor write (after the create, so a run that
# creates nothing never moves it) → print the path.
#
# bash, not sh: the `10#` arithmetic is a bash extension. Runs on bash 3.2
# (stock macOS): case patterns are parenthesised for that reason.

set -u

slug="${1:-}"
root="${2:-${TASK_OBSERVER_WORKSPACE:-}}"

if [ -z "$slug" ]; then
  echo "usage: new-observation.sh <slug> [workspace-root]" >&2; exit 1
fi
case $slug in
  (*[!a-z0-9-]*|-*|*-|*--*|"")
    echo "slug must be kebab-case (a-z, 0-9, single hyphens): got '$slug'" >&2; exit 1 ;;
esac
case $slug in
  ([0-9][0-9][0-9][0-9]-*) echo "slug must not start with an id prefix: got '$slug'" >&2; exit 1 ;;
esac
if [ -z "$root" ]; then
  echo "no workspace root: pass it as the second argument or set TASK_OBSERVER_WORKSPACE" >&2; exit 1
fi
case $root in
  (/*) ;;
  (*) echo "workspace root must be an ABSOLUTE path, never relative to the cwd: got '$root'" >&2; exit 1 ;;
esac

d="$root/skill-observations/observation-log"   # may contain a space: every expansion stays quoted
if [ ! -d "$d" ] || [ ! -d "$d/archive" ]; then
  echo "STRUCTURE MISSING — expected '$d' and '$d/archive' (Session Start step 1 creates them); HALT and re-probe, never recreate from here" >&2
  exit 1
fi

today=$(date +%F)

# --- archival sweep: stale resolved files move before the id is read --------
n_files=$(find "$d" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')
seen=$(cd "$d" && awk 'FNR==1 {n++; nextfile} END {print n+0}' *.md 2>/dev/null)   # files the sweep's glob reaches, counted apart from the sweep
if [ "$n_files" -gt 0 ] && [ "${seen:-0}" -eq 0 ]; then
  echo "ARCHIVAL SWEEP BROKEN — $n_files files present, 0 examined" >&2; exit 1
fi
# one awk for the whole set (a process per file crosses a tool timeout on a
# large log); one mv per stale resolved file, bounded by the files due
( cd "$d" && awk -v today="$today" 'FNR==1 {st=""; r=""; fm=/^---[[:space:]]*$/; if (!fm) nextfile; next}
    fm && /^---[[:space:]]*$/ {if (st ~ /^(actioned|declined|superseded)$/ && r ~ /^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]$/ && r < today) print FILENAME; nextfile}
    fm && /^status:/ {st=$2}
    fm && /^resolved:/ {r=$2}' *.md 2>/dev/null | while IFS= read -r x; do mv "$x" archive/; done )

# --- id: max of active prefixes, archive prefixes and the floor, plus one ---
# Globs and builtins list the files, never `ls`: a profile alias or function
# can rebind that word. The floor is read as digits only (a CRLF or padded
# file still reads), and 10# keeps a zero-padded number out of octal.
floor=$(sed '1!d; s/[^0-9]//g' "$d/archive/.id-floor" 2>/dev/null); floor=$((10#${floor:-0}))
ids=$(for p in "$d"/[0-9]*.md "$d"/archive/[0-9]*.md; do [ -e "$p" ] && printf '%s\n' "${p##*/}"; done | grep -oE '^[0-9]+')
if [ "$(printf '%s' "$ids" | grep -c .)" -ne "$(find "$d" "$d/archive" -maxdepth 1 -name '[0-9]*.md' | wc -l)" ]; then
  echo "ID COMMAND BROKEN — the listing and find disagree on the prefixed files" >&2; exit 1
fi
hi=$(printf '%s\n' "$ids" | sort -n | tail -1); hi=$((10#${hi:-0}))
if [ "$hi" -lt "$floor" ]; then
  echo "NOTE: highest file id $hi is below .id-floor $floor — ids issued without a file; the new id goes above the floor" >&2
fi
next_id=$(( (hi > floor ? hi : floor) + 1 ))
prefix=$(printf '%04d' "$next_id")

# floor-staleness note: the floor lags the directory when an issuer skipped
# the floor write. Harmless here (max-of-three absorbs it) but worth a line,
# because a lagging floor is the precondition for a restart once the active
# directory is archived down.
top_active=$(for p in "$d"/[0-9]*.md; do [ -e "$p" ] && printf '%s\n' "${p##*/}"; done | grep -oE '^[0-9]+' | sort -n | tail -1)
if [ -s "$d/archive/.id-floor" ] && [ -n "${top_active:-}" ] && [ "$floor" -lt "$((10#$top_active))" ]; then
  echo "NOTE: .id-floor ($floor) is below the highest active id ($((10#$top_active))) — an issuer skipped the floor write; corrected now" >&2
fi

# --- collision guard on the id PREFIX, across active and archive ------------
# Two writers deriving the same number with different slugs produce two
# different paths; a path check passes both. The invariant is a unique
# number, so the guard is keyed on the number.
if [ -n "$(find "$d" -maxdepth 2 -name "${prefix}-*.md")" ]; then
  echo "COLLISION — id $next_id already used; re-derive (re-run this script)" >&2; exit 1
fi

# --- noclobber create: never truncate an existing file ----------------------
f="$d/${prefix}-${slug}.md"
if ! (set -C; : > "$f") 2>/dev/null; then
  echo "CREATE FAILED — $f exists or is unwritable" >&2; exit 1
fi

# --- floor write, after the create: never lower (next_id > floor) ------------
printf '%s\n' "$next_id" > "$d/archive/.id-floor" || { echo "FLOOR WRITE FAILED — $d/archive/.id-floor (the file $f exists; fix the floor by hand)" >&2; exit 1; }

printf '%s\n' "$f"
