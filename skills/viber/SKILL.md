---
name: viber
version: 1.0.0
description: 'The Viber regime — disciplined vibe-engineering. In a project declaring Viber, use the viber CLI for live census state, next-step reasoning, and recorded skill execution; reading this skill never substitutes for running the CLI. Start or resume with viber situation. Domain content stays with its owning skill and the ledger points to it (never copies); ownerless relocatable knowledge lands under .viber/, code and root-files stay untouched, questions / decisions / learned facts go to the Markdown memory ledger, and drafts stay revisable in [DR]. Recurring skills that were started but never ok-ed stay visible in a cross-step REVISIT pool; --note / viber note keep self-notes on the card; viber use records a batch; multi-project data resumes with --project <id> / viber now and re-binds a moved folder with viber project link. Sibling skills vinit, vcompact and vflow guide entry, compaction and task-scale flows; they are not shell commands. Not a replacement for the specialized skill that does the actual task.'
when_to_use: Any work inside a project whose AGENTS.md declares Viber — routing outputs, capturing to the memory files, checking supervision/structure/lifecycle rules, or on /viber and "vibe-engineering with discipline" requests. Also when an agent is about to place a knowledge artifact anywhere and does not know why.
argument-hint: "[the work under viber, or status to read where the project stands]"
---

# Viber — the regime, not a task

Viber guides the workflow without controlling the code. This skill is the standing posture; the heavy specs
live in `references/` and load one at a time.

## First act — activation check

Read `AGENTS.md`. Viber is active when it carries a Viber declaration — the `## Viber` section or any clear
sentence ("This project uses Viber", "Vibe Mode On"). No declaration → this skill does not apply: work
normally, and say once that `/vinit` would set the regime. Never write or remove the declaration yourself.

## Required CLI loop

**The skill supplies the rules; the CLI supplies live census state and records execution. Use both.**
Loading `/viber`, reading its references, or describing a command is not running that command.

Once activation is confirmed, run `viber situation -f json` from the project root **before substantive
work**. Repeat on a new session, handoff, or context resume; do not trust a remembered snapshot. Use
`-C "<census-file>"` when the project declares a different census location.

| Need | Execute |
|---|---|
| Orient on entry/resume | `viber situation -f json` |
| Decide what comes next | `viber next -f json`; use its reasons, not a remembered skill list |
| Inspect a candidate | `viber skill <name> -f json` or `viber skill <name> --content` |
| Record actual skill work | `viber use <name>` when work begins; `viber outcome <name> <result> "<evidence>"` when that invocation ends (`ok`, `fail`, or `skip`); `viber use a b c` to batch |
| Leave yourself a note | `viber note --on <name> "…"` (no invocation) or any write with `--note "…"`; it persists on the card |
| Revisit deferred recurring work | `viber next`/`situation` list a **REVISIT** pool: `recurring` skills used but never `ok`, surfaced across steps until settled |
| Work on / find another project | `viber now` shows the active one; `viber --project <id> <cmd>` resumes by id; `viber project link <id> --to <dir>` re-binds a moved folder |
| Update census facts | The relevant `viber set`, `log`, `add-skill`, or `refresh` command; check `--help` and `viber fields` rather than inventing fields |
| Verify census changes | `viber lint`; address or explicitly report findings before handing off |

- Execute commands through the shell and read their actual output. Never claim CLI-backed state without it.
- `skill` inspects metadata; it does not invoke that skill. Do the requested work with the fitting
  specialized skill, regardless of deck. Do not keep reloading Viber or prefer its sibling skills merely
  because Viber is active. Guidance does not override a task the user already chose.
- For census-registered skills, record only real invocations, not recommendations or metadata reads.
  Surface a missing registration instead of inventing a ledger entry. Respect disabled telemetry; never
  enable it silently. An `ok` invocation is not proof that an entire lifecycle phase is complete.
- The CLI is the sole writer of census JSON and telemetry. Markdown registry annotations and memory
  ledgers keep their documented writers; do not invent CLI commands for them or parallel JSON state files.
- If the CLI cannot run, try the project's documented launcher, report the exact failure, and mark
  CLI-derived state unverified. Do not silently switch to hand-edited census data, fabricate results, or
  recreate an existing census. A missing census follows `/vinit`, not an improvised copy script.
- Reuse a fresh result within the task. Re-read after relevant persisted state changes, not on every chat
  message; reconciliation is part of the task, not a repeated status performance.
- Recurring revisit is the CLI's job, not memory: when `next`/`situation` show a **REVISIT** entry,
  the recurring skill is unfinished — return to it and close with `outcome … ok`. Notes (`note`/`--note`)
  are self-markers on the census, never a substitute for a domain Skill's own artifact.
- Multiple projects share one install: trust `viber now` for where you are, and re-bind a relocated
  project with `viber project link` rather than editing the registry by hand.

## Standing behaviors

- **Ownership first, then the umbrella.** Decide who owns each fact before where it sits: domain content stays
  in its owning Skill's canonical artifact (a documentation Skill's specification tree, feature/schema docs,
  `AGENTS.md` rules) and the memory ledger points to it — pointer, not copy, one fact one home. Only **ownerless** relocatable
  knowledge goes to `.viber/<original-relative-path>`. Layout homes beat the umbrella: run output →
  `artifacts/<producer>/`, agent temp → `scratch/<task>/`, utilities → `tools/`, operations → `scripts/`;
  root-files (`AGENTS.md`, `README.md`), all code, and a Skill's anchored working directory stay.
- **Capture on arrival.** A question deferred → `memory.md` (with what blocks it). A question answered —
  explicit or implied → `settled.md` (answer + reason, marked provisional during [DR]). A fact learned about
  the user or project → `learnt.md` (evidence + implication). Record when it happens, not at session end.
- **Honest gaps.** An unanswered decision stays `pending — not assumed`; never fill it with a plausible default.
- **Draft posture.** During [DR] docs and prior answers are the current best, not law (`thaw`); formal
  decision records begin only at [IP].
- **Router stance.** Know where the project stands (phase, completed, open, blocked) and surface deferred
  questions when their blockers clear — guidance, never control; the user decides.

## Load exactly one reference

| The question | Read |
|---|---|
| Phases, skills, commands, project states [DR][IP][PP] | `references/lifecycle.md` |
| Who owns this fact? Where does it go? Supervision active? Participation? | `references/supervision.md` |
| Canonical layout, home of every file kind, git treatment | `references/structure.md` |
| Memory files: templates, field rules, move-on-answer discipline | `references/memory.md` |
| Settings chain: config get/set, layers, telemetry/plugins switches | `references/config.md` |
| Progress tracking, next-step logic, skill suggestions, warnings | `references/router.md` |
| A subsystem diagram (render or edit) | `assets/diagrams/*.mmd` |
| Bootstrapping a memory file from scratch | `assets/templates/*.md` |

## Agent commands (sibling skills)

These are slash-invoked workflows, not shell subcommands. Use the CLI loop above for live state;
`/vinit` guides full setup, while `viber init` only creates a missing census.

| Command | Does |
|---|---|
| `/vinit` | enter Viber: registry, memory files, layout duties, the AGENTS.md declaration, start the flow |
| `/vcompact` | make room without loss: archive finished history to `.viber/.compact/<id>/` |
| `/vflow` | build task-scale mini-lifecycles under `.viber/flow/` |

## Layout

```text
viber/
├── SKILL.md              this posture
├── references/           lifecycle · supervision · structure · memory · router · config
├── scripts/
│   └── check_orphans.mjs  doc-link integrity: orphans + broken targets (pure Node, zero deps)
└── assets/
    ├── diagrams/         the four flow diagrams (.mmd, obey use-mmd)
    └── templates/        empty memory.md / settled.md / learnt.md
```

## Bundled tools

| Script | Does | Usage |
|---|---|---|
| `scripts/check_orphans.mjs` | Verifies every `.md` in a docs tree has ≥1 incoming link. Reports orphans and broken link targets. Exempts root `index.md` + each first-level directory's `index.md` as entry points. | `node scripts/check_orphans.mjs <docs-root> [--ignore <relative-path>]...` |

`--ignore` is repeatable: suppresses broken-link reports for known unauthored targets (path relative to
docs root). Exit 0 = clean, 1 = orphans found, 2 = usage error.

**Hook integration:** copy the script into the project's `.agents/scripts/` (or reference it from the
skill path), then register a `PostToolUse` hook on `Write|Edit` in `.agents/hooks.json`. The hook command
carries the project-specific docs root and `--ignore` flags — the script itself holds no project identity.

## What this skill is not

Not the lifecycle steps themselves (`idea-md`, `steering`, FULL CODE do those), not a tech-stack chooser,
not the rulebook writer, not the executor of application work. The agent still runs the Viber CLI to
maintain workflow awareness, then uses the appropriate specialized skill for the actual task.
