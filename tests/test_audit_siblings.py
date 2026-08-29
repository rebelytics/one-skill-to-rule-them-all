"""Tests for scripts/audit-siblings.py — the sibling-check discipline audit.

Pins the proposed finding matrix. Every finding key is a deterministic,
machine-checkable fact; these tests assert both the key and the process-level
exit code (0 clean / 1 findings / 2 broken input) where it matters.
"""

import json
import subprocess
import sys

import pytest

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
AUDIT = ROOT / "scripts" / "audit-siblings.py"


# ---------------------------------------------------------------- helpers ---

DEFAULT_FIELDS = {
    "id": "1",
    "title": "Some observation",
    "status": "open",
    "skill": '["task-observer"]',
    "siblings_checked": "none",
    "date": "2026-01-01",
}


def obs(body="body text\n", drop=(), **overrides):
    """Build an observation file's text from an explicit, deterministic
    frontmatter (no YAML library involved)."""
    fields = dict(DEFAULT_FIELDS)
    fields.update(overrides)
    lines = ["---"]
    for k in DEFAULT_FIELDS:
        if k in drop:
            continue
        if k in fields:
            lines.append(f"{k}: {fields[k]}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body


def build_log(base, specs):
    d = base / "oblog"
    d.mkdir(parents=True)
    for name, content in specs:
        (d / name).write_text(content, encoding="utf-8")
    return d


def run_cli(*args, cwd=None):
    return subprocess.run([sys.executable, str(AUDIT), *args],
                          capture_output=True, text=True, cwd=cwd)


# --------------------------------------------------------------- clean log ---

def test_clean_log_no_findings(tmp_path):
    d = build_log(tmp_path, [
        ("0001-a.md", obs(id="1", skill='["task-observer"]',
                          siblings_checked="none")),
        ("0002-b.md", obs(id="2", skill='["a"]',
                          siblings_checked="family: a, b — "
                                            "instance-specific, no propagation")),
    ])
    r = run_cli(str(d), cwd=tmp_path)
    assert r.returncode == 0
    assert "OK: audit clean" in r.stdout
    assert "observations logged without a sibling check: 0" in r.stdout


# ---------------------------------------------------------- field absence ----

def test_missing_siblings_checked(tmp_path):
    d = build_log(tmp_path, [("0001-x.md", obs(drop=("siblings_checked",)))])
    r = run_cli(str(d), cwd=tmp_path)
    assert r.returncode == 1
    assert "missing-sibling-check" in r.stdout
    assert "observations logged without a sibling check: 1" in r.stdout


def test_blank_siblings_checked(tmp_path):
    d = build_log(tmp_path, [("0001-x.md", obs(siblings_checked=""))])
    r = run_cli(str(d), cwd=tmp_path)
    assert r.returncode == 1
    assert "missing-sibling-check" in r.stdout


def test_malformed_siblings_checked(tmp_path):
    d = build_log(tmp_path, [("0001-x.md", obs(siblings_checked="sort of"))])
    r = run_cli(str(d), cwd=tmp_path)
    assert r.returncode == 1
    assert "malformed-sibling-check" in r.stdout


# --------------------------------------------------------------- verdicts ----

def test_propagation_underlist_single_skill(tmp_path):
    d = build_log(tmp_path, [("0001-x.md", obs(
        skill='["a"]',
        siblings_checked="family: a, b — shared, both added"))])
    r = run_cli(str(d), cwd=tmp_path)
    assert r.returncode == 1
    assert "propagation-underlist" in r.stdout


def test_propagation_named_sibling_absent_from_skill(tmp_path):
    """skill has >=2 entries but the verdict names a family member that is
    absent from `skill` — the named-members arm of propagation-underlist."""
    d = build_log(tmp_path, [("0001-x.md", obs(
        skill='["a", "c"]',
        siblings_checked="family: a, b — shared, both added"))])
    r = run_cli(str(d), cwd=tmp_path)
    assert r.returncode == 1
    assert "propagation-underlist" in r.stdout


def test_propagation_consistent_multi_skill_ok(tmp_path):
    d = build_log(tmp_path, [("0001-x.md", obs(
        skill='["a", "b"]',
        siblings_checked="family: a, b — shared, both added"))])
    r = run_cli(str(d), cwd=tmp_path)
    assert r.returncode == 0


def test_instance_specific_single_skill_ok(tmp_path):
    d = build_log(tmp_path, [("0001-x.md", obs(
        skill='["a"]',
        siblings_checked="family: a, b — instance-specific, no propagation"))])
    r = run_cli(str(d), cwd=tmp_path)
    assert r.returncode == 0


# ------------------------------------------------- generic-insight detection -

def test_generic_phrase_single_skill_flagged(tmp_path):
    d = build_log(tmp_path, [("0001-x.md", obs(
        skill='["x"]',
        body="This design applies to any file-writing script.\n"))])
    r = run_cli(str(d), cwd=tmp_path)
    assert r.returncode == 1
    assert "generic-insight-under-scoped" in r.stdout


def test_generic_phrase_multi_skill_not_flagged(tmp_path):
    d = build_log(tmp_path, [("0001-x.md", obs(
        skill='["x", "y"]',
        body="This design applies to any file-writing script.\n"))])
    r = run_cli(str(d), cwd=tmp_path)
    assert r.returncode == 0


# ------------------------------------------------------------ the registry ---

def test_registry_family_member_marked_none(tmp_path):
    d = build_log(tmp_path, [("0001-x.md", obs(skill='["a"]',
                                               siblings_checked="none"))])
    reg = tmp_path / "families.md"
    reg.write_text("## filers\n**Members:** a, b\n"
                   "**Coherence model:** synced-duplicates\n", encoding="utf-8")
    r = run_cli(str(d), "--registry", str(reg), cwd=tmp_path)
    assert r.returncode == 1
    assert "family-member-marked-none" in r.stdout


def test_registry_parses_families(audit):
    mf = audit.parse_registry(
        "## filers\n**Members:** a, b\n"
        "## uploaders\n**Members:** b, c\n")
    assert mf["a"] == {"filers"}
    assert mf["b"] == {"filers", "uploaders"}
    assert mf["c"] == {"uploaders"}


def test_no_registry_still_runs_field_checks(tmp_path):
    d = build_log(tmp_path, [("0001-x.md", obs(drop=("siblings_checked",)))])
    r = run_cli(str(d), cwd=tmp_path)      # deliberately no --registry
    assert r.returncode == 1
    assert "missing-sibling-check" in r.stdout


# ---------------------------------------------------------- scan guard / IO --

def test_broken_scan_guard_exit2(tmp_path):
    d = tmp_path / "oblog"
    d.mkdir()
    (d / "0001-nofm.md").write_text("# no frontmatter\n\nbody\n",
                                    encoding="utf-8")
    r = run_cli(str(d), cwd=tmp_path)
    assert r.returncode == 2
    assert "SCAN BROKEN" in r.stderr


def test_exit_codes_0_and_1(tmp_path):
    bad = build_log(tmp_path, [("0001-x.md", obs(drop=("siblings_checked",)))])
    assert run_cli(str(bad), cwd=tmp_path).returncode == 1
    good = build_log(tmp_path / "clean", [("0001-x.md", obs())])
    assert run_cli(str(good), cwd=tmp_path).returncode == 0


# ---------------------------------------------------------------- JSON out --

def test_json_output(tmp_path):
    d = build_log(tmp_path, [("0001-x.md", obs(drop=("siblings_checked",)))])
    r = run_cli(str(d), "--json", cwd=tmp_path)
    assert r.returncode == 1
    payload = json.loads(r.stdout)
    assert payload["observations"] == 1
    assert payload["findings_count"] == 1
    assert payload["observations_without_sibling_check"] == 1
    # deterministic, machine-readable finding
    f = payload["findings"][0]
    assert f["key"] == "missing-sibling-check"
    assert f["id"] == 1


# ------------------------------------------------------- non-integer id sort --

def test_non_numeric_id_does_not_crash(tmp_path):
    """A non-integer `id` must coerce to None so the deterministic sort never
    compares an int against a non-int (TypeError). Findings still reported."""
    d = build_log(tmp_path, [
        ("0001-a.md", obs(id="abc", drop=("siblings_checked",))),
        ("0002-b.md", obs(id="2", drop=("siblings_checked",))),
    ])
    r = run_cli(str(d), cwd=tmp_path)
    assert r.returncode == 1
    assert "Traceback" not in r.stderr
    # both observations still produce their finding
    assert r.stdout.count("missing-sibling-check") == 2


def test_id_as_list_does_not_crash(tmp_path):
    """`id: [1]` parses to a list; int() must fail gracefully to None."""
    d = build_log(tmp_path, [("0001-a.md", obs(id="[1]", drop=("siblings_checked",)))])
    r = run_cli(str(d), cwd=tmp_path)
    assert r.returncode == 1
    assert "Traceback" not in r.stderr
    assert "missing-sibling-check" in r.stdout


def test_json_deterministic_with_mixed_ids(tmp_path):
    """Mixed int/non-int IDs sort deterministically and never crash in --json."""
    d = build_log(tmp_path, [
        ("0001-a.md", obs(id="abc", drop=("siblings_checked",))),
        ("0002-b.md", obs(id="2", drop=("siblings_checked",))),
        ("0003-c.md", obs(id="[9]", drop=("siblings_checked",))),
    ])
    r1 = run_cli(str(d), "--json", cwd=tmp_path)
    r2 = run_cli(str(d), "--json", cwd=tmp_path)
    assert r1.returncode == 1
    assert r1.stdout == r2.stdout          # deterministic across runs
    payload = json.loads(r1.stdout)
    ids = [f["id"] for f in payload["findings"]]
    assert 2 in ids                        # the clean int sorts normally


# ------------------------------------------------- negative propagation ------

def test_negative_verdict_not_treated_as_propagation(tmp_path):
    """'not shared' / 'not added' must not read as positive propagation merely
    because they contain 'shared' / 'added' — no propagation-underlist finding."""
    d = build_log(tmp_path, [
        ("0001-a.md", obs(id="1", skill='["a"]',
                          siblings_checked="family: a, b — "
                                            "not shared, instance-specific")),
        ("0002-b.md", obs(id="2", skill='["b"]',
                          siblings_checked="family: a, b — "
                                            "not added to siblings")),
    ])
    r = run_cli(str(d), cwd=tmp_path)
    assert r.returncode == 0
    assert "OK: audit clean" in r.stdout
    assert "propagation-underlist" not in r.stdout
