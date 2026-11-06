# task-observer-flush (experimental)

**Experimental.** This plugin is shared for testing; see "Where it runs"
below before relying on it.

A turn-end guard for task-observer. When a turn used tools and wrote nothing to
`skill-observations/observation-log/` or `checkpoints.log`, it adds one line
beneath the answer and reminds the next turn to flush pending observations (or
append a `no observations` line to `checkpoints.log`).

Install from a terminal Claude Code session:

```
/plugin marketplace add rebelytics/one-skill-to-rule-them-all
/plugin install task-observer-flush@one-skill-to-rule-them-all
```

Choose the user scope.

## Where it runs

- **Claude Code in a terminal:** verified.
- **Cowork:** a terminal install never reaches Cowork, which loads the
  plugins enabled on your claude.ai account. Tried with the plugin enabled
  there: in a fresh cloud Cowork session no note appeared, and another
  hook plugin enabled the same way did not fire either, so Cowork does
  not appear to run these hooks. Reports from other setups are welcome.
- **The desktop app's Code tab:** unknown.

Please report what you see, whether it works or not, in a new issue in this
repository.
