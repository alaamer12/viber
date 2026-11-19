import os
from importlib.resources import files
from pathlib import Path
from tempfile import NamedTemporaryFile

from pydantic import ValidationError

from viber.core.lint import run_lint
from viber.core.mutations import today
from viber.data.frontmatter import list_content, parse_frontmatter
from viber.data.skill_registry import conflicting_sources, scan_skills
from viber.data.store import CensusError, dump_census, load_census
from viber.models.domain import Finding, Phase, Severity
from viber.models.schema import Census, Content, SkillEntry


def load_seed() -> tuple[Census, Path | None]:
    checkout = Path(__file__).resolve().parents[3]
    source = checkout / "viber.json"
    source_tree = checkout / "src" / "viber" / "core"
    if source_tree == Path(__file__).resolve().parent and source.is_file():
        return load_census(source), source
    try:
        text = files("viber.data").joinpath("seed.json").read_text(encoding="utf-8")
        return Census.model_validate_json(text), None
    except (OSError, ValidationError) as exc:
        raise CensusError(f"cannot load packaged master seed: {exc}") from exc


def _source_directory(census: Census, seed_path: Path | None, entry: SkillEntry) -> Path | None:
    if not entry.path:
        return None
    path = Path(entry.path)
    if path.is_absolute():
        return path
    if entry.owned:
        return seed_path.parent / path if seed_path else None
    deck = census.decks.get(entry.deck or "author")
    if not deck or not deck.registry:
        return seed_path.parent / path if seed_path else None
    registry = Path(deck.registry)
    if not registry.is_absolute():
        if seed_path is None:
            return None
        registry = seed_path.parent / registry
    return registry / path


def prepare_census(
    seed: Census, seed_path: Path | None, roots: list[Path], target: Path,
) -> tuple[Census, list[Finding]]:
    installed = scan_skills(roots)
    conflicts = conflicting_sources(installed)
    if conflicts:
        details = "; ".join(f"{name}: {', '.join(paths)}" for name, paths in conflicts.items())
        raise CensusError(f"conflicting skill sources — choose one registered source: {details}")
    by_name = {skill.name: skill for skill in installed}
    census = seed.model_copy(deep=True)
    for name, entry in census.skills.items():
        matched = by_name.get(name)
        directory = matched.source if matched else _source_directory(seed, seed_path, entry)
        entry.history = []
        entry.fit.blockers = []
        if entry.fit.__pydantic_extra__:
            entry.fit.__pydantic_extra__.pop("phase", None)
        if directory is None or not (directory / "SKILL.md").is_file():
            entry.path = None
            entry.fit.blockers = [
                f"Skill '{name}' is not installed; register its path before invoking it."
            ]
            continue
        directory = directory.resolve()
        metadata = parse_frontmatter(directory / "SKILL.md")
        entry.path = directory.as_posix()
        entry.version = metadata.get("version")
        entry.description = metadata.get("description") or entry.description
        entry.content = Content.model_validate(list_content(directory))
    census.projectPhase = Phase.DRAFT
    census.created = today()
    census.createdBy = "viber init"
    census.history = []
    if "project" in census.decks:
        project = census.decks["project"]
        project.name = "Project Deck"
        project.remote = None
        umbrella = target.parent.parent if target.parent.name == ".data" else target.parent
        project.registry = (umbrella / "registry.md").resolve().as_posix()
    census = Census.model_validate(census.model_dump(mode="json", by_alias=True))
    findings = run_lint(census, target)
    return census, findings


def create_census(path: Path, census: Census) -> None:
    temporary: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent,
            prefix=".viber-init-", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(dump_census(census))
        # Linking publishes the complete file atomically without replacing a concurrent creator.
        os.link(temporary, path)
    except FileExistsError as exc:
        raise CensusError(f"refusing to overwrite census: {path}") from exc
    except OSError as exc:
        raise CensusError(f"cannot create census at {path}: {exc}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def has_errors(findings: list[Finding]) -> bool:
    return any(f.severity in (Severity.ERROR, Severity.QUESTION) for f in findings)
