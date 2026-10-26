#!/usr/bin/env bash
# diff-staged.sh — the reconciliation gate's installed-vs-staged compare
# (references/weekly-review.md, "Compare with the installer's frontmatter
# quoting normalised") as one command with one verdict line.
#
# Usage:
#   bash scripts/diff-staged.sh <staged-skill-dir> <live-skill-dir>
#
# Prints exactly one line, and exits with its code:
#   IDENTICAL                        0  same skill (installer quoting aside)
#   DIFFERS <n> path(s): <p>; <p>…   1  classify it: (b), (c) or (d)
#   ERROR <what>                     2  the compare did not run — not
#                                       reconciled, never "identical"
# ERROR covers a wrong argument count, a missing path, a file where a
# directory belongs, a SKILL.md that cannot be read or parsed, and a failed
# normalisation. The exits of `diff -rq` alone cannot tell "differs" from
# "never ran" (a missing path and a real difference look alike to a loop
# that only checks for non-zero), and a loop over a joined string of names
# runs no compare at all: this script names the path it could not use.
#
# SKILL.md is compared by parsed frontmatter value plus body bytes, through
# `validate-skill-bundle.py --compare-frontmatter` beside this file; where
# no python3 runs, through the text normaliser the same section documents
# (name:, description:, version: quotes stripped). Every other file is
# compared literally, VCS metadata and build artefacts excluded, and a
# checkout's .claude-plugin/ manifests (live may be a repository checkout;
# a skill bundle never carries them).
#
# bash 3.2-compatible (stock macOS).

set -u

if [ $# -ne 2 ]; then
  echo "ERROR usage: diff-staged.sh <staged-skill-dir> <live-skill-dir> (got $# argument(s))"; exit 2
fi
staged=$1; live=$2
for p in "$staged" "$live"; do
  if [ ! -e "$p" ]; then echo "ERROR missing: '$p'"; exit 2; fi
  if [ ! -d "$p" ]; then echo "ERROR not a directory: '$p'"; exit 2; fi
  if [ ! -f "$p/SKILL.md" ]; then echo "ERROR no SKILL.md in '$p'"; exit 2; fi
done

here=$(cd "$(dirname "$0")" && pwd)
diffs=
add() { diffs="$diffs${diffs:+; }$1"; n=$((n + 1)); }
n=0

# --- SKILL.md: frontmatter by value, body by bytes ----------------------------
if command -v python3 >/dev/null 2>&1 && [ -f "$here/validate-skill-bundle.py" ]; then
  cmp_out=$(PYTHONDONTWRITEBYTECODE=1 python3 "$here/validate-skill-bundle.py" --compare-frontmatter "$live/SKILL.md" "$staged/SKILL.md" 2>&1)
  rc=$?
  case $rc in
    (0) ;;
    (1) add "SKILL.md ($(printf '%s\n' "$cmp_out" | grep 'DIFFERS' | tr '\n' ' ' | sed 's/ *$//'))" ;;
    (*) echo "ERROR SKILL.md compare failed: $(printf '%s' "$cmp_out" | tr '\n' ' ')"; exit 2 ;;
  esac
else
  fm=$'1,/^---$/{/^(name|description|version):[[:space:]]*".*"[[:space:]]*$/{s/:[[:space:]]*"/: /;s/"[[:space:]]*$//;s/\\\\"/"/g;s/\\\\\\\\/\\\\/g;};/^(name|description|version):[[:space:]]*\'.*\'[[:space:]]*$/{s/:[[:space:]]*\'/: /;s/\'[[:space:]]*$//;s/\'\'/\'/g;};}'
  a=$(mktemp) && b=$(mktemp) || { echo "ERROR normalisation: mktemp failed"; exit 2; }
  trap 'rm -f "$a" "$b"' EXIT
  if ! sed -E "$fm" "$live/SKILL.md" > "$a" || ! sed -E "$fm" "$staged/SKILL.md" > "$b" || [ ! -s "$a" ] || [ ! -s "$b" ]; then
    echo "ERROR normalisation of SKILL.md failed (no python3; text fallback)"; exit 2
  fi
  diff "$a" "$b" >/dev/null; rc=$?
  case $rc in
    (0) ;;
    (1) add "SKILL.md (text fallback; a description the installer re-folded also shows here)" ;;
    (*) echo "ERROR SKILL.md text compare exited $rc"; exit 2 ;;
  esac
fi

# --- every other file, literally ----------------------------------------------
out=$(LC_ALL=C diff -rq -x SKILL.md -x .git -x .hg -x .svn -x .claude-plugin -x __pycache__ -x '*.pyc' -x .DS_Store "$live" "$staged" 2>&1)
rc=$?
case $rc in
  (0|1) ;;
  (*) echo "ERROR diff -rq exited $rc: $(printf '%s' "$out" | tr '\n' ' ')"; exit 2 ;;
esac
if [ -n "$out" ]; then
  while IFS= read -r line; do
    case $line in
      ("Files $live/"*" and $staged/"*" differ") r=${line#"Files $live/"}; r=${r%%" and $staged/"*}; add "$r" ;;
      ("Only in $live: "*|"Only in $live/"*) r=${line#"Only in $live"}; r=${r/: //}; add "live only: ${r#/}" ;;
      ("Only in $staged: "*|"Only in $staged/"*) r=${line#"Only in $staged"}; r=${r/: //}; add "staged only: ${r#/}" ;;
      (*) add "$line" ;;
    esac
  done <<< "$out"
fi

if [ "$n" -eq 0 ]; then echo "IDENTICAL"; exit 0; fi
echo "DIFFERS $n path(s): $diffs"; exit 1
