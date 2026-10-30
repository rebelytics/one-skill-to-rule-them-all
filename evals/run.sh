#!/usr/bin/env bash
# run.sh — run a skill's agent-tier eval cases with `claude -p` (headless) and
# grade them.
#
# Usage:
#   bash evals/run.sh --skill-dir <dir> --out <results-dir> [options]
#
#   --skill-dir <dir>     the skill under test: a directory holding SKILL.md
#                         (and its references/ and scripts/), e.g. a checkout
#                         of the test branch, or of main for the baseline
#   --out <dir>           results directory; must lie OUTSIDE this repository
#                         (transcripts and run workspaces are written there)
#   --runs <n>            runs per case (default 3)
#   --cases <dir>         a cases directory; repeatable. Default: evals/cases
#                         in this repository. A local folder outside the repo
#                         (e.g. <workspace>/skill-observations/evals/cases,
#                         with its fixtures in ../fixtures) is added the same
#                         way and never ships.
#   --case <id>           run only this case id; repeatable
#   --instructions <file> text substituted for [INSTRUCTIONS] in fixture files
#                         (for task-observer: the activation block of the
#                         version under test — see evals/README.md)
#   --config-dir <dir>    an isolated Claude Code config directory to run in
#                         (CLAUDE_CONFIG_DIR); default: a fresh one under --out
#   --no-isolate          run with your own config directory: your user-level
#                         instruction file and skills then load too, and a run
#                         may write to your real workspace — not recommended
#   --max-turns <n>       passed to claude (default 40)
#   --model <name>        passed to claude
#   --allowed-tools <s>   passed to claude --allowedTools
#                         (default "Bash Read Write Edit Glob Grep Skill Task")
#
# Layout written: <out>/<case-id>/run-<n>/{case.yaml, meta.json,
# transcript.jsonl, stderr.txt, workspace/}, then <out>/summary.json from
# grade.py. Each run gets a fresh copy of the case's fixture workspace with the
# skill installed as a project skill (<workspace>/.claude/skills/<name>/);
# files named *.fixture are renamed without the suffix after [INSTRUCTIONS]
# and [ABSOLUTE PATH] (the run workspace) are substituted. Script-tier cases
# are skipped: they run in the skill's own selftest harness.
#
# Model calls: one per prompt turn, so cases x runs x turns per version; a
# drift comparison runs two versions.
set -u

here=$(cd "$(dirname "$0")" && pwd -P)
repo=$(cd "$here/.." && pwd -P)
skill_dir= out= runs=3 instr= cfg= isolate=1 max_turns=40 model=
tools="Bash Read Write Edit Glob Grep Skill Task"
cases_dirs=() only=()

die() { echo "run.sh: $*" >&2; exit 2; }
while [ $# -gt 0 ]; do
  case "$1" in
    --skill-dir) skill_dir=${2:-}; shift 2 ;;
    --out) out=${2:-}; shift 2 ;;
    --runs) runs=${2:-}; shift 2 ;;
    --cases) cases_dirs+=("${2:-}"); shift 2 ;;
    --case) only+=("${2:-}"); shift 2 ;;
    --instructions) instr=${2:-}; shift 2 ;;
    --config-dir) cfg=${2:-}; shift 2 ;;
    --no-isolate) isolate=0; shift ;;
    --max-turns) max_turns=${2:-}; shift 2 ;;
    --model) model=${2:-}; shift 2 ;;
    --allowed-tools) tools=${2:-}; shift 2 ;;
    -h|--help) sed -n '2,40p' "$0"; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

[ -n "$skill_dir" ] && [ -f "$skill_dir/SKILL.md" ] || die "--skill-dir must name a directory holding SKILL.md"
[ -n "$out" ] || die "--out is required"
case "$runs" in ''|*[!0-9]*|0) die "--runs must be a positive integer" ;; esac
[ -z "$instr" ] || [ -f "$instr" ] || die "--instructions file not found: $instr"
command -v claude >/dev/null 2>&1 || die "claude (Claude Code CLI) is not on PATH"
command -v python3 >/dev/null 2>&1 || die "python3 is not on PATH"
[ ${#cases_dirs[@]} -gt 0 ] || cases_dirs=("$here/cases")

skill_dir=$(cd "$skill_dir" && pwd -P)
mkdir -p "$out" || die "cannot create $out"
out=$(cd "$out" && pwd -P)
case "$out/" in "$repo"/*) die "--out lies inside this repository ($repo): results never ship" ;; esac
field() { awk -v k="$1" 'NR > 1 && /^---$/ { exit } index($0, k ":") == 1 { v = substr($0, length(k) + 2); gsub(/^[ \t]+|[ \t]+$/, "", v); gsub(/^["\047]|["\047]$/, "", v); print v; exit }' "$skill_dir/SKILL.md"; }
name=$(field name); version=$(field version)
[ -n "$name" ] || die "no name: in the frontmatter of $skill_dir/SKILL.md"

if [ "$isolate" = 1 ]; then
  cfg=${cfg:-$out/.claude-config}
  mkdir -p "$cfg"
  [ ! -e "$cfg/CLAUDE.md" ] && [ ! -e "$cfg/skills" ] || die "config dir $cfg holds CLAUDE.md or skills/: not isolated"
  export CLAUDE_CONFIG_DIR="$cfg"
else
  [ -d "$HOME/.claude/skills/$name" ] && echo "WARNING: $HOME/.claude/skills/$name is installed and will load beside the copy under test" >&2
  echo "WARNING: --no-isolate: your own instruction file and skills load in every run" >&2
fi

grade=(python3 -B "$here/grade.py")
n_cases=0 n_runs=0
for cd_ in "${cases_dirs[@]}"; do
  [ -d "$cd_" ] || die "cases directory not found: $cd_"
  for cf in "$cd_"/*.yaml; do
    [ -e "$cf" ] || continue
    spec=$("${grade[@]}" export "$cf") || die "invalid case: $cf"
    get() { printf '%s' "$spec" | python3 -c "import json,sys; v=json.load(sys.stdin)[sys.argv[1]]; print(v if not isinstance(v, list) else len(v))" "$1"; }
    id=$(get id); [ "$(get skill)" = "$name" ] || continue
    if [ ${#only[@]} -gt 0 ]; then
      hit=0; for o in "${only[@]}"; do [ "$o" = "$id" ] && hit=1; done
      [ "$hit" = 1 ] || continue
    fi
    if [ "$(get tier)" != agent ]; then echo "skip $id: tier $(get tier)"; continue; fi
    fixture=$(get fixture); turns=$(get prompts); from=$(get skill_from_turn)
    if grep -rqF '[INSTRUCTIONS]' "$fixture" 2>/dev/null && [ -z "$instr" ]; then
      die "$id: its fixture uses [INSTRUCTIONS]; pass --instructions <file>"
    fi
    n_cases=$((n_cases + 1))
    for r in $(seq 1 "$runs"); do
      rd="$out/$id/run-$r"
      rm -rf "$rd"; mkdir -p "$rd/workspace"
      cp "$cf" "$rd/case.yaml"
      cp -R "$fixture/." "$rd/workspace/"
      ws=$(cd "$rd/workspace" && pwd -P)
      # substitute and rename the *.fixture files
      find "$ws" -type f -name '*.fixture' | while IFS= read -r f; do
        python3 - "$f" "$ws" "$instr" <<'PY'
import sys, pathlib
f, ws, instr = sys.argv[1], sys.argv[2], sys.argv[3]
t = pathlib.Path(f).read_text(encoding="utf-8")
if instr:
    t = t.replace("[INSTRUCTIONS]", pathlib.Path(instr).read_text(encoding="utf-8").rstrip("\n"))
t = t.replace("[ABSOLUTE PATH]", ws)
pathlib.Path(f[:-len(".fixture")]).write_text(t, encoding="utf-8")
pathlib.Path(f).unlink()
PY
      done
      # the skill's own files only — a skill kept at a repository root must
      # not bring the repository (and these evals) along
      install_skill() {
        mkdir -p "$ws/.claude/skills/$name" && cp "$skill_dir/SKILL.md" "$ws/.claude/skills/$name/" &&
        for x in references scripts assets LICENSE; do
          [ -e "$skill_dir/$x" ] && cp -R "$skill_dir/$x" "$ws/.claude/skills/$name/"
        done; return 0
      }
      [ "$from" -le 1 ] && install_skill
      printf '{"case": "%s", "run": %s, "skill": "%s", "version": "%s", "skill_dir": "%s", "workspace_abs": "%s", "started": "%s"}\n' \
        "$id" "$r" "$name" "$version" "$skill_dir" "$ws" "$(date '+%F %T')" > "$rd/meta.json"
      sid=
      for t in $(seq 1 "$turns"); do
        [ "$t" = "$from" ] && [ "$from" -gt 1 ] && install_skill
        prompt=$(printf '%s' "$spec" | python3 -c "import json,sys; print(json.load(sys.stdin)['prompts'][int(sys.argv[1]) - 1])" "$t")
        printf '{"type": "eval_turn", "turn": %s}\n' "$t" >> "$rd/transcript.jsonl"
        args=(-p "$prompt" --output-format stream-json --verbose --max-turns "$max_turns" --allowedTools "$tools")
        [ -n "$model" ] && args+=(--model "$model")
        [ -n "$sid" ] && args+=(--resume "$sid")
        ( cd "$ws" && claude "${args[@]}" ) >> "$rd/transcript.jsonl" 2>> "$rd/stderr.txt"
        echo "  $id run $r turn $t: claude exited $?"
        sid=$(python3 -c "
import json, sys
sid = ''
for line in open(sys.argv[1], encoding='utf-8', errors='replace'):
    try:
        ev = json.loads(line)
    except ValueError:
        continue
    sid = ev.get('session_id') or sid
print(sid)" "$rd/transcript.jsonl")
      done
      n_runs=$((n_runs + 1))
    done
  done
done

[ "$n_cases" -gt 0 ] || die "no agent-tier case for skill $name in: ${cases_dirs[*]}"
echo "ran $n_cases cases, $n_runs runs, skill $name $version"
"${grade[@]}" grade "$out"
