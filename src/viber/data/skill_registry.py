from dataclasses import dataclass
from pathlib import Path

from viber.data.frontmatter import parse_frontmatter, when_to_use
from viber.data.store import CensusError


@dataclass(frozen=True)
class SkillMetadata:
    name: str
    description: str
    when_to_use: str
    source: Path
    viber: str | None
    version: str | None


def scan_skills(roots: list[Path]) -> list[SkillMetadata]:
    found: dict[Path, SkillMetadata] = {}
    for root in roots:
        try:
            if not root.is_dir():
                raise CensusError(f"invalid skills root: {root} (expected a directory)")
            candidates = [root] if (root / "SKILL.md").is_file() else sorted(root.iterdir())
            for directory in candidates:
                source = directory.resolve()
                skill_md = source / "SKILL.md"
                if source in found or not skill_md.is_file():
                    continue
                metadata = parse_frontmatter(skill_md)
                name = metadata.get("name")
                description = metadata.get("description")
                if not name or not name.strip() or not description or not description.strip():
                    raise CensusError(f"{skill_md}: nonempty name and description are required")
                found[source] = SkillMetadata(
                    name=name.strip(), description=description,
                    when_to_use=when_to_use(metadata, skill_md), source=source,
                    viber=metadata.get("viber"), version=metadata.get("version"),
                )
        except OSError as exc:
            raise CensusError(f"cannot scan skills root {root}: {exc}") from exc
    return sorted(
        found.values(), key=lambda skill: (skill.name.casefold(), skill.source.as_posix())
    )


def conflicting_sources(skills: list[SkillMetadata]) -> dict[str, list[str]]:
    sources: dict[str, list[str]] = {}
    for skill in skills:
        sources.setdefault(skill.name, []).append(skill.source.as_posix())
    return {name: paths for name, paths in sources.items() if len(paths) > 1}
