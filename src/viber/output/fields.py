"""Field registry: every emitted key per command, its group, profile membership and
dependencies. The single source of truth for what `--include/--exclude/-P` can address."""

from typing import Final

from viber.models.domain import FieldSpec, Profile

_ALL: Final = frozenset(Profile)
_STD_FULL: Final = frozenset({Profile.STANDARD, Profile.FULL})


def _f(
    key: str, group: str, profiles: frozenset[Profile], depends_on: tuple[str, ...] = ()
) -> FieldSpec:
    return FieldSpec(key=key, group=group, profiles=profiles, depends_on=depends_on)


REGISTRY: Final[dict[str, tuple[FieldSpec, ...]]] = {
    "skill": (
        _f("skill", "identity", _ALL),
        _f("version", "identity", _ALL),
        _f("type", "identity", _ALL),
        _f("deck", "identity", _ALL),
        _f("path", "identity", _ALL),
        _f("owned", "identity", _STD_FULL),
        _f("step", "identity", _ALL),
        _f("description", "purpose", _STD_FULL),
        _f("use_cases", "purpose", _STD_FULL),
        _f("fit", "fit", _STD_FULL),
        _f("long_hints", "fit", frozenset({Profile.FULL}), ("fit",)),
        _f("content", "content", _STD_FULL),
        _f("history", "history", frozenset({Profile.FULL})),
    ),
    "step": (
        _f("step", "identity", _ALL),
        _f("phase", "identity", _STD_FULL),
        _f("goal", "purpose", _STD_FULL),
        _f("needs", "purpose", frozenset({Profile.FULL})),
        _f("possible_skills", "pool", _STD_FULL),
        _f("commands", "roster", _STD_FULL),
        _f("roster", "roster", _ALL),
    ),
    "next": (
        _f("step", "identity", _STD_FULL),
        _f("candidates", "decision", _ALL),
        _f("reasons", "decision", _ALL, ("candidates",)),
        _f("suggestion", "context", _STD_FULL, ("candidates",)),
        _f("blocked", "context", _STD_FULL),
        _f("previous", "context", _STD_FULL),
        _f("needs", "decision", _STD_FULL),
        _f("commands", "decision", frozenset({Profile.FULL})),
        _f("long_hints", "detail", frozenset({Profile.FULL})),
    ),
    "deck": (
        _f("deck", "identity", _ALL),
        _f("name", "identity", _STD_FULL),
        _f("description", "purpose", _STD_FULL),
        _f("mutability", "identity", _ALL),
        _f("registry", "source", _STD_FULL),
        _f("remote", "source", _STD_FULL),
        _f("skills_count", "roster", _ALL),
        _f("skills", "roster", _STD_FULL),
        _f("decks", "roster", _ALL),
    ),
    "status": (
        _f("phase", "core", _ALL),
        _f("step", "core", _ALL),
        _f("total", "counts", _STD_FULL),
        _f("blocked", "counts", _STD_FULL),
        _f("unclassified", "counts", _STD_FULL),
    ),
    "situation": (
        _f("phase", "core", _ALL),
        _f("step", "core", _ALL),
        _f("previous", "core", _STD_FULL),
        _f("total", "counts", _STD_FULL),
        _f("blocked", "counts", _STD_FULL),
        _f("unclassified", "counts", frozenset({Profile.FULL})),
        _f("roster", "state", _STD_FULL),
        _f("usage", "state", _STD_FULL),
        _f("next", "decision", _STD_FULL),
        _f("needs", "decision", _STD_FULL),
        _f("open", "decision", _STD_FULL),
    ),
    "list": (
        _f("count", "core", _ALL),
        _f("skills", "rows", _ALL),
        _f("brief", "rows", _ALL),
        _f("by", "rows", _STD_FULL),
        _f("filter", "rows", _STD_FULL),
    ),
    "stats": (
        _f("present", "core", _ALL),
        _f("skill", "core", _STD_FULL),
        _f("rows", "rows", _ALL),
    ),
    "patterns": (
        _f("present", "core", _ALL),
        _f("top", "core", _STD_FULL),
        _f("rows", "rows", _ALL),
    ),
    "lint": (
        _f("summary", "core", _ALL),
        _f("findings", "rows", _STD_FULL),
    ),
    "config": (
        _f("keys", "rows", _ALL),
        _f("key", "core", _ALL),
        _f("value", "core", _ALL),
        _f("source", "detail", _STD_FULL),
        _f("default", "detail", frozenset({Profile.FULL})),
        _f("project", "source", _ALL),
        _f("user", "source", _ALL),
        _f("plugin_dirs", "source", _STD_FULL),
    ),
}


def specs_for(command: str) -> tuple[FieldSpec, ...]:
    return REGISTRY[command]


def known_keys(command: str) -> tuple[str, ...]:
    return tuple(s.key for s in specs_for(command))
