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

from viber.core.settings import Flags, resolve
from viber.data import config_store
from viber.data.config_store import ConfigError
from viber.data.store import CensusError, CensusUsageError, load_census, resolve_census_path
from viber.data.telemetry import TelemetryDB
from viber.models.domain import FormatKind, Profile
from viber.models.schema import Census
from viber.output.display import PLAIN, report_error, report_warning, resolve_display
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
    ) -> None:
        self.display = resolve_display(no_rich)
        loaded = config_store.load(os.environ)
        settings = resolve(
            Flags(census, fmt, out, force, profile, include, exclude),
            os.environ,
            loaded.project,
            loaded.user,
        )
        for warning in (*self.display.warnings, *loaded.warnings, *settings.warnings):
            report_warning(self.display, warning)
        self.settings = settings
        self.census_path = resolve_census_path(settings.census)
        self.fmt = settings.format
        self.out = settings.out
        self.force = settings.force
        self.profile = settings.profile
        self.include = settings.include
        self.exclude = settings.exclude

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
