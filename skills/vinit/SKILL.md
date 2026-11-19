---
name: vinit
version: 1.0.0
description: 'Viber entry command (written /viber init in the spec): indexes the user''s registered Skill deck into .viber/registry.md, asks which deck Skills to exclude from the supervision umbrella and states each consequence, bootstraps the memory files and the project layout''s .gitignore duties, writes the AGENTS.md Viber declaration (the activation marker), then starts the lifecycle at the right step. Re-runnable: refreshes the registry, never erases memory. Not for authoring the rest of AGENTS.md (agents-md owns that) and not for choosing skills.'
when_to_use: First Viber run in a project, or a refresh — /vinit, "/viber init", "set up Viber here", or when Viber posture is wanted but no declaration exists yet.
argument-hint: "[none — re-run refreshes registry and re-checks project state]"
---

# vinit — enter Viber

Three steps, safe to repeat. The full contracts (registry format, participation rules, migration) are in
`references/init.md`; this file is the runbook.

## Step 1 — understand the deck

1. Find every registered Skill (global + project-level) and ask the user about extension repositories.
2. Read metadata only from each `SKILL.md`: name, description, when-to-use, and the `viber: part|separated` tag.
   Use `viber registry --skills-root "<installed-root>"` to export metadata; repeat `--skills-root` for every
   registered root, with `-f json` and `-o "<export-file>"` when needed. This is not the annotated registry:
   classification and exclusions remain agent/user work. Resolve YAML scalars safely and derive missing
   when-to-use from the description's trigger clause, then its first sentence; never leave a blank cell.
3. Classify: Viber lifecycle Skill vs deck, scope, area, conflicts; write `.viber/registry.md`.
4. **Ask about exclusions** — which deck Skills should stay outside the umbrella — stating each consequence:
   in-deck = output rerouted to `.viber` + remembered; out = no guaranteed control or memory. Record in the
   registry's `Viber` column.
5. Create the memory files from `viber` skill `assets/templates/` if absent — never overwrite existing ones.
6. Ensure `.gitignore` carries the layout duties (`artifacts/`, `scratch/`, env/build outputs); create
   layout folders only on first write. Existing root artifacts: ask, recommend moving under `.viber`.
   Follow `viber` skill → `references/structure.md` section 5: `.viber/` knowledge is committed by default,
   not blanket-ignored. Preserve explicit existing project policy; do not ask an ignore-or-commit question.
7. Bootstrap a missing census with `viber init --skills-root "<installed-root>"` from the project root;
   repeat `--skills-root` for additional roots. It writes `.viber/.data/viber.json` by default and refuses
   an existing census; `-C` selects a census **file**, not a project directory. Installed paths resolve to
   absolute realpaths; missing Skills retain null paths and blockers with a warning. On refresh, reuse the
   existing census. Preserve the seed's generic `doing`/`why` until personalizing them via
   `viber set <skill> doing "<project task>"` and `viber set <skill> why "<project reason>"`; never clear them.
   Full census duties: `references/init.md` section 2.9.

## Step 2 — mention it in AGENTS.md

Add or refresh the `## Viber` section (registry + memory pointers) — this is the activation marker. If
`AGENTS.md` is missing, create it with only this section; `agents-md` completes it later in Phase 1.

## Step 3 — start the flow

New project → open Phase 1 (`idea-md`). Existing → mark found outputs Needs Review (presence ≠ completion),
missing ones Not Started, name the next step, suggest fitting deck Skills. Then let the Router guide
(`viber` skill → `references/router.md`).

## Load when detail is needed

| Need | Read |
|---|---|
| Full spec, registry format, rules | `references/init.md` |
| Umbrella + participation semantics | `viber` skill → `references/supervision.md` |
| The flow diagram | `assets/diagrams/init-flow.mmd` |

## What this command is not

Not a reset (repeat runs refresh, never erase); not the rulebook writer; not a Skill installer — it reads
the deck as registered and records the user's exclusions. This agent workflow is not the shell command
`viber init`: that command only bootstraps the census, without writing the registry, memory files,
`AGENTS.md`, or `.gitignore`, or starting the lifecycle.
