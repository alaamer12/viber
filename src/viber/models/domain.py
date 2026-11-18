"""Internal domain objects: enums and frozen value dataclasses (no validation here —
pydantic owns the boundary; these are the shapes the core passes around)."""

from dataclasses import dataclass
from enum import StrEnum

SkillName = str
StepName = str
DeckName = str


class Phase(StrEnum):
    DRAFT = "DR"
    IN_PROGRESS = "IP"
    POST_PRODUCTION = "PP"


class SkillType(StrEnum):
    BATTERY = "battery"
    META = "meta"
    NORMAL = "normal"
    HYBRID = "hybrid"
    OTHERWISE = "otherwise"


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    QUESTION = "question"


class FormatKind(StrEnum):
    TXT = "txt"
    JSON = "json"


class Profile(StrEnum):
    MINIMAL = "minimal"
    STANDARD = "standard"
    FULL = "full"


class SetField(StrEnum):
    BLOCKERS = "blockers"
    PHASE = "phase"
    TYPE = "type"
    USE_CASES = "use_cases"
    DECK = "deck"
    PATH = "path"
    DOING = "doing"
    WHY = "why"


class Outcome(StrEnum):
    OK = "ok"
    FAIL = "fail"
    SKIP = "skip"


class Source(StrEnum):
    FLAG = "flag"
    ENV = "env"
    PROJECT = "project"
    USER = "user"
    DEFAULT = "default"


class ConfigKey(StrEnum):
    CENSUS = "census"
    PROFILE = "profile"
    FORMAT = "format"
    TELEMETRY = "telemetry"
    PLUGINS = "plugins"


@dataclass(slots=True, frozen=True)
class Finding:
    severity: Severity
    check: str
    subject: str
    detail: str
    question: str | None = None

    @property
    def ask_user(self) -> bool:
        return self.question is not None


@dataclass(slots=True, frozen=True)
class FieldSpec:
    key: str
    group: str
    profiles: frozenset[Profile]
    depends_on: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class Candidate:
    """One unblocked skill offered by `next`."""

    name: SkillName
    reasons: tuple[str, ...]
    when: str
    consumes: tuple[str, ...]
    produces: tuple[str, ...]
    suggestion: str = ""


@dataclass(slots=True, frozen=True)
class VersionDrift:
    name: SkillName
    census_version: str
    disk_version: str


@dataclass(slots=True, frozen=True)
class RosterRow:
    name: SkillName
    version: str
    status: str  # ready | blocked | command | candidate
