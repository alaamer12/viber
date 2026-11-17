"""Shared fixtures: a hand-authored mini census and temp telemetry db."""

import json
import os
from pathlib import Path
from typing import Any

import pytest

from viber.data.telemetry import TelemetryDB


@pytest.fixture(autouse=True)
def hermetic_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """No ambient VIBER_* var or real user config may leak into any test."""
    for var in [k for k in os.environ if k.startswith("VIBER_")]:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("VIBER_CONFIG", str(tmp_path / "absent-config.json"))
    monkeypatch.setenv("VIBER_CONFIG_HOME", str(tmp_path / "absent-config-home"))

MINI: dict[str, Any] = {
    "name": "viber",
    "version": "0.1.0",
    "created": "2026-11-16",
    "createdBy": "test",
    "projectPhase": "DR",
    "decks": {
        "author": {
            "name": "Amr's Deck",
            "description": "closed battery",
            "mutability": "closed",
            "registry": "REG",
            "remote": None,
            "skills": ["idea-md", "reveal", "steering", "vinit"],
        },
        "project": {
            "name": "Alaamer's Deck",
            "description": "user installs",
            "mutability": "open",
            "registry": ".viber/registry.md",
            "remote": None,
            "skills": ["webthing"],
        },
    },
    "lifecycle": [
        {
            "step": "Idea & Understanding",
            "phase": "DR",
            "goal": "capture the idea",
            "needs": ["write the concept down"],
            "possible_skills": ["idea-md", "reveal", "webthing"],
            "commands": ["vinit"],
        },
        {
            "step": "Implementation",
            "phase": "IP",
            "goal": "build it",
            "needs": ["write code"],
            "possible_skills": ["steering"],
            "commands": [],
        },
        {
            "step": "Shared",
            "phase": None,
            "goal": "any-time tools",
            "needs": ["pressure-test"],
            "possible_skills": [],
            "commands": [],
        },
    ],
    "skills": {
        "idea-md": {
            "version": "1.0.0",
            "type": "normal",
            "description": "Idea doc from raw concept",
            "use_cases": ["raw spoken concept"],
            "deck": "author",
            "path": None,
            "owned": False,
            "content": {
                "entry": "SKILL.md",
                "references": ["references/x.md"],
                "assets": [],
                "examples": [],
            },
            "fit": {
                "role": "first doc",
                "when": "no IDEA.md yet",
                "serves": ["Idea & Understanding"],
                "after": [],
                "before": [
                    {
                        "skill": "reveal",
                        "hint": "landscape sharpens the doc",
                        "long_hint": "reveal feeds steering",
                    }
                ],
                "with": [],
                "produces": ["IDEA.md"],
                "consumes": [],
                "blockers": [],
            },
            "history": [],
        },
        "reveal": {
            "version": "1.0.0",
            "type": "normal",
            "description": "Landscape check",
            "use_cases": ["has this been built"],
            "deck": "author",
            "path": None,
            "owned": False,
            "content": {"entry": "SKILL.md", "references": [], "assets": [], "examples": []},
            "fit": {
                "role": "awareness",
                "when": "idea written",
                "serves": ["Idea & Understanding"],
                "after": [
                    {
                        "skill": "idea-md",
                        "hint": "landscape needs the written idea",
                        "long_hint": "search axes come from IDEA.md",
                    }
                ],
                "before": [],
                "with": [],
                "produces": ["report"],
                "consumes": ["IDEA.md"],
                "blockers": [],
            },
            "history": [],
        },
        "steering": {
            "version": "1.0.0",
            "type": "battery",
            "description": "Two-tier docs",
            "use_cases": ["requirements into docs"],
            "deck": "author",
            "path": None,
            "owned": False,
            "content": {"entry": "SKILL.md", "references": [], "assets": [], "examples": []},
            "fit": {
                "role": "taxonomy",
                "when": "idea exists",
                "serves": ["Idea & Understanding", "Implementation"],
                "after": [
                    {
                        "skill": "idea-md",
                        "hint": "docs need the idea",
                        "long_hint": "long text here",
                    }
                ],
                "before": [],
                "with": [],
                "produces": [".steering/"],
                "consumes": ["IDEA.md"],
                "blockers": [],
            },
            "history": [],
        },
        "webthing": {
            "version": "2.0.0",
            "type": "otherwise",
            "description": "Foreign web skill",
            "use_cases": ["whatever"],
            "deck": "project",
            "path": None,
            "owned": False,
            "content": {"entry": "SKILL.md", "references": [], "assets": [], "examples": []},
            "fit": {
                "role": "",
                "when": "",
                "serves": [],
                "after": [],
                "before": [],
                "with": [],
                "produces": [],
                "consumes": [],
                "blockers": ["awaiting user decision"],
            },
            "history": [],
        },
        "vinit": {
            "version": "1.0.0",
            "type": "meta",
            "description": "Entry command",
            "use_cases": ["first run"],
            "deck": "author",
            "path": None,
            "owned": True,
            "content": {"entry": "SKILL.md", "references": [], "assets": [], "examples": []},
            "fit": {
                "role": "bootstrap",
                "when": "no registry",
                "serves": [],
                "after": [],
                "before": [],
                "with": [],
                "produces": ["registry"],
                "consumes": [],
                "blockers": [],
            },
            "history": [],
        },
    },
    "unclassified": [],
    "history": [],
}


@pytest.fixture()
def mini() -> dict[str, Any]:
    return json.loads(json.dumps(MINI))


@pytest.fixture()
def census_file(tmp_path: Path, mini: dict[str, Any]) -> Path:
    p = tmp_path / "viber.json"
    p.write_text(json.dumps(mini, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


@pytest.fixture()
def db(tmp_path: Path) -> TelemetryDB:
    return TelemetryDB(tmp_path / "telemetry.db")


SEED_PATH = Path(__file__).parents[1] / "viber.json"
