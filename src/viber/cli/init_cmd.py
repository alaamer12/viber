from dataclasses import asdict
from importlib.resources import files
import os
from pathlib import Path
from typing import Annotated

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
    command,
)
from viber.core import bootstrap, projects
from viber.core.lint import summarize
from viber.data.skill_registry import conflicting_sources, scan_skills
from viber.data.store import CENSUS_NAME, DEFAULT_DATA_DIR, CensusError
from viber.models.domain import FormatKind
from viber.output.display import TextPart, render_parts
from viber.output.emit import emit

SkillsRootsOpt = Annotated[
    list[Path] | None,
    typer.Option("--skills-root", "-S", help="Installed skills folder (repeat for multiple roots)"),
]


def _protect_output(g: Globals, protected: list[Path]) -> None:
    if g.out is None:
        return
    for output in (g.out, g.out.with_name(g.out.name + ".tmp")):
        for source in protected:
            if output.resolve() == source.resolve() or (
                output.exists() and source.exists() and output.samefile(source)
            ):
                raise CensusError(f"report output would overwrite protected input: {source}")
    if g.out.exists() and not g.force:
        raise CensusError(f"refusing to overwrite {g.out} — pass --force")
    if g.out.is_dir():
        raise CensusError(f"report output must be a file: {g.out}")


def init_at(
    target: Path,
    skills_root: list[Path],
    fmt: FormatOpt,
    out: OutOpt,
    force: ForceOpt,
    profile: ProfileOpt,
    include: IncludeOpt,
    exclude: ExcludeOpt,
    no_rich: bool,
    banner: bool,
) -> int:
    """Create a project census at `target`, register a fingerprint id, emit + banner."""
    g = Globals(None, fmt, out, force, profile, include, exclude, no_rich=no_rich)
    selection = g.selection("init")
    if target.exists() or target.is_symlink():
        raise CensusError(f"refusing to overwrite census: {target}")
    seed, source = bootstrap.load_seed()
    protected = [target, *([source] if source else [])]
    resource = files("viber.data").joinpath("seed.json")
    if isinstance(resource, Path):
        protected.append(resource)
    _protect_output(g, protected)
    data, findings = bootstrap.prepare_census(seed, source, skills_root or [], target)
    failed = bootstrap.has_errors(findings)
    project_dir = (
        target.parent.parent.parent if target.parent.name == ".data" else target.parent
    )
    pid = projects.project_id(project_dir)
    data.project_id = pid
    if not failed:
        bootstrap.create_census(target, data)
        projects.register_project(os.environ, pid, project_dir, data.name)
    payload = {
        "census": target.resolve().as_posix(),
        "project_id": pid,
        "created": not failed,
        "resolved": sum(entry.path is not None for entry in data.skills.values()),
        "summary": summarize(findings),
        "findings": [
            {**asdict(f), "severity": f.severity.value, "ask_user": f.question is not None}
            for f in findings
        ],
    }
    emit("init", payload, selection, g.target())
    if not failed and banner and g.fmt is FormatKind.TXT and g.out is None:
        print(
            render_parts(
                g.display,
                [TextPart("PROJECT STARTED", "bold bright_green")]
                + [
                    TextPart(f"  id:    {pid}"),
                    TextPart(f"  name:  {data.name}"),
                    TextPart(f"  dir:   {project_dir.as_posix()}"),
                    TextPart(f"  resume from anywhere:  viber --project {pid} <command>"),
                    TextPart("  record the id in AGENTS.md — it is not sensitive."),
                    TextPart(
                        "  (the id is a location fingerprint; if this folder moves, re-bind "
                        "it with `viber project link`)"
                    ),
                ],
            )
        )
    return 1 if failed else 0


@command
def init_cmd(
    skills_root: SkillsRootsOpt = None,
    banner: BannerOpt = True,
    census: CensusOpt = None,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
    no_rich: NoRichOpt = False,
) -> int:
    """Create a project census from the packaged seed; never replace existing project data."""
    g = Globals(census, fmt, out, force, profile, include, exclude, no_rich=no_rich)
    target = (
        Path(g.settings.census)
        if g.settings.census
        else Path.cwd() / DEFAULT_DATA_DIR / CENSUS_NAME
    )
    return init_at(
        target, skills_root or [], fmt, out, force, profile, include, exclude, no_rich, banner
    )


@command
def registry_cmd(
    skills_root: SkillsRootsOpt = None,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
    no_rich: NoRichOpt = False,
) -> int:
    """Export installed skill metadata; leave classification and exclusions to /vinit."""
    g = Globals(None, fmt, out, force, profile, include, exclude, no_rich=no_rich)
    selection = g.selection("registry")
    if not skills_root:
        raise ValueError("provide at least one --skills-root (installed skills directory)")
    skills = scan_skills(skills_root)
    _protect_output(g, [skill.source / "SKILL.md" for skill in skills] + [g.census_path])
    conflicts = conflicting_sources(skills)
    payload = {
        "skills": [{**asdict(skill), "source": skill.source.as_posix()} for skill in skills],
        "conflicts": [{"name": name, "sources": sources} for name, sources in conflicts.items()],
    }
    emit("registry", payload, selection, g.target())
    return 1 if conflicts else 0


COMMANDS = {"init": init_cmd, "registry": registry_cmd}
