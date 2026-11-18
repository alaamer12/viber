"""Pydantic boundary models: the census file is untrusted input — validate on load,
dump on save. extra="allow" everywhere so unknown keys survive a round-trip, and
declaration order mirrors the seed's exact key order (round-trip parity is tested)."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from viber.models.domain import Mutability, Phase, SkillType


class _Model(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class Relation(_Model):
    skill: str
    hint: str = ""
    long_hint: str = ""

    @model_validator(mode="before")
    @classmethod
    def _accept_plain_string(cls, v: Any) -> Any:
        if isinstance(v, str):
            return {"skill": v, "hint": "", "long_hint": ""}
        return v


class Fit(_Model):
    role: str = ""
    when: str = ""
    doing: str = ""
    why: str = ""
    serves: list[str] = []
    after: list[Relation] = []
    before: list[Relation] = []
    with_: list[Relation] = Field(default=[], validation_alias="with", serialization_alias="with")
    produces: list[str] = []
    consumes: list[str] = []
    blockers: list[str] = []


class Content(_Model):
    entry: str = "SKILL.md"
    references: list[str] = []
    assets: list[str] = []
    examples: list[str] = []


class SkillEntry(_Model):
    version: str | None = None
    type: SkillType = SkillType.NORMAL
    description: str | None = None
    use_cases: list[str] = []
    deck: str | None = None
    path: str | None = None
    owned: bool = False
    content: Content = Field(default_factory=Content)
    fit: Fit = Field(default_factory=Fit)
    history: list[dict[str, Any]] = Field(default_factory=list)


class Deck(_Model):
    name: str = ""
    description: str = ""
    mutability: Mutability = Mutability.OPEN
    registry: str = ""
    remote: str | None = None
    skills: list[str] = Field(default_factory=list)


class Step(_Model):
    step: str
    phase: Phase | None = None
    goal: str = ""
    needs: list[str] = Field(default_factory=list)
    possible_skills: list[str] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)


class Census(_Model):
    name: str = "viber"
    version: str = ""
    created: str = ""
    createdBy: str = ""
    projectPhase: Phase = Phase.DRAFT
    decks: dict[str, Deck] = Field(default_factory=dict)
    lifecycle: list[Step] = Field(default_factory=list)
    skills: dict[str, SkillEntry] = Field(default_factory=dict)
    unclassified: list[Any] = Field(default_factory=list)
    history: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _required_top_keys(cls, v: Any) -> Any:
        if isinstance(v, dict):
            missing = {"skills", "lifecycle", "decks"} - set(v)
            if missing:
                raise ValueError(f"census missing required keys: {', '.join(sorted(missing))}")
        return v
