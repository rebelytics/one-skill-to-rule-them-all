#!/usr/bin/env bash
# add-evidence.sh — append one use_evidence: line to an observation's
# header, inside the block of its use_evidence: key, as one command.
#
# Usage:
#   bash scripts/add-evidence.sh <workspace-root> <file> "<line>"
#
#   <workspace-root>  the pinned absolute workspace path — the directory that
#                     holds skill-observations/. Never resolved from the cwd;
#                     the path may contain spaces.
#   <file>            the observation: its file name (0042-slug.md), looked
#                     up in observation-log/ and then archive/, or a path to
#                     a file in one of the two. Never created here.
#   <line>            `YYYY-MM-DD accepted|declined|used — <short context>`,
#                     with or without the leading `- `: one line, no `: `
#                     and no ` #` in it, not ending in `:` (the first and the
#                     last turn the item into a mapping, the second cuts it —
#                     references/observation-log.md, Frontmatter fields)
#
# The line goes in under the header's use_evidence: key, after the items
# already there, at their indent (two spaces for the first), before the next
# key. Never before the header's closing `---`: there it lands under
# whichever key is last (escalated: in the template) and reads as that
# key's item. Refused by name, exit 1, nothing written:
#   NO SUCH ENTRY      no file of that name in observation-log/ or archive/,
#                      or in both, or a path outside them
#   NO use_evidence: KEY  the header has none (the creation helper writes one
#                      in every header; add it with the editing tool first)
#   and a header that does not open and close, a key written twice, a key
#   line carrying a value (`use_evidence: []`), or a line of the wrong shape.
#
# The new text is built in a scratch directory and checked before the
# write: every old line in place and one line added. The file is re-read
# just before the write and the run stops if it changed; the write goes
# through a hidden temp file and `mv`, then is re-read against the checked
# text. Prints the written file's path and the added line.
#
# Exit status: 0 written, 1 refused or failed, 2 usage.
# bash, not sh; runs on bash 3.2 (stock macOS): case patterns parenthesised.

set -u

usage='usage: add-evidence.sh <workspace-root> <file> "<YYYY-MM-DD accepted|declined|used — context>"'
[ $# -eq 3 ] || { echo "$usage" >&2; exit 2; }
root=$1; arg=$2; line=$3
[ -n "$root" ] && [ -n "$arg" ] && [ -n "$line" ] || { echo "$usage" >&2; exit 2; }
miss=
for t in awk sed grep cat cmp cp mv mktemp head tail wc tr; do command -v "$t" >/dev/null 2>&1 || miss="$miss $t"; done
[ -z "$miss" ] || { printf 'TOOLS MISSING —%s not on PATH; nothing written\n' "$miss" >&2; exit 1; }
case $root in
  (/*|[A-Za-z]:[/\\]*) ;;
  (*) echo "workspace root must be an ABSOLUTE path, never relative to the cwd: got '$root'" >&2; exit 2 ;;
esac
d="$root/skill-observations/observation-log"
if [ ! -d "$d" ] || [ ! -d "$d/archive" ]; then
  echo "STRUCTURE MISSING — expected '$d' and '$d/archive'; nothing written, never recreated from here" >&2; exit 1
fi

# --- the line: one item the header can carry ---------------------------------
case $line in
  (*$'\n'*|*$'\r'*|*$'\t'*) echo "the line must be one line with no tab; nothing written" >&2; exit 1 ;;
esac
item=${line#- }
case $item in
  (*': '*|*' #'*|*:) echo "the line holds ': ' or ' #', or ends in ':' — reword the context (a YAML list item cannot carry them unquoted); nothing written" >&2; exit 1 ;;
esac
printf '%s\n' "$item" | LC_ALL=C grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2} (accepted|declined|used) — [^[:space:]]' || {
  echo "the line must read 'YYYY-MM-DD accepted|declined|used — <context>': got '$line'; nothing written" >&2; exit 1; }

# --- the file: resolved now, in observation-log/ or archive/ ------------------
rp() { (cd -P "$1" 2>/dev/null && pwd -P); }
case $arg in
  (*/*|*\\*)
    p=$arg; pd=$(rp "${arg%/*}")
    { [ -f "$p" ] && [ -n "$pd" ] && { [ "$pd" = "$(rp "$d")" ] || [ "$pd" = "$(rp "$d/archive")" ]; }; } || {
      echo "NO SUCH ENTRY — '$arg' is not a file in $d or its archive/; nothing written and no file created" >&2; exit 1; } ;;
  (*)
    if [ -f "$d/$arg" ] && [ -f "$d/archive/$arg" ]; then
      echo "NO SUCH ENTRY — '$arg' is in both observation-log/ and archive/ (a restored copy: the scan's RESURRECTED); nothing written" >&2; exit 1
    elif [ -f "$d/$arg" ]; then p="$d/$arg"
    elif [ -f "$d/archive/$arg" ]; then p="$d/archive/$arg"
    else echo "NO SUCH ENTRY — no '$arg' in observation-log/ or archive/; nothing written and no file created. Check the name against the log as it stands now" >&2; exit 1
    fi ;;
esac
f=${p##*/}
case $f in ([0-9]*.md) ;; (*) echo "NO SUCH ENTRY — '$f' is not a numbered entry (NNNN-slug.md); nothing written" >&2; exit 1 ;; esac

t=$(mktemp -d 2>/dev/null) || { echo "cannot create a scratch directory (mktemp -d)" >&2; exit 1; }
trap 'rm -rf "$t"' EXIT   # the scratch directory this run created, nothing else
cp "$p" "$t/old" || { echo "cannot read $f; nothing written" >&2; exit 1; }
# K <line> (the key), V (a value on the key line), L <line> (the block's last
# line), I <indent> (the first item's), CR (the key line ends in CR), NOHDR, OPEN
LC_ALL=C awk 'FNR==1 {sub(/^\357\273\277/, ""); if (!/^---[[:space:]]*$/) {print "NOHDR"; exit}; fm=1; next}
  fm && /^---[[:space:]]*$/ {if (inb) print "L " last; fm=0; exit}
  fm && /^[A-Za-z_][A-Za-z0-9_]*:/ {if (inb) {print "L " last; inb=0}
    if (/^use_evidence:/) {print "K " FNR; v=$0; sub(/^use_evidence:/, "", v); if (v ~ /\r$/) print "CR"; sub(/\r$/, "", v); sub(/^[[:space:]]+/, "", v)
      if (v != "" && v !~ /^#/) print "V"; inb=1; last=FNR}
    next}
  fm && inb && /^[[:space:]]*-[[:space:]]/ {if (!ind) {i=$0; sub(/-.*/, "", i); print "I " length(i); ind=1}; last=FNR; next}
  fm && inb && /^[[:space:]]/ {last=FNR; next}
  fm && inb {print "L " last; inb=0}
  END {if (fm) print "OPEN"}' "$t/old" > "$t/map"
grep -q '^NOHDR\|^OPEN' "$t/map" && { echo "$f: the header does not open on line 1 or does not close; nothing written — fix it with the editing tool" >&2; exit 1; }
nk=$(grep -c '^K ' "$t/map" | tr -d ' ')
[ "$nk" -eq 0 ] && { echo "NO use_evidence: KEY — $f has none in its header; nothing written. Add the key with the editing tool (the creation helper writes it in every new header), then re-run" >&2; exit 1; }
[ "$nk" -eq 1 ] || { echo "$f: use_evidence: occurs $nk times in the header, not once; nothing written — keep one with the editing tool" >&2; exit 1; }
grep -q '^V$' "$t/map" && { echo "$f: use_evidence: carries a value on its own line (an inline list or text); nothing written — rewrite it as a block list with the editing tool" >&2; exit 1; }
at=$(sed -n 's/^L //p' "$t/map")
ni=$(sed -n 's/^I //p' "$t/map"); ni=${ni:-2}
pad=$(printf '%*s' "$ni" '')
cr=; grep -q '^CR$' "$t/map" && cr=$'\r'
new_l="$pad- $item$cr"
{ head -n "$at" "$t/old"; printf '%s\n' "$new_l"; tail -n +"$((at + 1))" "$t/old"; } > "$t/new"
# the invariant: the old text, byte for byte, once the added line is taken out
{ head -n "$at" "$t/new"; tail -n +"$((at + 2))" "$t/new"; } > "$t/back"
cmp -s "$t/back" "$t/old" && [ "$(sed -n "$((at + 1))p" "$t/new")" = "$new_l" ] || {
  echo "$f: the new text would change more than the one added line; nothing written" >&2; exit 1; }

# --- write: re-read, replace, re-read ------------------------------------------
cmp -s "$t/old" "$p" || { echo "CHANGED SINCE READ — $f changed while this run built its text; nothing written, re-run" >&2; exit 1; }
part="${p%/*}/.${p##*/}.part"
cp "$t/new" "$part" && mv -f "$part" "$p" || { echo "WRITE FAILED — $p keeps its old text" >&2; exit 1; }
cmp -s "$t/new" "$p" || { echo "VERIFY FAILED — $p does not hold the checked text" >&2; exit 1; }
printf '%s\n%s\n' "$p" "$pad- $item"
