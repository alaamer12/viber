"""Display layer tests: resolution precedence, cross-backend consistency,
byte-clean guarantees, and the --no-rich flag end to end."""

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from viber.app import build_app
from viber.output import display as dp
from viber.output.display import (
    Display,
    KVPart,
    TextPart,
    display_table,
    render_parts,
    resolve_display,
    resolve_width,
)
from viber.output.display_cmd import RICH_BUILDERS
from viber.output.render import RENDERERS

runner = CliRunner()

RICH = Display("rich", False, 80)
PLAIN = Display("plain", False, 80)


@pytest.fixture(scope="module")
def app() -> Any:
    return build_app()


def call(app: Any, args: list[str], census_file: Path | None = None) -> Any:
    base = ["--census", str(census_file)] if census_file else []
    return runner.invoke(app, args + base)


class TestResolution:
    def test_flag_beats_everything(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("VIBER_RICH", "1")
        assert resolve_display(no_rich=True).layout == "plain"

    def test_env_zero_forces_plain(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("VIBER_RICH", "0")
        d = resolve_display()
        assert d.layout == "plain" and not d.color

    def test_env_one_forces_rich_layout_piped(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("VIBER_RICH", "1")
        monkeypatch.setattr(dp, "rich_available", lambda: True)
        monkeypatch.setattr(dp, "_tty", lambda: False)
        d = resolve_display()
        assert d.layout == "rich" and not d.color  # piped: layout yes, ANSI never

    def test_color_only_with_tty(self, monkeypatch: Any) -> None:
        monkeypatch.setattr(dp, "rich_available", lambda: True)
        monkeypatch.setattr(dp, "_tty", lambda: True)
        assert resolve_display().color

    def test_auto_layout_rich_even_piped(self, monkeypatch: Any) -> None:
        monkeypatch.setattr(dp, "rich_available", lambda: True)
        monkeypatch.setattr(dp, "_tty", lambda: False)
        d = resolve_display()
        assert d.layout == "rich" and not d.color  # display is rich; color is the tty's

    def test_rich_unavailable_still_degrades_plain(self, monkeypatch: Any) -> None:
        monkeypatch.setattr(dp, "rich_available", lambda: False)
        assert resolve_display().layout == "plain"

    def test_garbage_env_warns_and_falls_to_auto(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("VIBER_RICH", "maybe")
        monkeypatch.setattr(dp, "rich_available", lambda: False)
        d = resolve_display()
        assert d.layout == "plain" and any("maybe" in w for w in d.warnings)

    def test_forced_rich_without_rich_degrades(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("VIBER_RICH", "1")
        monkeypatch.setattr(dp, "rich_available", lambda: False)
        d = resolve_display()
        assert d.layout == "plain" and any("unavailable" in w for w in d.warnings)

    def test_width_clamps(self, monkeypatch: Any) -> None:
        assert resolve_width({"COLUMNS": "10"}) == 60
        assert resolve_width({"COLUMNS": "999"}) == 240
        assert resolve_width({"COLUMNS": "120"}) == 120


class TestBackendConsistency:
    ROWS = [["idea-md", "1.0.2", "ready"], ["steering", "1.0.2", "blocked"]]

    def test_empty_table_says_none_in_both_modes(self) -> None:
        assert "(none)" in display_table(RICH, ["A", "B"], [])
        assert "(none)" in display_table(PLAIN, ["A", "B"], [])

    def test_same_information_both_modes(self) -> None:
        rich_out = display_table(RICH, ["Skill", "Version", "Status"], self.ROWS)
        plain_out = display_table(PLAIN, ["Skill", "Version", "Status"], self.ROWS)
        for cell in ("idea-md", "steering", "ready", "blocked", "1.0.2"):
            assert cell in rich_out and cell in plain_out

    def test_bracketed_prose_survives_rich(self) -> None:
        text = 'awaiting ["user decision"] on battery vs meta'
        out = render_parts(RICH, [TextPart(text)])
        assert '["user decision"]' in out
        assert "[battery]" not in out  # markup was NOT interpreted

    def test_unicode_both_modes(self) -> None:
        rows = [["أي مفهوم", "idea — written"]]
        for d in (RICH, PLAIN):
            out = display_table(d, ["Desc", "Note"], rows)
            assert "أي مفهوم" in out and "—" in out

    def test_no_ansi_when_layout_rich_but_piped(self) -> None:
        out = display_table(RICH, ["A"], [["x"]])
        assert "\x1b" not in out

    def test_color_only_emits_ansi_for_rich(self) -> None:
        colorful = Display("rich", True, 80)
        assert "\x1b" in display_table(colorful, ["A"], [["x"]])

    def test_width_respected(self) -> None:
        narrow = Display("rich", False, 60)
        rows = [["some-skill", "a" * 90]]
        out = display_table(narrow, ["Skill", "Desc"], rows)
        assert all(len(line) <= 60 for line in out.split("\n"))

    def test_kv_both_modes(self) -> None:
        parts = [KVPart([("phase", "DR"), ("step", "Idea & Understanding")])]
        for d in (RICH, PLAIN):
            out = render_parts(d, parts)
            assert "DR" in out and "Idea & Understanding" in out

    def test_large_table_both_modes(self) -> None:
        rows = [[f"s{i}", str(i)] for i in range(200)]
        for d in (RICH, PLAIN):
            out = display_table(d, ["Skill", "N"], rows)
            for probe in ("s0", "s99", "s199"):
                assert probe in out


def test_rich_builders_subset_of_renderers() -> None:
    assert set(RICH_BUILDERS) <= set(RENDERERS)


class TestCliFlag:
    @pytest.mark.parametrize(
        ("cmd", "info", "boxy"),
        [
            (["status"], "phase: DR", False),
            (["list"], "steering", True),
            (["step"], "Idea & Understanding", True),
            (["skill", "steering"], "description", True),
            (["lint"], "lint:", True),
        ],
    )
    def test_default_rich_nr_plain_same_info(
        self, app: Any, census_file: Path, cmd: list[str], info: str, boxy: bool
    ) -> None:
        default = call(app, cmd, census_file)
        plain = call(app, cmd + ["-nr"], census_file)
        assert default.exit_code == plain.exit_code == 0
        assert info in default.output and info in plain.output
        assert "\x1b" not in default.output  # piped: layout rich, bytes clean
        has_boxes = "─" in default.output or "┌" in default.output
        assert has_boxes == boxy
        assert "─" not in plain.output and "┌" not in plain.output

    def test_forced_env_equals_default_now(
        self, app: Any, census_file: Path, monkeypatch: Any
    ) -> None:
        monkeypatch.setenv("VIBER_RICH", "1")
        forced = call(app, ["list"], census_file)
        default = call(app, ["list"], census_file)
        assert forced.output == default.output
        assert "\x1b" not in forced.output and "─" in forced.output

    def test_help_documents_the_flag(self, app: Any) -> None:
        r = call(app, ["status", "--help"])
        assert "--no-rich" in r.output and "-nr" in r.output

    def test_bad_cluster_rejected(self, app: Any, census_file: Path) -> None:
        r = call(app, ["next", "-rn"], census_file)
        assert r.exit_code == 2

    def test_json_stays_machine_strict_under_forced_rich(
        self, app: Any, census_file: Path, monkeypatch: Any
    ) -> None:
        monkeypatch.setenv("VIBER_RICH", "1")
        r = call(app, ["status", "-f", "json"], census_file)
        assert json.loads(r.output)["phase"]

    def test_out_file_stays_plain_under_forced_rich(
        self, app: Any, census_file: Path, tmp_path: Path, monkeypatch: Any
    ) -> None:
        monkeypatch.setenv("VIBER_RICH", "1")
        out = tmp_path / "status.txt"
        r = call(app, ["status", "-o", str(out)], census_file)
        assert r.exit_code == 0
        text = out.read_text(encoding="utf-8")
        assert "\x1b" not in text and "│" not in text and "phase" in text

    def test_error_goes_to_stderr_stdout_clean(self, app: Any, census_file: Path) -> None:
        r = call(app, ["use", "ghost"], census_file)
        assert r.exit_code == 1
        assert r.stdout_bytes == b"" or r.stdout == ""
