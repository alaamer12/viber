from dataclasses import asdict
from importlib.resources import files
from pathlib import Path
from typing import Annotated

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
from viber.core import bootstrap
from viber.core.lint import summarize
from viber.data.skill_registry import conflicting_sources, scan_skills
from viber.data.store import CENSUS_NAME, DEFAULT_DATA_DIR, CensusError
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


@command
def init_cmd(
    skills_root: SkillsRootsOpt = None,
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
        Path(g.settings.census) if g.settings.census
        else Path.cwd() / DEFAULT_DATA_DIR / CENSUS_NAME
    )
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
    if not failed:
        bootstrap.create_census(target, data)
    payload = {
        "census": target.resolve().as_posix(),
        "created": not failed,
        "resolved": sum(entry.path is not None for entry in data.skills.values()),
        "summary": summarize(findings),
        "findings": [
            {**asdict(f), "severity": f.severity.value, "ask_user": f.question is not None}
            for f in findings
        ],
    }
    emit("init", payload, selection, g.target())
    return 1 if failed else 0


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
