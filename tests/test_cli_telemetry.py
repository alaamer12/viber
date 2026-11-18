"""Telemetry command tests: use/outcome/stats/patterns round-trip."""

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


def call(app: Any, args: list[str], census_file: Path) -> Any:
    return runner.invoke(app, args + ["-C", str(census_file)])


def test_use_outcome_stats_flow(app: Any, census_file: Path) -> None:
    assert call(app, ["use", "idea-md"], census_file).exit_code == 0
    assert (census_file.parent / "telemetry.db").is_file()
    r = call(app, ["use", "reveal"], census_file)
    assert r.exit_code == 0
    o = call(app, ["outcome", "idea-md", "ok", "worked"], census_file)
    assert o.exit_code == 0 and "idea-md -> ok" in o.output
    s = call(app, ["stats", "idea-md", "-f", "json"], census_file)
    data = json.loads(s.output)
    rows = data["rows"]
    assert rows["count"] == 1 and rows["ok"] == 1
    p = call(app, ["patterns", "-f", "json"], census_file)
    payload = json.loads(p.output)
    rows = payload["rows"]
    assert rows == [] or rows[0]["sequence"] == "idea-md -> reveal"
    n = call(app, ["next", "-f", "json"], census_file)
    assert "reveal" in json.dumps(json.loads(n.output))  # suggestion or candidate


def test_outcome_without_open_fails(app: Any, census_file: Path) -> None:
    r = call(app, ["outcome", "steering", "ok"], census_file)
    assert r.exit_code == 1


def test_use_unknown_skill(app: Any, census_file: Path) -> None:
    assert call(app, ["use", "ghost"], census_file).exit_code == 1


def test_previous_step_surfaces_in_next_and_situation(app: Any, census_file: Path) -> None:
    assert call(app, ["use", "steering"], census_file).exit_code == 0
    assert call(app, ["outcome", "steering", "ok"], census_file).exit_code == 0
    assert "last: steering" in call(app, ["next"], census_file).output
    assert "last: steering" in call(app, ["situation"], census_file).output
    j = json.loads(call(app, ["next", "-f", "json"], census_file).output)
    assert j["previous"]["skill"] == "steering" and j["previous"]["outcome"] == "ok"


def test_previous_absent_without_telemetry(app: Any, census_file: Path) -> None:
    s = call(app, ["situation"], census_file)
    assert "no previous step recorded" in s.output
