# Bounded slice — the entry path

Load triggers: a bounded slice runs (the offer in Session Start step 3, or a request to review the N oldest open entries)

A slice bounds the work, so its entry cost is bounded too. This file is
loaded instead of the whole of `weekly-review.md`, and that file's sections
are read one at a time, when the slice reaches them. Read a section from
its heading to the next step's heading (`grep -n` the heading, then read
that range). A section that sends you to another section, or a case this
file does not name, loads that section as well. Every rule in a section
read still binds: this file orders the reads, it replaces none of them.

**What a slice is.** A review of the N oldest OPEN entries, and it runs
as a review, not a glance. **Selection:** the N oldest by `date:`, then
id, leaving out parked entries and those asked and unanswered
(`weekly-review.md`, Approval policy, "An escalation is recorded on the
entry"), which the record lists once under "Waiting for the user" — and
re-asks, as a yes-or-no with the recommendation, each such entry whose
last ask was in the previous review, appending the re-ask to its
`escalated:` field; one re-asked and still unanswered is parked (Approval
policy). **Run for the slice:** Steps 3, 5 and 6 over its entries, and the
gate for the skills it stages. For each skill the slice stages, also list
the open entries naming it (`bash scripts/skill-load.sh "[ABSOLUTE PATH]"
<skill-name> --query-only`) and read the titles of those outside the
slice: the staged text stays consistent with them, or the record names
the conflict. They are checked for contradiction only, never reported as
reviewed. **Run for the whole log whatever the slice:** Step 1's integrity
checks (duplicate id, contiguity, header conformance, the inbox drain) and
Step 6's re-scan against the Step 1 list — a slice that skips them leaves
the log unchecked for as long as slices are all that run. **Record:**
`reviews/<date>-slice/REVIEW.md`, the Step 7 template with a first line
"Bounded slice: N of M open — ids …", and the steps not run named (Step 4,
the promotion pass); entries outside the slice are never reported as
reviewed. **Timestamp:** Step 8 with `rec` set to the slice's record,
bound to an outcome like a full review.

**The order, and the section of `weekly-review.md` each step reads:**

1. **Queue and integrity, whole log.** Step 1 from "Drain the observation
   inbox" up to "Staged-work reconciliation gate": the drain and harvest,
   the queue built from the files, the list kept on disk, the duplicate-id,
   contiguity and header checks. Then select the slice as above.
2. **Bodies and routing, slice only.** Step 3, for the slice's entries.
   An entry that needs the user's decision also reads Approval policy.
3. **Apply, only where the slice stages something.** "Staged-work
   reconciliation gate" for each skill it stages, then Step 5 and, at
   delivery, "Delivering updated skills". A slice that stages nothing
   reads none of them.
4. **Re-scan and mark, whole log.** Step 6.
5. **Record.** The Step 7 template ("Weekly Skill Review Complete").
6. **Timestamp.** Step 8, with `rec="reviews/$d-slice"`.
