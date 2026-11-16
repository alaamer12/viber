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
    OutOpt,
    ProfileOpt,
    command,
)
from viber.core.census_ops import current_step, entry_of
from viber.data.telemetry import now_iso
from viber.models.domain import FormatKind, Outcome, Profile
from viber.output.emit import emit


def _ack(g: Globals, message: str) -> None:
    emit("ack", {"message": message}, [], g.target())


@command
def use_cmd(
    skill: str,
    step_override: str = typer.Option("", "--step-override", help="Record under this step name"),
    census: CensusOpt = None,
    fmt: FormatOpt = FormatKind.TXT,
    out: OutOpt = None,
    force: ForceOpt = False,
    profile: ProfileOpt = Profile.STANDARD,
    include: IncludeOpt = "",
    exclude: ExcludeOpt = "",
) -> int:
    g = Globals(census, fmt, out, force, profile, include, exclude)
    data = g.load()
    if entry_of(data, skill) is None:
        typer.secho(f"error: skill '{skill}' not in census", fg="red", err=True)
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
    fmt: FormatOpt = FormatKind.TXT,
    out: OutOpt = None,
    force: ForceOpt = False,
    profile: ProfileOpt = Profile.STANDARD,
    include: IncludeOpt = "",
    exclude: ExcludeOpt = "",
) -> int:
    g = Globals(census, fmt, out, force, profile, include, exclude)
    data = g.load()  # census presence validated for the uniform contract
    assert data is not None
    db = g.db()
    if not db.exists():
        typer.secho("error: no telemetry db", fg="red", err=True)
        return 1
    if db.close_open(skill, result.value, note) is None:
        typer.secho(f"error: no open invocation for '{skill}'", fg="red", err=True)
        return 1
    _ack(g, f"{skill} -> {result.value}")
    return 0


COMMANDS: dict[str, Callable[..., None]] = {
    "use": use_cmd,
    "outcome": outcome_cmd,
}
