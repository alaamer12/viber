# Viber Development Pipeline

> How design drafts become shipped agent skills. This document governs the project's own development — Viber applied to itself.

## The two layers

| Layer | Path | Phase | Nature |
|---|---|---|---|
| Design drafts | `docs/` | [DR] Draft | Provisional. Ideas get written, grilled, refined. Thaw posture applies — nothing here is law. |
| Shipped skills | `skills/` | [IP] In-Progress | Derived product. What users install and agents execute. Lean, imperative, token-efficient. |

The docs are the source of truth for **why**. The skills are the source of truth for **what the agent does**. When they diverge, the pipeline below defines which wins and how to reconcile.

## Stages

### 1. Draft

Write or refine in `docs/`. Use `close-topics` to walk one design area at a time, `grill-me` to stress-test decisions. Open questions stay visible — never silently omit an undecided point.

- One concern per file, at full depth.
- Diagrams live in `docs/diagrams/` as `.mmd` files; docs link to them, never inline mermaid.
- The `docs/index.md` index stays current (standing instruction inside it).

### 2. Settle

A topic closes when the user decides. Record the decision in the doc: what was chosen, what was rejected, why. Mark the section settled (a brief note, not a formal ADR — this project is still [DR]).

Settled content is stable enough to promote. Unsettled content stays in docs and does not leak into skills.

### 3. Promote

Port settled design into `skills/`. This is a **rewrite**, not a copy:

| Docs version | Skills version |
|---|---|
| Exploratory prose, alternatives, rationale | Imperative contracts: do X, then Y, gate on Z |
| Full context for a human designer | Minimal context for an agent executing a task |
| May explain the same concept twice across files | One home per concept; everything else is a link |
| Diagrams illustrate design reasoning | Diagrams show the agent's decision flow |

Promotion checklist:

1. Identify which skill owns the concern (`viber`, `vinit`, `vcompact`, `vflow`, `adapt`).
2. Write or update the reference file in `skills/<name>/references/`.
3. Update `skills/<name>/SKILL.md` dispatcher if the load-table or mode changed.
4. Update `skills/<name>/assets/` if templates or diagrams changed.
5. Add a back-link in the docs file: "Shipped as `skills/<name>/references/<file>.md`."
6. If the change adds/removes a skill or alters its phase, use `viber add-skill` / `remove-skill` / `set`.

### 4. Verify

Before shipping:

- Every relative link in the changed skill files resolves.
- Frontmatter: `name` matches folder, `description` is single-line ≤ 1024 chars.
- `viber refresh <skill>` succeeds (re-reads frontmatter + content tree).
- `viber status` shows expected phase and blocker count.
- No design rationale leaked into skill references (skills tell the agent what to do, not why the design exists).
- No settled decision contradicted by the skill's instructions.

### 5. Ship

From the insource registry root:

```bash
cd F:/Projects/Agent/skills/insource
python manager.py viber
```

This reads `viber.json` (resolved via `../../projects/viber/viber.json`), symlinks every listed skill into all agent roots, and reports relinked/unchanged/failed counts.

After install: verify a symlink resolves (`test -f ~/.qoder/skills/viber/SKILL.md`).

## Sync rules

| Situation | Action |
|---|---|
| Doc changes materially (new decision, altered flow) | Re-promote the affected skill reference. |
| Skill changes (bug fix, wording, new mode) | Add a note in the corresponding doc section. Full doc rewrite only if the design itself changed. |
| Doc and skill contradict | The skill wins for agent behavior (it's what executes). The doc wins for design intent. Reconcile by re-promoting or by updating the doc to reflect the shipped reality. |
| New skill added | `viber add-skill <name> --deck <d> --path <p>`, add doc coverage, run installer. |
| Skill removed | `viber remove-skill <name>`, mark doc section superseded, run installer. |

## What this pipeline is not

- Not a CI/CD system. The agent walks these stages conversationally, using the `viber` CLI for census writes.
- Not a release calendar. Promotion happens when a topic settles, not on a schedule.
- Not a gate against iteration. Drafts can be re-opened (thaw). A shipped skill can be revised. The pipeline describes the flow, not a one-way ratchet.

## The census and telemetry

The agent never hand-edits `viber.json`. All reads and writes go through the `viber` CLI
(the `viber` package; `viber.py` is only the launcher shim). Setup once: `uv sync` in this
project creates the isolated `.venv` with typer, pydantic and the `viber` console script.

```bash
viber skill idea-md --content   # what files to read
viber next                      # what to do next, and why
viber lint                      # audit census; deck conflicts surface as ASK USER
viber use idea-md               # record invocation (AGENTS.md instruction)
viber set idea-md blockers '["awaiting user concept"]'
viber refresh idea-md           # re-read frontmatter from disk
```

Per-project data lives at `.viber/.data/`:

| File | Role |
|---|---|
| `viber.json` | Census: every skill's version, description, content paths, fit, blockers, history |
| `telemetry.db` | SQLite: invocations, outcomes, patterns. Feeds `stats`, `patterns`, smarter `next` |

Each skill's `fit` carries its position in the web of work: `after`, `before` and `with` are lists of
relation objects — `{"skill": "<name>", "hint": "<why this edge exists, one line>",
"long_hint": "<the use-case it covers>"}`. `after` names what should run first, `before` what this
feeds, `with` what pairs naturally. The same text describes the edge from both ends, so a relation is
authored once. `viber next` answers not only *which skill* but *why* — it reads the chosen
skill's `after` edges and states each predecessor's hint; `skill <name>` lists the full relation web,
and `--long` adds the use-case detail.

Lifecycle steps own no skills: each step declares `{step, phase, goal, needs, possible_skills, commands}`
— `needs` states the capabilities the step must accomplish, `possible_skills` is the favorite-deck
pool: deck skills declared as useful candidates for that step, from any deck, and `commands` lists
Viber's own v-commands declared at that step. The installed binding lives skill-side in
`fit.serves: [step names]`: any Skill from any deck can serve any step; vinit fills `serves` per
project as it studies what the user actually has. A possible candidate not installed is a suggestion
to surface, never a blocker. `step` shows goal + needs, the resolved roster, and remaining candidates;
`next` walks the roster ordered topologically along within-step `after` edges.

`viber lint` audits the census read-only: schema keys, type/phase enums, dangling
relations and serves, broken skill paths, census-vs-disk version drift, deck-membership mismatches,
candidates missing from the census, unclassified overlaps. It exits 1 on errors or open decisions.
When one skill name is claimed by **two decks** (conflicting versions or sources), lint does NOT pick
a winner — it emits an `ASK USER` finding: the agent must put the choice to the user, then record it
with `set <skill> deck <chosen>`, which rewrites all deck membership lists and logs the decision to
the skill's history. Conflicts are user decisions; the census only surfaces them.

Every skill entry also carries what it *is* and what it's *for*:
- `type` — one of exactly five: `battery` (one skill, several levels/modes over one domain),
  `meta` (its subject is the agent/skill system itself — Viber's own command skills live here),
  `normal` (single-purpose workflow), `hybrid` (a method that also ships execution machinery),
  `otherwise` (cannot be classified — e.g., a skill whose schema is broken or foreign that `vinit`
  met on the web; honest "unknown", never a guessed bucket).
- `use_cases` — concrete situations the skill applies to, across every domain it touches (a skill
  like `mistakes` lists both documentation errors and source-code bug classes). `next` recommendations,
  router guidance and vinit's per-project study read these to judge fit by evidence, not by name.
`set <skill> type <battery|meta|normal|hybrid|otherwise>` and `set <skill> use_cases '["..."]'`
keep both writable through the CLI.

The source project's `viber.json` (at project root) is the master seed. `vinit` reads it, studies the user's actual deck, and writes the per-project census into `.viber/.data/`. The `--census <path>` flag overrides resolution for development against the seed.

## Layout

```
projects/viber/
├── README.md          project identity and map
├── PIPELINE.md        this file
├── pyproject.toml     uv/hatchling package definition (console script: viber)
├── viber.py           launcher shim (keeps `python viber.py <cmd>` working anywhere)
├── viber.json         master seed census (42 skills, decks, lifecycle)
├── src/viber/     the CLI: cli (parsing) · core (rules) · data (IO) · output (shaping)
├── tests/             pytest suites incl. legacy-parity against the seed
├── docs/              design drafts [DR]
│   ├── index.md       global index
│   ├── regime/        how Viber governs a project
│   │   ├── index.md
│   │   ├── lifecycle.md
│   │   ├── router.md
│   │   ├── supervision.md
│   │   ├── structure.md
│   │   └── memory.md
│   ├── commands/      the v-command specs
│   │   ├── index.md
│   │   ├── init.md
│   │   ├── compact.md
│   │   └── flow.md
│   └── diagrams/      .mmd sources + legacy png
└── skills/            shipped agent skills [IP]
    ├── viber/         regime dispatcher + references
    ├── vinit/         entry command
    ├── vcompact/      compaction command
    ├── vflow/         flow command
    └── adapt/         gap-filling intermediate
```