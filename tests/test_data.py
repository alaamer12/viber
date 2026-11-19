"""Data-layer tests: store round-trip, validation, frontmatter, telemetry."""

import json
from pathlib import Path
from typing import Any

import pytest

from viber.data import frontmatter
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


@pytest.mark.parametrize(
    ("marker", "expected"),
    [
        (">", "first second\n"),
        (">-", "first second"),
        (">+", "first second\n\n"),
        ("|", "first\nsecond\n"),
        ("|-", "first\nsecond"),
        ("|+", "first\nsecond\n\n"),
    ],
)
def test_frontmatter_block_scalars(tmp_path: Path, marker: str, expected: str) -> None:
    md = tmp_path / "SKILL.md"
    md.write_text(f"---\ndescription: {marker}\n  first\n  second\n\n---\n", encoding="utf-8")
    assert parse_frontmatter(md)["description"] == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("'It''s useful'", "It's useful"),
        ('"Say \\"hello\\""', 'Say "hello"'),
        ('"Use --- between: sections # literally"', "Use --- between: sections # literally"),
        ("Use for checks # author note", "Use for checks"),
        ("|-\n  ---\n  # literal content", "---\n# literal content"),
    ],
)
def test_frontmatter_quotes_separators_and_comments(
    tmp_path: Path, value: str, expected: str
) -> None:
    md = tmp_path / "SKILL.md"
    md.write_text(f"---\ndescription: {value}\n---\nbody: [not YAML\n", encoding="utf-8")
    assert parse_frontmatter(md)["description"] == expected


def test_frontmatter_preserves_unconsumed_metadata(tmp_path: Path) -> None:
    md = tmp_path / "SKILL.md"
    md.write_text(
        "---\nname: sample\nhooks:\n  Stop:\n    - hooks:\n"
        "        - command: check\n          timeout: 10\n"
        "metadata: {tags: [python, yaml], enabled: true}\nuser-invocable: false\n---\n",
        encoding="utf-8",
    )
    assert parse_frontmatter(md) == {
        "name": "sample",
        "hooks": {"Stop": [{"hooks": [{"command": "check", "timeout": 10}]}]},
        "metadata": {"tags": ["python", "yaml"], "enabled": True},
        "user-invocable": False,
    }


@pytest.mark.parametrize("text", ["", "plain text", "---not a fence\nname: x\n---\n"])
def test_frontmatter_missing_exact_opening_fence(tmp_path: Path, text: str) -> None:
    md = tmp_path / "SKILL.md"
    md.write_text(text, encoding="utf-8")
    assert parse_frontmatter(md) == {}


@pytest.mark.parametrize("ending", ["", "---not a fence\n", "--- \n", "  ---\n"])
def test_frontmatter_requires_exact_closing_fence(tmp_path: Path, ending: str) -> None:
    md = tmp_path / "SKILL.md"
    md.write_text(f"---\nname: x\n{ending}", encoding="utf-8")
    with pytest.raises(CensusError, match="unterminated") as exc:
        parse_frontmatter(md)
    assert str(md) in str(exc.value)


@pytest.mark.parametrize(
    "content",
    [
        "description: [broken",
        'description: "unterminated',
        "metadata: {nested: [broken}",
        "description: !!python/object/apply:builtins.str [unsafe]",
        "description: !unknown value",
        "version: !!int invalid",
    ],
)
def test_frontmatter_invalid_yaml_is_contextual(tmp_path: Path, content: str) -> None:
    md = tmp_path / "SKILL.md"
    md.write_text(f"---\n{content}\n---\n", encoding="utf-8")
    with pytest.raises(CensusError, match="YAML") as exc:
        parse_frontmatter(md)
    assert str(md) in str(exc.value)


@pytest.mark.parametrize("content", ["[a, b]", "[]", "plain scalar", "false", "1", "null", ""])
def test_frontmatter_requires_mapping(tmp_path: Path, content: str) -> None:
    md = tmp_path / "SKILL.md"
    md.write_text(f"---\n{content}\n---\n", encoding="utf-8")
    with pytest.raises(CensusError, match="mapping") as exc:
        parse_frontmatter(md)
    assert str(md) in str(exc.value)


@pytest.mark.parametrize("field", ["name", "description", "when_to_use", "viber"])
@pytest.mark.parametrize("value", ["true", "42", "[text]", "{nested: text}"])
def test_frontmatter_rejects_nonstring_consumed_fields(
    tmp_path: Path, field: str, value: str
) -> None:
    md = tmp_path / "SKILL.md"
    md.write_text(f"---\n{field}: {value}\n---\n", encoding="utf-8")
    with pytest.raises(CensusError, match=field) as exc:
        parse_frontmatter(md)
    assert str(md) in str(exc.value)


def test_frontmatter_allows_null_text_fields(tmp_path: Path) -> None:
    md = tmp_path / "SKILL.md"
    md.write_text(
        "---\nname: null\ndescription: null\nwhen_to_use: null\nviber: null\n---\n",
        encoding="utf-8",
    )
    assert parse_frontmatter(md) == dict.fromkeys(["name", "description", "when_to_use", "viber"])


@pytest.mark.parametrize("tag", ["part", "separated", "excluded"])
def test_frontmatter_accepts_viber_tags(tmp_path: Path, tag: str) -> None:
    md = tmp_path / "SKILL.md"
    md.write_text(f"---\nviber: {tag}\n---\n", encoding="utf-8")
    assert parse_frontmatter(md)["viber"] == tag


@pytest.mark.parametrize("tag", ["unknown", "PART", "''"])
def test_frontmatter_rejects_invalid_viber_tags(tmp_path: Path, tag: str) -> None:
    md = tmp_path / "SKILL.md"
    md.write_text(f"---\nviber: {tag}\n---\n", encoding="utf-8")
    with pytest.raises(CensusError, match="viber") as exc:
        parse_frontmatter(md)
    assert str(md) in str(exc.value)


@pytest.mark.parametrize(("value", "expected"), [('"1.2.3"', "1.2.3"), ("2", "2"), ("1.5", "1.5")])
def test_frontmatter_version_scalar_conversion(tmp_path: Path, value: str, expected: str) -> None:
    md = tmp_path / "SKILL.md"
    md.write_text(f"---\nversion: {value}\n---\n", encoding="utf-8")
    assert parse_frontmatter(md)["version"] == expected


@pytest.mark.parametrize("value", ["true", "false", "[1, 2]", "{major: 1}", "null", "2026-11-19"])
def test_frontmatter_rejects_invalid_versions(tmp_path: Path, value: str) -> None:
    md = tmp_path / "SKILL.md"
    md.write_text(f"---\nversion: {value}\n---\n", encoding="utf-8")
    with pytest.raises(CensusError, match="version") as exc:
        parse_frontmatter(md)
    assert str(md) in str(exc.value)


@pytest.mark.parametrize("failure", ["missing", "directory", "invalid-utf8"])
def test_frontmatter_read_errors_are_contextual(tmp_path: Path, failure: str) -> None:
    md = tmp_path / "SKILL.md"
    if failure == "directory":
        md.mkdir()
    elif failure == "invalid-utf8":
        md.write_bytes(b"---\nname: \xff\n---\n")
    with pytest.raises(CensusError) as exc:
        parse_frontmatter(md)
    assert str(md) in str(exc.value)


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        ({"when_to_use": "  Explicit trigger.\n", "description": "Use for other work."},
         "Explicit trigger."),
        ({"when_to_use": "Standalone trigger."}, "Standalone trigger."),
        ({"when_to_use": None, "description": "Summary. Use when checking YAML. Extra detail."},
         "Use when checking YAML."),
        ({"when_to_use": "", "description": "Summary. Use for authoring tests. Extra detail."},
         "Use for authoring tests."),
        ({"when_to_use": " \n\t", "description": "Summary. Use before releasing. Extra detail."},
         "Use before releasing."),
        ({"description": "Summary. Invoke when reviewing. Extra detail."},
         "Invoke when reviewing."),
        ({"description": "Summary; use when checking YAML! Extra detail."},
         "use when checking YAML!"),
        ({"description": "Summary. Use\nwhen checking YAML without punctuation"},
         "Use\nwhen checking YAML without punctuation"),
        ({"description": "  First sentence. Second sentence.  "}, "First sentence."),
        ({"description": "First question? Second sentence."}, "First question?"),
        ({"description": "  Description without punctuation  "}, "Description without punctuation"),
        ({"description": "Reuse when needed. Second sentence."}, "Reuse when needed."),
    ],
)
def test_when_to_use_fallbacks(
    tmp_path: Path, metadata: dict[str, Any], expected: str
) -> None:
    assert frontmatter.when_to_use(metadata, tmp_path / "SKILL.md") == expected


@pytest.mark.parametrize(
    "metadata",
    [{}, {"description": None}, {"description": ""},
     {"when_to_use": " \n", "description": " \t"}],
)
def test_when_to_use_requires_real_text(tmp_path: Path, metadata: dict[str, Any]) -> None:
    md = tmp_path / "SKILL.md"
    with pytest.raises(CensusError, match="when_to_use") as exc:
        frontmatter.when_to_use(metadata, md)
    assert str(md) in str(exc.value)


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


@pytest.mark.parametrize(
    ("path", "value", "needle"),
    [
        (["projectPhase"], "ZZ", "projectPhase"),
        (["skills", "idea-md", "type"], "totally-bogus", "type"),
        (["lifecycle", 0, "phase"], "QQ", "phase"),
        (["decks", "author", "mutability"], "sometimes", "mutability"),
    ],
)
def test_closed_sets_hard_fail_on_load(
    tmp_path: Path, mini: dict, path: list, value: str, needle: str
) -> None:
    """No bogus enum ever flows inward: load is the boundary and it refuses."""
    node = mini
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    p = tmp_path / "viber.json"
    p.write_text(json.dumps(mini), encoding="utf-8")
    with pytest.raises(CensusError) as exc:
        load_census(p)
    assert needle in str(exc.value)
