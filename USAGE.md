# Viber CLI — Usage

The common commands, and how to pipe useful information out of the census.
Every example here was run against this repository's master seed (`viber.json`)
before being written down; output shapes are current.

Install and first contact are in [README.md](README.md). This file assumes a
working `viber` (via `uv run viber …` in a checkout, the console script, or
`python -m viber …`). `-C viber.json` appears where the census is not the
default-located one; drop it when `.viber/.data/viber.json` is your project's.

## Bootstrap a project

Run from the target project's root with the CLI already installed:

```bash
viber init --skills-root "<installed-skills-folder>"
viber registry --skills-root "<installed-skills-folder>" -f json
viber registry --skills-root "<installed-skills-folder>" -o "skill-metadata.md"
viber lint
```

`--skills-root` / `-S` is repeatable; each root is an installed-skills folder
whose immediate children contain `SKILL.md`, or one skill directory itself.
Canonical symlink aliases are deduplicated. Different sources declaring the
same skill name are reported rather than silently selecting a winner.

`init` creates `.viber/.data/viber.json` unless `-C`, environment, or configuration
selects another census file. It never uses the read commands' root-seed fallback
as a destination. Installed paths become absolute realpaths; unavailable skills
keep null paths and installation blockers. The command validates and lints before
writing, resets copied project progress/history, and preserves generic task
instructions for `/vinit` to personalize. A repeat run refuses the existing
census; even `--force` applies only to a report file, never to census replacement.

Explicit skill roots win over the seed's source/deck locations. Without a match,
a checkout can use its original skill locations; an installed wheel requires
registered roots for skills not otherwise available. The master seed is packaged,
not fetched from the network. No skill installation happens automatically.

`registry` exports all skills in the supplied roots, not just the seed roster.
Its text/file format is an escaped Markdown metadata table; terminal rich mode
uses boxed tables, and `-f json` preserves structured values. Missing triggers
fall back to the description's trigger clause, then its first sentence. Invalid
YAML or unusable metadata fails with the source path. Duplicate sources return
exit 1 with conflict details. Classification, areas, exclusions, and the final
annotated `.viber/registry.md` remain the agent `/vinit` workflow's responsibility.
Neither shell command edits AGENTS.md, ignore rules, or memory ledgers.

## 1. The daily loop

```bash
viber situation            # everything a competent colleague would ask: status, roster, usage, next, owed decisions
viber next                 # next unblocked skills — each with do:, why:, and the predecessor reason
viber next -n 3            # cap the candidate list
viber status               # phase, current step, counts — the minimal heartbeat
viber use steering         # record "I am doing steering now" (feeds last:/patterns)
viber use idea-md reveal steering   # bulk: record several previously-done skills at once
viber use agents-md --note "skeleton only"   # invoke and attach a self-note in one call
viber outcome steering ok  # close it — optional free-text note as a third argument
viber note --on agents-md "add REACH fence after Foundation"   # a note without running the skill
viber lint                 # census audit; exit 1 with findings, conflicts surface as ASK USER decisions
viber lint --remote        # + compare deck clones against their configured GitHub upstreams (network)
viber now                  # which project you are on, its location and step
```

The golden pattern for an agent session: `situation` to orient, act, `use` +
`outcome` to keep the ledger honest, `lint` before declaring done.

When a `recurring` skill (e.g. `agents-md`) has been started but never marked `ok`, `next` and
`situation` keep it visible in a **REVISIT** pool even after the project advances past its step —
the reminder that unfinished recurring work was otherwise forgotten. Recording `outcome … ok` clears
it. To work on a different project from anywhere: `viber --project <id> <cmd>`, or
`viber project use <id>` to make it the default (see `docs/commands/project.md`).

## 2. Reading the census

```bash
viber skill steering                 # full card: identity, fit, relations, content manifest
viber skill steering --brief         # one line: name, version, description
viber skill steering -P minimal      # identity block only
viber skill steering --long          # relation long_hint detail (the use-case each edge covers)
viber step "Idea & Understanding"    # the step: roster (ready/blocked/command), needs, candidates
viber deck author                    # deck card: registry, remote, membership; no name = all decks
viber list --by type                 # whole roster sorted; also --by step|deck|version
viber list -b                        # compact name+version table
```

Writing goes through the same doors only via the write commands (`init`, `set`, `log`, `note`,
`add-skill`, `remove-skill`, `refresh`, and the `project` sub-app) — the CLI is the sole writer of
the census, the registry, and the project data; hand-editing `viber.json` is the forbidden cure for
every ailment.

## 3. `fields` — the self-documenting surface

```bash
viber fields                         # all 119 artifact fields: Field · Type · Req · Limit · Meaning
viber fields fit.doing               # one field, fully: writers, consumers, default, resolved limit line
viber fields groups                  # the 16 families with their row counts
viber fields -G telemetry            # one family (-G env, -G frontmatter, -G memory …)
viber fields -N hint                 # substring over paths (relation.hint, long_hint, argument-hint …)
viber fields -G skill -N history     # filters combine
```

Groups cover the whole surface, not just the census JSON: `census`, `deck`,
`step`, `skill`, `fit`, `relation`, `content`, `history`, `frontmatter`,
`config`, `telemetry`, `env`, `memory`, `settled`, `learnt`, `registry`
(plus `skill.<name>` map-key rows). Caps live in `src/viber/models/limits.py`
and the `limit` column resolves against it — what the CLI enforces and what it
explains cannot drift.

## 4. Piping JSON out

`-f json` prints the profile-selected payload. Stdout JSON is native UTF-8;
piped output is ANSI-free by structure, so any JSON consumer works directly:

```bash
# names of unblocked next candidates
viber next -f json | python -c "import json,sys; print(*[c['skill'] for c in json.load(sys.stdin)['candidates']])"

# the same with jq, if you have it
viber next -f json | jq -r '.candidates[].skill'

# status fields for a dashboard line
viber status -f json | python -c "import json,sys; d=json.load(sys.stdin); print(d['phase'], d['step'])"

# lint as a machine gate — exit code + payload
viber lint -f json > lint.json && echo "clean" || cat lint.json

# field rows for a generated reference table
viber fields -G frontmatter -f json | jq -r '.fields[] | [.field, .type, .meaning] | @tsv'
```

The `profile` decides how much arrives; `include`/`exclude` carve single keys:

```bash
viber skill steering -P full            # everything incl. long_hints and history
viber skill steering -f json -E content # drop one payload key (comma list for more)
viber next -P full -f json              # adds needs, commands, previous, long detail
viber config list -P full -f json       # adds plugin_dirs
```

`-I/--include` and `-E/--exclude` address keys by their `fields.py` names; a
wrong name fails loudly with the closest suggestion — there is no `none`.

Exit codes are the contract: `0` success, `1` invalid input / findings /
refusals, `2` usage errors and write-cap rejections. A rejection prints the
full Error-as-Truth line — identity, cap, received count, why, recovery:

```bash
$ viber set idea-md doing "$(python -c 'print("x"*2500)')"
error: DOING_MAX_CHARS — doing cannot exceed 2000 characters (got 2500). fit.doing is
the concrete next-task paragraph, not an essay Fix: tighten it: viber set <skill> doing
$ echo $?
2
```

## 5. Files and redirects

```bash
viber next -o plan.txt          # compact plain flush (report lands on stderr, not stdout)
viber fields -f json -o f.json  # JSON file — kept ASCII-escaped, byte-stable
viber next -o plan.txt --force  # explicit overwrite permission
viber lint > report.txt         # shell redirect still gets rich layout bytes, zero ANSI
```

`--out` is the machine path: always plain renderers, never boxes, never color.

## 6. Display switches

| Want | Use |
|---|---|
| plain everywhere | `-nr` on the command, or `VIBER_RICH=0` for the shell |
| no color but keep layout | `NO_COLOR=1` (color axis only; layout unchanged) |
| deterministic width | `COLUMNS=120` (clamped 60–240) |
| grep-friendly output | pipe it — layout stays rich, ANSI is zero — or `-nr` for flat text |

The one hard rule: nothing that is not a live terminal ever receives ANSI
bytes. `viber <cmd> -f json | jq` is structurally safe; `viber <cmd> -o file`
is plain; color exists only where a human is looking.

## 7. Config the long way once

```bash
viber config list                        # all six chain keys with value, source layer, default
viber config get profile                 # one key, traceable
viber config set profile full            # project layer: everyone sharing the repo gets full payloads
viber config set format json -u          # user layer: my machine is a machine
viber config unset profile               # back to inherited
viber config path                        # where both layers live
```

Precedence is `flag > env (VIBER_*) > project config > user config > default`;
`viber fields -G config` and [docs/regime/config.md](docs/regime/config.md)
own the details.

## 8. Cross-cutting flags & resume

```bash
viber use idea-md --note "first pass only"   # attach a self-note while running a skill
viber note --on agents-md "add REACH fence"  # a note with NO skill run
viber skill agents-md --notes                # show the notes ledger on the card
viber next -n 3 --project <id>               # resume that project for this call
viber project use <id>                       # make it the default (local folder still wins)
viber now <id> --details                     # that project: location, step, counts, last action
viber project link <id> --to <newdir>        # a moved folder: re-bind its id
```

`--note` and `--project` are accepted across the command set; `--details` on `now`/`project status`;
`--notes` on `skill`. `--banner`/`--no-banner` toggles the project START/RESUME/LINK banners (text
only — `-f json` never carries them, so it stays clean for piping).

## 9. Notes from real terminals

- **`| head` on Windows**: closing the pipe early can print
  `OSError: [Errno 22]` after the output — a Python-on-Windows artifact of the
  broken pipe, not a viber failure; the data before it is complete.
- **`$?` after a pipe** reports the *last* command in the pipeline; to test
  viber's own exit code, run it unpiped or use `${PIPESTATUS[0]}` in bash.
- **rich tables at 80 columns wrap** — long rows fold. For reading: widen
  (`COLUMNS=120`); for tooling: `-f json` or `-nr`. Never parse wrapped boxes.

## 10. Reference points

- [README.md](README.md) — what Viber is and how to install it
- [docs/regime/display.md](docs/regime/display.md) — the two-axis display doctrine
- [docs/regime/limits.md](docs/regime/limits.md) — Error-as-Truth boundary model
- [docs/commands/project.md](docs/commands/project.md) — multi-project, resume, linking, details
- [docs/commands/note.md](docs/commands/note.md) — the `--note` flag and `viber note`
- [docs/regime/config.md](docs/regime/config.md) — the settings chain
- `viber fields` — live answer for every artifact field and its limit
