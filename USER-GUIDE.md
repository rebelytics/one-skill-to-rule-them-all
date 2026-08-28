# Getting Started with the task-observer meta-skill (aka "One skill to rule them all")

This guide includes practical tips for getting value out of the meta-skill. It's based on my own daily usage of the skill across Claude Cowork, the web interface, Claude Code (only via the desktop app) and the mobile app. I've been using this skill for seven months now and it has logged more than 1200 observations across my 70 skills, most of which were applied as skill improvements. The majority of my 70 skills were themselves created based on observations by the meta-skill.

The best way to get started with this new work setup in any environment is to grab the skill, the reference files, the user guide and the readme file from the repo and feed them to the AI of your choice. It should then be able to guide you towards the best equivalent of this setup for your particular environment, no matter which system you use. As long as skills are supported, this approach should work with any AI system, with some adjustments.

The meta-skill was primarily designed for Claude Cowork, so these tips focus on that environment. If you use the skill in other environments, I expect most of the ideas to still apply. Please just adapt them where needed. And if you could report back to me your experience in other environments, that would be amazing.

The rest of this user guide focusses on Claude and specifically Claude Cowork, but again, most of this should be applicable to other environments.

## Where the skill runs

The skill is a multi-file bundle: `SKILL.md`, a `references/` folder that is loaded on demand, and a `scripts/` folder with two small helpers (the pre-3.0 log migration and the bundle validation gate). To install it, put all three into one folder, zip that folder, and upload it via Settings → Customize in your Claude account. Uploading the bare SKILL.md alone results in a degraded install — the skill still works, but will tell you which files are missing, and the automatic upgrade from a pre-3.0 log won't run without `scripts/` (see the Installation section of the readme for other environments).

Once you've uploaded the skill, it's available in all chats (web interface, mobile app, desktop app) and also in the Cowork and Code tabs of the desktop app. Its full potential can be exploited in Cowork tasks and Code sessions.

## Using the skill in chats

You can use the meta-skill in regular chats, and I sometimes do: for example, when I start a conversation on my phone or via the web interface. The meta-skill will log observations during the conversation, but unlike in a Cowork session, it won't be able to write them to a shared storage.

You'll need to ask for a handoff doc at the end of the session, or the skill might guide Claude to offer one proactively as the conversation winds down. You can then take that handoff doc to the next session or, even better, to a Cowork task or Code session.

I developed the first versions of this skill in the Claude web interface before moving to Cowork, but the need for a shared storage was what pushed me there. If you see value in the meta-skill, but you're mainly using Chat, it's likely that you'll end up using Cowork too.

## Setting up your shared folder

Once you start your first task in Cowork after installing the meta-skill, make sure that you select a shared folder. For the skill to work in its current form, you always need to use the same folder.

I started with an empty folder just for Claude Cowork, and it turned into a thriving knowledge base within days. If you prefer to give Claude access to a folder that already has files in it, that's also fine: no risk, no fun.

### What gets stored where

The meta-skill writes only to its own subdirectories of your shared folder:

- `[your shared folder]/skill-observations/` — the observation log (a folder, `observation-log/`, with one small file per observation and resolved ones under its `archive/`), the cross-cutting principles file, and a few small bookkeeping files the skill maintains (the last review date, a checkpoint marker, the skill-family registry)
- `[your shared folder]/skill-updates/` — staged versions of skill updates that are waiting for you to install them

Existing files in your shared folder are not modified by the observer. If you point the meta-skill at a folder that already contains client work or personal documents, those files stay where they are; the observer only reads from them when you ask Claude to use them in a task. Skill updates are also never installed automatically — they're staged in `skill-updates/` for you to review and install yourself.

## Checking whether the skill has loaded

Once you've started a Cowork task by giving your first instructions or some context about the work, you can check in the right sidebar which skills have been invoked. If you think the current task has skill creation or improvement potential but you don't see the task observer, ask Claude directly why the skill hasn't loaded. It should then guide you towards a better setup.

## Dual-layer activation

The task observer needs to be active at the start of a session to automatically log observations in the background, but you can always invoke it later and ask Claude to analyse the entire conversation for skill creation or improvement potentials. The skill can activate on its own by matching your task description against its triggers, but this isn't always reliable: Claude is mainly focused on your task, not on loading background skills.

The more reliable approach is a dual-layer setup: the skill's own triggers plus a direct instruction in your CLAUDE.md file telling Claude to load the task observer at the start of every task-oriented session. Make sure that instruction says to run the skill's Session Start Protocol, not just to load the skill — loading and executing are separate steps, and a session that loads the file and then stops has activated nothing. The meta-skill itself will guide you towards setting this up, and the same approach works for any other skill you want to load consistently (so keep this in mind for the future).

## How the skill works during a session

Once the skill is loaded, it starts logging observations in the background without interrupting your work. This defensive design is intentional: the skill stays out of your way.

Be aware that this means the skill won't always push skill creation and improvement opportunities on you proactively. If you want it to be more aggressive, that's a good reason to start editing it and developing your own version of the meta-skill (more on that below).

## Checking in on observations

One thing I do frequently is ask towards the end of a session: "Any observations logged?" Claude then gives me an overview of everything it captured. You can also prompt Claude to do a deeper analysis of the session to find observations it might have missed.

Over time, I got used to just asking about the logged observations every time I archive a task. I like to keep my task list clean, so I archive all tasks that are done and just do a quick check on the logged observations at the same time. This has proven to be the most reliable way to log as many relevant observations as possible.

If you want to browse the observations yourself, you'll find them at `[your shared folder]/skill-observations/observation-log/` — one small Markdown file per observation, each starting with a frontmatter header (status, skill, type, date) followed by the issue, the suggested improvement, and the principle. Resolved observations move to `observation-log/archive/`. You don't normally need to look at these directly (Claude handles that), but they're there if you're curious. Storing one file per observation, with the metadata in frontmatter, lets Claude scan just the headers to find what's open instead of re-reading the whole backlog — which keeps token usage low as observations pile up.

### Upgrading from a version before 3.0

Versions before 3.0.0 kept all observations in one file, `skill-observations/log.md`. Version 3.0.0 stores one file per observation. The first session that runs with the new version installed will notice the old file and convert it with a small script bundled in the skill — it checks the log first, reports anything it isn't sure about, and keeps the old file as `log.md.migrated` so nothing is lost. You don't need to do anything except say yes when asked; the details, including how to roll back, are in `references/migration.md`.

## The cross-cutting principles file

As observations accumulate, some of them reveal principles that aren't specific to one skill but apply across your whole library. For example, "every skill with rules should have a mechanism to enforce them" isn't about any single skill: it's about all of them.

The task observer captures these as cross-cutting principles in a separate file. When skills are later created or updated, Claude checks them against these principles automatically. This is another source of compounding value: the more you use the system, the higher the quality floor across all your skills.

## Open-source vs internal skills

The task observer distinguishes between two types of skills:

**Open-source skills** are methodology-driven and project-agnostic. They capture workflows and processes that would be useful to anyone in your field. The default bias is towards open-source: if a skill could go either way, the meta-skill will try to strip out the specifics and generalise.

**Internal skills** contain information specific to you, your clients, or your projects. Personal preferences, proprietary processes, project context: anything that wouldn't make sense outside your own work.

This distinction matters because the open-source/internal boundary is also a confidentiality boundary. The skill has built-in safeguards across multiple layers to prevent confidential data from leaking into open-source skills. If you work with clients or handle sensitive information, the system is designed to protect that: but it's worth knowing the distinction exists so you can tag observations correctly when prompted.

It is always your own decision if you want to open-source any of your skills at all, or if you prefer to keep them all to yourself.

## The weekly review (now possible via scheduled tasks)

The skill has a built-in weekly review cycle. If more than 7 days have passed since the last review and there are open observations waiting, Claude will offer to run a comprehensive review at the start of your next task-oriented session. It's a one-line offer, not an interruption: you can run the review right away or carry on with your task and let a later session (or a scheduled run) handle it.

What to expect when the review runs: Claude cross-checks all open observations against all your skills, checks whether cross-cutting principles are being followed everywhere, applies the improvements it can, and presents you with a summary of what changed and what needs your attention. It's thorough: the review covers your entire skill library, not just the skills mentioned in individual observations.

I only ever reached this threshold once, because I normally update skills more regularly than once a week. But it's there as a safety net to make sure observations don't pile up indefinitely.

Now, since Claude Cowork introduced scheduled tasks, I have an automatic skill review task that runs every Monday, Wednesday and Friday morning. It goes through the 20 to 30 open observations that normally accumulate from my work every two working days. This 3x per week cadence works perfectly for me at the moment.

## The skill-creator

Claude has a built-in skill called `skill-creator` that handles the actual building and restructuring of skills. The task observer and the skill creator work hand in hand: the observer identifies what to build or improve, and the creator handles how.

## Making the skill your own

If the skill isn't working the way you want (too passive, too aggressive, too passive-aggressive, missing things, surfacing things you don't care about) start editing it. This is now YOUR meta-skill and you can adjust it however you like.

The easiest way to improve the skill is by talking about it directly with Claude. Explain what's not working and how it could work better. Claude and the meta-skill itself will guide you towards a better version.

## Getting kickstarted

One thing that will help you get going faster is to create some basic skills proactively, instead of waiting for the task observer to suggest new skills to you.

A great candidate for everyone is a personal writing style skill. Ask Claude to analyse some of your writing samples (ideally your best pre-AI work) and create a writing style skill from that. From then on, every time you fix a draft from Claude, paste your edited version back in. The meta-skill will take care of logging observations to improve your writing style skill over time.

But the writing style skill is really just a very basic example. Over time, you will realise how the meta-skill can help you turn even your most complex processes and workflows into repeatable tasks.

I hope you have a lot of fun and that this approach has as much impact on your work as it has on mine. If you have any questions or comments whatsoever, I'm looking forward to hearing from you.

You know where to find me.

Thanks for reading,

Eoghan (rebelytics.com)
