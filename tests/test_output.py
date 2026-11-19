"""Output framework tests: profiles, overrides, conflicts, renderers, emit."""

from pathlib import Path
from typing import Any

import pytest

from viber.models.domain import FormatKind, Profile
from viber.output.emit import EmitError, EmitTarget, emit, filter_payload
from viber.output.profiles import ProfileError, resolve_selection
from viber.output.render import render_text

SKILL_PAYLOAD: dict[str, Any] = {
    "skill": "steering",
    "version": "1.0.2",
    "type": "battery",
    "deck": "author",
    "path": "Groups/Viber/steering",
    "owned": False,
    "step": "Idea & Understanding",
    "description": "Two-tier docs",
    "use_cases": ["requirements into docs"],
    "fit": {
        "role": "taxonomy",
        "when": "idea exists",
        "serves": ["Idea & Understanding"],
        "after": [
            {"skill": "idea-md", "hint": "docs need the idea", "long_hint": "long text here"}
        ],
        "before": [],
        "with": [],
        "produces": [".steering/"],
        "consumes": ["IDEA.md"],
        "blockers": [],
    },
    "content": {
        "entry": "SKILL.md",
        "references": ["references/a.md"],
        "assets": [],
        "examples": [],
    },
    "history": [{"date": "2026-01-01", "event": "seeded"}],
}


def test_standard_selection_order() -> None:
    sel = resolve_selection("skill", Profile.STANDARD)
    assert sel == [
        "skill",
        "version",
        "type",
        "deck",
        "path",
        "owned",
        "recurring",
        "step",
        "description",
        "use_cases",
        "fit",
        "content",
    ]
    assert "history" not in sel and "notes" not in sel and "long_hints" not in sel


def test_minimal_and_full() -> None:
    assert "description" not in resolve_selection("skill", Profile.MINIMAL)
    full = resolve_selection("skill", Profile.FULL)
    assert "history" in full and "long_hints" in full and "notes" in full


def test_include_unknown_suggests() -> None:
    with pytest.raises(ProfileError, match="did you mean"):
        resolve_selection("skill", Profile.STANDARD, include=("descriptn",))


def test_dependency_conflict() -> None:
    with pytest.raises(ProfileError, match="requires 'fit'"):
        resolve_selection("skill", Profile.MINIMAL, include=("long_hints",))


def test_exclude_frees_conflict() -> None:
    sel = resolve_selection("skill", Profile.STANDARD, exclude=("fit", "long_hints"))
    assert "long_hints" not in sel


def test_txt_compact_no_boxes() -> None:
    sel = resolve_selection("skill", Profile.STANDARD, include=("long_hints",))
    text = render_text("skill", SKILL_PAYLOAD, sel)
    assert "|" not in text and "+" not in text
    assert "steering" in text and "docs need the idea" in text
    assert "long text here" in text  # --long adds it
    assert not text.endswith("\n\n")


def test_txt_no_long_hints() -> None:
    sel = resolve_selection("skill", Profile.STANDARD)  # long_hints off by default
    text = render_text("skill", SKILL_PAYLOAD, sel)
    assert "long text here" not in text


def test_json_filter_and_strip() -> None:
    sel = resolve_selection("skill", Profile.FULL, exclude=("long_hints",))
    data = filter_payload("skill", SKILL_PAYLOAD, sel)
    assert "history" in data and "content" in data
    from viber.output.emit import _strip_long_hints

    stripped = _strip_long_hints(data, sel)
    assert "long_hint" not in stripped["fit"]["after"][0]


def test_json_full_profile_covers_entry_keys() -> None:
    entry_keys = {
        "version",
        "type",
        "description",
        "use_cases",
        "deck",
        "path",
        "owned",
        "content",
        "fit",
        "history",
    }
    sel = resolve_selection("skill", Profile.FULL)
    data = filter_payload("skill", SKILL_PAYLOAD, sel)
    assert entry_keys <= set(data)


def test_emit_stdout_and_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    sel = resolve_selection("status", Profile.STANDARD)
    payload = {
        "phase": "DR",
        "step": "Idea & Understanding",
        "total": 42,
        "blocked": 1,
        "unclassified": 6,
    }
    emit("status", payload, sel, EmitTarget())
    assert "DR" in capsys.readouterr().out
    out = tmp_path / "s.txt"
    emit("status", payload, sel, EmitTarget(out=out))
    assert out.read_text(encoding="utf-8").startswith("phase: DR")
    assert "flushed" in capsys.readouterr().err


def test_emit_refuses_overwrite_and_force(tmp_path: Path) -> None:
    out = tmp_path / "s.txt"
    out.write_text("old", encoding="utf-8")
    sel = resolve_selection("status", Profile.STANDARD)
    payload = {"phase": "DR", "step": "x", "total": 1, "blocked": 0, "unclassified": 0}
    with pytest.raises(EmitError, match="refusing to overwrite"):
        emit("status", payload, sel, EmitTarget(out=out))
    emit("status", payload, sel, EmitTarget(out=out, force=True))
    assert "phase: DR" in out.read_text(encoding="utf-8")


def test_emit_json_ascii_safe(tmp_path: Path) -> None:
    out = tmp_path / "d.json"
    sel = resolve_selection("skill", Profile.STANDARD)
    payload = dict(SKILL_PAYLOAD, description="naïve → arrow ✓")
    emit("skill", payload, sel, EmitTarget(fmt=FormatKind.JSON, out=out))
    raw = out.read_bytes()
    raw.decode("ascii")  # would raise if non-ascii leaked
    assert "\\u2192" in raw.decode("ascii")


def test_registry_and_renderers_stay_in_lockstep() -> None:
    """A REGISTRY command without a renderer surfaces as a KeyError exit 1 —
    this guard makes that impossible to ship."""
    from viber.output.fields import REGISTRY
    from viber.output.render import RENDERERS

    assert set(REGISTRY) <= set(RENDERERS)
