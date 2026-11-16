"""Resolution: step rosters (topological), current step, `next` candidates with
reasons, and the deck/pool gap — the decision algebra of the census."""

import heapq
from typing import Any

from viber.core.census_ops import (
    blockers_of,
    rels,
    serving_skills,
    step_of,
)
from viber.core.census_ops import (
    current_step as current_step,
)
from viber.data.telemetry import TelemetryDB
from viber.models.domain import RosterRow, SkillName, StepName
from viber.models.schema import Census


def step_roster(census: Census, step_name: StepName) -> list[SkillName]:
    """Serving skills ordered by within-step after-edges; ties and cycles fall back
    to census insertion order (reproduces the curated favorite-deck sequence)."""
    members = serving_skills(census, step_name)
    index = {n: i for i, n in enumerate(members)}
    indeg = dict.fromkeys(members, 0)
    dependents: dict[SkillName, list[SkillName]] = {n: [] for n in members}
    for m in members:
        entry = census.skills[m]
        for rel in rels(entry, "after"):
            p = rel.skill
            if p in index and p != m:
                indeg[m] += 1
                dependents[p].append(m)
    ready = [index[n] for n in members if indeg[n] == 0]
    heapq.heapify(ready)
    out: list[SkillName] = []
    while ready:
        n = members[heapq.heappop(ready)]
        out.append(n)
        for nxt in dependents[n]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                heapq.heappush(ready, index[nxt])
    if len(out) != len(members):
        out += [n for n in members if n not in out]
    return out


def roster_rows(census: Census, step_name: StepName) -> list[RosterRow]:
    rows: list[RosterRow] = []
    for name in step_roster(census, step_name):
        entry = census.skills[name]
        blocked = blockers_of(census, name)
        rows.append(
            RosterRow(
                name=name, version=entry.version or "?", status="blocked" if blocked else "ready"
            )
        )
    return rows


def uninstalled_candidates(census: Census, step_name: StepName) -> list[SkillName]:
    roster = set(step_roster(census, step_name))
    step = next(s for s in census.lifecycle if s.step == step_name)
    return [c for c in step.possible_skills if c not in roster]


def _reasons(
    census: Census, name: SkillName, long: bool
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    short: list[str] = []
    detail: list[str] = []
    entry = census.skills[name]
    if not entry.fit.after:
        step_name = entry.fit.serves[0] if entry.fit.serves else "-"
        short.append(f"first in {step_name} — no recorded predecessors")
        return tuple(short), tuple(detail)
    for rel in entry.fit.after:
        if rel.skill not in census.skills:
            short.append(f"references predecessor '{rel.skill}' not in census (see lint)")
            continue
        if blockers_of(census, rel.skill):
            short.append(f"waits on {rel.skill} (blocked)")
        elif rel.hint:
            short.append(f"follows {rel.skill}: {rel.hint}")
            if long and rel.long_hint:
                detail.append(f"{rel.skill}: {rel.long_hint}")
        else:
            short.append(f"follows {rel.skill}")
    return tuple(short), tuple(detail)


def next_candidates(
    census: Census, db: TelemetryDB | None, count: int = 1, long: bool = False
) -> dict[str, Any]:
    step_name = current_step(census)
    if step_name is None:
        return {"step": None, "candidates": [], "blocked": []}
    blocked: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for name in step_roster(census, step_name):
        entry = census.skills[name]
        blockers = blockers_of(census, name)
        if blockers:
            blocked.append({"skill": name, "blockers": ", ".join(blockers)})
            continue
        reasons, reason_long = _reasons(census, name, long)
        suggestion = ""
        if db is not None and db.exists():
            succ = db.successor(name)
            if succ:
                suggestion = f"historically followed by {succ[0]} ({succ[1]}x)"
        candidates.append(
            {
                "skill": name,
                "when": entry.fit.when,
                "reasons": list(reasons),
                "reason_long": list(reason_long),
                "consumes": list(entry.fit.consumes),
                "produces": list(entry.fit.produces),
                "suggestion": suggestion,
            }
        )
        if len(candidates) >= count:
            break
    return {"step": step_name, "candidates": candidates, "blocked": blocked}


def status_payload(census: Census) -> dict[str, Any]:
    step_name = current_step(census)
    blocked = sum(1 for e in census.skills.values() if e.fit.blockers)
    return {
        "phase": census.projectPhase,
        "step": step_name or "-",
        "total": len(census.skills),
        "blocked": blocked,
        "unclassified": len(census.unclassified),
    }


def list_payload(
    census: Census, by: str = "name", flt: str | None = None, brief: bool = False
) -> dict[str, Any]:
    sortable = ("name", "version", "type", "deck", "step", "owned")
    if by not in sortable:
        raise ValueError(f"unknown --by key: {by!r} (choose from {', '.join(sortable)})")
    rows = []
    for name, entry in census.skills.items():
        rows.append(
            {
                "name": name,
                "version": entry.version or "?",
                "type": entry.type,
                "deck": entry.deck or "?",
                "step": step_of(census, name),
                "owned": entry.owned,
            }
        )
    if flt:
        for clause in (c.strip() for c in flt.split(",") if c.strip()):
            if "=" not in clause:
                raise ValueError(f"bad filter clause: {clause!r} (expected key=value)")
            key, _, val = clause.partition("=")
            if key not in sortable:
                raise ValueError(f"unknown filter key: {key!r} (choose from {', '.join(sortable)})")
            rows = [r for r in rows if str(r[key]) == val]
    rows.sort(key=lambda r: str(r[by]))
    return {"count": len(rows), "skills": rows, "brief": brief, "by": by, "filter": flt or ""}


def deck_payload(census: Census, name: str | None) -> dict[str, Any]:
    if name:
        deck = census.decks[name]
        d = deck.model_dump(mode="json", by_alias=True)
        return {
            "deck": name,
            "name": d["name"],
            "description": d["description"],
            "mutability": d["mutability"],
            "registry": d["registry"],
            "remote": d["remote"],
            "skills_count": len(d["skills"]),
            "skills": d["skills"],
        }
    return {
        "decks": [
            {
                "name": k,
                "mutability": v.mutability,
                "skills_count": len(v.skills),
                "registry": v.registry,
            }
            for k, v in census.decks.items()
        ]
    }
