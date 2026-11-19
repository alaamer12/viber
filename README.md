# Viber

Agents start your project cold: they re-ask settled decisions, invent parallel
implementations, and stop knowing what was next the moment the context window
rolls over. **Viber makes your project askable.** One census CLI answers *what
is the situation*, *what is the next unblocked step and why*, and *what does
every field mean* — and five agent skills enforce the discipline that keeps
those answers true: a fixed five-step lifecycle (Idea → Vision → Foundation →
Implementation → Shared), memory ledgers for questions, decisions and learned
facts, and a supervision umbrella that relocates generated knowledge instead of
littering your repo.

Viber's own documentation is its product: the design drafts in `docs/` are the
suite's source, the shipped skills in `skills/` are what agents execute, and
`viber.json` is the master census — every skill, its fit, its relations and
reasons — that seeds every project that adopts the regime.

## Install the skills (skills.sh)

The five Viber skills are a standard SKILL.md suite on GitHub, installable with
the open agent-skills CLI ([skills.sh](https://skills.sh), Node.js ≥ 22.20)
into any of 75+ coding agents:

```bash
# from your project folder — interactive pick of skills and agents
npx skills add alaamer12/viber

# specific skill only
npx skills add alaamer12/viber --skill viber

# skip installing, just run one skill as a prompt
npx skills use alaamer12/viber@viber
```

Then in your project: run `/viber init` (the `vinit` skill) — it inventories
your deck, writes the census, and the regime is live.

The author of this suite also installs it from source:
`cd F:/Projects/Agent/skills/insource && python manager.py viber` symlinks the
full 41-skill lifecycle set (Viber's five plus every deck skill the census
references) into all agent folders. The two paths serve different needs:
skills.sh distributes the standalone suite; `manager.py` maintains the author's
linked development deck, where edits land live through the symlinks.

## Install the CLI

The census CLI is a Python package (`viber`, typer + pydantic, strict mypy):

```bash
git clone https://github.com/alaamer12/viber && cd viber
uv sync
uv run viber status        # phase, current step, counts
```

or `uv tool install git+https://github.com/alaamer12/viber.git` for the
`viber` console script without a checkout.
Run it as `viber <cmd>` (console script after install) or `python -m viber
<cmd>` — both enter the same `viber.app:main`; output is always UTF-8
regardless of Windows console codepage. `--help` is everywhere, and
`viber fields` explains every field of every artifact the CLI touches.

From a new project's root, bootstrap its census using the installed skills folder:

```bash
viber init --skills-root "<installed-skills-folder>"
viber registry --skills-root "<installed-skills-folder>" -f json
viber lint
```

Repeat `--skills-root` for additional registered folders. `init` writes
`.viber/.data/viber.json`, resolves installed paths to absolute realpaths, and
refuses to overwrite an existing census. Missing skills remain explicit warnings
with installation blockers. `registry` exports YAML-resolved metadata with
nonempty invocation triggers; it does not overwrite the annotated registry.
The agent `/vinit` workflow still owns classification, exclusions, memory, and
AGENTS.md. `-C` always names a census **file**, not a project folder.

Daily usage and the pipe patterns (JSON, `-nr`, `--out`) live in
**[USAGE.md](USAGE.md)**.

## What you get, concretely

| Question | Command | Evidence behind the answer |
|---|---|---|
| What is the situation? | `viber situation` | phase, step, roster, usage ledger, owed decisions, next |
| What should happen next — and why? | `viber next` | unblocked skills with `do:` / `why:` lines, predecessor reasons, needs that stand without a skill |
| What does this field mean, who writes it, its limit? | `viber fields` | 119 rows over census, frontmatter, config, telemetry, env and ledgers — from code, not prose |
| Is the census honest? | `viber lint` | referential integrity, disk drift, deck conflicts surfaced as ASK USER decisions; `--remote` adds GitHub upstream truth |
| Who did what, when? | `viber use` / `outcome` / `stats` | SQLite invocation ledger feeding `next` patterns and the `last:` line |

Writes are the CLI's alone: `init`, `set`, `log`, `add-skill`, `refresh` validate at
the boundary, every bounded field has a cataloged cap with an identity and a
recovery line (the Error-as-Truth doctrine, `docs/regime/limits.md`), and
nothing is ever silently trimmed — history rolls at 100 and says so.

## Where to start reading

| You want to… | Go to |
|---|---|
| Use the CLI day to day | [USAGE.md](USAGE.md) |
| Understand the lifecycle and its phases | [docs/regime/lifecycle.md](docs/regime/lifecycle.md) |
| See how skills are routed and selected | [docs/regime/router.md](docs/regime/router.md) |
| Understand the supervision umbrella | [docs/regime/supervision.md](docs/regime/supervision.md) |
| See the canonical project layout Viber enforces | [docs/regime/structure.md](docs/regime/structure.md) |
| Understand the memory ledger | [docs/regime/memory.md](docs/regime/memory.md) |
| Understand the settings chain and plugin surface | [docs/regime/config.md](docs/regime/config.md) |
| Understand display modes (rich, pipes, JSON) | [docs/regime/display.md](docs/regime/display.md) |
| Read a command's design spec (init / compact / flow) | [docs/commands/init.md](docs/commands/init.md) · [docs/commands/compact.md](docs/commands/compact.md) · [docs/commands/flow.md](docs/commands/flow.md) |
| See what agents actually execute | [skills/](skills/) — each subfolder is an installable skill |
| Understand how drafts become shipped skills | [PIPELINE.md](PIPELINE.md) |
| Browse all design docs | [docs/index.md](docs/index.md) |

## Structure

```
viber/
├── docs/           design drafts — provisional, iterated, grilled
├── skills/         shipped agent skills — lean, imperative (viber, vinit, vcompact, vflow, adapt)
├── src/viber/      the census CLI package (typer + pydantic, strict mypy)
├── tests/          pytest suites incl. byte-exact seed round-trip parity and doc tripwires
├── viber.json      master seed census — every skill, relation, hint and reason
├── pyproject.toml  uv-managed, hatchling build, console script `viber`
├── USAGE.md        the common commands and the pipe patterns
└── PIPELINE.md     the draft → settle → promote → verify → ship workflow
```

### Display modes

Viber renders rich boxed tables wherever it displays — piped or not (typer
already ships rich). Color is granted by the live terminal alone:

| Situation | Output |
|---|---|
| interactive terminal | rich layout + color |
| piped / redirected stdout | rich layout, **zero ANSI bytes** |
| `--no-rich` / `-nr` (any command) | plain — the flag always wins |
| `VIBER_RICH=0` env | plain, including for typer's own help |
| `--out` file | plain bytes — machine contract, never configurable |
| `-f json` | live terminal: syntax-colored; piped or `--out`: untouched bytes (stdout is native UTF-8, files keep ASCII escapes) |

If a legacy Windows console shows box glyphs as tofu, `-nr` is the instant revert.

Building the distributable: `uv build` → `dist/viber-<version>.whl` + sdist.
Publishing (`uv publish`) is a deliberate decision, not an automatic step.

## Relationship to insource

Viber owns its five skills (`viber`, `vinit`, `vcompact`, `vflow`, `adapt`).
The deck skills the census references (steering, architecture, agents-md, etc.)
live in the author's insource registry at `F:/Projects/Agent/skills/insource`
and are resolved by path through the census decks; `manager.py viber` reads
this project's `viber.json` by relative path and installs the whole set.
Other adopters go through skills.sh and get the five standalone — the census
decks then resolve to whatever skill folder each project registers.

## Status

The project is in [DR] Draft / [IP] In-Progress. Design docs are provisional
(thaw posture applies). Shipped skills are functional and installed. The CLI is
production-grade: strict typing, full regression suite, byte-exact seed
round-trip parity, documentation tripwire tests, packaged wheel.
Post-production [PP] begins at first real release.
