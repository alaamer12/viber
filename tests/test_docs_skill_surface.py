"""Skill-name tripwire: prose we hand an agent — docs, README, shipped SKILL.md
files, reference tables, and Mermaid diagrams — must name Skills that exist on
the seed's live surface. A renamed or absorbed Skill leaves its old name behind;
``tools/audit_skill_refs.py`` derives the retired-name map from the seed and this
test pins the repo clean against it. The detector itself is proven to have teeth
(a planted stale reference is caught) so a green run is not a vacuous one."""

import importlib.util
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location("audit_skill_refs", ROOT / "tools" / "audit_skill_refs.py")
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

RETIRED = audit.derive_retired(audit.load_skills(ROOT / "viber.json"))


def test_retired_map_tracks_known_renames() -> None:
    assert RETIRED.get("styleup") == "styling"
    assert RETIRED.get("style-up") == "styling"
    assert RETIRED.get("type-up") == "typing"
    assert RETIRED.get("tier-up") == "typing"
    assert set(RETIRED.values()) <= set(audit.load_skills(ROOT / "viber.json"))


def test_no_stale_skill_references() -> None:
    findings = audit.scan(ROOT, RETIRED)
    assert findings == [], "\n".join(f"{f}:{n}: '{r}' -> '{c}'" for f, n, r, c in findings)


def test_detector_catches_planted_stale_reference() -> None:
    tmp = Path(tempfile.mkdtemp())
    try:
        shutil.copy(ROOT / "viber.json", tmp / "viber.json")
        (tmp / "docs" / "diagrams").mkdir(parents=True)
        (tmp / "docs" / "diagrams" / "x.mmd").write_text('STU["styleup"]\nuse type-up here\n', encoding="utf-8")
        (tmp / "skills" / "styling").mkdir(parents=True)
        (tmp / "skills" / "styling" / "SKILL.md").write_text("Absorbs former styleup skill.\n", encoding="utf-8")
        findings = audit.scan(tmp, RETIRED)
        assert ("docs/diagrams/x.mmd", 1, "styleup", "styling") in findings
        assert any(r == "type-up" for _, _, r, _ in findings)
        assert not any(f.startswith("skills/styling") for f, _, _, _ in findings)
        audit.fix(tmp, RETIRED)
        assert audit.scan(tmp, RETIRED) == []
    finally:
        shutil.rmtree(tmp)