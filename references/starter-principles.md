# Starter Cross-Cutting Principles (optional seed)

This file is NOT the adopter's principles file. It is an optional seed:
a curated set of generic methodology principles, accumulated over a long
run of the task-observer loop and stripped of their provenance
(observation ids, dates, the originating setup's skill and client names).
The live file is `[workspace folder]/skill-observations/cross-cutting-principles.md`,
and its authority comes from the adopter's own evidence trail — so nothing
here takes effect until the adopter consciously imports it.

**When to read this file:** only at first run, when the Session Start
Protocol (SKILL.md, step 1) is creating the principles file and offers the
choice "start empty, or seed from the starter set". Never read it once the
adopter's own file exists.

**How to import:** copy the entries the adopter chooses (all, or a subset)
into the live file in the template format from `references/skill-authoring.md`,
setting `**Added:**` to the import date, `**Propagation:** opportunistic`,
`**Status:** active`, and adding `**Origin:** imported from starter set` to
each. The Origin marker is load-bearing: it tells every later review that
the entry arrived without local evidence, so the pruning pass can drop it
as freely as any single-observation rule. Imported principles that never
fire in the adopter's own work should be removed, not kept out of respect.

---

### 1. Open-source skills must include an open-source licence
**Applies to:** all open-source skills
**Requirement:** Include a recognised open-source licence statement in the
skill preamble and a corresponding `LICENSE` (or `LICENSE.txt`) file in the
skill directory. Any commonly recognised licence is acceptable — CC BY 4.0
for prose-heavy skills, MIT or Apache 2.0 for code-heavy skills, CC BY-SA
or the GPL family for stronger copyleft. The choice belongs to the skill's
author; the requirement is that there *be* a licence.

### 2. Open-source skills must include author attribution and a feedback pathway
**Applies to:** all open-source skills
**Requirement:** Include an attribution block at the top of the skill with
author name, contact link, licence statement, and a feedback and support
pathway (an issue tracker, a repository, a contact address). A published
skill without a route back to its author cannot improve from its readers.

### 3. Skills with rules must include a pre-flight verification step
**Applies to:** all skills with explicit rules or requirements
**Requirement:** Include a verification step where the agent re-reads the
skill's rules and checks its output against them before delivery. Rules
that are not enforced are suggestions.

### 4. Open-source skills must not contain client-identifying information
**Applies to:** all open-source skills
**Requirement:** No client names, project URLs, domain names, or proprietary
details anywhere in the skill, its references, or its examples. Enforce at
authoring time, at observation-logging time, and again at publication —
the log and the commit message are artefacts too.

### 5. Open-source skills must use tool-agnostic language, with concrete examples first
**Applies to:** all open-source skills
**Requirement:** Reference capabilities (browser access, file system access,
web search, a scheduler) rather than hard-coding a dependency on one
product. Skills are read by agents, not humans, and an agent pattern-matches
against concrete tool names in its toolset — so name the concrete tool for
the primary environment as an example, then give the generic fallback:
"In [environment], use `[tool]`. Elsewhere, use the available equivalent."
Generic-first phrasing optimises for human readability at the cost of
machine actionability.

### 6. Skills that generate structured output must be grounded in multiple real examples
**Applies to:** all skills that produce structured output (configs, markup,
code templates, data formats)
**Requirement:** Inform the skill with several real-world examples of the
target format, never a single instance — one example creates blind spots
around edge cases, advanced features, and format variations. Where the
resulting specification is too detailed for the skill body, put it in a
reference file and point to it.

### 7. Subagents must have complete inputs and verified outputs
**Applies to:** all skills that delegate content generation to subagents
**Requirement:** Use subagents for speed, but never let them guess at data
values. Safe delegations: validation, formatting checks, cross-reference
checks — anything where every required input can be passed in the brief.
Unsafe without safeguards: anything requiring live data. For data-bearing
tasks, the parent gathers the raw data first and passes it complete; a
subagent lacking a value writes a `[VERIFY: value not confirmed]`
placeholder rather than a plausible invention. After the return, the
parent verifies every concrete value against the source. Two sub-rules:
**(visualisation)** when delegating a chart or table, pass the exact data
in final display order — pre-filtered, pre-sorted — never a broader set the
subagent must rank, and spot-check content accuracy against the source,
not just layout; **(characterisation)** value-checking does not fire on
output stated as a *judgement* — a reported conflict, defect, risk or
readiness verdict has no unit to check — so any subagent claim that will
reach the user as a finding must be spot-checked by the parent at whatever
granularity makes it falsifiable (one grep is usually enough). Require
subagents to return locatable evidence (file, line, matched string) with
every claim; a claim without evidence is a claim to verify, not to relay.
A wrong value fails loudly when something computes with it; a wrong
characterisation is consumed by being agreed with, and agreement leaves no
trace.

### 8. Graceful tool-failure recovery
**Applies to:** all skills that use interactive tools
**Requirement:** When a tool interaction (a question widget, a form input)
is rejected or fails, recover conversationally without exposing internal
error states to the user. Rephrase in plain text and continue; do not
assume the user dismissed the interaction.

### 9. Match interaction modality to conversation energy
**Applies to:** all skills that gather user input
**Requirement:** Use structured tools (question widgets, forms) for
structured intake at the start of tasks. During free-flowing dialogue,
prefer plain-text questions. Do not downgrade a rich conversation to
multiple choice.

### 10. Small actionable sets are presented inline AND saved to file
**Applies to:** all skills that produce deliverable results
**Requirement:** When the result is a small set of actionable items (roughly
25 or fewer links, tasks, or similar), present it inline in the
conversation AND save it to a file — the file is the persistent record,
the inline list serves the immediate workflow. For larger sets the file is
primary and a summary is shown inline. Do not force the user to open a
file for something they will consume right now.

### 11. Skills require pruning, not just growth
**Applies to:** all skills
**Requirement:** During every review, look for content to remove with the
same deliberateness as content to add: rules from a single observation that
never recurred, sections never consulted, elaborate workflows users
consistently shortcut, complexity added "just in case" that never triggers.
A skill that only grows eventually becomes too heavy to be useful.

### 12. Use canonical identifiers from source data, never reconstruct from derived fields
**Applies to:** all skills that join, match, or cross-reference data from
more than one source
**Requirement:** Always use the canonical identifier from the source system.
Never reconstruct an identifier from a derived or transformed field
(generating a URL from a name, inferring an id from a slug). Reconstructed
identifiers introduce silent false positives that pass casual review and
corrupt the analysis. A curated lookup table is more work up front and
produces verifiable, auditable results.

### 13. Skills that read or write workspace files must maintain a reference index
**Applies to:** all skills that depend on, or produce, files in the shared
workspace
**Requirement:** Include a "Reference files" section listing the key files
with a one-line description each, maintained as a living index — added to
when files are created, pruned when they are superseded. Without it, a new
session loading the skill has no way to discover that relevant workspace
files exist, and the skill cannot leverage its own historical outputs.

### 14. Scheduled tasks invoke skills; they do not reimplement them
**Applies to:** all scheduled tasks that perform a workflow documented in a
skill
**Requirement:** A scheduled task's prompt loads the skill and follows its
instructions; it does not inline the workflow. The skill stays the single
source of truth: improvements flow into the scheduled execution
automatically, and the methodology remains shareable and versioned.
Duplicating skill content into a task prompt creates a maintenance fork
that drifts, and traps methodology in a non-shareable location.

### 15. Scheduled task prompts are lightweight orchestrators — intelligence lives in skills
**Applies to:** all scheduled tasks
**Requirement:** Task prompts carry no domain knowledge, source lists,
output formats, or filtering criteria; all of that belongs in a skill the
task invokes. Pattern: task prompt = "Load skill X, then follow its
instructions." This lets the skill improve independently of the task, be
invoked manually in ad-hoc sessions, and be observed by the task-observer
on every run. When creating any scheduled task, first ask whether a skill
exists for its domain — and if not, create the skill first.

### 16. Interrupted operations are partial operations — verify state before retrying
**Applies to:** all skills that perform bulk data operations or multi-step
mutations
**Requirement:** When an operation is interrupted, times out, or fails
partway, assume partial success, not total failure. Before retrying by the
same or another method, verify the current state — bulk inserts (some rows
succeeded), file operations (some files written), multi-step workflows
(some steps completed). The pattern: interrupt → verify state → adjust the
remaining work → proceed. Never assume a clean slate after a failure.

### 17. Never suggest manual typing of technical content as a workaround
**Applies to:** all skills and all conversational interactions
**Requirement:** When a tool-based workflow breaks (formatting, paste
failures, encoding), never suggest that the user manually type or
transcribe code, markup, structured data, or any technical content —
regardless of length. Find another machine-assisted route: a different
file format, a different delivery mechanism, a different tool. "It's only
N lines" is never a justification.

### 18. Browser automation is a costly last resort
**Applies to:** all skills that use or recommend browser automation
**Requirement:** Browser tool payloads compound as a conversation grows.
Any skill that uses them must document the cost, offer non-browser
alternatives where they exist, position the non-browser path as the
default when equally effective, and include a checkpoint for sessions that
exceed a small number of browser calls. Escalate strictly: fetch or search
tools first, the browser only after those have failed on a specific
source, and where the browser is needed but unavailable, wait for the user
rather than skipping, aborting, or inventing an alternative.

### 19. Skills recommending API access must note network-sandbox implications
**Applies to:** all skills that recommend direct access to a third-party
API
**Requirement:** Note that users in sandboxed environments (desktop agents,
corporate proxies) may need to allowlist the API's domain in their network
settings and restart the application before the call succeeds, and name
the domain(s) where known. Otherwise the user discovers the blocker
through failed requests mid-workflow.

### 20. Skills contain only behaviour-changing content
**Applies to:** all skills, open-source and internal
**Requirement:** Keep only content that changes the agent's behaviour at
execution time. Changelogs, version notes, history sections, credits,
self-narrating prose, and maintainer-facing context belong in a supporting
document, in commit history, or in a README — not in the skill. The test:
would removing this line change how the agent behaves? This does NOT cut
examples, anti-patterns, or worked scenarios — those are load-bearing for
rule adherence, because bare rules get violated more reliably than rules
with context. Every non-load-bearing line is token cost paid on every load
with no behavioural payoff.

### 21. Use agent-agnostic language in open-source skills
**Applies to:** all open-source skills
**Requirement:** Refer to the executing AI as "the agent" rather than by a
vendor's model name, except where the reference is genuinely specific to
that vendor: product names (an app, a CLI, a hosted chat), a config-file
naming convention, an architecture or API only that vendor has. Generic
references to the executor ("[model] does X", "tells [model] to") become
"the agent". This extends the tool-agnostic principle to actor references.
Internal skills that only ever run in one setup are exempt.

### 22. Verifying current vendor guidance requires a dated changelog check, not just the docs page
**Applies to:** all skills that verify or assert a third-party platform's
current guidance
**Requirement:** When a workflow confirms what a vendor currently
recommends, supports, or requires, check the vendor's dated changelog or
updates page — not only the documentation page (e.g. a search engine's
dated "updates" page alongside its docs). Fetched docs pages are cache
snapshots and have been observed serving week-stale versions missing new
properties; the changelog is dated and authoritative, and catches both a
stale fetch and changes since the skill was written. Corollary: any
"this property/change does not exist" claim about recently updated
documentation needs a second channel (changelog, raw fetch, or browser)
before delivery — channel staleness is the first hypothesis, not vendor
absence.

### 23. Never aggregate across structurally different segments
**Applies to:** all skills that report a metric summed, averaged, or ranked
over more than one segment (market, brand, client, instrument, template,
channel, time bucket)
**Requirement:** Before aggregating, check whether the segments are
structurally comparable — same instrument, same population size, same
denominator behaviour. If not, report per segment first, and aggregate
only with the heterogeneity stated. Aggregation is an editorial decision,
not a neutral default. The diagnostic: an aggregate over heterogeneous
segments always flatters one segment and buries another, **and the buried
one is usually the finding** — so when an aggregate produces a "weakness",
check whether a small segment is being drowned by a large one before
reporting it.

### 24. Fetch the instance before describing it
**Applies to:** all skills that describe, classify, or verify a specific
artefact — a URL, a DOM element, a host, a record, a file — from evidence
about it
**Requirement:** Before asserting what a specific artefact *is*, obtain the
artefact itself rather than reasoning from a signal that correlates with
it. Surface patterns are evidence *about* an artefact and get substituted
for it because they are already in hand while fetching costs a call; the
substitution is invisible in the output, because an inference from a
familiar-looking pattern reads exactly like a verified fact. Typical
errors: a matching DNS record read as proof a host served content when it
served a redirect; a URL sweep read as evidence of what links to those
URLs; character proximity in serialised HTML read as DOM containment; a
URL's shape read as its page type when the dataset carried a page-type
column. The diagnostic: name the evidence a claim rests on and ask whether
it is the artefact or a correlate; if a correlate, ask what fetching the
artefact would cost — usually one call. Two corollaries: where a dataset
already classifies the entity, read its field rather than re-deriving it;
where direct access is blocked, prefer another response-level channel
(an inspection tool, a rendered view) over an infrastructure-level signal.

### 25. One verified reason beats two, where the second is unchecked
**Applies to:** all skills that produce recommendations, advice, arguments,
or justifications
**Requirement:** Every supporting reason attached to a recommendation must
clear the same evidence bar as the recommendation itself. When a single
justification feels thin, state it more precisely rather than reaching for
a second; if a second reason cannot be checked in the moment, flag it as
unchecked or leave it out. The mechanism does not feel like invention: the
search for a second reason is a search for something *plausible that
points the same way*, and supporting reasons get a fraction of the
scrutiny precisely because they are not the load-bearing claim — yet they
are the part the reader has no independent way to check. A wrong
supporting reason transfers its unreliability to the sound claim beside
it. Corollary: before building an argument on figures from a document,
establish who authored them — inherited or third-party numbers deviate in
both directions and change which of them are worth contesting at all.
