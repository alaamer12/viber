"""The limits catalog — the ONE home for every field boundary.

Field -> Error -> Violation (docs/regime/limits.md owns the doctrine; this file
owns the numbers). Caps are deliberately generous: hitting one during honest work
means the cap is wrong, not the agent. Identity codes, caps, the purpose each bound
protects, and the recovery command live here exactly once; guards (writes), lint
(loaded census), and `viber fields` (the transparent face) all read this table, so
what the CLI promises and what it enforces cannot drift.

Intentional duplication per Error-as-Truth: DESCRIPTION_MAX_CHARS and
DOING_MAX_CHARS are distinct violations of distinct fields — never a shared one.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

KIND_CHARS: Final = "chars"
KIND_ITEMS: Final = "items"
_KIND_LABEL: Final = {KIND_CHARS: "MAX_CHARS", KIND_ITEMS: "MAX_ITEMS"}


@dataclass(frozen=True, slots=True)
class Limit:
    field: str
    kind: str
    cap: int
    why: str
    recovery: str

    @property
    def identity(self) -> str:
        return f"{self.field.upper()}_{_KIND_LABEL[self.kind]}"

    @property
    def unit(self) -> str:
        return "characters" if self.kind == KIND_CHARS else "records"

    def message(self, got: int) -> str:
        return (
            f"{self.identity} — {self.field} cannot exceed {self.cap} {self.unit} "
            f"(got {got}). {self.why} Fix: {self.recovery}"
        )


def _l(field: str, kind: str, cap: int, why: str, recovery: str) -> Limit:
    return Limit(field=field, kind=kind, cap=cap, why=why, recovery=recovery)


_C = KIND_CHARS
_I = KIND_ITEMS

_RAW: Final[tuple[Limit, ...]] = (
    # skill entry — strings
    _l("name", _C, 100, "skill names are filesystem slugs", "use a short slug (kebab-case)"),
    _l(
        "version", _C, 40, "version is a dot-number tag",
        "fix SKILL.md frontmatter `version`, then `viber refresh <skill>`",
    ),
    _l(
        "description", _C, 4000,
        "the census stores summaries, not documents — the body lives in SKILL.md",
        "shorten the frontmatter description in SKILL.md, then `viber refresh <skill>`",
    ),
    _l(
        "role", _C, 400, "fit.role is one line of orientation",
        "rewrite the deck's fit.role for this skill",
    ),
    _l("when", _C, 400, "fit.when is the trigger moment, one line", "rewrite fit.when shorter"),
    _l(
        "doing", _C, 2000, "fit.doing is the concrete next-task paragraph, not an essay",
        "tighten it: viber set <skill> doing",
    ),
    _l(
        "why", _C, 2000, "fit.why is one argument, not the whole debate",
        "tighten it: viber set <skill> why",
    ),
    _l(
        "hint", _C, 300, "an edge hint reads inside one terminal line",
        "shorten the edge hint at its source",
    ),
    _l("long_hint", _C, 1500, "long_hint is the use-case sentence of an edge", "shorten it"),
    _l(
        "path", _C, 500, "paths longer than this signal a wrong root",
        "pass the clone-relative path: viber set <skill> path",
    ),
    # skill entry — lists
    _l(
        "history", _I, 100, "a ledger, not an archive — rolling window: oldest evicts on append",
        "the /vcompact skill archives the old trail if you want it kept; "
        "eviction itself is automatic and announced",
    ),
    _l(
        "blockers", _I, 20, "blocked means a handful of named walls",
        "consolidate blockers: viber set <skill> blockers",
    ),
    _l(
        "use_cases", _I, 30, "situations a skill applies to, enumerable",
        "merge near-duplicate cases: viber set <skill> use_cases",
    ),
    _l(
        "serves", _I, 12, "steps are the spine — a skill serving everything serves nothing",
        "pick the steps that genuinely consume it",
    ),
    _l(
        "produces", _I, 40, "artifacts a skill creates, enumerable",
        "group entries by artifact family",
    ),
    _l(
        "consumes", _I, 40, "inputs a skill reads, enumerable",
        "group entries by artifact family",
    ),
    _l(
        "after", _I, 50, "predecessor edges beyond this repeat the census as a graph",
        "keep ordering edges, drop descriptive ones to with",
    ),
    _l("before", _I, 50, "successor edges mirror after", "order edges here, narrative in hints"),
    _l("with", _I, 50, "pairing is short and true", "prune to the real companions"),
    # history record parts
    _l("event", _C, 300, "a history line is one dated sentence", "summarize the event line"),
    _l("date", _C, 40, "dates are YYYY-MM-DD, not prose", "use the ISO day form"),
    # list-item strings — distinct fields, distinct violations (Error as Truth)
    _l(
        "blocker", _C, 300, "one blocker names one wall, in a line",
        "split compound blockers or shorten each",
    ),
    _l(
        "use_case", _C, 300, "a situation that fits the skill, in a phrase",
        "shorten the case line",
    ),
    _l(
        "artifact", _C, 300, "produces/consumes/needs entries name things, not paragraphs",
        "name the artifact, explain elsewhere",
    ),
    # lifecycle step parts
    _l("step_name", _C, 100, "step names are spine labels", "shorten the step name"),
    _l("goal", _C, 500, "a step goal is one sentence of intent", "tighten the step goal"),
    # census-level
    _l(
        "skills", _I, 5000, "a census of thousands of skills is a registry service, not a file",
        "split decks or prune registrations",
    ),
    _l(
        "unclassified", _I, 200, "awaiting-classification is a queue, not a landfill",
        "classify or drop entries via deck membership",
    ),
    _l(
        "lifecycle", _I, 12, "the fixed spine has five steps; growth means a fork, not a project",
        "merge back into the canonical steps",
    ),
    _l(
        "needs", _I, 20, "step needs are the accomplishments list of one phase",
        "consolidate step needs",
    ),
    _l(
        "possible_skills", _I, 100, "the candidate pool per step stays readable",
        "curate the step's pool",
    ),
    _l(
        "commands", _I, 30, "v-commands per step, enumerable", "prune declared commands",
    ),
    _l(
        "deck.skills", _I, 5000, "deck membership mirrors the census bound",
        "prune deck membership",
    ),
    _l(
        "registry", _C, 500, "a registry pointer is one path",
        "shorten or relocate the deck registry",
    ),
    _l(
        "deck_name", _C, 100, "a deck name is a label, not a document",
        "shorten the deck's name in the seed",
    ),
    _l(
        "deck_description", _C, 1000, "deck description orients, never documents",
        "tighten the deck's description",
    ),
    _l(
        "project.name", _C, 100, "census name is the project slug",
        "rename the census via the seed",
    ),
    _l("census.version", _C, 40, "seed version tag", "bump the seed version normally"),
    _l("created", _C, 40, "creation stamp", "keep ISO day form"),
    _l("createdBy", _C, 200, "one author line", "keep it one line"),
)

LIMITS: Final[dict[str, Limit]] = {lim.field: lim for lim in _RAW}


def guard_chars(field: str, value: str) -> None:
    """Raise ValueError (CLI maps to exit 2) with the cataloged message on overflow."""
    lim = LIMITS[field]
    if len(value) > lim.cap:
        raise ValueError(lim.message(len(value)))


def guard_items(field: str, values: Sequence[object]) -> None:
    lim = LIMITS[field]
    if len(values) > lim.cap:
        raise ValueError(lim.message(len(values)))


def append_history(target: list[dict[str, str]], record: dict[str, str]) -> int:
    """Rolling ledger: append, evict oldest past the cap, return how many evicted.
    Callers MUST mention eviction in the ack — nothing here is silent."""
    target.append(record)
    evicted = max(0, len(target) - LIMITS["history"].cap)
    if evicted:
        del target[:evicted]
    return evicted
