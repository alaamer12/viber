# Viber

This repository is the independent source for the Viber skill suite: the design drafts that shape it, the shipped skills that agents execute, and the `viber` census CLI that agents use to know what to do next — and why.

## Where to start

| You want to… | Go to |
|---|---|
| Understand the lifecycle and its phases | [docs/regime/lifecycle.md](docs/regime/lifecycle.md) |
| See how skills are routed and selected | [docs/regime/router.md](docs/regime/router.md) |
| Understand the supervision umbrella | [docs/regime/supervision.md](docs/regime/supervision.md) |
| See the canonical project layout Viber enforces | [docs/regime/structure.md](docs/regime/structure.md) |
| Understand the memory ledger | [docs/regime/memory.md](docs/regime/memory.md) |
| Understand the settings chain and plugin surface | [docs/regime/config.md](docs/regime/config.md) |
| Read a command's design spec (init / compact / flow) | [docs/commands/init.md](docs/commands/init.md) · [docs/commands/compact.md](docs/commands/compact.md) · [docs/commands/flow.md](docs/commands/flow.md) |
| See what agents actually execute | [skills/](skills/) — each subfolder is an installable skill |
| Understand how drafts become shipped skills | [PIPELINE.md](PIPELINE.md) |
| Install the full suite | `cd F:/Projects/Agent/skills/insource && python manager.py viber` |
| Browse all design docs | [docs/index.md](docs/index.md) |

## Structure

```
viber/
├── docs/           design drafts — provisional, iterated, grilled
├── skills/         shipped agent skills — lean, imperative, installed via symlink
├── src/viber/  the census CLI package (typer + pydantic, strict mypy)
├── tests/          pytest suites incl. byte-exact seed round-trip parity
├── viber.json      master seed census — every skill, relation, hint and reason
├── pyproject.toml  uv-managed, hatchling build, console script `viber`
└── PIPELINE.md     the draft → settle → promote → verify → ship workflow
```

## The CLI

Install once, project-local (never the user environment):

```bash
cd "F:/Projects/Agent/projects/viber"
uv sync                       # creates .venv, installs deps + the viber script
uv run viber status           # phase, current step, counts
uv run viber situation        # the whole picture in one call: status, usage, next, owed decisions
uv run viber next -n 3        # next unblocked skills, each with its reasons
uv run viber skill steering -P full -f json
uv run viber next -o plan.txt # compact flush (txt default; --format json for data)
uv run viber lint             # census audit; conflicts surface as ASK USER decisions
uv run viber lint --remote    # also compare deck clones against their GitHub upstreams (network)
uv run viber list -nr         # plain output, scriptable (rich boxes are for humans)
uv run viber config list      # the settings chain: value, source layer, default per key
uv run viber config set profile full   # state a preference once, visibly; flags still win
```

Run the CLI as `viber <cmd>` (console script after `uv sync`/install) or
`python -m viber <cmd>` — both enter the same `viber.app:main`. No launcher shim:
`viber.py` is gone; `python -m viber` from this checkout's venv is the portable
entry, and output is always UTF-8 regardless of the Windows console codepage.

### Display modes

On a real terminal viber renders rich boxed tables (typer already ships rich). Three ways to get plain
output, and one hard guarantee:

| Situation | Output |
|---|---|
| interactive terminal | rich layout + color |
| piped / redirected stdout | rich layout, **zero ANSI bytes** — display is rich wherever it displays |
| `--no-rich` / `-nr` (any command, any subcommand) | plain — the flag always wins |
| `VIBER_RICH=0` env | plain, including for typer's own help |
| `--out` file, `-f json` | plain bytes — machine contracts, never configurable |

If a legacy Windows console shows box glyphs as tofu, `-nr` is the instant revert. Details:
[docs/regime/display.md](docs/regime/display.md).

Building the distributable: `uv build` → `dist/viber-<version>.whl` + sdist.
Publishing (`uv publish`) is a deliberate decision, not an automatic step.

## Relationship to insource

Viber owns its five skills (`viber`, `vinit`, `vcompact`, `vflow`, `adapt`). The deck skills it references (steering, architecture, agents-md, etc.) live in the insource registry at `F:/Projects/Agent/skills/insource` and are resolved by path through the census decks. Installation is driven by insource's `manager.py viber` command, which reads this project's `viber.json` via a relative path.

## Status

The project is in [DR] Draft / [IP] In-Progress. Design docs are provisional (thaw posture applies). Shipped skills are functional and installed. The CLI is production-grade: strict typing, full test suite, byte-exact seed round-trip parity, packaged wheel. Post-production [PP] begins at first real release.
