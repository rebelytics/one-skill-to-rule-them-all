# Eval set

Behaviour checks for a skill, run by a model against fixture workspaces and
graded from the transcript. The selftests in `scripts/` prove that the
skill's scripts do what they say; these cases check what an agent does with
the skill's text: whether the session-start probe rides in the first tool
batch, whether a skill load brings its observation lookup with it, whether a
subagent stays out of the log. Rewording a rule can change any of these
without a single script changing, so the set is run whenever the text
changes in a way that could move behaviour.

## Scope

The format is not specific to Task Observer. It is meant for every skill
you log observations for, opted in skill by skill: a skill has cases when
someone wrote some, and a case names the skill it tests. Run the set for a
skill when its text is restructured and for every change classified
needs-test; its drift report is one row of the merge review. This
repository ships cases for `task-observer` only.

You can keep your own cases outside the repository, for skills you
maintain privately or for situations from your own work: a folder such as
`<workspace>/skill-observations/evals/` with `cases/` and `fixtures/`
inside, passed to the runner with `--cases`. It is read exactly like
`evals/cases/` and never ships.

## Layout

```text
evals/
  README.md         this specification
  run.sh            the runner: claude -p, headless, N runs per case
  grade.py          the grader: assertions, pass rates, the drift table
  cases/<id>.yaml   one case per file
  fixtures/<name>/  fixture workspaces the cases start from
  selftest/         hand-written transcripts that test grade.py itself
```

Results never go into the repository: the runner refuses an `--out` inside
it.

## A case

One YAML file per case in `cases/`, named after its `id`:

```yaml
id: per-skill-lookup-at-skill-load
skill: task-observer
source: none
tier: agent
rule: 'references/observation-scan.md § The per-skill lookup at every skill load'
situation:
  workspace: fixtures/basic
  prompt: 'Add a line to docs/notes.md recording that the demo project was reviewed today.'
expectations:
  - check: same_batch
    a_tool: Skill
    a_input: 'fixture-notes'
    b_tool: Bash
    b_input: 'skill-load\.sh[^\n]*fixture-notes'
  - check: file_matches
    path: skill-observations/checkpoints.log
    pattern: 'loaded fixture-notes'
```

| Field | Meaning |
|---|---|
| `id` | the case's name; equals the file name without `.yaml` |
| `skill` | the skill under test, by its frontmatter `name:` |
| `source` | the public issue the case comes from (`'#123'`, quoted), or `none`. Never an id from a private observation log: those mean nothing to anyone else and can carry context that is not yours to publish |
| `tier` | `agent` (run by a model, graded here) or `script` (a deterministic check that belongs in the skill's own selftest harness; listed here for completeness, skipped by the runner) |
| `rule` | the file and section whose rule should fire, `file § heading` |
| `situation.workspace` | the fixture directory, relative to the folder holding `cases/` |
| `situation.prompt` | the opening prompt; or `situation.prompts`, a list, one per turn (later turns resume the same session) |
| `situation.skill_installed_from_turn` | optional: install the skill only before this turn (default 1), for cases about a skill that does not resolve at first |
| `expectations` | a list of assertions, each with a `check:` type below |

Write values in the plain subset of YAML the grader reads without PyYAML:
mappings, lists, quoted or plain scalars, `|` blocks. Put regular
expressions in single quotes (a literal `'` is written `''`).

### Checks

Patterns are Python regular expressions. `{workspace}` in a pattern stands
for the run's workspace path, escaped. Tool inputs are matched as plain
text, one string value per line, so a pattern sees a command the way the
shell does. Tool names are regular expressions matched whole (`Task|Agent`).
A batch is the set of tool calls the main agent makes between two tool
results; `turn:` (default 1) picks the turn where a check is turn-scoped.

| `check:` | Keys | Passes when |
|---|---|---|
| `first_batch_includes_tool` | `tool`, `input_matches`, `turn` | the first tool batch of the turn holds a matching call |
| `same_batch` | `a_tool`, `a_input`, `b_tool`, `b_input`, `turn` | one batch holds both calls (any turn unless `turn:` is given) |
| `tool_call_before` | `first_tool`/`first_input` or `first_text`; `second_tool`/`second_input` or `second_text`; `turn`; `second_optional` | the first matching event comes before the first matching second event; `*_text` matches the main agent's text |
| `file_exists` / `file_absent` | `path` | the path, relative to the run workspace, exists / does not exist after the run |
| `file_matches` | `path`, `pattern` | the file exists and the pattern matches its content (multiline) |
| `transcript_matches` / `transcript_not_matches` | `pattern`, `scope` (`text`, `tool_input`, `any`; default `text`), `agent` (`main`, `sub`, `any`; default `main`), `turn` | the pattern is found / not found in the chosen part of the transcript |
| `grader` | `question` | decided by a blind model grader, see below |

A subagent's events are the ones whose `parent_tool_use_id` is set; a case
about delegation checks them with `agent: sub`.

## Fixtures

A fixture is a small workspace copied fresh for every run. Two
substitutions happen in each copy, in files whose name ends in `.fixture`,
which are then renamed without the suffix: `[INSTRUCTIONS]` becomes the
text of the runner's `--instructions` file, and `[ABSOLUTE PATH]` becomes the
run's workspace path. The suffix keeps the repository's own tools from
reading the fixtures as real files: a `CLAUDE.md` here would load into a
maintainer's session working in this folder, and a `SKILL.md` would be
offered as a skill by installers that scan the repository.

The skill under test is installed in each run workspace as a project skill
(`.claude/skills/<name>/`, its `SKILL.md` with `references/`, `scripts/`,
`assets/` and `LICENSE` where present).

For `task-observer` the instructions are the activation block of the
version under test, so each version runs with its own block:

```bash
awk '/^### The activation block/{f=1} f&&/^```text/{c=1;next} c&&/^```/{exit} c' \
  <checkout>/references/environments.md > <scratch>/block-<version>.txt
```

## Running

```bash
bash evals/run.sh --skill-dir <checkout-of-main> --out <results>/main \
  --instructions <block-of-main> --runs 3
bash evals/run.sh --skill-dir <checkout-of-test-branch> --out <results>/test \
  --instructions <block-of-test-branch> --runs 3
python3 evals/grade.py drift <results>/main <results>/test
```

The runner calls `claude -p` with `--output-format stream-json --verbose`,
so the transcript records every tool call, writes each run to
`<out>/<case>/run-<n>/` (`case.yaml`, `meta.json`, `transcript.jsonl`,
`stderr.txt`, and the `workspace/` as the run left it), and grades the
directory at the end. By default it runs in an isolated config directory
(`CLAUDE_CONFIG_DIR` under `--out`), so neither your own instruction file
nor your installed skills load and no run can write to your real workspace.
That directory needs credentials: set `ANTHROPIC_API_KEY`, or log in once
with `CLAUDE_CONFIG_DIR` pointing at a directory you then pass with
`--config-dir`. Check the flags against `claude --help` of your version
before a first run.

## Grading

Assertions decide. A case states what must be true of the transcript or
the workspace, and a run passes when all of its assertions pass. A blind
model grader is used only for what no assertion can express (`check:
grader`), and it is never told which version produced the run: the grader
writes those items to `grader-queue.jsonl`, shuffled, with the run's text
and without its version or path, and the run stays pending until a grade
exists.

Each case runs 3 times per version, because one run of a model is an
anecdote. The drift report is the pass rate per case, old against new
(`grade.py drift`), with each case marked `same`, `improved`, `REGRESSION`,
`new case` or `not run in new`; it goes into the merge review as one row.

## Cost

Every run is at least one model call per prompt turn: cases × 3 runs × 2
versions for a drift report, more for multi-turn cases. The 14 shipped
cases come to 84 runs per comparison (90 prompt turns: one case has two). Cap a run's length with
`--max-turns`, and narrow a check to the cases a change touches with
`--case`.

## Testing the grader

```bash
python3 evals/grade.py selftest
python3 evals/grade.py check evals/cases
bash -n evals/run.sh
```

`selftest/` holds hand-written transcripts in the runner's layout
(`results-old/`, `results-new/`) and `expected.json` with the verdict every
run and every drift row must get; the selftest also validates the shipped
cases and checks that the plain-YAML reader and PyYAML read them the same.
