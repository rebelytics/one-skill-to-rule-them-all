#!/usr/bin/env bash
# stage-patch.sh — stage a change to a non-skill file (a `target_file:`
# entry's file, a state file) as a unified diff against the live file,
# refusing a change that repeats a heading the live file already has.
#
# Usage:
#   bash scripts/stage-patch.sh [--allow-repeat <heading line>]... <live-file> <changed-file> <patch-out>
#
#   <live-file>     the file as it stands now, at its live path
#   <changed-file>  the review's changed copy of it
#   <patch-out>     where the patch goes (references/weekly-review.md,
#                   Delivery: skill-updates/<date>/_target-files/); never
#                   overwritten — an existing path is refused
#   --allow-repeat  one heading line, exactly as written, that the change
#                   may repeat on purpose (a recurring "### Example"); one
#                   flag per heading, so each exception is named
#
# The refusal: in a Markdown file (.md, .markdown, .mdx), a heading line
# (`#` to `######` and a space, outside fenced code) that the changed copy
# holds more often than the live file, where the live file holds it at
# least once, means the change adds a section the target already has.
# HEADING REPEATED names each such heading with its live line number; no
# patch is written (exit 1). A review that re-routed an entry to another
# file and checked presence only against the old target staged exactly
# that: a second section beside one the user had already written. A
# section moved within the file keeps its count and passes.
#
# Prints one line and exits with its code:
#   STAGED <patch-out> — <a> added, <r> removed line(s); <heading note>   0
#   HEADING REPEATED … / NO CHANGE …                                       1
#   ERROR <what>                                                           2
#
# bash 3.2-compatible (stock macOS).

set -u

allow=$'\n'
while [ $# -gt 0 ]; do
  case $1 in
    (--allow-repeat) [ $# -ge 2 ] || { echo "ERROR --allow-repeat needs a heading line"; exit 2; }
      allow="$allow$2"$'\n'; shift 2 ;;
    (--) shift; break ;;
    (-*) echo "ERROR unknown option '$1' (the option is --allow-repeat <heading line>)"; exit 2 ;;
    (*) break ;;
  esac
done
[ $# -eq 3 ] || { echo "ERROR usage: stage-patch.sh [--allow-repeat <heading>]... <live-file> <changed-file> <patch-out> (got $# argument(s))"; exit 2; }
live=$1; changed=$2; out=$3
for x in "$live" "$changed"; do
  [ -f "$x" ] && [ -r "$x" ] || { echo "ERROR not a readable file: '$x'"; exit 2; }
done
[ -e "$out" ] && { echo "ERROR '$out' exists: a staged patch is never overwritten — name a new one or integrate by hand"; exit 2; }
[ -d "$(dirname "$out")" ] || { echo "ERROR no directory for '$out'"; exit 2; }
for t in awk diff grep dirname; do command -v "$t" >/dev/null 2>&1 || { echo "ERROR $t not on PATH; nothing staged"; exit 2; }; done

if diff -q "$live" "$changed" >/dev/null 2>&1; then
  echo "NO CHANGE — '$changed' is identical to '$live'; nothing staged"; exit 1
fi

# --- the heading check (Markdown only) ---------------------------------------
hnote="heading check: not a Markdown file, skipped"
case $live in
  (*.md|*.markdown|*.mdx|*.MD)
    rep=$(ALLOW="$allow" LC_ALL=C awk -v q="'" '
      FNR == 1 {fe = 0; sub(/^\357\273\277/, "")}
      {sub(/\r$/, ""); l = $0}
      l ~ /^ ? ? ?(```|~~~)/ {fe = !fe; next}
      fe {next}
      l ~ /^ ? ? ?##?#?#?#?#?([ \t]|$)/ {sub(/^ +/, "", l); sub(/[ \t]+$/, "", l)
        if (FILENAME == ARGV[1]) {lc[l]++; if (!(l in at)) at[l] = FNR} else cc[l]++}
      END {for (h in cc) if ((h in lc) && cc[h] > lc[h] && index(ENVIRON["ALLOW"], "\n" h "\n") == 0)
             printf "%s%s%s%s (live line %d)", (n++ ? "; " : ""), q, h, q, at[h]}' "$live" "$changed")
    if [ -n "$rep" ]; then
      echo "HEADING REPEATED — no patch written: the change adds heading(s) '$live' already has: $rep. The section exists there: re-run the presence check against this file and merge into it, or name an intended repeat with --allow-repeat"; exit 1
    fi
    hnote="heading check: no heading repeated" ;;
esac

# --- write the patch, never over an existing file -----------------------------
( set -C; LC_ALL=C diff -u "$live" "$changed" > "$out" ) 2>/dev/null
rc=$?
if [ "$rc" -ne 1 ] || [ ! -s "$out" ]; then
  echo "ERROR diff -u exited $rc writing '$out'; check the path, remove a partial file by hand"; exit 2
fi
a=$(awk 'NR > 2 && /^\+/ {n++} END {print n + 0}' "$out"); r=$(awk 'NR > 2 && /^-/ {n++} END {print n + 0}' "$out")
echo "STAGED $out — $a added, $r removed line(s); $hnote"
