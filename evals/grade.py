#!/usr/bin/env python3
"""grade.py — grade eval runs of a skill from their stream-json transcripts.

Usage:
  python3 evals/grade.py grade <results-dir> [--json <file>]
      Grade every run under <results-dir> (the layout run.sh writes:
      <results-dir>/<case-id>/run-<n>/{case.yaml, meta.json, transcript.jsonl,
      workspace/}); print the pass rate per case and per assertion; write a
      JSON summary to <results-dir>/summary.json (or --json).
  python3 evals/grade.py drift <old-results-dir> <new-results-dir>
      Grade both and print the drift table: pass rate per case, old vs new.
  python3 evals/grade.py check <cases-dir> [<cases-dir> ...]
      Validate case files: required fields, known check types, the fixture.
  python3 evals/grade.py export <case.yaml>
      Print the fields run.sh needs, as JSON (prompts, fixture, skill, tier).
  python3 evals/grade.py selftest
      Grade the hand-written transcripts in evals/selftest/ and compare every
      verdict with the expected one; check the shipped cases too.

Assertions decide. A `grader` expectation is not graded here: it is listed,
with the run's text and no version label, in grader-queue.jsonl for a blind
model grader, and the run's verdict stays pending until that grade exists.

Standard library only; PyYAML is used when installed, and a small reader for
the YAML subset the case format allows otherwise (both read the shipped cases
identically — the selftest checks that where PyYAML is present).
"""
import json
import os
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REQUIRED = ("id", "skill", "source", "situation", "rule", "expectations", "tier")
TIERS = ("script", "agent")
CHECKS = {
    # check type: required keys beside `check`
    "first_batch_includes_tool": ("tool",),
    "same_batch": ("a_tool", "b_tool"),
    "tool_call_before": (),          # first_tool|first_text and second_tool|second_text
    "file_exists": ("path",),
    "file_absent": ("path",),
    "file_matches": ("path", "pattern"),
    "transcript_matches": ("pattern",),
    "transcript_not_matches": ("pattern",),
    "grader": ("question",),
}
SOURCE_RE = re.compile(r"^(#\d+|none)$")


# ---------------------------------------------------------------- YAML subset

def _scalar(s):
    s = s.strip()
    if s.startswith("'") and s.endswith("'") and len(s) >= 2:
        return s[1:-1].replace("''", "'")
    if s.startswith('"') and s.endswith('"') and len(s) >= 2:
        return json.loads(s)
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if s in ("true", "false"):
        return s == "true"
    if s in ("null", "~", ""):
        return None
    return s


def _strip_comment(line):
    # a comment starts at ` #` outside quotes; the subset keeps it simple
    out, q = [], None
    for i, ch in enumerate(line):
        if q:
            if ch == q:
                q = None
        elif ch in "'\"":
            q = ch
        elif ch == "#" and (i == 0 or line[i - 1] == " "):
            break
        out.append(ch)
    return "".join(out).rstrip()


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def _block_scalar(lines, i, parent_indent):
    body, ind = [], None
    while i < len(lines):
        raw = lines[i]
        if raw.strip() == "":
            body.append("")
            i += 1
            continue
        if _indent(raw) <= parent_indent:
            break
        if ind is None:
            ind = _indent(raw)
        body.append(raw[ind:])
        i += 1
    while body and body[-1] == "":
        body.pop()
    return "\n".join(body) + "\n", i


def _parse(lines, i, indent):
    """Parse the block starting at line i whose items sit at `indent`."""
    while i < len(lines) and _strip_comment(lines[i]).strip() == "":
        i += 1
    if i >= len(lines):
        return None, i
    first = _strip_comment(lines[i])
    if first.lstrip().startswith("- ") or first.strip() == "-":
        items = []
        while i < len(lines):
            line = _strip_comment(lines[i])
            if line.strip() == "":
                i += 1
                continue
            if _indent(line) != indent or not line.lstrip().startswith("-"):
                break
            rest = line.lstrip()[1:].lstrip()
            if rest == "|":
                val, i = _block_scalar(lines, i + 1, indent)
                items.append(val)
            elif re.match(r"^[A-Za-z_][\w-]*:(\s|$)", rest):
                # a mapping item: re-read its first key at indent+2
                lines = lines[:i] + [" " * (indent + 2) + rest] + lines[i + 1:]
                val, i = _parse(lines, i, indent + 2)
                items.append(val)
            else:
                items.append(_scalar(rest))
                i += 1
        return items, i
    out = {}
    while i < len(lines):
        line = _strip_comment(lines[i])
        if line.strip() == "":
            i += 1
            continue
        if _indent(line) != indent:
            if _indent(line) < indent:
                break
            raise ValueError(f"line {i + 1}: unexpected indent")
        m = re.match(r"^\s*([A-Za-z_][\w-]*):(?:\s+(.*))?$", line)
        if not m:
            break
        key, rest = m.group(1), (m.group(2) or "").strip()
        if rest == "|":
            out[key], i = _block_scalar(lines, i + 1, indent)
        elif rest == "":
            j = i + 1
            while j < len(lines) and _strip_comment(lines[j]).strip() == "":
                j += 1
            if j < len(lines) and _indent(lines[j]) > indent or (
                    j < len(lines) and _indent(lines[j]) == indent
                    and lines[j].lstrip().startswith("- ")):
                out[key], i = _parse(lines, j, _indent(lines[j]))
            else:
                out[key], i = None, i + 1
        else:
            out[key] = _scalar(rest)
            i += 1
    return out, i


def read_subset(text):
    val, _ = _parse(text.splitlines(), 0, 0)
    return val


def load_case(path):
    text = Path(path).read_text(encoding="utf-8")
    try:
        import yaml  # noqa: F401
    except ImportError:
        return read_subset(text)
    import yaml
    return yaml.safe_load(text)


# ---------------------------------------------------------------- cases

def check_case(path, case, fails):
    where = str(path)
    if not isinstance(case, dict):
        fails.append(f"{where}: not a mapping")
        return
    for k in REQUIRED:
        if k not in case:
            fails.append(f"{where}: missing `{k}`")
    if case.get("id") and Path(path).stem != case["id"]:
        fails.append(f"{where}: id {case['id']!r} differs from the file name")
    src = str(case.get("source", ""))
    if not SOURCE_RE.match(src):
        fails.append(f"{where}: source {src!r} is neither a public issue number (#N) nor none")
    if case.get("tier") not in TIERS:
        fails.append(f"{where}: tier {case.get('tier')!r} is not one of {TIERS}")
    sit = case.get("situation") or {}
    if case.get("tier") == "agent":
        if not sit.get("workspace"):
            fails.append(f"{where}: situation.workspace missing")
        elif not fixture_dir(path, case).is_dir():
            fails.append(f"{where}: fixture {sit.get('workspace')!r} not found")
        if not prompts(case):
            fails.append(f"{where}: situation.prompt (or prompts) missing")
    exps = case.get("expectations") or []
    if not exps:
        fails.append(f"{where}: no expectations")
    for n, e in enumerate(exps, 1):
        ck = (e or {}).get("check")
        if ck not in CHECKS:
            fails.append(f"{where}: expectation {n}: unknown check {ck!r}")
            continue
        for k in CHECKS[ck]:
            if k not in e:
                fails.append(f"{where}: expectation {n} ({ck}): missing `{k}`")
        if ck == "tool_call_before":
            for side in ("first", "second"):
                if f"{side}_tool" not in e and f"{side}_text" not in e:
                    fails.append(f"{where}: expectation {n}: needs {side}_tool or {side}_text")
        for k, v in e.items():
            if k in ("pattern",) or k.endswith(("_input", "_text")) or k == "input_matches":
                try:
                    re.compile(str(v).replace("{workspace}", "W"))
                except re.error as err:
                    fails.append(f"{where}: expectation {n}: bad regex in {k}: {err}")


def fixture_dir(case_path, case):
    """situation.workspace is relative to the cases directory's parent."""
    return (Path(case_path).resolve().parent.parent / case["situation"]["workspace"]).resolve()


def prompts(case):
    sit = case.get("situation") or {}
    if sit.get("prompts"):
        return [str(p) for p in sit["prompts"]]
    return [str(sit["prompt"])] if sit.get("prompt") else []


# ---------------------------------------------------------------- transcripts

def flatten(value):
    """A tool input as plain text: every string value on its own line, so a
    pattern meets a command as the shell would, not JSON-escaped."""
    if isinstance(value, dict):
        return "\n".join(flatten(v) for _, v in sorted(value.items()))
    if isinstance(value, list):
        return "\n".join(flatten(v) for v in value)
    return "" if value is None else str(value)


class Transcript:
    """Main-agent tool batches and text per turn, plus subagent events.

    A batch is the run of tool_use blocks the main agent emits between two
    tool results; a turn is one prompt (run.sh writes an eval_turn marker
    line before each). Events with a non-null parent_tool_use_id belong to a
    subagent."""

    def __init__(self, path):
        self.batches = {}   # turn -> [[(name, input_json)], ...]
        self.text = {}      # turn -> [text]
        self.order = []     # (turn, kind, name, payload) in order, main agent
        self.sub = []       # (kind, name, payload) subagent
        self.bad_lines = 0
        turn, open_batch = 1, False
        for raw in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
            if not raw.strip():
                continue
            try:
                ev = json.loads(raw)
            except ValueError:
                self.bad_lines += 1
                continue
            if ev.get("type") == "eval_turn":
                turn, open_batch = int(ev.get("turn", turn + 1)), False
                continue
            sub = ev.get("parent_tool_use_id") not in (None, "")
            msg = ev.get("message") or {}
            content = msg.get("content") if isinstance(msg.get("content"), list) else []
            if ev.get("type") == "assistant":
                for block in content:
                    if block.get("type") == "tool_use":
                        item = (block.get("name", ""), flatten(block.get("input", {})))
                        if sub:
                            self.sub.append(("tool",) + item)
                            continue
                        if not open_batch:
                            self.batches.setdefault(turn, []).append([])
                            open_batch = True
                        self.batches[turn][-1].append(item)
                        self.order.append((turn, "tool") + item)
                    elif block.get("type") == "text":
                        if sub:
                            self.sub.append(("text", "", block.get("text", "")))
                            continue
                        self.text.setdefault(turn, []).append(block.get("text", ""))
                        self.order.append((turn, "text", "", block.get("text", "")))
            elif ev.get("type") == "user" and not sub:
                if any(b.get("type") == "tool_result" for b in content):
                    open_batch = False


def _match_tool(item, tool, pattern, ws):
    name, inp = item   # the tool name is a regex, matched whole: 'Task|Agent'
    return re.fullmatch(str(tool), name) is not None and (
        pattern is None or re.search(_pat(pattern, ws), inp) is not None)


def _pat(p, ws):
    return str(p).replace("{workspace}", re.escape(ws))


def evaluate(e, tr, run_dir, ws):
    """(verdict, note): True / False, or None for pending (grader)."""
    ck = e["check"]
    turn = int(e.get("turn", 1))
    if ck == "first_batch_includes_tool":
        batches = tr.batches.get(turn) or []
        if not batches:
            return False, f"no tool batch in turn {turn}"
        ok = any(_match_tool(i, e["tool"], e.get("input_matches"), ws) for i in batches[0])
        return ok, "" if ok else f"first batch of turn {turn}: {[n for n, _ in batches[0]]}"
    if ck == "same_batch":
        for b in tr.batches.get(turn, []) if "turn" in e else [b for t in sorted(tr.batches) for b in tr.batches[t]]:
            if any(_match_tool(i, e["a_tool"], e.get("a_input"), ws) for i in b) and \
               any(_match_tool(i, e["b_tool"], e.get("b_input"), ws) for i in b):
                return True, ""
        return False, "no batch holds both calls"
    if ck == "tool_call_before":
        def first_index(side):
            for n, (t, kind, name, payload) in enumerate(tr.order):
                if "turn" in e and t != turn:
                    continue
                if f"{side}_tool" in e and kind == "tool" and \
                        _match_tool((name, payload), e[f"{side}_tool"], e.get(f"{side}_input"), ws):
                    return n
                if f"{side}_text" in e and kind == "text" and re.search(_pat(e[f"{side}_text"], ws), payload):
                    return n
            return None
        a, b = first_index("first"), first_index("second")
        if a is None:
            return False, "first event never happened"
        if b is None:
            return (False, "second event never happened") if not e.get("second_optional") else (True, "")
        return a < b, "" if a < b else "second event came first"
    if ck in ("file_exists", "file_absent", "file_matches"):
        p = Path(run_dir) / "workspace" / e["path"]
        if ck == "file_exists":
            return p.exists(), "" if p.exists() else f"missing: {e['path']}"
        if ck == "file_absent":
            return not p.exists(), "" if not p.exists() else f"present: {e['path']}"
        if not p.is_file():
            return False, f"missing: {e['path']}"
        ok = re.search(_pat(e["pattern"], ws), p.read_text(encoding="utf-8", errors="replace"), re.M)
        return bool(ok), "" if ok else f"no match in {e['path']}"
    if ck in ("transcript_matches", "transcript_not_matches"):
        scope, agent = e.get("scope", "text"), e.get("agent", "main")
        hay = []
        if agent in ("main", "any"):
            for (t, kind, name, payload) in tr.order:
                if "turn" in e and t != turn:
                    continue
                if (scope == "text" and kind == "text") or (scope == "tool_input" and kind == "tool") or scope == "any":
                    hay.append(payload)
        if agent in ("sub", "any"):
            for (kind, name, payload) in tr.sub:
                if (scope == "text" and kind == "text") or (scope == "tool_input" and kind == "tool") or scope == "any":
                    hay.append(payload)
        found = any(re.search(_pat(e["pattern"], ws), h, re.M) for h in hay)
        if ck == "transcript_matches":
            return found, "" if found else "pattern not found"
        return not found, "" if not found else "pattern found"
    if ck == "grader":
        return None, "pending: blind grader"
    return False, f"unknown check {ck}"


# ---------------------------------------------------------------- grading

def grade_dir(results):
    """{case_id: {"runs": [...], "rule": str}} for one results directory."""
    out = {}
    for case_dir in sorted(p for p in Path(results).iterdir() if p.is_dir()):
        for run in sorted(p for p in case_dir.iterdir() if p.is_dir() and p.name.startswith("run-")):
            cf, tf = run / "case.yaml", run / "transcript.jsonl"
            if not cf.is_file() or not tf.is_file():
                continue
            case = load_case(cf)
            meta = json.loads((run / "meta.json").read_text()) if (run / "meta.json").is_file() else {}
            ws = meta.get("workspace_abs", str(run / "workspace"))
            tr = Transcript(tf)
            results_ = []
            for e in case["expectations"]:
                v, note = evaluate(e, tr, run, ws)
                results_.append({"check": e["check"], "verdict": v, "note": note})
            verdicts = [r["verdict"] for r in results_]
            run_v = False if False in verdicts else (None if None in verdicts else True)
            entry = out.setdefault(case["id"], {"rule": case.get("rule", ""), "runs": []})
            entry["runs"].append({"run": run.name, "pass": run_v, "assertions": results_,
                                  "bad_lines": tr.bad_lines, "dir": str(run)})
    return out


def rate(entry):
    runs = entry["runs"]
    passed = sum(1 for r in runs if r["pass"] is True)
    pending = sum(1 for r in runs if r["pass"] is None)
    return passed, len(runs), pending


def print_grades(graded):
    for cid, entry in graded.items():
        p, n, pend = rate(entry)
        print(f"{cid}: {p}/{n} runs pass" + (f", {pend} pending a grader" if pend else "") + f"  [{entry['rule']}]")
        k = len(entry["runs"][0]["assertions"]) if entry["runs"] else 0
        for i in range(k):
            col = [r["assertions"][i] for r in entry["runs"]]
            ok = sum(1 for a in col if a["verdict"] is True)
            pend = sum(1 for a in col if a["verdict"] is None)
            notes = sorted({a["note"] for a in col if a["verdict"] is False and a["note"]})
            print(f"    {i + 1}. {col[0]['check']}: {ok}/{len(col)}" + (f", {pend} pending" if pend else "")
                  + (f" — {'; '.join(notes)}" if notes else ""))
        bad = sum(r["bad_lines"] for r in entry["runs"])
        if bad:
            print(f"    NOTE: {bad} transcript lines were not JSON")


def grader_queue(graded, dest):
    """Blinded items for a model grader: no version, no path, shuffled ids."""
    items = []
    for cid, entry in graded.items():
        for r in entry["runs"]:
            for a in r["assertions"]:
                if a["verdict"] is None:
                    tr = Transcript(Path(r["dir"]) / "transcript.jsonl")
                    text = "\n".join(t for turn in sorted(tr.text) for t in tr.text[turn])
                    items.append({"case": cid, "text": text})
    random.shuffle(items)
    with open(dest, "w", encoding="utf-8") as f:
        for n, it in enumerate(items, 1):
            f.write(json.dumps({"item": n, **it}) + "\n")
    return len(items)


def summary(graded):
    return {cid: {"passed": rate(e)[0], "runs": rate(e)[1], "pending": rate(e)[2],
                  "rule": e["rule"],
                  "assertions": [[a["verdict"] for a in r["assertions"]] for r in e["runs"]]}
            for cid, e in graded.items()}


def drift_rows(old, new):
    rows = []
    for cid in sorted(set(old) | set(new)):
        o = rate(old[cid])[:2] if cid in old else None
        n = rate(new[cid])[:2] if cid in new else None
        ro = o[0] / o[1] if o and o[1] else None
        rn = n[0] / n[1] if n and n[1] else None
        flag = ""
        if ro is not None and rn is not None:
            flag = "REGRESSION" if rn < ro else ("improved" if rn > ro else "same")
        elif rn is None:
            flag = "not run in new"
        else:
            flag = "new case"
        rows.append((cid, o, n, flag))
    return rows


def print_drift(rows):
    print("| case | old | new | drift |")
    print("|---|---|---|---|")
    for cid, o, n, flag in rows:
        f = lambda x: f"{x[0]}/{x[1]}" if x else "—"
        print(f"| {cid} | {f(o)} | {f(n)} | {flag} |")


# ---------------------------------------------------------------- selftest

def selftest():
    fails = []
    base = HERE / "selftest"
    expected = json.loads((base / "expected.json").read_text())
    got = {}
    for label in ("results-old", "results-new"):
        g = grade_dir(base / label)
        for cid, e in g.items():
            for r in e["runs"]:
                got[f"{label}/{cid}/{r['run']}"] = {"pass": r["pass"],
                                                   "assertions": [a["verdict"] for a in r["assertions"]]}
        if label == "results-old":
            old = g
        else:
            new = g
    n = 0
    for key, want in expected["runs"].items():
        n += 1
        have = got.get(key)
        if have is None:
            fails.append(f"{key}: not graded")
        elif have != want:
            fails.append(f"{key}: expected {want}, got {have}")
    for key in sorted(set(got) - set(expected["runs"])):
        fails.append(f"{key}: graded but has no expected verdict")
    rows = {cid: flag for cid, o, nn, flag in drift_rows(old, new)}
    for cid, flag in expected["drift"].items():
        n += 1
        if rows.get(cid) != flag:
            fails.append(f"drift {cid}: expected {flag}, got {rows.get(cid)}")
    # the shipped cases validate, and the subset reader agrees with PyYAML
    case_fails = []
    paths = sorted((HERE / "cases").glob("*.yaml")) + sorted(base.glob("results-*/*/run-*/case.yaml"))
    for p in sorted((HERE / "cases").glob("*.yaml")):
        check_case(p, load_case(p), case_fails)
    fails += case_fails
    try:
        import yaml
        for p in paths:
            n += 1
            if yaml.safe_load(p.read_text()) != read_subset(p.read_text()):
                fails.append(f"{p}: the subset reader and PyYAML disagree")
    except ImportError:
        print("note: PyYAML not installed — subset-reader agreement not checked")
    # the subset reader on its own fixture
    sample = "a: 1\nb:\n  c: 'x '' y'\n  d: |\n    line 1\n    line 2\nl:\n  - check: t\n    k: \"q\\\"\"\n  - plain\n"
    n += 1
    want = {"a": 1, "b": {"c": "x ' y", "d": "line 1\nline 2\n"}, "l": [{"check": "t", "k": 'q"'}, "plain"]}
    if read_subset(sample) != want:
        fails.append(f"subset reader fixture: got {read_subset(sample)!r}")
    print(f"selftest: {n} checks, {len(fails)} failed")
    for f in fails:
        print("  FAIL " + f)
    return 1 if fails else 0


# ---------------------------------------------------------------- main

def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if argv else 2
    cmd, args = argv[0], argv[1:]
    if cmd == "grade" and args:
        g = grade_dir(args[0])
        if not g:
            print(f"GRADE BROKEN — no graded runs under {args[0]} (expected <case>/run-<n>/transcript.jsonl)")
            return 1
        print_grades(g)
        dest = args[args.index("--json") + 1] if "--json" in args else str(Path(args[0]) / "summary.json")
        Path(dest).write_text(json.dumps(summary(g), indent=2) + "\n")
        q = grader_queue(g, str(Path(dest).with_name("grader-queue.jsonl")))
        print(f"summary: {dest}" + (f"; {q} items queued for the blind grader" if q else ""))
        return 0
    if cmd == "drift" and len(args) == 2:
        old, new = grade_dir(args[0]), grade_dir(args[1])
        if not old or not new:
            print("DRIFT BROKEN — a results directory held no graded runs")
            return 1
        print_drift(drift_rows(old, new))
        return 0
    if cmd == "check" and args:
        fails, n = [], 0
        for d in args:
            for p in sorted(Path(d).glob("*.yaml")):
                n += 1
                check_case(p, load_case(p), fails)
        print(f"cases checked: {n}; problems: {len(fails)}")
        for f in fails:
            print("  " + f)
        return 1 if fails or n == 0 else 0
    if cmd == "export" and len(args) == 1:
        case = load_case(args[0])
        fails = []
        check_case(args[0], case, fails)
        if fails:
            print("\n".join(fails), file=sys.stderr)
            return 2
        sit = case["situation"]
        print(json.dumps({"id": case["id"], "skill": case["skill"], "tier": case["tier"],
                          "fixture": str(fixture_dir(args[0], case)) if case["tier"] == "agent" else "",
                          "prompts": prompts(case),
                          "skill_from_turn": int(sit.get("skill_installed_from_turn", 1))}))
        return 0
    if cmd == "selftest":
        return selftest()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
