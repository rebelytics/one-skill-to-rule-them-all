#!/usr/bin/env bash
# set-fields.sh — change named frontmatter fields in several existing
# observation entries, or renumber one, as one checked command: the path for
# a change that touches more than one entry.
#
# Usage:
#   bash scripts/set-fields.sh [--check] <workspace-root> <plan-file>
#
#   <workspace-root>  the pinned absolute workspace path — the directory that
#                     holds skill-observations/. Never resolved from the cwd;
#                     the path may contain spaces.
#   <plan-file>       one operation per line, fields separated by ONE tab;
#                     blank lines and lines opening with # are skipped:
#       set<TAB><file><TAB><key><TAB><value>
#                     the header's one `key:` line becomes `key: <value>`;
#                     <value> is the YAML text exactly as it is to be
#                     written, so a prose value carries its double quotes
#       rename<TAB><file><TAB>next
#                     the entry takes a fresh id from the counter (as the
#                     creation helper issues one); its filename prefix and
#                     its `id:` change together and the body gains a line
#                     naming the old number
#                     <file> is a name in observation-log/ (`0012-slug.md`)
#                     or under its archive/ (`archive/0012-slug.md`).
#   --check           run phase 1 only and write nothing
#
# Phase 1 writes nothing to the log. It builds every file's new text in a
# scratch directory and checks each: the header opens on line 1 and closes;
# `id:` reads as the filename prefix before the change and after it; every
# named key occurs exactly once in the old header and in the new one; no
# header key occurs twice; a named key holds a one-line value (a block value
# is edited with the editing tool); the new text differs from the old ONLY on
# the named keys' lines — every other line in place, byte for byte — plus the
# renumber line a rename appends; and no new header line trips the scan's
# suspect-YAML rules. Any failure refuses the WHOLE plan by name (exit 1):
# a batch that is half applied is the state this script exists to prevent.
#
# Phase 2 re-reads every file and stops before any write if one changed since
# phase 1; claims each rename's number (a noclobber marker in
# archive/.id-claims/, as the creation helper does); writes each file through
# a hidden temp file and `mv` (a rename then moves the file to its new name,
# never over an existing one); writes .id-floor after the renames; and
# re-reads every written file against the text phase 1 built. A mismatch is
# VERIFY FAILED, exit 1, naming the file.
#
# Exit status: 0 done (or --check passed), 1 refused or failed, 2 usage.
#
# Why a script: a loop written for the occasion once wrote one entry's lines
# over another's file with every count intact; the check that would have
# caught it is "the new text differs from the old only on the named lines",
# and a check a session must remember to run is a convention. The rename
# matches the creation helper's duplicate-prefix renumber: a fresh number
# from the counter, filename and `id:` together, the old number noted in the
# body (references/observation-log.md, "Assigning an id").
#
# bash, not sh; runs on bash 3.2 (stock macOS): no arrays of arrays, no
# mapfile, case patterns parenthesised.

set -u

check=
while [ $# -gt 0 ]; do
  case $1 in
    (--check) check=1; shift ;;
    (--) shift; break ;;
    (-*) echo "unknown option '$1' (the option is --check)" >&2; exit 2 ;;
    (*) break ;;
  esac
done
[ $# -eq 2 ] || { echo "usage: set-fields.sh [--check] <workspace-root> <plan-file>" >&2; exit 2; }
root=$1; plan=$2
case $root in
  (/*|[A-Za-z]:[/\\]*) ;;
  (*) echo "workspace root must be an ABSOLUTE path, never relative to the cwd: got '$root'" >&2; exit 2 ;;
esac
[ -f "$plan" ] && [ -r "$plan" ] || { echo "plan file is missing or unreadable: '$plan'" >&2; exit 2; }
d="$root/skill-observations/observation-log"
if [ ! -d "$d" ] || [ ! -d "$d/archive" ]; then
  echo "STRUCTURE MISSING — expected '$d' and '$d/archive'; nothing written" >&2; exit 1
fi

# --- the suspect-YAML rules of session-start-scan.sh, as one program `sus` ---
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

t=$(mktemp -d 2>/dev/null) || { echo "cannot create a scratch directory (mktemp -d)" >&2; exit 1; }
trap 'rm -rf "$t"' EXIT   # the scratch directory this run created, nothing else
refuse=
no() { refuse="$refuse  $1"$'\n'; }

# --- the plan, read as data --------------------------------------------------
# One normalised line per operation: op TAB file TAB key TAB value.
LC_ALL=C awk -F '\t' -v OFS='\t' '
  /^[[:space:]]*$/ || /^#/ {next}
  $1 == "set"    && NF >= 4 && $2 != "" && $3 ~ /^[a-z_]+$/ {v = $0; for (i = 1; i <= 3; i++) sub(/^[^\t]*\t/, "", v); print "set", $2, $3, v; next}
  $1 == "rename" && NF == 3 && $2 != "" && $3 == "next" {print "rename", $2, "", ""; next}
  {print "bad", NR, "-", $0}' "$plan" > "$t/ops"   # no empty field: a tab IFS collapses two tabs into one
while IFS="$(printf '\t')" read -r op f k v; do
  case $op in (bad) no "plan line $f is not 'set<TAB>file<TAB>key<TAB>value' or 'rename<TAB>file<TAB>next': $v" ;; esac
done < "$t/ops"
[ -s "$t/ops" ] || no "the plan holds no operation"
cut -f 2 "$t/ops" | grep -v '^[0-9]*$' | awk '!s[$0]++' > "$t/files"   # each named file once, in plan order

# --- phase 1: build and check every new text; write nothing to the log ------
floor=$(sed '1!d; s/[^0-9]//g' "$d/archive/.id-floor" 2>/dev/null); floor=$((10#${floor:-0}))
hi=$(for p in "$d"/[0-9]*.md "$d"/archive/[0-9]*.md; do [ -e "$p" ] && printf '%s\n' "${p##*/}"; done | grep -oE '^[0-9]+' | sort -n | tail -1)
hi=$((10#${hi:-0}))
cl=$(for p in "$d"/archive/.id-claims/[0-9]*; do [ -e "$p" ] && printf '%s\n' "${p##*/}"; done | sort -n | tail -1); cl=$((10#${cl:-0}))
[ "$cl" -gt "$hi" ] && hi=$cl   # a number another writer has claimed is never issued again
next=$(( (hi > floor ? hi : floor) + 1 ))
today=$(date +%F)
i=0
while IFS= read -r f; do
  i=$((i + 1)); [ -n "$f" ] || continue
  case $f in
    ([0-9]*-*.md|archive/[0-9]*-*.md) ;;
    (*) no "$f: not an entry name under observation-log/ (NNNN-slug.md or archive/NNNN-slug.md)"; continue ;;
  esac
  case $f in (*/*/*|*..*) no "$f: a path outside observation-log/"; continue ;; esac
  p="$d/$f"
  [ -f "$p" ] && [ ! -L "$p" ] || { no "$f: no such entry file"; continue; }
  cp "$p" "$t/old.$i"
  base=${f##*/}; dir=${f%"$base"}; pre=${base%%[!0-9]*}; slug=${base#"$pre"}
  # The header map: H <close line>, K <line> <key>, C <line> (a value continued
  # on an indented line), or NOHDR / OPEN.
  LC_ALL=C awk 'FNR==1 {sub(/^\357\273\277/, ""); if (!/^---[[:space:]]*$/) {print "NOHDR"; exit}; fm=1; next}
    fm && /^---[[:space:]]*$/ {print "H " FNR; fm=0; exit}
    fm && /^[A-Za-z_][A-Za-z0-9_]*:/ {k=$0; sub(/:.*/, "", k); print "K " FNR " " k; next}
    fm && /^[[:space:]]+[^[:space:]#]/ {print "C " FNR}
    END {if (fm) print "OPEN"}' "$t/old.$i" > "$t/map.$i"
  if grep -q '^NOHDR\|^OPEN' "$t/map.$i"; then no "$f: the header does not open on line 1 or does not close"; continue; fi
  dupk=$(sed -n 's/^K [0-9]* //p' "$t/map.$i" | LC_ALL=C sort | uniq -d | tr '\n' ' ')
  [ -n "$dupk" ] && { no "$f: header key(s) occur twice: $dupk— fix the file with the editing tool first"; continue; }
  idv=$(LC_ALL=C awk 'FNR==1 {sub(/^\357\273\277/, "")} /^---[[:space:]]*$/ {if (++n == 2) exit; next} n == 1 && /^id:/ {v=$2; gsub(/["\047\r]/, "", v); print v; exit}' "$t/old.$i")
  case $idv in (""|*[!0-9]*) no "$f: id: does not read as a number before the change (read '$idv')"; continue ;; esac
  [ "$((10#$idv))" -eq "$((10#$pre))" ] || { no "$f: id: $idv does not read as the filename prefix $pre before the change — fix that first"; continue; }
  # this file's operations
  awk -F '\t' -v f="$f" -v OFS='\t' '$2 == f && $1 == "set" {print $3, $4}' "$t/ops" > "$t/kv.$i"
  ren=$(awk -F '\t' -v f="$f" '$2 == f && $1 == "rename" {n++} END {print n + 0}' "$t/ops")
  [ "$ren" -le 1 ] || { no "$f: renamed more than once in one plan"; continue; }
  dupset=$(cut -f 1 "$t/kv.$i" | LC_ALL=C sort | uniq -d | tr '\n' ' ')
  [ -n "$dupset" ] && { no "$f: the plan sets key(s) more than once: $dupset"; continue; }
  bad=
  while IFS="$(printf '\t')" read -r k v; do
    case $k in (""|*[!a-z_]*) bad=1; no "$f: '$k' is not a header key name"; continue ;; esac
    nk=$(grep -c "^K [0-9]* $k\$" "$t/map.$i")
    [ "$nk" -eq 1 ] || { bad=1; no "$f: key $k occurs $nk times in the header, not once"; continue; }
    ln=$(sed -n "s/^K \([0-9]*\) $k\$/\1/p" "$t/map.$i")
    grep -q "^C $((ln + 1))\$" "$t/map.$i" && { bad=1; no "$f: $k holds a block value on the lines below it — edit it with the editing tool"; }
    case $v in (*$'\r'*|*$'\n'*) bad=1; no "$f: the value for $k spans lines" ;; esac
  done < "$t/kv.$i"
  [ -n "$bad" ] && continue
  # the new text: the named lines replaced, nothing else touched
  nid=$((10#$pre)); target="$f"
  if [ "$ren" -eq 1 ]; then
    nid=$next; next=$((next + 1)); target="$dir$(printf '%04d' "$nid")$slug"
    [ -n "$(find "$d" -maxdepth 2 -name "$(printf '%04d' "$nid")-*.md")" ] && { no "$f: id $nid is already used"; continue; }
    printf 'id\t%s\n' "$nid" >> "$t/kv.$i"
  fi
  LC_ALL=C awk -F '\t' 'NR == FNR {v[$1] = $0; sub(/^[^\t]*\t/, "", v[$1]); next}
    FNR == 1 {fm = 1; print; next}
    fm && /^---[[:space:]]*$/ {fm = 0; print; next}
    fm && /^[A-Za-z_][A-Za-z0-9_]*:/ {k = $0; sub(/:.*/, "", k); if (k in v) {print k ":" (v[k] == "" ? "" : " " v[k]); next}}
    {print}' "$t/kv.$i" "$t/old.$i" > "$t/new.$i"
  if [ "$ren" -eq 1 ]; then
    printf '\nRenumbered from %s to %s on %s (scripts/set-fields.sh).\n' "$((10#$pre))" "$nid" "$today" >> "$t/new.$i"
  fi
  # the invariant: every line in place except the named keys' lines (and the
  # renumber line a rename appends); each named key once; id: = the prefix
  diffk=$(LC_ALL=C awk -F '\t' -v ren="$ren" 'FILENAME == ARGV[1] {named[$1] = 1; next}
    FILENAME == ARGV[2] {o[FNR] = $0; on = FNR; next}
    {nw[FNR] = $0; nn = FNR}
    END {
      if ((ren && nn != on + 2) || (!ren && nn != on)) print "LINES " on " " nn
      for (j = 1; j <= on && j <= nn; j++) if (o[j] != nw[j]) {
        k = o[j]; if (k !~ /^[A-Za-z_][A-Za-z0-9_]*:/) {print "OTHER " j; continue}; sub(/:.*/, "", k)
        k2 = nw[j]; sub(/:.*/, "", k2); if (!(k in named) || k2 != k) print "OTHER " j }
    }' "$t/kv.$i" "$t/old.$i" "$t/new.$i")
  [ -n "$diffk" ] && { no "$f: the new text would change lines other than the named keys ($(printf '%s' "$diffk" | tr '\n' ' '))"; continue; }
  nidv=$(LC_ALL=C awk '/^---[[:space:]]*$/ {if (++n == 2) exit; next} n == 1 && /^id:/ {v=$2; gsub(/["\047\r]/, "", v); print v; exit}' "$t/new.$i")
  tpre=${target##*/}; tpre=${tpre%%[!0-9]*}
  case $nidv in (""|*[!0-9]*) nidv=x ;; esac
  [ "$nidv" != x ] && [ "$((10#$nidv))" -eq "$((10#$tpre))" ] || { no "$f: the new text's id: ($nidv) would not read as its filename prefix $tpre — another entry's id; a renumber is the rename operation"; continue; }
  for k in $(cut -f 1 "$t/kv.$i"); do
    [ "$(grep -c "^$k:" "$t/new.$i")" -ge 1 ] || { no "$f: $k missing from the new text"; continue 2; }
  done
  newdup=$(LC_ALL=C awk '/^---[[:space:]]*$/ {if (++n == 2) exit; next} n == 1 && /^[A-Za-z_][A-Za-z0-9_]*:/ {k=$0; sub(/:.*/, "", k); if (s[k]++ == 1) print k}' "$t/new.$i")
  [ -n "$newdup" ] && { no "$f: the new header would carry a key twice: $newdup"; continue; }
  sh=$(LC_ALL=C awk "$sus" "$t/new.$i" | cut -f 3)
  [ -n "$sh" ] && { no "$f: a new header line looks like invalid YAML (the scan's suspect rules) — quote the value: $sh"; continue; }
  printf '%s\t%s\t%s\n' "$i" "$f" "$target" >> "$t/todo"
done < "$t/files"

if [ -n "$refuse" ]; then
  printf 'PLAN REFUSED — nothing written:\n%s' "$refuse" >&2; exit 1
fi
n_files=$(grep -c . "$t/todo")
n_ops=$(grep -c . "$t/ops")
echo "PLAN OK — $n_ops operation(s) over $n_files file(s); every new text differs from its old one only on the named lines"
[ -n "$check" ] && exit 0

# --- phase 2: re-read, claim, write, re-read ---------------------------------
while IFS="$(printf '\t')" read -r i f target; do
  cmp -s "$t/old.$i" "$d/$f" || { echo "CHANGED SINCE CHECK — $f changed after phase 1 (another writer); nothing written, re-run the plan" >&2; exit 1; }
done < "$t/todo"
c="$d/archive/.id-claims"; top=$floor
while IFS="$(printf '\t')" read -r i f target; do
  [ "$f" = "$target" ] && continue
  mkdir -p "$c" || { echo "CLAIM DIR FAILED — cannot create '$c'; nothing written" >&2; exit 1; }
  np=${target##*/}; np=${np%%[!0-9]*}
  (set -C; : > "$c/$np") 2>/dev/null || { echo "CLAIM TAKEN — id $((10#$np)) was claimed by another writer since phase 1; nothing written, re-run the plan" >&2; exit 1; }
  [ "$((10#$np))" -gt "$top" ] && top=$((10#$np))
done < "$t/todo"
wrote=0
while IFS="$(printf '\t')" read -r i f target; do
  p="$d/$f"; part="${p%/*}/.${p##*/}.part"
  cp "$t/new.$i" "$part" && mv -f "$part" "$p" || { echo "WRITE FAILED — $f (files written before it: $wrote; the rest untouched)" >&2; exit 1; }
  if [ "$f" != "$target" ]; then
    if [ -e "$d/$target" ] || ! mv -n "$p" "$d/$target" || [ -e "$p" ]; then
      echo "RENAME INCOMPLETE — $f holds the new id; move it to $target by hand" >&2; exit 1
    fi
    echo "renamed $f -> $target"
  else
    echo "wrote $f ($(cut -f 1 "$t/kv.$i" | tr '\n' ' ' | sed 's/ $//'))"
  fi
  wrote=$((wrote + 1))
done < "$t/todo"
if [ "$top" -gt "$floor" ]; then
  printf '%s\n' "$top" > "$d/archive/.id-floor" || { echo "FLOOR WRITE FAILED — set $d/archive/.id-floor to $top by hand" >&2; exit 1; }
fi
while IFS="$(printf '\t')" read -r i f target; do
  cmp -s "$t/new.$i" "$d/$target" || { echo "VERIFY FAILED — $target does not hold the text phase 1 built" >&2; exit 1; }
done < "$t/todo"
echo "done — $wrote file(s) written and re-read against the checked text"
