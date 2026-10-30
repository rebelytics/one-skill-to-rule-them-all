# Open Skill Library

This is a list of open-source skills maintained with Task Observer. Skills are grouped by category and sorted alphabetically within each category.

A listing is not a security review: read a skill before you install it. This page only links to each skill's repository and never copies its files.

## Meta-skills

| Skill | What it does | Licence | Last skill update |
|---|---|---|---|
| [skill-publishing](https://github.com/rebelytics/skill-publishing) | Publishes agent skills as open-source repositories and keeps the published copies identical to the installed ones. | CC BY 4.0 | 2026-10 |
| [task-observer](https://github.com/rebelytics/one-skill-to-rule-them-all) | Watches your work sessions, logs where skills fall short, and turns the observations into reviewed skill updates. | CC BY 4.0 | 2026-10 |

## AI visibility strategy

| Skill | What it does | Licence | Last skill update |
|---|---|---|---|
| [ai-visibility-tracking-strategy-builder](https://github.com/rebelytics/ai-visibility-tracking-strategy-builder) | Builds and refines the prompt set and reporting structure for tracking how a brand appears in AI answers. | CC BY 4.0 | 2026-10 |
| [peec-ai-tracking-strategy-builder](https://github.com/rebelytics/peec-ai-tracking-strategy-builder) | Peec AI companion to the tracking strategy builder: project setup, writes and analysis in Peec AI. | CC BY 4.0 | 2026-10 |
| [searchviu-tracking-strategy-builder](https://github.com/rebelytics/searchviu-tracking-strategy-builder) | searchVIU companion to the tracking strategy builder: prompt sets, field mapping, validation and CSV handover. | CC BY 4.0 | 2026-10 |
| [sistrix-tracking-strategy-builder](https://github.com/rebelytics/sistrix-tracking-strategy-builder) | SISTRIX companion to the tracking strategy builder: AI tracker tags, CSV imports and update quotas. | CC BY 4.0 | 2026-10 |

## Tool companions (MCP servers)

| Skill | What it does | Licence | Last skill update |
|---|---|---|---|
| [peec-ai-mcp](https://github.com/rebelytics/peec-ai-mcp) | Companion skill for the Peec AI MCP server: reports, competitive analysis and reading Peec metrics correctly. | CC BY 4.0 | 2026-10 |
| [searchviu-mcp](https://github.com/rebelytics/searchviu-mcp) | Companion skill for the searchVIU MCP server: querying crawl reports, date filters, row caps and API passthrough. | CC BY 4.0 | 2026-10 |
| [sistrix-mcp](https://github.com/rebelytics/sistrix-mcp) | Companion skill for the SISTRIX MCP server: visibility, keyword, backlink and AI visibility data. | CC BY 4.0 | 2026-10 |

## Technical SEO

| Skill | What it does | Licence | Last skill update |
|---|---|---|---|
| [redirect-verification](https://github.com/rebelytics/redirect-verification) | Checks a reported redirect or link fix against its spec, using crawl data and targeted live requests. | CC BY 4.0 | 2026-10 |
| [translation-audit](https://github.com/rebelytics/translation-audit) | Audits translated titles, headings, descriptions and body content across the language versions of a website. | CC BY 4.0 | 2026-09 |

"Last skill update" is the month of the last commit on the default branch that touches the skill's own files: `SKILL.md`, `references/` or `scripts/`.

## Add your skill

Open a pull request that adds a row for your skill in the right category, in alphabetical order.

The criterion is that the skill is maintained with Task Observer. We judge that from the skill's content: it follows Task Observer's [skill-authoring guidelines](references/skill-authoring.md). If your skill diverges from them on purpose because you adjusted the guidelines in your own copy of Task Observer, say so in the pull request.

Requirements:

- The skill is in a public repository.
- It has an open licence: any OSI-approved licence or a Creative Commons licence.

If no category fits your skill, open a new one. Improvements to the existing categories are welcome.

## Staying listed

A skill stays listed while it is actively maintained: there has been a commit touching its skill files (`SKILL.md`, `references/`, `scripts/`) within the last three months. Changes to the README or other files do not count. A skill without such a commit moves to "Unmaintained" below, with the month it moved, and comes back when its skill files change again. The same rule applies to the maintainer's own skills. The list is checked regularly.

## Unmaintained

None at the moment.
