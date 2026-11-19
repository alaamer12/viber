# Project — driving many projects from one install

> `viber project …` (a sub-app) and top-level `viber now`. Multi-project data: create a project's
> census and mint its id, resume it by id from any directory, re-bind it when its folder moves, and
> list/inspect them all. Settings precedence lives in [../regime/config.md](../regime/config.md)
> (§3.1); the id itself is stored as `project_id` in the census (see `viber fields project_id`).

## The model

One viber install, many projects. Each project's data is **self-contained** under
`<project>/.viber/.data/` (census `viber.json` + `telemetry.db`). A **project id** — a short
location fingerprint (a hash of the project folder's path) — names a project across machines'
working directories. It is minted when the data is created and recorded in the census, so an agent
can keep it in `AGENTS.md`. It is not sensitive.

A user-level registry, `<user config dir>/projects.json`, maps **id → folder** so `--project <id>`
resolves without a path. The fingerprint is derived from the folder, so it is a convenience, **not a
guarantee**: move the folder and the id no longer points anywhere — that is what `link` fixes.

## Commands

```bash
viber init                          # create data for the current folder; print its id + resume line
viber project create <dir>          # same, for a project at another path
viber project use <id>              # make <id> the default so bare `viber <cmd>` resumes it
viber project use --none            # clear the default
viber --project <id> <cmd>          # one-off resume: run <cmd> against that project (next/situation/…)
viber now                           # where am I — active project id, location, phase, step
viber now <id> --details            # that project's counts, decks, recurring-pending, last action
viber project list                  # every registered project with link health (ok | missing)
viber project status [id] --details # same detail view via the sub-app
viber project link <id> --to <dir>  # re-bind a moved/renamed project (or adopt unregistered data)
```

## Selection precedence

Which project a command runs against:

`-C <census>` (explicit file)  →  `--project <id>` flag  →  `VIBER_PROJECT` env  →  the **nearest
enclosing project** (walks up from cwd to the first folder with a `.viber/.data`)  →  the `project`
user-config default (`project use`). An enclosing folder beats the saved default, so running from
`proj/src/deep` operates on `proj`; pass `--project` to override. The default resumes only where there
is no enclosing project data. The walk-up stops at a `.git` boundary (a dir, or a worktree/submodule
`.git` file), so a checkout nested inside another never borrows the parent's data — init the
worktree/submodule itself, or point at it with `--project`/`-C`.

## Linking after a move

When a project folder is relocated, `viber project list` shows its entry with `link: missing`. Re-bind:

```bash
viber project link <id> --to <newdir>
```

This validates `<newdir>/.viber/.data/viber.json` exists, repoints the registry, refreshes the
stored fingerprint, and prints a `LINKED <id>` banner with the new resume command. If the id is
unknown to the registry, `link` adopts the folder's own `project_id` (recovering data whose registry
entry was lost).

## Notes

- **Branches are safe.** The id is derived from the folder path, not the file, so `git checkout`ing a
  different branch (or committing `.viber/.data/viber.json`) keeps the same id; the telemetry/census
  files persist across branch switches. A census committed with a foreign `project_id` is overridden by
  the location (reported as `stored_id_differs`). A separate `git worktree` per branch is a separate
  location — init it or `--project`/`link` it; the `.git`-boundary rule stops it borrowing the parent.
- `--project` is threaded on the daily-loop commands (`next`, `situation`, `status`, `use`,
  `outcome`, `set`, `log`, `note`, `skill`, `now`); every command honors the saved default.
- The START/RESUME/LINK banners print only in text mode (never inside `-f json`) and can be silenced
  per-command with `--no-banner` for scripting.
- `project list` / `status` emit the `project` payload; `--json` and `-P full` expose every field.
