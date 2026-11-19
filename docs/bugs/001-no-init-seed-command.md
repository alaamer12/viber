# BUG-001: No CLI command to bootstrap a project census

**Severity:** high — blocks the documented workflow
**Found:** 2026-11-19, during `/vinit` on Kabrha
**Affects:** `src/viber/` (CLI), `skills/vinit/references/init.md`

## Problem

The vinit spec says the census (`.viber/.data/viber.json`) is "written only through the CLI." But the CLI
has no `init`, `seed`, or `bootstrap` command that creates a project census from the master seed. The only
way to get a working census in a new project is to manually copy `viber.json` from the viber repo root and
fix all 42 skill paths by hand.

## Reproduction

```bash
cd /path/to/new-project
uv run viber status -C .
# → Error: no census found at .viber/.data/viber.json or ./viber.json
```

There is no `viber init` or `viber seed` to create it.

## Expected

A CLI command (e.g. `viber init -C <project>` or `viber seed -C <project>`) that:
1. Creates `.viber/.data/` if absent
2. Copies the master seed (skill catalog with fields)
3. Resolves all skill paths to absolute realpaths on the current machine
4. Sets project-specific `doing`/`why` to empty or a sensible default
5. Runs lint to confirm 0 errors

## Actual

Manual copy + a custom Python script to fix 41/42 relative paths. The agent had to write throwaway code
that the CLI should own.

## Suggested fix

Add a `viber init` subcommand (or `viber seed`) that reads the master `viber.json` from the package's own
data directory, resolves paths via `os.path.realpath` against the skills root, and writes the project census.
The master seed's relative paths (`skills/<name>`) become absolute at init time, not at copy time.

## Resolution

Resolved 2026-11-19. `viber init --skills-root "<installed-root>"` now bootstraps
`.viber/.data/viber.json` from the packaged master seed. `-C` selects an output
census file, not a project directory. Initialization resolves installed paths,
resets copied project progress/history, preserves generic task guidance, and runs
lint before exclusive creation. Existing censuses and unrelated project files
are never replaced. Missing catalog skills remain explicit warnings and blockers.

Verified by `tests/test_bootstrap_cli.py` and an installed-wheel run in a clean
temporary project: 41 resolved skills, zero lint errors, one prototype warning,
and an unchanged census after repeat-init refusal. The wheel's seed bytes match
the master. The earlier sections preserve the original incident and proposed options.