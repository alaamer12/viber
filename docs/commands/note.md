# Note — the agent's self-notes

> `viber note --on <skill> "…"` and the global `--note` flag. Notes are a first-class ledger on the
> census JSON, visible on the skill card, separate from the machine `history` trail and the
> telemetry outcome note. Field meanings: `viber fields skill.notes`.

## Why

An agent makes a decision, spots a caveat, or defers a piece of work and needs to leave itself a
marker — not a lifecycle event, not code, just a note attached to a skill or to the project. Notes
persist in `viber.json` so the next session (or `next`/`situation`'s revisit reason) sees them.

## Commands

```bash
viber note --on <skill> "text"      # write a note WITHOUT running the skill
viber note --on . "text"            # a note on the project itself (census.notes)
viber use <skill> --note "text"     # record the invocation AND attach the note
viber set <skill> <field> <value> --note "text"   # write the field and note why
viber log <skill> <event> --note "text"           # a history event plus a self-note
viber skill <skill> --notes         # show the notes section on the card (FULL profile)
```

The `--note` flag is accepted on the target-bearing commands above and on `outcome` (where the
positional note is also kept on the card). Each note is `{date, text, context}`; `context` records
which command attached it (`note`, `use`, `outcome`, `set`, …).

## Shape and limits

- One note per skill is `300` characters; the ledger rolls at `100` notes per skill — the oldest
  evicts on append and the ack says so. Prune settled notes, or `vcompact` them. (Caps: `viber
  fields notes`.)
- Notes are hidden from the default `skill` card view (they live in the FULL profile) — pass
  `--notes` or `-P full` to see them. They are always in the `-f json` census.
- Notes are census state, independent of telemetry: with `telemetry=false`, `viber use <skill> --note`
  and `viber outcome <skill> <result> "<note>"` still write the note to the card (they just record no
  invocation) and the ack says so.
- Notes never substitute for the domain spec: a decision that belongs in a Skill's own artifact goes
  there, and the ledger points to it — pointer, not copy (see [../regime/supervision.md](../regime/supervision.md)).

## Example

```bash
viber use agents-md
viber outcome agents-md skip --note "skeleton only; add the REACH fence after Foundation"
viber next            # after the phase advances, agents-md shows under REVISIT with that note
```
