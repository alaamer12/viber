"""Domain queries over validated census models — pure, no IO, no printing."""

from typing import Any

from viber.models.domain import SkillName, StepName
from viber.models.schema import Census, Relation, SkillEntry


def entry_of(census: Census, name: SkillName) -> SkillEntry | None:
    return census.skills.get(name)


def rels(fit_owner: SkillEntry, kind: str) -> list[Relation]:
    fit = fit_owner.fit
    if kind == "after":
        return fit.after
    if kind == "before":
        return fit.before
    if kind == "with":
        return fit.with_
    raise ValueError(f"unknown relation kind: {kind}")


def blockers_of(census: Census, name: SkillName) -> list[str]:
    entry = entry_of(census, name)
    return list(entry.fit.blockers) if entry else []


def step_of(census: Census, name: SkillName) -> str:
    entry = entry_of(census, name)
    if entry and entry.fit.serves:
        return ", ".join(entry.fit.serves)
    for step in census.lifecycle:
        if name in step.commands:
            return step.step
    return "-"


def current_step(census: Census) -> StepName | None:
    phase = census.projectPhase
    for step in census.lifecycle:
        if step.phase == phase:
            return step.step
    for step in census.lifecycle:
        if step.phase is None:
            return step.step
    return None


def serving_skills(census: Census, step_name: StepName) -> list[SkillName]:
    return [n for n, e in census.skills.items() if step_name in e.fit.serves]


def skill_payload(census: Census, name: SkillName) -> dict[str, Any]:
    entry = entry_of(census, name)
    assert entry is not None  # caller-checked
    payload: dict[str, Any] = {"skill": name, **entry.model_dump(mode="json", by_alias=True)}
    payload["step"] = step_of(census, name)
    return payload
