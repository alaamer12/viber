"""Core algebra unit tests: roster topology, blockers, reasons, pool gap."""

import json
from pathlib import Path
from typing import Any

from viber.core import resolution
from viber.data.store import load_census


def census_from(tmp_path: Path, mutate: Any) -> Any:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from conftest import MINI
    data = json.loads(json.dumps(MINI))
    mutate(data)
    p = tmp_path / "viber.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return load_census(p)


def test_roster_respects_after_edges(tmp_path: Path) -> None:
    def m(d: dict) -> None:
        # reverse insertion: reveal listed before idea-md, edges must fix order
        skills = d["skills"]
        ordered = {"idea-md": skills["idea-md"], "reveal": skills["reveal"]}
        for k in ("idea-md", "reveal"):
            del skills[k]
        d["skills"] = {"reveal": ordered["reveal"], **skills, "idea-md": ordered["idea-md"]}
    census = census_from(tmp_path, m)
    roster = resolution.step_roster(census, "Idea & Understanding")
    assert roster.index("idea-md") < roster.index("reveal")
    assert roster.index("idea-md") < roster.index("steering")


def test_cycle_falls_back_to_insertion(tmp_path: Path) -> None:
    def m(d: dict) -> None:
        d["skills"]["idea-md"]["fit"]["after"] = [
            {"skill": "reveal", "hint": "cycle", "long_hint": ""}]
    census = census_from(tmp_path, m)
    roster = resolution.step_roster(census, "Idea & Understanding")
    assert sorted(roster) == sorted(resolution.serving_skills(census, "Idea & Understanding"))


def test_blocked_skill_surfaces_in_blocked(tmp_path: Path) -> None:
    def m(d: dict) -> None:
        d["skills"]["idea-md"]["fit"]["blockers"] = ["awaiting concept"]
    census = census_from(tmp_path, m)
    out = resolution.next_candidates(census, None)
    assert out["blocked"][0]["skill"] == "idea-md"
    assert out["candidates"][0]["skill"] == "reveal"
    assert "waits on idea-md" in out["candidates"][0]["reasons"][0]


def test_no_predecessors_reason(tmp_path: Path) -> None:
    census = census_from(tmp_path, lambda d: None)
    out = resolution.next_candidates(census, None)
    assert "no recorded predecessors" in out["candidates"][0]["reasons"][0]


def test_uninstalled_candidates(tmp_path: Path) -> None:
    def m(d: dict) -> None:
        del d["skills"]["webthing"]
        d["decks"]["project"]["skills"] = []
    census = census_from(tmp_path, m)
    assert resolution.uninstalled_candidates(census, "Idea & Understanding") == ["webthing"]
