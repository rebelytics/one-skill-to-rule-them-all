# task-observer-flush

A turn-end guard for task-observer. When a turn used tools and wrote nothing to
`skill-observations/observation-log/` or `checkpoints.log`, it adds one line
beneath the answer and reminds the next turn to flush pending observations (or
append a `no observations` line to `checkpoints.log`).

Install from a terminal Claude Code session:

```
/plugin marketplace add rebelytics/one-skill-to-rule-them-all
/plugin install task-observer-flush@one-skill-to-rule-them-all
```

Choose the user scope. Verified in Claude Code terminal sessions; whether the
hook runs in Cowork sessions, which load the plugins enabled on the account,
and in the desktop app's Code tab is being tested.
