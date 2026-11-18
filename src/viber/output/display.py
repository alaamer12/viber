"""The display layer — the package's ONLY rich importer.

Two independent axes, verified against rich 15: layout (rich/plain) and color
(ANSI permitted or not). Color is granted only when stdout is a real terminal —
`no_color=True` alone still emits escapes under `force_terminal`, so pipes get a
plain Console writing to a buffer: full box layout, zero bytes of ANSI.

Business code builds `Part` specs (text, key-values, tables, panels) and never
imports rich; this module renders the same parts in both backends, guaranteeing
consistent information. Every primitive returns `str`; `emit` stays the single
stdout writer, `report_*` the only stderr writers.

Resolution: -nr flag > VIBER_RICH env > auto (rich importable AND tty AND TERM ok).
"""

import os
import shutil
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from io import StringIO
from typing import Any, Final, Literal

from viber.core.settings import parse_bool

DisplayMode = Literal["rich", "plain"]

_MIN_WIDTH: Final = 60
_MAX_WIDTH: Final = 240
_DUMB_TERMS: Final = frozenset({"dumb", "unknown"})  # unset TERM is normal, not dumb


@dataclass(frozen=True, slots=True)
class Display:
    layout: DisplayMode = "plain"
    color: bool = False
    width: int = 100
    warnings: tuple[str, ...] = ()

    @property
    def rich(self) -> bool:
        return self.layout == "rich"


PLAIN: Final = Display()

_rich_state: dict[str, Any] = {}


def rich_available() -> bool:
    """Importable-and-usable rich, cached. A guarded import, not find_spec: a spec
    can exist for a broken install, and we are about to use it either way."""
    if "ok" not in _rich_state:
        try:
            import rich.console  # noqa: F401  (the probe IS the point)

            _rich_state["ok"] = True
        except ImportError:
            _rich_state["ok"] = False
    return bool(_rich_state["ok"])


def _tty() -> bool:
    try:
        return bool(sys.stdout.isatty())
    except Exception:
        return False


def resolve_width(env: Mapping[str, str] | None = None, fallback: int = 100) -> int:
    env = os.environ if env is None else env
    raw = env.get("COLUMNS")
    width: int | None = int(raw) if raw and raw.strip().isdigit() else None
    if width is None:
        try:
            width = shutil.get_terminal_size((fallback, 24)).columns
        except OSError:
            width = fallback
    return max(_MIN_WIDTH, min(_MAX_WIDTH, width))


def resolve_display(no_rich: bool = False, env: Mapping[str, str] | None = None) -> Display:
    """Pure, once-per-run. Never emits: warnings ride along on the Display."""
    env = os.environ if env is None else env
    width = resolve_width(env)
    warnings: list[str] = []
    if no_rich:
        return Display("plain", False, width)
    term = env.get("TERM", "")
    tty = _tty() and term not in _DUMB_TERMS
    raw = env.get("VIBER_RICH")
    forced = parse_bool(raw) if raw else None
    if raw and forced is None:
        warnings.append(f"invalid VIBER_RICH {raw!r} — falling back to auto-detect")
    if forced is False:
        return Display("plain", False, width, tuple(warnings))
    if forced is True:
        if rich_available():
            return Display("rich", tty, width, tuple(warnings))
        warnings.append("VIBER_RICH requested but rich is unavailable — plain layout")
        return Display("plain", False, width, tuple(warnings))
    if rich_available():
        return Display("rich", tty, width, tuple(warnings))
    return Display("plain", False, width, tuple(warnings))


# ---------------------------------------------------------------- parts


@dataclass(frozen=True, slots=True)
class TextPart:
    text: str
    style: str = ""


@dataclass(frozen=True, slots=True)
class KVPart:
    pairs: Sequence[tuple[str, str]]


@dataclass(frozen=True, slots=True)
class TablePart:
    columns: Sequence[str]
    rows: Sequence[Sequence[str | TextPart]]
    empty: str = "(none)"


@dataclass(frozen=True, slots=True)
class PanelPart:
    body: str
    title: str | None = None


Part = TextPart | KVPart | TablePart | PanelPart


# ------------------------------------------------------------- backends


def plain_table_lines(columns: Sequence[str], rows: Sequence[Sequence[Any]]) -> list[str]:
    """The one plain table formatter (relocated from output.render)."""
    if not rows:
        return ["(none)"]
    str_rows = [[str(c.text if isinstance(c, TextPart) else c) for c in row] for row in rows]
    widths = [len(c) for c in columns]
    for row in str_rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    out = [
        "  ".join(c.ljust(widths[i]) for i, c in enumerate(columns)),
        "  ".join("-" * w for w in widths),
    ]
    out += ["  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)) for row in str_rows]
    return out


def make_console(d: Display, file: Any) -> Any:
    """A Console with the two verified traps disabled: explicit width (rich reads
    std fds otherwise) and markup/highlight off (prose brackets are data)."""
    from rich.console import Console

    return Console(
        file=file,
        width=d.width,
        force_terminal=d.color,
        no_color=not d.color,
        highlight=False,
        markup=False,
    )


def _to_rich(part: Part) -> Any:
    from rich import box
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    if isinstance(part, TextPart):
        return Text(part.text) if not part.style else Text(part.text, style=part.style)
    if isinstance(part, KVPart):
        from rich.console import Group

        return Group(
            *[
                Text.assemble((key, "cyan"), Text(f": {value}"))
                for key, value in part.pairs
            ]
        )  # fmt: skip
    if isinstance(part, TablePart):
        if not part.rows:
            return Text(part.empty, style="dim")
        table = Table(box=box.SIMPLE_HEAVY, show_edge=False, pad_edge=False)
        for col in part.columns:
            table.add_column(col, overflow="fold")
        for row in part.rows:
            table.add_row(
                *[
                    Text(str(v.text), style=v.style) if isinstance(v, TextPart) else str(v)
                    for v in row
                ]
            )
        return table
    if isinstance(part, PanelPart):
        from rich.text import Text as _T

        return Panel(_T(part.body), title=part.title, border_style="dim")
    raise TypeError(f"unknown display part: {part!r}")


def _to_plain_lines(part: Part) -> list[str]:
    if isinstance(part, TextPart):
        return part.text.split("\n")
    if isinstance(part, KVPart):
        width = max((len(k) for k, _ in part.pairs), default=0)
        return [f"{k.ljust(width)}  {v}" if v else f"{k}: -" for k, v in part.pairs]
    if isinstance(part, TablePart):
        return plain_table_lines(part.columns, part.rows)
    if isinstance(part, PanelPart):
        lines = [f"── {part.title} " if part.title else "──"]
        lines += [f"  {line}" for line in part.body.split("\n")]
        return lines
    raise TypeError(f"unknown display part: {part!r}")


def render_parts(d: Display, parts: Sequence[Part]) -> str:
    """Parts in, display-ready text out — same information in both backends."""
    parts = [p for p in parts if not (isinstance(p, TextPart) and p.text == "")]
    if not d.rich:
        lines: list[str] = []
        for part in parts:
            lines += _to_plain_lines(part)
        return "\n".join(lines)
    buf = StringIO()
    console = make_console(d, buf)
    from rich.console import Group

    console.print(Group(*[_to_rich(p) for p in parts]))
    return buf.getvalue().rstrip("\n")


# ----------------------------------------------------------- primitives


def display_table(
    d: Display, columns: Sequence[str], rows: Sequence[Sequence[str]], empty: str = "(none)"
) -> str:
    return render_parts(d, [TablePart(columns, rows, empty)])


def display_panel(d: Display, body: str, title: str | None = None) -> str:
    return render_parts(d, [PanelPart(body, title)])


def display_success(d: Display, message: str) -> str:
    return render_parts(d, [TextPart(f"ok: {message}", "bold green" if d.rich else "")])


def display_info(d: Display, message: str) -> str:
    return render_parts(d, [TextPart(f"info: {message}")])


def display_status(d: Display, label: str, value: str, state: str | None = None) -> str:
    styles = {"ready": "green", "blocked": "red", "command": "cyan", "candidate": "yellow"}
    return render_parts(
        d, [TextPart(f"{label}: {value}", styles.get(state or "", "") if d.rich else "")]
    )


def display_warning(d: Display, message: str) -> str:
    return render_parts(d, [TextPart(f"warning: {message}", "yellow" if d.rich else "")])


def display_error(d: Display, message: str) -> str:
    return render_parts(d, [TextPart(f"error: {message}", "bold red" if d.rich else "")])


# stderr writers — the only places display prints directly

BLIND: Final = Display()  # for messages emitted before/independent of resolution


def report_warning(d: Display, message: str) -> None:
    print(display_warning(d, message), file=sys.stderr)


def report_error(d: Display, message: str) -> None:
    print(display_error(d, message), file=sys.stderr)
