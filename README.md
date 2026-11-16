# Viber

Disciplined vibe-engineering. A lifecycle regime that governs how agents design, build, and maintain projects — from first idea through post-production.

This repository is the independent source for the Viber skill suite: the design drafts that shape it, the shipped skills that agents execute, and the `viber` census CLI that agents use to know what to do next — and why.

## Where to start

| You want to… | Go to |
|---|---|
| Understand the lifecycle and its phases | [docs/regime/lifecycle.md](docs/regime/lifecycle.md) |
| See how skills are routed and selected | [docs/regime/router.md](docs/regime/router.md) |
| Understand the supervision umbrella | [docs/regime/supervision.md](docs/regime/supervision.md) |
| See the canonical project layout Viber enforces | [docs/regime/structure.md](docs/regime/structure.md) |
| Understand the memory ledger | [docs/regime/memory.md](docs/regime/memory.md) |
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
├── tests/          pytest suites incl. legacy-parity against the first-commit seed
├── viber.json      master seed census — every skill, relation, hint and reason
├── viber.py        launcher shim — keeps `python viber.py <cmd>` working anywhere
├── pyproject.toml  uv-managed, hatchling build, console script `viber`
└── PIPELINE.md     the draft → settle → promote → verify → ship workflow
```

## The CLI

Install once, project-local (never the user environment):

```bash
cd "F:/Projects/Agent/projects/viber"
uv sync                       # creates .venv, installs deps + the viber script
uv run viber status           # phase, current step, counts
uv run viber next -n 3        # next unblocked skills, each with its reasons
uv run viber skill steering -P full -f json
uv run viber next -o plan.txt # compact flush (txt default; --format json for data)
uv run viber lint             # census audit; conflicts surface as ASK USER decisions
```

`python viber.py <cmd> ...` keeps working from any project as the launcher shim
(AGENTS.md instruction unchanged): it runs the package in-process, falls back to
this project's `.venv` or `uv run`, and otherwise prints the exact bootstrap
commands — it never installs anything silently.

Building the distributable: `uv build` → `dist/viber-<version>.whl` + sdist.
Publishing (`uv publish`) is a deliberate decision, not an automatic step.

## Relationship to insource

Viber owns its five skills (`viber`, `vinit`, `vcompact`, `vflow`, `adapt`). The deck skills it references (steering, architecture, agents-md, etc.) live in the insource registry at `F:/Projects/Agent/skills/insource` and are resolved by path through the census decks. Installation is driven by insource's `manager.py viber` command, which reads this project's `viber.json` via a relative path.

## Status

The project is in [DR] Draft / [IP] In-Progress. Design docs are provisional (thaw posture applies). Shipped skills are functional and installed. The CLI is production-grade: strict typing, full test suite, legacy output parity, packaged wheel. Post-production [PP] begins at first real release.
