# BUG-002: init.md vs structure.md contradict on .viber/ git treatment

**Severity:** medium — spec contradiction forces a user decision that should not exist
**Found:** 2026-11-19, during `/vinit` on Kabrha
**Affects:** `skills/vinit/references/init.md` §2.8, `skills/viber/references/structure.md` §3.7

## Problem

Two authoritative specs give opposite instructions:

- **init.md §2.8** (gitignore duties): lists `.viber/` among paths to ignore, treating it as generated
  agent state.
- **structure.md §3.7**: "`.viber/` — the knowledge umbrella … Committed: that is the transparency the
  user chose."

An agent following init.md literally would gitignore the entire knowledge tree. An agent following
structure.md would commit it. The user had to resolve the contradiction manually.

## Expected

One authoritative answer. structure.md §3.7 is the later, more deliberate design (the umbrella is
committed knowledge). init.md §2.8 should say: "ignore `artifacts/`, `scratch/`, `**/.venv/`, and
environment/output folders inside `.viber/` — but NOT `.viber/` itself."

## Actual

init.md §2.8 still carries the old ignore recommendation. The Kabrha project resolved this by user
decision (settled.md #1: committed), but every new project will hit the same contradiction.

## Suggested fix

Rewrite init.md §2.8 to align with structure.md §3.7. The gitignore minimum becomes:

```gitignore
artifacts/
scratch/
**/.venv/
# .viber/ is committed knowledge — only env/output folders inside it are ignored
```

Remove any line that suggests ignoring `.viber/` itself. Add a cross-reference: "see structure.md §5
for the full git treatment."

## Resolution

Resolved 2026-11-19. The init draft, shipped init reference, runbook, structure
Git-treatment section, and config cross-reference now agree: `.viber/` is durable
committed knowledge, with only generated/environment/private outputs ignored.
The blanket-ignore and config-unignore recipe was removed. Explicit existing
project Git policies are preserved; this correction changes no actual ignore files.

Verified by reviewing both spec copies and searching active Markdown for the old
recommendation. The earlier sections preserve the original incident.