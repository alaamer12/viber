"""The emit sink: one exit path for every command.

Rules: files get compact plain output only (never ANSI); a resolved rich display
mode routes structured payloads through display_cmd (boxed layout, color only on a
real tty); JSON is machine-strict (ASCII-safe dumps). Write is atomic, refuses
existing targets without force, and reports bytes on stderr so stdout and
exit codes stay clean for pipes.
"""

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from viber.models.domain import FormatKind
from viber.output.display import PLAIN, Display
from viber.output.display_cmd import render_command
from viber.output.render import registry_order, render_text


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
    display: Display = PLAIN


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


def emit(command: str, payload: dict[str, Any], selection: list[str], target: EmitTarget) -> None:
    if target.fmt == FormatKind.JSON:
        data = filter_payload(command, payload, selection)
        if command == "skill":
            data = _strip_long_hints(data, selection)
        text = json.dumps(data, indent=2)
    elif target.out is not None:
        # files are machine contracts: always the plain renderers, never rich
        text = render_text(command, payload, selection)
    elif target.display.rich:
        text = render_command(command, payload, selection, target.display)
    else:
        text = render_text(command, payload, selection)

    if target.out is not None:
        _write_file(target.out, text, target.force)
        return
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
