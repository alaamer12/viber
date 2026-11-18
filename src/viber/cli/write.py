"""Write commands: set, log, add-skill, remove-skill, refresh — plus the read-only
lint command (lives here as the census health companion of the writers)."""

from collections.abc import Callable
from typing import Any

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
from viber.core import lint as lint_core
from viber.core import mutations
from viber.data.store import CensusUsageError
from viber.models.domain import Finding, SetField, Severity, SkillType
from viber.output.emit import emit


def _ack(g: Globals, message: str, payload_extra: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {"message": message}
    if payload_extra:
        payload.update(payload_extra)
    emit("ack" if not payload_extra else "ack-show", payload, [], g.target())


@command
def set_cmd(
    skill: str,
    field: SetField,
    value: str,
    show: bool = typer.Option(False, "--show/--no-show", "-s", help="Echo the updated record"),
    census: CensusOpt = None,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
    no_rich: NoRichOpt = False,
) -> int:
    """Write one census field (caps and meanings: viber fields). set <skill> <field> <value>."""
    g = Globals(census, fmt, out, force, profile, include, exclude, no_rich=no_rich)
    data = g.load()
    message = mutations.set_field(data, skill, field, value, g.census_path)
    extra = None
    if show and skill != ".":
        from viber.core.census_ops import skill_payload

        extra = {"show": skill_payload(data, skill)}
    _ack(g, message, extra)
    return 0


@command
def log_cmd(
    skill: str,
    event: str,
    census: CensusOpt = None,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
    no_rich: NoRichOpt = False,
) -> int:
    """Append a dated event to a skill's history (rolling at cap — viber fields)."""
    g = Globals(census, fmt, out, force, profile, include, exclude, no_rich=no_rich)
    data = g.load()
    _ack(g, mutations.log_event(data, skill, event, g.census_path))
    return 0


@command
def add_skill_cmd(
    name: str,
    deck: str = typer.Option(..., "--deck", "-d"),
    path: str = typer.Option(..., "--path", "-p"),
    serves: str = typer.Option("", "--serve", "-s", help="Comma list of step names"),
    stype: SkillType = typer.Option(SkillType.NORMAL, "--type", "-t"),
    use_case: list[str] = typer.Option([], "--use-case", "-u", help="Repeatable"),
    census: CensusOpt = None,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
    no_rich: NoRichOpt = False,
) -> int:
    """Register a new skill: deck, path, served steps, type, use-cases (caps: viber fields)."""
    g = Globals(census, fmt, out, force, profile, include, exclude, no_rich=no_rich)
    data = g.load()
    steps = [s.strip() for s in serves.split(",") if s.strip()]
    for s in steps:
        if s not in {st.step for st in data.lifecycle}:
            raise ValueError(f"unknown step '{s}' for --serve")
    _ack(
        g,
        mutations.add_skill(
            data, name, deck, path, steps, stype.value, list(use_case), g.census_path
        ),
    )
    return 0


@command
def remove_skill_cmd(
    name: str,
    dry_run: bool = typer.Option(False, "--dry-run", "-d"),
    census: CensusOpt = None,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
    no_rich: NoRichOpt = False,
) -> int:
    """Drop a skill from the census (--dry-run previews the fallout)."""
    g = Globals(census, fmt, out, force, profile, include, exclude, no_rich=no_rich)
    data = g.load()
    _ack(g, mutations.remove_skill(data, name, g.census_path, dry=dry_run))
    return 0


@command
def refresh_cmd(
    name: str | None = typer.Argument(None),
    everything: bool = typer.Option(False, "--all", "-a"),
    check: bool | None = typer.Option(
        None, "--check/--no-check", "-c", help="Report drift without writing"
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
    """Re-read a skill's frontmatter and content tree from disk (or --all)."""
    g = Globals(census, fmt, out, force, profile, include, exclude, no_rich=no_rich)
    data = g.load()
    if not name and not everything:
        raise ValueError("give a skill name or --all")
    names = sorted(data.skills) if everything else [name or ""]
    if check:
        rows = mutations.drift_rows(data, g.census_path)
        emit("drift", {"drift": rows}, [], g.target())
        return 0
    messages = []
    skipped = 0
    for n in names:
        try:
            messages.append(mutations.refresh_skill(data, n, g.census_path))
        except CensusUsageError:
            if not everything:
                raise
            skipped += 1
    if everything and skipped:
        messages.append(f"skipped {skipped} (no readable SKILL.md)")
    mutations.save(data, g.census_path)
    _ack(g, "; ".join(messages))
    return 0


@command
def lint_cmd(
    only: Severity | None = typer.Option(None, "--only", help="error|warning|question"),
    ask_only: bool = typer.Option(False, "--ask-only", "-a"),
    remote: bool = typer.Option(
        False,
        "--remote",
        "-R",
        help="Check deck git remotes against upstream (network; offline degrades to warning)",
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
    """Audit the census; deck conflicts surface as ASK USER decisions."""
    g = Globals(census, fmt, out, force, profile, include, exclude, no_rich=no_rich)
    data = g.load()
    all_findings = lint_core.run_lint(data, g.census_path, remote=remote)
    findings = all_findings
    if only:
        findings = [f for f in findings if f.severity is only]
    if ask_only:
        findings = [f for f in findings if f.severity is Severity.QUESTION]
    payload: dict[str, Any] = {
        "findings": [_finding_dict(f) for f in findings],
        "summary": lint_core.summarize(all_findings),
    }
    emit("lint", payload, g.selection_with("lint"), g.target())
    summary: dict[str, int] = payload["summary"]
    return 1 if (summary["errors"] or summary["questions"]) else 0


def _finding_dict(f: Finding) -> dict[str, Any]:
    from dataclasses import asdict

    d: dict[str, Any] = dict(asdict(f))
    d["severity"] = str(f.severity.value)
    d["ask_user"] = f.question is not None
    return d


COMMANDS: dict[str, Callable[..., None]] = {
    "set": set_cmd,
    "log": log_cmd,
    "add-skill": add_skill_cmd,
    "add-s": add_skill_cmd,
    "remove-skill": remove_skill_cmd,
    "rm-skill": remove_skill_cmd,
    "refresh": refresh_cmd,
    "lint": lint_cmd,
}
