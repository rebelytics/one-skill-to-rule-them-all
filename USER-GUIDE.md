# Getting Started with the task-observer meta-skill (aka "One skill to rule them all")

This guide includes practical tips for getting value out of the meta-skill. It's based on my own daily usage of the skill across Cowork, the web interface, and the mobile app.

The meta-skill was primarily designed for Cowork, so these tips focus on that environment. If you use the skill in other environments, I expect most of the ideas to still apply. Please just adapt them where needed. And if you could report back to me your experience in other environments, that would be amazing.

## Where the skill runs

Once you've uploaded the skill via Settings → Capabilities in your Claude account, it's available in all chats (web interface, mobile app, desktop app) and also in the Cowork and Code tabs of the desktop app. Its full potential can be exploited in Cowork tasks.

## Using the skill in chats

You can use the meta-skill in regular chats, and I sometimes do: for example, when I start a conversation on my phone or via the web interface. The meta-skill will log observations during the conversation, but unlike in a Cowork session, it won't be able to write them to a shared storage.

You'll need to ask for a handoff doc at the end of the session, or the skill might guide Claude to offer one proactively as the conversation winds down. You can then take that handoff doc to the next session or, even better, to a Cowork task.

I developed the first versions of this skill in the Claude web interface before moving to Cowork, but the need for a shared storage was what pushed me there. If you see value in the meta-skill, it's likely that you'll end up using Cowork too.

## Setting up your shared folder

Once you start your first task in Cowork after installing the meta-skill, make sure that you select a shared folder. For the skill to work in its current form, you always need to use the same folder.

I started with an empty folder just for Claude Cowork, and it turned into a thriving knowledge base within days. If you prefer to give Claude access to a folder that already has files in it, that's also fine: no risk, no fun.

**Important:** Always select the folder at the beginning of every task. At the time of writing, I'm not aware of a way to add the folder after the task has started. This is an annoying limitation and I often have to create a handoff doc and start a new task because I forget to add the folder at the beginning of a task.

## Checking whether the skill has loaded

Once you've started a Cowork task by giving your first instructions or some context about the work, you can check in the right sidebar which skills have been invoked. If you think the current task has skill creation or improvement potential but you don't see the task observer, ask Claude directly why the skill hasn't loaded. It should then guide you towards a better setup.

## Dual-layer activation

The task observer needs to be active at the start of a session to automatically log observations in the background, but you can always invoke it later and ask Claude to analyse the entire conversation for skill creation or improvement potentials. The skill can activate on its own by matching your task description against its triggers, but this isn't always reliable: Claude is mainly focused on your task, not on loading background skills.

The more reliable approach is a dual-layer setup: the skill's own triggers plus a direct instruction in your CLAUDE.md file telling Claude to load the task observer at the start of every task-oriented session. The meta-skill itself will guide you towards setting this up, and the same approach works for any other skill you want to load consistently (so keep this in mind for the future).

## How the skill works during a session

Once the skill is loaded, it starts logging observations in the background without interrupting your work. This defensive design is intentional: the skill stays out of your way.

Be aware that this means the skill won't always push skill creation and improvement opportunities on you proactively. If you want it to be more aggressive, that's a good reason to start editing it and developing your own version of the meta-skill (more on that below).

## Checking in on observations

One thing I do frequently is ask towards the end of a session: "Any observations logged?" Claude then gives me an overview of everything it captured. You can also prompt Claude to do a deeper analysis of the session to find observations it might have missed.

If you want to browse the observation log yourself, you can find it at `[your shared folder]/skill-observations/log.md`. You don't normally need to look at it directly (Claude handles that), but it's there if you're curious.

## The cross-cutting principles file

As observations accumulate, some of them reveal principles that aren't specific to one skill but apply across your whole library. For example, "every skill with rules should have a mechanism to enforce them" isn't about any single skill: it's about all of them.

The task observer captures these as cross-cutting principles in a separate file. When skills are later created or updated, Claude checks them against these principles automatically. This is another source of compounding value: the more you use the system, the higher the quality floor across all your skills.

## Open-source vs internal skills

The task observer distinguishes between two types of skills:

**Open-source skills** are methodology-driven and project-agnostic. They capture workflows and processes that would be useful to anyone in your field. The default bias is towards open-source: if a skill could go either way, the meta-skill will try to strip out the specifics and generalise.

**Internal skills** contain information specific to you, your clients, or your projects. Personal preferences, proprietary processes, project context: anything that wouldn't make sense outside your own work.

This distinction matters because the open-source/internal boundary is also a confidentiality boundary. The skill has built-in safeguards across multiple layers to prevent confidential data from leaking into open-source skills. If you work with clients or handle sensitive information, the system is designed to protect that: but it's worth knowing the distinction exists so you can tag observations correctly when prompted.

## The weekly review

The skill has a built-in weekly review cycle. If more than 7 days have passed since the last review and there are open observations waiting, Claude will trigger a comprehensive review at the start of your next task-oriented session.

What to expect when it triggers: Claude pauses to cross-check all open observations against all your skills, checks whether cross-cutting principles are being followed everywhere, applies the improvements it can, and presents you with a summary of what changed and what needs your attention. It's thorough: the review covers your entire skill library, not just the skills mentioned in individual observations.

I've never actually reached this threshold, because I normally update skills more regularly than once a week. But it's there as a safety net to make sure observations don't pile up indefinitely.

## The skill-creator

Claude has a built-in skill called `skill-creator` that handles the actual building and restructuring of skills. The task observer and the skill creator work hand in hand: the observer identifies what to build or improve, and the skill creator handles how.

Every time I feel like there are enough observations to act on, I start a quick skill improvement session in a Cowork task. I just tell Claude that I think it's time to improve a certain skill, or all skills that have observations waiting. Claude then creates updated versions that I can review before uploading them via Settings → Capabilities.

## Making the skill your own

If the skill isn't working the way you want (too passive, too aggressive, too passive-aggressive, missing things, surfacing things you don't care about) start editing it. This is now your meta-skill and you can adjust it however you like.

The easiest way to improve the skill is by talking about it directly with Claude. Explain what's not working and how it could work better. Claude and the meta-skill itself will guide you towards a better version.

## Getting kickstarted

One thing that will help you get going faster is to create some basic skills proactively, instead of waiting for the task observer to suggest new skills to you.

A great candidate for everyone is a personal writing style skill. Ask Claude to analyse some of your writing samples (ideally your best pre-AI work) and create a writing style skill from that. From then on, every time you fix a draft from Claude, paste your edited version back in. The meta-skill will take care of logging observations to improve your writing style skill over time.

But the writing style skill is really just a very basic example. Over time, you will realise how the meta-skill can help you turn even your most complex processes and workflows into repeatable tasks.

I hope you have a lot of fun and that this approach has as much impact on your work as on mine. If you have any questions or comments whatsoever, I'm looking forward to hearing from you.

You know where to find me.

Thanks for reading,

Eoghan
