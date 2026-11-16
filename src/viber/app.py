"""Typer app assembly: registers every command module's COMMANDS map.

Adding a command = write the handler, put it in the module's COMMANDS dict. Nothing else.
"""

import typer

from viber import __version__


def _register(app: typer.Typer) -> None:
    from viber.cli import read, telemetry, write

    for module in (read, write, telemetry):
        for name, fn in module.COMMANDS.items():
            app.command(name)(fn)


def build_app() -> typer.Typer:
    app = typer.Typer(
        add_completion=False,
        no_args_is_help=True,
        help=f"Viber census CLI v{__version__} — the agent's read/write interface "
        "to .viber/.data/viber.json + telemetry.db",
    )
    _register(app)
    return app


def main(argv: list[str] | None = None) -> None:
    """Entry point (console script + `python -m viber` + launcher shim).

    Vendored typer._click only runs its real intake when args are passed explicitly,
    so we always hand it sys.argv[1:].
    """
    import sys

    build_app()(sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    main()
