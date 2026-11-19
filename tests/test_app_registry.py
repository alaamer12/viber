"""The command surface is frozen: adding or removing a command must be a
deliberate act that updates this list, never an accident of an import."""

from typer.main import get_command

from viber.app import build_app

EXPECTED = sorted(
    [
        "skill",
        "step",
        "next",
        "deck",
        "status",
        "situation",
        "fields",
        "list",
        "ls",
        "stats",
        "patterns",
        "set",
        "log",
        "note",
        "add-skill",
        "add-s",
        "remove-skill",
        "rm-skill",
        "refresh",
        "lint",
        "use",
        "outcome",
        "config",
        "init",
        "now",
        "project",
        "registry",
    ]
)


def test_command_surface_frozen() -> None:
    names = sorted(get_command(build_app()).commands)
    assert names == EXPECTED
