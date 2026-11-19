"""Notes (global --note + `note --on`) and bulk `use`."""

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


def _notes(census_file: Path, skill: str = "idea-md") -> list[dict[str, Any]]:
    return json.loads(census_file.read_text(encoding="utf-8"))["skills"][skill]["notes"]


# --- bulk use ---------------------------------------------------------------
def test_bulk_use_records_each(app: Any, census_file: Path) -> None:
    r = call(app, ["use", "idea-md", "reveal"], census_file)
    assert r.exit_code == 0 and "use idea-md, reveal" in r.output
    for s in ("idea-md", "reveal"):
        data = json.loads(call(app, ["stats", s, "-f", "json"], census_file).output)
        assert data["rows"]["count"] == 1


def test_bulk_use_validate_first_records_nothing(app: Any, census_file: Path) -> None:
    r = call(app, ["use", "idea-md", "ghost"], census_file)
    assert r.exit_code == 1 and "not in census" in r.output
    data = json.loads(call(app, ["stats", "idea-md", "-f", "json"], census_file).output)
    assert data["present"] is False  # bad name in the bulk aborted before any record


# --- notes ------------------------------------------------------------------
def test_note_on_records_without_invocation(app: Any, census_file: Path) -> None:
    r = call(app, ["note", "--on", "idea-md", "the fence still needs REACH"], census_file)
    assert r.exit_code == 0
    assert _notes(census_file)[0]["text"] == "the fence still needs REACH"
    assert _notes(census_file)[0]["context"] == "note"
    stats = json.loads(call(app, ["stats", "idea-md", "-f", "json"], census_file).output)
    assert stats["present"] is False  # note alone never invokes


def test_use_with_note_attaches_note(app: Any, census_file: Path) -> None:
    assert call(app, ["use", "idea-md", "--note", "first pass"], census_file).exit_code == 0
    assert _notes(census_file)[-1]["context"] == "use"
    stats = json.loads(call(app, ["stats", "idea-md", "-f", "json"], census_file).output)
    assert stats["rows"]["count"] == 1


def test_outcome_note_lands_on_census(app: Any, census_file: Path) -> None:
    assert call(app, ["use", "reveal"], census_file).exit_code == 0
    assert call(app, ["outcome", "reveal", "skip", "landscape unclear"], census_file).exit_code == 0
    assert _notes(census_file, "reveal")[-1]["context"] == "outcome"


def test_project_note_targets_census_root(app: Any, census_file: Path) -> None:
    assert call(app, ["note", "--on", ".", "ship by end of week"], census_file).exit_code == 0
    root = json.loads(census_file.read_text(encoding="utf-8"))["notes"]
    assert root[-1]["text"] == "ship by end of week"


def test_notes_hidden_until_requested(app: Any, census_file: Path) -> None:
    call(app, ["note", "--on", "idea-md", "visible only on demand"], census_file)
    std = call(app, ["skill", "idea-md", "-f", "json"], census_file)
    assert "notes" not in json.loads(std.output)  # STANDARD omits notes
    full = call(app, ["skill", "idea-md", "-P", "full", "-f", "json"], census_file)
    assert "visible only on demand" in json.dumps(json.loads(full.output))
    txt = call(app, ["skill", "idea-md", "--notes", "-nr"], census_file)
    assert "notes" in txt.output and "visible only on demand" in txt.output


def test_notes_roll_at_cap(app: Any, census_file: Path) -> None:
    data = json.loads(census_file.read_text(encoding="utf-8"))
    data["skills"]["idea-md"]["notes"] = [
        {"date": "2020-01-01", "text": f"old {i}", "context": "note"} for i in range(100)
    ]
    census_file.write_text(json.dumps(data), encoding="utf-8")
    r = call(app, ["note", "--on", "idea-md", "the overflow note"], census_file)
    assert r.exit_code == 0 and "rolled" in r.output
    after = _notes(census_file)
    assert len(after) == 100 and after[-1]["text"] == "the overflow note"
    assert not any(str(n["text"]).startswith("old 0") for n in after)


def test_note_on_unknown_skill(app: Any, census_file: Path) -> None:
    assert call(app, ["note", "--on", "ghost", "x"], census_file).exit_code == 1


def test_note_survives_telemetry_disabled(
    app: Any, census_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VIBER_TELEMETRY", "false")
    r = call(app, ["use", "idea-md", "--note", "kept anyway"], census_file)
    assert r.exit_code == 0 and "telemetry disabled" in r.output and "note recorded" in r.output
    assert _notes(census_file)[-1] == {
        "date": _notes(census_file)[-1]["date"],
        "text": "kept anyway",
        "context": "use",
    }
    # no invocation was recorded — the note is pure census state
    assert json.loads(call(app, ["stats", "idea-md", "-f", "json"], census_file).output)["present"] is False


def test_outcome_note_survives_telemetry_disabled(
    app: Any, census_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VIBER_TELEMETRY", "false")
    r = call(app, ["outcome", "reveal", "ok", "evidence"], census_file)
    assert r.exit_code == 0 and "note recorded on reveal" in r.output
    assert _notes(census_file, "reveal")[-1]["context"] == "outcome"
