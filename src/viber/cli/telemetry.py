"""Telemetry commands: use, outcome — the invocation ledger."""

from collections.abc import Callable

import typer

from viber.cli.deps import (
    BannerOpt,
    CensusOpt,
    ExcludeOpt,
    ForceOpt,
    FormatOpt,
    Globals,
    IncludeOpt,
    NoRichOpt,
    NoteOpt,
    OutOpt,
    ProfileOpt,
    ProjectOpt,
    command,
)
from viber.core import mutations
from viber.core.census_ops import current_step, entry_of
from viber.data.telemetry import now_iso
from viber.models.domain import Outcome
from viber.output.display import report_error
from viber.output.emit import emit


def _ack(g: Globals, message: str) -> None:
    emit("ack", {"message": message}, [], g.target())


@command
def use_cmd(
    skills: list[str] = typer.Argument(
        None, help="one or more skills to record (bulk: viber use a b c)"
    ),
    step_override: str = typer.Option(
        "", "--step-override", "-s", help="Record under this step name"
    ),
    note: NoteOpt = None,
    census: CensusOpt = None,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
    project: ProjectOpt = None,
    banner: BannerOpt = True,
    no_rich: NoRichOpt = False,
) -> int:
    """Record skill invocations in telemetry (the AGENTS.md instruction). Bulk: pass several."""
    g = Globals(
        census, fmt, out, force, profile, include, exclude,
        no_rich=no_rich, project=project, banner=banner,
    )  # fmt: skip
    data = g.load()
    unknown = [s for s in skills if entry_of(data, s) is None]
    if unknown:  # validate-first: a bad name records nothing
        report_error(g.display, f"skill(s) not in census: {', '.join(unknown)}")
        return 1
    tele = g.settings.telemetry
    if tele:
        db = g.db(); ts = now_iso()
        step = step_override or (current_step(data) or None)
    for s in skills:
        if tele:
            db.record_invocation(s, ts, step, data.projectPhase)
        if note is not None:  # a self-note is census state — record even if telemetry is off
            mutations.record_note(data, s, note, "use", g.census_path)
    if not tele:
        _ack(g, "telemetry disabled" + (f" — note recorded on {', '.join(skills)}" if note else ""))
        return 0
    _ack(g, f"use {', '.join(skills)}" + (" (+note)" if note is not None else ""))
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
    project: ProjectOpt = None,
    banner: BannerOpt = True,
    no_rich: NoRichOpt = False,
) -> int:
    """Close the newest open invocation of a skill with ok/fail/skip (note also kept on the card)."""
    g = Globals(
        census, fmt, out, force, profile, include, exclude,
        no_rich=no_rich, project=project, banner=banner,
    )  # fmt: skip
    data = g.load()  # census presence validated for the uniform contract
    assert data is not None
    if not g.settings.telemetry:
        if note is not None:  # the note is census state; keep it even when telemetry is off
            mutations.record_note(data, skill, note, "outcome", g.census_path)
        _ack(g, "telemetry disabled" + (f" — note recorded on {skill}" if note is not None else ""))
        return 0
    db = g.db()
    if not db.exists():
        report_error(g.display, "no telemetry db")
        return 1
    if db.close_open(skill, result.value, note) is None:
        report_error(g.display, f"no open invocation for '{skill}'")
        return 1
    if note is not None:
        mutations.record_note(data, skill, note, "outcome", g.census_path)
    _ack(g, f"{skill} -> {result.value}")
    return 0


COMMANDS: dict[str, Callable[..., None]] = {
    "use": use_cmd,
    "outcome": outcome_cmd,
}
