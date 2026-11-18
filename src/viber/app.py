"""Typer app assembly: registration lives in cli.registry (the plugin seam).

Adding a command = write the handler, put it in the module's COMMANDS dict.
"""

import os
import sys

# VIBER_RICH=0 must be seen by typer before it loads, so --help panels degrade too
if os.environ.get("VIBER_RICH", "").strip().lower() in {"0", "false", "no", "off"}:
    os.environ.setdefault("TYPER_USE_RICH", "0")

import typer  # noqa: E402

from viber import __version__
from viber.cli import registry
from viber.core.settings import Flags, Settings, resolve
from viber.data import config_store
from viber.data.config_store import ConfigPaths
from viber.output.display import report_warning, resolve_display


def _boot() -> tuple[Settings, ConfigPaths]:
    """Chain snapshot taken before parsing: the plugins opt-in must be known
    while commands are still being registered."""
    loaded = config_store.load(os.environ)
    settings = resolve(Flags(), os.environ, loaded.project, loaded.user)
    display = resolve_display()
    for warning in (*display.warnings, *loaded.warnings, *settings.warnings):
        report_warning(display, warning)
    return settings, config_store.locate(os.environ)


def build_app() -> typer.Typer:
    app = typer.Typer(
        add_completion=False,
        no_args_is_help=True,
        help=f"Viber census CLI v{__version__} — the agent's read/write interface "
        "to .viber/.data/viber.json + telemetry.db",
    )
    settings, paths = _boot()
    warnings = registry.register(
        app,
        plugins_enabled=settings.plugins,
        plugin_dirs=(paths.project_plugins, paths.user_plugins),
    )
    for warning in warnings:
        report_warning(resolve_display(), warning)
    return app


def _force_utf8() -> None:
    # Census hints carry em-dashes; Windows pipes default to the locale codepage
    # and corrupt them for any byte-reading consumer.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    """Entry point (console script + `python -m viber`).

    Vendored typer._click only runs its real intake when args are passed explicitly,
    so we always hand it sys.argv[1:].
    """
    _force_utf8()
    build_app()(sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    main()
