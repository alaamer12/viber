# Viber Config — The Settings Chain

> Owns the CLI's own configuration: the precedence chain, the five keys, the files, the env names, the `config` command family, and the internal plugin surface. The census (`viber.json`) owns skill knowledge — never settings; settings own tool behavior — never knowledge. Diagram: none yet (open item).
> Shipped as `skills/viber/references/config.md`.

## 1. Overview

Every viber run resolves its behavior through one chain, owned by a single pure
resolver (`core/settings.py`):

```text
flag  >  env (VIBER_*)  >  project config  >  user config  >  built-in default
```

The chain exists so an agent or a project can state a preference once, visibly,
instead of repeating flags on every call — while an explicit flag always keeps
command. Nothing here is hidden: `viber config list` shows every key, its value,
the layer it came from, and its default; `viber config path` shows the files.

### Core Principle

**One visible chain, one writer.** The CLI is the sole writer of settings, exactly
as it is of the census; a damaged read never bricks a run; a write never damages a
file it cannot parse.

## 2. The Keys

| Key | Type | Default | Layers | Why it earns the chain |
|---|---|---|---|---|
| `census` | path | `""` (auto-detect) | flag, env, project, user | odd layouts (insource `manager.py` split) get a config answer, not env archaeology |
| `profile` | minimal / standard / full | `standard` | flag, env, project, user | "this project always wants full" |
| `format` | txt / json | `txt` | flag, env, project, user | agent-driven projects want json everywhere |
| `telemetry` | bool | `true` | env, project, user | A/B the regime, CI runs that must write nothing |
| `plugins` | bool | `false` | env, project, user | the trust switch for drop-in commands (section 6) |

Deliberately **flag-only, never configurable**: `out`, `force`, `include`,
`exclude`. A global `force` disarms the one overwrite guard the emit layer has;
a global `out` hijacks stdout from every command; a global include/exclude would
raise `ProfileError` on unrelated commands. The `CHAIN` table in
`src/viber/core/settings.py` is the single visible statement of this, and it
generates the `config set` key whitelist — `viber config set force true` fails
with the closed-set choice error (exit 2); it does not write a key nothing reads.

Relative paths (a `census` value) resolve against **cwd**, never against the
config file's own directory — matching how the census itself is discovered.

## 3. The Files

```text
<project-root>/.viber/.data/config.json   project layer — shared, committed-able
<user config dir>/config.json             user layer — per machine, never shared
```

The user dir is the platform app dir (`typer.get_app_dir("viber")`) unless
`VIBER_CONFIG_HOME` says otherwise. `VIBER_CONFIG` points the project layer at
any explicit file (the escape hatch, and the test seam).

Both files are JSON with the five keys (plus unknown keys that survive round-trips,
the same `extra="allow"` doctrine as the census). No comments: the CLI is the
writer, and `config list` is the reader.

## 4. Validation Policy — the Asymmetry, Argued

- **Reads: warn-and-fallthrough.** A value that fails to parse prints a yellow
  stderr warning and that one key drops to the next layer. A typo in `profile`
  must not brick every command — because the doctrine forbids hand-editing the
  file to repair it, a hard-fail would force exactly the thing it forbids.
- **Writes: strict.** `config set` into a file it cannot parse refuses outright
  (exit 1) rather than destroying the other settings in it.

This is a stated deviation from census load behavior (which hard-fails); it holds
because a census is shared knowledge whose corruption must be loud, while settings
are per-layer tool preferences each of which can be skipped alone.

## 5. The `config` Command Family

| Command | Answers |
|---|---|
| `viber config list` | every key: value, source layer, default (`-f json` for machines) |
| `viber config get <key>` | the effective value and where it came from |
| `viber config set <key> <value> [--user \| --path F]` | write one layer (project unless told) |
| `viber config unset <key> [--user \| --path F]` | remove from one layer; the ack names the value and layer that takes over |
| `viber config path` | the files and plugin dirs, with exists/absent marks |

Env names: `VIBER_CENSUS VIBER_PROFILE VIBER_FORMAT VIBER_TELEMETRY VIBER_PLUGINS`
(values) plus `VIBER_CONFIG`, `VIBER_CONFIG_HOME` (locators). No implicit per-command
env prefixes — discoverable beats clever.

## 6. The Plugin Surface — Internal, Opt-in, Add-only

The CLI is assembled through a registry seam (`cli/registry.py`): built-in command
modules register first, command families come in as sub-apps (`config` is that
pattern's first customer), and drop-in plugins register last, from
`.viber/plugins/*.py` and `<user dir>/plugins/*.py`.

A plugin is a plain module exporting `COMMANDS: dict[str, callable]`; handlers use
the same global-option contract as built-ins. The policy is **add-only**: a plugin
can never shadow a built-in or another plugin (first wins, collision skipped with a
warning), and a broken plugin is skipped, not fatal — the CLI must survive its own
extensions.

**Trust boundary, stated plainly:** a plugin file is Python executed with the
invoking user's permissions on every run. Cloning a repo therefore ships code, not
data. That is why `plugins` defaults to `false`, why enabling it is an explicit
visible line in the project config (or an env var someone typed), and why this is
an **internal** surface: this project's own extension points, not a community
distribution story. `VIBER_PLUGINS=0` kills it instantly.

## 7. How It Connects

| Component | Relationship |
|---|---|
| `census` / PIPELINE | Knowledge vs behavior — the census never holds settings; settings never hold skill data |
| `structure.md` | `.viber/.data/config.json` sits beside the census and telemetry; project settings follow the committed-knowledge default, with only generated, environment, and declared-private paths ignored (section 5 there) |
| `supervision.md` | settings files live under `.viber` like all Viber state; the umbrella never reroutes them elsewhere |
| emit/profile layer | `profile`/`format` config values feed the same `-P`/`-f` machinery — no second shaping path |
| telemetry | `telemetry false` gates the two writers (`use`, `outcome`); readers already handle an absent db |
| `display.md` | presentation is **not** a chain key: display capability is per-machine (flag/env), chain keys are per-project policy |

## 8. Rules

- The chain order is law in exactly one place (`core/settings.py`); no command re-resolves.
- Explicit flag beats everything; that is how a user escapes their own defaults.
- CLI sole writer; hand-editing is drift, not workflow.
- Reads warn and fall through; writes refuse or succeed, never half-write.
- Console capability never enters the chain (`display.md` owns it) — a committed config must not silently
  downgrade a teammate's terminal.
- Plugins: default off, add-only, skip-and-warn, visible opt-in.
- No caching of resolved settings across a process boundary in tests; two file reads per command is the price of honesty.

## 9. Open Items

1. **Per-deck/per-step defaults** — whether any census-adjacent preference belongs in config later (e.g. default `next -n`); undecided, nothing ships.
2. **Config diagram** — a `.mmd` of the chain per the diagram rules when the layer earns one.
3. **`config import`** — whether a paste-ready settings file deserves a bulk write command.
