#!/usr/bin/env python3
"""
migrate-log.py — convert a legacy single-file observation log (log.md) into
one Markdown file per observation, with YAML frontmatter.

Upgrade-only: needed solely by installs that used a task-observer version
before v3.0.0. Fresh v3 installs start with the per-file layout and never
run this.

Usage
-----
  # validate parsing only, write nothing (safe on any log, incl. archives)
  python3 migrate-log.py --check log.md [more.md ...]

  # convert an active log into a target directory
  python3 migrate-log.py --convert log.md --out observation-log/ \
      [--id-floor-from archive/]

Design notes
------------
* Only a fixed set of metadata labels is lifted into frontmatter. Every other
  bolded label (one-off things like "Fix applied:", "Root cause:") stays in
  the body verbatim, so nothing is silently dropped.
* `skill` is ALWAYS a list, even with one entry, so consumers never branch on
  string-vs-list. First entry is primary by convention.
* Ambiguity is flagged, never guessed. Anything the parser is not confident
  about is written into the file as `migration_note` and listed in the report.
"""

import argparse
import json
import os
import re
import sys
from datetime import date

# --- labels lifted into frontmatter; everything else stays in the body ------
META_LABELS = {
    "Status": "status_raw",
    "Date": "date",
    "Session context": "session_context",
    "Skill": "skill_raw",
    "Type": "type",
    "Phase/Area": "area",
    "Reference file": "reference",
    "Reference files": "reference",
}

# Flags that genuinely need a human decision, versus ones that are merely
# worth recording. Only the former earn a `migration_note` in the file —
# flagging every qualifier as "needs review" cries wolf and buries the two
# entries that actually lost information.
REVIEW_FLAGS = {
    "candidate-name-unparseable",
    "status-missing",
    "status-unrecognised",
    "status-unbalanced-parens",
    "resolved-date-missing",
    "skill-missing",
    "skill-name-unparseable",
    "group-qualifier-ambiguous",
    "duplicate-id",
    "body-empty",
    "date-not-iso",
}

ENTRY_RE = re.compile(r"^### Observation (\d+):[ \t]*(.*)$")
LABEL_RE = re.compile(r"^\*\*([A-Za-z][A-Za-z /-]*):\*\*[ \t]*(.*)$")
ISO_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
STATUS_RE = re.compile(r"^(OPEN|ACTIONED|DECLINED|SUPERSEDED)\b(.*)$", re.I)
NEW_SKILL_RE = re.compile(r"^New skill candidate:\s*(.+)$", re.I)
SKILL_NAME_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)$")


def split_top_level(text, seps=";"):
    """Split on any char in `seps`, but not inside parentheses or brackets."""
    parts, buf, depth = [], [], 0
    for ch in text:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        if ch in seps and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def slugify(title, maxlen=60):
    s = title.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if len(s) > maxlen:
        s = s[:maxlen].rsplit("-", 1)[0]
    return s or "untitled"


def parse_entries(text, source):
    """Yield raw entry dicts: id, title, meta{label: value}, body, source."""
    lines = text.splitlines()
    starts = [i for i, ln in enumerate(lines) if ENTRY_RE.match(ln)]
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        m = ENTRY_RE.match(lines[start])
        block = lines[start + 1:end]

        # trailing section separators / date headers belong to no entry
        while block and (
            not block[-1].strip()
            or block[-1].startswith("## ")
            or re.match(r"^-{3,}\s*$", block[-1])
        ):
            block.pop()

        # Metadata labels are not always contiguous or first: older entries put
        # **Status:** after a blank line following Phase/Area. So keep lifting
        # known labels until the first UNKNOWN label (Issue / Fix applied /
        # Principle / ...), which is where the body genuinely starts.
        meta, cur = {}, None
        body_lines, in_body = [], False
        for ln in block:
            lm = LABEL_RE.match(ln)
            if lm and not in_body:
                label = lm.group(1).strip()
                if label in META_LABELS:
                    cur = label
                    meta[label] = lm.group(2).strip()
                    continue
                in_body = True
                body_lines.append(ln)
                continue
            if in_body:
                body_lines.append(ln)
                continue
            if not ln.strip():
                cur = None              # blank line ends a wrapped field only
                continue
            if cur is not None:         # continuation of a wrapped field
                meta[cur] += " " + ln.strip()
            else:
                in_body = True
                body_lines.append(ln)

        yield {
            "id": int(m.group(1)),
            "title": m.group(2).strip(),
            "meta": meta,
            "body": "\n".join(body_lines).strip(),
            "source": source,
        }


def parse_status(raw, flags):
    if not raw:
        flags.append("status-missing")
        return "open", None, None, None
    m = STATUS_RE.match(raw.strip())
    if not m:
        flags.append("status-unrecognised")
        return "open", None, raw.strip(), None
    status = m.group(1).lower()
    rest = m.group(2).strip()

    # Split marker-region from free-text resolution FIRST. The resolution text
    # very often contains a date ("staged to skill-updates/2026-08-14/",
    # "applied in weekly review 2026-03-04") that is NOT the resolution date.
    # Reading a date from anywhere in the line silently invented a wrong
    # `resolved` value for 356 archived entries during testing.
    prefix, resolution = rest, None
    for dash in ("—", " -- ", " - "):
        if dash in rest:
            prefix, resolution = rest.split(dash, 1)
            resolution = resolution.strip()
            break

    dm = ISO_DATE_RE.search(prefix)
    resolved = dm.group(1) if dm else None
    hint = None
    if status != "open" and not resolved:
        flags.append("resolved-date-missing")
        hm = ISO_DATE_RE.search(resolution or "")
        if hm:
            hint = hm.group(1)          # candidate only — never authoritative
            flags.append("resolved-date-hint-in-text")
    if resolution is None and resolved:
        resolution = prefix[dm.end():].strip(" (),—-") or None
    if rest.count("(") != rest.count(")"):
        flags.append("status-unbalanced-parens")
    if status == "open" and rest:
        flags.append("open-with-trailing-text")
    return status, resolved, resolution, hint


ABSORB_RE = re.compile(
    r"\b(?:or\s+)?(?:addition to|added to|extend|extension of|fold into|part of)\s+"
    r"([a-z0-9][a-z0-9._-]*)", re.I)


def parse_skill(raw, area, known_skills, flags):
    """Return (skill_list, proposes_skill_list, area, qualifiers).

    `skill` = existing skill(s) this observation improves.
    `proposes_skill` = new skill(s) it argues for.
    They are independent: an observation may do both ("could extend an
    existing skill, but the angle is distinct enough to stand alone"), or
    either alone. Forcing one field to carry both is what left such entries
    with no skill at all.
    """
    if not raw:
        flags.append("skill-missing")
        return [], [], area, {}

    nm = NEW_SKILL_RE.match(raw.strip())
    if nm:
        rest = nm.group(1).strip()
        pm = re.match(r"^(.*?)\s*\((.*)\)\s*$", rest)
        cand = (pm.group(1) if pm else rest).strip().strip('"')
        qual = pm.group(2).strip() if pm else None
        absorbs = []
        if qual:
            am = ABSORB_RE.search(qual)
            if am and (not known_skills or am.group(1) in known_skills):
                absorbs = [am.group(1)]
                qual = None
        quals = {cand: qual} if qual else {}
        if not SKILL_NAME_RE.match(cand):
            flags.append("candidate-name-unparseable")
            return absorbs, [], area, {"_unparsed": [rest]}
        return absorbs, [cand], area, quals

    names, quals = [], {}
    # Two nesting levels: ";" separates qualified groups, "," separates names
    # within a group. A qualifier trailing a multi-name group is ambiguous —
    # it may apply to the whole group or only the last name — so flag it.
    for group in split_top_level(raw, ";"):
        gm = re.match(r"^(.*?)\s*\((.*)\)\s*$", group)
        body = (gm.group(1) if gm else group).strip()
        gqual = gm.group(2).strip() if gm else None
        subnames = split_top_level(body, ",")
        if len(subnames) > 1 and gqual:
            flags.append("group-qualifier-ambiguous")
        for part in subnames:
            pm = re.match(r"^(.*?)\s*\((.*)\)\s*$", part)
            name = (pm.group(1) if pm else part).strip()
            qual = (pm.group(2).strip() if pm else None) or (
                gqual if len(subnames) == 1 else None
            )
            if name.lower() in ("all skills", "all", "any skill"):
                name = "all-skills"
                flags.append("skill-all-skills-sentinel")
            if not SKILL_NAME_RE.match(name):
                flags.append("skill-name-unparseable")
                quals.setdefault("_unparsed", []).append(part)
                continue
            if known_skills and name not in known_skills and name != "all-skills":
                flags.append("skill-name-unknown")
            names.append(name)
            if qual:
                quals[name] = qual
        if gqual and len(subnames) > 1:
            quals.setdefault("_group", []).append(f"{body} -> ({gqual})")

    # clean single-skill case: promote the qualifier into an empty area field
    if len(names) == 1 and not area and len(quals) == 1 and names[0] in quals:
        return names, [], quals[names[0]], {}
    if quals:
        flags.append("skill-qualifiers-need-review")
    return names, [], area, quals


def to_record(entry, known_skills):
    flags = []
    meta = entry["meta"]
    status, resolved, resolution, hint = parse_status(meta.get("Status", ""), flags)
    skills, proposes, area, quals = parse_skill(
        meta.get("Skill", ""), meta.get("Phase/Area", "").strip(), known_skills, flags
    )
    if skills or proposes:
        flags[:] = [f for f in flags if f != "skill-missing"]
    d = meta.get("Date", "").strip()
    if d and not ISO_DATE_RE.match(d):
        flags.append("date-not-iso")
    if not entry["body"]:
        flags.append("body-empty")
    # Trailing text on an OPEN status line ("OPEN — handed to session X") is a
    # note, not a resolution. Keep it, but never under `resolution`, which
    # consumers read as "what was done".
    status_note = None
    if status == "open" and resolution:
        status_note, resolution = resolution, None
    return {
        "id": entry["id"],
        "title": entry["title"],
        "status": status,
        "type": meta.get("Type", "").strip() or None,
        "skill": skills,
        "proposes_skill": proposes,
        "area": area or None,
        "date": d or None,
        "session_context": meta.get("Session context", "").strip() or None,
        "resolved": resolved,
        "resolved_hint": hint,
        "resolution": resolution,
        "status_note": status_note,
        "reference": meta.get("Reference file", "").strip() or None,
        "skill_qualifiers": quals or None,
        "flags": flags,
        "body": entry["body"],
        "source": entry["source"],
    }


def y(v):
    """Emit a YAML scalar. JSON string syntax is a valid YAML subset."""
    return json.dumps(v, ensure_ascii=False)


def render(rec):
    fm = [
        "---",
        f"id: {rec['id']}",
        f"title: {y(rec['title'])}",
        f"status: {rec['status']}",
    ]
    if rec["type"]:
        fm.append(f"type: {rec['type']}")
    fm.append("skill: [" + ", ".join(y(s) for s in rec["skill"]) + "]")
    if rec["proposes_skill"]:
        fm.append("proposes_skill: [" + ", ".join(y(c) for c in rec["proposes_skill"]) + "]")
    if rec["area"]:
        fm.append(f"area: {y(rec['area'])}")
    if rec["date"]:
        fm.append(f"date: {rec['date']}")
    if rec["session_context"]:
        fm.append(f"session_context: {y(rec['session_context'])}")
    if rec["resolved"]:
        fm.append(f"resolved: {rec['resolved']}")
    elif rec["resolved_hint"]:
        fm.append(f"resolved: null   # candidate from body text: {rec['resolved_hint']} — unconfirmed")
    if rec["resolution"]:
        fm.append(f"resolution: {y(rec['resolution'])}")
    if rec.get("status_note"):
        fm.append(f"status_note: {y(rec['status_note'])}")
    if rec["reference"]:
        fm.append(f"reference: {y(rec['reference'])}")
    if rec["skill_qualifiers"]:
        fm.append("skill_qualifiers:")
        for k, v in rec["skill_qualifiers"].items():
            fm.append(f"  {k}: {y(v if isinstance(v, str) else '; '.join(v))}")
    if rec.get("override_reason"):
        fm.append(f"migration_override: {y(rec['override_reason'])}")
    needs = sorted(set(rec["flags"]) & REVIEW_FLAGS)
    if needs:
        fm.append(f"migration_note: {y('needs review: ' + ', '.join(needs))}")
    fm.append("---")
    return "\n".join(fm) + "\n\n" + rec["body"] + "\n"


def id_floor_from(paths):
    hi = 0
    for p in paths:
        for root, _, files in os.walk(p):
            for f in files:
                if f.endswith(".md"):
                    try:
                        with open(os.path.join(root, f), encoding="utf-8") as fh:
                            for ln in fh:
                                m = ENTRY_RE.match(ln)
                                if m:
                                    hi = max(hi, int(m.group(1)))
                    except OSError:
                        pass
                mm = re.match(r"^(\d+)-", f)
                if mm:
                    hi = max(hi, int(mm.group(1)))
    return hi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--check", action="store_true", help="parse and report only")
    ap.add_argument("--convert", action="store_true", help="write output files")
    ap.add_argument("--out")
    ap.add_argument("--id-floor-from", action="append", default=[])
    ap.add_argument("--known-skills")
    ap.add_argument("--overrides", help="JSON file of manual resolutions, keyed by id")
    args = ap.parse_args()

    known = set()
    if args.known_skills and os.path.isdir(args.known_skills):
        known = {d for d in os.listdir(args.known_skills)
                 if os.path.isdir(os.path.join(args.known_skills, d))}

    overrides = {}
    if args.overrides:
        with open(args.overrides, encoding="utf-8") as fh:
            overrides = {k: v for k, v in json.load(fh).items() if not k.startswith("_")}

    records, seen = [], {}
    for path in args.logs:
        with open(path, encoding="utf-8") as fh:
            for entry in parse_entries(fh.read(), os.path.basename(path)):
                rec = to_record(entry, known)
                ov = overrides.get(str(rec["id"]))
                if ov:
                    for k, v in ov.items():
                        if k == "_resolves":
                            rec["flags"] = [f for f in rec["flags"] if f not in v]
                        elif k == "_reason":
                            rec["override_reason"] = v
                        else:
                            rec[k] = v
                if rec["id"] in seen:
                    rec["flags"].append("duplicate-id")
                seen[rec["id"]] = rec["source"]
                records.append(rec)

    print(f"parsed {len(records)} entries from {len(args.logs)} file(s)")
    counts = {}
    for r in records:
        for f in set(r["flags"]):
            counts[f] = counts.get(f, 0) + 1
    if counts:
        print("\nflags:")
        for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
            print(f"  {v:5d}  {k}")
    else:
        print("\nflags: none")
    needs_review = [r for r in records if set(r["flags"]) & REVIEW_FLAGS]
    print(f"\nneeds human review: {len(needs_review)}/{len(records)}")
    print(f"parsed losslessly:  {len(records)-len(needs_review)}/{len(records)}")

    if not args.convert:
        return

    out = args.out or "observation-log"
    os.makedirs(out, exist_ok=True)
    for r in records:
        fn = f"{r['id']:04d}-{slugify(r['title'])}.md"
        with open(os.path.join(out, fn), "w", encoding="utf-8") as fh:
            fh.write(render(r))

    floor = max([r["id"] for r in records] + [id_floor_from(args.id_floor_from)])
    arch = os.path.join(out, "archive")
    os.makedirs(arch, exist_ok=True)
    with open(os.path.join(arch, ".id-floor"), "w") as fh:
        fh.write(f"{floor}\n")

    print(f"\nwrote {len(records)} files to {out}/")
    print(f"id floor: {floor}  (-> {os.path.join(arch, '.id-floor')})")
    flagged = [r for r in records if set(r["flags"]) & REVIEW_FLAGS]
    if flagged:
        print(f"\n{len(flagged)} file(s) carry migration_note and need review:")
        for r in flagged:
            why = ", ".join(sorted(set(r["flags"]) & REVIEW_FLAGS))
            print(f"  #{r['id']:<5} {why:<42} {r['title'][:56]}")
    info = [r for r in records if set(r["flags"]) - REVIEW_FLAGS]
    if info:
        print(f"\n{len(info)} file(s) recorded extra detail (no action needed): "
              f"skill qualifiers preserved in `skill_qualifiers`")


if __name__ == "__main__":
    main()
