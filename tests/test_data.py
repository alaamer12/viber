"""Data-layer tests: store round-trip, validation, frontmatter, telemetry."""

import json
from pathlib import Path

import pytest

from viber.data.frontmatter import list_content, parse_frontmatter
from viber.data.store import CensusError, dump_census, load_census, save_census
from viber.data.telemetry import TelemetryDB


def test_roundtrip_preserves_mini(mini: dict, census_file: Path) -> None:
    census = load_census(census_file)
    assert json.loads(dump_census(census)) == mini


def test_missing_required_keys_rejected(tmp_path: Path) -> None:
    p = tmp_path / "viber.json"
    p.write_text('{"name": "broken"}', encoding="utf-8")
    with pytest.raises(CensusError, match="missing required keys: decks, lifecycle, skills"):
        load_census(p)


def test_missing_file_rejected(tmp_path: Path) -> None:
    with pytest.raises(CensusError, match="census not found"):
        load_census(tmp_path / "nope.json")


def test_legacy_string_relations_upgrade(mini: dict, tmp_path: Path) -> None:
    mini["skills"]["reveal"]["fit"]["after"] = ["idea-md"]  # old plain-string form
    p = tmp_path / "viber.json"
    p.write_text(json.dumps(mini), encoding="utf-8")
    census = load_census(p)
    rel = census.skills["reveal"].fit.after[0]
    assert rel.skill == "idea-md" and rel.hint == ""
    dumped = json.loads(dump_census(census))
    assert dumped["skills"]["reveal"]["fit"]["after"] == [
        {"skill": "idea-md", "hint": "", "long_hint": ""}
    ]


def test_save_is_atomic(census_file: Path) -> None:
    census = load_census(census_file)
    save_census(census_file, census)
    assert not census_file.with_suffix(".tmp").exists()
    assert census_file.is_file()
    # content still valid json and equal
    assert json.loads(census_file.read_text(encoding="utf-8")) == json.loads(dump_census(census))


def test_extras_survive_roundtrip(mini: dict, tmp_path: Path) -> None:
    mini["skills"]["idea-md"]["future_key"] = {"a": 1}
    mini["some_top_level_extra"] = [1, 2]
    p = tmp_path / "viber.json"
    p.write_text(json.dumps(mini), encoding="utf-8")
    census = load_census(p)
    out = json.loads(dump_census(census))
    assert out["skills"]["idea-md"]["future_key"] == {"a": 1}
    assert out["some_top_level_extra"] == [1, 2]


def test_frontmatter_shapes(tmp_path: Path) -> None:
    md = tmp_path / "SKILL.md"
    md.write_text(
        '---\nname: x\ndescription: >-\n  folded one\n  folded two\nversion: "1.2.3"\n---\nbody\n',
        encoding="utf-8",
    )
    fm = parse_frontmatter(md)
    assert fm["name"] == "x"
    assert fm["description"] == "folded one folded two"
    assert fm["version"] == "1.2.3"
    md2 = tmp_path / "plain.md"
    md2.write_text("no frontmatter here", encoding="utf-8")
    assert parse_frontmatter(md2) == {}


def test_list_content_scans(tmp_path: Path) -> None:
    skill = tmp_path / "s"
    (skill / "references").mkdir(parents=True)
    (skill / "assets").mkdir()
    (skill / "references" / "a.md").write_text("x", encoding="utf-8")
    (skill / "assets" / "b.mmd").write_text("x", encoding="utf-8")
    c = list_content(skill)
    assert c["entry"] == "SKILL.md"
    assert c["references"] == ["references/a.md"]
    assert c["assets"] == ["assets/b.mmd"]


def test_telemetry_lifecycle(db: TelemetryDB) -> None:
    assert not db.exists()
    db.record_invocation("idea-md", "2026-11-16T00:00:00Z", "Idea & Understanding", "DR")
    db.record_invocation("reveal", "2026-11-16T01:00:00Z", "Idea & Understanding", "DR")
    assert db.close_open("idea-md", "ok", "done") is not None
    assert db.close_open("unknown", "ok", None) is None
    stats = db.skill_stats("idea-md")
    assert stats["count"] == 1 and stats["ok"] == 1
    assert db.successor("idea-md") == ("reveal", 1)
    assert ("idea-md -> reveal", 1) in db.pairs()
    assert db.all_stats()[0]["skill"] in ("idea-md", "reveal")


def test_frontmatter_bom_tolerated(tmp_path: Path) -> None:
    md = tmp_path / "SKILL.md"
    md.write_bytes("\ufeff---\nname: x\ndescription: y\nversion: '1.0.0'\n---\n".encode("utf-8"))
    assert parse_frontmatter(md)["version"] == "1.0.0"
