"""Tests for scripts/validate-skill-bundle.py — the pre-delivery gate.

Every check is "measure -> compare to bound in the same step" (an unasserted
metric manufactures confidence). Tests here pin each bound and each measured
failure so loosening one is a visible diff, not silent regression.

Also pins two subtle invariants the code comments call out:
* a ZIP member path containing a backslash must be detected from the raw
  central-directory bytes (`zipfile.namelist` hides it);
* `Path('.').name` is '' — the script resolves the dir first.
"""

import pathlib
import subprocess
import sys
import zipfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
VALIDATE = ROOT / "scripts" / "validate-skill-bundle.py"


# ---------------------------------------------------------------- helpers ---

def skill_md(name, description="A test skill.", body="", extra=""):
    extra = (extra.rstrip("\n") + "\n") if extra else ""
    return f"---\nname: {name}\n{extra}description: {description}\n---\n\n# {name}\n\n{body}\n"


def staged(tmp_path, name, description="A test skill.", body="", extra="", cited=None):
    """Create a staged skill dir and return its Path."""
    d = tmp_path / name
    d.mkdir()
    (d / "SKILL.md").write_text(skill_md(name, description, body, extra))
    if cited:
        for rel in cited:
            fp = d / rel
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text("# ref", encoding="utf-8")
    return d


# --------------------------------------------------------- structural checks --

def test_ok_staged_dir_passes(validate, tmp_path):
    d = staged(tmp_path, "task-observer", cited=["references/guide.md"],
               body="Load `references/guide.md` when needed.")
    fails: list = []
    validate.check_dir(d, fails)
    assert not fails


def test_missing_skill_md(validate, tmp_path):
    d = tmp_path / "some-skill"
    d.mkdir()
    fails: list = []
    validate.check_dir(d, fails)
    assert any("SKILL.md missing" in m for m in fails)


def test_no_frontmatter(validate, tmp_path):
    d = tmp_path / "demo-skill"
    d.mkdir()
    (d / "SKILL.md").write_text("# no frontmatter\n", encoding="utf-8")
    fails: list = []
    validate.check_dir(d, fails)
    assert any("no leading --- block" in m for m in fails)


def test_frontmatter_not_a_mapping(validate, tmp_path, monkeypatch):
    # Deterministic: force `import yaml` to succeed so the YAML branch runs,
    # then hand it a doc that parses to a list rather than a mapping.
    class _FakeYaml:
        @staticmethod
        def safe_load(fm):
            return ["a", "list"]
    monkeypatch.setitem(sys.modules, "yaml", _FakeYaml())

    d = tmp_path / "demo-skill"
    d.mkdir()
    (d / "SKILL.md").write_text("---\n- list\n---\n\nbody", encoding="utf-8")
    fails: list = []
    validate.check_dir(d, fails)
    assert any("does not parse to a mapping" in m for m in fails)


def test_regex_fallback_when_yaml_absent(validate, tmp_path, monkeypatch):
    # None in sys.modules makes `import yaml` raise ImportError, forcing the
    # documented regex fallback. name + folded description are recovered, so a
    # valid bundle still passes without PyYAML installed.
    monkeypatch.setitem(sys.modules, "yaml", None)
    d = tmp_path / "demo-skill"
    d.mkdir()
    (d / "SKILL.md").write_text(skill_md("demo-skill"), encoding="utf-8")
    fails: list = []
    validate.check_dir(d, fails)
    assert not fails


@pytest.mark.parametrize("name", ["MySkill", "my_skill", "MY-SKILL", "UPPER"])
def test_name_not_kebab_case(validate, tmp_path, name):
    d = tmp_path / name
    d.mkdir()
    (d / "SKILL.md").write_text(skill_md(name), encoding="utf-8")
    fails: list = []
    validate.check_dir(d, fails)
    assert any("not kebab-case" in m for m in fails)


def test_name_missing(validate, tmp_path):
    d = tmp_path / "anon-skill"
    d.mkdir()
    (d / "SKILL.md").write_text("---\ndescription: x\n---\n\nbody", encoding="utf-8")
    fails: list = []
    validate.check_dir(d, fails)
    assert any("`name` missing" in m for m in fails)


def test_name_mismatch_dir(validate, tmp_path):
    d = tmp_path / "foo"
    d.mkdir()
    (d / "SKILL.md").write_text(skill_md("bar"), encoding="utf-8")
    fails: list = []
    validate.check_dir(d, fails)
    assert any("!= directory" in m for m in fails)


def test_description_missing(validate, tmp_path):
    d = tmp_path / "demo-skill"
    d.mkdir()
    (d / "SKILL.md").write_text("---\nname: demo-skill\n---\n\nbody", encoding="utf-8")
    fails: list = []
    validate.check_dir(d, fails)
    assert any("`description` missing" in m for m in fails)


def test_description_over_cap(validate, tmp_path):
    d = staged(tmp_path, "demo-skill", description="x" * 1500)
    fails: list = []
    validate.check_dir(d, fails)
    assert any("chars > cap" in m for m in fails)


def test_folded_description(validate):
    fm = "name: demo-skill\ndescription: >-\n  hello world\n  foo bar\n"
    assert validate.folded_description(fm) == "hello world foo bar"

    fm2 = 'name: demo-skill\ndescription: "plain inline"\n'
    assert validate.folded_description(fm2) == "plain inline"


def test_cited_path_missing(validate, tmp_path):
    d = staged(tmp_path, "demo-skill",
               body="See `references/guide.md` for details.")
    fails: list = []
    validate.check_dir(d, fails)
    assert any("cited path missing" in m and "references/guide.md" in m
               for m in fails)


def test_cited_path_present_no_fail(validate, tmp_path):
    d = staged(tmp_path, "demo-skill", cited=["references/guide.md"],
               body="See `references/guide.md`.")
    fails: list = []
    validate.check_dir(d, fails)
    assert not any("cited path missing" in m for m in fails)


@pytest.mark.parametrize("rel", [
    "__pycache__/x.py", ".DS_Store",
])
def test_build_junk_in_tree(validate, tmp_path, rel):
    d = staged(tmp_path, "demo-skill")
    p = d / rel
    if rel == ".DS_Store":
        p.write_text("junk", encoding="utf-8")
    else:
        p.mkdir(parents=True, exist_ok=True)
        (p / "cache.py").write_text("x", encoding="utf-8")
    fails: list = []
    validate.check_dir(d, fails)
    assert any("build artefact" in m for m in fails)


def test_pyc_junk(validate, tmp_path):
    d = staged(tmp_path, "demo-skill")
    (d / "foo.pyc").write_text("junk", encoding="utf-8")
    fails: list = []
    validate.check_dir(d, fails)
    assert any("build artefact" in m for m in fails)


def test_dot_lock_junk(validate, tmp_path):
    d = staged(tmp_path, "demo-skill")
    (d / ".~lock.docx#").write_text("junk", encoding="utf-8")
    fails: list = []
    validate.check_dir(d, fails)
    assert any("build artefact" in m for m in fails)


# -------------------------------------------------------------- ZIP checks ---

def test_pack_uses_posix_separators(validate, tmp_path):
    d = staged(tmp_path, "demo-skill", cited=["references/guide.md"])
    out = tmp_path / "bundle.skill"
    validate.pack(d, out)

    with zipfile.ZipFile(out) as z:
        names = z.namelist()
    assert names  # at least one member
    assert "\\" not in "\n".join(names)
    assert all(n.startswith("demo-skill/") for n in names)

    # and it passes the raw-byte gate too
    fails: list = []
    validate.check_bundle(out, fails)
    assert not fails


def test_check_bundle_detects_backslash(validate, tmp_path):
    # The gate scans the raw central-directory bytes rather than trusting
    # zipfile.namelist() (the code comment notes the convenience reader can
    # rewrite separators). Write a member whose stored name really contains a
    # literal 0x5C and confirm the raw scan flags it.
    path = tmp_path / "evil.skill"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("task-observer\\evil.txt", "x")
    fails: list = []
    validate.check_bundle(path, fails)
    assert any("backslash" in m for m in fails)


def test_bundle_no_members(validate, tmp_path):
    path = tmp_path / "empty.skill"
    with zipfile.ZipFile(path, "w"):
        pass
    fails: list = []
    validate.check_bundle(path, fails)
    assert any("no members found" in m for m in fails)


# ------------------------------------------------------------ exit codes -----

def test_main_pack_verify_ok(tmp_path):
    d = staged(tmp_path, "demo-skill", cited=["references/guide.md"],
               body="See `references/guide.md`.")
    out = tmp_path / "ok.skill"
    r = subprocess.run(
        [sys.executable, str(VALIDATE), str(d), "--pack", str(out)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    assert "OK: all gate checks passed" in r.stdout
    assert out.is_file()


def test_main_dir_fail_exit1(tmp_path):
    # no SKILL.md — real process-level failure path
    d = tmp_path / "bad-skill"
    d.mkdir()
    r = subprocess.run(
        [sys.executable, str(VALIDATE), str(d)],
        capture_output=True, text=True,
    )
    assert r.returncode == 1
    assert "FAIL:" in r.stdout

    # and --bundle over a backslashed archive returns 1 even when the dir itself is fine
    good = staged(tmp_path, "ok")
    evil = tmp_path / "evil2.skill"
    with zipfile.ZipFile(evil, "w") as z:
        z.writestr("ok\\evil.txt", "x")
    r2 = subprocess.run(
        [sys.executable, str(VALIDATE), str(good), "--bundle", str(evil)],
        capture_output=True, text=True,
    )
    assert r2.returncode == 1
    assert "backslash" in r2.stdout
