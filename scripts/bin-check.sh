#!/usr/bin/env bash
# bin-check.sh — run a script from the workspace copy of this skill's scripts
# (skill-observations/.bin/) only when every file there carries the INSTALLED
# script's digest, as one command that refuses otherwise.
#
# Usage:
#   bash "<root>/skill-observations/.bin/bin-check.sh" <workspace-root> <digests-file> <script> [args...]
#
#   <digests-file>  `sha256sum` (or `shasum -a 256`) output over the installed
#                   scripts/, computed WHERE THE SKILL IS INSTALLED (the cloud
#                   container of a bridged session) and passed to the device.
#                   That digest is the one operand that can fail: `.bin/`
#                   hashed against the MANIFEST written from `.bin/` is a
#                   tautology (references/environments.md, "Where the scripts
#                   are not on the device").
#   <script>        the file name under .bin/ to run (session-start-scan.sh,
#                   skill-load.sh, new-observation.sh, …); a .py runs under python3
#
# Exit status: the script's own once it runs; 3 = refused, nothing ran — a
# .bin/ file whose digest differs from, or is missing from, the installed set
# (refresh .bin/ from the installed scripts: references/weekly-review.md,
# Step 1 gate); 2 = usage. bash 3.2-compatible; paths may contain spaces.

set -u
root="${1:-}"; dig="${2:-}"; script="${3:-}"
if [ -z "$root" ] || [ -z "$dig" ] || [ -z "$script" ]; then
  echo "usage: bin-check.sh <workspace-root> <digests-file> <script> [args...]" >&2; exit 2
fi
[ -r "$dig" ] || { echo "digests file missing or unreadable: '$dig'" >&2; exit 2; }
shift 3
bin="$root/skill-observations/.bin"
[ -f "$bin/$script" ] || { echo "BIN REFUSED — no '$script' under '$bin'" >&2; exit 3; }
digest_of() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -c1-64; }
for f in "$bin"/*.sh "$bin"/*.py; do
  [ -e "$f" ] || continue
  n=${f##*/}
  want=$(awk -v n="$n" '{p=$2; sub(/^\*/, "", p); sub(/.*\//, "", p); if (p == n) {print $1; exit}}' "$dig")
  [ -n "$want" ] || { echo "BIN REFUSED — $n has no digest in the installed set ($dig): a stale .bin/, or a file the install does not ship" >&2; exit 3; }
  [ "$want" = "$(digest_of "$f")" ] || { echo "BIN REFUSED — $n differs from the installed script: refresh .bin/ from the installed scripts (weekly-review.md, Step 1 gate), then re-run" >&2; exit 3; }
done
case $script in
  (*.py) exec python3 "$bin/$script" "$@" ;;
  (*)    exec bash "$bin/$script" "$@" ;;
esac
