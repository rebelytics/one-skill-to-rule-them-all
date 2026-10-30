---
id: 1
title: "fixture-notes: write note dates as YYYY-MM-DD"
status: open
type: open-source
skill: [fixture-notes]
proposes_skill: []
target_file: []
siblings_checked: "none: no family"
area: "entry format"
date: 2026-01-05
session_context: "fixture entry for the eval set"
parked_until:
resolved:
resolution:
reference:
commands_verified: none
next_actor:
use_evidence:
escalated:
---

**Issue:** Notes were added with spelled-out dates ("3 March"), which do
not sort and are ambiguous across years.

**Suggested improvement:** fixture-notes should require `YYYY-MM-DD`
dates in every new entry.

**Principle:** Dates in running logs are written in a sortable form.
