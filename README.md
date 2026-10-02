# task-observer - One Skill to Rule Them All

## The meta-skill that builds and improves all your skills, including itself.

**Why "One Skill to Rule Them All"?** The slogan doesn't claim this is the best skill. It couldn't be: a meta-skill is useless without the skills it watches over. It describes what Task Observer does: keep an eye on how all your other skills are working and suggest improvements. You decide which changes are installed.

This meta-skill has **logged over 1,600 observations across my 81 skills**, most of which were turned into skill improvements. The majority of my 81 skills were themselves created based on observations by the meta-skill.

The current version of task-observer also includes improvements from 69 different contributors, each credited as an author or co-author in the commit history, and its commits close 99 issues and pull requests. Without these contributions, the project wouldn't be half as good as it is today.

This meta-skill is a practical application of the [Augmented Expertise](https://www.rebelytics.com/augmented-expertise/) methodology, an AI framework for knowledge workers. However, users have reported successful integrations into their Hermes and Openclaw setups, so it works equally well with autonomous agents.

## Quick install

1. **From a terminal (Vercel's skills CLI, needs Node.js):** `npx skills add rebelytics/one-skill-to-rule-them-all --skill task-observer` — add `-g` to install it for all your projects.
2. **In the Claude apps (web, desktop, mobile, Cowork):** upload the `.skill` bundle from the latest release via Settings → Customize.
3. **Then activate it:** add the activation instruction from `references/environments.md` to your CLAUDE.md (or your platform's equivalent). Installing alone is not enough, because description matching under-triggers; see "Check that it actually runs" below.

## Why you should use task-observer

Creating skills is powerful but time-consuming. The skills that do get built stay frozen: they never learn from how you actually use them.

Task Observer fixes those problems. It's a meta-skill that runs alongside your work, watches what you do, and does two things:

1. **Identifies new skills for you** — it spots repeating patterns in your work and flags them as skill candidates, then helps you build them, so you get skills without staring at a blank page.
2. **Improves your existing skills** — it notices corrections you make, preferences you express, and gaps in your current skills, then suggests specific updates.

You work normally. It watches. Your skill library grows and gets better over time.

## The self-improving part

This is the detail that makes Task Observer truly beautiful in my opinion. Because it runs during every session and observes all active skills — including itself — it captures improvements to its own methodology over time.

If it misses something, or if its observation format could be clearer, or if it's triggering in contexts where it shouldn't — it notices, and it logs that too. The skill that improves all your skills also improves itself.

## What it does

Task Observer monitors your work sessions and looks for three things:

1. **Corrections and adjustments** — if you adjust the AI's output or steer it in a different direction, that's a signal that a skill could be clearer or more complete
2. **Gaps no skill covers yet** — if you're doing something manually or repeatedly that could be systematised, the observer flags it as a candidate for a new skill
3. **Its own blind spots** — the observer watches itself too, capturing improvements to its own methodology as you use it

During each session, it produces a structured observation log: what it noticed, which skills are affected, and specific suggested improvements. You review, approve, and your skills evolve.

Some observations reveal patterns that aren't specific to one skill. These get captured as **cross-cutting principles** in a separate log — and new skills are automatically checked against them whenever they're created or updated. The more you use the system, the higher the quality floor across your whole skill library.

The observer doesn't modify your installed skills. In an interactive review you approve each change; a scheduled review applies the observations that need no decision from you to staged copies only. Nothing goes live until you install the updated bundle, so you stay in control of what changes and when.

## How this differs from project memory

Claude Code Projects can write project memory on its own: when you correct a thread and tell Claude to remember the correction, it goes into that project's memory and later threads start with it. Those entries are notes the agent keeps to, scoped to one project, and they are deleted with the project.

Task Observer does a different job, and the two work best together. **Scope:** project memory records a fact or a pitfall for *this* project; Task Observer turns recurring friction into a change to a reusable skill, which then carries into every project that loads that skill. **Control:** project memory is written automatically and applied as an instruction; a Task Observer observation is a proposal, and a human review sits between the observation and the rule it becomes. Nothing changes a skill until you install the staged update.

The practical link: a pitfall you find yourself storing in project memory more than once, or in more than one project, is a Task Observer signal — it has stopped being about the project and started being about the skill.

## Who it's for

You don't need to be a developer. If you use skills in any capacity and you want those skills to get better over time instead of staying frozen, this is for you.

If you're a builder, you can easily integrate this skill, or even just the methodology, into your existing setup. Just point your agent at the repo and let it guide you towards the ideal implementation for your specific setup.

The task observer is particularly valuable if you've built multiple skills and want a systematic way to maintain and improve them without manually auditing each one. It's also useful if you don't have any skills yet: the observer will start identifying skill candidates for you and help you build them.

One honest boundary: the formal observation log and review cycle pay off most as your skill library and usage grow — many skills, parallel sessions, scheduled reviews. If you run a small setup with a handful of skills, your AI system's built-in memory features may cover much of the same ground with less overhead, and editing a skill directly is quick. The observer's value compounds with scale: adopt it early if you expect your library to grow, or come back to it when direct editing stops feeling manageable.

## How it works

**The best way to get started with this work setup in any environment is to grab the skill, readme and user guide, feed them to your AI and let it guide you towards the best setup for your particular environment** - No matter which AI system you use. As long as skills are supported, you should be able to use this approach with some adjustments. And even without skills, the methodology should work with any other type of knowledge base that your AI has access to.

## Installation

The skill is a small bundle: `SKILL.md`, the files in `references/` that are loaded on demand (this keeps the always-loaded part lean), and four helper scripts in `scripts/`. Installing only SKILL.md works, but runs degraded and isn't recommended — the skill will tell you which files are missing.

**Get the files:** download the `.skill` bundle attached to the latest release, or download the repo as a ZIP (Code → Download ZIP) / clone it and keep `SKILL.md`, `references/` and `scripts/` together.

**Claude (web interface, desktop app, mobile app, Cowork):** upload the `.skill` bundle via Settings → Customize (or put `SKILL.md`, `references/` and `scripts/` into one folder and zip that folder). The skill is then available in all chats and in Cowork tasks.

**Claude Code:** place the folder at `.claude/skills/task-observer/` (project-level) or in your user-level skills directory, preserving the `references/` and `scripts/` subfolders.

**Other systems:** keep the folder structure intact wherever your platform expects skills, and let your AI guide you (see "How it works" above).

**From the command line (Vercel's skills CLI):** `npx skills add rebelytics/one-skill-to-rule-them-all --skill task-observer`. This is the most-used install route — the skills.sh listing reports over 9,000 installs, a lower bound because the CLI's install telemetry is opt-out, and it carries independent security audits from Gen Agent Trust Hub, Socket and Snyk.

**Check that it actually runs.** Installing the files is not the same as activating the skill: description matching alone under-triggers, so add the activation instruction from `references/environments.md` to your CLAUDE.md (or your platform's equivalent) or install the session-start hook. Then verify in a *new* session — the session you install in cannot prove it — that the skill is invoked before the first tool call. The external tell if you skipped this: if `skill-observations/observation-log/` doesn't exist after a few sessions of real work, activation never happened.

## Claude environment notes

**In Claude Cowork (including Dispatch) or Claude Code in the desktop app:** Full experience. The observer writes observation logs to your filesystem, so improvements persist between sessions and can be actioned easily. Observations land in `[your shared folder]/skill-observations/observation-log/`, one small file each; proposed skill updates land in `[your shared folder]/skill-updates/`. Upgrading from a version before 3.0? The first session converts your old single-file log automatically (see the user guide). You don't normally need to look at these directly — Claude handles them — but they're there if you want to inspect what's been captured.

**In Claude.ai web or Claude Chat in the desktop app / mobile app:** Handoff doc mode. Since there's no filesystem access, the observer produces a structured handoff document at the end of your session that you can use to update your skills in a dedicated session.

## Compatibility

**Tested and designed for:**
- Claude Cowork (full experience with filesystem access)
- Claude Dispatch
- Claude.ai web interface (handoff doc mode)
- Claude mobile app (handoff doc mode)
- Claude Code in the desktop app

**Confirmed to work by users:**
- Claude Code without desktop app — the methodology and format translate directly - plenty of users have reported seamless experiences with this.

**Versions for other environments created by users:**
- Codex version by AllstarGER: [https://github.com/AllstarGER/one-skill-to-rule-them-all](https://github.com/AllstarGER/one-skill-to-rule-them-all) (based on an older version of task-observer)
- Please get in touch if you've open-sourced an adaptation of the meta-skill for another system or environment. I'm happy to include it here.

**Potentially compatible with caveats:**
- Other skills-compatible platforms (ChatGPT, Gemini CLI, Cursor, etc.) — the skill uses Claude-centric concepts like `<available_skills>` and skill-creator references that other systems would need to interpret or adapt. The SKILL.md format is cross-platform, but the content assumes Claude's architecture.
- Users have reported successful integrations into Openclaw and Hermes setups.

If you try it in another environment, please let me know how it goes. Issues and pull requests welcome.

## Quick start

1. Read the user guide at [https://github.com/rebelytics/one-skill-to-rule-them-all/blob/main/USER-GUIDE.md](https://github.com/rebelytics/one-skill-to-rule-them-all/blob/main/USER-GUIDE.md)
2. Give the content of this repo (skill, readme and user guide) to the AI system of your choice and let it guide you towards the ideal configuration for your individual setup.
3. Make sure that the skill loads in all sessions where it's needed (I solved this via an instruction in my CLAUDE.md file).
4. Try to remember to ask "Any observations logged?" when you finish a session (I do this every time I archive a session). Sometimes, the skill then finds additional improvement potential that it didn't log before.
5. Schedule a recurring review session that applies all open observations. Mine runs Monday, Wednesday and Friday morning, but you should adapt this to your needs.

## Contributing

This is an open-source project for the community. If you use it, I would love to hear from you:

- **Bug reports and feature requests:** Open an issue or a pull request, whichever you prefer — you are credited either way. See [CONTRIBUTING.md](CONTRIBUTING.md) for how reports become changes and how credit works.
- **Platform compatibility reports:** Tried it somewhere other than Claude? Tell me what happened.
- **Interesting use cases:** Have you come up with a creative way of using or improving Task Observer?
- **Integrations with other systems:** One user told me that they connected task observer to Obsidian. Do you have a similar story?

## License

This work is licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).

You're free to use, adapt, and redistribute — even commercially — as long as you give appropriate credit: Link to the original repo (https://github.com/rebelytics/one-skill-to-rule-them-all/) and name the author (Eoghan Henn / rebelytics.com).

## Further reading

If you want to learn more about the methodology behind this skill, please read the [Augmented Expertise manifesto](https://www.rebelytics.com/augmented-expertise/).

## Listed in

task-observer is indexed in these community lists and skill directories:

- [VoltAgent / awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills)
- [Get Claude Skills](https://www.getclaudeskills.com/skills/task-observer-rebelytics)
- [Claude Code Marketplaces](https://claudemarketplaces.com/skills/rebelytics/one-skill-to-rule-them-all/task-observer)
- [Surf Skills](https://surfskills.surf/s/rebelytics/one-skill-to-rule-them-all/task-observer)
- [BehiSecc / awesome-claude-skills](https://github.com/BehiSecc/awesome-claude-skills)
- [KIMI](https://www.kimi.ai/resources/claude-code-skills)
- [CorpusIQ — Hermes skills catalog](https://www.corpusiq.io/docs/hermes/skills/catalog/task-observer-setup)
- [SkillFoxx](https://skillfoxx.ru/en/skills/task-observer-one-skill-to-rule-them-all)
- [Zread](https://zread.ai/rebelytics/one-skill-to-rule-them-all)
- [TypingMind](https://www.typingmind.com/skills/rebelytics-task-observer)

It is also redistributed, unmodified and under CC BY 4.0, in [iamneilroberts/claude-skills](https://github.com/iamneilroberts/claude-skills).

## Recommended by

I would like to thank the following creators, platforms, publications, companies and kind people who have recommended task-observer to their audiences:

- Dan Kornas: [https://x.com/DanKornas/status/2074370062031462787](https://x.com/DanKornas/status/2074370062031462787)
- Kelli Hrivnak: [https://www.linkedin.com/posts/kellihrivnak_to-those-building-out-skills-in-claude-lets-share-7478433968837517312-UhPj/](https://www.linkedin.com/posts/kellihrivnak_to-those-building-out-skills-in-claude-lets-share-7478433968837517312-UhPj/)
- Maverick Maltin: [https://www.tiktok.com/@maverickgpt/video/7661705764901227807](https://www.tiktok.com/@maverickgpt/video/7661705764901227807)
- Claudia Faith: [https://levelupwithai.substack.com/p/this-is-how-you-use-claude-in-2026](https://levelupwithai.substack.com/p/this-is-how-you-use-claude-in-2026)
- Andrea Saez: [https://dreasaez.medium.com/your-ai-skills-are-silos-heres-how-to-fix-that-bdb04a507785](https://dreasaez.medium.com/your-ai-skills-are-silos-heres-how-to-fix-that-bdb04a507785)
- Aashish Pahwa: [https://www.instagram.com/p/DXwqpPQj62s/](https://www.instagram.com/p/DXwqpPQj62s/)
- Nick Saraev: [https://www.instagram.com/reels/DaN0yYtPzjY/](https://www.instagram.com/reels/DaN0yYtPzjY/)
- Peter Griffin AI: [https://www.instagram.com/reels/DavN_06t105/](https://www.instagram.com/reels/DavN_06t105/)
- Myriam Jessier: [https://www.linkedin.com/posts/myriamjessier_i-feel-like-i-am-part-of-an-mlm-sponsored-share-7483809490992140288-6Lwm/](https://www.linkedin.com/posts/myriamjessier_i-feel-like-i-am-part-of-an-mlm-sponsored-share-7483809490992140288-6Lwm/)
- Victor Dorneanu: [https://brainfck.org/t/self-improving-agents/](https://brainfck.org/t/self-improving-agents/)
- CORE.TODAY: [https://core.today/blog/task-observer-meta-skill](https://core.today/blog/task-observer-meta-skill)
- Tom Dörr: [https://x.com/tom_doerr/status/2072251701608784049](https://x.com/tom_doerr/status/2072251701608784049)
- Vaibhav Sisinty: [https://x.com/VaibhavSisinty/status/2063290847723192610](https://x.com/VaibhavSisinty/status/2063290847723192610)
- Evgeny Shkuratov: [https://www.instagram.com/reels/DaHqy6MApwN/](https://www.instagram.com/reels/DaHqy6MApwN/)
- Juan Pablo Rosso: [https://www.instagram.com/reels/Dayv8dvjeLi/](https://www.instagram.com/reels/Dayv8dvjeLi/)
- Johannes Manske: [https://www.linkedin.com/posts/johannesmanske_vor-8-wochen-war-ki-noch-sparringspartner-share-7461096580809547777-0ty7/](https://www.linkedin.com/posts/johannesmanske_vor-8-wochen-war-ki-noch-sparringspartner-share-7461096580809547777-0ty7/)
- Xavier Ting: [https://xaviertingai.com/tools/task-observer.html](https://xaviertingai.com/tools/task-observer.html)
- Lazy Owen (게으른 빌더): [https://lazyowen.com/guides/claude-skills-top5-0815](https://lazyowen.com/guides/claude-skills-top5-0815)
- Minhaj Rais: [https://justbeingresourceful.com/2026/08/21/5-claude-code-plugins-worth-installing-in-2026-and-the-fine-print-on-the-unlimited-tokens-claim/](https://justbeingresourceful.com/2026/08/21/5-claude-code-plugins-worth-installing-in-2026-and-the-fine-print-on-the-unlimited-tokens-claim/)
- Denghao (等號): [https://denghao.substack.com/p/5](https://denghao.substack.com/p/5)
- Erfan Iranshad: [https://erfaniranshad.ir/5-claude-code-plugins/](https://erfaniranshad.ir/5-claude-code-plugins/)
- Tech Future Atlas: [https://techfutureatlas.com/posts/t3_1tm887i/](https://techfutureatlas.com/posts/t3_1tm887i/)
- 球球不冲了: [https://www.binance.com/en/square/post/355189407349041](https://www.binance.com/en/square/post/355189407349041)
- AI LABS: [https://www.youtube.com/watch?v=jyLKRN36-Dc](https://www.youtube.com/watch?v=jyLKRN36-Dc)
- Aarush Jain: [https://medium.com/no-time/i-stopped-losing-hours-to-claude-errors-these-6-claude-skills-changed-everything-6814f594d29e](https://medium.com/no-time/i-stopped-losing-hours-to-claude-errors-these-6-claude-skills-changed-everything-6814f594d29e)
- gptsavyy: [https://www.instagram.com/reel/DbFs6QENr43/](https://www.instagram.com/reel/DbFs6QENr43/)
- Hudson Brendon: [https://gist.github.com/hudsonbrendon/818e84cd81bcc215a3ad00286b04af82](https://gist.github.com/hudsonbrendon/818e84cd81bcc215a3ad00286b04af82)
- IA IRL: [https://www.tiktok.com/@ia_irl/video/7665714151305547030](https://www.tiktok.com/@ia_irl/video/7665714151305547030)
- Ozzibig.ai: [https://www.tiktok.com/@ozzibig/video/7662484018075634976](https://www.tiktok.com/@ozzibig/video/7662484018075634976)
- Danielgpt2: [https://www.tiktok.com/@danielgpt2/photo/7663796072724172054](https://www.tiktok.com/@danielgpt2/photo/7663796072724172054)
- Doit.systemIA: [https://www.youtube.com/shorts/535GKrg1E08](https://www.youtube.com/shorts/535GKrg1E08)
- Erfan Yousefi: [https://codenight.ir/articles/claude-code-plugins](https://codenight.ir/articles/claude-code-plugins)
- MigueBaenaIA: [https://www.youtube.com/shorts/OBeoYZzHDcw](https://www.youtube.com/shorts/OBeoYZzHDcw)
- Santiago Cosme: [https://www.linkedin.com/posts/santiagocosme_5-skills-para-poner-90-ugcPost-7491131673254846465-SQAl/](https://www.linkedin.com/posts/santiagocosme_5-skills-para-poner-90-ugcPost-7491131673254846465-SQAl/)
- Skillselion: [https://skillselion.com/guides/task-observer-skill-claude-code-guide](https://skillselion.com/guides/task-observer-skill-claude-code-guide)
- Adele Newenham: [https://www.aiwithadele.com/guides/claude-code-plugins](https://www.aiwithadele.com/guides/claude-code-plugins)
- Hysen Labs: [https://hysenlabs.com/en/projects/rebelytics-one-skill-to-rule-them-all](https://hysenlabs.com/en/projects/rebelytics-one-skill-to-rule-them-all)
- Uday Sharma: [https://medium.com/@neuraldev/5-claude-code-plugins-that-take-your-setup-to-the-next-level-d5d61c2c5828](https://medium.com/@neuraldev/5-claude-code-plugins-that-take-your-setup-to-the-next-level-d5d61c2c5828)
- SnowTiger: [https://www.toutiao.com/article/7687548501114225192/](https://www.toutiao.com/article/7687548501114225192/)
- Divad: [https://divadsanders.medium.com/i-fixed-everything-wrong-with-claude-code-5-best-claude-plugins-c1af8d813ee1](https://divadsanders.medium.com/i-fixed-everything-wrong-with-claude-code-5-best-claude-plugins-c1af8d813ee1)
- Abhijay Arora Vuyyuru (AI Action Letter): [https://abhijayvuyyuru.substack.com/p/dont-use-claude-code-without-these](https://abhijayvuyyuru.substack.com/p/dont-use-claude-code-without-these)
- The Ai Impact: [https://www.theaiimpact.co/guides/claude-code-add-ons](https://www.theaiimpact.co/guides/claude-code-add-ons)
- Bill Prin: [https://x.com/Bill_Prin/status/2103189962640552198](https://x.com/Bill_Prin/status/2103189962640552198)
- Jake Austin: [https://www.snapchat.com/@itsjakeaustin3/spotlight/W7_EDlXWTBiXAEEniNoMPwAAYaGlrcndlbmJsAaDY8w3vAaDY8nNPAAAAAw](https://www.snapchat.com/@itsjakeaustin3/spotlight/W7_EDlXWTBiXAEEniNoMPwAAYaGlrcndlbmJsAaDY8w3vAaDY8nNPAAAAAw)

If I forgot to list your recommendation here, please let me know or submit it via a PR in the same format as the others.

## Security audit

[![Oathe Security](https://img.shields.io/endpoint?url=https%3A%2F%2Faudit-engine.oathe.ai%2Fapi%2Fbadge%2Frebelytics%2Fone-skill-to-rule-them-all&style=for-the-badge&logo=data:image/svg%2Bxml;base64,PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHZpZXdCb3g9JzAgMCAyNCAyNCcgZmlsbD0nd2hpdGUnPjxwYXRoIGQ9J00xMiAyQzkuMjQgMiA3IDQuMjQgNyA3djNINmMtMS4xIDAtMiAuOS0yIDJ2OGMwIDEuMS45IDIgMiAyaDEyYzEuMSAwIDItLjkgMi0ydi04YzAtMS4xLS45LTItMi0yaC0xVjdjMC0yLjc2LTIuMjQtNS01LTV6bTMgMTBIOVY3YzAtMS42NiAxLjM0LTMgMy0zczMgMS4zNCAzIDN2M3onLz48L3N2Zz4=&labelColor=000000&cacheSeconds=3600)](https://oathe.ai/report/rebelytics/one-skill-to-rule-them-all)

---

**Created and maintained by [Eoghan Henn](https://rebelytics.com), improved by its community of users**
