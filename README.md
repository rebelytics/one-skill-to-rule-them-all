# One Skill to Rule Them All

**The meta-skill that builds and improves all your skills, including itself.**

Creating Claude skills is powerful but time-consuming. And the skills that do get built stay frozen — they never learn from how you actually use them.

Task Observer fixes both problems. It's a Claude skill that runs alongside your work, watches what you do, and does two things:

1. **Creates new skills for you** — it spots repeating patterns in your work and drafts skill candidates automatically, so you get skills without the upfront effort of writing them from scratch
2. **Improves your existing skills** — it notices corrections you make, preferences you express, and gaps in your current skills, then suggests specific updates

You work normally. It watches. Your skill library grows and gets better over time.

## What it does

Task Observer monitors your work sessions and looks for three things:

1. **Corrections and adjustments** — if you adjust Claude's output or steer it in a different direction, that's a signal that a skill could be clearer or more complete
2. **Gaps no skill covers yet** — if you're doing something manually that could be systematised, the observer flags it as a candidate for a new skill
3. **Its own blind spots** — the observer watches itself too, capturing improvements to its own methodology as you use it

At the end of each session, it produces a structured observation log: what it noticed, which skills are affected, and specific suggested improvements. You review, approve, and your skills evolve.

## Who it's for

You don't need to be a developer. If you use Claude skills in any capacity — for writing, research, client work, analysis, content creation, anything — and you want those skills to get better over time instead of staying frozen, this is for you.

It's particularly valuable if you've built multiple skills and want a systematic way to maintain and improve them without manually auditing each one. But it's equally useful if you have zero skills — the observer will start identifying and drafting them for you.

## How it works

No configuration required to get started. Drop the SKILL.md into your skills directory and it activates automatically during task-oriented sessions. It reads the available skills in your environment, watches how they perform during your work, and logs observations using a structured format.

The observer doesn't modify your skills directly. It produces recommendations that you review. You stay in control of what changes and when.

**In Cowork:** Full experience. The observer writes observation logs to your filesystem, so improvements persist between sessions and can be actioned immediately.

**In Claude.ai web/mobile:** Handoff doc mode. Since there's no filesystem access, the observer produces a structured handoff document at the end of your session that you can use to update your skills manually.

## Compatibility

**Tested and designed for:**
- Claude Cowork (full experience with filesystem access)
- Claude.ai web interface (handoff doc mode)

**Expected to work but untested:**
- Claude Code — the methodology and format should translate directly, but I haven't verified it in practice

**Potentially compatible with caveats:**
- Other Agent Skills-compatible platforms (Codex CLI, Gemini CLI, Cursor, etc.) — the skill uses Claude-centric concepts like `<available_skills>` and skill-creator references that other systems would need to interpret or adapt. The SKILL.md format is cross-platform, but the content assumes Claude's architecture

If you try it on another platform, please open an issue and tell me.

## Quick start

1. Download `SKILL.md` from this repository
2. Add it to your skills:
   - **Cowork / Claude.ai:** Upload as a custom skill via Settings → Capabilities → Skills
   - **Claude Code:** Place in your skills directory (e.g., `~/.claude/skills/task-observer/SKILL.md`)
3. Work normally. The observer activates automatically during task-oriented sessions
4. Review the observation log at the end of your session
5. Apply the improvements you agree with to your other skills

## The self-improving part

This is the detail that makes the task observer different from a linter or a review checklist. Because it runs during every session and observes all active skills — including itself — it captures improvements to its own methodology over time.

If it misses something, or if its observation format could be clearer, or if it's triggering in contexts where it shouldn't — it notices, and it logs that too. The skill that improves all your skills also improves itself.

## Contributing

This is an early release. If you use it, I want to hear from you:

- **Bug reports and feature requests:** Open an issue
- **Observations about the observer:** If the skill captures something interesting about its own behaviour, I'd love to see it
- **Platform compatibility reports:** Tried it somewhere other than Cowork or Claude.ai? Tell me what happened

## License

This work is licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).

You're free to use, adapt, and redistribute — even commercially — as long as you give appropriate credit.

---

**Created by [Eoghan Henn](https://rebelytics.com)**
