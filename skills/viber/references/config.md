# Config — Reading and Setting Viber's Own Behavior

The viber CLI resolves every run through one chain: **flag > env > project config > user config >
default**. Never hand-edit a config file; the CLI is the sole writer.

## Check where a value comes from

Before assuming any command's profile/format/census behavior:

```bash
viber config list            # every key: value, source layer, default
viber config get <key>       # one key with its layer
viber config path            # the files and plugin dirs (exists/absent)
```

Keys: `census`, `project`, `profile`, `format`, `telemetry`, `plugins`. Everything else (`out`, `force`,
`include`, `exclude`) is flag-only — refuse to write it; the CLI rejects it, and so should you.

## Set

```bash
viber config set <key> <value>          # project layer (default target)
viber config set <key> <value> --user   # only when the user asked for per-machine
viber config unset <key>                # removes from one layer; ack names what takes over
```

- Values: `profile` = minimal|standard|full · `format` = txt|json · `telemetry`/`plugins` = true|false ·
  `census` = path resolved against cwd.
- A bad current flag is the user's escape hatch: pass the flag; do not "fix" config mid-task.
- Yellow stderr warnings during any command mean a config layer was skipped — surface them, don't swallow.

## Telemetry

`telemetry=false` → `use`/`outcome` ack "telemetry disabled" and write nothing. Do not fake
invocations into the db by hand when disabled.

## Multi-project

`viber init` mints a short location-fingerprint **id** for a project and registers it (id → folder)
in the user `projects.json`; print and record the id — it is not sensitive. Resume from anywhere:
`viber --project <id> <cmd>`, or make it the default with `viber project use <id>` (then plain
`viber <cmd>` works on it). Selection: `-C` file > `--project` flag > `VIBER_PROJECT` env > the **nearest enclosing project**
(walks up from cwd) > the `project` saved default. An enclosing folder beats the default; pass
`--project` to override. The walk-up stops at a `.git` boundary (dir or worktree/submodule file), so a
nested checkout never borrows the parent's data.
The id is derived from the path, so a **moved** folder needs `viber project link <id> --to <newdir>`
(no guarantee — `viber project list` flags `missing`). `viber now <id> --details` shows location,
step, counts, last action.

## Plugins (internal, off by default)

`.viber/plugins/*.py` add commands only — they never shadow built-ins; broken files skip with
warnings. Enable only on explicit user decision (`viber config set plugins true`); state the
trust cost (repo-shipped code executes) before enabling, and never enable on your own initiative.
