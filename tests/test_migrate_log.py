"""Tests for scripts/migrate-log.py — legacy single-file log -> per-file.

Pins the failure modes the project documents in references/migration.md and
references/observation-log.md:
* the resolution date is read ONLY from the marker region before the em-dash
  (reading it from the free text invented a wrong `resolved` for hundreds of
  archived entries);
* `skill` is always a list;
* unknown metadata labels stay in the body verbatim;
* ambiguity is flagged (migration_note), never guessed;
* check-only mode writes nothing.
"""

import subprocess
import sys

import pytest

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
MIGRATE = ROOT / "scripts" / "migrate-log.py"


def run_cli(tmp_path, *args, cwd=None):
    return subprocess.run(
        [sys.executable, str(MIGRATE), *args],
        capture_output=True, text=True, cwd=cwd or tmp_path,
    )


@pytest.fixture
def log_file(tmp_path):
    """Write a legacy single-file log and return (log_path, tmp_path)."""

    def write(text, name="log.md"):
        p = tmp_path / name
        p.write_text(text, encoding="utf-8")
        return p

    return write, tmp_path


# ---------------------------------------------------------------- helpers ---

def render(migrate, entry_text, **kw):
    """Parse a bare multi-entry text and render all records to strings."""
    from collections import namedtuple
    records = []
    for e in migrate.parse_entries(entry_text, "test.md"):
        rec = migrate.to_record(e, kw.get("known", set()))
        records.append(migrate.render(rec))
    return records


# ------------------------------------------------ end-to-end conversion ----

LEGACY = """\
# The observation log

### Observation 1: First observation
**Date:** 2026-01-01
**Type:** open-source
**Skill:** task-observer
**Phase/Area:** core
**Session context:** testing
**Status:** OPEN

Body text here.

### Observation 2: Second observation
**Status:** ACTIONED (2026-01-05) — applied in weekly review
**Date:** 2026-01-02
**Skill:** task-observer (How to Log)

Fixed it.
"""


def test_basic_conversion_end_to_end(log_file):
    write, tmp = log_file
    log = write(LEGACY)
    r = run_cli(tmp, "--convert", str(log), "--out", str(tmp / "out"))
    assert r.returncode == 0
    assert "wrote 2 files" in r.stdout

    f1 = tmp / "out" / "0001-first-observation.md"
    f2 = tmp / "out" / "0002-second-observation.md"
    assert f1.is_file() and f2.is_file()

    text1 = f1.read_text(encoding="utf-8")
    for line in ["id: 1", "title: \"First observation\"",
                 "status: open", "skill: [\"task-observer\"]",
                 "date: 2026-01-01", "Body text here."]:
        assert line in text1

    # entry 2 has a resolution date in the marker region -> resolved set
    text2 = f2.read_text(encoding="utf-8")
    assert "resolved: 2026-01-05" in text2
    # single-skill qualifier promoted into area
    assert "area: \"How to Log\"" in text2


def test_skill_always_a_list(migrate):
    out = render(migrate, "### Observation 1: X\n**Skill:** task-observer\n\nb")
    assert 'skill: ["task-observer"]' in out[0]
    assert 'skill: "task-observer"' not in out[0]


def test_new_skill_candidate_goes_to_proposes(migrate):
    out = render(migrate,
                 "### Observation 1: X\n**Skill:** New skill candidate: helper-ctl\n\nb")
    assert 'proposes_skill: ["helper-ctl"]' in out[0]
    assert "skill: []" in out[0]


def test_resolution_date_from_marker_region_only(migrate):
    """The documented regression: a date in the free text after the dash is
    NOT the resolution date."""
    raw = ("### Observation 1: X\n"
           "**Status:** ACTIONED (2026-01-05) — applied in weekly review 2026-03-04\n"
           "**Date:** 2026-01-02\n"
           "**Skill:** task-observer\n\nb")
    out = render(migrate, raw)
    assert "resolved: 2026-01-05" in out[0]
    assert "resolved: 2026-03-04" not in out[0]
    # resolution free text preserved, not misread as a date
    assert 'resolution: "applied in weekly review 2026-03-04"' in out[0]
    # no 'needs review' noise for a properly-dated resolution
    assert "migration_note" not in out[0]


def test_date_in_text_after_dash_is_hint_not_resolved(migrate):
    raw = ("### Observation 1: X\n"
           "**Status:** ACTIONED — staged to skill-updates/2026-08-14\n\nb")
    out = render(migrate, raw)
    # no authoritative resolved date (none in marker region)
    assert "resolved: 2026-08-14" not in out[0]
    # the candidate is surfaced as an unconfirmed hint + needs-review flag
    assert "unconfirmed" in out[0]
    assert "resolved-date-missing" in out[0]


def test_open_with_trailing_note_is_status_note(migrate):
    raw = ("### Observation 1: X\n"
           "**Status:** OPEN — handed to session E\n\nb")
    out = render(migrate, raw)
    assert 'status_note: "handed to session E"' in out[0]
    assert "resolution:" not in out[0]


def test_unknown_labels_kept_in_body(migrate):
    raw = ("### Observation 1: X\n"
           "**Status:** OPEN\n"
           "**Date:** 2026-01-01\n"
           "**Fix applied:** thing\n\nbody")
    out = render(migrate, raw)
    # 'Fix applied' is not a lifted label -> stays verbatim in the body
    assert "**Fix applied:** thing" in out[0]
    # once the body begins, following blank lines are preserved, not stripped
    assert "**Fix applied:** thing\n\nbody" in out[0]


def test_split_top_level_respects_parens(migrate):
    assert migrate.split_top_level("a (x; y); b", ";") == ["a (x; y)", "b"]
    assert migrate.split_top_level("one; two", ";") == ["one", "two"]
    assert migrate.split_top_level("(solo)", ";") == ["(solo)"]


def test_single_skill_qualifier_promotes_to_area(migrate):
    recs = list(migrate.parse_entries(
        "### Observation 1: X\n**Skill:** task-observer (How to Log)\n\nb", "t"))
    rec = migrate.to_record(recs[0], set())
    assert rec["skill"] == ["task-observer"]
    assert rec["area"] == "How to Log"          # no 'How to Log' lost
    assert not rec["skill_qualifiers"]


def test_all_skills_sentinel(migrate):
    recs = list(migrate.parse_entries(
        "### Observation 1: X\n**Skill:** all skills\n\nb", "t"))
    rec = migrate.to_record(recs[0], set())
    assert rec["skill"] == ["all-skills"]
    assert "skill-all-skills-sentinel" in rec["flags"]


def test_duplicate_id_flagged(log_file):
    write, tmp = log_file
    dup = ("### Observation 7: One\n**Status:** OPEN\n\nb\n"
           "### Observation 7: Two\n**Status:** OPEN\n\nc\n")
    log = write(dup)
    r = run_cli(tmp, "--check", str(log))
    assert r.returncode == 0
    assert "duplicate-id" in r.stdout
    # both flagged -> needs human review (duplicate-id is a REVIEW_FLAG)
    assert "needs human review: 2/2" in r.stdout


def test_id_floor_from_scans_archive(migrate, tmp_path):
    # nested "_legacy" holds monolithic archive entries; root holds per-file ids
    (tmp_path / "root").mkdir()
    (tmp_path / "root" / "12-foo.md").write_text("x", encoding="utf-8")
    arch = tmp_path / "root" / "archive"
    arch.mkdir()
    (arch / "legacy.md").write_text(
        "### Observation 8: old\n...\n### Observation 42: older\n", encoding="utf-8")
    (arch / "9-zip.md").write_text("x", encoding="utf-8")
    assert migrate.id_floor_from([tmp_path / "root"]) == 42


def test_convert_writes_id_floor(log_file):
    write, tmp = log_file
    write("### Observation 3: X\n**Status:** OPEN\n\nb")
    r = run_cli(tmp, "--convert", str(tmp / "log.md"),
                "--out", str(tmp / "out"), "--id-floor-from", str(tmp))
    assert r.returncode == 0
    floor = (tmp / "out" / "archive" / ".id-floor").read_text().strip()
    assert floor == "3"


def test_date_not_iso_flagged(migrate):
    recs = list(migrate.parse_entries(
        "### Observation 1: X\n**Date:** Jan 5 2026\n\nb", "t"))
    rec = migrate.to_record(recs[0], set())
    assert "date-not-iso" in rec["flags"]


def test_status_unrecognised(migrate):
    recs = list(migrate.parse_entries(
        "### Observation 1: X\n**Status:** RESOLVED\n\nb", "t"))
    rec = migrate.to_record(recs[0], set())
    assert "status-unrecognised" in rec["flags"]
    assert rec["status"] == "open"          # safe fallback


def test_status_missing(migrate):
    recs = list(migrate.parse_entries(
        "### Observation 1: X\n**Date:** 2026-01-01\n\nb", "t"))
    rec = migrate.to_record(recs[0], set())
    assert "status-missing" in rec["flags"]
    # a status-missing entry earns a migration_note (review-gated flag)
    out = migrate.render(rec)
    assert "migration_note" in out


def test_overrides_resolve_flags_and_set_fields(log_file):
    write, tmp = log_file
    # entry 5 has no Skill line -> would be flagged skill-missing
    log = write("### Observation 5: X\n**Status:** OPEN\n\nb")
    ov = tmp / "overrides.json"
    ov.write_text(
        '{"5": {"_resolves": ["skill-missing"], "_reason": "it is a new skill",'
        ' "skill": ["existing-skill"], "proposes_skill": ["candidate-name"]}}',
        encoding="utf-8")
    r = run_cli(tmp, "--convert", str(log), "--out", str(tmp / "out"),
                "--overrides", str(ov))
    assert r.returncode == 0
    text = (tmp / "out" / "0005-x.md").read_text(encoding="utf-8")
    assert 'skill: ["existing-skill"]' in text
    assert 'proposes_skill: ["candidate-name"]' in text
    assert 'migration_override: "it is a new skill"' in text
    # the resolved flag no longer names skill-missing
    assert "skill-missing" not in text


def test_check_mode_writes_nothing(log_file):
    write, tmp = log_file
    outdir = tmp / "out"
    log = write(LEGACY)
    r = run_cli(tmp, "--check", str(log), "--out", str(outdir))
    assert r.returncode == 0
    assert "parsed 2 entries" in r.stdout
    # --check must not create the out dir or any files
    assert not outdir.exists()
    assert sorted(p.name for p in tmp.iterdir()) == ["log.md"]


def test_slugify_len_and_empty(migrate):
    assert len(migrate.slugify("A" * 70)) <= 60
    # truncated at the LAST hyphen, so "aaa-" does not survive
    s = migrate.slugify("word " + "x" * 80)
    assert not s.endswith("-")
    assert migrate.slugify("!!!") == "untitled"
