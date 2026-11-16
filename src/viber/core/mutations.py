"""Census mutations — validated writes; the census is only ever touched through here."""

from datetime import UTC, datetime
from typing import Any

from viber.core.census_ops import entry_of, rels
from viber.data.frontmatter import list_content, parse_frontmatter
from viber.data.store import CensusUsageError, save_census
from viber.models.domain import SetField, SkillType
from viber.models.schema import Census, Content, SkillEntry


def today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def skill_dir_on_disk(census: Census, census_path: Any, entry: SkillEntry) -> Any:
    from pathlib import Path

    path_str = entry.path
    if not path_str:
        return None
    skill_dir = Path(path_str)
    if not skill_dir.is_absolute():
        if entry.owned:
            skill_dir = Path(census_path).parent / path_str
        else:
            deck = census.decks.get(entry.deck or "author")
            registry = deck.registry if deck else ""
            skill_dir = (
                Path(registry) / path_str if registry else Path(census_path).parent / path_str
            )
    return skill_dir


def set_field(census: Census, target: str, field: SetField, value: str, census_path: Any) -> str:
    if target == ".":
        if field is not SetField.PHASE:
            raise CensusUsageError("project-level set only supports 'phase'")
        if value not in {"DR", "IP", "PP"}:
            raise CensusUsageError("phase must be one of DR|IP|PP")
        old = census.projectPhase
        census.projectPhase = value
        census.history.append({"date": today(), "event": f"phase transition {old}->{value}"})
        save_census(census_path, census)
        return f"projectPhase: {old} -> {value}"
    entry = entry_of(census, target)
    if entry is None:
        raise KeyError(f"skill '{target}' not in census")
    if field is SetField.BLOCKERS:
        import json

        parsed = json.loads(value)
        if not isinstance(parsed, list):
            raise CensusUsageError("blockers must be a JSON array")
        entry.fit.blockers = [str(v) for v in parsed]
    elif field is SetField.PHASE:
        if value not in {"DR", "IP", "PP", "null"}:
            raise CensusUsageError("phase must be one of DR|IP|PP|null")  # stored as extra key
        extras = entry.fit.__pydantic_extra__
        if extras is None:
            extras = {}
            entry.fit.__pydantic_extra__ = extras
        extras["phase"] = None if value == "null" else value
    elif field is SetField.TYPE:
        entry.type = SkillType(value).value
    elif field is SetField.USE_CASES:
        import json

        parsed = json.loads(value)
        if not isinstance(parsed, list) or not all(isinstance(x, str) for x in parsed):
            raise CensusUsageError("use_cases must be a JSON array of strings")
        entry.use_cases = parsed
    elif field is SetField.DECK:
        if value not in census.decks:
            raise CensusUsageError(f"deck '{value}' not defined")
        prev_deck: str | None = entry.deck
        for deck in census.decks.values():
            while target in deck.skills:
                deck.skills.remove(target)
        census.decks[value].skills.append(target)
        census.decks[value].skills.sort()
        entry.deck = value
        entry.history.append(
            {"date": today(), "event": f"deck resolved by user: {prev_deck} -> {value}"})
    elif field is SetField.PATH:
        from pathlib import Path
        probe = Path(value)
        if not probe.is_absolute():
            probe = Path(census_path).parent / value if entry.owned else Path(
                census.decks[entry.deck or "author"].registry or ".") / value
        if not (probe / "SKILL.md").is_file():
            raise CensusUsageError(f"no SKILL.md at {value}")
        old_path = entry.path
        entry.path = value
        entry.history.append({"date": today(), "event": f"path updated: {old_path} -> {value}"})
    save_census(census_path, census)
    return f"{target}.{field.value} updated"


def log_event(census: Census, target: str, event: str, census_path: Any) -> str:
    record = {"date": today(), "event": event}
    if target == ".":
        census.history.append(record)
    else:
        entry = entry_of(census, target)
        if entry is None:
            raise KeyError(f"skill '{target}' not in census")
        entry.history.append(record)
    save_census(census_path, census)
    return f"logged: {event}"


def add_skill(
    census: Census,
    name: str,
    deck: str,
    path: str,
    serves: list[str],
    stype: str,
    use_cases: list[str],
    census_path: Any,
) -> str:
    from pathlib import Path

    if entry_of(census, name):
        raise CensusUsageError(f"skill '{name}' already exists")
    if not deck or not path:
        raise CensusUsageError("--deck and --path required")
    if deck not in census.decks:
        raise CensusUsageError(f"deck '{deck}' not defined")
    skill_dir = Path(path)
    if not (skill_dir / "SKILL.md").is_file():
        raise CensusUsageError(f"no SKILL.md at {path}")
    fm = parse_frontmatter(skill_dir / "SKILL.md")
    if deck in census.decks and name not in census.decks[deck].skills:
        census.decks[deck].skills.append(name)
        census.decks[deck].skills.sort()
    entry = SkillEntry.model_validate(
        {
            "version": fm.get("version"),
            "type": SkillType(stype).value if stype else SkillType.NORMAL.value,
            "description": fm.get("description", ""),
            "use_cases": use_cases,
            "deck": deck,
            "path": path,
            "owned": False,
            "content": list_content(skill_dir),
            "fit": {"role": "", "when": "", "serves": serves, "blockers": []},
            "history": [{"date": today(), "event": "registered via add-skill"}],
        }
    )
    census.skills[name] = entry
    save_census(census_path, census)
    return f"added: {name} v{entry.version or '?'}"


def remove_skill(census: Census, name: str, census_path: Any, dry: bool = False) -> str:
    if entry_of(census, name) is None:
        raise KeyError(f"skill '{name}' not in census")
    if dry:
        return f"would remove: {name}"
    del census.skills[name]
    for deck in census.decks.values():
        if name in deck.skills:
            deck.skills.remove(name)
    for step in census.lifecycle:
        if name in step.commands:
            step.commands.remove(name)
        if name in step.possible_skills:
            step.possible_skills.remove(name)
    for entry in census.skills.values():
        for kind in ("after", "before", "with"):
            rel_list = [r for r in rels(entry, kind) if r.skill != name]
            if kind == "after":
                entry.fit.after = rel_list
            elif kind == "before":
                entry.fit.before = rel_list
            else:
                entry.fit.with_ = rel_list
    save_census(census_path, census)
    return f"removed: {name}"


def disk_version(census: Census, name: str, census_path: Any) -> str | None:
    entry = entry_of(census, name)
    if entry is None or entry.path is None:
        return None
    skill_dir = skill_dir_on_disk(census, census_path, entry)
    if skill_dir is None or not (skill_dir / "SKILL.md").is_file():
        return None
    return parse_frontmatter(skill_dir / "SKILL.md").get("version")


def drift_rows(census: Census, census_path: Any) -> list[dict[str, str]]:
    rows = []
    for name, entry in census.skills.items():
        disk = disk_version(census, name, census_path)
        if disk and entry.version and disk != entry.version:
            rows.append({"name": name, "census_version": entry.version, "disk_version": disk})
    return rows


def refresh_skill(census: Census, name: str, census_path: Any) -> str:
    entry = entry_of(census, name)
    if entry is None:
        raise KeyError(f"skill '{name}' not in census")
    skill_dir = skill_dir_on_disk(census, census_path, entry)
    if skill_dir is None:
        raise CensusUsageError(f"skill '{name}' has no path")
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        raise CensusUsageError(f"SKILL.md not found at {skill_dir}")
    fm = parse_frontmatter(skill_md)
    entry.version = fm.get("version")
    entry.description = fm.get("description", "")
    entry.content = Content.model_validate(list_content(skill_dir))
    entry.history.append({"date": today(), "event": "refreshed from disk"})
    return f"refreshed: {name} v{entry.version}"


def save(census: Census, census_path: Any) -> None:
    save_census(census_path, census)
