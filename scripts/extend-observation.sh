#!/usr/bin/env bash
# extend-observation.sh — append a new instance to an existing observation,
# the entry resolved by its id at the moment of the write.
#
# Usage:
#   bash scripts/extend-observation.sh [--reopen] --body-file <file> --session <text> <id> [workspace-root]
#
#   <id>              the entry's number (7 or 0007)
#   [workspace-root]  the pinned absolute workspace path — the directory that
#                     holds skill-observations/. Defaults to the environment
#                     variable TASK_OBSERVER_WORKSPACE; never resolved from
#                     the cwd. The path may contain spaces.
#   --body-file <file> the paragraph to append (the new instance), written
#                     by the caller with a QUOTED heredoc; copied verbatim
#                     below the entry's body, after one blank line
#   --session <text>  one line naming this session; added to the header's
#                     session_context: (joined with "; ", double-quoted)
#   --reopen          the entry is archived or resolved and the new instance
#                     shows its fix did not hold: an archived file moves back
#                     to observation-log/, status: becomes open, resolved: is
#                     emptied (resolution: stays as the record), and the
#                     appended text opens with a line saying so
#
# The id is looked up across observation-log/ and archive/ when the script
# runs, never taken from a path the session remembers: a redirect onto a
# remembered path creates whatever is missing, so an entry archived since
# the path was read came back as a headerless stub that every scan reads as
# an open entry. Refused by name, exit 1, nothing written:
#   NO SUCH ENTRY   no file carries the id (no file is ever created here)
#   DUPLICATE ID    two files carry it (renumber first: set-fields.sh)
#   ENTRY CLOSED    the match is archived, or its status is actioned,
#                   declined or superseded, and --reopen was not given; its
#                   resolution: is printed, with the two other ways on: a
#                   new entry citing the id, or a carrier for an unapplied
#                   remainder (references/observation-families.md)
#   and a header that does not open and close, an id: that does not read as
#   the filename prefix, a session_context: written as a block value, or a
#   body file that is missing or blank.
# A parked entry is extended in place, its status unchanged, with a NOTE.
#
# The new text is built in a scratch directory and checked before the
# write: every line of the old file in place except session_context: (and,
# with --reopen, status: and resolved:), the appended lines after it. The
# file is re-read just before the write and the run stops if it changed;
# the write goes through a hidden temp file and `mv`, then is re-read
# against the checked text. Prints the written file's path (one line).
#
# Exit status: 0 written, 1 refused or failed, 2 usage.
# bash, not sh; runs on bash 3.2 (stock macOS): case patterns parenthesised.

set -u

body=; sess=; reopen=; id=; root=; sset=; npos=0
while [ $# -gt 0 ]; do
  case $1 in
    (--body-file) [ $# -ge 2 ] || { echo "--body-file needs a file argument" >&2; exit 2; }; body=$2; shift 2 ;;
    (--body-file=*) body=${1#--body-file=}; shift ;;
    (--session) [ $# -ge 2 ] || { echo "--session needs a text argument" >&2; exit 2; }; sess=$2; sset=1; shift 2 ;;
    (--session=*) sess=${1#--session=}; sset=1; shift ;;
    (--reopen) reopen=1; shift ;;
    (--*) echo "unknown option: $1" >&2; exit 2 ;;
    (*) npos=$((npos + 1))
        case $npos in (1) id=$1 ;; (2) root=$1 ;; (*) echo "too many arguments: $1" >&2; exit 2 ;; esac
        shift ;;
  esac
done
[ -n "$root" ] || root="${TASK_OBSERVER_WORKSPACE:-}"
usage="usage: extend-observation.sh [--reopen] --body-file <file> --session <text> <id> [workspace-root]"
[ -n "$id" ] && [ -n "$body" ] && [ -n "$sset" ] || { echo "$usage" >&2; exit 2; }
case $id in (*[!0-9]*|"") echo "the id must be a number: got '$id'" >&2; exit 2 ;; esac
n=$((10#$id)); [ "$n" -gt 0 ] || { echo "the id must be a number above 0: got '$id'" >&2; exit 2; }
miss=
for t in awk sed grep cat cmp cp mv mktemp date tr tail; do command -v "$t" >/dev/null 2>&1 || miss="$miss $t"; done
[ -z "$miss" ] || { printf 'TOOLS MISSING —%s not on PATH; nothing written\n' "$miss" >&2; exit 1; }
[ -n "$root" ] || { echo "no workspace root: pass it after the id or set TASK_OBSERVER_WORKSPACE" >&2; exit 2; }
case $root in
  (/*|[A-Za-z]:[/\\]*) ;;
  (*) echo "workspace root must be an ABSOLUTE path, never relative to the cwd: got '$root'" >&2; exit 2 ;;
esac
{ [ -f "$body" ] && [ -r "$body" ] && grep -q '[^[:space:]]' "$body"; } || { echo "--body-file is missing, unreadable or blank: '$body'; nothing written" >&2; exit 1; }
case $sess in
  (*$'\n'*|*$'\r'*|*$'\t'*) echo "--session must be one line with no tab; nothing written" >&2; exit 1 ;;
esac
[ -n "$(printf '%s' "$sess" | tr -d '[:space:]')" ] || { echo "--session is blank; nothing written" >&2; exit 1; }
d="$root/skill-observations/observation-log"
if [ ! -d "$d" ] || [ ! -d "$d/archive" ]; then
  echo "STRUCTURE MISSING — expected '$d' and '$d/archive'; nothing written, never recreated from here" >&2; exit 1
fi

# --- resolve the id NOW, across active and archive ---------------------------
hits=
for p in "$d"/[0-9]*.md "$d"/archive/[0-9]*.md; do
  [ -f "$p" ] || continue
  b=${p##*/}; pre=${b%%[!0-9]*}
  [ "$((10#$pre))" -eq "$n" ] && hits="$hits${hits:+|}${p#"$d"/}"
done
case $hits in
  ("") echo "NO SUCH ENTRY — id $n matches no file in observation-log/ or archive/; nothing written and no file created. Check the number against the log as it stands now; an id carried in memory may be stale" >&2; exit 1 ;;
  (*"|"*) echo "DUPLICATE ID — id $n is carried by $(printf '%s' "$hits" | sed 's/|/ and /g'); nothing written. Renumber one first (scripts/set-fields.sh, a rename line)" >&2; exit 1 ;;
esac
f=$hits; p="$d/$f"; arch=; case $f in (archive/*) arch=1 ;; esac

t=$(mktemp -d 2>/dev/null) || { echo "cannot create a scratch directory (mktemp -d)" >&2; exit 1; }
trap 'rm -rf "$t"' EXIT   # the scratch directory this run created, nothing else
cp "$p" "$t/old" || { echo "cannot read $f; nothing written" >&2; exit 1; }
# H <close line> | K <line> <key> | C <line> (an indented continuation) | NOHDR | OPEN
LC_ALL=C awk 'FNR==1 {sub(/^\357\273\277/, ""); if (!/^---[[:space:]]*$/) {print "NOHDR"; exit}; fm=1; next}
  fm && /^---[[:space:]]*$/ {print "H " FNR; fm=0; exit}
  fm && /^[A-Za-z_][A-Za-z0-9_]*:/ {k=$0; sub(/:.*/, "", k); print "K " FNR " " k; next}
  fm && /^[[:space:]]+[^[:space:]#]/ {print "C " FNR}
  END {if (fm) print "OPEN"}' "$t/old" > "$t/map"
grep -q '^NOHDR\|^OPEN' "$t/map" && { echo "$f: the header does not open on line 1 or does not close; nothing written — fix it with the editing tool" >&2; exit 1; }
val() {   # the one-line value of header key $1, quotes kept
  LC_ALL=C awk -v k="$1" '/^---[[:space:]]*$/ {if (++c == 2) exit; next} c == 1 && index($0, k ":") == 1 {v = substr($0, length(k) + 2); sub(/^[[:space:]]+/, "", v); sub(/[[:space:]\r]+$/, "", v); print v; exit}' "$t/old"
}
idv=$(val id | tr -d "\"'"); pre=${f##*/}; pre=${pre%%[!0-9]*}
case $idv in (""|*[!0-9]*) echo "$f: id: does not read as a number (read '$idv'); nothing written" >&2; exit 1 ;; esac
[ "$((10#$idv))" -eq "$((10#$pre))" ] || { echo "$f: id: $idv does not read as the filename prefix $pre; nothing written — fix that first" >&2; exit 1; }
st=$(val status | sed 's/[[:space:]]#.*$//' | tr -d "\"' ")
closed=; case $st in (actioned|declined|superseded) closed=$st ;; esac
if { [ -n "$arch" ] || [ -n "$closed" ]; } && [ -z "$reopen" ]; then
  printf 'ENTRY CLOSED — %s is %s; nothing written. Its resolution: %s\nA new instance of a closed finding is a new entry citing #%s, or a carrier holding an unapplied remainder (references/observation-families.md, the carrier pattern); re-run with --reopen only when the instance shows the fix did not hold\n' \
    "$f" "${arch:+archived}${arch:+${closed:+, }}${closed:+status $closed}" "$(val resolution)" "$n" >&2
  exit 1
fi
nsc=$(grep -c ' session_context$' "$t/map")
[ "$nsc" -eq 1 ] || { echo "$f: session_context: occurs $nsc times in the header, not once; nothing written" >&2; exit 1; }
ln=$(sed -n 's/^K \([0-9]*\) session_context$/\1/p' "$t/map")
grep -q "^C $((ln + 1))\$" "$t/map" && { echo "$f: session_context: holds a block value — extend it with the editing tool; nothing written" >&2; exit 1; }

# --- the new session_context value: old text and this session, double-quoted -
old=$(val session_context)
case $old in
  ('""'|"''"|"") inner= ;;
  (\"*\") inner=${old#\"}; inner=${inner%\"} ;;
  (\'*\') inner=${old#\'}; inner=${inner%\'}; inner=$(printf '%s' "$inner" | sed "s/''/'/g; s/\\\\/\\\\\\\\/g; s/\"/\\\\\"/g") ;;
  (*) inner=$(printf '%s' "$old" | sed 's/[[:space:]]#.*$//; s/\\/\\\\/g; s/"/\\"/g') ;;
esac
add=$(printf '%s' "$sess" | sed 's/\\/\\\\/g; s/"/\\"/g')
today=$(date +%F)
note=; [ -n "$reopen" ] && [ -n "$arch$closed" ] && note="Re-opened on $today from ${closed:-its archived state}${arch:+${closed:+, archived}}; the resolution above stays as the record."
SC="\"$inner${inner:+; }$add\"" RE="$reopen$closed" LC_ALL=C awk 'FNR==1 {fm=1; print; next}
  fm && /^---[[:space:]]*$/ {fm=0; print; next}
  fm && /^session_context:/ {print "session_context: " ENVIRON["SC"]; next}
  fm && ENVIRON["RE"] != "" && /^status:/ {print "status: open"; next}
  fm && ENVIRON["RE"] != "" && /^resolved:/ {print "resolved:"; next}
  {print}' "$t/old" > "$t/new"
{ printf '\n'; [ -n "$note" ] && printf '%s\n\n' "$note"; cat "$body"; [ -z "$(tail -c 1 "$body")" ] || printf '\n'; } >> "$t/new"
# the invariant: the old lines in place except the named keys, the rest appended
bad=$(LC_ALL=C awk -v re="$reopen$closed" 'FILENAME == ARGV[1] {o[FNR] = $0; on = FNR; next}
  {nw[FNR] = $0; nn = FNR}
  END {if (nn <= on) print "LINES"
    for (j = 1; j <= on; j++) if (o[j] != nw[j]) {k = o[j]; sub(/:.*/, "", k)
      if (!(k == "session_context" || (re != "" && (k == "status" || k == "resolved"))) || index(nw[j], k ":") != 1) print "LINE " j}}' "$t/old" "$t/new")
[ -z "$bad" ] || { echo "$f: the new text would change lines other than the named keys ($(printf '%s' "$bad" | tr '\n' ' ')); nothing written" >&2; exit 1; }

# --- write: re-read, move back (--reopen of an archived file), replace, re-read
cmp -s "$t/old" "$p" || { echo "CHANGED SINCE READ — $f changed while this run built its text; nothing written, re-run" >&2; exit 1; }
if [ -n "$arch" ]; then
  dest="$d/${f#archive/}"
  [ -e "$dest" ] && { echo "$dest exists beside archive/$f; nothing written — compare the two by hand" >&2; exit 1; }
  mv -n "$p" "$dest" && [ ! -e "$p" ] || { echo "MOVE FAILED — archive/$f could not move back to observation-log/; nothing written" >&2; exit 1; }
  p=$dest
fi
part="${p%/*}/.${p##*/}.part"
cp "$t/new" "$part" && mv -f "$part" "$p" || { echo "WRITE FAILED — $p keeps its old text${arch:+ (moved out of archive/; the next archival sweep returns it)}" >&2; exit 1; }
cmp -s "$t/new" "$p" || { echo "VERIFY FAILED — $p does not hold the checked text" >&2; exit 1; }
[ "$st" = parked ] && echo "NOTE: $f is parked; the instance is appended and the status left parked — check whether it meets parked_until:" >&2
printf '%s\n' "$p"
