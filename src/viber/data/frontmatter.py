"""Safe SKILL.md frontmatter parsing, trigger fallback, and content-tree scanning."""

import re
from pathlib import Path
from typing import Any

import yaml

from viber.data.store import CensusError

_TRIGGER = re.compile(r"\b(?:use\s+(?:when|for|before)|invoke\s+when)\b", re.IGNORECASE)
_SCAN_SKIP = (".git", "__pycache__", "scripts")


def _string_field(metadata: dict[str, Any], field: str, source: Path) -> str | None:
    value = metadata.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise CensusError(f"invalid frontmatter in {source}: {field} must be a string or null")
    return value


def parse_frontmatter(skill_md: Path) -> dict[str, Any]:
    """Read a fenced YAML mapping without flattening unconsumed metadata."""
    try:
        text = skill_md.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise CensusError(f"cannot read frontmatter from {skill_md}: {exc}") from exc
    lines = text.split("\n")
    if lines[0] != "---":
        return {}
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise CensusError(f"unterminated frontmatter in {skill_md}: missing closing ---") from exc
    try:
        result = yaml.safe_load("\n".join(lines[1:end]) + "\n")
    except (yaml.YAMLError, ValueError, TypeError) as exc:
        raise CensusError(f"invalid YAML frontmatter in {skill_md}: {exc}") from exc
    if not isinstance(result, dict):
        raise CensusError(f"invalid frontmatter in {skill_md}: expected a YAML mapping")
    if any(not isinstance(key, str) for key in result):
        raise CensusError(f"invalid frontmatter in {skill_md}: mapping keys must be strings")
    for field in ("name", "description", "when_to_use", "viber"):
        _string_field(result, field, skill_md)
    if result.get("viber") is not None and result["viber"] not in (
        "part", "separated", "excluded"
    ):
        raise CensusError(
            f"invalid frontmatter in {skill_md}: viber must be part, separated, or excluded"
        )
    if "version" in result:
        version = result["version"]
        if isinstance(version, bool) or not isinstance(version, (str, int, float)):
            raise CensusError(
                f"invalid frontmatter in {skill_md}: version must be a string or number"
            )
        result["version"] = str(version)
    return result


def when_to_use(metadata: dict[str, Any], source: Path) -> str:
    """Prefer explicit trigger text, then a description trigger, then its first sentence."""
    explicit = _string_field(metadata, "when_to_use", source)
    if explicit is not None and explicit.strip():
        return explicit.strip()
    description = _string_field(metadata, "description", source)
    if description is None or not description.strip():
        raise CensusError(
            f"invalid frontmatter in {source}: when_to_use or description must contain text"
        )
    description = description.strip()
    trigger = _TRIGGER.search(description)
    text = description[trigger.start():] if trigger else description
    return re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0].strip()


def list_content(skill_dir: Path) -> dict[str, Any]:
    refs: list[str] = []
    assets: list[str] = []
    examples: list[str] = []
    targets: list[tuple[str, list[str]]] = [
        ("references", refs),
        ("assets", assets),
        ("examples", examples),
    ]
    for sub, bucket in targets:
        d = skill_dir / sub
        if d.is_dir():
            bucket.extend(
                str(f.relative_to(skill_dir)).replace("\\", "/")
                for f in sorted(d.rglob("*"))
                if f.is_file()
            )
    for sub_dir in sorted(skill_dir.iterdir()):
        if sub_dir.is_dir() and sub_dir.name not in (
            "references",
            "assets",
            "examples",
            *_SCAN_SKIP,
        ):
            for sub, bucket in targets:
                d = sub_dir / sub
                if d.is_dir():
                    bucket.extend(
                        str(f.relative_to(skill_dir)).replace("\\", "/")
                        for f in sorted(d.rglob("*"))
                        if f.is_file()
                    )
    return {"entry": "SKILL.md", "references": refs, "assets": assets, "examples": examples}
