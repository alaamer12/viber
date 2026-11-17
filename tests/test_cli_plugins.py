"""Drop-in plugins: off by default, add-only, collision and failure skip-and-warn."""

from pathlib import Path

import typer
from typer.testing import CliRunner

from viber.app import build_app
from viber.cli import registry

runner = CliRunner()

GOOD = """
from viber.cli.deps import command


@command
def hello() -> int:
    print("hi from plugin")
    return 0


COMMANDS = {"hello": hello}
"""
COLLIDER = 'COMMANDS = {"status": lambda: 0}\n'
BROKEN = "def (\n"
NO_DICT = "x = 1\n"


def make_plugins(tmp_path: Path, files: dict[str, str]) -> tuple[Path, ...]:
    plugins = tmp_path / ".viber" / "plugins"
    plugins.mkdir(parents=True)
    for name, body in files.items():
        (plugins / name).write_text(body, encoding="utf-8")
    return (plugins,)


def register(tmp_path: Path, files: dict[str, str]) -> tuple[typer.Typer, list[str]]:
    app = typer.Typer()
    dirs = make_plugins(tmp_path, files)
    warnings = registry.register(app, plugins_enabled=True, plugin_dirs=dirs)
    return app, warnings


def test_off_by_default(tmp_path: Path) -> None:
    dirs = make_plugins(tmp_path, {"x.py": GOOD})
    assert dirs  # plugin present...
    app = build_app()  # ...but plugins are not enabled: default chain says false
    r = runner.invoke(app, ["hello"])
    assert r.exit_code == 2


def test_enabled_adds_command(tmp_path: Path) -> None:
    app, warnings = register(tmp_path, {"x.py": GOOD})
    assert warnings == []
    r = runner.invoke(app, ["hello"])
    assert r.exit_code == 0 and "hi from plugin" in r.output


def test_collision_skipped_with_warning(tmp_path: Path) -> None:
    app, warnings = register(tmp_path, {"x.py": COLLIDER})
    assert any("collides" in w for w in warnings)
    assert runner.invoke(app, ["--help"]).exit_code == 0


def test_broken_plugin_skipped_others_survive(tmp_path: Path) -> None:
    app, warnings = register(tmp_path, {"bad.py": BROKEN, "good.py": GOOD})
    assert any("import failed" in w for w in warnings)
    r = runner.invoke(app, ["hello"])
    assert r.exit_code == 0 and "hi from plugin" in r.output


def test_missing_commands_dict_warns(tmp_path: Path) -> None:
    _, warnings = register(tmp_path, {"x.py": NO_DICT})
    assert any("no COMMANDS" in w for w in warnings)
