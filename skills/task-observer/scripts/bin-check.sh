#!/usr/bin/env bash
# bin-check.sh — run a script from the workspace copy of this skill's scripts
# (skill-observations/.bin/) only when every file there carries the INSTALLED
# script's digest, as one command that refuses otherwise.
#
# Usage:
#   bash "<root>/skill-observations/.bin/bin-check.sh" [--installed-version <v>] <workspace-root> <digests-file> <script> [args...]
#
#   <digests-file>  `sha256sum` (or `shasum -a 256`) output over the installed
#                   scripts/, computed WHERE THE SKILL IS INSTALLED (the cloud
#                   container of a bridged session) and passed to the device.
#                   That digest is the one operand that can fail: `.bin/`
#                   hashed against the MANIFEST written from `.bin/` is a
#                   tautology (references/environments.md, "Where the scripts
#                   are not on the device"), so a digests file carrying a
#                   `verified_against:` line is the MANIFEST and is refused.
#                   It may open with the installed SKILL.md's `version:` line
#                   (the "Refresh the digests" row there writes it).
#   --installed-version <v>  the installed skill's frontmatter `version:`,
#                   where the digests file does not carry it.
#   <script>        the file name under .bin/ to run (session-start-scan.sh,
#                   skill-load.sh, new-observation.sh, …); a .py runs under
#                   the first of python3, python that RUNS and reports major
#                   version 3 — `command -v` alone finds a Windows Store
#                   alias, a stub that only prints an install hint
#
# Version gate: .bin/MANIFEST carries `verified_against: <version>`, the
# installed version .bin/ was last refreshed from. With the installed version
# known, a MANIFEST without that line, or an installed version newer than it
# (dotted numeric compare), is refused before any digest is read: the install
# postdates the copy. With no installed version the gate is skipped with a
# note on stderr and the digest compare alone decides.
#
# Exit status: the script's own once it runs; 3 = refused, nothing ran — a
# .bin/ file whose digest differs from, or is missing from, the installed set,
# or a failed version gate (refresh .bin/ from the installed scripts:
# references/weekly-review.md, Step 1 gate), or a .py with no working Python 3
# to run it (its own line, `BIN REFUSED — no working Python 3`, never a digest
# failure); 2 = usage. bash 3.2-compatible;
# paths may contain spaces.

set -u
usage="usage: bin-check.sh [--installed-version <v>] <workspace-root> <digests-file> <script> [args...]"
iv=""
if [ "${1:-}" = "--installed-version" ]; then
  [ -n "${2:-}" ] || { echo "$usage" >&2; exit 2; }
  iv=$2; shift 2
fi
root="${1:-}"; dig="${2:-}"; script="${3:-}"
if [ -z "$root" ] || [ -z "$dig" ] || [ -z "$script" ]; then
  echo "$usage" >&2; exit 2
fi
[ -r "$dig" ] || { echo "digests file missing or unreadable: '$dig'" >&2; exit 2; }
shift 3
bin="$root/skill-observations/.bin"
[ -f "$bin/$script" ] || { echo "BIN REFUSED — no '$script' under '$bin'" >&2; exit 3; }
# `key: "1.2.3"` -> 1.2.3 (first matching line of a file; quotes and spaces dropped)
field() { awk -v k="$1" 'index($0, k ":") == 1 {v = substr($0, length(k) + 2); gsub(/["'"'"' \t\r]/, "", v); print v; exit}' "$2"; }
[ -z "$(field verified_against "$dig")" ] || { echo "BIN REFUSED — '$dig' carries verified_against: it is the MANIFEST, not the installed digests" >&2; exit 3; }
[ -n "$iv" ] || iv=$(field version "$dig")
iv=$(printf '%s' "$iv" | tr -d "\"' ")
if [ -z "$iv" ]; then
  echo "bin-check: version gate skipped — no installed version (--installed-version, or a version: line in the digests file)" >&2
else
  va=""; [ -r "$bin/MANIFEST" ] && va=$(field verified_against "$bin/MANIFEST")
  [ -n "$va" ] || { echo "BIN REFUSED — .bin/MANIFEST has no verified_against: line; installed $iv: refresh .bin/ (weekly-review.md, Step 1 gate)" >&2; exit 3; }
  newer=$(awk -v a="$iv" -v b="$va" 'BEGIN {na = split(a, x, "."); nb = split(b, y, "."); n = na > nb ? na : nb
    for (i = 1; i <= n; i++) { p = x[i] + 0; q = y[i] + 0; if (p > q) {print 1; exit} if (p < q) {print 0; exit} } print 0}')
  [ "$newer" = 0 ] || { echo "BIN REFUSED — installed $iv is newer than .bin/MANIFEST verified_against $va: refresh .bin/ from the installed scripts (weekly-review.md, Step 1 gate), then re-run" >&2; exit 3; }
fi
digest_of() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -c1-64; }
for f in "$bin"/*.sh "$bin"/*.py; do
  [ -e "$f" ] || continue
  n=${f##*/}
  want=$(awk -v n="$n" '{p=$2; sub(/^\*/, "", p); sub(/.*\//, "", p); if (p == n) {print $1; exit}}' "$dig")
  [ -n "$want" ] || { echo "BIN REFUSED — $n has no digest in the installed set ($dig): a stale .bin/, or a file the install does not ship" >&2; exit 3; }
  [ "$want" = "$(digest_of "$f")" ] || { echo "BIN REFUSED — $n differs from the installed script: refresh .bin/ from the installed scripts (weekly-review.md, Step 1 gate), then re-run" >&2; exit 3; }
done
case $script in
  (*.py)
    py=
    for c in python3 python; do
      if command -v "$c" >/dev/null 2>&1 \
         && "$c" -c 'import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)' </dev/null >/dev/null 2>&1; then
        py=$c; break
      fi
    done
    [ -n "$py" ] || { echo "BIN REFUSED — no working Python 3 to run '$script' (python3 and python are absent, or neither runs and reports version 3 — a Windows Store alias is the usual cause); the digests matched, nothing ran: install Python 3 or put a working one first on PATH" >&2; exit 3; }
    exec "$py" "$bin/$script" "$@" ;;
  (*)    exec bash "$bin/$script" "$@" ;;
esac
