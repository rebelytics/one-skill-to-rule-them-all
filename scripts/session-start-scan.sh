#!/usr/bin/env bash
# session-start-scan.sh — the Session Start step 2 scan of the observation
# log, as one command.
#
# Usage:
#   bash scripts/session-start-scan.sh [--entries-to <file>] [workspace-root]
#   (options first: an argument after the root is refused, exit 2)
#
#   [workspace-root]  the pinned absolute workspace path — the directory that
#                     holds skill-observations/. Defaults to the environment
#                     variable TASK_OBSERVER_WORKSPACE. One of the two is
#                     required; the log is never resolved from the cwd. The
#                     path may contain spaces.
#   --entries-to <file>
#                     write the per-entry listing to <file>
#                     instead of stdout, for a channel that caps the output
#                     (a bridged device shell): stdout then carries only the
#                     finding lines, the counts, the principles' headings and
#                     the summary block, and the entries are read from the
#                     file on demand. <file> is a path THIS run created
#                     (`mktemp`), never a fixed name in a shared scratch
#                     directory: an existing non-empty file is refused (exit
#                     2), because a redirect onto another session's file
#                     followed by a read returns that session's scan.
#
# Prints, on stdout, in this order: any DUE / NOTE / LOST ENTRIES / UNFILLED /
# DUPLICATE ID / RESURRECTED lines
# (DUE: a session-start duty still owed — `DUE: workspace creation` when one
# of the four artefacts the Workspace creation command makes is missing,
# `DUE: starter-set reconciliation` when skill-observations/
# starter-principles-reviewed.txt is absent or names an older set than
# references/starter-principles.md beside this script; where that file is
# unreadable — a .bin/ copy in a bridged session — an absent marker is still
# DUE and an older one is not compared, so no line prints for it;
# UNFILLED: a header whose title: is empty — the skeleton new-observation.sh
# writes at create time, a write in progress or abandoned; NOTE: id: … when
# a header's id does not read as its filename prefix; DUPLICATE ID — NNNN:
# <file1>, <file2> when two files across observation-log/ and archive/ share
# a numeric prefix — a write that went around the id snippet's prefix
# guard; RESURRECTED — when an active file is byte-identical to its
# same-named archive/ copy, a restored archive entry, never renumbered); the
# counts line (files, parsed, suspect, archive-suspect, resurrected); a SPLIT STORE line when a
# pre-3.0 log.md sits beside the directory; a NOTE: pointer line when
# skill-observations/MOVED.md exists; a NOTE: legacy staging root line when
# skill-observations/skill-updates/ (the pre-3.0 staging root) exists; a GAP
# line when the previous scan in checkpoints.log is 7 or more days old; the logs found under the root's
# parent; the active principles' headings; then one line per numbered entry,
# `id | status | skill | proposes_skill | title` (`-` for a field the header
# lacks), parked entries after the others, an actioned, declined or
# superseded entry as `id | status | skill | proposes_skill | resolved <date>
# — title withheld` (its title names a defect that is probably fixed), and
# `--- <file> (no header)` or
# `--- <file> (header not closed)` for a file whose header did not parse (or,
# with --entries-to, that listing goes to the file); the full headers go to
# skill-observations/last-scan-headers.txt, overwritten each run, for a step
# that needs another field; then the summary
# block: every finding line (DUE / NOTE / LOST ENTRIES / UNFILLED / DUPLICATE
# ID / RESURRECTED / SPLIT STORE / GAP) repeated VERBATIM, and LAST one `end of scan` line
# repeating the counts, how many finding lines stand above the entries, and
# this script's version (VERSION below, equal to the skill's `version:`), so
# a run can tell a script that lacks a feature from one that is broken. The findings
# open the output and close it, so a view cut by `head` keeps them and one
# cut by `tail` keeps them with the summary; the same lines are written to
# skill-observations/last-scan-findings.txt (overwritten each run, empty
# when there are none), which the end line names, so a run whose output was
# cut anyway still has them on disk. Three places, because an instruction
# not to cut the output was broken while it was in context: the barrier is
# the output's shape, not the reader. None of it replaces reading the output
# whole, which the end line says.
# Appends one line to skill-observations/checkpoints.log:
#   YYYY-MM-DD HH:MM [<cwd's last segment>] session-start scan: files=N parsed=N principles=N
#
# Exit status:
#   0  the scan ran (NOTE lines are findings, not failures)
#   1  SCAN COMMAND BROKEN — numbered files exist but no header parsed, or
#      a count did not read as a number; or SCAN TOOLS MISSING — a command
#      the scan runs is not on PATH. The scan halts there, before the
#      checkpoint line and the content print (the sidecar file holds that
#      one line, so no earlier run's findings survive the halt)
#   2  refused: no workspace root, a root that is not an absolute path, a
#      root with no skill-observations/observation-log/ under it (the line
#      says which: a path inside the workspace, a first run, a pre-3.0
#      log.md, a root that does not exist), an
#      --entries-to path that exists and is not empty, an unknown option, or
#      any argument after the root (an option there is a usage error)
#   3  --entries-to left its file empty while numbered files exist: a broken
#      run, named by a NOTE line in the summary block and the sidecar
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

VERSION="3.9.0"   # equal to the skill's frontmatter version:; the end line names it

entries=   # --entries-to target; empty = the entries print to stdout
while [ $# -gt 0 ]; do
  case $1 in
    (--entries-to) [ $# -ge 2 ] || { echo "--entries-to needs a file path" >&2; exit 2; }; entries="$2"; shift 2 ;;
    (--entries-to=*) entries="${1#--entries-to=}"; shift ;;
    (--) shift; break ;;
    (-*) echo "unknown option '$1' (the options are --entries-to <file>)" >&2; exit 2 ;;
    (*) break ;;
  esac
done
root="${1:-${TASK_OBSERVER_WORKSPACE:-}}"
# Nothing may follow the root: the loop above stops at it, so an option
# written after it was never parsed — a trailing --entries-to silently fell
# back to printing the entries on stdout and left its file empty. Refused
# by name instead, before anything is written.
[ $# -gt 0 ] && shift
if [ $# -gt 0 ]; then
  echo "argument after the workspace root: '$1' — options go BEFORE the root (bash session-start-scan.sh --entries-to <file> <root>); nothing was scanned" >&2; exit 2
fi

if [ -n "$entries" ] && [ -s "$entries" ]; then
  echo "--entries-to '$entries' exists and is not empty: pass a path this run created (mktemp), never a fixed name another session may hold" >&2; exit 2
fi

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

# --- the root holds a log: refused by name, before any command runs ----------
# A wrong root used to print six find errors, `files: 0`, exit 0 and a
# checkpoint line: a clean empty backlog. Only builtins run here.
if [ ! -d "$d" ]; then
  r="${root%/}"
  case $r in
    (*/skill-observations/observation-log) why="that is the log itself — pass '${r%/skill-observations/observation-log}', the directory that contains skill-observations/" ;;
    (*/skill-observations) why="that is skill-observations/ itself — pass '${r%/skill-observations}', the directory that contains it" ;;
    (*) if [ ! -d "$root" ]; then why="the root does not exist — check the pinned path"
        elif [ -e "$root/skill-observations/log.md" ]; then why="a pre-3.0 log.md and no directory — run the migration (references/migration.md) first"
        elif [ ! -d "$root/skill-observations" ]; then why="no skill-observations/ — a first run: run the Workspace creation command (references/observation-log.md) first, or pass the workspace root"
        else why="skill-observations/ holds no observation-log/ — run the Workspace creation command (references/observation-log.md)"; fi ;;
  esac
  echo "no observation log under '$root': $why; nothing was scanned or written" >&2; exit 2
fi

# --- the tools: a missing command is a broken scan, never an empty log -------
# On a runner without the usual commands every count came back empty and the
# trace line was appended anyway. The halt line goes to the sidecar too.
miss=
for t in find awk sed wc tr date sort grep head cut dirname tee; do
  command -v "$t" >/dev/null 2>&1 || miss="$miss $t"
done
if [ -n "$miss" ]; then
  printf 'SCAN TOOLS MISSING —%s not on PATH; nothing scanned, no checkpoint line written\n' "$miss"
  printf 'SCAN TOOLS MISSING —%s not on PATH\n' "$miss" > "$root/skill-observations/last-scan-findings.txt" 2>/dev/null
  exit 1
fi

# --- counts -------------------------------------------------------------------
# n: numbered, non-empty files — what the parse can read. Counted from the
# literal path, independent of $d, so the guard below compares two numbers
# derived by different means.
n=$(find "$root/skill-observations/observation-log" -maxdepth 1 -name '[0-9]*.md' ! -empty | wc -l | tr -d ' ')
# parsed: files whose header opens on line 1 (after a UTF-8 BOM, if any) and
# closes with a second `---`. Counted by its own command, never inside the
# printing loop.
parsed=$(LC_ALL=C find "$d" -maxdepth 1 -name '[0-9]*.md' -exec awk 'FNR==1 {sub(/^\357\273\277/, ""); fm=/^---[[:space:]]*$/; if (!fm) nextfile; next} fm && /^---[[:space:]]*$/ {print FILENAME; nextfile}' {} + | wc -l | tr -d ' ')
bad=; case $n in (""|*[!0-9]*) bad=1 ;; esac; case $parsed in (""|*[!0-9]*) bad=1 ;; esac
if [ -n "$bad" ]; then echo "SCAN COMMAND BROKEN — the counts did not read as numbers (files='$n' parsed='$parsed')" | tee "$root/skill-observations/last-scan-findings.txt"; exit 1; fi

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
# A hit prints `<file> TAB <rule> TAB <line>`; the scan counts the lines, the
# creation helper names the rule and the line in its refusal.
# Every rule allows any number of spaces after the key's colon and any
# &anchor / !tag before the value. The program holds no literal brace pair:
# find -exec … {} + would replace it.
# >>> sus: shared with new-observation.sh, byte for byte (the selftest compares them)
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
  fm && /'"$key"'[^"\047[{|>#&![:space:]].*: / {print FILENAME "\t3\t" $0; nextfile}
  fm && /'"$key"'("([^"\\]|\\.)*"[[:space:]]*[^[:space:]#]|\047([^\047]|\047\047)*\047([[:space:]]+[^[:space:]#]|[^[:space:]#\047]))/ {print FILENAME "\t4\t" $0; nextfile}
  fm && /'"$key"'[`@%]/ {print FILENAME "\t5\t" $0; nextfile}
  fm && /'"$key"'"([^"\\]|('"$esc_ok"'))*\\('"$esc_bad"')/ {print FILENAME "\t6\t" $0; nextfile}
  fm && /^[a-z_]+:[ ]+\[/ {v=$0; sub(/^[a-z_]+:[ ]+/,"",v); gsub(/"([^"\\]|\\.)*"/,"",v); gsub(/\047[^\047]*\047/,"",v); sub(/[[:space:]]#.*/,"",v); if (v ~ /:/) {print FILENAME "\t7\t" $0; nextfile}}'
# <<< sus
suspect=$(LC_ALL=C find "$d" -maxdepth 1 -name '[0-9]*.md' -exec awk "$sus" {} + | wc -l | tr -d ' ')
a_sus=0; [ -d "$d/archive" ] && a_sus=$(LC_ALL=C find "$d/archive" -maxdepth 1 -name '*.md' -exec awk "$sus" {} + | wc -l | tr -d ' ')   # archive/ may not exist yet

# --- principles: count the headings under `## Active Principles` --------------
# A fenced block is skipped, so a template inside the file is not a principle.
p="$root/skill-observations/cross-cutting-principles.md"
pa='/^(\140\140\140|~~~)/ {f=!f} f {next} /^## Active Principles/ {a=1; h=1; next} a && /^## / {a=0}'
pr=absent; [ -f "$p" ] && pr=$(awk "$pa"' a && /^### / {n++} END {print (h ? n+0 : "unparsed")}' "$p")
# finding prints one finding line (DUE / NOTE / LOST ENTRIES / UNFILLED /
# SPLIT STORE / GAP) above the entries, keeps it for the summary block and the
# sidecar file, and counts it (fx) for the end-of-scan line. Every finding
# goes through it, so the three copies cannot differ.
fx=0; findings=
sidecar="$root/skill-observations/last-scan-findings.txt"
finding() { printf '%s\n' "$1"; findings="$findings$1"$'\n'; fx=$((fx + 1)); }
[ "$pr" = unparsed ] && finding "NOTE: the principles file has no '## Active Principles' heading — 'could not parse', not 'no principles'; read it directly"

# --- due: the step 1 duties the prose names, printed when still owed ----------
# Workspace creation: the four artefacts its command makes and asserts.
miss=
for x in observation-log/archive last-review-date.txt cross-cutting-principles.md; do
  [ -e "$root/skill-observations/$x" ] || miss="$miss${miss:+, }$x"
done
[ -n "$miss" ] && finding "DUE: workspace creation — missing: $miss; run the Workspace creation command (references/observation-log.md) before anything else this session"
# Starter-set reconciliation: the marker against the shipped set, read from
# the reference beside this script. Where that file is unreadable (a .bin/
# copy), an absent marker is still due; an older one cannot be compared.
mk="$root/skill-observations/starter-principles-reviewed.txt"
sp="$(dirname "$0")/../references/starter-principles.md"
ship=; [ -r "$sp" ] && ship=$(sed -n 's/^Starter set version:[[:space:]]*\([0-9][0-9]*\).*/\1/p' "$sp" | head -n 1)
if [ ! -e "$mk" ]; then
  finding "DUE: starter-set reconciliation — skill-observations/starter-principles-reviewed.txt is absent; load references/starter-principles.md (Reconciliation) and offer once"
elif [ -n "$ship" ]; then
  mv_v=$(sed '1!d; s/[^0-9]//g' "$mk")
  if [ -z "$mv_v" ] || [ "$((10#$mv_v))" -lt "$ship" ]; then
    finding "DUE: starter-set reconciliation — marker v${mv_v:-?} < shipped set v$ship; load references/starter-principles.md (Reconciliation) and offer once"
  fi
fi

# --- the guard: files present and nothing parsed is a broken command ----------
# The sidecar takes the guard line too: a stale finding file from the previous
# run must not survive a run that halted.
if [ "$n" -gt 0 ] && [ "$parsed" -eq 0 ]; then echo "SCAN COMMAND BROKEN — $n files present, 0 headers parsed" | tee "$sidecar"; exit 1; fi

# --- findings ----------------------------------------------------------------
# Lost entries: a zero-byte numbered file, or one with no opening `---`.
lost=$( { find "$d" -maxdepth 1 -name '[0-9]*.md' -empty; LC_ALL=C find "$d" -maxdepth 1 -name '[0-9]*.md' ! -empty -exec awk 'FNR==1 {sub(/^\357\273\277/, ""); if (!/^---[[:space:]]*$/) print FILENAME; nextfile}' {} +; } | sed 's|.*/||' | LC_ALL=C sort | tr '\n' ' ')
[ -n "$lost" ] && finding "LOST ENTRIES — no header, an interrupted write; report each, never reuse or delete: $lost"
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
[ -n "$unfilled" ] && finding "UNFILLED — a header with an empty title: the helper's skeleton, a write in progress or abandoned; it holds its id, so fill it or decline it, never reuse or delete: $unfilled"
idmis=$(printf '%s\n' "$hd" | sed -n 's/^I \(.*\) \(.*\)$/\1 (id: \2)/p' | LC_ALL=C sort | tr '\n' ' ')
[ -n "$idmis" ] && finding "NOTE: id: does not read as the filename prefix — another entry's id retyped, or a body written into the wrong file; fix the field, never the filename, after reading the body: $idmis"
# Duplicate numeric prefixes across observation-log/ and archive/: two files
# sharing one id are a write that went around the snippet's prefix guard
# (the guard lives on one write path; this check reads them all). The
# prefix is compared as a number, so 0063- and 63- are one id; archived
# files are named with their archive/ prefix. One finding line per id,
# counted and written to the sidecar like every other.
# An active file byte-identical to its same-named archive/ copy is not a
# collision: a sync or mirror restored an archived entry (an `mv` the mirror
# turned into a copy). It is reported as RESURRECTED, left out of the
# DUPLICATE ID check and of the entries print, and counted on its own; the
# fix removes the active copy and never renumbers. Without cmp on PATH the
# pair falls through to DUPLICATE ID.
res=; nres=0
if [ -d "$d/archive" ] && command -v cmp >/dev/null 2>&1; then
  for p_a in "$d"/[0-9]*.md; do
    [ -f "$p_a" ] || continue
    b_a=${p_a##*/}
    if [ -f "$d/archive/$b_a" ] && cmp -s "$p_a" "$d/archive/$b_a"; then res="$res/$b_a"; nres=$((nres + 1)); fi
  done
  [ -n "$res" ] && res="$res/"
fi
[ "$nres" -gt 0 ] && finding "RESURRECTED — $nres active file(s) byte-identical to their archive/ copy, a sync or mirror restoring archived entries: $(printf '%s' "$res" | sed 's|^/||; s|/$||; s|/|, |g'); remove the active copy, never renumber, and record the sync client (references/environments.md, \"Stable is not the same as always available\")"
dups=$( { find "$d" -maxdepth 1 -name '[0-9]*.md' | sed 's|.*/||' | LC_ALL=C awk -v skip="$res" 'index(skip, "/" $0 "/") == 0'; [ -d "$d/archive" ] && find "$d/archive" -maxdepth 1 -name '[0-9]*.md' | sed 's|.*/\([^/]*\)$|archive/\1|'; } \
  | LC_ALL=C sort | LC_ALL=C awk '{f=$0; sub(/^archive\//, "", f); n=substr(f, 1, match(f, /[^0-9]/) - 1) + 0; c[n]++; if (n in l) l[n]=l[n] ", " $0; else l[n]=$0} END {for (n in c) if (c[n] > 1) printf "%04d: %s\n", n, l[n]}' | LC_ALL=C sort)
if [ -n "$dups" ]; then
  # a here-string, not a pipe: `finding` must update fx and findings in THIS shell
  while IFS= read -r line; do [ -n "$line" ] && finding "DUPLICATE ID — $line — two writes share one id; re-id the uncited file (else the later one) in the next review and never cite the number bare"; done <<< "$dups"
fi
# Headers that did not parse, by name: no opening, or no closing `---`. The
# names ride on the finding line itself, so the repeat and the sidecar carry them.
if [ "$parsed" -lt "$n" ]; then
  unparsed=$(LC_ALL=C find "$d" -maxdepth 1 -name '[0-9]*.md' -exec awk 'FNR==1 {if (NR>1 && fm) print f; f=FILENAME; sub(/^\357\273\277/, ""); fm=/^---[[:space:]]*$/; if (!fm) {print f; nextfile}; next} fm && /^---[[:space:]]*$/ {fm=0; nextfile} END {if (fm) print f}' {} + | sed 's|.*/||' | LC_ALL=C sort | tr '\n' ' ')
  finding "NOTE: $((n - parsed)) of $n headers did not parse (no opening or no closing ---): $unparsed"
fi
[ "$suspect" -gt 0 ] || [ "$a_sus" -gt 0 ] && finding "NOTE: $suspect of $n headers (and $a_sus in archive/) look like invalid YAML (an unquoted ': ', text after a closing quote, a value opening with a backtick, @ or %, an undefined escape, a colon in an unquoted list entry) — quote or fix them (File format)"
printf 'files: %s  parsed: %s  suspect (awk, a floor): %s  archive-suspect: %s  resurrected: %s\n' "$n" "$parsed" "$suspect" "$a_sus" "$nres"

# --- split store: a pre-3.0 log.md beside the directory -----------------------
# The creation command's LEGACY guard fires only when the directory is
# absent, so a legacy file written AFTER the migration — by an older
# installed copy the host still loads — sits beside the directory unseen.
# Report it with its entry count; the creation command refuses on it too.
lg="$root/skill-observations/log.md"
if [ -e "$lg" ]; then
  finding "SPLIT STORE — log.md holds $(grep -c '^### Observation ' "$lg" | tr -d ' ') observations not in observation-log/: an older installed copy of the skill still writes the legacy file; name each copy's version, then migrate the remainder (references/migration.md) with ids re-issued from this directory's counter"
fi
# The pre-3.0 staging root: an upgrade never moves it, and rounds staged
# there are invisible to a review that reads [workspace]/skill-updates/.
ls_old="$root/skill-observations/skill-updates"
if [ -d "$ls_old" ]; then
  finding "NOTE: legacy staging root skill-observations/skill-updates/ exists ($(find "$ls_old" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ') round directories) — 3.0+ pins [workspace]/skill-updates/; move its rounds and their PENDING entries by hand, then remove it"
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
  finding "NOTE: pointer at this root (skill-observations/MOVED.md): \"$mv_line\" — $mv_after entries written here since it; report both roots and ask, never consolidate or re-anchor on it"
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
[ -n "$gap" ] && finding "GAP: the previous session-start scan ran ${gap% *}, ${gap#* } days ago. If work happened in between, the skill was not activated in those sessions: check the activation instruction (references/environments.md, \"Verify activation in a NEW session\")"

# --- the trace: one line per session, with date, time and source -------------
printf '%s [%s] session-start scan: files=%s parsed=%s principles=%s\n' "$(date '+%F %H:%M')" "${PWD##*/}" "$n" "$parsed" "$pr" \
  >> "$root/skill-observations/checkpoints.log"

# --- sibling logs: every observation log up to three levels under the parent -
# A report, never a reason to consolidate from here.
find "$(dirname "$root")" -maxdepth 3 -type d -path '*/skill-observations/observation-log' 2>/dev/null | LC_ALL=C sort | while IFS= read -r o; do printf '%s=%s\n' "${o%/skill-observations/observation-log}" "$(find "$o" -maxdepth 1 -name '[0-9]*.md' | wc -l | tr -d ' ')"; done | awk '{s = s "  " $0} END {print "logs under the parent (report; never consolidate from here):" s}'

# --- content: printed with the headers below ---------------------------------
# The active principles' headings.
[ -f "$p" ] && awk "$pa"' a && /^### / {sub(/\r$/, ""); print}' "$p"
# Every numbered entry, one awk for the whole set over the directory's own
# glob (no word splitting of a spaced path). This is the only half a content
# classifier can refuse, so everything above has already run when it is.
# Step 2 holds four fields per entry, so the print carries those four and
# the id, one line each; the whole headers (about five times the bytes at a
# few hundred entries — enough for a session to cut the output) go to the
# headers file. With --entries-to, the listing goes to that file: a failed
# redirect skips the print and surfaces as the content print's exit status.
headers="$root/skill-observations/last-scan-headers.txt"
print_headers() {
  ( export LC_ALL=C; [ "$n" -eq 0 ] || { cd "$d" && awk 'FNR==1 && NR>1 && fm {print "---"}
    FNR==1 {sub(/^\357\273\277/, ""); fm=/^---[[:space:]]*$/; print "# " FILENAME; if (!fm) {print "---"; nextfile}; next}
    fm && /^---[[:space:]]*$/ {fm=0; print "---"; nextfile}
    fm
    END {if (fm) print "---"}' [0-9]*.md; } )
}
print_entries() {
  ( export LC_ALL=C; [ "$n" -eq 0 ] || { cd "$d" && awk -v skip="$res" 'function v(k) { if (k in bl) return "[" f[k] "]"; return (k in f && f[k] != "") ? f[k] : "-" }
    function emit(  l, s) { l = v("id") " | " v("status") " | " v("skill") " | " v("proposes_skill") " | " v("title")
      s = f["status"]; gsub(/["\047[:space:]]/, "", s)
      if (s ~ /^(actioned|declined|superseded)$/) l = v("id") " | " s " | " v("skill") " | " v("proposes_skill") " | resolved " v("resolved") " — title withheld"
      if (s == "parked") pk = pk l "\n"; else print l }
    FNR==1 {if (NR>1 && fm) print "--- " prev " (header not closed)"; split("", f); split("", bl); key = ""; prev = FILENAME
            if (skip != "" && index(skip, "/" FILENAME "/")) {fm=0; nextfile}
            sub(/^\357\273\277/, ""); fm=/^---[[:space:]]*$/; if (!fm) {print "--- " FILENAME " (no header)"; nextfile}; next}
    fm {sub(/\r$/, "")}
    fm && /^---[[:space:]]*$/ {fm=0; emit(); nextfile}
    fm && /^[A-Za-z_]+:/ {key=$0; sub(/:.*/, "", key); x=$0; sub(/^[A-Za-z_]+:[[:space:]]*/, "", x); sub(/[[:space:]]+$/, "", x); if (x !~ /^["\047]/) sub(/[[:space:]]+#.*$/, "", x); f[key]=x; next}
    fm && key != "" && f[key] == "" && /^[[:space:]]+-[[:space:]]/ {bl[key]=1}
    fm && key in bl && /^[[:space:]]+-[[:space:]]/ {x=$0; sub(/^[[:space:]]+-[[:space:]]*/, "", x); f[key] = (f[key] == "" ? x : f[key] ", " x); next}
    END {if (fm) print "--- " prev " (header not closed)"; printf "%s", pk}' [0-9]*.md; } )
}
hd_note="$headers"
print_headers > "$headers" 2>/dev/null || hd_note="$headers (write failed)"
if [ -n "$entries" ]; then
  print_entries > "$entries"; rc=$?
  ent="; entries written to $entries"
  # A zero-line entries file beside files: N > 0 is a broken run, not an
  # empty log: said in the summary block and the sidecar, and the exit is 3.
  if [ "$rc" -eq 0 ] && [ "$n" -gt 0 ] && [ ! -s "$entries" ]; then
    findings="${findings}NOTE: entries file '$entries' is empty beside files: $n — a broken run, not an empty log; re-run the scan into a new mktemp file"$'\n'
    rc=3; empty_ent=1
  fi
else
  print_entries; rc=$?
  ent=
fi

# --- LAST: the summary block — the findings again, then the end-of-scan line -
# The finding lines are repeated here VERBATIM, after the entries, and written
# to the sidecar file (overwritten every run; empty when there are none): a
# view cut to its last lines, or a grep over the end, still carries every
# finding, and a run that cut the output anyway finds them on disk. The end
# line repeats the counts, says how many finding lines stand above the
# entries, and names the sidecar; it is a pointer to the whole output, never
# its replacement.
sc="$sidecar"
printf '%s' "$findings" > "$sidecar" 2>/dev/null || sc="$sidecar (write failed)"
printf '%s' "$findings"
st=; [ "$rc" -eq 0 ] || st="; content print exited $rc"
[ -n "${empty_ent:-}" ] && st="; the entries file is EMPTY (exit 3)"
printf 'end of scan — files: %s  parsed: %s  suspect: %s  archive-suspect: %s  resurrected: %s  principles: %s; finding lines above the entries (DUE / NOTE / LOST ENTRIES / UNFILLED / DUPLICATE ID / RESURRECTED / SPLIT STORE / GAP): %s, repeated just above this line and written to %s%s%s; full headers in %s. Read the output whole: never cut it with head, tail or grep — session-start-scan.sh v%s\n' \
  "$n" "$parsed" "$suspect" "$a_sus" "$nres" "$pr" "$fx" "$sc" "$ent" "$st" "$hd_note" "$VERSION"
exit "$rc"
