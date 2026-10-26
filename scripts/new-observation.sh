#!/usr/bin/env bash
# new-observation.sh — derive the next observation id AND create the file,
# as one command that cannot be split.
#
# Usage:
#   bash scripts/new-observation.sh [--body <entry-file>] <slug> [workspace-root]
#
#   <slug>            kebab-case, no id prefix, no extension ("short-slug")
#   [workspace-root]  the pinned absolute workspace path — the directory that
#                     holds skill-observations/. Defaults to the environment
#                     variable TASK_OBSERVER_WORKSPACE. One of the two is
#                     required; the log is never resolved from the cwd.
#   --body <entry-file> optional, before or after the slug: once the file is
#                     created, <entry-file> (the COMPLETE entry, frontmatter and body, written by the
#                     caller with a QUOTED heredoc) is copied into it with
#                     the literal placeholders __ID__ and __DATE__ replaced
#                     everywhere by the issued id and today's date
#                     (YYYY-MM-DD). A quoted heredoc cannot carry the id, and
#                     an unquoted one runs every backticked span in the body;
#                     this flag fills the two values so neither is needed.
#                     The body's header is checked BEFORE anything is
#                     touched: `status:` must read `open`, `type:` must be
#                     `open-source` or `internal`, and `siblings_checked:`
#                     must be non-empty, and no header line may trip the
#                     scan's suspect-YAML rules (an unquoted `: ` and the
#                     rest) — a header breaking any of these is refused by
#                     name (BODY REFUSED) and no file, claim or floor write
#                     happens. The three fields are the ones a writer
#                     measurably forgets, the YAML shape the one the next
#                     session's scan would catch too late; a rule with no
#                     gate behind it is a convention; the gate is here
#                     because this is the only write path.
#
# Prints the created file's absolute path on stdout (one line) and exits 0.
# Any guard firing prints its message on stderr and exits 1 with NO file
# created. The file is never empty: the create writes a frontmatter
# skeleton — `id:` (the number, unpadded), `date:` today, `status: open`,
# every other field present and empty — so a scan that meets it mid-write
# reads a header with its id, not a LOST entry, and the id is on disk
# before anything can retype it. Without --body, fill the skeleton's
# fields in place (the `id:` line is already right: copy nothing, retype
# nothing) and append the body below the closing `---`. With --body, the
# filled copy is built beside the file and renamed over it, so the file
# holds either the skeleton or the whole body, never a part.
#
# This is the id-derivation snippet from SKILL.md "How to Log", plus a
# number claim the inline snippet lacks, packaged so that the moment of
# derivation cannot drift away from the moment of writing: an id derived
# at session start and carried in memory to a later write is the collision
# the snippet's rules forbid, and a rule that has failed twice while loaded
# needs the write path itself to enforce it. Where this script can run, it
# is the only write path.
#
# Steps, in order: body header check (--body only; a refusal touches
# nothing) → archival sweep of stale resolved files (a side effect of
# deriving the id, never a separate duty; a same-named archived file is
# never overwritten) → id = max(active prefixes, archive prefixes,
# .id-floor) + 1, the listing guarded against find's count before the floor
# enters → DUPLICATE PREFIX refusal (two files across active and archive
# already sharing a number: no id is issued until one is renumbered; an
# active file byte-identical to its archive/ copy is refused as RESURRECTED,
# remove the active copy) → number claim (a noclobber marker per id in archive/.id-claims/,
# so two writers running at once never share one) → PREFIX collision guard
# across active and archive (two slugs sharing one number is the failure; a
# path check cannot see it) → noclobber create of the skeleton → floor
# write (after the create, so a run that creates nothing never moves it) →
# body copy with the placeholders filled, built as a hidden sibling and
# renamed into place (--body only) → id check on the written header →
# print the path.
#
# bash, not sh: the `10#` arithmetic is a bash extension. Runs on bash 3.2
# (stock macOS): case patterns are parenthesised for that reason, and the
# argument loop uses no array.

set -u

slug=; root=; body=; npos=0
while [ $# -gt 0 ]; do
  case $1 in
    (--body)
      [ $# -ge 2 ] || { echo "--body needs a file argument" >&2; exit 1; }
      body=$2; shift 2 ;;
    (--body=*) body=${1#--body=}; shift ;;
    (--*) echo "unknown option: $1" >&2; exit 1 ;;
    (*)
      npos=$((npos + 1))
      case $npos in
        (1) slug=$1 ;;
        (2) root=$1 ;;
        (*) echo "too many arguments: $1" >&2; exit 1 ;;
      esac
      shift ;;
  esac
done
[ -n "$root" ] || root="${TASK_OBSERVER_WORKSPACE:-}"

if [ -z "$slug" ]; then
  echo "usage: new-observation.sh [--body <entry-file>] <slug> [workspace-root]" >&2; exit 1
fi
if [ -n "$body" ] && ! { [ -f "$body" ] && [ -r "$body" ]; }; then
  echo "--body file is missing or unreadable: '$body'" >&2; exit 1
fi
# --- the suspect-YAML rules of session-start-scan.sh, as one program `sus` ---
# Kept in one form for both scripts: the selftest asserts the text between
# the two markers is identical in each. Each rule prints the file, its
# number and the line it fired on (rules: session-start-scan.sh, "suspect").
# >>> sus: shared with session-start-scan.sh, byte for byte (the selftest compares them)
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

# --- body schema: refuse a header the log's rules forbid, before any write ---
# Read as data, like the copy below. A value is taken bare, with a trailing
# `# comment` (the core template carries one on status: and type:) and
# trailing spaces stripped; status words stay bare, so a quoted `"open"` is
# refused too — the archival sweep reads `$2` and would never match it.
if [ -n "$body" ]; then
  why=$(LC_ALL=C awk '
    FNR==1 {sub(/^\357\273\277/, ""); if (/^---[[:space:]]*$/) fm=1; else nofm=1; next}
    fm && /^---[[:space:]]*$/ {closed=1; exit}
    fm && /^status:/ {st=$0; sub(/^status:[[:space:]]*/, "", st); sub(/[[:space:]]+#.*$/, "", st); sub(/[[:space:]]+$/, "", st); hs=1}
    fm && /^type:/ {ty=$0; sub(/^type:[[:space:]]*/, "", ty); sub(/[[:space:]]+#.*$/, "", ty); sub(/[[:space:]]+$/, "", ty); ht=1}
    fm && /^siblings_checked:/ {sc=$0; sub(/^siblings_checked:[[:space:]]*/, "", sc); sub(/[[:space:]]+$/, "", sc); hc=1}
    END {
      if (nofm) {print "line 1 is not ---"; exit}
      if (!closed) {print "the header never closes (no second ---)"; exit}
      if (!hs || st != "open") print "status: must read open" (hs ? " (read \047" st "\047)" : " (missing)")
      if (!ht || (ty != "open-source" && ty != "internal")) print "type: must be open-source or internal" (ht ? " (read \047" ty "\047)" : " (missing)")
      if (!hc || sc == "" || sc == "\"\"" || sc == "\047\047") print "siblings_checked: must be non-empty" (hc ? "" : " (missing)")
    }' "$body")
  # The scan's suspect rules, run here before the write: a header the next
  # session's scan would flag as invalid YAML is refused by name instead.
  sh_why=$(LC_ALL=C awk "$sus" "$body" | awk -F '\t' '{k=$3; sub(/:.*/, "", k)
    r = ($2 == 3 ? "holds an unquoted \047: \047" : $2 == 4 ? "has text after its closing quote" : $2 == 5 ? "opens with a backtick, @ or %" : $2 == 6 ? "holds an escape YAML does not define" : "is a [ ] list with a colon outside quotes")
    print k ": " r " — fix or quote the value (line: " $3 ")"}')
  [ -n "$sh_why" ] && why="$why${why:+
}$sh_why"
  if [ -n "$why" ]; then
    printf 'BODY REFUSED — no file created; fix the header of %s:\n%s\n' "$body" "$why" >&2; exit 1
  fi
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
# A Windows drive path (C:/... or C:\...) is absolute there and relative on
# POSIX, so it is accepted only where cygpath can convert it (Git Bash, MSYS,
# Cygwin); the printed path is converted back, into the form the pin used.
pin_form=
case $root in
  ([A-Za-z]:[/\\]*)
    command -v cygpath >/dev/null 2>&1 || { echo "workspace root is a drive-letter path but cygpath is not available to convert it: got '$root'" >&2; exit 1; }
    root=$(cygpath -u "$root"); pin_form=-m ;;
esac
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
n_files=$(find "$d" -maxdepth 1 -name '[0-9]*.md' ! -empty | wc -l | tr -d ' ')   # a zero-byte file gives awk no line to count
seen=$(cd "$d" && awk 'FNR==1 {n++; nextfile} END {print n+0}' [0-9]*.md 2>/dev/null)   # files the sweep's glob reaches, counted apart from the sweep
if [ "$n_files" -gt 0 ] && [ "${seen:-0}" -eq 0 ]; then
  echo "ARCHIVAL SWEEP BROKEN — $n_files files present, 0 examined" >&2; exit 1
fi
# one awk for the whole set (a process per file crosses a tool timeout on a
# large log); one mv per stale resolved file, bounded by the files due
( cd "$d" && LC_ALL=C awk -v today="$today" 'FNR==1 {st=""; r=""; sub(/^\357\273\277/, ""); fm=/^---[[:space:]]*$/; if (!fm) nextfile; next}
    fm && /^---[[:space:]]*$/ {if (st ~ /^(actioned|declined|superseded)$/ && r ~ /^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]$/ && r < today) print FILENAME; nextfile}
    fm && /^status:/ {st=$2}
    fm && /^resolved:/ {r=$2}' [0-9]*.md 2>/dev/null | while IFS= read -r x; do
      mv -n "$x" archive/ 2>/dev/null   # -n: never overwrite a same-named archived file
      if [ -e "$x" ]; then
        if [ -e "archive/$x" ]; then echo "NOTE: $x not archived — archive/$x already exists; compare the two copies by hand" >&2
        else echo "NOTE: $x not archived — the move failed" >&2; fi
      fi
    done )

# --- id: max of active prefixes, archive prefixes and the floor, plus one ---
# Globs and builtins list the files, never `ls`: a profile alias or function
# can rebind that word. The floor is read as digits only (a CRLF or padded
# file still reads), and 10# keeps a zero-padded number out of octal.
floor=$(sed '1!d; s/[^0-9]//g' "$d/archive/.id-floor" 2>/dev/null); floor=$((10#${floor:-0}))
# Up to three attempts, a second apart: a writer running at the same moment
# can create a file between the listing and find's count; a broken listing
# disagrees every time.
for attempt in 1 2 3; do
  ids=$(for p in "$d"/[0-9]*.md "$d"/archive/[0-9]*.md; do [ -e "$p" ] && printf '%s\n' "${p##*/}"; done | grep -oE '^[0-9]+')
  [ "$(printf '%s' "$ids" | grep -c .)" -eq "$(find "$d" "$d/archive" -maxdepth 1 -name '[0-9]*.md' | wc -l)" ] && break
  if [ "$attempt" -eq 3 ]; then
    echo "ID COMMAND BROKEN — the listing and find disagree on the prefixed files" >&2; exit 1
  fi
  sleep 1
done

# --- duplicate prefix: no id is issued while two files share one ------------
# The uniqueness invariant is enforced here, on the write path, where it can
# break; the scan's DUPLICATE ID line only reports it when read. Numbers are
# compared as numbers, so 0007- and 7- are one id. The renumber keeps the
# cited (else the earlier) file's number and re-creates the other through
# this helper, which this refusal would block while both are listed: so it is
# moved out of the listing first (a leading dot, which no `[0-9]*.md` glob
# sees), re-created from it with --body, and the moved copy deleted.
dup=$(for p in "$d"/[0-9]*.md "$d"/archive/[0-9]*.md; do [ -e "$p" ] && printf '%s\n' "${p#"$d"/}"; done \
  | LC_ALL=C awk '{b=$0; sub(/^archive\//, "", b); n=substr(b, 1, match(b, /[^0-9]/) - 1) + 0; if (n in s) {print n "|" s[n] "|" $0; exit}; s[n]=$0}')
if [ -n "$dup" ]; then
  dn=${dup%%|*}; rest=${dup#*|}
  # An active file byte-identical to its same-named archive/ copy is a
  # restored archive entry (a sync or mirror), not a collision: never renumber.
  d1=${rest%%|*}; d2=${rest#*|}
  if [ "archive/$d1" = "$d2" ] && command -v cmp >/dev/null 2>&1 && cmp -s "$d/$d1" "$d/$d2"; then
    printf 'RESURRECTED — %s is byte-identical to %s: a sync or mirror restored an archived entry; no id is issued while it stands. Remove the active copy (never renumber it) and record the sync client (references/environments.md, "Stable is not the same as always available")\n' "$d1" "$d2" >&2
    exit 1
  fi
  printf 'DUPLICATE PREFIX — id %s is carried by both %s and %s; no id is issued while it stands. Renumber first: keep the number on the file something cites, else the earlier one (by date:); move the other out of the listing (rename it with a leading dot), set its id: to __ID__, re-create it with --body <the moved file>, then delete the moved copy; or renumber it in one step with a set-fields.sh rename line (references/observation-log.md, "Assigning an id")\n' \
    "$dn" "${rest%%|*}" "${rest#*|}" >&2
  exit 1
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
if [ -s "$d/archive/.id-floor" ] && [ -n "${top_active:-}" ] && [ "$floor" -lt "$((10#$top_active))" ] \
   && [ ! -e "$d/archive/.id-claims/$(printf '%04d' "$((10#$top_active))")" ]; then   # a claimed id is a writer still running, not a skip
  echo "NOTE: .id-floor ($floor) is below the highest active id ($((10#$top_active))) — an issuer skipped the floor write; corrected now" >&2
fi

# --- claim the NUMBER atomically ---------------------------------------------
# Two writers running at once derive the same number from the same listing,
# and the guard below cannot see a file the other has not created yet. The
# claim is a noclobber create of an empty marker named by the number alone,
# so exactly one writer gets each number; the other moves up one and tries
# again. Markers are never removed (nothing here needs delete permission),
# and a marker left by a run that stopped before its create only leaves a
# gap in the ids.
c="$d/archive/.id-claims"
mkdir -p "$c" || { echo "CLAIM DIR FAILED — cannot create '$c'" >&2; exit 1; }
tries=0
until (set -C; : > "$c/$prefix") 2>/dev/null; do
  tries=$((tries + 1))
  if [ "$tries" -ge 100 ]; then
    echo "CLAIM FAILED — 100 consecutive numbers up to $next_id already claimed under '$c'" >&2; exit 1
  fi
  next_id=$((next_id + 1)); prefix=$(printf '%04d' "$next_id")
done

# --- collision guard on the id PREFIX, across active and archive ------------
# Two writers deriving the same number with different slugs produce two
# different paths; a path check passes both. The invariant is a unique
# number, so the guard is keyed on the number.
if [ -n "$(find "$d" -maxdepth 2 -name "${prefix}-*.md")" ]; then
  echo "COLLISION — id $next_id already used; re-derive (re-run this script)" >&2; exit 1
fi

# --- noclobber create: never truncate an existing file ----------------------
# The create and the first content are one printf: the file is a header
# with its id from the first instant it exists. An empty file in the log is
# a LOST entry by definition (the scan says so), and a create that leaves
# one is a LOST entry for as long as the caller takes to write the body.
# The field list mirrors the core template (How to Log) in its order, the
# optional and conditional fields included (commands_verified, next_actor,
# use_evidence, escalated): a copy that claims to mirror a template drifts the moment
# the template gains a field, so the selftest asserts each field is here.
# `title:` is left empty on purpose — the scan reports a header with an
# empty title as UNFILLED, a write in progress or abandoned, distinct from
# LOST.
f="$d/${prefix}-${slug}.md"
skel=$(printf '%s\nid: %s\ntitle: ""\nstatus: open\ntype:\nskill: []\nproposes_skill: []\ntarget_file: []\nsiblings_checked: ""\narea: ""\ndate: %s\nsession_context: ""\nparked_until:\nresolved:\nresolution:\nreference:\ncommands_verified:\nnext_actor:\nuse_evidence:\nescalated:\n---' --- "$next_id" "$today")   # the format opens with %s: a leading --- reads as an option
if ! (set -C; printf '%s\n' "$skel" > "$f") 2>/dev/null; then
  echo "CREATE FAILED — $f exists or is unwritable" >&2; exit 1
fi

# --- floor write, after the create: never lower (next_id > floor) ------------
# The floor takes the highest CLAIMED number, not only this run's: a writer
# that finished first must not be left above the floor by a slower one.
top_claim=$(for p in "$c"/[0-9]*; do [ -e "$p" ] && printf '%s\n' "${p##*/}"; done | sort -n | tail -1)
top_claim=$((10#${top_claim:-0})); [ "$top_claim" -gt "$next_id" ] || top_claim=$next_id
printf '%s\n' "$top_claim" > "$d/archive/.id-floor" || { echo "FLOOR WRITE FAILED — $d/archive/.id-floor (the file $f exists; fix the floor by hand)" >&2; exit 1; }

# --- body copy, placeholders filled (--body only) ----------------------------
# The body file is read as data: sed matches the two literal placeholders
# (no regex metacharacters in either) and the replacements are an integer
# and a YYYY-MM-DD date, so nothing needs escaping and every other byte —
# backticks, $, quotes — reaches the file verbatim. Plain `s///g`, no -i and
# no GNU-only flag: BSD sed runs this too. The filled copy is built as a
# hidden sibling (a leading dot: no `[0-9]*.md` listing or glob sees it)
# and renamed over the skeleton, one atomic step, so no reader ever meets
# the file truncated. Where the rename is refused (a mount that treats
# replacing a file as a delete), the copy is written in place instead and
# the sibling is left for the user — nothing here deletes.
if [ -n "$body" ]; then
  part="$d/.${prefix}-${slug}.md.part"
  if ! sed -e "s/__ID__/$next_id/g" -e "s/__DATE__/$today/g" "$body" > "$part"; then
    echo "BODY COPY FAILED — $f holds the frontmatter skeleton only; write the body into it by hand (id $next_id)" >&2; exit 1
  fi
  if ! mv -f "$part" "$f" 2>/dev/null; then
    if cat "$part" > "$f"; then
      echo "NOTE: rename refused — body copied in place; remove '$part' by hand" >&2
    else
      echo "BODY COPY FAILED — $f holds the frontmatter skeleton only; the filled copy is at '$part' (id $next_id)" >&2; exit 1
    fi
  fi
  # The id in the written header must be the one this run issued: a body
  # that carried a literal id instead of __ID__ is the mismatch the scan
  # reports; say so here, where the body is still in hand.
  got=$(LC_ALL=C awk 'FNR==1 {sub(/^\357\273\277/, "")} /^---[[:space:]]*$/ {if (++n == 2) exit; next} n == 1 && /^id:/ {v=$2; gsub(/["\047\r]/, "", v); print v; exit}' "$f")
  case $got in
    (*[!0-9]*|"") echo "NOTE: $f carries no numeric id: in its header (read '$got'); set id: $next_id" >&2 ;;
    (*) [ "$((10#$got))" -eq "$next_id" ] || echo "NOTE: $f carries id: $got but its prefix is $prefix — the body held a literal id; set id: $next_id" >&2 ;;
  esac
fi

if [ -n "$pin_form" ]; then cygpath "$pin_form" "$f"; else printf '%s\n' "$f"; fi
