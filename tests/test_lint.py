"""Lint scenarios: clean census, dangling relation, version drift, null-path warn,
cross-deck conflict question and its resolution through `set deck`."""

import json
from pathlib import Path
from typing import Any

import pytest
from conftest import MINI
from typer.testing import CliRunner

from viber.app import build_app

runner = CliRunner()


@pytest.fixture(scope="module")
def app() -> Any:
    return build_app()


def lint_json(app: Any, census_file: Path, extra: list[str] | None = None) -> list[dict]:
    r = runner.invoke(app, ["lint", "-f", "json"] + (extra or []) + ["-C", str(census_file)])
    payload = json.loads(r.output)
    return payload["findings"] if isinstance(payload, dict) else payload


def make_census(tmp_path: Path, mutate) -> Path:
    data = json.loads(json.dumps(MINI))
    mutate(data)
    p = tmp_path / "viber.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_clean_census_has_no_errors(tmp_path: Path, app: Any) -> None:
    p = make_census(tmp_path, lambda d: None)
    findings = lint_json(app, p)
    assert not [f for f in findings if f["severity"] == "error"]


def test_dangling_relation_error(tmp_path: Path, app: Any) -> None:
    def m(d: dict) -> None:
        d["skills"]["reveal"]["fit"]["after"].append(
            {"skill": "ghost", "hint": "", "long_hint": ""}
        )

    p = make_census(tmp_path, m)
    findings = lint_json(app, p)
    assert any(f["check"] == "dangling-relation" and f["subject"] == "reveal" for f in findings)


def test_unknown_serves_error(tmp_path: Path, app: Any) -> None:
    def m(d: dict) -> None:
        d["skills"]["idea-md"]["fit"]["serves"].append("Made-Up Step")

    p = make_census(tmp_path, m)
    assert any(f["check"] == "dangling-serves" for f in lint_json(app, p))


def test_null_path_without_blockers_warns(tmp_path: Path, app: Any) -> None:
    def m(d: dict) -> None:
        d["skills"]["webthing"]["fit"]["blockers"] = []

    p = make_census(tmp_path, m)
    assert any(f["check"] == "null-path" and f["severity"] == "warning" for f in lint_json(app, p))


def test_null_path_with_blockers_still_warns(tmp_path: Path, app: Any) -> None:
    p = make_census(tmp_path, lambda d: None)
    findings = lint_json(app, p)
    assert any(
        f["check"] == "null-path" and f["subject"] == "webthing"
        and f["severity"] == "warning" and "cannot" in f["detail"]
        for f in findings
    )
    result = runner.invoke(app, ["lint", "-C", str(p), "-nr"])
    assert result.exit_code == 0
    assert "webthing" in result.output


def test_version_drift_warning(tmp_path: Path, app: Any) -> None:
    skill = tmp_path / "disk"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        '---\nname: disk\ndescription: x\nversion: "2.0.0"\n---\n', encoding="utf-8"
    )

    def m(d: dict) -> None:
        d["skills"]["idea-md"]["path"] = str(skill)

    p = make_census(tmp_path, m)
    findings = lint_json(app, p)
    drift = [f for f in findings if f["check"] == "version-drift"]
    assert drift and "1.0.0" in drift[0]["detail"] and "2.0.0" in drift[0]["detail"]


def test_cross_deck_conflict_question_and_resolution(tmp_path: Path, app: Any) -> None:
    def m(d: dict) -> None:
        d["decks"]["project"]["skills"].append("steering")

    p = make_census(tmp_path, m)
    findings = lint_json(app, p)
    conflict = [f for f in findings if f["check"] == "deck-conflict" and f["subject"] == "steering"]
    assert conflict and conflict[0]["severity"] == "question" and conflict[0]["ask_user"]
    assert "ASK USER" in runner.invoke(app, ["lint", "--ask-only", "-C", str(p)]).output
    resolved = runner.invoke(app, ["set", "steering", "deck", "author", "-C", str(p)])
    assert resolved.exit_code == 0
    assert not [f for f in lint_json(app, p) if f["check"] == "deck-conflict"]


def test_lint_exit_codes(tmp_path: Path, app: Any) -> None:
    p = make_census(
        tmp_path,
        lambda d: d["skills"]["reveal"]["fit"]["before"].append(
            {"skill": "ghost", "hint": "", "long_hint": ""}
        ),
    )
    r = runner.invoke(app, ["lint", "-C", str(p)])
    assert r.exit_code == 1
    only = runner.invoke(app, ["lint", "--only", "error", "-f", "json", "-C", str(p)])
    assert all(f["severity"] == "error" for f in json.loads(only.output)["findings"])
