#!/usr/bin/env python3
"""
validate-skill-bundle.py — the pre-delivery gate, as assertions.

Checks a staged skill directory (and optionally its packed .skill bundle)
against the criteria the INSTALLER enforces, not against what seems
sensible. Every check compares a measurement to a bound in the same step:
an unasserted metric manufactures confidence that no defect exists.

Usage
-----
  python3 validate-skill-bundle.py <staged-skill-dir> [--bundle file.skill] [--pack out.skill]
  python3 validate-skill-bundle.py --repo-only <repo-dir>

  --pack        writes a well-formed bundle (POSIX separators on any platform)
                after the directory checks pass, then validates it.
  --repo        additionally check the repo's manifests against the skill.
  --repo-only   check ONLY the repo's manifests, skipping the skill checks.
                Also runs the markdown shape check over the repo-root .md
                files (README, guides): a blank line splitting one list in
                two is reported as a failure with file:line.

Why --repo-only exists: in a repo whose root IS the skill directory
(`SKILL.md` at the top level), the two check sets contradict each other.
The skill checks require the directory name to equal the frontmatter `name`
and forbid a plugin manifest; the repo is named after the repository, not
the skill, and is the one place the manifest belongs. Running the skill
checks over a repo root therefore reports two failures that are both
correct behaviour. Point the skill checks at the staged skill directory and
`--repo-only` at the repo.

Exit status 0 = every check passed; 1 = at least one failed (all failures
are listed, not just the first).

Limits are stated as numbers and labelled with where they come from, so
the check is implementable without guessing and can be updated when the
consumer changes them.
"""

import pathlib
import re
import struct
import sys
import zipfile

MAX_DESCRIPTION_CHARS = 1024   # installer's documented cap on the folded description
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")   # kebab-case
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

# --- Core-size ratchet -------------------------------------------------------
# The per-session core is loaded in full, every session, by every consumer of
# the skill. It has grown before: a split brought it down and two months of
# ordinary review rounds put it back, because nothing in the loop pushed the
# other way. A guideline that is only prose loses to a hundred individually
# reasonable additions.
#
# CEILING ONLY EVER GOES DOWN. Raising it is not a fix for a failing gate; it
# is the failure. A release that needs more room in the core needs a split
# instead, and the reference files are where the room is. The number below is
# the high-water mark at the release that introduced this check — every later
# release either holds it or lowers it.
#
# TARGET is the size the core is trying to reach. The gap between CEILING and
# TARGET is reported on every run, passing or failing, so the debt stays
# visible rather than being rediscovered by a contributor with a line counter.
# The ceiling is a property of the SKILL, not of this script. It is read from
# the skill under test — `core_max_lines:` in SKILL.md frontmatter, or a
# `.core-ceiling` file beside it holding the number. A skill that declares
# neither has not opted in: the count is reported and nothing is gated. This
# script ships inside task-observer but is run against every skill in a
# library, and a constant that describes one skill must never bound another.
CORE_CEILING_FILE = ".core-ceiling"
CORE_CEILING_KEY = "core_max_lines"
TARGET_CORE_LINES = 500
PATH_RE = re.compile(r"`((?:references|scripts|assets)/[^`\s*?]+\.[A-Za-z0-9]+)`")
BUILD_JUNK = {"__pycache__", ".DS_Store"}
# Edit residue: strings that only ever enter a file through a failed
# replacement, an unresolved template slot or an unfinished merge. The gate
# checks bundle FORM; this is the one CONTENT assertion, because a literal
# backreference passed apply, gate and install once.
SLOT_WHY = "unresolved template slot"
RESIDUE_RES = [
    (re.compile(r"(?m)^\\[0-9]\s*$"), "literal regex backreference on its own line"),
    (re.compile(r"(?<![\w`])\\[1-9](?![\w])"), "literal regex backreference in prose"),
    (re.compile(r"(?m)^(<<<<<<<|=======|>>>>>>>)( |$)"), "merge conflict marker"),
    (re.compile(r"\{\{[A-Za-z_][A-Za-z0-9_ .-]*\}\}"), SLOT_WHY),
    (re.compile(r"\b(TODO|FIXME|XXX)\b: ?(fill|replace|write)", re.I), "placeholder note left in"),
]
# A file that IS a template carries its slots as the deliverable, not as
# residue: exempt it from the SLOT rule only — every other residue rule and
# every other gate check still runs on it, so the exemption never becomes the
# hand-zip that also skips the checks nobody questioned.
TEMPLATE_MARKER = "<!-- template: slots intentional -->"


def slots_are_intentional(path, body):
    return "template" in str(path).lower() or body.lstrip().startswith(TEMPLATE_MARKER)
SECOND_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n\s*(---\n|name:|description:)", re.S)


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return m.group(1) if m else None


def folded_description(fm):
    """The description as the installer sees it, for both YAML block styles.

    Folded (`>`) joins its lines with spaces; literal (`|`) keeps the line
    breaks. Both accept a chomping indicator (`-`, `+`) and an explicit indent
    digit. Matching only `>` meant a `|` description fell through to the
    single-line branch below, which measured the string "|" — one character,
    inside every cap by construction, so the gate reported a pass having
    measured nothing at all. Any block style must be recognised here or the
    length check silently stops being a length check.
    """
    m = re.search(r"(?ms)^description:\s*([>|])[-+]?\d?\s*\n(.*?)(?=^\S|\Z)", fm)
    if m:
        body = m.group(2)
        if m.group(1) == ">":
            return " ".join(body.split())
        return "\n".join(line.strip() for line in body.strip("\n").splitlines())
    m = re.search(r"(?m)^description:\s*(.+)$", fm)
    return m.group(1).strip().strip('"\'') if m else ""


def check_frontmatter_shape(fm, fails, yaml_available):
    """Structural checks that do not need PyYAML.

    The gate's `frontmatter parses` item degrades to a regex when PyYAML is
    absent, and a regex happily accepts a block a YAML parser rejects. The
    case that got through: a cosmetic re-wrap turned a single-line
    `description:` into a key line followed by UNINDENTED continuation lines.
    The body loaded fine, so the defect surfaced only in the client's skill
    listing, where the description had been replaced by the H1 title.

    So: check the shape here, always, whichever branch ran above — and say
    which branch ran, because `OK` from the regex branch and `OK` from the
    parser branch are not the same assurance.
    """
    in_block = False
    for n, line in enumerate(fm.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if re.match(r"^[A-Za-z_][\w.-]*:", line):
            in_block = bool(re.search(r":\s*[>|][-+]?\d?\s*$", line))
            continue
        if line[:1].isspace() or line.lstrip().startswith("- "):
            continue          # indented continuation or list item: fine
        if in_block:
            # A block scalar's body must be indented. An unindented line ends
            # the block, and since it is not a `key:` line either, it is the
            # re-wrap defect.
            fails.append(
                f"frontmatter:{n}: unindented continuation line inside a block "
                f"scalar — YAML ends the block here and rejects the rest "
                f"({line.strip()[:60]!r})")
        else:
            fails.append(
                f"frontmatter:{n}: line is neither `key: value` nor an indented "
                f"continuation ({line.strip()[:60]!r})")
        in_block = False
    if not yaml_available:
        print("note: PyYAML not installed — frontmatter checked structurally, "
              "not parsed. Install PyYAML for the stronger check.")


def read_core_ceiling(skill_md):
    """The skill's own ceiling, or None if it has not declared one.

    Two sources, frontmatter first: `core_max_lines: N` in SKILL.md, else a
    `.core-ceiling` file beside it containing the number. None means the skill
    has not opted in — which is not a failure and must not be treated as one.
    A malformed value is also None, and says so, because silently falling back
    to some default is how one skill's number ends up bounding another.
    """
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"(?s)^---\n(.*?)\n---\n", text)
    if m:
        km = re.search(r"(?m)^%s:\s*(\S+)\s*$" % CORE_CEILING_KEY, m.group(1))
        if km:
            v = km.group(1).strip("\"'")   # a quoted number is still the number
            if v.isdigit():
                return int(v)
            print(f"note: {CORE_CEILING_KEY} is not a whole number "
                  f"({km.group(1)!r}) — core size not gated")
            return None
    f = skill_md.parent / CORE_CEILING_FILE
    if f.exists():
        raw = f.read_text(encoding="utf-8").strip()
        if raw.isdigit():
            return int(raw)
        print(f"note: {CORE_CEILING_FILE} is not a whole number ({raw!r}) — "
              f"core size not gated")
    return None


def check_core_size(skill_md, fails):
    """The ratchet, against the skill's OWN declared ceiling.

    Counted with splitlines() so the number matches `wc -l` on a
    newline-terminated file. Counting newlines and adding one reports 755 for
    a 754-line file, which is a one-line phantom in a check whose whole job is
    to compare a count to a bound.
    """
    lines = len(skill_md.read_text(encoding="utf-8").splitlines())
    over_target = lines - TARGET_CORE_LINES
    ceiling = read_core_ceiling(skill_md)
    if ceiling is None:
        note = f"core SKILL.md {lines} lines (no ceiling declared — not gated"
        if over_target > 0:
            note += f"; {over_target} over the {TARGET_CORE_LINES}-line target"
        print(note + ")")
        return
    if lines > ceiling:
        fails.append(
            f"core SKILL.md {lines} lines > this skill's declared ceiling "
            f"{ceiling}. Move content to a reference file — do not raise the "
            f"ceiling.")
    else:
        headroom = ceiling - lines
        note = f"core SKILL.md {lines} lines (ceiling {ceiling}, {headroom} to spare"
        if over_target > 0:
            note += f"; {over_target} over the {TARGET_CORE_LINES}-line target"
        print(note + ")")


def check_reference_indexes(skill_dir, fails):
    """Every heading in a reference file appears in that file's own Contents.

    The per-file `## Contents` index exists so a reader can see what the file
    covers without loading it, and so the core's pointers have something to
    resolve against. Nothing kept it current: an index is edited by hand, in a
    different part of the file from the section being added, and a stale one
    is indistinguishable from a complete one at a glance. Both misses this
    check caught were made while writing the rule that the index matters.

    Pointer targets are checked too — a core pointer naming a heading that
    does not exist sends the reader to a file to find nothing, which is worse
    than no pointer, because they stop looking.
    """
    def norm(s):
        return " ".join(s.split())

    def defence(text):
        """Blank fenced blocks, keeping line count, so a `##` inside a
        template (a summary skeleton, a principles entry, a registry stanza)
        is not mistaken for a section of the file. Every early failure this
        check reported was of exactly that kind."""
        return re.sub(r"(?ms)^```.*?^```[ \t]*$",
                      lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)

    refs = skill_dir / "references"
    if not refs.is_dir():
        return
    for p in sorted(refs.glob("*.md")):
        body = defence(p.read_text(encoding="utf-8"))
        m = re.search(r"(?ms)^## Contents\s*\n(.*?)(?=^## )", body)
        if not m:
            continue          # a file may legitimately have no index
        # Index entries wrap, and legitimately carry a parenthetical the
        # heading does not ("Lean Content (including progressive
        # disclosure…)"). So: join continuation lines into their entry, then
        # match a heading as a PREFIX of an entry, not by equality. Requiring
        # equality reported a correctly-indexed section as missing — the
        # check's own first finding was its own defect.
        entries, cur = [], None
        for line in m.group(1).splitlines():
            if re.match(r"^\s*-\s+", line):
                if cur is not None:
                    entries.append(norm(cur))
                cur = re.sub(r"^\s*-\s+", "", line)
            elif cur is not None and line.strip():
                cur += " " + line.strip()
        if cur is not None:
            entries.append(norm(cur))
        # Headings below the index, excluding the index itself
        after = body[m.end():]
        for h in re.findall(r"(?m)^#{2,3}\s+(.+?)\s*$", after):
            hn = norm(h)
            if not any(e == hn or e.startswith(hn + " ") or e.startswith(hn + "(")
                       for e in entries):
                fails.append(f"{p.name}: heading not in its own Contents index: {h!r}")

    core = (skill_dir / "SKILL.md").read_text(encoding="utf-8")

    # --- Reference shape: reported, never gated -----------------------------
    # The core's size ceiling does not transfer to reference files, because
    # their cost is conditional: a long file loaded once a month is cheap. The
    # signal that matters is how many DISTINCT episodes pull a file in, since
    # every one of them pays for the whole file. Measured once on this bundle,
    # the largest reference (1,105 lines) had a single trigger and was
    # correctly shaped, while a smaller one carried fourteen — so a size rule
    # would have flagged the healthy file and missed the mis-shaped one.
    #
    # Printed rather than enforced on purpose: one snapshot is not enough to
    # site a threshold, and the same measurement already overturned the rule
    # it was meant to support. Let a series accumulate, then decide.
    triggers = {}
    for m in re.finditer(r'`references/([a-z-]+\.md)`[^(]{0,40}\("([^"]+)"\)', core, re.S):
        triggers.setdefault(m.group(1), set()).add(norm(m.group(2)))
    if refs.is_dir():
        rows = []
        for p in sorted(refs.glob("*.md")):
            n = len(p.read_text(encoding="utf-8").splitlines())
            rows.append((p.name, n, len(triggers.get(p.name, ()))))
        worst = max((t for _, _, t in rows), default=0)
        print("reference shape (lines / distinct load triggers; not gated): "
              + ", ".join(f"{n}={ln}/{t}" for n, ln, t in rows))
        if worst >= 10:
            print(f"note: one reference file carries {worst} distinct load triggers — "
                  f"split by episode is indicated when this grows; size is not the signal")

    for m in re.finditer(r'`references/([a-z-]+\.md)`[^(]{0,40}\("([^"]+)"\)', core, re.S):
        fname, heading = m.group(1), norm(m.group(2))
        target = refs / fname
        if not target.is_file():
            fails.append(f"SKILL.md points at a reference that does not exist: {fname}")
            continue
        heads = {norm(x) for x in re.findall(r"(?m)^#{2,4}\s+(.+?)\s*$",
                                            defence(target.read_text(encoding="utf-8")))}
        if heading not in heads:
            fails.append(f"SKILL.md pointer has no target heading: {fname} -> {heading!r}")


def check_plugin_manifest(skill_dir, fails):
    """A skill bundle must NOT contain a plugin manifest.

    The uploader refuses it outright: *"A skill cannot contain a plugin
    manifest (…/.claude-plugin/plugin.json). Remove it, or upload this content
    as a plugin instead."* Skill and plugin are two upload kinds, not one
    artefact wearing both hats.

    This check was originally written the other way round, because the plugin
    reference documents a skills-directory plugin: a folder under a skills
    directory carrying this manifest loads as a plugin in place. That is true
    of a directory copied there by hand, and says nothing about what the
    uploader accepts — a distinction no amount of reading the plugin docs
    surfaces, because the constraint lives in the other product surface. The
    manifest is therefore repo-only, and `check_repo_versions` validates it
    there.

    The practical consequence, worth stating where someone will read it: a
    user who installs the `.skill` gets a skill, not a plugin. Only the
    repo-copy install path yields plugin behaviour.
    """
    manifest = skill_dir / ".claude-plugin" / "plugin.json"
    if manifest.is_file():
        fails.append(
            "a skill bundle must not contain .claude-plugin/plugin.json — the "
            "uploader rejects it ('upload this content as a plugin instead'). "
            "Keep the manifest at the repo root only; check_repo_versions "
            "validates it there.")


def check_dir(skill_dir, fails):
    # Resolve before comparing names: Path('.').name is '' for a relative
    # argument naming the current directory, which false-fails a correct
    # bundle and blames the frontmatter for an argument problem.
    skill_dir = pathlib.Path(skill_dir).resolve()
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        fails.append("SKILL.md missing"); return
    text = skill_md.read_text(encoding="utf-8")
    fm = frontmatter(text)
    if fm is None:
        fails.append("frontmatter: no leading --- block"); return
    # `yaml_available` is about the LIBRARY, not about this file parsing. A
    # parse failure is a defect in the file and is reported as one; only a
    # missing library downgrades the check, and only that case earns the note.
    yaml_available = True
    try:
        import yaml  # optional; fall back to regex checks if absent
        data = yaml.safe_load(fm)
        if not isinstance(data, dict):
            fails.append("frontmatter: does not parse to a mapping")
            data = {}
    except ImportError:
        yaml_available = False
        # Strip one layer of matching surrounding quotes: the template asks
        # for `name: "x"`, a real parser never sees the quote characters as
        # part of the value, and .strip() removes whitespace, not quotes —
        # so the hardened fallback failed the bundle it ships inside.
        raw = (re.search(r"(?m)^name:\s*(.+)$", fm) or [None, ""])[1].strip()
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
            raw = raw[1:-1]
        data = {"name": raw, "description": folded_description(fm)}
    except Exception as e:  # yaml error
        # Name the cause the check can detect, not the first field it then
        # fails to find: an unquoted `: ` inside a description is the common
        # way a whole block stops parsing, and "name missing" sends the
        # author to fix a field that is present.
        fails.append(
            f"frontmatter did not parse (likely an unquoted `: ` in a value — "
            f"double-quote the value or reword it): {e}")
        data = None
    name = str((data or {}).get("name") or "").strip()
    if data is None:
        pass  # already reported above; a missing-name report here would mislead
    elif not name:
        fails.append("frontmatter: `name` missing")
    elif not NAME_RE.match(name):
        fails.append(f"frontmatter: `name` not kebab-case: {name!r}")
    elif name != skill_dir.name:
        fails.append(f"frontmatter: `name` {name!r} != directory {skill_dir.name!r}")
    desc = folded_description(fm)
    if not desc:
        fails.append("frontmatter: `description` missing")
    elif len(desc) > MAX_DESCRIPTION_CHARS:
        fails.append(f"description {len(desc)} chars > cap {MAX_DESCRIPTION_CHARS}")
    elif len(desc) > 900:
        print(f"warn: description {len(desc)} chars (cap {MAX_DESCRIPTION_CHARS}) — near the boundary")
    # Every cited bundled path exists (backticked, real extension — globs in
    # prose are skipped). Ownership is inferred from the shape of the span, so
    # the convention has to make the two cases distinguishable: PATH_RE requires
    # the reserved prefix IMMEDIATELY after the backtick, which means a path
    # qualified with its owning skill's name — `<skill-name>/references/x.md` —
    # does not match and is exempt by construction. That qualified form is how a
    # skill cites a file belonging to a different skill; re-wording a legitimate
    # cross-reference so the backtick no longer starts with the prefix is not.
    # The failure message names the convention, because a false FAIL here is
    # otherwise indistinguishable from a genuinely missing file.
    for rel in sorted(set(PATH_RE.findall(text))):
        if not (skill_dir / rel).is_file():
            fails.append(
                f"cited path missing from staged set: {rel} "
                f"— if this file belongs to another skill, cite it as "
                f"`<skill-name>/{rel}`, which this check exempts")
    # exactly one frontmatter block: a second `---` block (or stray
    # name:/description: lines) directly after the first is a duplicated
    # header that every field check passes by construction
    if SECOND_FRONTMATTER_RE.match(text):
        fails.append("frontmatter: a second frontmatter block follows the first")
    check_frontmatter_shape(fm, fails, yaml_available)
    check_core_size(skill_md, fails)
    check_reference_indexes(skill_dir, fails)
    check_plugin_manifest(skill_dir, fails)
    for p in skill_dir.rglob("*"):
        if p.name in BUILD_JUNK or p.suffix == ".pyc" or p.name.startswith(".~lock"):
            fails.append(f"build artefact in staged tree: {p.relative_to(skill_dir)}")
        # content residue in every text file of the bundle, not only SKILL.md
        if p.is_file() and p.suffix.lower() in (".md", ".txt", ".yml", ".yaml", ".json"):
            body = p.read_text(encoding="utf-8", errors="replace")
            # code is where backreferences legitimately live: blank out
            # fenced blocks and inline spans, keeping line numbers intact
            prose = re.sub(r"(?ms)^```.*?^```[ \t]*$", lambda m: re.sub(r"[^\n]", " ", m.group(0)), body)
            prose = re.sub(r"`[^`\n]*`", lambda m: " " * len(m.group(0)), prose)
            rel = p.relative_to(skill_dir)
            exempt_slots = slots_are_intentional(rel, body)
            for rx, why in RESIDUE_RES:
                if why == SLOT_WHY and exempt_slots:
                    continue
                m = rx.search(prose)
                if m:
                    line = body.count("\n", 0, m.start()) + 1
                    fails.append(f"edit residue in {p.relative_to(skill_dir)}:{line}: {why} ({m.group(0).strip()!r})")


def check_repo_versions(repo_dir, fails):
    """Every manifest in the repo carries the same version as the skill's own.

    `.claude-plugin/plugin.json` is canonical — it is the one the installer
    reads, and it is the one that ships inside the skill bundle. Every other
    site is a copy, and a copy that drifts is worse than no copy: the
    installer's update check is keyed on the version, so a manifest left at
    the old number means `/plugin update` reports "already at the latest
    version" while serving stale files.

    Deliberately NOT a site: `marketplace.json` has no `version` field. The
    plugin's own manifest wins where both are set, so leaving it out removes
    a copy rather than synchronising one.
    """
    import json
    repo_dir = pathlib.Path(repo_dir)
    canonical_path = repo_dir / ".claude-plugin" / "plugin.json"
    if not canonical_path.is_file():
        fails.append("repo: .claude-plugin/plugin.json missing (the canonical version site)")
        return
    try:
        canonical = str(json.loads(canonical_path.read_text(encoding="utf-8")).get("version", "")).strip()
    except Exception as e:
        fails.append(f"repo: .claude-plugin/plugin.json does not parse: {e}")
        return
    if not SEMVER_RE.match(canonical):
        fails.append(f"repo: canonical version is not semver: {canonical!r}")
        return
    name = str(json.loads(canonical_path.read_text(encoding="utf-8")).get("name") or "").strip()
    if not NAME_RE.match(name):
        fails.append(f"repo: .claude-plugin/plugin.json `name` not kebab-case: {name!r}")
    if "description" in json.loads(canonical_path.read_text(encoding="utf-8")):
        fails.append(
            "repo: .claude-plugin/plugin.json carries `description`. Remove it — "
            "the skill's own frontmatter description drives invocation, and a "
            "second copy here is unread by the loader and drifts from the first.")
    print(f"repo: canonical version {canonical}")
    for rel in (".tessl-plugin/plugin.json",):
        p = repo_dir / rel
        if not p.is_file():
            continue
        try:
            v = str(json.loads(p.read_text(encoding="utf-8")).get("version", "")).strip()
        except Exception as e:
            fails.append(f"repo: {rel} does not parse: {e}")
            continue
        if v != canonical:
            fails.append(f"repo: {rel} version {v!r} != canonical {canonical!r}")
    # The skill's own frontmatter carries the version too, so a session can
    # name what it loaded without the repo-only manifest (which never ships
    # inside a bundle). It is a copy of the canonical number like the others.
    skill_md = repo_dir / "SKILL.md"
    if skill_md.is_file():
        fm = frontmatter(skill_md.read_text(encoding="utf-8")) or ""
        m = re.search(r'(?m)^version:\s*["\']?([^"\'\s]+)["\']?\s*$', fm)
        if not m:
            fails.append("repo: SKILL.md frontmatter has no `version:` (it must equal the canonical version)")
        elif m.group(1) != canonical:
            fails.append(f"repo: SKILL.md frontmatter version {m.group(1)!r} != canonical {canonical!r}")
    mp = repo_dir / ".claude-plugin" / "marketplace.json"
    if mp.is_file():
        try:
            data = json.loads(mp.read_text(encoding="utf-8"))
        except Exception as e:
            fails.append(f"repo: .claude-plugin/marketplace.json does not parse: {e}")
            data = {}
        stray = [k for k in ("version",) if k in data]
        stray += [f"plugins[{i}].version" for i, e in enumerate(data.get("plugins", []))
                  if isinstance(e, dict) and "version" in e]
        if stray:
            fails.append(
                f"repo: marketplace.json carries a version ({', '.join(stray)}). "
                f"Remove it — plugin.json wins where both are set, so this is a "
                f"copy to keep in sync for no benefit.")


LIST_ITEM_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+\S")


def check_markdown_shape(repo_dir, fails):
    """A stray blank line inside a tight list splits it in two when rendered.

    The skill checks never read repo-root prose, the confidentiality scan is
    a term search, and a diff review reads added lines — so an entry inserted
    into a README list by string replacement, which pushed the list's closing
    blank into the middle of it, passed all three and was caught by a human
    reading line numbers.

    The predicate: a blank line whose previous and next non-empty lines are
    list items at the same indent and of the same kind (bullet or numbered),
    where the list is otherwise TIGHT — one of those two items sits directly
    against another item with no blank between. Measured on seven repo roots
    before the tightness clause: 9 hits, 0 defects, all one deliberately
    loose list (every item blank-separated); with it: 0 hits, and the
    fixture's known defect still reported. Fenced blocks become opaque
    separator lines so code never reads as a list, and a run of blanks
    reports once, at its first line.
    """
    def kind(m):
        return (m.group(1), m.group(2)[0].isdigit()) if m else None

    repo_dir = pathlib.Path(repo_dir)
    for p in sorted(repo_dir.glob("*.md")):
        body = p.read_text(encoding="utf-8", errors="replace")
        prose = re.sub(r"(?ms)^```.*?^```[ \t]*$",
                       lambda m: re.sub(r"[^\n]+", "~", m.group(0)), body)
        lines = prose.splitlines()
        items = [kind(LIST_ITEM_RE.match(l)) for l in lines]
        for i, line in enumerate(lines):
            if line.strip() or (i and not lines[i - 1].strip()):
                continue
            prev = next((j for j in range(i - 1, -1, -1) if lines[j].strip()), None)
            nxt = next((j for j in range(i + 1, len(lines)) if lines[j].strip()), None)
            if prev is None or nxt is None or not items[prev] or items[prev] != items[nxt]:
                continue
            tight = (prev > 0 and items[prev - 1] == items[prev]) or \
                    (nxt + 1 < len(lines) and items[nxt + 1] == items[nxt])
            if tight:
                fails.append(f"{p.name}:{i + 1}: blank line splits a list in two "
                             f"(same-kind items at the same indent on both sides)")


def pack(src, out):
    """Always writes POSIX separators, on any platform."""
    src = pathlib.Path(src)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(p for p in src.rglob("*") if p.is_file()):
            arc = f"{src.name}/{f.relative_to(src).as_posix()}"
            assert "\\" not in arc, arc
            z.write(f, arcname=arc)


def check_bundle(path, fails):
    """Central directory as raw bytes: a convenience reader (zipfile.namelist)
    rewrites 0x5C to '/' and would report a malformed archive as clean."""
    data, i, n_members = pathlib.Path(path).read_bytes(), 0, 0
    while True:
        i = data.find(b"PK\x01\x02", i)
        if i < 0:
            break
        n, m, k = (struct.unpack_from("<H", data, i + o)[0] for o in (28, 30, 32))
        name = data[i + 46:i + 46 + n]
        n_members += 1
        if b"\x5c" in name:
            fails.append(f"bundle: backslash in member path {name!r} (installer rejects it)")
        # The uploader rejects a skill bundle carrying a plugin manifest. The
        # release workflow happens to copy three paths by name rather than the
        # whole tree, so it never picked this up — an accident, not a design.
        # Assert it here so the property holds however the bundle is built.
        if b".claude-plugin/" in name:
            fails.append(
                f"bundle: contains a plugin manifest ({name.decode(errors='replace')}) — "
                f"the uploader rejects a skill bundle that carries one")
        i += 46 + n + m + k
    if n_members == 0:
        fails.append("bundle: no members found")


def main(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    if "--repo-only" in argv:
        fails = []
        repo = argv[argv.index("--repo-only") + 1]
        check_repo_versions(repo, fails)
        check_markdown_shape(repo, fails)
        if fails:
            print("FAIL:")
            for f in fails:
                print("  -", f)
            return 1
        print("OK: repo manifest checks passed")
        return 0
    skill_dir = argv[1]
    bundle = pack_to = None
    if "--bundle" in argv:
        bundle = argv[argv.index("--bundle") + 1]
    if "--pack" in argv:
        pack_to = argv[argv.index("--pack") + 1]
    repo = argv[argv.index("--repo") + 1] if "--repo" in argv else None
    fails = []
    check_dir(skill_dir, fails)
    if repo:
        check_repo_versions(repo, fails)
    if pack_to and not fails:
        pack(skill_dir, pack_to); bundle = pack_to
        print(f"packed {pack_to}")
    if bundle:
        check_bundle(bundle, fails)
    if fails:
        print("FAIL:")
        for f in fails:
            print("  -", f)
        return 1
    print("OK: all gate checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
