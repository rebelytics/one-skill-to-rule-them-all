# One Skill to Rule Them All

_UPDATE AFTER THREE MONTHS OF USING THIS: The meta-skill has **logged and applied over 600 improvements across my 40 skills**, all of which were themselves created based on observations by the meta-skill._

**The meta-skill that builds and improves all your skills, including itself.**

Creating skills is powerful but time-consuming. And the skills that do get built stay frozen: they never learn from how you actually use them.

Task Observer fixes both problems. It's a skill that runs alongside your work, watches what you do, and does two things:

1. **Creates new skills for you** — it spots repeating patterns in your work and drafts skill candidates automatically, so you get skills without the upfront effort of writing them from scratch
2. **Improves your existing skills** — it notices corrections you make, preferences you express, and gaps in your current skills, then suggests specific updates

You work normally. It watches. Your skill library grows and gets better over time.

## What it does

Task Observer monitors your work sessions and looks for three things:

1. **Corrections and adjustments** — if you adjust the AI's output or steer it in a different direction, that's a signal that a skill could be clearer or more complete
2. **Gaps no skill covers yet** — if you're doing something manually that could be systematised, the observer flags it as a candidate for a new skill
3. **Its own blind spots** — the observer watches itself too, capturing improvements to its own methodology as you use it

At the end of each session, it produces a structured observation log: what it noticed, which skills are affected, and specific suggested improvements. You review, approve, and your skills evolve.

Some observations reveal patterns that aren't specific to one skill. These get captured as **cross-cutting principles** in a separate file — and new skills are automatically checked against them whenever they're created or updated. The more you use the system, the higher the quality floor across your whole skill library.

## Who it's for

You don't need to be a developer. If you use skills in any capacity (for writing, research, client work, analysis, content creation, anything) and you want those skills to get better over time instead of staying frozen, this is for you.

It's particularly valuable if you've built multiple skills and want a systematic way to maintain and improve them without manually auditing each one. But it's equally useful if you don't have any skills yet: the observer will start identifying and drafting them for you.

## How it works

**The best way to get started with this work setup in any environment is probably to grab the skill, readme and user guide, feed them to your AI and let it guide you towards the best setup for your particular environment** - No matter which AI system you use. As long as skills are supported, you should be able to use this approach with some adjustments.

The observer doesn't modify your skills directly. It produces recommendations that you review. You stay in control of what changes and when.

**In Claude Cowork (including Dispatch) or Claude Code in the desktop app:** Full experience. The observer writes observation logs to your filesystem, so improvements persist between sessions and can be actioned easily. Observations land in `[your shared folder]/skill-observations/`; proposed skill updates land in `[your shared folder]/skill-updates/`. You don't normally need to look at these directly — Claude handles them — but they're there if you want to inspect what's been captured.

**In Claude.ai web or Claude Chat in the desktop app / mobile app:** Handoff doc mode. Since there's no filesystem access, the observer produces a structured handoff document at the end of your session that you can use to update your skills manually.

## Compatibility

**Tested and designed for:**
- Claude Cowork (full experience with filesystem access)
- Claude Dispatch
- Claude.ai web interface (handoff doc mode)
- Claude mobile app (handoff doc mode)
- Claude Code in the desktop app

**Expected to work but untested:**
- Claude Code without desktop app — the methodology and format should translate directly, but I haven't verified it in practice

**Versions for other environments created by users:**
- Codex version by AllstarGER: [https://github.com/AllstarGER/one-skill-to-rule-them-all](https://github.com/AllstarGER/one-skill-to-rule-them-all)

**Potentially compatible with caveats:**
- Other Agent Skills-compatible platforms (ChatGPT, Gemini CLI, Cursor, etc.) — the skill uses Claude-centric concepts like `<available_skills>` and skill-creator references that other systems would need to interpret or adapt. The SKILL.md format is cross-platform, but the content assumes Claude's architecture.

If you try it on another platform, please let me know how it goes. Issues and pull requests welcome.

## Quick start

1. I recommend that you give the content of this repo (skill, readme and user guide) to the AI system of your choice and let it guide you towards the ideal configuration for your individual setup.
2. Read the user guide at [https://github.com/rebelytics/one-skill-to-rule-them-all/blob/main/USER-GUIDE.md](https://github.com/rebelytics/one-skill-to-rule-them-all/blob/main/USER-GUIDE.md)
3. Make sure that the skill loads in all sessions where it's needed (I solved this via an instruction in my CLAUDE.md file)
4. Try to remember to ask "Any observations logged" when you finish a session (I do this every time I archive a session). Often, the skill then finds additional improvement potential that it didn't log before.
5. Schedule a recurring review session that applies all open observations. Mine runs Monday, Wednesday and Friday morning, but you should adapt this to your needs.

## The self-improving part

This is the detail that makes the task observer truly beautiful in my opinion. Because it runs during every session and observes all active skills — including itself — it captures improvements to its own methodology over time.

If it misses something, or if its observation format could be clearer, or if it's triggering in contexts where it shouldn't — it notices, and it logs that too. The skill that improves all your skills also improves itself.

## Contributing

This is an early release. If you use it, I want to hear from you:

- **Bug reports and feature requests:** Open an issue
- **Observations about the observer:** If the skill captures something interesting about its own behaviour, I'd love to see it
- **Platform compatibility reports:** Tried it somewhere other than Claude? Tell me what happened

## License

This work is licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).

You're free to use, adapt, and redistribute — even commercially — as long as you give appropriate credit.

## Security audit

[![Oathe Security](https://img.shields.io/endpoint?url=https%3A%2F%2Faudit-engine.oathe.ai%2Fapi%2Fbadge%2Frebelytics%2Fone-skill-to-rule-them-all&style=for-the-badge&logo=data:image/svg%2Bxml;base64,PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHZpZXdCb3g9JzAgMCAyNCAyNCcgZmlsbD0nd2hpdGUnPjxwYXRoIGQ9J00xMiAyQzkuMjQgMiA3IDQuMjQgNyA3djNINmMtMS4xIDAtMiAuOS0yIDJ2OGMwIDEuMS45IDIgMiAyaDEyYzEuMSAwIDItLjkgMi0ydi04YzAtMS4xLS45LTItMi0yaC0xVjdjMC0yLjc2LTIuMjQtNS01LTV6bTMgMTBIOVY3YzAtMS42NiAxLjM0LTMgMy0zczMgMS4zNCAzIDN2M3onLz48L3N2Zz4=&labelColor=000000&cacheSeconds=3600)](https://oathe.ai/report/rebelytics/one-skill-to-rule-them-all)

---

**Created by [Eoghan Henn](https://rebelytics.com)**
