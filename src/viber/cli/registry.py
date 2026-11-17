"""Command registration — the internal plugin seam.

Built-in modules register first, command families come in as sub-apps (config
is the proof that the seam works without any special-casing), and drop-in plugins
last: they can add names, never shadow built-ins or each other — first wins,
rest skipped with a warning.
"""

import importlib
from collections.abc import Callable
from pathlib import Path

import typer

BUILTIN_MODULES: tuple[str, ...] = ("viber.cli.read", "viber.cli.write", "viber.cli.telemetry")

SUBAPPS: tuple[tuple[str, str, str], ...] = (
    (
        "config",
        "Viber settings — chain-aware defaults (flag > env > project > user > default)",
        "viber.cli.config_cmd",
    ),
)


def register(
    app: typer.Typer,
    *,
    plugins_enabled: bool = False,
    plugin_dirs: tuple[Path, ...] = (),
) -> list[str]:
    taken: set[str] = set()
    warnings: list[str] = []

    for mod_name in BUILTIN_MODULES:
        module = importlib.import_module(mod_name)
        for name, fn in module.COMMANDS.items():
            app.command(name)(fn)
            taken.add(name)

    for sub_name, help_text, mod_name in SUBAPPS:
        sub = typer.Typer(name=sub_name, no_args_is_help=True, help=help_text)
        for cmd_name, fn in importlib.import_module(mod_name).COMMANDS.items():
            sub.command(cmd_name)(fn)
        app.add_typer(sub)
        taken.add(sub_name)

    if plugins_enabled:
        from viber.cli.plugins import collect

        commands_by_origin, load_warnings = collect(plugin_dirs)
        warnings.extend(load_warnings)
        for origin, commands in commands_by_origin:
            for name, fn in commands.items():
                if name in taken:
                    warnings.append(f"plugin {origin}: '{name}' collides — skipped")
                    continue
                app.command(name)(fn)
                taken.add(name)

    return warnings


Handler = Callable[..., int]
