# Skill families — the sibling check and the carrier pattern

Load triggers: resolving an observation's siblings (skill families); partially actioning a multi-skill observation (carrier pattern)

The core skill requires the sibling check at write time and the carrier
pattern for a partial action (How to Log; Acting on Observations). This
file holds the family registry's form, the coherence models, the fallback
when no registry exists, and the carrier protocol in full. The log's
layout and the id snippet are in `observation-log.md`.

## Contents

- Skill families and the sibling check
- Partially actioning a multi-skill observation — the carrier pattern

## Skill families and the sibling check

Where several skills implement one idea — the same methodology for
different tools, the same structure for different subjects, the same
companion pattern for different base skills — the shared part drifts by
default, because each member is maintained only in the sessions that use
it and nobody looks at the set (measured in real libraries: a rule
applicable to every member of a five-skill family present in one; a rule
whose own text says it "applies to any file-writing script" present in
one of four). Nobody removed anything; some members grew and others did not.

**Why the check has to be a write-time step rather than a habit.** An
insight found while using one member usually applies to the rest, and
nothing in the ordinary workflow asks — so `skill:` collapses to the one
skill in front of you, and the divergence has no symptom until a drift
audit reads two members side by side, months later. The `skill:` field
is already a list; the mechanism exists, the *check* does not, and a list
field with no rule to populate it collapses to a single value. Four
parts, in increasing cost:

**1. Declare the families and the pattern groups —**
`skill-observations/skill-families.md`. The registry holds two kinds of
grouping, and conflating them is what makes it either block publication
or ship references nobody can use:

| Kind | Defined by | Members may cross-reference? | Shared rules live |
|---|---|---|---|
| **Family** | the same tool, or a core skill and its companions | yes — a user of one has reason to load the others | in the members (per the coherence model) |
| **Pattern group** | the same shape — one companion per tool, one dossier per subject — with no reason for a user of one to have another | **never** — a sibling paragraph naming the others is a defect, published or not | in cross-cutting principles |

Group skills by what a user of one would also need, not by what they
look alike. Propagation and cross-referencing are different relationships:
a pattern group earns the sibling check at write time (the "could this
sentence survive removing the tool name?" test, below, is exactly what
such a group is good for) and no cross-references; a family earns both.

**A skill can belong to more than one grouping** — typically a per-tool
family and a core/companion family at once — and the registry records
each membership separately rather than forcing a single home. The
sibling check (part 2) runs against **every** family and every pattern
group the target belongs to, not just the first one it resolves to.

Each entry carries the members and the load-bearing second column:
**what is shared versus what is legitimately member-specific.** Without
that column every observation looks like it might apply everywhere and the
check generates noise instead of signal. Record the *coherence model* for
each FAMILY too, because it decides what "fixing drift" means (a pattern
group has no coherence model — there is no shared text to keep in sync):

| Coherence model | Meaning | Fixing drift means |
|---|---|---|
| `synced-duplicates` | each member is self-contained (e.g. published standalone) and shared sections are kept in sync | edit every member |
| `shared-core` | one skill holds the common material; the others load it as a companion | edit the core once, check the pointers |

```markdown
## [group name]
**Kind:** family | pattern group
**Members:** skill-a, skill-b, skill-c
**Coherence model:** synced-duplicates | shared-core   # families only
**Shared:** [the material every member should carry]
**Member-specific:** [what legitimately differs, and why]
```

Duplication is sometimes correct and absence is not always drift — that is
exactly what the shared/member-specific split records.

**2. Logging-time check** (SKILL.md, "How to Log"). Before writing an
observation, resolve the target against the registry — against every
family and every pattern group it appears in, since membership is
plural. For each sibling in each of them, either add it to `skill:` or
state in the body why it does not apply (an insight shared across a
PATTERN group lands in cross-cutting principles, per the table above).
**No registry yet, or the target is not in it?** The check is still
required: scan the installed skill names for a
shared prefix, suffix or subject (`*-extras` companions, per-tool
implementations of one method, per-subject dossiers), do the evaluation
against whatever set that yields, and propose the registry entry. Two
cheap tests decide the verdict:

- Could this sentence survive having the tool's, client's or subject's
  name removed? If yes it belongs to every sibling.
- Does the rule declare its own generality ("this applies more broadly",
  "not specific to X")? That phrasing is the cheapest possible propagation
  signal and needs a mechanism that notices it — treat it as an automatic
  multi-skill flag rather than a stylistic aside.

**An absence claim inherits the scope of the search that produced it.**
The installed names a session can see are the user scope plus the
project it runs in. A skill scoped to another project, and the generator
source a project copy is rendered from (a tool-owned directory rendered
into `.claude/skills/`), are invisible from here, so "no installed skill
covers this" is a blind spot until those scopes have been searched — and
a narrow scope never invents a skill, it only misses real ones. Before
writing `proposes_skill:`, a `none` in `siblings_checked:`, or a target as
missing, search the other scopes by the problem as well as by the name —
a proposal is named after the task that surfaced it, and the skill that
already solves it rarely shares the name — and record in
`siblings_checked:` which scopes were searched: "not found" is a finding
only together with where you looked (Session Start step 6). Enumerate the
scopes by glob rather than a recursive `find`, which over a projects root
full of worktrees runs for minutes, and guard the enumeration: an empty
result tells you about the instrument before the library.

```bash
root="[PROJECTS ROOT]"   # absolute path of the directory holding the user's repositories
[ -d "$root" ] || { echo "SWEEP BROKEN — projects root $root does not exist"; exit 1; }
list=$(for d in "$root"/*/.claude/skills/*/ "$root"/*/*/.claude/skills/*/; do [ -f "$d/SKILL.md" ] && echo "${d%/}"; done)
n=$(printf '%s\n' "$list" | grep -c .); p=$(for d in "$root"/*/ "$root"/*/*/; do [ -d "$d" ] && echo; done | wc -l | tr -d ' ')
echo "project skills: $n (in $p directories under $root, two levels deep)"
printf '%s\n' "$list" | grep "/<skill-name>$"                                            # by name: the bare name, any plugin: prefix dropped
printf '%s\n' "$list" | while IFS= read -r d; do if [ -n "$d" ]; then grep -Il -i -- "<term from the body>" "$d/SKILL.md" || :; fi; done   # by problem; a non-match is not an error
```

Globs two levels under the root, one `grep` per project skill — bounded
by the skills found, never by the tree beneath them. `project skills: 0`
over a root that holds directories is an answer about this machine only
if those directories are the repositories you meant; `0 directories` is
a wrong root. Add the equivalent directory of any other tool the user
runs skills from (its project-level skills directory, in place of
`.claude/skills`); the activation block pins the root as
`[PROJECTS ROOT]`, substituted at install like `[ABSOLUTE PATH]`. Run the
sweep before a `proposes_skill:` write, and name its root and count in
`siblings_checked:`.

**3. Record the verdict** in `siblings_checked:` — the field makes an
absent judgement visible (core, How to Log). Because the
field is frontmatter, the cheap scan (`observation-scan.md`) can report "N observations
logged without a sibling check" without reading a single body. Where a
skill already relies on "the write is the enforcement", a new rule that
writes nothing is the odd one out and should be suspected on that basis.

**Recording the verdict is not recording its evidence.** The field makes
the absence of the *ritual* visible, not the absence of the *grounds*, and
once the ritual is habitual a specific-sounding verdict can be an
assumption that reads like a checked one. The asymmetry decides where the
ground goes: a sibling wrongly included costs one redundant paragraph at
the next review; a sibling wrongly excluded leaves the family silently and
for good, because nothing downstream ever acts on a negative verdict. So
every exclusion names what it rests on — the file and section read in that
sibling — or says `assumed`, and the review opens an `assumed` sibling
before accepting the exclusion. Example:
`siblings_checked: "list-commands: render, pick, close — render added; pick excluded (pick.md §2, selects by stable id); close excluded (assumed)"`.

**4. Propagation and drift audit at review time** — `weekly-review.md`,
Steps 3 and 4.

## Partially actioning a multi-skill observation — the carrier pattern

`status:` is per-observation, but `skill:` is a list, so the lifecycle
field is coarser than the work it tracks. When one session legitimately
acts on only a subset of the listed skills — a release session owning one
skill while a parallel review owns the rest — both plain moves are wrong:
left `open`, another session may re-apply the finished portion; marked
`actioned`, the unfinished portions silently leave every future review
queue. Split the record along the work's seams instead:

1. **While the partial work is in progress**, note the claim in the body:
   "portion X being applied by session Y — do not re-apply." The claim is
   what protects the in-flight portion from a parallel session.
2. **On completion**, mark the observation `actioned` with a `resolution:`
   naming exactly which portions were applied.
3. **In the same turn**, log a carrier observation holding the remaining
   portions: only the outstanding skills in its `skill:` list, a body
   stating it carries the unapplied remainder of the original (cite the
   original's id), and the substance the outstanding portions need —
   never just a pointer, since the original is about to archive.
4. **Reviews treat carriers as first-class.** A carrier enters the work
   queue like any other open observation; nothing about its provenance
   defers or demotes it.

Principle: when a record's lifecycle field is coarser than the work it
tracks, every state transition tells some consumer a lie — split the
record along the work's seams rather than overloading the status.
