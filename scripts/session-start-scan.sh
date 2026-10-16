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
# Prints, on stdout, in this order: any NOTE / LOST ENTRIES / UNFILLED lines
# (UNFILLED: a header whose title: is empty — the skeleton new-observation.sh
# writes at create time, a write in progress or abandoned; NOTE: id: … when
# a header's id does not read as its filename prefix); the counts
# line (files, parsed, suspect, archive-suspect); a SPLIT STORE line when a
# pre-3.0 log.md sits beside the directory; a NOTE: pointer line when
# skill-observations/MOVED.md exists; a GAP line when the previous scan in
# checkpoints.log is 7 or more days old; the logs found under the root's
# parent; the active principles' headings; then the frontmatter of every
# numbered entry, each header followed by one `---` line; and LAST one
# `end of scan` line repeating the counts and how many finding lines
# (NOTE / LOST ENTRIES / UNFILLED / SPLIT STORE / GAP) stand above the entries. The findings open the
# output and the summary closes it, so a view cut by `head` keeps the
# findings and one cut by `tail` keeps the summary and its finding count;
# neither replaces reading the output whole, which the summary line says.
# Appends one line to skill-observations/checkpoints.log:
#   YYYY-MM-DD HH:MM [<cwd's last segment>] session-start scan: files=N parsed=N principles=N
#
# Exit status:
#   0  the scan ran (NOTE lines are findings, not failures)
#   1  SCAN COMMAND BROKEN — numbered files exist but no header parsed; the
#      scan halts there, before the checkpoint line and the content print
#   2  refused: no workspace root, or a root that is not an absolute path
#   any other non-zero status is the content print's own (the counts and the
#   checkpoint line above it already ran, and the end-of-scan line names the
#   status) — a refused or failed print is never an empty log
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
# fx counts the finding lines (NOTE / LOST ENTRIES / UNFILLED / SPLIT STORE / GAP) printed above the
# entries, for the end-of-scan line.
fx=0
[ "$pr" = unparsed ] && { echo "NOTE: the principles file has no '## Active Principles' heading — 'could not parse', not 'no principles'; read it directly"; fx=$((fx + 1)); }

# --- the guard: files present and nothing parsed is a broken command ----------
if [ "$n" -gt 0 ] && [ "$parsed" -eq 0 ]; then echo "SCAN COMMAND BROKEN — $n files present, 0 headers parsed"; exit 1; fi

# --- findings ----------------------------------------------------------------
# Lost entries: a zero-byte numbered file, or one with no opening `---`.
lost=$( { find "$d" -maxdepth 1 -name '[0-9]*.md' -empty; LC_ALL=C find "$d" -maxdepth 1 -name '[0-9]*.md' ! -empty -exec awk 'FNR==1 {sub(/^\357\273\277/, ""); if (!/^---[[:space:]]*$/) print FILENAME; nextfile}' {} +; } | sed 's|.*/||' | LC_ALL=C sort | tr '\n' ' ')
[ -n "$lost" ] && { echo "LOST ENTRIES — no header, an interrupted write; report each, never reuse or delete: $lost"; fx=$((fx + 1)); }
# Unfilled and mismatched headers, from one awk over the parsed headers:
# U <file> for a header whose title: is empty — the skeleton the helper
# writes at create time, so a write in progress or abandoned, distinct from
# LOST (it holds its id); I <file> <id> for a header whose id: does not
# read as the filename prefix (a retyped id, or a body written into another
# entry's file). The id may be padded or not — both forms exist in live
# logs — so the comparison is numeric.
hd=$(LC_ALL=C find "$d" -maxdepth 1 -name '[0-9]*.md' -exec awk 'FNR==1 {sub(/^\357\273\277/, ""); fm=/^---[[:space:]]*$/; ti=0; idv="none"; f=FILENAME; sub(/.*\//, "", f); pre=substr(f, 1, match(f, /[^0-9]/) - 1); if (!fm) nextfile; next}
  fm && /^---[[:space:]]*$/ {if (ti) print "U " f; if (idv !~ /^0*[1-9][0-9]*$/ || idv + 0 != pre + 0) print "I " f " " idv; nextfile}
  fm && /^title:/ {v=$0; sub(/^title:[[:space:]]*/, "", v); sub(/[[:space:]]+$/, "", v); ti=(v == "" || v == "\"\"" || v == "\047\047")}
  fm && /^id:/ {idv=$2; gsub(/["\047\r]/, "", idv)}' {} +)
unfilled=$(printf '%s\n' "$hd" | sed -n 's/^U //p' | LC_ALL=C sort | tr '\n' ' ')
[ -n "$unfilled" ] && { echo "UNFILLED — a header with an empty title: the helper's skeleton, a write in progress or abandoned; it holds its id, so fill it or decline it, never reuse or delete: $unfilled"; fx=$((fx + 1)); }
idmis=$(printf '%s\n' "$hd" | sed -n 's/^I \(.*\) \(.*\)$/\1 (id: \2)/p' | LC_ALL=C sort | tr '\n' ' ')
[ -n "$idmis" ] && { echo "NOTE: id: does not read as the filename prefix — another entry's id retyped, or a body written into the wrong file; fix the field, never the filename, after reading the body: $idmis"; fx=$((fx + 1)); }
# Headers that did not parse, by name: no opening, or no closing `---`.
[ "$parsed" -lt "$n" ] && { echo "NOTE: $((n - parsed)) of $n headers did not parse (no opening or no closing ---):"; fx=$((fx + 1)); } && LC_ALL=C find "$d" -maxdepth 1 -name '[0-9]*.md' -exec awk 'FNR==1 {if (NR>1 && fm) print f; f=FILENAME; sub(/^\357\273\277/, ""); fm=/^---[[:space:]]*$/; if (!fm) {print f; nextfile}; next} fm && /^---[[:space:]]*$/ {fm=0; nextfile} END {if (fm) print f}' {} +
[ "$suspect" -gt 0 ] || [ "$a_sus" -gt 0 ] && { echo "NOTE: $suspect of $n headers (and $a_sus in archive/) look like invalid YAML (an unquoted ': ', text after a closing quote, a value opening with a backtick, @ or %, an undefined escape, a colon in an unquoted list entry) — quote or fix them (File format)"; fx=$((fx + 1)); }
printf 'files: %s  parsed: %s  suspect (awk, a floor): %s  archive-suspect: %s\n' "$n" "$parsed" "$suspect" "$a_sus"

# --- split store: a pre-3.0 log.md beside the directory -----------------------
# The creation command's LEGACY guard fires only when the directory is
# absent, so a legacy file written AFTER the migration — by an older
# installed copy the host still loads — sits beside the directory unseen.
# Report it with its entry count; the creation command refuses on it too.
lg="$root/skill-observations/log.md"
if [ -e "$lg" ]; then
  echo "SPLIT STORE — log.md holds $(grep -c '^### Observation ' "$lg" | tr -d ' ') observations not in observation-log/: an older installed copy of the skill still writes the legacy file; name each copy's version, then migrate the remainder (references/migration.md) with ids re-issued from this directory's counter"
  fx=$((fx + 1))
fi

# --- pointer: skill-observations/MOVED.md marks a root as abandoned ------------
# Left by a consolidation or a re-anchor (references/environments.md, "Before
# creating a log, search for one"). A session still anchored here is the one
# that has to see it, and nothing else in the protocol lists the root. Data,
# not an order: report it, with how many entries were written here after it.
mv_ptr="$root/skill-observations/MOVED.md"
if [ -f "$mv_ptr" ]; then
  mv_line=$(head -n 1 "$mv_ptr" | tr -d '\r' | cut -c 1-200)
  mv_after=$(find "$d" -maxdepth 1 -name '[0-9]*.md' -newer "$mv_ptr" 2>/dev/null | wc -l | tr -d ' ')
  echo "NOTE: pointer at this root (skill-observations/MOVED.md): \"$mv_line\" — $mv_after entries written here since it; report both roots and ask, never consolidate or re-anchor on it"
  fx=$((fx + 1))
fi

# --- gap: days since the previous session-start scan --------------------------
# Read before this run's trace line is appended. The previous scan's date is
# the last day a session ran the protocol; a gap of 7 days or more (the
# review interval) while the user kept working is the one sign a skill that
# stopped being activated can leave: the sessions in between never reached
# the step that would say so. Day numbers come from awk, so no `date -d`
# (GNU) or `date -j` (BSD) is needed. No earlier scan line: no note.
ck="$root/skill-observations/checkpoints.log"
gap=$( [ -f "$ck" ] && LC_ALL=C awk -v today="$(date +%F)" '
  function dn(s,  y, m, d) { y = substr(s, 1, 4) + 0; m = substr(s, 6, 2) + 0; d = substr(s, 9, 2) + 0
    if (m < 3) { y--; m += 12 }
    return 365 * y + int(y / 4) - int(y / 100) + int(y / 400) + int((153 * (m - 3) + 2) / 5) + d }
  / session-start scan:/ && /^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]/ { last = substr($ 0, 1, 10) }
  END { if (last != "") { g = dn(today) - dn(last); if (g >= 7) print last " " g } }' "$ck")
[ -n "$gap" ] && { echo "GAP: the previous session-start scan ran ${gap% *}, ${gap#* } days ago. If work happened in between, the skill was not activated in those sessions: check the activation instruction (references/environments.md, \"Verify activation in a NEW session\")"; fx=$((fx + 1)); }

# --- the trace: one line per session, with date, time and source -------------
printf '%s [%s] session-start scan: files=%s parsed=%s principles=%s\n' "$(date '+%F %H:%M')" "${PWD##*/}" "$n" "$parsed" "$pr" \
  >> "$root/skill-observations/checkpoints.log"

# --- sibling logs: every observation log up to three levels under the parent -
# A report, never a reason to consolidate from here.
find "$(dirname "$root")" -maxdepth 3 -type d -path '*/skill-observations/observation-log' 2>/dev/null | LC_ALL=C sort | while IFS= read -r o; do printf '%s=%s\n' "${o%/skill-observations/observation-log}" "$(find "$o" -maxdepth 1 -name '[0-9]*.md' | wc -l | tr -d ' ')"; done | awk '{s = s "  " $0} END {print "logs under the parent (report; never consolidate from here):" s}'

# --- content: printed with the headers below ---------------------------------
# The active principles' headings.
[ -f "$p" ] && awk "$pa"' a && /^### / {sub(/\r$/, ""); print}' "$p"
# The frontmatter of every numbered entry, one awk for the whole set over the
# directory's own glob (no word splitting of a spaced path). This is the only
# half a content classifier can refuse, so everything above has already run
# when it is.
( export LC_ALL=C; [ "$n" -eq 0 ] || { cd "$d" && awk 'FNR==1 && NR>1 && fm {print "---"}
    FNR==1 {sub(/^\357\273\277/, ""); fm=/^---[[:space:]]*$/; if (!fm) {print "---"; nextfile}; next}
    fm && /^---[[:space:]]*$/ {fm=0; print "---"; nextfile}
    fm
    END {if (fm) print "---"}' [0-9]*.md; } )
rc=$?

# --- LAST: the end-of-scan line ----------------------------------------------
# Repeats the counts and says how many finding lines stand above the entries,
# so output cut to its last lines still shows that there were findings to
# read; it is a pointer to the whole output, never its replacement.
st=; [ "$rc" -eq 0 ] || st="; content print exited $rc"
printf 'end of scan — files: %s  parsed: %s  suspect: %s  archive-suspect: %s  principles: %s; finding lines above the entries (NOTE / LOST ENTRIES / UNFILLED / SPLIT STORE / GAP): %s%s. Read the output whole: never cut it with head, tail or grep\n' \
  "$n" "$parsed" "$suspect" "$a_sus" "$pr" "$fx" "$st"
exit "$rc"
