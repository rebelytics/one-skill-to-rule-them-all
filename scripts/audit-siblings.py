#!/usr/bin/env python3
"""
audit-siblings.py — mechanical audit of the observation log's sibling-check
discipline.

The sibling check is write-time enforcement (SKILL.md, "What to Watch For"),
and the project's own reference material records that prose instruction alone
is "demonstrably not enough" — observations were logged under-scoped by
authors who had written the rule earlier that same session. This script turns
the review's judgement call into measurable findings: for every observation
file it reads the frontmatter-only fields whose *absence* is the only signal a
review can act on, and reports each as a concrete, machine-checkable line.

It reads only the `id`, `title`, `skill` and `siblings_checked:` frontmatter
fields, plus a single bounded scan of the file text for a fixed set of
self-declared-generality phrases (see GENERIC_LITERALS below) — never a full
body judgement. Stdlib only; no dependencies.

Usage
-----
  python3 scripts/audit-siblings.py <observation-log-dir> \
      [--registry skill-families.md] [--json]

Finding keys (stable machine identifiers, no prose)
  missing-sibling-check      `siblings_checked:` absent or blank            [high]
  malformed-sibling-check    present but neither `none` nor
                             `family: members — verdict`                    [high]
  propagation-underlist      verdict claims shared/propagation but `skill`
                             carries <2 entries or lacks the named members  [high]
  generic-insight-under-scoped  body/title matches a fixed genericity
                             phrase while `skill` has <=1 entry            [med]
  family-member-marked-none  (with --registry) primary `skill` target is a
                             declared family member but the field is `none` [high]

Exit codes
  0  clean
  1  findings present
  2  invalid/broken input or usage (including the scan guard: files present
     but 0 headers parsed -> a broken command, never a clean log)
"""

import glob
import json
import os
import re
import sys

# --- fixed, explicit genericity phrases (the "automatic multi-skill flag") ---
GENERIC_LITERALS = (
    "applies to any",
    "applies more broadly",
    "not specific to",
    "any file-writing",
)
GENERIC_RE = re.compile(r"any [-a-z0-9]+-writing script", re.IGNORECASE)

# Verdict keywords that claim propagation.
PROPAGATE_KEYWORDS = ("shared", "added", "propagat", "applies to",
                      "applies more broadly")

# Negative wording overrides positive keywords regardless of order/substrings:
# "not shared" contains "shared", "not added" contains "added" — neither may be
# read as propagation. (Surrounding spaces keep "no "/"not " boundary-anchored.)
NEGATION_MARKERS = ("no ", "not ", "n't", "never ")

MISSING_KEYS = ("missing-sibling-check", "malformed-sibling-check")

FM_RE = re.compile(r"^---[ \t]*\n(.*?)\n---[ \t]*\n?", re.DOTALL)


def unquote(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def parse_list(val):
    val = val.strip()
    if val.startswith("[") and val.endswith("]"):
        val = val[1:-1]
    return [unquote(x.strip()) for x in val.split(",") if x.strip()]


def parse_frontmatter(text):
    """Return a dict of top-level frontmatter fields ({} if no block)."""
    m = FM_RE.match(text)
    if not m:
        return {}
    data = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if not key:
            continue
        if val.startswith("[") and val.endswith("]"):
            data[key] = parse_list(val)
        else:
            data[key] = unquote(val)
    return data


def parse_registry(text):
    """Parse skill-families.md into member -> {family names}.

    Format (references/observation-log.md): one family per `## name` heading,
    its members on the following `**Members:**` line.
    """
    member_families = {}
    fam = None
    prefix = "**Members:**"
    for line in text.splitlines():
        if line.startswith("## "):
            fam = line[3:].strip()
        elif line.startswith(prefix) and fam:
            members = [m.strip() for m in
                       line[len(prefix):].split(",") if m.strip()]
            for m in members:
                member_families.setdefault(m, set()).add(fam)
    return member_families


def indicates_propagation(verdict):
    v = " " + verdict.lower() + " "
    if any(k in v for k in NEGATION_MARKERS):
        return False
    return any(k in v for k in PROPAGATE_KEYWORDS)


def generic_hit(text):
    low = text.lower()
    if any(k in low for k in GENERIC_LITERALS):
        return True
    return bool(GENERIC_RE.search(low))


def _f(key, severity, rec_id, title, filename, detail):
    return {"key": key, "severity": severity, "id": rec_id,
            "file": filename, "title": title, "detail": detail}


def audit_text(text, filename, member_families=None):
    member_families = member_families or {}
    rec = parse_frontmatter(text)
    # Any id that is not a clean integer (garbage string, list, float) becomes
    # None so the deterministic sort can never mix int and non-int keys.
    rec_id = rec.get("id")
    try:
        rec_id = int(rec_id)
    except (TypeError, ValueError):
        rec_id = None
    title = rec.get("title") or filename

    skill = rec.get("skill")
    if skill is None:
        skill = []
    elif isinstance(skill, str):
        skill = [skill]

    sc = rec.get("siblings_checked")
    sc_raw = sc.strip() if isinstance(sc, str) else ""
    findings = []

    if not isinstance(sc, str) or not sc_raw:
        findings.append(_f("missing-sibling-check", "high", rec_id, title,
                           filename, "siblings_checked field missing or blank"))
    else:
        is_none = sc_raw.lower() == "none"
        has_sep = "—" in sc_raw
        if is_none:
            if skill and skill[0] in member_families:
                families = ", ".join(sorted(member_families[skill[0]]))
                findings.append(_f(
                    "family-member-marked-none", "high", rec_id, title, filename,
                    f"{skill[0]} is a family member ({families}) but "
                    f"siblings_checked is 'none'"))
        elif has_sep:
            family_part, _, verdict = sc_raw.partition("—")
            named = [x.strip() for x in
                     family_part.split(":")[-1].split(",") if x.strip()]
            if indicates_propagation(verdict):
                if len(skill) < 2:
                    findings.append(_f(
                        "propagation-underlist", "high", rec_id, title, filename,
                        "siblings_checked claims propagation but `skill` lists "
                        "only 1 member"))
                elif named and not set(named) <= set(skill):
                    missing = sorted(set(named) - set(skill))
                    findings.append(_f(
                        "propagation-underlist", "high", rec_id, title, filename,
                        "propagation names members absent from `skill`: "
                        + ", ".join(missing)))
        else:
            findings.append(_f(
                "malformed-sibling-check", "high", rec_id, title, filename,
                "siblings_checked is neither `none` nor "
                "'family: members — verdict'"))

    if generic_hit(text) and len(skill) <= 1:
        findings.append(_f(
            "generic-insight-under-scoped", "med", rec_id, title, filename,
            "self-declared-generality phrasing with a single (or no) `skill` "
            "entry"))

    return findings


def run_audit(logdir, member_families):
    paths = sorted(glob.glob(os.path.join(logdir, "*.md")))
    findings, parsed = [], 0
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            text = fh.read()
        if parse_frontmatter(text):
            parsed += 1
        findings.extend(audit_text(text, os.path.basename(p), member_families))
    findings.sort(key=lambda f: (f["id"] if f["id"] is not None else float("inf"),
                                 f["key"], f["file"]))
    missing = sum(1 for f in findings if f["key"] in MISSING_KEYS)
    return {
        "paths": len(paths),
        "parsed": parsed,
        "broken": bool(paths) and parsed == 0,
        "findings": findings,
        "findings_count": len(findings),
        "missing_sibling_check_count": missing,
    }


def main(argv):
    logdir = registry = None
    json_out = False
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--registry":
            i += 1
            if i >= len(argv):
                return 2
            registry = argv[i]
        elif a == "--json":
            json_out = True
        elif a.startswith("-"):
            return 2
        elif logdir is None:
            logdir = a
        else:
            return 2
        i += 1

    if not logdir:
        return 2
    if not os.path.isdir(logdir):
        print(f"audit-siblings: no such directory: {logdir}", file=sys.stderr)
        return 2

    member_families = {}
    if registry:
        if not os.path.isfile(registry):
            print(f"audit-siblings: no such registry: {registry}",
                  file=sys.stderr)
            return 2
        with open(registry, encoding="utf-8") as fh:
            member_families = parse_registry(fh.read())

    result = run_audit(logdir, member_families)
    if result["broken"]:
        print(f"SCAN BROKEN — {result['paths']} files present, "
              f"0 headers parsed", file=sys.stderr)
        return 2

    if json_out:
        print(json.dumps({
            "observations": result["paths"],
            "parsed": result["parsed"],
            "findings_count": result["findings_count"],
            "observations_without_sibling_check":
                result["missing_sibling_check_count"],
            "findings": result["findings"],
        }, ensure_ascii=False, indent=2))
    else:
        if result["findings"]:
            for f in result["findings"]:
                tag = {"high": "HIGH", "med": "MED"}.get(f["severity"], "NOTE")
                rid = f["id"] if f["id"] is not None else "-"
                print(f"[{tag}] #{rid} {f['title']} — "
                      f"{f['key']}: {f['detail']}")
        else:
            print("OK: audit clean")
        print(f"observations: {result['paths']}")
        print(f"observations logged without a sibling check: "
              f"{result['missing_sibling_check_count']}")

    return 1 if result["findings"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
