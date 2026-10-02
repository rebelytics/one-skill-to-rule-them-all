#!/usr/bin/env bash
# session-start-scan.sh — the Session Start step 2 scan of the observation
# log, as one command.
#
# Usage:
#   bash scripts/session-start-scan.sh [workspace-root]
#
#   [workspace-root]  the pinned absolute workspace path — the directory that
#                     holds skill-observations/. Defaults to the environment
#                     variable TASK_OBSERVER_WORKSPACE. One of the two is
#                     required; the log is never resolved from the cwd. The
#                     path may contain spaces.
#
# Prints, on stdout, in this order: any NOTE / LOST ENTRIES lines; the counts
# line (files, parsed, suspect, archive-suspect); the logs found under the
# root's parent; the active principles' headings; and LAST the frontmatter
# of every numbered entry, each header followed by one `---` line. Appends
# one line to skill-observations/checkpoints.log:
#   YYYY-MM-DD HH:MM [<cwd's last segment>] session-start scan: files=N parsed=N principles=N
#
# Exit status:
#   0  the scan ran (NOTE lines are findings, not failures)
#   1  SCAN COMMAND BROKEN — numbered files exist but no header parsed; the
#      scan halts there, before the checkpoint line and the content print
#   2  refused: no workspace root, or a root that is not an absolute path
#   any other non-zero status is the content print's own (the counts and the
#   checkpoint line above it already ran) — a refused or failed print is
#   never an empty log
#
# This is the inline scan SKILL.md carried in step 2, unchanged in what it
# runs and prints, moved into a file for two reasons. A reader can review it
# here, line by line, instead of as one block of awk regexes inside a numbered
# step. And it no longer travels through the agent's Bash tool as text: on a
# host whose tool halves runs of backslashes (Git for Windows' bash fed one
# `-c` argument), the suspect program's `\\` runs arrived altered, the program
# stopped compiling, and `suspect` read 0 with an error on stderr. A file
# read by bash arrives exact; the one-line invocation carries no backslash.
#
# bash, not sh: the invocation names bash, and every snippet in this skill is
# bash. Runs on bash 3.2 (stock macOS): case patterns are parenthesised.

set -u

root="${1:-${TASK_OBSERVER_WORKSPACE:-}}"

if [ -z "$root" ]; then
  echo "no workspace root: pass it as the first argument or set TASK_OBSERVER_WORKSPACE" >&2; exit 2
fi
# A Windows drive path (C:/... or C:\...) is absolute there and is used as
# given: Git Bash's find, awk and dirname accept it, and the paths the scan
# prints keep the form the pin used.
case $root in
  (/*|[A-Za-z]:[/\\]*) ;;
  (*) echo "workspace root must be an ABSOLUTE path, never relative to the cwd: got '$root'" >&2; exit 2 ;;
esac

# Every expansion of $root, $d and $p stays double-quoted: the pinned path
# routinely contains a space.
d="$root/skill-observations/observation-log"

# --- counts -------------------------------------------------------------------
# n: numbered, non-empty files — what the parse can read. Counted from the
# literal path, independent of $d, so the guard below compares two numbers
# derived by different means.
n=$(find "$root/skill-observations/observation-log" -maxdepth 1 -name '[0-9]*.md' ! -empty | wc -l | tr -d ' ')
# parsed: files whose header opens on line 1 (after a UTF-8 BOM, if any) and
# closes with a second `---`. Counted by its own command, never inside the
# printing loop.
parsed=$(LC_ALL=C find "$d" -maxdepth 1 -name '[0-9]*.md' -exec awk 'FNR==1 {sub(/^\357\273\277/, ""); fm=/^---[[:space:]]*$/; if (!fm) nextfile; next} fm && /^---[[:space:]]*$/ {print FILENAME; nextfile}' {} + | wc -l | tr -d ' ')

# --- suspect: headers that look like invalid YAML by shape (a floor) ----------
# The awk program `sus` is assembled from the named parts below, then run
# once over the active directory and once over archive/. One rule per line
# of the program, each printing the file name at its first hit:
#   1. line 1 opens the header (state resets per file, so an unclosed header
#      cannot leak into the next file under find -exec … +)
#   2. the closing `---` ends the header
#   3. a plain (unquoted) value holding `: `
#   4. text after a closing quote, double- or single-quoted
#   5. a value opening with a backtick, @ or %
#   6. a double-quoted value holding an escape YAML does not define
#   7. a [ … ] list whose unquoted part holds a colon
# Every rule allows any number of spaces after the key's colon and any
# &anchor / !tag before the value. The program holds no literal brace pair:
# find -exec … {} + would replace it.
key='^[a-z_]+:[ ]+([&!][^[:space:]]*[[:space:]]+)*'   # a key, its spaces, any &anchor or !tag
hx='[[:xdigit:]]'   # one hex digit
# cut_short N: N hex digits cut short — k hex digits (k < N), then a non-hex
# character, as one alternation: cut_short 2 is `[^h]|h[^h]`, h being $hx.
cut_short() {
  local k i pre alt=
  for ((k = 0; k < $1; k++)); do
    pre=
    for ((i = 0; i < k; i++)); do pre="$pre$hx"; done
    alt="$alt${alt:+|}$pre[^[:xdigit:]]"
  done
  printf '%s' "$alt"
}
# The escapes a double-quoted YAML scalar defines: one character from the set,
# or \x, \u, \U followed by exactly 2, 4 and 8 hex digits.
esc_ok='\\[0abtnvfre \t\r"\/\\N_LP]|\\x'"$hx$hx"'|\\u'"$hx$hx$hx$hx"'|\\U'"$hx$hx$hx$hx$hx$hx$hx$hx"
# What follows a backslash in an undefined escape: a character outside the
# set, or \x, \u, \U with too few hex digits.
esc_bad='[^0abtnvfre \t\r"\/\\N_LPxuU]|x('"$(cut_short 2)"')|u('"$(cut_short 4)"')|U('"$(cut_short 8)"')'
sus='FNR==1 {sub(/^\357\273\277/, ""); fm = (/^---[[:space:]]*$/ ? 1 : 0); if (!fm) nextfile; next}
  fm && /^---[[:space:]]*$/ {fm=0; nextfile}
  fm && /'"$key"'[^"\047[{|>#&![:space:]].*: / {print FILENAME; nextfile}
  fm && /'"$key"'("([^"\\]|\\.)*"[[:space:]]*[^[:space:]#]|\047([^\047]|\047\047)*\047([[:space:]]+[^[:space:]#]|[^[:space:]#\047]))/ {print FILENAME; nextfile}
  fm && /'"$key"'[`@%]/ {print FILENAME; nextfile}
  fm && /'"$key"'"([^"\\]|('"$esc_ok"'))*\\('"$esc_bad"')/ {print FILENAME; nextfile}
  fm && /^[a-z_]+:[ ]+\[/ {v=$0; sub(/^[a-z_]+:[ ]+/,"",v); gsub(/"([^"\\]|\\.)*"/,"",v); gsub(/\047[^\047]*\047/,"",v); sub(/[[:space:]]#.*/,"",v); if (v ~ /:/) {print FILENAME; nextfile}}'
suspect=$(LC_ALL=C find "$d" -maxdepth 1 -name '[0-9]*.md' -exec awk "$sus" {} + | wc -l | tr -d ' ')
a_sus=0; [ -d "$d/archive" ] && a_sus=$(LC_ALL=C find "$d/archive" -maxdepth 1 -name '*.md' -exec awk "$sus" {} + | wc -l | tr -d ' ')   # archive/ may not exist yet

# --- principles: count the headings under `## Active Principles` --------------
# A fenced block is skipped, so a template inside the file is not a principle.
p="$root/skill-observations/cross-cutting-principles.md"
pa='/^(\140\140\140|~~~)/ {f=!f} f {next} /^## Active Principles/ {a=1; h=1; next} a && /^## / {a=0}'
pr=absent; [ -f "$p" ] && pr=$(awk "$pa"' a && /^### / {n++} END {print (h ? n+0 : "unparsed")}' "$p")
[ "$pr" = unparsed ] && echo "NOTE: the principles file has no '## Active Principles' heading — 'could not parse', not 'no principles'; read it directly"

# --- the guard: files present and nothing parsed is a broken command ----------
if [ "$n" -gt 0 ] && [ "$parsed" -eq 0 ]; then echo "SCAN COMMAND BROKEN — $n files present, 0 headers parsed"; exit 1; fi

# --- findings ----------------------------------------------------------------
# Lost entries: a zero-byte numbered file, or one with no opening `---`.
lost=$( { find "$d" -maxdepth 1 -name '[0-9]*.md' -empty; LC_ALL=C find "$d" -maxdepth 1 -name '[0-9]*.md' ! -empty -exec awk 'FNR==1 {sub(/^\357\273\277/, ""); if (!/^---[[:space:]]*$/) print FILENAME; nextfile}' {} +; } | sed 's|.*/||' | LC_ALL=C sort | tr '\n' ' ')
[ -n "$lost" ] && echo "LOST ENTRIES — no header, an interrupted write; report each, never reuse or delete: $lost"
# Headers that did not parse, by name: no opening, or no closing `---`.
[ "$parsed" -lt "$n" ] && echo "NOTE: $((n - parsed)) of $n headers did not parse (no opening or no closing ---):" && LC_ALL=C find "$d" -maxdepth 1 -name '[0-9]*.md' -exec awk 'FNR==1 {if (NR>1 && fm) print f; f=FILENAME; sub(/^\357\273\277/, ""); fm=/^---[[:space:]]*$/; if (!fm) {print f; nextfile}; next} fm && /^---[[:space:]]*$/ {fm=0; nextfile} END {if (fm) print f}' {} +
[ "$suspect" -gt 0 ] || [ "$a_sus" -gt 0 ] && echo "NOTE: $suspect of $n headers (and $a_sus in archive/) look like invalid YAML (an unquoted ': ', text after a closing quote, a value opening with a backtick, @ or %, an undefined escape, a colon in an unquoted list entry) — quote or fix them (File format)"
printf 'files: %s  parsed: %s  suspect (awk, a floor): %s  archive-suspect: %s\n' "$n" "$parsed" "$suspect" "$a_sus"

# --- the trace: one line per session, with date, time and source -------------
printf '%s [%s] session-start scan: files=%s parsed=%s principles=%s\n' "$(date '+%F %H:%M')" "${PWD##*/}" "$n" "$parsed" "$pr" \
  >> "$root/skill-observations/checkpoints.log"

# --- sibling logs: every observation log up to three levels under the parent -
# A report, never a reason to consolidate from here.
find "$(dirname "$root")" -maxdepth 3 -type d -path '*/skill-observations/observation-log' 2>/dev/null | LC_ALL=C sort | while IFS= read -r o; do printf '%s=%s\n' "${o%/skill-observations/observation-log}" "$(find "$o" -maxdepth 1 -name '[0-9]*.md' | wc -l | tr -d ' ')"; done | awk '{s = s "  " $0} END {print "logs under the parent (report; never consolidate from here):" s}'

# --- content: printed with the headers below ---------------------------------
# The active principles' headings.
[ -f "$p" ] && awk "$pa"' a && /^### / {sub(/\r$/, ""); print}' "$p"
# LAST: the frontmatter of every numbered entry, one awk for the whole set
# over the directory's own glob (no word splitting of a spaced path). This is
# the only half a content classifier can refuse, so everything above has
# already run when it is.
( export LC_ALL=C; [ "$n" -eq 0 ] || { cd "$d" && awk 'FNR==1 && NR>1 && fm {print "---"}
    FNR==1 {sub(/^\357\273\277/, ""); fm=/^---[[:space:]]*$/; if (!fm) {print "---"; nextfile}; next}
    fm && /^---[[:space:]]*$/ {fm=0; print "---"; nextfile}
    fm
    END {if (fm) print "---"}' [0-9]*.md; } )
