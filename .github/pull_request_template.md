<!-- Thank you. CONTRIBUTING.md describes how pull requests are reviewed and credited. -->

**What this changes and why**

**Kind of change** — tick one:
- [ ] New behaviour
- [ ] Rewording of existing text (the substance is unchanged)
- [ ] Relocation of existing text (moved, not changed)

**Checks**
- [ ] Every command or snippet in the change was run, literally, from a clean shell (say which shell).
- [ ] `skills/task-observer/SKILL.md` stays within its line ceiling (`core_max_lines` in its frontmatter), or the description says what pays for the added lines; a change that trims the core lowers the ceiling to the new count in the same commit (the validator fails when the ceiling sits more than 3 lines above the core).
- [ ] Any new heading in a `skills/task-observer/references/` file has an entry in that file's Contents list.

**Related issues** — `closes #N` for each issue this resolves, one keyword per issue.
