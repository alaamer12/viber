# BUG-003: Master seed skill paths are relative — break on copy to any project

**Severity:** high — every new project census is broken on arrival
**Found:** 2026-11-19, during `/vinit` on Kabrha
**Affects:** `viber.json` (master seed at repo root), `src/viber/store.py`

## Problem

The master `viber.json` stores skill paths as relative strings (`skills/adapt`, `skills/agents-md`, …).
These resolve correctly only when the cwd is the viber repo itself. Copying the file to a project's
`.viber/.data/viber.json` makes all 42 paths invalid — lint reports 42 errors.

## Reproduction

```bash
cp viber.json /path/to/project/.viber/.data/viber.json
cd /path/to/project
uv run viber lint -C .
# → 42 errors: path does not exist
```

## Expected

Either:
- (A) The master seed stores absolute paths (machine-specific, regenerated per install), OR
- (B) The CLI resolves relative paths at load time against a configured skills root, OR
- (C) A `viber init` command (see BUG-001) resolves paths at write time so the project census always
  carries absolute realpaths.

Option C is cleanest: the master stays relative (portable across machines), the project census is
absolute (resolved once at init).

## Actual

The agent must write a custom script to `os.path.realpath` every path against the skills symlink root.
41 of 42 paths needed fixing (one was already absolute). This is mechanical work the CLI should own.

## Suggested fix

Coupled with BUG-001: the init/seed command resolves paths. Additionally, `store.py` could accept a
`--skills-root` flag or config key that resolves relative paths at load time as a fallback, so a
hand-copied census still works if the user sets the root.

## Resolution

Resolved 2026-11-19 using option C, together with BUG-001. The master remains
portable source data; `viber init --skills-root "<installed-root>"` writes
canonical absolute paths for installed skills into the new project census.
Explicit roots take precedence over source/deck fallbacks, symlink aliases are
deduplicated, and conflicting real sources prevent creation. Unavailable skills
retain null paths and blockers rather than invented paths.

Verified through `tests/test_bootstrap_cli.py`, seed-parity tests, and installed-wheel
initialization away from the checkout. Manual copies of old censuses are not
silently repaired at load time; existing project data is never rewritten by init.
The earlier sections preserve the original incident and alternatives.