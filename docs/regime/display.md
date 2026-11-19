# Viber Display — Presentation Modes

> Owns how viber *looks* in a terminal: the two capability axes, the resolution order, the single rich importer, and the byte-clean guarantees for pipes, files, and JSON. What the chain keys are and why display is not one of them is `config.md`. Diagram: none (a mode table is clearer than a graph).

## 1. Overview

Every byte viber writes to stdout passes one sink (`output/emit.py`) that picks a presentation mode per
run. Two axes, deliberately separate:

| Axis | Values | Decided by |
|---|---|---|
| **layout** | `rich` (boxed tables, panels) or `plain` (compact ASCII) | capability + flag + env (section 2) |
| **color** | ANSI escapes on/off | layout choice **and** whether stdout is a real terminal |

The split matters: `Console(force_terminal=True, no_color=True)` still emits escapes — a "no color" setting
never makes output byte-safe for pipes. Only `is_terminal == False` does that. So color is granted *by the
tty*, and the tty is consulted once, in `resolve_display()`.

## 2. Resolution order

```text
--no-rich / -nr flag   →   VIBER_RICH env (1/0/true/false…)   →   auto: rich importable → rich layout
```

Layout is **not** gated on the terminal — every command that displays output displays it rich, piped or
not; the terminal only gates *color*. A piped rich render is full box layout with zero ANSI bytes (a plain
`Console` writing to a buffer), so "rich everywhere stdout goes" costs pipes nothing but readability.
The remaining plain paths are the machine contracts: `--out` files, and `-f json` whenever stdout is not
a live terminal.

- `--no-rich` (short `-nr`) is terminal: plain layout, no color, nothing overrides it. No positive `--rich`
  flag exists on purpose — typer's decl parsing would bind `-nr` to the *positive* half of a
  `--rich/--no-rich` pair, inverting the name. Force-on is `VIBER_RICH=1`.
- A bad `VIBER_RICH` value warns and falls to auto — the chain doctrine: a read never bricks a run.
- `NO_COLOR` is honored by rich itself (color axis only); it never changes layout.
- Piped/redirected stdout gets **rich layout, zero ANSI**; `--out` files stay plain — machine contracts.
- `-f json` obeys the same color rule as everything else: a **live tty** gets syntax-colored JSON
  (`display_json`, ansi_dark theme); piped or redirected JSON returns the bytes untouched. Stdout JSON
  is native UTF-8 (readable — dashes are not `\u2014`); JSON written with `--out` keeps byte-stable
  ASCII escapes. Color never enters a pipe, and an over-long line drops color rather than clipping content.

## 3. The one importer rule

`src/viber/output/display.py` is the only module in the package that imports rich — lazily, guarded, cached
inside a monkeypatchable `rich_available()`. A top-level `import rich` would make every `-f json` call pay
rich's import cost for output that never touches it. Enforced by one grep (PIPELINE §4):

```bash
rg "^\s*(from rich|import rich)" src/viber/ | rg -v "output/display.py"   # must be empty
```

Command payload builders (`output/display_cmd.py`) receive a `Display` and call only `display.*` primitives;
they never import rich. An unknown command or missing rich builder degrades to the plain renderer —
presentation failure must never become a new error mode.

## 4. Consistency contract

- Both backends render **the same information**. The classic drift point: an empty table must show
  `(none)` in both modes, never rich's empty box.
- Every dynamic string (census prose, paths, hints) is markup-escaped — prose like `[awaiting user]` is text,
  not rich markup.
- Width is always explicit (`COLUMNS` → terminal size → clamp 60–240); rich's autodetect reads std fds even
  when writing to a buffer, which would make piped layout and tests machine-dependent.
- A rich-unavailable machine and a `-nr` machine produce **identical bytes** — the equivalence is a test, not
  a hope.
- `--help` is typer's own rendering: the flag cannot govern it; `VIBER_RICH=0` degrades it via env before
  typer loads.

## 5. Display primitives

`display.py` exposes the whole presentation surface: `display_table`, `display_panel`, `display_success`,
`display_info`, `display_status`, `display_warning`, `display_error`, `display_json` — all returning `str`
(so `emit` stays the single stdout writer); plus `report_warning` / `report_error`, the only stderr writers.
Business code never formats color; it picks a primitive.

## 6. Rules

- Flag > env > auto, evaluated once per run in `resolve_display()`; nothing re-detects later.
- Color requires a tty. `force_terminal` is never set for captured or piped output.
- Pipes, `--out` files, and un-tty'd JSON are ANSI-free by structure, not by luck; JSON on a live tty
  gets color the same way everything else does — granted by the tty alone.
- Display capability is per-machine (flag/env), never a chain key — see `config.md` 2; committing "my console"
  into shared repo state would silently downgrade teammates.
- Windows legacy consoles that render box glyphs wrong: `-nr` or `VIBER_RICH=0` is the documented instant
  revert.

## 7. Open Items

1. Whether status lines ever want a live `rich.Status` spinner (today viber is one-shot; nothing spins).
2. Theme tokens (brand colors) once more than the default palette is needed.
