"""Command-name tripwire: every `viber <token>` instruction we hand an agent — in
docs, README, PIPELINE, shipped SKILL.md files, or a limits recovery line — must
name a command that exists on the frozen surface. The `/viber compact` slash form
names SKILLS, not subcommands, and is deliberately excluded."""

import re
from pathlib import Path

from typer.main import get_command

from viber.app import build_app
from viber.models.limits import LIMITS

ROOT = Path(__file__).resolve().parents[1]
SURFACE = set(get_command(build_app()).commands) | {"command"}  # generic placeholder
PATTERN = re.compile(r"(?<!/)\b(?:uv run )?viber ([a-z][a-z0-9_-]*)")
SPAN = re.compile(r"`([^`\n]+)`")

SOURCES = [ROOT / "README.md", ROOT / "PIPELINE.md", ROOT / "USAGE.md"]
SOURCES += sorted((ROOT / "docs").rglob("*.md"))
SOURCES += sorted((ROOT / "skills").glob("*/SKILL.md"))


def test_documented_commands_exist() -> None:
    bad: list[str] = []
    for f in SOURCES:
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8")
        if f.parent == ROOT / "docs" / "bugs":
            # Incident reproductions quote nonexistent commands; only resolutions are guidance.
            text = text.partition("## Resolution\n")[2]
        for span in SPAN.findall(text):
            for m in PATTERN.finditer(span):
                if m.group(1) not in SURFACE:
                    bad.append(f"{f.relative_to(ROOT)}: viber {m.group(1)}")
    assert bad == []


def test_recovery_lines_name_real_commands() -> None:
    for lim in LIMITS.values():
        m = re.search(r"(?<!/)\bviber ([a-z][a-z0-9_-]*)", lim.recovery)
        if m is not None:
            assert m.group(1) in SURFACE, (lim.field, lim.recovery)
