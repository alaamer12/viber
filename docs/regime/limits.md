# Viber Limits — Bounded Fields, Truthful Errors

> Owns the boundary doctrine: why every census field has a cap, the Field–Error–Violation shape of limit errors, and how the CLI communicates them. The numbers themselves live in exactly one place (`src/viber/models/limits.py`) and the authoritative display is `viber fields` — one row per census field, its meaning, writers, consumers, and limit (words in `src/viber/models/fields_doc.py`) — this doc never restates the table.

## 1. Overview

The census is written by agents under time pressure. Any unbounded field is an
eventual explosion: a 100-record `history`, a 100k-char `description`, a `blockers`
list nobody can read. So every field carries a maximum — chosen generous enough to
never constrain honest work, tight enough that violation always means a mistake, not
a use case.

This implements **Error as Truth** (amr-tech, "Error as Truth"): every distinct
failure condition gets its own identity; errors never collapse into "invalid input";
the message carries what the application already knows — which field, which cap, how
many were received, and the exact command to recover.

### Core Principle

**The application knows the boundary; therefore the error must speak it.** A cap
without a named violation is a wall; a violation without a recovery line is a trap.
Both are the designer's failure, not the agent's.

## 2. The three enforcement moments

| Moment | What happens | Why this shape |
|---|---|---|
| **Write** (`set`, `add-skill`, `log`, `refresh`) | hard reject, exit 2, cataloged message: identity, cap, got, recovery command | the agent attempting the violation is present — tell them exactly what to do instead |
| **Write to a rolling ledger** (`history`) | never rejects: appends, evicts oldest past the cap, and **acks the eviction** in the response line | history is a ledger, and blocking a routine `refresh` because a skill has a rich past would punish honesty; silent trimming would lie — so it trims *and says so* |
| **Load** (census already containing violations — only a hand-edit, itself forbidden, produces this) | file stays readable; every over-cap becomes a lint **error** with identity + got + fix | a hard-fail at load would brick every command, and the doctrine forbids hand-editing the cure — that is a lockout, the anti-pattern this doc exists to avoid |

## 3. Field → Error → Violation

Ownership is explicit and duplication is intentional: `DESCRIPTION_MAX_CHARS` and
`DOING_MAX_CHARS` are **different** violations even though both count characters —
different fields, different caps, different recoveries. One violation never serves
two fields. Identities are `{FIELD}_{KIND}` with kinds:

- `MAX_CHARS` — a string longer than its ceiling
- `MAX_ITEMS` — a list longer than its ceiling
- `EMPTY` / `BAD_DATE` where the field's existence rule requires it

Every identity exists in `limits.py` exactly once, with its cap, one-line **why**
(the purpose the bound protects), and its **recovery** (the exact move that fixes
it: the `/vcompact` skill before a full history, shorten `SKILL.md` frontmatter
before `refresh`, split relations, etc.). Messages are assembled from the catalog, so what
the CLI prints always matches what `viber fields` promises — drift is impossible
because both read the same table.

## 4. Audience calibration

| Audience | Gets |
|---|---|
| agent at a rejection | identity, cap, received count, recovery command — exit 2 on stderr |
| machine (`-f json`) | the same strings verbatim in `detail`; identities parse stable |
| human | `viber fields` rich table: Field · Type · Req · Limit · Meaning — every census field explained, live from code; `viber fields <path>` adds writers, consumers, and the full limit line |

## 5. Rules

- One catalog: caps exist only in `limits.py`; lint, guards, and `fields` read it.
- No violation message without a recovery line.
- No silent trim, no silent truncate, ever; eviction is announced in the ack.
- Bounds are generous by default — a cap you hit during honest work is a bug in the cap, not in the agent; raise it in the catalog and the docs follow automatically.
- `viber fields` is read-only and offline; help texts point at it (`caps: viber fields`).

## 6. Open Items

1. Per-project cap overrides (a project genuinely needing richer history) — would
   make caps configurable and the catalog's single-home promise murkier; nothing shipped.
2. Whether `lint --fix` may auto-trim rolled ledgers (it could, honestly, since the
   trim is the rolling policy already).
