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
# no working Python 3 runs, through the text normaliser the same section
# documents (name:, description:, version: quotes stripped), with one
# `diff-staged: no working Python 3 …` line on stderr saying so. "Working"
# is measured, not looked up: the interpreter is the first of python3,
# python that runs `-c` and reports major version 3. `command -v` alone
# finds a Windows Store alias (an app-execution stub that prints an install
# hint and exits non-zero), and an identical copy then read as ERROR. Every other file is
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

# --- a Python 3 that runs, not one that is merely on PATH ----------------------
py=
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 \
     && "$c" -c 'import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)' </dev/null >/dev/null 2>&1; then
    py=$c; break
  fi
done

# --- SKILL.md: frontmatter by value, body by bytes ----------------------------
if [ -n "$py" ] && [ -f "$here/validate-skill-bundle.py" ]; then
  cmp_out=$(PYTHONDONTWRITEBYTECODE=1 "$py" "$here/validate-skill-bundle.py" --compare-frontmatter "$live/SKILL.md" "$staged/SKILL.md" 2>&1)
  rc=$?
  case $rc in
    (0) ;;
    (1) add "SKILL.md ($(printf '%s\n' "$cmp_out" | grep 'DIFFERS' | tr '\n' ' ' | sed 's/ *$//'))" ;;
    (*) echo "ERROR SKILL.md compare failed: $(printf '%s' "$cmp_out" | tr '\n' ' ')"; exit 2 ;;
  esac
else
  if [ -z "$py" ]; then
    why="no working Python 3"
    echo "diff-staged: no working Python 3 (python3 and python are absent, or neither runs and reports version 3 — a Windows Store alias is the usual cause): SKILL.md compared by the text fallback, which reads a description the installer re-folded as a difference" >&2
  else
    why="no validate-skill-bundle.py beside this script"
  fi
  fm=$'1,/^---$/{/^(name|description|version):[[:space:]]*".*"[[:space:]]*$/{s/:[[:space:]]*"/: /;s/"[[:space:]]*$//;s/\\\\"/"/g;s/\\\\\\\\/\\\\/g;};/^(name|description|version):[[:space:]]*\'.*\'[[:space:]]*$/{s/:[[:space:]]*\'/: /;s/\'[[:space:]]*$//;s/\'\'/\'/g;};}'
  a=$(mktemp) && b=$(mktemp) || { echo "ERROR normalisation: mktemp failed"; exit 2; }
  trap 'rm -f "$a" "$b"' EXIT
  if ! sed -E "$fm" "$live/SKILL.md" > "$a" || ! sed -E "$fm" "$staged/SKILL.md" > "$b" || [ ! -s "$a" ] || [ ! -s "$b" ]; then
    echo "ERROR normalisation of SKILL.md failed ($why; text fallback)"; exit 2
  fi
  diff "$a" "$b" >/dev/null; rc=$?
  case $rc in
    (0) ;;
    (1) add "SKILL.md (text fallback, $why; a description the installer re-folded also shows here)" ;;
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
