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

  --pack   writes a well-formed bundle (POSIX separators on any platform)
           after the directory checks pass, then validates it.

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
PATH_RE = re.compile(r"`((?:references|scripts|assets)/[^`\s*?]+\.[A-Za-z0-9]+)`")
BUILD_JUNK = {"__pycache__", ".DS_Store"}


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return m.group(1) if m else None


def folded_description(fm):
    m = re.search(r"(?ms)^description:\s*>-?\s*\n(.*?)(?=^\S|\Z)", fm)
    if m:
        return " ".join(m.group(1).split())
    m = re.search(r"(?m)^description:\s*(.+)$", fm)
    return m.group(1).strip().strip('"\'') if m else ""


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
    try:
        import yaml  # optional; fall back to regex checks if absent
        data = yaml.safe_load(fm)
        if not isinstance(data, dict):
            fails.append("frontmatter: does not parse to a mapping")
            data = {}
    except ImportError:
        data = {"name": (re.search(r"(?m)^name:\s*(.+)$", fm) or [None, ""])[1].strip(),
                "description": folded_description(fm)}
    except Exception as e:  # yaml error
        fails.append(f"frontmatter: YAML parse error: {e}"); data = {}
    name = str(data.get("name") or "").strip()
    if not name:
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
    # every cited bundled path exists (backticked, real extension — globs in prose are skipped)
    for rel in sorted(set(PATH_RE.findall(text))):
        if not (skill_dir / rel).is_file():
            fails.append(f"cited path missing from staged set: {rel}")
    for p in skill_dir.rglob("*"):
        if p.name in BUILD_JUNK or p.suffix == ".pyc" or p.name.startswith(".~lock"):
            fails.append(f"build artefact in staged tree: {p.relative_to(skill_dir)}")


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
        i += 46 + n + m + k
    if n_members == 0:
        fails.append("bundle: no members found")


def main(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    skill_dir = argv[1]
    bundle = pack_to = None
    if "--bundle" in argv:
        bundle = argv[argv.index("--bundle") + 1]
    if "--pack" in argv:
        pack_to = argv[argv.index("--pack") + 1]
    fails = []
    check_dir(skill_dir, fails)
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
