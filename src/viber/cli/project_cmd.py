"""`viber project` sub-app — create, resume (use), link (re-bind a moved folder),
list, status. The top-level `viber now` (in read.py) shares this `project` payload."""

import os
from collections.abc import Callable
from pathlib import Path

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
    OutOpt,
    ProfileOpt,
    ProjectOpt,
    command,
)
from viber.core import projects
from viber.core.resolution import current_step
from viber.data import config_store
from viber.data.store import load_census, save_census
from viber.models.domain import FormatKind
from viber.output.display import TextPart, render_parts
from viber.output.emit import emit

_DATA_REL = Path(".viber") / ".data" / "viber.json"


def _ack(g: Globals, message: str) -> None:
    emit("ack", {"message": message}, [], g.target())


def _census_for(dir: Path) -> Path:
    return dir / _DATA_REL


@command
def create_cmd(
    directory: str = typer.Argument(help="project directory to create viber data in"),
    skills_root: list[Path] = typer.Option([], "--skills-root", "-S", help="installed skills dir"),
    banner: BannerOpt = True,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
    no_rich: NoRichOpt = False,
) -> int:
    """Create a project census at a path and register it under a new id (init, but explicit)."""
    from viber.cli import init_cmd

    target = Path(directory).expanduser().resolve()
    return init_cmd.init_at(
        target, skills_root, fmt, out, force, profile, include, exclude, no_rich, banner
    )


@command
def use_cmd(
    project_id: str = typer.Argument(None, help="project id to make the default"),
    none: bool = typer.Option(False, "--none", help="clear the default project"),
    fmt: FormatOpt = None,
    out: OutOpt = None,
    no_rich: NoRichOpt = False,
) -> int:
    """Persist the default project so bare `viber <cmd>` resumes it."""
    g = Globals(None, fmt, out, None, None, None, None, no_rich=no_rich)
    paths = config_store.locate(os.environ)
    if none:
        removed = config_store.unset_value(paths.user, "project")
        _ack(g, "default project cleared" if removed else "no default project was set")
        return 0
    if project_id is None:
        _ack(g, "give an id, or --none to clear")
        return 2
    if projects.lookup_project(os.environ, project_id) is None:
        _ack(g, f"unknown id '{project_id}' — run `viber project list` or `viber project link`")
        return 1
    config_store.set_value(paths.user, "project", project_id)
    _ack(g, f"default project set: {project_id}")
    return 0


@command
def link_cmd(
    project_id: str = typer.Argument(None, help="existing id to re-bind"),
    to: str = typer.Option(..., "--to", help="new location holding this project's data"),
    fmt: FormatOpt = None,
    out: OutOpt = None,
    no_rich: NoRichOpt = False,
) -> int:
    """Re-bind a project id to a new location after the folder moved (or adopt data)."""
    g = Globals(None, fmt, out, None, None, None, None, no_rich=no_rich)
    new_dir = Path(to).expanduser().resolve()
    census = _census_for(new_dir)
    if not census.is_file():
        _ack(g, f"no census at {new_dir.as_posix()} — create it first (`viber init`)")
        return 1
    data = load_census(census)
    pid = project_id or data.project_id or projects.project_id(new_dir)
    projects.register_project(os.environ, pid, new_dir, data.name or "project")
    if data.project_id != pid:
        data.project_id = pid
        save_census(census, data)
    others = [
        other for other, rec in projects.all_projects(os.environ).items()
        if other != pid and projects.normalize_dir(rec["dir"]) == projects.normalize_dir(new_dir)
    ]  # fmt: skip
    warn = (
        f" — NOTE: id(s) {', '.join(others)} also point at this folder (overlap)"
        if others else ""
    )
    if g.fmt is FormatKind.TXT and g.out is None:
        print(
            render_parts(
                g.display,
                [
                    TextPart(f"LINKED {pid}", "bold bright_green"),
                    TextPart(f"  dir:    {new_dir.as_posix()}"),
                    TextPart(f"  resume: viber --project {pid} <command>"),
                ]
                + ([TextPart(warn.strip(" —"), "yellow")] if others else []),
            )
        )
    else:
        _ack(g, f"linked {pid} -> {new_dir.as_posix()}{warn}")
    return 0


@command
def list_cmd(
    fmt: FormatOpt = None,
    out: OutOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
    no_rich: NoRichOpt = False,
) -> int:
    """Show every registered project with its location and link health."""
    g = Globals(None, fmt, out, None, profile, include, exclude, no_rich=no_rich)
    rows = []
    for pid, rec in projects.all_projects(os.environ).items():
        rows.append(
            {
                "id": pid,
                "name": rec.get("name", ""),
                "dir": rec.get("dir", ""),
                "last_used": rec.get("last_used") or "-",
                "link": "ok" if _census_for(Path(rec["dir"])).is_file() else "missing",
            }
        )
    rows.sort(key=lambda r: r["id"])
    emit(
        "project",
        {"kind": "list", "rows": rows, "count": len(rows)},
        g.selection_with("project"),
        g.target(),
    )
    return 0


def build_status(g: Globals, details: bool = False) -> dict[str, object]:
    """Shared by `project status`, `viber now`, and `viber project <id> --details`.

    The id is derived from the resolved census path, never trusted from the file's
    stored `project_id` — a committed/checked-out census can carry a foreign or
    stale value, but the location is the ground truth.
    """
    present = g.census_path.is_file()
    dir_path = g.project_dir or str(projects.project_dir_for_census(g.census_path))
    canonical = projects.id_for_census(g.census_path) if present else (g.project_id or "-")
    out: dict[str, object] = {
        "kind": "status",
        "present": present,
        "id": canonical,
        "name": g.project_name or "-",
        "dir": dir_path,
        "source": g.project_source,
        "phase": "-",
        "step": "-",
        "census": g.census_path.resolve().as_posix(),
    }
    if present:
        from viber.core import resolution

        data = load_census(g.census_path)
        out["phase"] = str(data.projectPhase)
        out["step"] = current_step(data) or "-"
        out["name"] = g.project_name or data.name or "-"
        if data.project_id and data.project_id != canonical:
            out["stored_id_differs"] = data.project_id  # committed/foreign id — location wins
        if details:
            nxt = resolution.next_candidates(data, g.db(), count=1)
            out["skills"] = len(data.skills)
            out["blocked"] = sum(1 for e in data.skills.values() if e.fit.blockers)
            out["unclassified"] = len(data.unclassified)
            out["recurring_pending"] = len(nxt["revisit"])
            out["decks"] = len(data.decks)
            last = g.db().last_done() if g.db().exists() else None
            out["last_action"] = (
                f"{last['skill']} -> {last['outcome']} @ {last['ts']}" if last else "(none)"
            )
    return out


@command
def status_cmd(
    project_id: str = typer.Argument(None, help="project id to inspect (omit for the active one)"),
    details: bool = typer.Option(False, "--details", "-d", help="Expand counts and last action"),
    project: ProjectOpt = None,
    census: CensusOpt = None,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
    no_rich: NoRichOpt = False,
) -> int:
    """The active project (or `<id>`): location, selection, phase and step; --details expands."""
    g = Globals(
        census, fmt, out, force, profile, include, exclude,
        no_rich=no_rich, project=project or project_id,
    )  # fmt: skip
    emit("project", build_status(g, details), g.selection_with("project"), g.target())
    return 0


COMMANDS: dict[str, Callable[..., None]] = {
    "create": create_cmd,
    "use": use_cmd,
    "link": link_cmd,
    "list": list_cmd,
    "status": status_cmd,
}
