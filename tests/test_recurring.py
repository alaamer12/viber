"""Recurring skills: a used-but-never-ok'd recurring skill re-surfaces cross-step
in the `revisit` pool once it falls out of the current step, and an ok settles it."""

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from viber.app import build_app
from viber.data.telemetry import TelemetryDB

runner = CliRunner()


@pytest.fixture(scope="module")
def app() -> Any:
    return build_app()


def call(app: Any, args: list[str], census_file: Path) -> Any:
    return runner.invoke(app, args + ["-C", str(census_file)])


def _revisit(app: Any, census_file: Path) -> list[str]:
    j = json.loads(call(app, ["next", "-f", "json"], census_file).output)
    return [r["skill"] for r in j["revisit"]]


def test_recurring_surfaces_after_the_step_advances(app: Any, census_file: Path) -> None:
    assert call(app, ["set", "idea-md", "recurring", "true"], census_file).exit_code == 0
    assert call(app, ["use", "idea-md"], census_file).exit_code == 0
    assert call(app, ["outcome", "idea-md", "skip", "project unclear"], census_file).exit_code == 0
    # still in step 1 (DR) -> excluded from revisit (it is a current-step candidate)
    assert "idea-md" not in _revisit(app, census_file)
    # advance the project -> idea-md falls out of the roster but stays recurring/pending
    assert call(app, ["set", ".", "phase", "IP"], census_file).exit_code == 0
    assert "idea-md" in _revisit(app, census_file)
    j = json.loads(call(app, ["next", "-f", "json"], census_file).output)
    row = next(r for r in j["revisit"] if r["skill"] == "idea-md")
    assert row["reason"] == "recurring; last skip — project unclear"
    # settle it with an ok -> leaves the pool
    assert call(app, ["use", "idea-md"], census_file).exit_code == 0
    assert call(app, ["outcome", "idea-md", "ok", "rulebook written"], census_file).exit_code == 0
    assert "idea-md" not in _revisit(app, census_file)


def test_situation_shows_revisit(app: Any, census_file: Path) -> None:
    assert call(app, ["set", "idea-md", "recurring", "true"], census_file).exit_code == 0
    assert call(app, ["use", "idea-md"], census_file).exit_code == 0
    assert call(app, ["outcome", "idea-md", "fail"], census_file).exit_code == 0
    assert call(app, ["set", ".", "phase", "IP"], census_file).exit_code == 0
    s = call(app, ["situation"], census_file)
    assert "REVISIT (recurring, not yet ok)" in s.output and "idea-md" in s.output
    j = json.loads(call(app, ["situation", "-f", "json"], census_file).output)
    assert any(r["skill"] == "idea-md" for r in j["revisit"])


def test_never_invoked_recurring_is_absent(app: Any, census_file: Path) -> None:
    assert call(app, ["set", "steering", "recurring", "true"], census_file).exit_code == 0
    assert "steering" not in _revisit(app, census_file)  # recurring but no telemetry


def test_non_recurring_skip_is_absent(app: Any, census_file: Path) -> None:
    assert call(app, ["use", "reveal"], census_file).exit_code == 0
    assert call(app, ["outcome", "reveal", "skip"], census_file).exit_code == 0
    assert call(app, ["set", ".", "phase", "IP"], census_file).exit_code == 0
    assert "reveal" not in _revisit(app, census_file)  # not recurring


def test_set_recurring_roundtrip_and_bogus(app: Any, census_file: Path) -> None:
    assert call(app, ["set", "reveal", "recurring", "true"], census_file).exit_code == 0
    data = json.loads(census_file.read_text(encoding="utf-8"))
    assert data["skills"]["reveal"]["recurring"] is True
    assert call(app, ["set", "reveal", "recurring", "yes"], census_file).exit_code == 2


def test_latest_returns_newest_invocation(db: TelemetryDB) -> None:
    from viber.data.telemetry import now_iso

    db.record_invocation("idea-md", now_iso(), "Idea & Understanding", "DR")
    assert db.latest("idea-md")["outcome"] is None  # still open
    db.close_open("idea-md", "skip", "deferred")
    last = db.latest("idea-md")
    assert last["outcome"] == "skip" and last["note"] == "deferred"
    assert db.latest("ghost") is None


def test_recurring_rich_renders_revisit(
    app: Any, census_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VIBER_RICH", "true")
    call(app, ["set", "idea-md", "recurring", "true"], census_file)
    call(app, ["use", "idea-md"], census_file)
    call(app, ["outcome", "idea-md", "skip", "later"], census_file)
    call(app, ["set", ".", "phase", "IP"], census_file)
    res = call(app, ["situation"], census_file)
    assert "REVISIT" in res.output and "idea-md" in res.output
