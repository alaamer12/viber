# BUG-006 — Recurring skills are forgotten once the project advances

Found during dogfooding (2026-11-19). Status: **resolved**.

## Problem

Lifecycle skills that are meant to be revisited — the clearest case is `agents-md`, which serves
only the "Idea & Understanding" step — are typically started early, then their full content is
deferred because the project is not yet clear. An agent records `use` and `outcome skip` (or leaves
the invocation open) and moves on. Once the project advances past that step, the skill is never
re-suggested and the unfinished work is silently forgotten.

## Reproduction

```bash
viber use agents-md
viber outcome agents-md skip "project unclear, finish after Foundation"
viber set . phase IP          # advance the project past Idea & Understanding
viber next                    # agents-md is gone — it serves step 1, not the current step
```

## Expected

`next` / `situation` should keep a recurring skill that is used-but-unfinished visible, regardless of
which step the project is currently on, so the agent is reminded to return to it.

## Actual

Candidate eligibility comes solely from the current step's roster, gated by `fit.blockers`
(`core/resolution.py:next_candidates`). Completion lives only in telemetry. A skill outside the
current step is invisible forever — the forgetting was structural, not a missing field.

## Suggested fix

A skill-level `recurring` marker plus a cross-step revisit pool keyed on telemetry, surfaced by
`next` and `situation` and settled by an `ok`.

## Resolution

Implemented (2026-11-19):

- New skill field `recurring: bool` (`models/schema.py`, documented `skill.recurring`, writable via
  `viber set <skill> recurring true|false`). Marked `true` for `agents-md` in the seed.
- `TelemetryDB.latest(skill)` returns the newest invocation's outcome+note.
- `resolution.next_candidates` builds a `revisit` list: recurring, invoked (`count>0`) but never
  `ok` (`ok==0`), and outside the current-step roster. Surfaced in `next` and `situation` under a
  `REVISIT (recurring, not yet ok)` header, plain and rich, carrying the last outcome and note as the
  reason. `outcome … ok` settles it.
- Doctrine: `docs/regime/router.md` §4.4 and `docs/regime/lifecycle.md` §2.5 (and their shipped
  copies).

Verification: `tests/test_recurring.py` (cross-step surfacing, `ok` clears, never-invoked absent,
non-recurring absent, current-step member excluded, `set recurring` round-trip + bogus rejection);
full suite green (`pytest`).
