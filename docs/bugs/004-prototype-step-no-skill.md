# BUG-004: "prototype" lifecycle step has no registered skill

**Severity:** low — lint silently skips it; the Router cannot suggest a skill for the step
**Found:** 2026-11-19, during `/vinit` on Kabrha
**Affects:** `viber.json` (census), `skills/viber/references/lifecycle.md`

## Problem

The lifecycle defines a "prototype" step (Phase 2, Vision). The census carries an entry for it. But no
SKILL.md exists for a `prototype` skill in either the viber skills folder or the insource deck. The
registry has 75 skills; none is named `prototype`.

When lint encounters a census entry whose skill path does not resolve to a SKILL.md, it silently skips
validation rather than flagging the gap. The Router's next-step logic cannot suggest a skill for this
step because none is registered.

## Expected

Either:
- (A) A `prototype` skill exists (even a thin one that orchestrates the existing deck skills:
  `design-taste-frontend`, `ui-taste`, `capture`, `parity`), OR
- (B) The census marks the step as "composite — no single skill; driven by the agent using deck skills"
  and lint accepts that as valid, OR
- (C) Lint flags census entries with no resolvable skill as a warning: "step 'prototype' has no
  registered skill — the Router cannot suggest one."

## Actual

Silent skip. The project has a rich prototype (116 files) but the lifecycle tracking treats the step
as if it has no tooling. The agent drove it manually using deck skills, which worked, but the census
and Router are blind to it.

## Suggested fix

Option C minimum (lint warning), option A ideally (a thin orchestration skill that names the deck
skills it composes and the fidelity contract it enforces). The lifecycle doc should state which case
applies so the census schema can distinguish "skill exists" from "composite step."

## Resolution

Resolved 2026-11-19 using the user-selected warning-and-clarification option.
Lint now emits `null-path` for every missing registered path, including entries
that already have blockers. The warning explains that the Router cannot invoke
the skill and gives a registration command. Broken non-null paths remain errors.

Both lifecycle documents identify prototype as a mandatory deck-assisted task,
not a shipped skill. No new prototype workflow or schema was introduced.
Verified by `tests/test_lint.py`, CLI text/JSON output, and the installed-wheel
smoke run: prototype is visible while a warnings-only lint still exits zero.
The earlier sections preserve the original incident and alternatives.