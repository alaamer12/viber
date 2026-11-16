"""The emit sink: one exit path for every command.

Rules: files get compact plain output only (never ANSI); TTY gets a colorized pass
when rich/ansi is usable; JSON is machine-strict (ASCII-safe dumps). Write is atomic,
refuses existing targets without force, and reports bytes on stderr so stdout and
exit codes stay clean for pipes.
"""

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from viber.models.domain import FormatKind
from viber.output.render import registry_order, render_text

_IS_WIN_LEGACY = sys.platform == "win32"


@runtime_checkable
class Renderer(Protocol):
    def render_txt(self, payload: dict[str, Any], selection: list[str]) -> str: ...
    def render_json(self, payload: dict[str, Any], selection: list[str]) -> str: ...


class EmitError(Exception):
    """File-system refusal or write failure; CLI maps to exit code 1."""


@dataclass(slots=True, frozen=True)
class EmitTarget:
    fmt: FormatKind = FormatKind.TXT
    out: Path | None = None
    force: bool = False


def _strip_long_hints(payload: dict[str, Any], selection: list[str]) -> dict[str, Any]:
    """Drop long_hint from relation lists when the field is not selected (skill only)."""
    data = payload
    fit = data.get("fit")
    if not isinstance(fit, dict) or "long_hints" in selection:
        return data
    stripped = dict(data)
    new_fit = dict(fit)
    for kind in ("after", "before", "with"):
        rels = new_fit.get(kind)
        if isinstance(rels, list):
            new_fit[kind] = [
                {k: v for k, v in r.items() if k != "long_hint"} if isinstance(r, dict) else r
                for r in rels
            ]
    stripped["fit"] = new_fit
    return stripped


def filter_payload(command: str, payload: dict[str, Any], selection: list[str]) -> dict[str, Any]:
    """Top-level keys only, in registry order; commands without registry entries
    (ack/drift) pass through fully."""
    if not _has_registry(command):
        return payload
    return {k: payload[k] for k in registry_order(command) if k in payload and k in selection}


def _has_registry(command: str) -> bool:
    from viber.output.fields import REGISTRY

    return command in REGISTRY


def _colorize(text: str) -> str:
    lines = []
    for line in text.split("\n"):
        if (
            line
            and not line.startswith((" ", "-"))
            and (": " in line and line.split(":")[0].islower() and not line.startswith("- "))
        ):
            key, _, val = line.partition(": ")
            lines.append(f"\x1b[36m{key}\x1b[0m: {val}")
        elif line and not line.startswith((" ", "-")):
            lines.append(f"\x1b[1m{line}\x1b[0m")
        else:
            lines.append(line)
    return "\n".join(lines)


def emit(command: str, payload: dict[str, Any], selection: list[str], target: EmitTarget) -> None:
    if target.fmt == FormatKind.JSON:
        data = filter_payload(command, payload, selection)
        if command == "skill":
            data = _strip_long_hints(data, selection)
        text = json.dumps(data, indent=2)
    else:
        text = render_text(command, payload, selection)

    if target.out is not None:
        _write_file(target.out, text, target.force)
        return
    if target.fmt == FormatKind.TXT and sys.stdout.isatty() and not _IS_WIN_LEGACY:
        print(_colorize(text))
    else:
        print(text)


def _write_file(path: Path, text: str, force: bool) -> None:
    if path.exists() and not force:
        raise EmitError(f"refusing to overwrite {path} — pass --force")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)
    size = path.stat().st_size
    print(f"flushed: {path} ({size} bytes)", file=sys.stderr)
