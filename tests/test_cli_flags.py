"""CLI tests for read commands: flag equivalence, pairs, profiles, export."""

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from viber.app import build_app

runner = CliRunner()


@pytest.fixture(scope="module")
def app() -> Any:
    return build_app()


def invoke(app: Any, args: list[str]) -> Any:
    return runner.invoke(app, args)


def census_arg(census_file: Path) -> list[str]:
    return ["--census", str(census_file)]


class TestGlobals:
    def test_short_long_census(self, app: Any, census_file: Path) -> None:
        a = invoke(app, ["status", "-C", str(census_file)])
        b = invoke(app, ["status", "--census", str(census_file)])
        assert a.exit_code == b.exit_code == 0
        assert a.output == b.output

    def test_format_pair(self, app: Any, census_file: Path) -> None:
        short = invoke(app, ["status", "-f", "json"] + census_arg(census_file))
        long = invoke(app, ["status", "--format", "json"] + census_arg(census_file))
        assert short.exit_code == long.exit_code == 0
        assert json.loads(short.output) == json.loads(long.output)

    def test_default_is_txt(self, app: Any, census_file: Path) -> None:
        r = invoke(app, ["status"] + census_arg(census_file))
        assert "phase: DR" in r.output

    def test_missing_census_exit1(self, app: Any, tmp_path: Path) -> None:
        r = invoke(app, ["status", "-C", str(tmp_path / "nope.json")])
        assert r.exit_code == 1

    def test_profile_flags(self, app: Any, census_file: Path) -> None:
        m = invoke(app, ["skill", "steering", "-P", "minimal"] + census_arg(census_file))
        assert invoke(app, ["skill", "steering", "--profile", "full"]
                     + census_arg(census_file)).exit_code == 0
        assert m.exit_code == 0
        data = json.loads(
            invoke(
                app, ["skill", "steering", "-P", "full", "-f", "json"] + census_arg(census_file)
            ).output
        )
        assert "history" in data

    def test_include_exclude(self, app: Any, census_file: Path) -> None:
        r = invoke(
            app,
            ["skill", "steering", "--include", "history", "-f", "json"] + census_arg(census_file),
        )
        assert "history" in json.loads(r.output)
        r2 = invoke(
            app,
            ["skill", "steering", "--exclude", "description", "-f", "json"]
            + census_arg(census_file),
        )
        assert "description" not in r2.output

    def test_unknown_field_usage_error(self, app: Any, census_file: Path) -> None:
        r = invoke(app, ["skill", "steering", "--include", "nonsense"] + census_arg(census_file))
        assert r.exit_code == 2

    def test_dependency_conflict_error(self, app: Any, census_file: Path) -> None:
        r = invoke(
            app,
            ["skill", "steering", "-P", "minimal", "--include", "long_hints"]
            + census_arg(census_file),
        )
        assert r.exit_code == 2
        assert "requires" in r.output


class TestSkill:
    def test_brief_pair(self, app: Any, census_file: Path) -> None:
        a = invoke(app, ["skill", "steering", "-b"] + census_arg(census_file))
        b = invoke(app, ["skill", "steering", "--brief"] + census_arg(census_file))
        assert a.output == b.output
        assert a.output.startswith("steering v")

    def test_path_only(self, app: Any, census_file: Path) -> None:
        r = invoke(app, ["skill", "idea-md", "-p"] + census_arg(census_file))
        assert r.output.strip() == "null"

    def test_unknown_skill_exit1(self, app: Any, census_file: Path) -> None:
        r = invoke(app, ["skill", "nope"] + census_arg(census_file))
        assert r.exit_code == 1

    def test_long_toggle(self, app: Any, census_file: Path) -> None:
        withl = invoke(app, ["skill", "steering", "-l"] + census_arg(census_file))
        without = invoke(app, ["skill", "steering"] + census_arg(census_file))
        assert "long text here" in withl.output
        assert "long text here" not in without.output

    def test_no_relations(self, app: Any, census_file: Path) -> None:
        r = invoke(app, ["skill", "steering", "--no-relations"] + census_arg(census_file))
        assert "relations" not in r.output


class TestStepNextDeck:
    def test_current_step_and_name(self, app: Any, census_file: Path) -> None:
        cur = invoke(app, ["step"] + census_arg(census_file))
        named = invoke(app, ["step", "Idea & Understanding"] + census_arg(census_file))
        assert cur.exit_code == named.exit_code == 0

    def test_roster_and_pool_toggles(self, app: Any, census_file: Path) -> None:
        r = invoke(app, ["step", "--no-roster"] + census_arg(census_file))
        assert "idea-md" not in r.output or r.output.count("idea-md") <= 1  # only pool mentions
        p = invoke(app, ["step", "--no-pool"] + census_arg(census_file))
        assert "webthing" not in p.output

    def test_needs_full_only(self, app: Any, census_file: Path) -> None:
        r = invoke(app, ["step", "--needs"] + census_arg(census_file))
        assert "write the concept down" in r.output

    def test_next_count_short_long(self, app: Any, census_file: Path) -> None:
        a = invoke(app, ["next", "-n", "2"] + census_arg(census_file))
        b = invoke(app, ["next", "--count", "2"] + census_arg(census_file))
        assert a.exit_code == b.exit_code == 0
        assert "next: idea-md" in a.output

    def test_next_reasons_off(self, app: Any, census_file: Path) -> None:
        r = invoke(app, ["next", "--no-reasons"] + census_arg(census_file))
        assert "- follows" not in r.output and "- first" not in r.output

    def test_deck_toggles_and_unknown(self, app: Any, census_file: Path) -> None:
        r = invoke(app, ["deck", "author"] + census_arg(census_file))
        assert "Amr's Deck" in r.output
        ns = invoke(app, ["deck", "author", "--no-skills"] + census_arg(census_file))
        assert "idea-md" not in ns.output
        bad = invoke(app, ["deck", "nope"] + census_arg(census_file))
        assert bad.exit_code == 1


class TestListStatsPatterns:
    def test_list_and_alias(self, app: Any, census_file: Path) -> None:
        a = invoke(app, ["list"] + census_arg(census_file))
        b = invoke(app, ["ls"] + census_arg(census_file))
        assert a.output == b.output
        assert "idea-md" in a.output

    def test_filter_and_bad_filter(self, app: Any, census_file: Path) -> None:
        r = invoke(app, ["list", "--filter", "type=battery"] + census_arg(census_file))
        assert "steering" in r.output and "idea-md" not in r.output
        bad = invoke(app, ["list", "--filter", "nope=x"] + census_arg(census_file))
        assert bad.exit_code == 2

    def test_stats_no_data_and_patterns(self, app: Any, census_file: Path) -> None:
        s = invoke(app, ["stats"] + census_arg(census_file))
        assert "no telemetry" in s.output
        p = invoke(app, ["patterns"] + census_arg(census_file))
        assert p.exit_code == 0


class TestExport:
    def test_flush_txt_and_json(self, app: Any, census_file: Path, tmp_path: Path) -> None:
        o1 = tmp_path / "s.txt"
        r = invoke(app, ["status", "-o", str(o1)] + census_arg(census_file))
        assert r.exit_code == 0
        assert o1.read_text(encoding="utf-8").startswith("phase:")
        o2 = tmp_path / "s.json"
        invoke(app, ["status", "-f", "json", "--out", str(o2)] + census_arg(census_file))
        assert json.loads(o2.read_text(encoding="utf-8"))["total"] == 5

    def test_overwrite_refused_then_forced(
        self, app: Any, census_file: Path, tmp_path: Path
    ) -> None:
        o = tmp_path / "s.txt"
        o.write_text("old", encoding="utf-8")
        r = invoke(app, ["status", "-o", str(o)] + census_arg(census_file))
        assert r.exit_code == 1 and o.read_text(encoding="utf-8") == "old"
        r2 = invoke(app, ["status", "-o", str(o), "--force"] + census_arg(census_file))
        assert r2.exit_code == 0 and "phase" in o.read_text(encoding="utf-8")


def test_list_by_invalid(app: Any, census_file: Path) -> None:
    r = invoke(app, ["list", "--by", "nonsense"] + census_arg(census_file))
    assert r.exit_code == 2


def test_patterns_no_data_message(app: Any, census_file: Path) -> None:
    r = invoke(app, ["patterns"] + census_arg(census_file))
    assert r.exit_code == 0
    assert "no telemetry" in r.output


def test_situation_one_call(app: Any, census_file: Path) -> None:
    r = invoke(app, ["situation"] + census_arg(census_file))
    assert r.exit_code == 0
    for section in ("phase:", "step:", "usage", "next", "open decisions"):
        assert section in r.output


def test_situation_json_keys(app: Any, census_file: Path) -> None:
    r = invoke(app, ["situation", "-f", "json"] + census_arg(census_file))
    assert r.exit_code == 0
    data = json.loads(r.output)
    assert {"phase", "step", "roster", "usage", "next", "open"} <= set(data)


def test_skill_content_is_paths_only(app: Any, census_file: Path) -> None:
    full = invoke(app, ["skill", "steering"] + census_arg(census_file))
    only = invoke(app, ["skill", "steering", "--content"] + census_arg(census_file))
    assert only.exit_code == 0
    assert "description" not in only.output
    assert "SKILL.md" in only.output
    assert len(only.output) < len(full.output)


class TestSettingsChainCli:
    def test_env_census_found(self, app: Any, census_file: Path, monkeypatch: Any) -> None:
        monkeypatch.setenv("VIBER_CENSUS", str(census_file))
        r = invoke(app, ["status"])
        assert r.exit_code == 0 and "phase: DR" in r.output

    def test_flag_beats_env(
        self, app: Any, census_file: Path, tmp_path: Path, monkeypatch: Any
    ) -> None:
        monkeypatch.setenv("VIBER_CENSUS", str(tmp_path / "missing.json"))
        r = invoke(app, ["status", "-C", str(census_file)])
        assert r.exit_code == 0

    def test_env_profile_changes_output(
        self, app: Any, census_file: Path, monkeypatch: Any
    ) -> None:
        base = invoke(app, ["skill", "steering", "-C", str(census_file)])
        monkeypatch.setenv("VIBER_PROFILE", "minimal")
        lean = invoke(app, ["skill", "steering", "-C", str(census_file)])
        assert "description" in base.output
        assert "description" not in lean.output

    def test_config_file_layer(
        self, app: Any, census_file: Path, tmp_path: Path, monkeypatch: Any
    ) -> None:
        cfg = tmp_path / "cfg.json"
        cfg.write_text('{"profile": "minimal"}', encoding="utf-8")
        monkeypatch.setenv("VIBER_CONFIG", str(cfg))
        r = invoke(app, ["skill", "steering", "-C", str(census_file)])
        assert "description" not in r.output

    def test_no_force_tristate(self, app: Any, census_file: Path, tmp_path: Path) -> None:
        o = tmp_path / "out.txt"
        o.write_text("old", encoding="utf-8")
        r = invoke(app, ["status", "-o", str(o), "--no-force", "-C", str(census_file)])
        assert r.exit_code == 1 and o.read_text(encoding="utf-8") == "old"

    def test_telemetry_off(self, app: Any, census_file: Path, monkeypatch: Any) -> None:
        monkeypatch.setenv("VIBER_TELEMETRY", "0")
        r = invoke(app, ["use", "idea-md", "-C", str(census_file)])
        assert r.exit_code == 0 and "telemetry disabled" in r.output
        assert not (census_file.parent / "telemetry.db").exists()
        r2 = invoke(app, ["outcome", "idea-md", "ok", "-C", str(census_file)])
        assert r2.exit_code == 0 and "telemetry disabled" in r2.output
