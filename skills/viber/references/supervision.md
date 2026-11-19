# Viber Supervision — The Umbrella Mode

## 1. Overview

Viber Supervision is the mode in which **Viber owns the project's engineering-discipline artifacts**. When it is
active, the documentation and procedure outputs of every participating Skill are gathered under the project's
`.viber` directory, while the project's code and its root-files stay where they are.

The idea is **disciplined vibe-engineering**: the freedom of vibe coding, with the discipline of a single,
visible umbrella over everything the project decides, specifies, and learns. Viber does not touch the code; it
organizes the knowledge around the code.

This document defines four things:

1. **Activation** — how an agent knows Viber supervision is on (section 2).
2. **Participation** — which Skills fall under the umbrella (section 3).
3. **The frontmatter tag** — how a Skill declares its eligibility (section 4).
4. **The rerouting rule** — where a participating Skill's output goes (section 5).

### Core Principle

**Ownership follows the information's domain; the umbrella gathers only what has no other owner. Viber
never moves what must stay to function, and never touches code.**

Decide *who owns a piece of information* before *where its file sits* (section 5.0). A domain Skill owns its
own content in its canonical working directory — a documentation Skill's specification tree, the rulebook in
`AGENTS.md` — and Viber's ledger points to it rather than hoarding a copy. The umbrella gathers relocatable
knowledge that has **no anchored domain home** (a loose prototype, a plan note, a skill-state dot-folder). A
root-file (`README.md`, `AGENTS.md`), production code, and a Skill's canonical working directory stay where
they function. The test is not a fixed list and not "is it relocatable?" alone — it is two questions: *who owns
this fact?* and *must this live here to function or by convention?*

---

## 2. Activation — How the Agent Knows

Viber supervision is active when the project's `AGENTS.md` carries a **Viber declaration**. The agent reads
`AGENTS.md` at the start of every session and detects it.

The wording is **flexible** — any clear declaration counts:

- `## Viber` section (the canonical form `init` writes — see `vinit` skill → `references/init.md` section 3).
- "This project uses Viber."
- "Vibe Mode On."
- any equivalent sentence that states the project follows Viber.

The canonical `## Viber` section is preferred because it also points to the registry and the memory files. But
the agent recognizes the intent, not one exact string. When no Viber declaration is present, supervision is
**off**: Skills write to their normal paths, and nothing is rerouted.

`init` ensures the declaration exists (it adds or refreshes the `## Viber` section). Turning supervision off is
the user's decision — removing the declaration — never something the agent does on its own.

---

## 3. Participation — Which Skills Are Under the Umbrella

**Deck membership is the gate.** A Skill that is in the user's deck (registered) falls under Viber's umbrella by
default — **even if it carries no frontmatter tag**. This is what lets deck Skills, not only Viber's own
lifecycle Skills, participate without being rewritten.

A Skill is under the umbrella when **all** of these hold:

1. Viber supervision is **active** (section 2).
2. The Skill is **in the deck** — a registered Skill (global or project-level) or an extension-source Skill.
   Viber's own lifecycle Skills always participate; they are Viber.
3. The Skill is **not excluded** by the user (section 3.1).
4. The Skill is **not tagged `viber: separated`** (section 4).

An untagged deck Skill participates (default `part`). A Skill **outside the deck** — an Opensource Deck Skill
used one-off, not registered — is **not** under the umbrella's guarantee until it is registered or attached via
`adapt`.

### 3.1. `init` Asks About Exclusions, and States the Consequence

Because deck membership decides participation, `init` **asks the user** whether any deck Skills should be
excluded from the umbrella, and **clarifies the consequence** of each choice:

| Choice | Consequence |
|---|---|
| **In the deck / under the umbrella** | Viber reroutes the Skill's relocatable output into `.viber`, and remembers it (the memory files, the Router's tracking). The Skill's work is part of the project's disciplined record. |
| **Excluded / out of the deck** | Viber does **not** guarantee control or always-remembering. The Skill writes to its normal path; its output is not gathered under `.viber` and not tracked as part of the umbrella. |

The user decides per Skill. `init` records the exclusions in the registry (section 4 of `vinit` skill → `references/init.md`) so the
Router and every later session honor them. Excluding a Skill is never silent — the consequence is stated first.

---

## 4. The Frontmatter Tag

Every Skill that Viber uses declares its eligibility with a frontmatter tag in its `SKILL.md`:

```yaml
---
name: <skill-name>
description: <...>
viber: part        # or: separated
---
```

| Value | Meaning |
|---|---|
| `viber: part` | The Skill can join the umbrella. Its relocatable output is rerouted when supervision is active. |
| `viber: separated` | The Skill stays independent. Its output is **not** rerouted, even if it is in the deck — for Skills that operate outside the project's discipline (e.g. a Skill that writes the user's global config). |
| *(no tag)* | Treated as `part` **if the Skill is in the deck**. Deck membership, not the tag, is the primary gate. |

The tag is a Skill's self-declaration; deck membership and the user's exclusions are the operative controls.
`init` reads the tag as metadata (it reads only the top of `SKILL.md`, never the body) and records it in the
registry. The tag never overrides a user exclusion, and a `separated` tag opts the Skill out regardless of deck
membership.

**Examples:**

```yaml
# a documentation Skill — produces project specs; joins the umbrella
viber: part
```
```yaml
# personalize — writes the user's GLOBAL instructions, not this project's artifacts
viber: separated
```

---

## 5. The Rerouting Rule — Where Output Goes

### 5.0. Information ownership — decide the owner before the path

Before asking *where a file sits*, ask *who owns this piece of information*. Every fact has one owning
artifact, decided by its nature — not by whether it is relocatable, and not by Viber's preference for its own
files:

| The information is… | Its owner writes it in… | Viber's ledger… |
|---|---|---|
| Domain knowledge — a product requirement, a domain entity, a capability, a policy, a stack or architecture decision, a feature's behavior, a schema | the owning domain Skill's canonical artifact — its specification tree, feature docs, reference schemas, or the `AGENTS.md` rulebook, wherever that Skill writes them | points to it, and keeps the decision's question→answer→reason in `settled.md` |
| A conversational fact — an open or deferred question, a settled decision and its reason, a learned fact about the user or project | Viber memory: `.viber/memory.md`, `settled.md`, `learnt.md` | owns it; the domain doc may reference the decision |

**One fact, one home; pointer, not copy.** The owning artifact holds the operative content once. The other
store carries a brief pointer — never a duplicated body. This is the same one-fact-one-home rule a
documentation Skill enforces across its own tiers and `memory.md` enforces for the ledger: Viber's memory is an
index and a provenance ledger, not a second specification and not a mirror of every domain Skill's docs.

The balance runs both ways, per piece of information: a spec detail is written in the owning Skill's doc and
*mentioned* in Viber (`settled.md` points to it); a deferred question is written in Viber and *mentioned* in
the domain doc it belongs to. Viber does not pull a domain Skill's content into `.viber` to claim it, and a
domain Skill does not restate the ledger's questions and reasons.

**Ownership also anchors the path.** A participating Skill's canonical working directory is part of its
function: a documentation Skill reads and writes its own specification tree, so that tree stays at the project
root — rerouting it into `.viber` would break the Skill that owns it. The same holds for any domain artifact
whose path its Skill depends on (feature docs, reference schemas). The umbrella gathers relocatable knowledge
with **no anchored domain home**; it never relocates a domain Skill's working artifact away from the path that
Skill needs. When ownership and placement genuinely conflict, ask the user (section 5.3).

### 5.0.1. What the umbrella gathers

When supervision is active and a Skill participates, its **ownerless relocatable artifacts** are written under
`.viber`, preserving the path they would normally have relative to the project root:

```text
<normal-path>  →  .viber/<normal-path>
```

| Skill output | Owner / canonical home | Placement |
|---|---|---|
| a domain Skill's specification tree | the owning Skill's canonical path | anchored — stays; the ledger points to it |
| feature docs, reference schemas | the owning Skill's canonical path | anchored — stays; the ledger points to it |
| a loose prototype | no anchored domain home | `.viber/prototype/…` |
| a plan note | no anchored domain home | `.viber/docs/plans/…` |
| a skill-state dot-folder | relocatable state | `.viber/<its-normal-path>` |

The path is preserved, not flattened: `.viber/docs/plans/2026-11-19-auth.md`, not `.viber/auth.md`. The
umbrella mirrors the layout of the knowledge it gathers inside `.viber`; it does not flatten or claim a domain
Skill's anchored tree.

### 5.1. The Root-File Test (what stays)

Before rerouting an artifact, ask: **is it a root-file or code?**

- **Root-files stay at the project root.** `README.md` and `AGENTS.md` are root-files — they are conventionally
  and functionally anchored at the root (the harness loads `AGENTS.md` from there; `README.md` is the repo's
  front door). Moving them into `.viber` would break that. They are **never** rerouted.
- **Production code stays.** Code directories — whether **flat** (code lives directly in the project, not
  grouped under a single folder) or under `src/` (or any group directory) — are outside Viber's control. Viber
  never moves or reroutes code.
- **Layout homes come first.** The canonical layout (`structure.md`) assigns fixed homes that sit outside
  the umbrella by design: run output goes to `artifacts/<producer>/`, the agent's temporary work to
  `scratch/<task>/`, utilities and operations to `tools/` and `scripts/`.
- **A domain Skill's working directory is anchored.** its specification tree, feature docs, and reference schemas stay
  where their owning Skill reads and writes them (section 5.0); the ledger points to them, it does not reroute
  them.
- **Ownerless relocatable knowledge goes under `.viber`.** A loose prototype is *not* a root-file and has no
  anchored domain home: `prototype/` works just as well at `design/prototype/`, so it goes under the umbrella.
  The same for plan notes, flows, and skill-state dot-folders — knowledge with no other owner or layout home.

The test is the principle, not a memorized list: *who owns this fact (section 5.0)? must it live at the root,
is it code, is it a Skill's anchored working directory, or does the layout give it a home (`artifacts/`,
`scratch/`, `tools/`, `scripts/` — see `structure.md`)?* If any of those hold, it stays there. Ownerless
relocatable knowledge with no other home → `.viber`.

### 5.2. How the rerouting is applied

The rerouting is a convention the **agent applies when driving a Skill** under supervision; the Skill itself
need not be Viber-aware. The agent checks the registry (does this Skill participate?), information ownership
(who owns this fact — section 5.0), and the root-file test (is this artifact ownerless and relocatable?), then
writes only the ownerless relocatable part to `.viber/<normal-path>`. Domain-owned content stays in its Skill's
canonical artifact and the ledger points to it. This is how deck Skills join the umbrella without modification.

### 5.3. Turning Supervision On Over an Existing Project

When supervision is activated for a project whose **ownerless** relocatable artifacts already sit at the root
(a loose `docs/plans/`, for example), Viber does not move them silently and does not leave the choice
undeclared: it **asks the user**, and **recommends moving them under `.viber`** — one umbrella over the
project's ownerless knowledge is the point. A domain Skill's anchored tree (its specification tree, feature
docs, reference schemas) is **not** a migration candidate: it stays where its Skill reads it (section 5.0).
Declining is fine: the artifacts stay where they are, and the rerouting rule governs future output.

The same pattern settles every case supervision flags as ambiguous — an unclear exclusion, or an artifact that
is partly code and partly documentation (a codegen Skill): Viber **asks the user and recommends the `.viber`
placement** for the relocatable part, and records the choice. Never a silent auto-move, never a silent skip.

---

## 6. What Viber Owns, and What It Does Not

| Viber owns (`.viber/…`) | Owned by its domain Skill — stays at its canonical path | Stays at the project root |
|---|---|---|
| The memory files (`memory.md`, `settled.md`, `learnt.md`) | A documentation Skill's specification tree | `AGENTS.md` (the marker + rulebook) |
| The registry (`registry.md`) and Router state | Feature docs, reference schemas — their owning Skill's path | `README.md` (the repo front door) |
| Ownerless relocatable knowledge: prototypes, plan notes, flows, skill-state | Architecture, glossary, and other domain artifacts — their owning Skill's path | Production code — flat or `src/` (any layout) |

Viber owns the **conversational ledger and the ownerless knowledge around the code**, never the code itself and
never a domain Skill's content. The ledger points to where domain knowledge lives; it does not duplicate it
(section 5.0, `memory.md`). The full canonical layout — `tools/`, `scripts/`, `artifacts/`, `scratch/`, and the
git treatment of each — is `structure.md`; its section 6 maps supervision's outputs to their homes.

---

## 7. How It Connects

| Component | Relationship to Supervision |
|---|---|
| `init` | Ensures the AGENTS.md declaration; reads the `viber` frontmatter tag; asks about deck exclusions and states the consequence; records participation in the registry; creates the `.viber` directory. |
| **Router** | Reads the declaration (is supervision active?) and the registry (which Skills participate?). When driving a participating Skill, decides information ownership (section 5.0) and reroutes only its ownerless relocatable output. |
| `lifecycle` | Every lifecycle Skill participates; its ownerless relocatable outputs land under `.viber` when supervision is active, while domain-owned outputs (e.g. a documentation Skill's specification tree) stay anchored. |
| `memory` | The memory files already live under `.viber`; they are the umbrella's conversational ledger (see `memory.md`). |
| `adapt` | Attaching a deck Skill to the project brings it under the umbrella; a Skill created by `adapt` declares its `viber` tag. |
| `structure` | The canonical layout gives run output (`artifacts/`), agent temp (`scratch/`) and utilities/operations (`tools/`, `scripts/`) fixed homes outside the umbrella; supervision reroutes only knowledge without a layout home (see `structure.md` section 6). |
| `agents-md` | Owns `AGENTS.md` (a root-file, never rerouted); the Viber declaration lives there. |

---

## 8. Rules

- **Code is never touched.** Viber reroutes knowledge artifacts only; production code (flat or `src/`) stays.
- **Root-files stay.** `README.md` and `AGENTS.md` are never rerouted.
- **Ownership before placement.** Decide who owns each fact (section 5.0); domain content stays in its Skill's
  canonical artifact and the ledger points to it — pointer, not copy. One fact, one home.
- **A Skill's working directory is anchored.** its specification tree, feature docs, and reference schemas stay where
  their owning Skill reads them; the umbrella never reroutes them away.
- **Ownerless relocatable artifacts go under `.viber`**, preserving their relative path.
- **Layout homes win over the umbrella.** `artifacts/`, `scratch/`, `tools/`, `scripts/`, root-files and code keep their canonical placement (`structure.md`); `.viber` gathers the remaining ownerless relocatable knowledge.
- **Deck membership is the gate.** In-deck Skills participate by default, even untagged; out-of-deck Skills are
  not guaranteed.
- **Exclusions are explicit.** `init` asks and states the consequence; an exclusion is recorded, never silent.
- **The tag declares, the deck decides.** `viber: separated` opts a Skill out; an untagged deck Skill is `part`.
- **Activation is the user's.** Supervision is on when `AGENTS.md` declares it; the agent never turns it off.
- **Flagged items are asked, not assumed.** On migration and on ambiguous artifacts, Viber asks the user and recommends the `.viber` placement, then records the choice (section 5.3).
- **No secrets.** Nothing private is written into the registry or the rerouted artifacts' index.

---

## 9. Boundaries

### Supervision SHOULD

- Detect the Viber declaration in `AGENTS.md` at session start.
- Decide information ownership first (section 5.0): domain content stays with its Skill, the ledger points to it.
- Reroute participating Skills' ownerless relocatable artifacts to `.viber/<normal-path>`.
- Apply the root-file test before moving anything.
- Honor deck membership, the `viber` tag, and the user's recorded exclusions.
- Keep the code, root-files, and domain Skills' anchored working directories untouched.

### Supervision SHOULD NOT

- Move or reroute production code, `README.md`, or `AGENTS.md`.
- Hoard a domain Skill's content into `.viber`, or duplicate a spec/rule body the ledger only points to.
- Reroute a Skill's anchored working directory (its specification tree, feature docs, and reference schemas) away from
  the path that Skill reads.
- Reroute a Skill that is excluded, `separated`, or out of the deck.
- Flatten the path — the relative layout is preserved inside `.viber`.
- Turn itself off, or assume supervision is on without a declaration.
- Require a Skill to be rewritten to participate — the agent applies the umbrella.
- Guarantee control or memory for a Skill outside the deck.

---

## 10. Flow

The supervision decision path is diagrammed in [`supervision-flow.mmd`](../assets/diagrams/supervision-flow.mmd): declaration → participation → the root-file test → `.viber` or root.

---

## 11. Open Items

1. **Exclusion UX.** The exact form of `init`'s exclusion question (per-Skill prompt vs a single list) and how
   exclusions are revisited on a later `init`.

Resolved: migration asks the user and recommends `.viber` (section 5.3); mixed code-and-doc artifacts split
per artifact, the doc part under the umbrella, the code part at root, ambiguity asked.