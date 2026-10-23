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
  python3 validate-skill-bundle.py --selftest   # check fixtures and the scan script; exit 1 on any mismatch
  python3 validate-skill-bundle.py --compare-frontmatter <live/SKILL.md> <staged/SKILL.md>
  python3 validate-skill-bundle.py --help       # print this usage block; exit 0 (also -h)

  --compare-frontmatter  the reconciliation gate's installed-vs-staged
                compare: frontmatter by parsed value (installer quoting and
                folding ignored), body byte for byte. Exit 0 = equal, 1 = a
                real difference (named), 2 = unreadable input.

  --pack        writes a well-formed bundle (POSIX separators on any platform)
                after the directory checks pass, then validates it. An
                unquoted frontmatter `name:` is rewritten to the quoted form
                in the staged SKILL.md first, so the packed copy carries it.
                The written bundle must round-trip: its members are exactly
                the directory's files (build artefacts excluded), each equal
                byte for byte to what the packer wrote and to the file on
                disk; any mismatch fails the run (exit 1).
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
import tempfile
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
#
# The ceiling also FOLLOWS the core down. A check that only blocks growth
# leaves every trim as open headroom, and the next ordinary additions spend it
# without anyone deciding to. So a declared ceiling more than
# CEILING_SLACK_TOLERANCE lines above the core fails too; the fix is to lower
# the declared number to the current count in the same commit as the trim.
CORE_CEILING_FILE = ".core-ceiling"
CORE_CEILING_KEY = "core_max_lines"
CEILING_SLACK_TOLERANCE = 3
TARGET_CORE_LINES = 500
PATH_RE = re.compile(r"`((?:references|scripts|assets)/[^`\s*?]+\.[A-Za-z0-9]+)`")
# A path the agent EXECUTES rarely fills a whole backtick span: it sits after
# an interpreter, with arguments behind it, inline or in a fenced block, and
# PATH_RE never extracts it. So code is also split into commands, and an
# unqualified bundled path counts when the token before it is an interpreter.
# A bare path with no interpreter stays unchecked, which keeps a quoted
# example (`scripts/x/generate.py --logo ...`) out. Measured over 127 local
# skills: 28 hits, 0 missing, no normalisation needed.
CMD_PATH_RE = re.compile(r"(?:references|scripts|assets)/[^\s`'\"*?<>;|&]+\.[A-Za-z0-9]+")
CMD_INTERP = {"python3", "python", "py", "bash", "sh", "zsh", "node", "swift", "ruby", "perl", "run", "source"}
# A placeholder segment in a cited path — `<study>` or `{study}`, never
# spanning a `/` — marks a naming pattern, checked as a glob (check_dir).
SLOT_SEG_RE = re.compile(r"<[^<>/\s]+>|\{[^{}/\s]+\}")
# An interpreter's own options sit between it and the script: `py -3 x.py`
# (the Windows launcher, which migration.md recommends where `python3` is the
# Store alias), `python3 -X utf8 x.py`, `bash -eu x.sh`. Reading only the
# token right after the interpreter missed every one. Per family: options
# that take no value, options whose value is the next token, and options
# after which the next token is not a script at all (`-m`, `-c`), so nothing
# is checked. Other interpreters keep the token-right-after rule: their
# option grammars are not tabled here.
CMD_OPTS = {
    "python": (re.compile(r"-[bBdEiIOPqRsSuvx]+|-[0-9]+(\.[0-9]+)?(-(32|64))?|-[XW]\S+"),
               {"-X", "-W"}, re.compile(r"-[bBdEiIOPqRsSuvx]*[mc]\S*|-")),
    "shell": (re.compile(r"[-+][aefhiklnpuvxBCEHPT]+|--(norc|noprofile|login|posix|verbose|noediting|restricted)"),
              {"-o", "+o", "-O", "+O", "--rcfile", "--init-file"}, re.compile(r"-[a-zA-Z]*c[a-zA-Z]*|-s|-")),
}
CMD_FAMILY = {"python3": "python", "python": "python", "py": "python", "bash": "shell", "sh": "shell", "zsh": "shell"}
BUILD_JUNK = {"__pycache__", ".DS_Store"}
# Version-control metadata: a live skill can be a clone, a staged copy must
# not be. The other checks ask what is MISSING; this one asks what is there
# that should not be (a clone packed its whole history and passed).
VCS_DIRS = {".git", ".hg", ".svn"}
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
# The first block ends at its FIRST closing `---` line; the lookahead stops
# `.*?` from running on to a later pair of horizontal rules in the body.
SECOND_FRONTMATTER_RE = re.compile(r"^---\n(?:(?!\n---\n).)*?\n---\n\s*(---\n|name:|description:)", re.S)


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


def fallback_name(fm):
    """`name` as a YAML parser reads it, for the no-PyYAML branch.

    One layer of matching quotes is not part of the value (the template asks
    for `name: "x"`), and neither is a trailing comment: PyYAML ends the
    value at `#` after a closing quote, and at ` #` after a plain scalar.
    Stripping quotes only when the line ENDS in the quote left
    `name: 'x' # c` failing here while the parser passed it. A tab
    before `#` is a scanner error to PyYAML, so it is left in and fails too.
    """
    raw = (re.search(r"(?m)^name:\s*(.+)$", fm) or [None, ""])[1].strip()
    m = re.match(r"""^(["'])([^"'\\]*)\1 *(?:#.*)?$""", raw)
    return m.group(2) if m else re.sub(r" +#.*$", "", raw)


# (frontmatter `name:` value, kebab verdict the fallback must give) — each
# pins the fallback to what PyYAML returns for the same line.
FALLBACK_NAME_FIXTURES = [
    ("x", True), ('"x"', True), ("'x'", True),
    ("'x' # c", True), ('"x" # c', True), ("x # c", True), ("'x'#c", True),
    ("x#c", False), ("'a #b' # c", False), ("x\t# c", False), ("'x'y", False),
]


# --- Installed-vs-staged frontmatter comparison ------------------------------
# The installer rewrites the frontmatter it writes back: it quotes or unquotes
# `name:`, re-quotes `version: 1.5.0` as `version: '1.5.0'`, and turns a folded
# `description: >` block into one double-quoted line. A text diff reports every
# such copy as differing, and a normaliser that covers only some of those
# rewrites turns the rest into routine false alarms — which train the reader
# to wave real differences through. So the comparison is by PARSED VALUE: both
# headers are parsed with every scalar kept as a string (PyYAML's BaseLoader,
# so `1.5.0` and '1.5.0' are the same value and nothing is type-coerced), the
# trailing newline a block scalar carries is stripped, and the body after the
# closing `---` is compared byte for byte. Without PyYAML the fallback below
# reads top-level keys only and says so.

def split_skill_md(text):
    """(frontmatter text, body after the closing `---` line), or (None, text)."""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return (m.group(1), text[m.end():]) if m else (None, text)


def _unquote(raw):
    """One YAML flow scalar as the parser returns it: quotes and escapes
    resolved, a trailing comment dropped from a plain scalar."""
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] == '"':
        return re.sub(r'\\(["\\n/])', lambda m: "\n" if m.group(1) == "n" else m.group(1), raw[1:-1])
    if len(raw) >= 2 and raw[0] == raw[-1] == "'":
        return raw[1:-1].replace("''", "'")
    return re.sub(r"[ \t]+#.*$", "", raw)


def fallback_fields(fm):
    """Top-level keys of a frontmatter block without PyYAML: flow scalars via
    _unquote(), a quoted value continued over several lines folded with
    spaces, block scalars (`>`, `|`) via folded_description()'s rules, and a
    nested block (indented lines under an empty value) kept as its
    whitespace-normalised text. A floor, not a parser: it reads the shapes the
    installer writes and the template asks for."""
    out, key, buf = {}, None, []

    def close():
        if key is None:
            return
        first, rest = buf[0], buf[1:]
        if re.match(r"^[>|][-+]?\d?\s*$", first):
            out[key] = folded_description("description: " + "\n".join([first] + rest))
        elif first[:1] in ('"', "'") and rest:
            out[key] = _unquote(" ".join([first] + [r.strip() for r in rest]))
        elif not first and rest:
            out[key] = " ".join(" ".join(rest).split())
        else:
            out[key] = _unquote(first)

    for line in fm.splitlines():
        m = re.match(r"^([A-Za-z_][\w.-]*):(?:[ \t]+(.*))?$", line)
        if m:
            close()
            key, buf = m.group(1), [(m.group(2) or "").strip()]
        elif key is not None:
            buf.append(line)
    close()
    return out


def parse_frontmatter_values(fm, use_yaml=True):
    """(dict of top-level key -> value, parser label). Strings lose the
    trailing newline(s) a block scalar or an installer's `\\n` carries."""
    data, how = None, "fallback (no PyYAML: top-level keys only)"
    if use_yaml:
        try:
            import yaml
            data = yaml.load(fm, Loader=yaml.BaseLoader)
            how = "PyYAML BaseLoader"
        except ImportError:
            pass
    if data is None:
        data = fallback_fields(fm)
    if not isinstance(data, dict):
        raise ValueError("frontmatter does not parse to a mapping")
    return {k: (v.rstrip("\n") if isinstance(v, str) else v) for k, v in data.items()}, how


def compare_frontmatter_texts(a, b, use_yaml=True):
    """Compare two SKILL.md texts the way the reconciliation gate needs:
    returns (differing frontmatter keys, body equal?, parser label)."""
    (fa, ba), (fb, bb) = split_skill_md(a), split_skill_md(b)
    if fa is None or fb is None:
        raise ValueError("no leading --- frontmatter block")
    va, how = parse_frontmatter_values(fa, use_yaml)
    vb, _ = parse_frontmatter_values(fb, use_yaml)
    keys = sorted(k for k in set(va) | set(vb) if va.get(k) != vb.get(k))
    return keys, ba == bb, how


def compare_frontmatter_main(path_a, path_b):
    """--compare-frontmatter A B: exit 0 = same skill text (installer quoting
    aside), 1 = a real difference (each one named), 2 = unreadable input."""
    try:
        ta = pathlib.Path(path_a).read_text(encoding="utf-8")
        tb = pathlib.Path(path_b).read_text(encoding="utf-8")
        keys, body_equal, how = compare_frontmatter_texts(ta, tb)
    except (OSError, ValueError, UnicodeDecodeError) as e:
        print(f"compare: cannot compare: {e}"); return 2
    except Exception as e:   # a YAML error: the file is broken, say so
        print(f"compare: frontmatter did not parse: {e}"); return 2
    print(f"parser: {how}")
    print("frontmatter: equal by value" if not keys
          else "frontmatter: DIFFERS in " + ", ".join(keys))
    if body_equal:
        print("body: equal byte for byte")
    else:
        la = split_skill_md(ta)[1].splitlines()
        lb = split_skill_md(tb)[1].splitlines()
        n = next((i for i, (x, y) in enumerate(zip(la, lb)) if x != y), min(len(la), len(lb)))
        print(f"body: DIFFERS (first at body line {n + 1}; {len(la)} vs {len(lb)} lines)")
    return 0 if not keys and body_equal else 1


_FOLDED = ("---\nname: x\ndescription: >\n  One two: three,\n  four.\n---\nbody\n")
# (name, text A, text B, frontmatter keys that must differ, body must be equal)
COMPARE_FM_FIXTURES = [
    ("quoted vs unquoted name", '---\nname: "x"\n---\nbody\n', "---\nname: x\n---\nbody\n", [], True),
    ("version '1.5.0' vs 1.5.0", "---\nname: x\nversion: '1.5.0'\n---\nb\n",
     "---\nname: x\nversion: 1.5.0\n---\nb\n", [], True),
    ("folded description vs one-line quoted string, same text", _FOLDED,
     '---\nname: "x"\ndescription: "One two: three, four.\\n"\n---\nbody\n', [], True),
    ("a real value change is still reported", "---\nname: x\nversion: 1.5.0\n---\nb\n",
     "---\nname: x\nversion: '1.6.0'\n---\nb\n", ["version"], True),
    ("a body change is still reported", '---\nname: "x"\n---\nbody\n', "---\nname: x\n---\nbody2\n", [], False),
]


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
    target_note = (f" ({over_target} over the {TARGET_CORE_LINES}-line target)"
                   if over_target > 0 else "")
    ceiling = read_core_ceiling(skill_md)
    if ceiling is None:
        print(f"core {lines} / ceiling none / slack n/a — not gated{target_note}")
        return
    slack = ceiling - lines
    print(f"core {lines} / ceiling {ceiling} / slack {slack}{target_note}")
    if lines > ceiling:
        fails.append(
            f"core SKILL.md {lines} lines > this skill's declared ceiling "
            f"{ceiling}. Move content to a reference file — do not raise the "
            f"ceiling.")
    elif slack > CEILING_SLACK_TOLERANCE:
        fails.append(
            f"core SKILL.md {lines} lines, declared ceiling {ceiling}: slack "
            f"{slack} > tolerance {CEILING_SLACK_TOLERANCE}. Lower "
            f"{CORE_CEILING_KEY} (or {CORE_CEILING_FILE}) to {lines} in this "
            f"commit — a trim is locked in, not left as headroom.")


def _norm(s):
    return " ".join(s.split())


def _index_entries(body):
    """(match, entry groups) of a file's `## Contents` index, or (None, []).

    The index ends at the next `## ` heading, or — in a file whose entries
    are all `###` (a numbered principles list) — at the first `###` entry, a
    horizontal rule, or the end of the file. Bounding it by `## ` alone
    matched nothing in such a file, so the check skipped exactly the index
    that changes most often, and a numbered entry shipped with no Contents
    line. Within that span the ENTRIES end at the first paragraph — a
    non-blank line that neither opens a list item nor is indented under one
    — because a preamble between the index and the first section is prose,
    and reading its lines as entries let a later list in that preamble
    stand in for headings nothing indexed. Each group holds one entry's
    forms: the text, and for a numbered item the text with its marker.
    """
    def plain(s):
        # An entry written as an anchor link, `[Alpha](#alpha)`, is the
        # other common way to write an index; reading the brackets as text
        # failed every heading of a correct index, so the link is reduced
        # to its text before matching.
        return _norm(re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s))

    m = re.search(r"(?ms)^## Contents[ \t]*\n(.*?)(?=^## |^### |^-{3,}[ \t]*$|\Z)", body)
    if not m:
        return None, []       # a file may legitimately have no index
    # Index entries wrap, and legitimately carry a parenthetical the
    # heading does not ("Lean Content (including progressive
    # disclosure…)"). So: join continuation lines into their entry, then
    # match a heading as a PREFIX of an entry, not by equality. Requiring
    # equality reported a correctly-indexed section as missing — the
    # check's own first finding was its own defect.
    groups, cur, num = [], None, ""
    # A bullet is `-`, `*` or `+`: all three are Markdown lists, and an
    # index written with `*` otherwise had no entries at all. A numbered
    # list (`1. Alpha`, `1) Alpha`) is a list too; its entry is kept both
    # whole and without the marker, so it indexes `## 1. Alpha` and
    # `## Alpha` alike — reading it as no entry reported every heading
    # of a correct numbered index as missing.
    def flush():
        groups.append([plain(cur)] + ([plain(num + cur)] if num else []))
    for line in m.group(1).splitlines():
        mk = re.match(r"^\s*([-*+]|\d+[.)])\s+", line)
        if mk:
            if cur is not None:
                flush()
            cur = line[mk.end():]
            num = mk.group(1) + " " if mk.group(1)[0].isdigit() else ""
        elif cur is not None and line.strip():
            if not line[0].isspace():
                break         # a paragraph: the entries are over
            cur += " " + line.strip()
    if cur is not None:
        flush()
    return m, groups


def _entry_covers(entry, anchor):
    return entry == anchor or entry.startswith(anchor + " ") or entry.startswith(anchor + "(")


def index_misses(body):
    """Headings below a file's `## Contents` index that the index lacks.

    Every `##`/`###` heading after the index, numbered `### N.` entries
    included, must have its line (`_index_entries` says where the index
    ends and how an entry is read).
    """
    m, groups = _index_entries(body)
    if not m:
        return []
    entries = [e for g in groups for e in g]
    missing = []
    for h in re.findall(r"(?m)^#{2,3}\s+(.+?)\s*$", body[m.end():]):
        hn = _norm(h)
        if not any(_entry_covers(e, hn) for e in entries):
            missing.append(h)
    return missing


def index_orphans(body):
    """Index entries that resolve to no anchor in the same file — the
    reverse of `index_misses`. The forward pass certifies a stale index: an
    entry whose heading was renamed or deleted passes it, and a stale index
    is exactly what a trim or a relocation leaves behind. An anchor is a
    `##`–`####` heading below the index, or a bold lead opening a paragraph
    (`**Step 1 — load.**`, its closing `.` or `:` dropped) — an index
    legitimately lists the steps of a procedure written that way. A lead
    is a sentence where a heading is a title, so an entry may name a lead
    by its opening clause (`Step 2 — inventory skills` for a lead that
    goes on to say how). Measured before those rules: every hit on the
    bundle was one of the three shapes, and none was a defect.
    """
    m, groups = _index_entries(body)
    if not m:
        return []
    below = body[m.end():]
    heads = {_norm(h) for h in re.findall(r"(?m)^#{2,4}\s+(.+?)\s*$", below)}
    leads = {_norm(h).rstrip(".:") for h in re.findall(r"(?ms)^\*\*(.+?)\*\*", below)}   # a lead wraps
    return [g[0] for g in groups
            if not any(_entry_covers(e, a) for e in g for a in heads)
            and not any(_entry_covers(e, a) or a.startswith(e + " ") for e in g for a in leads)]


# (name, reference-file text, headings index_misses must report)
INDEX_FIXTURES = [
    ("###-only file with every entry indexed passes",
     "# T\n\n## Contents\n\n- 1. One\n- 2. Two\n\n---\n\n### 1. One\ntext\n\n### 2. Two\ntext\n", []),
    ("###-only file missing one Contents line fails",
     "# T\n\n## Contents\n\n- 1. One\n\n### 1. One\ntext\n\n### 2. Two\ntext\n", ["2. Two"]),
    ("## sections still bound the index",
     "# T\n\n## Contents\n\n- A\n\n## A\n\n### Sub\n", ["Sub"]),
    ("anchor-link entries match their headings",
     "# R\n\n## Contents\n\n- [Alpha](#alpha)\n- [Beta two](#beta-two) — what it covers\n\n## Alpha\n\ntext\n\n## Beta two\n\ntext\n", []),
    ("anchor-link index missing one heading still fails",
     "# R\n\n## Contents\n\n- [Alpha](#alpha)\n\n## Alpha\n\n## Beta\n", ["Beta"]),
    ("`*` bullets are entries too",
     "# R\n\n## Contents\n\n* [Alpha](#alpha)\n* Beta\n\n## Alpha\n\n## Beta\n", []),
    ("a numbered list indexes numbered headings",
     "# R\n\n## Contents\n\n1. Alpha\n2. Beta\n\n## 1. Alpha\n\n## 2. Beta\n", []),
    ("a numbered list indexes unnumbered headings too",
     "# R\n\n## Contents\n\n1. Alpha\n2) Beta two\n\n## Alpha\n\n## Beta two\n\n## Gamma\n", ["Gamma"]),
    ("a preamble paragraph ends the entries; a list inside it is not the index",
     "# R\n\n## Contents\n\n- Alpha\n\nPreamble prose.\n\n- Not an entry\n\n## Alpha\n\n## Beta\n", ["Beta"]),
]

# (name, reference-file text, entries index_orphans must report): the
# reverse pass — every entry resolves to a heading or a bold lead.
ORPHAN_FIXTURES = [
    ("every entry has its heading: nothing reported",
     "# R\n\n## Contents\n\n- Alpha\n- Beta two — what it covers\n\n## Alpha\n\n## Beta two\n", []),
    ("an entry whose heading was deleted is an orphan",
     "# R\n\n## Contents\n\n- Alpha\n- Beta\n\n## Alpha\n", ["Beta"]),
    ("an entry whose heading was renamed is an orphan",
     "# R\n\n## Contents\n\n- [Alpha](#alpha)\n\n## Alpha one\n", ["Alpha"]),
    ("a bold lead with its closing period anchors a step entry",
     "# R\n\n## Contents\n\n- Steps\n  - Step 1 — load\n\n## Steps\n\n**Step 1 — load.** Text.\n", []),
    ("an entry naming a lead's opening clause passes; a heading's prefix does not",
     "# R\n\n## Contents\n\n- Steps\n  - Step 2 — inventory\n- Alpha\n\n## Steps\n\n"
     "**Step 2 — inventory skills,\nby survival.** Text.\n\n## Alpha one\n", ["Alpha"]),
    ("a #### heading anchors an entry",
     "# R\n\n## Contents\n\n- Alpha\n- Deep\n\n## Alpha\n\n#### Deep\n", []),
    ("a numbered entry resolves through either of its forms",
     "# R\n\n## Contents\n\n1. Alpha\n2. Beta\n\n## 1. Alpha\n\n## Beta\n", []),
    ("a list in the preamble is not read as entries",
     "# R\n\n## Contents\n\n- Alpha\n\nPreamble prose.\n\n- Not an entry\n\n## Alpha\n", []),
]


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
        return blank_fenced_code(text)

    refs = skill_dir / "references"
    if not refs.is_dir():
        return
    for p in sorted(refs.glob("*.md")):
        text = defence(p.read_text(encoding="utf-8"))
        for h in index_misses(text):
            fails.append(f"{p.name}: heading not in its own Contents index: {h!r}")
        for e in index_orphans(text):
            fails.append(f"{p.name}: index entry without a heading: {e!r}")

    core = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    check_reference_shape(skill_dir, core, fails)

    # Both pointer forms name a target: `references/x.md` ("Heading") and
    # (`references/x.md`, "Heading"). The second form was invisible to this
    # check, so its targets went unverified. A pointer may name a heading up
    # to its ` — ` qualifier, as a Contents entry may.
    named, _ = core_pointers(core)
    for fname in sorted(named):
        target = refs / fname
        if not target.is_file():
            fails.append(f"SKILL.md points at a reference that does not exist: {fname}")
            continue
        heads = {norm(x) for x in re.findall(r"(?m)^#{2,4}\s+(.+?)\s*$",
                                            defence(target.read_text(encoding="utf-8")))}
        for heading in sorted(named[fname]):
            if not any(h == heading or h.startswith(heading + " — ") for h in heads):
                fails.append(f"SKILL.md pointer has no target heading: {fname} -> {heading!r}")


# --- Reference-file growth barrier ---------------------------------------------
# The core's ceiling does not transfer to reference files as a size rule,
# because their cost is conditional: a long file loaded once a month is cheap,
# and the signal that matters is how many DISTINCT episodes pull a file in,
# since every one of them pays for the whole file. Measured on this bundle,
# the largest reference had a single trigger and was correctly shaped while a
# smaller one carried many — a size rule alone flags the healthy file and
# misses the mis-shaped one. The figures are whatever the `reference shape`
# line prints on this run; never copy them into this comment.
#
# What a ceiling CAN do is stop silent growth, so the barrier combines the
# two: every reference file of a skill that opts in carries a line ceiling,
# and exceeding it fails and forces a decision whose remedy is chosen by the
# file's load-trigger count —
#   * more than SPLIT_TRIGGER_THRESHOLD triggers: split by episode;
#   * that many or fewer: trim, or raise the ceiling with a dated one-line
#     reason written beside the number.
# Size alone never forces a split, so a single-episode file is never split to
# meet a size rule. The ceiling follows trims down with the core's tolerance.
#
# Opt-in, per skill: a `references/ceilings.txt` file holds one line per file —
#   <file.md> <ceiling> [<YYYY-MM-DD> <reason for the last raise>]
# with `#` comments and blank lines allowed. Not a dotfile: an install route
# that drops dotfiles would silently switch the gate off. A skill without one
# has not opted in: the shape line is printed and nothing is gated, so the public validator
# imposes no budget on a skill whose author never set one.
#
# The trigger count is DECLARED, not inferred: each reference carries one
# `Load triggers: a; b; c` line in its header (before its first `## `
# heading), and the count is the number of distinct entries. Pointer scanning
# cannot be exact — one episode can be cited from several places, and a
# filename-only pointer names no section at all — so the scan is kept only as
# the fallback figure for a file that declares nothing (printed with `~`) and
# as a cross-check that a declaration has not fallen behind the core.
REF_CEILINGS_FILE = "ceilings.txt"
SPLIT_TRIGGER_THRESHOLD = 12
LOAD_TRIGGERS_RE = re.compile(r"(?m)^Load triggers:[ \t]*(.*?)[ \t]*$")
REF_CEILING_LINE_RE = re.compile(
    r"^(?P<file>[^\s/]+\.md)[ \t]+(?P<ceiling>\d+)"
    r"(?:[ \t]+(?P<date>\d{4}-\d{2}-\d{2})[ \t]+(?P<reason>\S.*?))?[ \t]*$")
# `references/x.md` ("Heading") — up to 40 characters between, newlines
# included, no backtick — and the parenthesised (`references/x.md`, "Heading").
REF_POINTER_RE = re.compile(r'`references/([a-z0-9-]+\.md)`(?:[^(`]{0,40}\(|,\s*)"([^"]+)"')
REF_ANY_POINTER_RE = re.compile(r"`references/([a-z0-9-]+\.md)`")


def core_pointers(core):
    """({file: {section names}}, {file: number of filename-only pointers}).

    Frontmatter is skipped. Filename-only pointers are counted once per
    paragraph or list item, so a sentence that cites a file twice is one
    pointer, not two."""
    m = re.match(r"(?s)^---\n.*?\n---\n", core)
    body = core[m.end():] if m else core
    named, named_at = {}, set()
    for pm in REF_POINTER_RE.finditer(body):
        named.setdefault(pm.group(1), set()).add(" ".join(pm.group(2).split()))
        named_at.add(pm.start())
    # block index for each line: a blank line or a list-item start opens one
    block, starts = 0, []
    for line in body.splitlines(True):
        if not line.strip() or re.match(r"^\s*(?:[-*]|\d+\.)\s", line):
            block += 1
        starts.append(block)
    offsets = [0]
    for line in body.splitlines(True):
        offsets.append(offsets[-1] + len(line))
    unnamed = {}
    for pm in REF_ANY_POINTER_RE.finditer(body):
        if pm.start() in named_at:
            continue
        ln = body.count("\n", 0, pm.start())
        unnamed.setdefault(pm.group(1), set()).add(starts[ln] if ln < len(starts) else -1)
    return named, {f: len(b) for f, b in unnamed.items()}


def declared_load_triggers(text):
    """The distinct entries of the header's `Load triggers:` line, or None."""
    head = re.split(r"(?m)^## ", text, maxsplit=1)[0]
    m = LOAD_TRIGGERS_RE.search(head)
    if not m:
        return None
    seen = []
    for t in m.group(1).split(";"):
        t = " ".join(t.split())
        if t and t.lower() not in (s.lower() for s in seen):
            seen.append(t)
    return seen


def read_ref_ceilings(refs, fails):
    """{file: (ceiling, date, reason)} from references/ceilings.txt, or None when
    the skill has not opted in. Every malformed line fails: a skill that
    opted in and wrote a line the gate cannot read must not pass ungated."""
    import datetime
    f = refs / REF_CEILINGS_FILE
    if not f.is_file():
        return None
    out = {}
    for i, raw in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = REF_CEILING_LINE_RE.match(line)
        where = f"references/{REF_CEILINGS_FILE}:{i}"
        if not m:
            fails.append(f"{where}: unreadable line {line!r} — the form is "
                         f"`<file.md> <lines> [<YYYY-MM-DD> <reason>]`; a raise "
                         f"carries both a date and a reason")
            continue
        date = m.group("date")
        if date:
            try:
                datetime.date.fromisoformat(date)
            except ValueError:
                fails.append(f"{where}: {date!r} is not a calendar date")
        name = m.group("file")
        if name in out:
            fails.append(f"{where}: {name} has a second ceiling line")
            continue
        out[name] = (int(m.group("ceiling")), date, m.group("reason"))
    return out


def check_reference_shape(skill_dir, core, fails):
    """Print the `reference shape` line; gate it when the skill opted in."""
    refs = pathlib.Path(skill_dir) / "references"
    if not refs.is_dir():
        return
    named, unnamed = core_pointers(core)
    ceilings = read_ref_ceilings(refs, fails)
    N, tol = SPLIT_TRIGGER_THRESHOLD, CEILING_SLACK_TOLERANCE
    rows = []
    for p in sorted(refs.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        lines = len(text.splitlines())
        declared = declared_load_triggers(text)
        scanned = len(named.get(p.name, ())) + unnamed.get(p.name, 0)
        rows.append((p.name, lines, declared, scanned))
    shown = []
    for name, lines, declared, scanned in rows:
        c = ceilings.get(name) if ceilings is not None else None
        t = str(len(declared)) if declared is not None else f"~{scanned}"
        shown.append(f"{name}={lines}/{c[0] if c else '-'}/{t}")
    gated = ("ceilings in references/" + REF_CEILINGS_FILE if ceilings is not None
             else "no references/" + REF_CEILINGS_FILE + " — not gated")
    print(f"reference shape (lines / ceiling / load triggers declared in the header, "
          f"~ = scanned from the core, none declared; split by episode above {N}; {gated}): "
          + ", ".join(shown))
    for name, lines, declared, scanned in rows:
        sections = len(named.get(name, ()))
        if declared is not None and sections > len(declared):
            print(f"note: the core names {sections} distinct sections of {name} but its "
                  f"header declares {len(declared)} load triggers — bring its "
                  f"`Load triggers:` line up to date")
        if declared is not None and len(declared) > N:
            print(f"note: {name} declares {len(declared)} load triggers (> {N}) — split "
                  f"by episode is indicated"
                  + (" once it outgrows its ceiling" if ceilings is not None
                     else "; size is not the signal"))
    if ceilings is None:
        return
    present = {name for name, *_ in rows}
    for name in sorted(set(ceilings) - present):
        fails.append(f"references/{REF_CEILINGS_FILE} names {name}, which is not in "
                     f"references/ — remove its line, or lower it with the file it moved to")
    for name, lines, declared, _ in rows:
        if name not in ceilings:
            fails.append(f"references/{name} has no ceiling: this skill opted in with "
                         f"references/{REF_CEILINGS_FILE}, so add `{name} {lines}` there")
            continue
        ceiling, date, reason = ceilings[name]
        if declared is None:
            fails.append(f"references/{name} declares no load triggers: add one "
                         f"`Load triggers: a; b; c` line to its header (before the first "
                         f"`## ` heading), one entry per distinct episode that loads it")
            continue
        n = len(declared)
        if lines > ceiling and n > N:
            fails.append(
                f"references/{name} {lines} lines > ceiling {ceiling}, with {n} load "
                f"triggers (> {N}): split it by episode, so each trigger loads only "
                f"its own part — a raise is not the remedy for a file this many "
                f"episodes pull in")
        elif lines > ceiling:
            fails.append(
                f"references/{name} {lines} lines > ceiling {ceiling}, with {n} load "
                f"trigger(s) (<= {N}): trim it back to {ceiling} lines or fewer, or raise the "
                f"ceiling in references/{REF_CEILINGS_FILE} to {lines} with a dated "
                f"one-line reason beside the number (`{name} {lines} YYYY-MM-DD why`)")
        elif ceiling - lines > tol:
            fails.append(
                f"references/{name} {lines} lines, ceiling {ceiling}: slack "
                f"{ceiling - lines} > tolerance {tol}. Lower its line in "
                f"references/{REF_CEILINGS_FILE} to {lines} in this commit — a trim "
                f"is locked in, not left as headroom")
        if reason and n > N:
            fails.append(
                f"references/{name} carries a raised ceiling ({date}: {reason}) but "
                f"declares {n} load triggers (> {N}): with that many episodes the "
                f"remedy is a split by episode, not a raise")


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
        data = {"name": fallback_name(fm), "description": folded_description(fm)}
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
    # A space before `#` starts a YAML comment, so a plain (unquoted) value
    # ends there and the block still parses: the raw line reads whole, the
    # installer gets a shorter value, and no parse check can see it.
    line = (re.search(r"(?m)^description:[ \t]*(.*)$", fm) or [None, ""])[1]
    if line[:1] not in ("", '"', "'", ">", "|") and re.search(r"[ \t]#", line):
        fails.append(
            "frontmatter: unquoted `description` contains ` #`, which starts a "
            "YAML comment and cuts the value there — double-quote the value")
    parsed = (data or {}).get("description")
    if yaml_available and isinstance(parsed, str):
        desc = parsed.strip()       # measure what the installer's parser returns
    if not desc:
        fails.append("frontmatter: `description` missing")
    elif len(desc) > MAX_DESCRIPTION_CHARS:
        fails.append(f"description {len(desc)} chars > cap {MAX_DESCRIPTION_CHARS}")
    elif len(desc) > 900:
        print(f"warn: description {len(desc)} chars (cap {MAX_DESCRIPTION_CHARS}) — near the boundary")
    for ln, tok in template_tokens(text):
        print(f"warn: SKILL.md:{ln}: {tok!r} is rewritten when the skill is invoked with "
              f"arguments — write an awk field as `$ 2`, or move the text to a reference or script")
    # Every cited bundled path exists (backticked, real extension — globs in
    # prose are skipped, and a naming pattern with a `<slot>` or `{slot}`
    # segment is matched as a glob against the staged set, not looked up:
    # `references/studies/<study>.md` documents a family of files, and it
    # passes when at least one staged file fits the pattern, fails when
    # none does). Ownership is inferred from the shape of the span, so
    # the convention has to make the two cases distinguishable: PATH_RE requires
    # the reserved prefix IMMEDIATELY after the backtick, which means a path
    # qualified with its owning skill's name — `<skill-name>/references/x.md` —
    # does not match and is exempt by construction. That qualified form is how a
    # skill cites a file belonging to a different skill. A skill that operates
    # on a repository names that repository's `scripts/` files too, in prose and
    # in run commands; the convention for those is the repository-relative
    # form, `./scripts/x.py`, exempt the same way (the `./` is not the prefix),
    # in prose and in command position alike. Both forms are conventions, not
    # disguises: re-wording a legitimate cross-reference so the backtick no
    # longer starts with the prefix is. Either form also passes a skill's OWN
    # missing file spelt that way — the same trade-off, accepted for both.
    # The failure message names both conventions, because a false FAIL here is
    # otherwise indistinguishable from a genuinely missing file.
    for rel in sorted(set(PATH_RE.findall(text)) | command_paths(text)):
        if SLOT_SEG_RE.search(rel):
            pat = SLOT_SEG_RE.sub("*", rel)
            if not any(q.is_file() for q in skill_dir.glob(pat)):
                fails.append(f"cited path pattern has no staged instance: {rel} "
                             f"(no file matches {pat})")
            continue
        if not (skill_dir / rel).is_file():
            fails.append(
                f"cited path missing from staged set: {rel} "
                f"— if this file belongs to another skill, cite it as "
                f"`<skill-name>/{rel}`; if it is a file in the repository the "
                f"skill operates on, cite it as `./{rel}`; both forms are "
                f"exempt from this check")
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
        parts = p.relative_to(skill_dir).parts
        if any(part in VCS_DIRS for part in parts):
            if not any(part in VCS_DIRS for part in parts[:-1]):   # report the top only
                fails.append(f"version-control metadata in staged tree: "
                             f"{p.relative_to(skill_dir)} (seed without it)")
            continue
        if p.name in BUILD_JUNK or p.suffix == ".pyc" or p.name.startswith(".~lock"):
            fails.append(f"build artefact in staged tree: {p.relative_to(skill_dir)}")
        # content residue in every text file of the bundle, not only SKILL.md
        if p.is_file() and p.suffix.lower() in (".md", ".txt", ".yml", ".yaml", ".json"):
            body = p.read_text(encoding="utf-8", errors="replace")
            rel = p.relative_to(skill_dir)
            for line, why, hit in residue_hits(rel, body):
                fails.append(f"edit residue in {rel}:{line}: {why} ({hit!r})")


FENCE_OPEN_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})")


def blank_fenced_code(text, fill=lambda h: re.sub(r"[^\n]", " ", h)):
    """Blank every fenced code block, at ANY indentation, keeping line count.

    A fence is ``` or ~~~ (three or more) after any leading whitespace, and it
    is closed only by a line of the same character, at least as long, with
    nothing after it. Detecting fences at column zero only read a block
    indented under a list item — the usual shape for a command inside a
    numbered step — as prose, so a correct `sed` with a backreference failed
    the residue check and was rewritten worse to pass it. A fence that never
    closes is left as prose: the gate errs toward reporting. Every check that
    must not read code as prose calls this one function (`fill` sets what a
    blanked line becomes), so the fence model cannot drift between checks.
    """
    out, held, fence = [], [], None
    for line in text.splitlines(keepends=True):
        if fence is None:
            m = FENCE_OPEN_RE.match(line)
            if m:
                fence, held = m.group(1), [line]
            else:
                out.append(line)
            continue
        held.append(line)
        if re.match(r"^[ \t]*%s{%d,}[ \t]*$" % (re.escape(fence[0]), len(fence)), line):
            out.extend(fill(h) for h in held)
            fence, held = None, []
    out.extend(held)          # unclosed fence: prose
    return "".join(out)


# A `$` right before a digit, and `$ARGUMENTS`, are rewritten by Claude
# Code's skill loader when the skill is invoked with arguments: `$0` becomes
# the first argument word, `$2` the third. The file on disk is unchanged, so
# no read of it shows the damage; an awk field reference in SKILL.md then
# runs as `{st=only,}`, a syntax error the snippet's `2>/dev/null` hides.
# `$ 2` (awk allows the space) and `${2}` arrive intact. Reported as a
# warning, never a failure: other skills use `$1` placeholders on purpose,
# and reference files and scripts are read or run as files, not templated.
TEMPLATE_TOKEN_RE = re.compile(r"\$(?:[0-9]|ARGUMENTS\b)")


def template_tokens(text):
    """[(line, token)] for every loader-substituted token in a SKILL.md."""
    return [(text.count("\n", 0, m.start()) + 1, m.group(0))
            for m in TEMPLATE_TOKEN_RE.finditer(text)]


# (name, SKILL.md text, tokens template_tokens must report)
TEMPLATE_FIXTURES = [
    ("awk field reference $2 is reported", "    fm && /^status:/ {st=$2}\n", [(1, "$2")]),
    ("$0 and $ARGUMENTS in prose are reported", "x\nquote $0 and $ARGUMENTS here\n",
     [(2, "$0"), (2, "$ARGUMENTS")]),
    ("spaced $ 2, ${2}, $NF and $d pass", "{st=$ 2} ${2} $NF \"$d\"\n", []),
]


def interp_name(tok):
    """`python3.12`, `python.exe`, `/usr/bin/python3` -> the CMD_INTERP name, else None."""
    name = re.sub(r"(?i)\.exe$", "", tok.rsplit("/", 1)[-1])
    name = re.sub(r"^python3\.?[0-9]+$", "python3", name)
    return name if name in CMD_INTERP else None


def script_index(toks, i):
    """Index of the script after the interpreter at toks[i], past its own
    options (CMD_OPTS); None where an option means no script follows."""
    j = i + 1
    fam = CMD_OPTS.get(CMD_FAMILY.get(interp_name(toks[i]), ""))
    if not fam:
        return j
    flag, takes_value, no_script = fam
    while j < len(toks):
        t = toks[j]
        if no_script.fullmatch(t):
            return None
        if t in takes_value:
            j += 2
        elif flag.fullmatch(t):
            j += 1
        else:
            break
    return j


def command_paths(text):
    """Unqualified bundled paths in command position (see CMD_PATH_RE)."""
    prose = blank_fenced_code(text)
    chunks = [a for a, b in zip(text.splitlines(), prose.splitlines()) if a != b]
    chunks += re.findall(r"`([^`\n]+)`", prose)
    out = set()
    for chunk in chunks:
        for seg in re.split(r"&&|\|\||;|\|", chunk):
            toks = seg.split()
            for i, t in enumerate(toks):
                if not interp_name(t):
                    continue
                j = script_index(toks, i)
                if j is not None and j < len(toks) and CMD_PATH_RE.fullmatch(toks[j]):
                    out.add(toks[j])
    return out


def residue_hits(rel, body):
    """Gate item 7 on one file: [(line, why, matched text)], first hit per rule.

    Code is where backreferences legitimately live: fenced blocks (at any
    indentation) and inline spans are blanked first, keeping line numbers.
    """
    prose = blank_fenced_code(body)
    prose = re.sub(r"`[^`\n]*`", lambda m: " " * len(m.group(0)), prose)
    exempt_slots = slots_are_intentional(rel, body)
    hits = []
    for rx, why in RESIDUE_RES:
        if why == SLOT_WHY and exempt_slots:
            continue
        m = rx.search(prose)
        if m:
            hits.append((body.count("\n", 0, m.start()) + 1, why, m.group(0).strip()))
    return hits


# (name, text, must_fail): each fixture pins one boundary of the residue
# check. Run with --selftest; exit 1 if any case disagrees.
RESIDUE_FIXTURES = [
    ("indented ``` block holding \\1 passes",
     "1. Normalise:\n\n   ```bash\n   sed -E 's/x(y)/\\1/' f\n   ```\n", False),
    ("indented ~~~ block holding \\1 passes",
     "- step\n    ~~~\n    sed -E 's/(a)/\\1/'\n    ~~~\n", False),
    ("column-0 ``` block holding \\1 passes",
     "```\ns/(a)/\\1/\n```\n", False),
    ("indented prose line holding \\1 fails",
     "1. Step\n\n   Replace it with \\1 here.\n", True),
    ("prose after a closed indented fence fails",
     "   ```\n   ok\n   ```\n   then \\1 leaked\n", True),
    ("a shorter or other-char line does not close the fence",
     "````\n```\n~~~\ns/(a)/\\1/\n````\n", False),
    ("unclosed fence stays prose and fails",
     "   ```\n   s/(a)/\\1/\n", True),
]


def roundtrip_case(after_pack):
    """Pack a three-file fixture skill (one the ceilings sidecar the bundle must
    carry), apply `after_pack` to the directory, and report whether
    verify_roundtrip() failed — None if the sidecar was not packed. Runs in a
    temporary directory outside any staged tree."""
    with tempfile.TemporaryDirectory() as tmp:
        src = pathlib.Path(tmp) / "fixture-skill"
        (src / "references").mkdir(parents=True)
        (src / "SKILL.md").write_text('---\nname: "fixture-skill"\n---\nbody\n', encoding="utf-8")
        (src / "references" / "a.md").write_text("one\n", encoding="utf-8")
        (src / "references" / REF_CEILINGS_FILE).write_text("a.md 1\n", encoding="utf-8")
        out = pathlib.Path(tmp) / "fixture-skill.skill"
        written = pack(src, out)
        if f"fixture-skill/references/{REF_CEILINGS_FILE}" not in written:
            return None           # the sidecar left out of the bundle
        after_pack(src)
        fails = []
        verify_roundtrip(out, src, written, fails)
        return bool(fails)


def _junk(src):
    (src / "__pycache__").mkdir()
    (src / "__pycache__" / "x.cpython-312.pyc").write_bytes(b"\0")


# (name, action on the directory after packing, must_fail): each pins one
# boundary of the --pack round-trip check.
SECOND_FM_FIXTURES = [
    ("duplicated header block", "---\nname: a\n---\n---\nname: a\n---\nbody\n", True),
    ("stray name: line after the header", "---\nname: a\n---\nname: a\nbody\n", True),
    ("two horizontal rules later in the body", "---\nname: a\n---\n\n# T\n\ntext\n\n---\n\n---\n\n## S\n", False),
]


# (name, SKILL.md body, paths command_paths must return)
COMMAND_PATH_FIXTURES = [
    ("inline run command with flags", "Run `python3 scripts/check.py --strict in.json` first.\n", {"scripts/check.py"}),
    ("fenced block, indented under a list item", "1. Build:\n\n   ```bash\n   cd x && python3 scripts/build.py --out dist\n   ```\n", {"scripts/build.py"}),
    ("uv run", "`uv run scripts/a.py`\n", {"scripts/a.py"}),
    ("quoted example with no interpreter is skipped", "e.g. `scripts/x/generate.py --logo l.png`\n", set()),
    ("qualified path is skipped", "`python3 other-skill/scripts/a.py`\n", set()),
    ("repository-relative ./ path is skipped", "`python3 ./scripts/report.py --check`\n", set()),
    ("path outside code is skipped", "python3 scripts/a.py in prose\n", set()),
    ("py launcher", "`py scripts/a.py`\n", {"scripts/a.py"}),
    ("py -3 version selector", "`py -3 scripts/a.py --x`\n", {"scripts/a.py"}),
    ("py -3.12 version selector", "`py -3.12 scripts/a.py`\n", {"scripts/a.py"}),
    ("py -3 -X utf8, fenced", "```\npy -3 -X utf8 scripts/a.py\n```\n", {"scripts/a.py"}),
    ("python3 -X utf8", "`python3 -X utf8 scripts/a.py`\n", {"scripts/a.py"}),
    ("python -u and python -B", "`python -u scripts/a.py && python -B scripts/b.py`\n",
     {"scripts/a.py", "scripts/b.py"}),
    ("python.exe and python3.12 spellings", "`python.exe scripts/a.py; python3.12 scripts/b.py`\n",
     {"scripts/a.py", "scripts/b.py"}),
    ("bash -eu and bash -o pipefail", "`bash -eu scripts/a.sh; bash -o pipefail scripts/b.sh`\n",
     {"scripts/a.sh", "scripts/b.sh"}),
    ("python3 -m pytest stays unchecked", "`python3 -m pytest scripts/test_x.py`\n", set()),
    ("bash -c stays unchecked", "`bash -c scripts/a.sh`\n", set()),
    ("npm run with -- stays unchecked", "`npm run build -- --out assets/out.png`\n", set()),
]


# The cited-path check end to end, over a minimal staged skill with no
# scripts/: (name, SKILL.md body, substring every failure must carry, or None
# when the body must pass; an optional fourth element lists files to stage
# beside SKILL.md). The `./` and `<skill-name>/` spellings are the two
# exemptions the failure message names; a `<slot>`/`{slot}` segment makes
# the span a naming pattern, matched as a glob.
CITED_PATH_FIXTURES = [
    ("unqualified prose path fails, naming both conventions",
     "The `scripts/report.py` vs `pkg/` collision fails partial runs.\n",
     "cite it as `./scripts/report.py`; both forms are exempt"),
    ("unqualified command path fails the same way",
     "Run `python3 scripts/report.py --check` first.\n", "cite it as `./scripts/report.py`"),
    ("repository-relative prose path passes",
     "The `./scripts/report.py` vs `pkg/` collision fails partial runs.\n", None),
    ("repository-relative command path passes",
     "Run `python3 ./scripts/report.py --check` first.\n", None),
    ("another skill's qualified path passes",
     "See `other-skill/references/x.md`.\n", None),
    ("a `<slot>` naming pattern passes when a staged file fits it",
     "One file per study: `references/studies/<study>.md`.\n", None, ["references/studies/alpha.md"]),
    ("a `{slot}` naming pattern with no staged instance fails, naming the glob",
     "One file per study: `references/studies/{study}.md`.\n",
     "cited path pattern has no staged instance: references/studies/{study}.md (no file matches references/studies/*.md)"),
]


ROUNDTRIP_FIXTURES = [
    ("fresh pack round-trips", lambda src: None, False),
    ("directory edited after packing fails",
     lambda src: (src / "references" / "a.md").write_text("two\n", encoding="utf-8"), True),
    ("file added after packing fails",
     lambda src: (src / "references" / "b.md").write_text("new\n", encoding="utf-8"), True),
    ("file removed after packing fails",
     lambda src: (src / "references" / "a.md").unlink(), True),
    ("build artefact is not a member and not a mismatch", _junk, False),
]


# The session-start scan ships as scripts/session-start-scan.sh beside this
# file. Each case runs it against a throwaway workspace (with a space in its
# path) and pins one boundary: (name, scenario, args, exit status, stdout
# substring, checkpoint lines written, stdout substring that must be ABSENT).
# Skipped, not failed, where no bash is on PATH: the scan is a bash script
# and the gate is not. The "gap" and "recent" scenarios seed checkpoints.log
# with one earlier scan line, 21 and 2 days old; "moved" adds a MOVED.md.
SCAN_SCRIPT = pathlib.Path(__file__).resolve().parent / "session-start-scan.sh"
SCAN_FIXTURES = [
    ("healthy log scans: counts line, one checkpoint line", "healthy", True, 0,
     "files: 2  parsed: 2  suspect (awk, a floor): 1", 1, "NOTE: pointer"),
    ("no header parses: guard halts before the checkpoint", "broken", True, 1,
     "SCAN COMMAND BROKEN", 0, ""),
    ("no workspace root: refused, nothing written", "healthy", False, 2, "", 0, ""),
    ("previous scan 21 days old: GAP line names its date", "gap", True, 0,
     "GAP: the previous session-start scan ran ", 2, ""),
    ("previous scan 2 days old: no GAP line", "recent", True, 0, "files: 2", 2, "GAP:"),
    ("MOVED.md at the root: NOTE names it and its first line", "moved", True, 0,
     'NOTE: pointer at this root (skill-observations/MOVED.md): "Moved to /new/root', 1, ""),
    ("the helper's skeleton (empty title) is UNFILLED, not LOST", "skeleton", True, 0,
     "UNFILLED — a header with an empty title", 1, "LOST ENTRIES —"),
    ("id: below the filename prefix is named with its value", "idmis", True, 0,
     "NOTE: id: does not read as the filename prefix", 1, ""),
    ("a zero-padded id reads as its prefix; only the wrong number is named", "padded", True, 0,
     "after reading the body: 0004-d.md (id: 5)", 1, "0002-b.md (id"),
    ("a pre-3.0 log.md beside the directory: SPLIT STORE with its count", "split", True, 0,
     "SPLIT STORE — log.md holds 2 observations not in observation-log/", 1, ""),
    ("use_evidence and next_actor in a header: parsed, not suspect", "fields", True, 0,
     "files: 2  parsed: 2  suspect (awk, a floor): 0", 1, "NOTE:"),
]


def scan_case(scenario, pass_root):
    """Run the scan script over a fixture workspace; return (status, stdout,
    checkpoint lines written)."""
    import os
    import subprocess
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / "work space"
        log = root / "skill-observations" / "observation-log"
        (log / "archive").mkdir(parents=True)
        ck = root / "skill-observations" / "checkpoints.log"
        ck.write_text("", encoding="utf-8")
        if scenario in ("gap", "recent"):
            import datetime
            day = datetime.date.today() - datetime.timedelta(days=21 if scenario == "gap" else 2)
            ck.write_text(f"{day} 09:00 [w] session-start scan: files=2 parsed=2 principles=absent\n",
                          encoding="utf-8")
        if scenario == "broken":
            (log / "0001-a.md").write_text('---\nid: 1\ntitle: "never closed"\n', encoding="utf-8")
        else:
            (log / "0001-a.md").write_text('---\nid: 1\ntitle: "ok"\n---\nbody\n', encoding="utf-8")
            rest = {"skeleton": [("0002-b.md", '---\nid: 2\ntitle: ""\nstatus: open\nskill: []\n---\n')],
                    "idmis": [("0002-b.md", '---\nid: 1\ntitle: "retyped"\n---\n')],
                    # the two optional fields: a bare word, and an append-only list
                    "fields": [("0002-b.md", '---\nid: 2\ntitle: "DECIDED: fields"\nstatus: open\n'
                                'next_actor: review\nuse_evidence:\n'
                                '  - 2026-01-02 accepted — one line of context\n'
                                '  - 2026-01-03 used — unattended run\n---\n')],
                    # both id forms exist in live logs: padded and unpadded read as the prefix
                    "padded": [("0002-b.md", '---\nid: 0002\ntitle: "padded"\n---\n'),
                               ("0003-c.md", '---\nid: 3\ntitle: "plain"\n---\n'),
                               ("0004-d.md", '---\nid: 5\ntitle: "wrong"\n---\n')]}
            for f, text in rest.get(scenario, [("0002-b.md", "---\nid: 2\ntitle: Fix: unquoted\n---\n")]):
                (log / f).write_text(text, encoding="utf-8")
        if scenario == "moved":
            (root / "skill-observations" / "MOVED.md").write_text(
                "Moved to /new/root on 2026-01-01\r\n", encoding="utf-8")
        if scenario == "split":
            (root / "skill-observations" / "log.md").write_text(
                "### Observation 1: A\n\n### Observation 2: B\n", encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k != "TASK_OBSERVER_WORKSPACE"}
        args = ["bash", str(SCAN_SCRIPT)] + ([str(root)] if pass_root else [])
        r = subprocess.run(args, cwd=tmp, env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        return r.returncode, r.stdout, len(ck.read_text(encoding="utf-8").splitlines())


# scripts/skill-load.sh, the per-skill lookup run beside each Skill
# invocation: (name, skill argument, absolute root?, exit status, stdout
# substring, checkpoint lines written[, "nolog"]). The fixture holds one
# match, one prefix-only name, one closed entry, one body-only mention and
# two target_file entries; "nolog" runs it against a root with no
# skill-observations/ at all (the first run, before step 1).
LOAD_SCRIPT = pathlib.Path(__file__).resolve().parent / "skill-load.sh"
LOAD_FIXTURES = [
    ("exact name, open only, frontmatter only", "foo", True, 0, "foo: 1 open observations\n0001-a.md", 1),
    ("plugin-qualified listing finds the bare-name entry", "plug:foo", True, 0,
     "plug:foo: 1 open observations\n0001-a.md", 1),
    ("relative root: refused, nothing written", "foo", False, 2, "", 0),
    ("a file name finds the target_file entry by its last segment", "reviewer.md", True, 0,
     "reviewer.md: 1 open observations\n0005-e.md", 1),
    ("the bare skill name does not match the file name", "reviewer", True, 0,
     "reviewer: 1 open observations\n0006-f.md", 1),
    ("no log yet: one NOTE line, exit 0, nothing written", "foo", True, 0,
     "NOTE: foo: no observation log yet at ", 0, "nolog"),
]


def load_case(skill, absolute, scenario=""):
    import os
    import subprocess
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / "work space"
        log = root / "skill-observations" / "observation-log"
        ck = root / "skill-observations" / "checkpoints.log"
        if scenario == "nolog":
            root.mkdir(parents=True)
        else:
            log.mkdir(parents=True)
            ck.write_text("", encoding="utf-8")
            for f, head, body in [("0001-a.md", "skill: [foo, bar]\nstatus: open", ""),
                                  ("0002-b.md", "skill: [foo-extras]\nstatus: open", ""),
                                  ("0003-c.md", "skill: foo\nstatus: actioned", ""),
                                  ("0004-d.md", "skill: [bar]\nstatus: open", "skill: foo\n"),
                                  ("0005-e.md", "skill: []\ntarget_file: [.claude/agents/reviewer.md]\nstatus: open", ""),
                                  ("0006-f.md", "skill: [reviewer]\nstatus: open", "")]:
                (log / f).write_text(f"---\nid: 1\n{head}\n---\n{body}", encoding="utf-8")
        arg = str(root) if absolute else os.path.relpath(root, tmp)
        r = subprocess.run(["bash", str(LOAD_SCRIPT), arg, skill], cwd=tmp, capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        written = len(ck.read_text(encoding="utf-8").splitlines()) if ck.is_file() else 0
        return r.returncode, r.stdout, written


# scripts/migrate-log.py, the pre-3.0 log converter: (name, legacy entry's
# **Skill:** line, overrides for entry 88 or None, exit status, substring the
# written file 0088-*.md must hold, substring it must NOT hold). The known
# skills are companion-a and companion-b.
MIGRATE_SCRIPT = pathlib.Path(__file__).resolve().parent / "migrate-log.py"
MIGRATE_FIXTURES = [
    ("override siblings_checked and target_file reach the file", "???",
     {"_resolves": ["skill-name-unparseable"], "_reason": "t", "skill": ["companion-a"],
      "siblings_checked": "PLANTED", "target_file": ["PLANTED/T.md"]}, 0,
     'target_file: ["PLANTED/T.md"]\nsiblings_checked: "PLANTED"', None),
    ("an override key the file cannot carry stops the run", "companion-a",
     {"sibling_checked": "typo"}, 2, None, None),
    ("a string where a list belongs stops the run", "companion-a",
     {"skill": "companion-a"}, 2, None, None),
    ("a known skill inside a qualifier is a review flag, not area", "companion-a (also touches companion-b A9)",
     None, 0, "needs review: skill-in-qualifier", "area:"),
    ("a plain qualifier is still promoted to area", "companion-a (section 3)",
     None, 0, 'area: "section 3"', "migration_note"),
    ("a --known-skills path that is not a directory stops the run", "companion-a",
     "BAD-SKILLS-DIR", 2, None, None),
]


def migrate_case(skill_line, ov):
    """Convert a one-entry legacy log; return (status, text of 0088-*.md or None)."""
    import json
    import subprocess
    with tempfile.TemporaryDirectory() as tmp:
        t = pathlib.Path(tmp)
        for k in ("companion-a", "companion-b"):
            (t / "skills" / k).mkdir(parents=True)
        (t / "log.md").write_text("### Observation 88: T\n**Date:** 2026-01-01\n**Status:** OPEN\n"
                                  f"**Skill:** {skill_line}\n\n**Issue:** x\n", encoding="utf-8")
        args = [sys.executable, str(MIGRATE_SCRIPT), "--convert", str(t / "log.md"),
                "--out", str(t / "out"), "--known-skills",
                str(t / ("missing" if ov == "BAD-SKILLS-DIR" else "skills"))]
        if isinstance(ov, dict):
            (t / "ov.json").write_text(json.dumps({"88": ov}), encoding="utf-8")
            args += ["--overrides", str(t / "ov.json")]
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
        files = sorted((t / "out").glob("0088-*.md")) if (t / "out").is_dir() else []
        return r.returncode, files[0].read_text(encoding="utf-8") if files else None


# scripts/new-observation.sh, the only write path where a script can run.
# Each case runs it against a throwaway workspace (with a space in its path)
# and pins one boundary: (name, scenario, slug, body text or None, exit
# status, stdout substring, stderr substring, names of the numbered files
# the log holds afterwards, the floor file's content or None). GOOD_BODY
# is a header the schema accepts, with the two placeholders and a backticked
# command span that must reach the file verbatim.
NEWOBS_SCRIPT = pathlib.Path(__file__).resolve().parent / "new-observation.sh"
GOOD_BODY = ('---\nid: __ID__\ntitle: "t"\nstatus: open            # open | actioned\n'
             'type: open-source       # open-source | internal\nskill: [foo]\n'
             'siblings_checked: "none — no family"\ndate: __DATE__\n---\n\n'
             '**Issue:** `$(date)` on __DATE__ as #__ID__\n')
NEWOBS_FIXTURES = [
    ("empty log: the path is printed, the skeleton holds the id, the floor moves",
     "empty", "first-slug", None, 0, "/0001-first-slug.md", "", ["0001-first-slug.md"], "1"),
    ("a claimed number is skipped: 0002 issued over a claim on 0001",
     "claimed", "second", None, 0, "/0002-second.md", "", ["0002-second.md"], "2"),
    ("--body: id and date filled, the backticked span intact",
     "empty", "with-body", GOOD_BODY, 0, "/0001-with-body.md", "", ["0001-with-body.md"], "1"),
    ("--body file missing: refused, nothing created",
     "nobody", "slug", None, 1, "", "missing or unreadable", [], None),
    ("--body with status actioned: refused by name, nothing created",
     "empty", "slug", GOOD_BODY.replace("status: open ", "status: actioned "), 1, "",
     "status: must read open", [], None),
    ("--body with a type outside the vocabulary: refused",
     "empty", "slug", GOOD_BODY.replace("type: open-source ", "type: process "), 1, "",
     "type: must be open-source or internal", [], None),
    ("--body with an empty siblings_checked: refused",
     "empty", "slug", GOOD_BODY.replace('siblings_checked: "none — no family"', 'siblings_checked: ""'),
     1, "", "siblings_checked: must be non-empty", [], None),
    ("a prefix in use under another slug the listing cannot see: COLLISION, no file",
     "hidden", "slug", None, 1, "", "COLLISION", [], None),
    ("a slug carrying an id prefix: refused",
     "empty", "0001-slug", None, 1, "", "must not start with an id prefix", [], None),
]


def newobs_case(scenario, slug, body):
    """Run the helper over a fixture workspace; return (status, stdout,
    stderr, numbered files in the log, floor content or None, created text)."""
    import os
    import subprocess
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / "work space"
        log = root / "skill-observations" / "observation-log"
        (log / "archive").mkdir(parents=True)
        if scenario == "claimed":
            (log / "archive" / ".id-claims").mkdir()
            (log / "archive" / ".id-claims" / "0001").write_text("", encoding="utf-8")
        if scenario == "hidden":
            (log / "other").mkdir()
            (log / "other" / "0001-x.md").write_text("---\nid: 1\n---\n", encoding="utf-8")
        args = ["bash", str(NEWOBS_SCRIPT)]
        if scenario == "nobody":
            args += ["--body", str(pathlib.Path(tmp) / "absent.md")]
        elif body is not None:
            (pathlib.Path(tmp) / "body.md").write_text(body, encoding="utf-8")
            args += ["--body", str(pathlib.Path(tmp) / "body.md")]
        args += [slug, str(root)]
        env = {k: v for k, v in os.environ.items() if k != "TASK_OBSERVER_WORKSPACE"}
        r = subprocess.run(args, cwd=tmp, env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        files = sorted(p.name for p in log.glob("[0-9]*.md"))
        floor = log / "archive" / ".id-floor"
        text = (log / files[0]).read_text(encoding="utf-8") if files else ""
        return (r.returncode, r.stdout, r.stderr, files,
                floor.read_text(encoding="utf-8").strip() if floor.is_file() else None, text)


def ref_shape_case(lines, triggers, sidecar):
    """Run check_reference_shape over a one-reference fixture skill: a.md of
    `lines` lines declaring `triggers` load triggers (None = no declaration),
    beside `sidecar` as references/ceilings.txt (None = not opted in). Returns
    the failures."""
    with tempfile.TemporaryDirectory() as tmp:
        refs = pathlib.Path(tmp) / "fixture-skill" / "references"
        refs.mkdir(parents=True)
        head = ["# A", ""]
        if triggers is not None:
            head += ["Load triggers: " + "; ".join(f"episode {i}" for i in range(triggers)), ""]
        body = head + ["## Contents", "", "- S", "", "## S"]
        body += ["text"] * (lines - len(body))
        (refs / "a.md").write_text("\n".join(body) + "\n", encoding="utf-8")
        if sidecar is not None:
            (refs / REF_CEILINGS_FILE).write_text(sidecar, encoding="utf-8")
        fails = []
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):   # the shape line is not the verdict
            check_reference_shape(refs.parent, "Load `references/a.md` (\"S\") when S.\n", fails)
        return fails


# (name, lines, declared triggers, sidecar, substring every failure set must
# hold — None = must pass, substring a failure must NOT hold): the growth
# barrier's boundaries, with N = SPLIT_TRIGGER_THRESHOLD and the tolerance.
REF_SHAPE_FIXTURES = [
    ("no sidecar: never gated, even far over any size and trigger count",
     5000, 40, None, None, None),
    ("no sidecar and no declaration: still not gated", 5000, None, None, None, None),
    ("under ceiling, inside tolerance", 98, 3, "a.md 100\n", None, None),
    ("at the tolerance boundary (slack 3) passes", 97, 3, "a.md 100\n", None, None),
    ("over ceiling, <= N triggers: trim or reasoned raise, never split",
     105, SPLIT_TRIGGER_THRESHOLD, "a.md 100\n", "trim it back", "split"),
    ("reasoned raise clears it (dated reason beside the number)",
     105, 3, "a.md 105 2026-01-31 one new episode section, single-trigger\n", None, None),
    ("over ceiling, > N triggers: split indicated",
     105, SPLIT_TRIGGER_THRESHOLD + 1, "a.md 100\n", "split it by episode", "trim"),
    ("a raise on a file with > N triggers fails: the remedy is a split",
     105, SPLIT_TRIGGER_THRESHOLD + 1, "a.md 105 2026-01-31 more room\n", "not a raise", None),
    ("shrink beyond tolerance: the ceiling must be lowered",
     96, 3, "a.md 100\n", "Lower its line", None),
    ("a raise with a reason but no date is unreadable", 100, 3, "a.md 100 more room\n",
     "unreadable line", None),
    ("opted in, file without a declaration fails", 100, None, "a.md 100\n",
     "declares no load triggers", None),
    ("opted in, file without a ceiling line fails", 100, 3, "# none yet\n",
     "has no ceiling", None),
]

# (name, core text, {file: section count}, {file: filename-only count})
POINTER_FIXTURES = [
    ("named form, wrapped heading", 'Load `references/a.md` ("One\n   two") now.\n', {"a.md": 1}, {}),
    ("parenthesised form", 'done (`references/a.md`,\n "One") here.\n', {"a.md": 1}, {}),
    ("filename-only pointers count once per paragraph",
     "See `references/a.md` and `references/a.md`.\n\nAlso `references/a.md`.\n", {}, {"a.md": 2}),
    ("a backtick between path and heading breaks the pairing",
     'See `references/a.md` and `x` ("Not a target").\n', {}, {"a.md": 1}),
]


def selftest():
    bad = total = 0
    for name, lines, trig, sidecar, want, avoid in REF_SHAPE_FIXTURES:
        fails = ref_shape_case(lines, trig, sidecar)
        ok = (not fails) if want is None else any(want in f for f in fails)
        if avoid is not None:
            ok = ok and not any(avoid in f for f in fails)
        bad += not ok; total += 1
        print(f"{'ok  ' if ok else 'FAIL'} reference ceiling: {name}"
              + ("" if ok else f" (failures {fails})"))
    for name, core, want_named, want_unnamed in POINTER_FIXTURES:
        named, unnamed = core_pointers(core)
        ok = {f: len(s) for f, s in named.items()} == want_named and unnamed == want_unnamed
        bad += not ok; total += 1
        print(f"{'ok  ' if ok else 'FAIL'} core pointer: {name}"
              + ("" if ok else f" (named {named}, filename-only {unnamed})"))
    for name, text, must_fail in RESIDUE_FIXTURES:
        failed = bool(residue_hits(pathlib.Path("fixture.md"), text))
        ok = failed == must_fail
        bad += not ok; total += 1
        print(f"{'ok  ' if ok else 'FAIL'} {name}")
    for name, text, must_fail in SECOND_FM_FIXTURES:
        ok = bool(SECOND_FRONTMATTER_RE.match(text)) == must_fail
        bad += not ok; total += 1
        print(f"{'ok  ' if ok else 'FAIL'} second-frontmatter: {name}")
    for value, kebab in FALLBACK_NAME_FIXTURES:
        ok = bool(NAME_RE.match(fallback_name(f"name: {value}\n"))) == kebab
        bad += not ok; total += 1
        print(f"{'ok  ' if ok else 'FAIL'} fallback name: {value!r}")
    try:
        import yaml  # noqa: F401
        branches = (True, False)
    except ImportError:
        branches = (False,)
        print("skip compare-frontmatter PyYAML branch: PyYAML not installed")
    for use_yaml in branches:
        for name, a, b, want_keys, want_body in COMPARE_FM_FIXTURES:
            keys, body_equal, _ = compare_frontmatter_texts(a, b, use_yaml)
            ok = keys == want_keys and body_equal == want_body
            bad += not ok; total += 1
            print(f"{'ok  ' if ok else 'FAIL'} compare-frontmatter "
                  f"({'PyYAML' if use_yaml else 'fallback'}): {name}"
                  + ("" if ok else f" (keys {keys}, body equal {body_equal})"))
    for name, text, want in INDEX_FIXTURES:
        ok = index_misses(text) == want
        bad += not ok; total += 1
        print(f"{'ok  ' if ok else 'FAIL'} reference index: {name}")
    for name, text, want in ORPHAN_FIXTURES:
        got = index_orphans(text)
        ok = got == want
        bad += not ok; total += 1
        print(f"{'ok  ' if ok else 'FAIL'} reference index (reverse): {name}"
              + ("" if ok else f" (got {got})"))
    for name, text, want in TEMPLATE_FIXTURES:
        ok = template_tokens(text) == want
        bad += not ok; total += 1
        print(f"{'ok  ' if ok else 'FAIL'} template token: {name}")
    with tempfile.TemporaryDirectory() as td:   # a token warns; it never fails the gate
        sk = pathlib.Path(td) / "tok"
        sk.mkdir()
        (sk / "SKILL.md").write_text('---\nname: tok\ndescription: "D."\n---\nawk \'{print $1}\'\n',
                                     encoding="utf-8")
        import contextlib
        import io
        fails, buf = [], io.StringIO()
        with contextlib.redirect_stdout(buf):
            check_dir(sk, fails)
        ok = not fails and "warn: SKILL.md:5: '$1'" in buf.getvalue()
        bad += not ok; total += 1
        print(f"{'ok  ' if ok else 'FAIL'} template token: warns, does not fail the gate"
              + ("" if ok else f" (fails {fails})"))
    for name, text, want in COMMAND_PATH_FIXTURES:
        ok = command_paths(text) == want
        bad += not ok; total += 1
        print(f"{'ok  ' if ok else 'FAIL'} command path: {name}")
    for name, body, want, *staged in CITED_PATH_FIXTURES:
        with tempfile.TemporaryDirectory() as td:
            sk = pathlib.Path(td) / "cp"
            sk.mkdir()
            (sk / "SKILL.md").write_text('---\nname: cp\ndescription: "D."\n---\n' + body,
                                         encoding="utf-8")
            for rel in (staged[0] if staged else []):
                (sk / rel).parent.mkdir(parents=True, exist_ok=True)
                (sk / rel).write_text("x\n", encoding="utf-8")
            import contextlib
            import io
            fails = []
            with contextlib.redirect_stdout(io.StringIO()):
                check_dir(sk, fails)
        cited = [f for f in fails if f.startswith("cited path ")]
        ok = (not fails) if want is None else (len(cited) == 1 and want in cited[0])
        bad += not ok; total += 1
        print(f"{'ok  ' if ok else 'FAIL'} cited path: {name}"
              + ("" if ok else f" (fails {fails})"))
    for name, after_pack, must_fail in ROUNDTRIP_FIXTURES:
        ok = roundtrip_case(after_pack) == must_fail
        bad += not ok; total += 1
        print(f"{'ok  ' if ok else 'FAIL'} round-trip: {name}")
    import shutil
    import subprocess
    if not shutil.which("bash"):
        print("skip scan script: no bash on PATH")
    elif not SCAN_SCRIPT.is_file():
        bad += 1; total += 1
        print(f"FAIL scan script: {SCAN_SCRIPT.name} missing beside this file")
    else:
        ok = subprocess.run(["bash", "-n", str(SCAN_SCRIPT)]).returncode == 0
        bad += not ok; total += 1
        print(f"{'ok  ' if ok else 'FAIL'} scan script: bash -n passes")
        for name, scenario, pass_root, want_rc, want_out, want_ck, absent in SCAN_FIXTURES:
            rc, out, ck = scan_case(scenario, pass_root)
            ok = rc == want_rc and want_out in out and ck == want_ck and not (absent and absent in out)
            bad += not ok; total += 1
            print(f"{'ok  ' if ok else 'FAIL'} scan script: {name}"
                  + ("" if ok else f" (exit {rc}, {ck} checkpoint lines)"))
    for eol in ("\n", "\r\n"):    # the name-quoting rewrite keeps the file's line endings
        with tempfile.TemporaryDirectory() as td:
            p = pathlib.Path(td) / "SKILL.md"
            p.write_bytes(eol.join(["---", "name: x-y", "description: d", "---", "body", ""]).encode())
            quoted = quote_frontmatter_name(p)
            out = p.read_bytes()
            ok = quoted and b'name: "x-y"' in out and \
                (out.count(b"\r\n") == 5 if eol == "\r\n" else b"\r" not in out)
        bad += not ok; total += 1
        print(f"{'ok  ' if ok else 'FAIL'} name quoting keeps {'CRLF' if eol == chr(13) + chr(10) else 'LF'} endings")
    if shutil.which("bash") and LOAD_SCRIPT.is_file():
        ok = subprocess.run(["bash", "-n", str(LOAD_SCRIPT)]).returncode == 0
        bad += not ok; total += 1
        print(f"{'ok  ' if ok else 'FAIL'} skill-load script: bash -n passes")
        for name, skill, absolute, want_rc, want_out, want_ck, *scenario in LOAD_FIXTURES:
            rc, out, ck = load_case(skill, absolute, *scenario)
            ok = rc == want_rc and want_out in out and ck == want_ck
            bad += not ok; total += 1
            print(f"{'ok  ' if ok else 'FAIL'} skill-load script: {name}"
                  + ("" if ok else f" (exit {rc}, {ck} checkpoint lines, out {out!r})"))
    elif shutil.which("bash"):
        bad += 1; total += 1
        print(f"FAIL skill-load script: {LOAD_SCRIPT.name} missing beside this file")
    if shutil.which("bash") and NEWOBS_SCRIPT.is_file():
        import datetime
        ok = subprocess.run(["bash", "-n", str(NEWOBS_SCRIPT)]).returncode == 0
        bad += not ok; total += 1
        print(f"{'ok  ' if ok else 'FAIL'} new-observation script: bash -n passes")
        today = datetime.date.today().isoformat()
        for name, scenario, slug, body, want_rc, want_out, want_err, want_files, want_floor in NEWOBS_FIXTURES:
            rc, out, err, files, floor, text = newobs_case(scenario, slug, body)
            ok = (rc == want_rc and want_out in out and want_err in err
                  and files == want_files and floor == want_floor)
            if ok and files and body is None:     # the skeleton: id on disk, status open, title empty
                ok = f"id: {int(files[0][:4])}\n" in text and "status: open\n" in text and 'title: ""\n' in text
            if ok and files and body is not None:  # the copy: placeholders filled, the span verbatim
                ok = ("id: 1\n" in text and f"date: {today}\n" in text and "`$(date)`" in text
                      and f"on {today} as #1\n" in text and "__ID__" not in text)
            bad += not ok; total += 1
            print(f"{'ok  ' if ok else 'FAIL'} new-observation script: {name}"
                  + ("" if ok else f" (exit {rc}, files {files}, floor {floor!r}, err {err.strip()!r})"))
    elif shutil.which("bash"):
        bad += 1; total += 1
        print(f"FAIL new-observation script: {NEWOBS_SCRIPT.name} missing beside this file")
    if MIGRATE_SCRIPT.is_file():
        for name, skill_line, ov, want_rc, has, lacks in MIGRATE_FIXTURES:
            rc, text = migrate_case(skill_line, ov)
            ok = rc == want_rc and (text is None if want_rc else text is not None) \
                and (has is None or has in (text or "")) and (lacks is None or lacks not in (text or ""))
            bad += not ok; total += 1
            print(f"{'ok  ' if ok else 'FAIL'} migrate-log: {name}" + ("" if ok else f" (exit {rc})"))
    else:
        bad += 1; total += 1
        print(f"FAIL migrate-log: {MIGRATE_SCRIPT.name} missing beside this file")
    print(f"selftest: {total - bad}/{total} passed")
    return 1 if bad else 0


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

    plugin.json also carries a `description` (and `keywords`) written for
    discovery, mirrored in the marketplace entry, because that entry is what a
    browser sees before install. It is deliberately not the SKILL.md
    description: that one is the invocation trigger, read by the loader.
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
    desc = str(json.loads(canonical_path.read_text(encoding="utf-8")).get("description") or "").strip()
    if not desc:
        fails.append(
            "repo: .claude-plugin/plugin.json has no `description`. Add one written for "
            "discovery: `/plugin` search, the pre-install listing and plugin directories "
            "read it. It is not compared with the SKILL.md description, which is the "
            "invocation trigger and has a different reader; re-read both at every release.")
    print(f"repo: canonical version {canonical}")
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
        # A marketplace entry with a non-relative source is all a browser sees
        # before install, so it mirrors plugin.json's description and keywords.
        pj = json.loads(canonical_path.read_text(encoding="utf-8"))
        for i, e in enumerate(data.get("plugins", [])):
            if not isinstance(e, dict) or e.get("name") != pj.get("name"):
                continue
            if str(e.get("description") or "").strip() != desc:
                fails.append(f"repo: marketplace.json plugins[{i}].description differs from plugin.json's")
            if e.get("keywords", []) != pj.get("keywords", []):
                fails.append(f"repo: marketplace.json plugins[{i}].keywords differ from plugin.json's")


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
        prose = blank_fenced_code(body, fill=lambda h: re.sub(r"[^\n]+", "~", h))
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


def quote_frontmatter_name(skill_md):
    """Rewrite an unquoted frontmatter `name: x` to `name: "x"`, in place.

    Provenance: the skill installer writes `name:` back quoted on some installs
    and unquoted on others, with no visible pattern, but has never been seen
    REMOVING quotes that were present. Emitting the quoted form here therefore
    makes most installed copies byte-identical to the staged one, and every
    installed-vs-staged comparison (the reconciliation gate, keep-two) stops
    reporting a one-line diff that reviewers learn to wave through. Those
    comparisons still normalise the line as the backstop. Runs only on the
    pack path, after every check passed, so the value is known kebab-case.
    """
    raw = skill_md.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    text = raw.replace("\r\n", "\n")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return False
    nm = re.search(r"(?m)^name:[ \t]*([^\s\"'][^\n]*?)[ \t]*$", m.group(1))
    if not nm or not NAME_RE.match(nm.group(1)):
        return False          # already quoted, absent, or carrying a comment: leave it
    start = m.start(1) + nm.start()
    end = m.start(1) + nm.end()
    old = text[start:end]
    new = f'name: "{nm.group(1)}"'
    out = text[:start] + new + text[end:]
    skill_md.write_bytes((out.replace("\n", "\r\n") if crlf else out).encode("utf-8"))
    print(f"pack: quoted the frontmatter name in {skill_md} ({old!r} -> {new!r}); "
          f"the packed copy carries the quoted form")
    return True


def is_build_junk(path, root):
    rel = path.relative_to(root)
    return (any(part in BUILD_JUNK or part in VCS_DIRS or part.startswith(".~lock")
                for part in rel.parts)
            or path.suffix == ".pyc")


def packable_files(src):
    """The files a bundle carries: every regular file but build artefacts.
    pack() and verify_roundtrip() share this, so they cannot disagree about
    what a member is."""
    return sorted(p for p in src.rglob("*") if p.is_file() and not is_build_junk(p, src))


def member_name(src, f):
    return f"{src.name}/{f.relative_to(src).as_posix()}"


def pack(src, out):
    """Always writes POSIX separators, on any platform.

    Returns {member: bytes} — what the packer meant to write — so the caller
    can verify the bundle against it. The source is resolved first: the
    member prefix is the directory's name, and Path('.').name is ''.
    """
    src = pathlib.Path(src).resolve()
    written = {}
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in packable_files(src):
            arc = member_name(src, f)
            assert "\\" not in arc, arc
            data = f.read_bytes()
            z.writestr(zipfile.ZipInfo.from_file(f, arcname=arc), data,
                       compress_type=zipfile.ZIP_DEFLATED)
            written[arc] = data
    return written


def verify_roundtrip(bundle, src, written, fails):
    """The bundle is the deliverable; the directory is what the next review
    diffs. An edit to the directory after packing leaves the two different,
    the user installs the bundle, and a later comparison of the directory
    against live reads the missing content as "not installed". So: the
    members must be exactly the directory's packable files, each equal byte
    for byte to what pack() wrote (`written`; None skips that half) and to
    the file on disk now. Returns True when the round trip holds."""
    src = pathlib.Path(src).resolve()
    with zipfile.ZipFile(bundle) as z:
        names = z.namelist()
        members = {n: z.read(n) for n in names}
    expected = {member_name(src, f): f for f in packable_files(src)}
    problems = []
    if len(names) != len(members):
        problems.append(f"{len(names) - len(members)} duplicate member name(s)")
    problems += [f"missing from the bundle: {a}" for a in sorted(set(expected) - set(members))]
    problems += [f"in the bundle, not in the directory: {a}" for a in sorted(set(members) - set(expected))]
    for arc in sorted(set(expected) & set(members)):
        if written is not None and members[arc] != written.get(arc):
            problems.append(f"member differs from what the packer wrote: {arc}")
        elif members[arc] != expected[arc].read_bytes():
            problems.append(f"directory file differs from the packed member: {arc}")
    for p in problems:
        fails.append(f"bundle round-trip: {p} — the bundle does not carry the staged "
                     f"directory; finish every edit, then re-pack (packing is the last write)")
    return not problems


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
        if re.search(rb"(^|/)\.(git|hg|svn)(/|$)", name):
            fails.append(f"bundle: contains version-control metadata "
                         f"({name.decode(errors='replace')})")
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
    # A console or pipe whose code page cannot encode a character this script
    # prints (U+2014 under cp949 or cp932) would raise UnicodeEncodeError and
    # exit 1 with no verdict, the code a failed gate uses. Replace instead.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="replace")
            except (ValueError, AttributeError):
                pass
    if len(argv) < 2:
        print(__doc__); return 2
    if argv[1] in ("--help", "-h"):
        print(__doc__); return 0
    if argv[1] == "--selftest":
        return selftest()
    if argv[1] == "--compare-frontmatter":
        if len(argv) != 4:
            print("usage: --compare-frontmatter <SKILL.md A> <SKILL.md B>"); return 2
        return compare_frontmatter_main(argv[2], argv[3])
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
        quote_frontmatter_name(pathlib.Path(skill_dir).resolve() / "SKILL.md")
        written = pack(skill_dir, pack_to); bundle = pack_to
        print(f"packed {pack_to}")
        if verify_roundtrip(pack_to, skill_dir, written, fails):
            print(f"pack: round trip OK — {len(written)} members equal the staged "
                  f"directory byte for byte")
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
