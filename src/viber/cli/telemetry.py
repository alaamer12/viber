"""Telemetry commands: use, outcome — the invocation ledger."""

from collections.abc import Callable

import typer

from viber.cli.deps import (
    CensusOpt,
    ExcludeOpt,
    ForceOpt,
    FormatOpt,
    Globals,
    IncludeOpt,
    NoRichOpt,
    OutOpt,
    ProfileOpt,
    command,
)
from viber.core.census_ops import current_step, entry_of
from viber.data.telemetry import now_iso
from viber.models.domain import Outcome
from viber.output.display import report_error
from viber.output.emit import emit


def _ack(g: Globals, message: str) -> None:
    emit("ack", {"message": message}, [], g.target())


@command
def use_cmd(
    skill: str,
    step_override: str = typer.Option(
        "", "--step-override", "-s", help="Record under this step name"
    ),
    census: CensusOpt = None,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
    no_rich: NoRichOpt = False,
) -> int:
    """Record a skill invocation in telemetry (the AGENTS.md instruction)."""
    g = Globals(census, fmt, out, force, profile, include, exclude, no_rich=no_rich)
    if not g.settings.telemetry:
        _ack(g, "telemetry disabled")
        return 0
    data = g.load()
    if entry_of(data, skill) is None:
        report_error(g.display, f"skill '{skill}' not in census")
        return 1
    step = step_override or (current_step(data) or None)
    g.db().record_invocation(skill, now_iso(), step, data.projectPhase)
    _ack(g, f"use {skill}")
    return 0


@command
def outcome_cmd(
    skill: str,
    result: Outcome,
    note: str | None = typer.Argument(None),
    census: CensusOpt = None,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
    no_rich: NoRichOpt = False,
) -> int:
    """Close the newest open invocation of a skill with ok/fail/skip."""
    g = Globals(census, fmt, out, force, profile, include, exclude, no_rich=no_rich)
    if not g.settings.telemetry:
        _ack(g, "telemetry disabled")
        return 0
    data = g.load()  # census presence validated for the uniform contract
    assert data is not None
    db = g.db()
    if not db.exists():
        report_error(g.display, "no telemetry db")
        return 1
    if db.close_open(skill, result.value, note) is None:
        report_error(g.display, f"no open invocation for '{skill}'")
        return 1
    _ack(g, f"{skill} -> {result.value}")
    return 0


COMMANDS: dict[str, Callable[..., None]] = {
    "use": use_cmd,
    "outcome": outcome_cmd,
}
