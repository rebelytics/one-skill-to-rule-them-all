# Contributing

Thank you for using the skill and for taking the time to report what you
found. This page describes how contributions have actually been handled,
so you know what to expect.

## Open an issue or a pull request — whichever you prefer

Both are welcome, and you are credited either way. Pick the one that
costs you less:

- **An issue** is perfect when you have observed a failure, a gap or a
  wrong assumption. The most useful reports say what happened, why the
  current text did not prevent it, and — if you have one — what you think
  the fix is. Many issues on this repository already contain the exact
  wording that ended up in the skill.
- **A pull request** is perfect when you have a tested change. Keep it
  focused on one problem; say plainly whether it relocates existing text,
  rewords it, or adds new behaviour, because those are reviewed
  differently.

You do not need to do more than that. The maintainer turns issues into
changes, rebases pull requests onto the current branch, merges, and
releases. Nobody is asked to "send a PR instead" — a good report is a
complete contribution.

Before filing, a quick search of existing issues *and* pull requests
saves everyone a round trip: if something adjacent exists, reference it
and say how yours differs.

## How you are credited

- A **merged pull request** keeps your authorship on the commit.
- An **issue that supplied the fix** — wording, a command, a design —
  is implemented by the maintainer with a `Co-authored-by:` trailer
  naming you, so the contribution shows on your profile.
- An **issue that supplied the report** without a fix design gets a
  `Reported-by:` trailer.
- Where a pull request identifies a real problem but the maintainer
  resolves it differently, the commit explains why and credits you as the
  reporter.

Release notes mention contributors by handle. If you would rather not be
credited, say so in the issue.

## What kind of change goes where

- **Improvements to the core skill** — fixes, clarifications, missing
  cases, portability, enforcement — are merged into the skill itself,
  via a release branch that is run for a while before it reaches `main`.
- **Permanent variants** — a port to another platform, a different
  philosophy of what the skill should do — live best as a fork, linked
  from the README so people can find them. A separate repository for
  something that should converge splits the issues and the users; a
  branch for something that will stay parallel does the same in reverse.

If you are not sure which yours is, open an issue and ask.

## How changes are reviewed

- A pull request is reviewed against **its own base branch**, not against
  the maintainer's local install, which is usually ahead of the published
  version. If that gap matters for your change, the maintainer pushes the
  delta first and asks you to rebase.
- A change that **rewords or relocates** existing text is checked for two
  things separately: that the substance survived, and that the
  *enforcement machinery* survived — checkpoints, assertions, mandatory
  writes, defaults. Compression tends to remove enforcement first,
  because it reads as repetition. Any net-new behaviour in a "pure
  restructuring" change must be declared in the description; undeclared
  behaviour changes are the one thing that delays a merge.
- **Embedded commands are run, literally, from a clean shell** before
  they are merged. If your change adds or edits a snippet, saying where
  you ran it helps.
- Nothing in the skill may require fetching an external URL at run time,
  and nothing may contain information that identifies a real client or
  project.

## Licence

Contributions are accepted under the repository's licence (CC BY 4.0).
By contributing you agree that your change is distributed under it, with
credit as described above.
