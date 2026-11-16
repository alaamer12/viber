"""Write-command tests: set semantics, add/remove cycle, refresh, dry-run."""

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


def read(census_file: Path) -> dict:
    return json.loads(census_file.read_text(encoding="utf-8"))


def test_set_blockers_roundtrip(app: Any, census_file: Path) -> None:
    r = call(app, ["set", "idea-md", "blockers", '["waiting for user"]'], census_file)
    assert r.exit_code == 0 and "updated" in r.output
    assert read(census_file)["skills"]["idea-md"]["fit"]["blockers"] == ["waiting for user"]
    call(app, ["set", "idea-md", "blockers", "[]"], census_file)
    assert read(census_file)["skills"]["idea-md"]["fit"]["blockers"] == []


def test_set_bad_json_exit(app: Any, census_file: Path) -> None:
    r = call(app, ["set", "idea-md", "blockers", "{not json}"], census_file)
    assert r.exit_code == 2


def test_set_type_enum_enforced(app: Any, census_file: Path) -> None:
    ok = call(app, ["set", "idea-md", "type", "battery"], census_file)
    assert ok.exit_code == 0
    assert read(census_file)["skills"]["idea-md"]["type"] == "battery"
    bad = call(
        app,
        [
            "set",
            "idea-md",
            "type",
            "nonsense",
        ],
        census_file,
    )
    assert bad.exit_code == 2


def test_set_project_phase(app: Any, census_file: Path) -> None:
    r = call(app, ["set", ".", "phase", "IP"], census_file)
    assert r.exit_code == 0
    data = read(census_file)
    assert data["projectPhase"] == "IP"
    assert any("phase transition" in h["event"] for h in data["history"])


def test_set_show_echoes(app: Any, census_file: Path) -> None:
    r = call(app, ["set", "steering", "type", "battery", "--show"], census_file)
    assert "skill: steering" in r.output


def test_log_project_and_skill(app: Any, census_file: Path) -> None:
    call(app, ["log", ".", "did a thing"], census_file)
    call(app, ["log", "reveal", "step done"], census_file)
    data = read(census_file)
    assert data["history"][-1]["event"] == "did a thing"
    assert data["skills"]["reveal"]["history"][-1]["event"] == "step done"


def test_add_and_remove_cycle(app: Any, census_file: Path, tmp_path: Path) -> None:
    skill = tmp_path / "demo"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        '---\nname: demo\ndescription: Demo.\nversion: "0.1.0"\n---\n', encoding="utf-8"
    )
    r = call(
        app,
        [
            "add-s",
            "demo",
            "-d",
            "author",
            "-p",
            str(skill),
            "-s",
            "Idea & Understanding",
            "-t",
            "normal",
            "-u",
            "testing",
        ],
        census_file,
    )
    assert r.exit_code == 0, r.output
    data = read(census_file)
    entry = data["skills"]["demo"]
    assert entry["deck"] == "author" and "demo" in data["decks"]["author"]["skills"]
    assert entry["fit"]["serves"] == ["Idea & Understanding"]
    assert entry["use_cases"] == ["testing"]
    dry = call(app, ["rm-skill", "demo", "--dry-run"], census_file)
    assert "would remove: demo" in dry.output
    assert "demo" in read(census_file)["skills"]
    call(app, ["remove-skill", "demo"], census_file)
    final = read(census_file)
    assert "demo" not in final["skills"]
    assert "demo" not in final["decks"]["author"]["skills"]


def test_add_serve_unknown_step(app: Any, census_file: Path, tmp_path: Path) -> None:
    skill = tmp_path / "demo2"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: demo2\ndescription: x\n---\n", encoding="utf-8")
    r = call(app, ["add-s", "demo2", "-d", "author", "-p", str(skill), "-s", "Nope"], census_file)
    assert r.exit_code == 2


def test_refresh_single_and_check(app: Any, census_file: Path, tmp_path: Path) -> None:
    skill = tmp_path / "rf"
    (skill / "references").mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        '---\nname: rf\ndescription: Before.\nversion: "1.0.0"\n---\n', encoding="utf-8"
    )
    data = read(census_file)
    data["skills"]["rf"] = {
        "version": "0.9.0",
        "type": "normal",
        "description": "stale",
        "use_cases": [],
        "deck": "author",
        "path": str(skill),
        "owned": False,
        "content": {"entry": "SKILL.md", "references": [], "assets": [], "examples": []},
        "fit": {"blockers": []},
        "history": [],
    }
    data["decks"]["author"]["skills"].append("rf")
    census_file.write_text(json.dumps(data), encoding="utf-8")
    chk = call(app, ["refresh", "rf", "--check"], census_file)
    assert chk.exit_code == 0 and "rf" in chk.output and "1.0.0" in chk.output
    apply = call(app, ["refresh", "rf"], census_file)
    assert "refreshed: rf v1.0.0" in apply.output
    updated = read(census_file)["skills"]["rf"]
    assert updated["description"] == "Before."
    allchk = call(app, ["refresh", "--all", "--check"], census_file)
    assert allchk.exit_code == 0


def test_refresh_requires_target(app: Any, census_file: Path) -> None:
    r = call(app, ["refresh"], census_file)
    assert r.exit_code == 2


def test_set_unknown_skill_exit1(app: Any, census_file: Path) -> None:
    r = call(app, ["set", "ghost", "type", "meta"], census_file)
    assert r.exit_code == 1


def test_add_skill_rejects_unknown_deck(app: Any, census_file: Path, tmp_path: Path) -> None:
    skill = tmp_path / "deckcase"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: deckcase\ndescription: x\n---\n", encoding="utf-8")
    r = call(app, ["add-s", "deckcase", "-d", "nosuch", "-p", str(skill)], census_file)
    assert r.exit_code == 2


def test_refresh_all_skips_unreadable(app: Any, census_file: Path) -> None:
    r = call(app, ["refresh", "--all"], census_file)
    assert r.exit_code == 0
    assert "skipped" in r.output or "refreshed" in r.output
