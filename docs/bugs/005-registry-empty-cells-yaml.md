# BUG-005: Registry generation leaves empty "When to use" cells and leaks YAML block scalars

**Severity:** medium — 38/75 skills had empty cells; 4 had raw `>-` as content
**Found:** 2026-11-19, during `/vinit` on Kabrha (user spotted it post-generation)
**Affects:** `skills/vinit/references/init.md` §2.2 (spec gap, now patched), agent generation logic

## Problem

Two defects in registry generation:

1. **No fallback for absent `when_to_use`.** Many skills (anti-slop, architecture, fix, grill-me,
   implement, mistakes, packages, planner, pvc, readme-md, states, and 27 deck skills) have no
   `when_to_use` frontmatter field. The generator left the cell empty instead of deriving it from
   the description's trigger clause.

2. **YAML block scalars unresolved.** Skills using `description: >-` (steering, update,
   design-taste-frontend, exmaine) had the literal string `>-` written into the Purpose and/or
   When-to-use cells instead of the resolved multiline content.

## Reproduction

Generate a registry from the 75-skill deck at `C:/Users/amrmu/.qoder/skills`. Any naive
frontmatter parser that does `fm.get("when_to_use", "")` without fallback, and does not use a
proper YAML loader, produces these defects.

## Expected

- Every "When to use" cell is non-empty. Fallback chain: explicit `when_to_use` → description
  trigger clause ("Use when…", "Use for…", "Invoke when…") → description first sentence.
- YAML block scalars (`>-`, `|`) are resolved to their string value before extraction.

## Actual

38 empty cells, 4 `>-` artifacts. The user caught it; the agent regenerated with a proper
`yaml.safe_load` + fallback script.

## Spec fix applied

`skills/vinit/references/init.md` §2.2 now carries two new bullets (added 2026-11-19):
- "YAML block scalars are resolved."
- "When-to-use fallback (never empty)."

## Remaining work

The spec is patched. If a CLI `viber init` command is built (BUG-001), its registry generation
must implement these rules. Until then, the agent-driven generation must use a proper YAML parser
and the fallback chain — the spec now says so explicitly.

## Resolution

Resolved 2026-11-19. Shared frontmatter ingestion now uses `yaml.safe_load`,
preserves folded/literal scalar semantics and quoted values, and reports malformed
or wrongly typed metadata with its source path. `viber registry --skills-root
"<installed-root>"` exports all installed metadata through the tested fallback
chain, with escaped Markdown cells or structured JSON. It does not overwrite
annotated registries or infer exclusions; `/vinit` now uses this metadata export.

Verified by `tests/test_data.py`, `tests/test_bootstrap_cli.py`, and a live
installed-wheel export: all 76 currently registered skills have nonempty trigger
text and no source conflicts. Refresh retains curated census trigger guidance;
invalid YAML cannot disappear into refresh-all's missing-skill skip.
The earlier sections preserve the original incident and the then-pending work.