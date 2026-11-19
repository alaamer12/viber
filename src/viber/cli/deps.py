"""Global option plumbing: shared Annotated types + builder, and the command decorator
that maps domain exceptions to the exit-code contract (0 ok, 1 invalid/findings,
2 usage). Handlers declare the global options explicitly — 100% standard typer.
Defaults are sentinels (None): the real value comes from the settings chain
flag > env > project config > user config > built-in default (core.settings)."""

import functools
import os
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

import typer

from viber.core.projects import lookup_project, touch_used
from viber.core.settings import Flags, resolve
from viber.data import config_store
from viber.data.config_store import ConfigError
from viber.data.store import (
    CENSUS_NAME,
    DEFAULT_DATA_DIR,
    CensusError,
    CensusUsageError,
    load_census,
    resolve_census_path,
)
from viber.data.telemetry import TelemetryDB
from viber.models.domain import FormatKind, Profile, Source
from viber.models.schema import Census
from viber.output.display import (
    PLAIN,
    TextPart,
    render_parts,
    report_error,
    report_warning,
    resolve_display,
)
from viber.output.emit import EmitError, EmitTarget
from viber.output.profiles import ProfileError, resolve_selection

CensusOpt = Annotated[
    str | None, typer.Option("--census", "-C", help="Census path [env VIBER_CENSUS]")
]
FormatOpt = Annotated[
    FormatKind | None, typer.Option("--format", "-f", help="Output format [env VIBER_FORMAT]")
]
OutOpt = Annotated[Path | None, typer.Option("--out", "-o", help="Flush output to file")]
ForceOpt = Annotated[
    bool | None, typer.Option("--force/--no-force", "-F", help="Overwrite --out target")
]
ProfileOpt = Annotated[
    Profile | None, typer.Option("--profile", "-P", help="Output profile [env VIBER_PROFILE]")
]
IncludeOpt = Annotated[
    str | None, typer.Option("--include", "-I", help="Comma list of extra fields")
]
ExcludeOpt = Annotated[
    str | None, typer.Option("--exclude", "-E", help="Comma list of dropped fields")
]
NoRichOpt = Annotated[
    bool,
    typer.Option(
        "--no-rich",
        "-nr",
        help="Plain output: no rich tables or color [env VIBER_RICH] [default: auto-detect]",
    ),
]
NoteOpt = Annotated[
    str | None,
    typer.Option(
        "--note", help="Attach a self-note to the target (stored in the census, shown on the card)"
    ),
]
ProjectOpt = Annotated[
    str | None,
    typer.Option("--project", help="Resume a project by id (see `viber now` / `viber init`)"),
]
BannerOpt = Annotated[
    bool,
    typer.Option("--banner/--no-banner", help="Show the START/RESUME project banner"),
]


def _find_local_census(start: Path) -> Path | None:
    """The nearest enclosing project's census, walking up from `start`.

    Stops at a VCS boundary (a `.git` directory or, for a worktree/submodule, a
    `.git` file): a checkout nested inside another never silently borrows the
    parent's project data, and the search never escapes the current checkout.
    The data check precedes the boundary check, so a project root (which holds
    both) resolves correctly.
    """
    current = start.resolve()
    for folder in (current, *current.parents):
        found = folder / DEFAULT_DATA_DIR / CENSUS_NAME
        if found.is_file():
            return found
        if (folder / ".git").exists():
            break
    return None


class Globals:
    """Resolved settings for one invocation (flags through the config chain)."""

    def __init__(
        self,
        census: str | None,
        fmt: FormatKind | None,
        out: Path | None,
        force: bool | None,
        profile: Profile | None,
        include: str | None,
        exclude: str | None,
        *,
        no_rich: bool = False,
        project: str | None = None,
        banner: bool = True,
    ) -> None:
        self.display = resolve_display(no_rich)
        loaded = config_store.load(os.environ)
        settings = resolve(
            Flags(census, project, fmt, out, force, profile, include, exclude),
            os.environ,
            loaded.project,
            loaded.user,
        )
        for warning in (*self.display.warnings, *loaded.warnings, *settings.warnings):
            report_warning(self.display, warning)
        self.settings = settings
        self.fmt = settings.format
        self.out = settings.out
        self.force = settings.force
        self.profile = settings.profile
        self.include = settings.include
        self.exclude = settings.exclude
        self.project_id: str | None = None
        self.project_name: str | None = None
        self.project_dir: str | None = None
        self.project_source: str = "cwd"
        self.census_path = self._resolve_census(settings, banner)

    def _resolve_census(self, settings: Any, banner: bool) -> Path:
        # an explicit census file wins over everything
        if settings.census:
            self.project_source = "census"
            return resolve_census_path(settings.census)
        # an explicit --project flag / VIBER_PROJECT env wins over a local folder
        project_is_explicit = settings.sources.get("project") in (Source.FLAG, Source.ENV)
        if settings.project and project_is_explicit:
            return self._use_project(settings.project, banner)
        # otherwise prefer the project you are standing in (or under) — walk up
        local = _find_local_census(Path.cwd())
        if local is not None:
            return local
        # ...and only then fall back to the saved default project
        if settings.project:
            return self._use_project(settings.project, banner)
        return resolve_census_path(None)

    def _use_project(self, project_id: str, banner: bool) -> Path:
        self.project_source = "project"
        self.project_id = project_id
        rec = lookup_project(os.environ, project_id)
        if rec is None:
            raise CensusUsageError(
                f"unknown project id '{project_id}' — list them: `viber project list`, "
                f"or re-bind a moved folder: `viber project link {project_id} --to <dir>`"
            )
        self.project_dir = rec.get("dir")
        self.project_name = rec.get("name")
        touch_used(os.environ, project_id)
        if banner and self.fmt is FormatKind.TXT and self.out is None:
            print(
                render_parts(
                    self.display,
                    [TextPart(f"RESUMED {self.project_name or 'project'}", "bold bright_cyan")]
                    + [
                        TextPart(f"  id:  {self.project_id}"),
                        TextPart(f"  dir: {self.project_dir}"),
                    ],
                )
            )
        return Path(self.project_dir) / DEFAULT_DATA_DIR / CENSUS_NAME

    def selection(self, command: str) -> list[str]:
        return resolve_selection(command, self.profile, self.include, self.exclude)

    def selection_with(
        self, command: str, flag_overrides: dict[str, bool | None] | None = None
    ) -> list[str]:
        """Profile selection, then tri-state command flags (None = leave profile as
        is), then the user's explicit --include/--exclude which always win."""
        from viber.output.fields import specs_for
        from viber.output.render import registry_order

        sel = list(self.selection(command))
        if flag_overrides:
            for key, want in flag_overrides.items():
                if want is True and key not in sel:
                    sel.append(key)
                elif want is False:
                    sel = [k for k in sel if k != key]
        known = {s.key for s in specs_for(command)}
        for key in self.include:
            if key in known and key not in sel:
                sel.append(key)
        for key in self.exclude:
            sel = [k for k in sel if k != key]
        return [k for k in registry_order(command) if k in sel]

    def target(self) -> EmitTarget:
        # files are machine contracts: the plain display, whatever the terminal is
        display = PLAIN if self.out is not None else self.display
        return EmitTarget(fmt=self.fmt, out=self.out, force=self.force, display=display)

    def db(self) -> TelemetryDB:
        return TelemetryDB(self.census_path.parent / "telemetry.db")

    def load(self) -> Census:
        return load_census(self.census_path)


def command(fn: Callable[..., int]) -> Callable[..., None]:
    """Wrap `def h(..., g-built options...) -> int`: exception mapping + exit code."""

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        display = resolve_display(bool(kwargs.get("no_rich")))
        try:
            code = fn(*args, **kwargs)
        except (CensusError, EmitError, ConfigError, KeyError) as exc:
            report_error(display, str(exc))
            raise typer.Exit(1) from exc
        except (ProfileError, CensusUsageError, ValueError) as exc:
            report_error(display, str(exc))
            raise typer.Exit(2) from exc
        except typer.Exit:
            raise
        if code:
            raise typer.Exit(code)

    return wrapper
