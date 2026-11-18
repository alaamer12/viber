"""Read commands: skill, step, next, deck, status, situation, list, stats, patterns.

Handlers declare the seven global options explicitly (standard typer style) and
assemble `Globals` in one line.
"""

from collections.abc import Callable
from typing import Any

import typer

from viber.cli.deps import (
    CensusOpt,
    ExcludeOpt,
    ForceOpt,
    FormatOpt,
    Globals,
    IncludeOpt,
    OutOpt,
    ProfileOpt,
    command,
)
from viber.core import census_ops, resolution
from viber.core import lint as lint_core
from viber.output.emit import emit


def _apply(sel: list[str], overrides: dict[str, bool]) -> list[str]:
    out = list(sel)
    for key, want in overrides.items():
        if want and key not in out:
            out.append(key)
        elif not want:
            out = [k for k in out if k != key]
    return out


def _fail(msg: str) -> int:
    typer.secho(f"error: {msg}", fg="red", err=True)
    return 1


@command
def skill_cmd(
    name: str,
    content: bool | None = typer.Option(
        None,
        "--content/--no-content",
        "-c",
        help="Content file paths only (with --content); omit the tree (with --no-content)",
    ),
    path_only: bool = typer.Option(False, "--path", "-p", help="Print the disk path only"),
    brief: bool = typer.Option(False, "--brief", "-b", help="One-line summary"),
    relations: bool | None = typer.Option(
        None, "--relations/--no-relations", "-r", help="Fit section incl. relations"
    ),
    use_cases: bool | None = typer.Option(
        None, "--use-cases/--no-use-cases", "-u", help="When-to-use situations"
    ),
    history: bool | None = typer.Option(
        None, "--history/--no-history", "-H", help="Census history entries"
    ),
    long_hints: bool | None = typer.Option(
        None, "--long", "-l", help="Show relation long_hint detail"
    ),
    census: CensusOpt = None,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
) -> int:
    """Full census card for one skill: identity, fit, relations, content."""
    g = Globals(census, fmt, out, force, profile, include, exclude)
    data = g.load()
    if census_ops.entry_of(data, name) is None:
        return _fail(f"skill '{name}' not in census")
    if path_only:
        print(data.skills[name].path or "null")
        return 0
    if brief:
        entry = data.skills[name]
        desc = (entry.description or "")[:100]
        print(f"{name} v{entry.version or '?'} — {desc}")
        return 0
    payload = census_ops.skill_payload(data, name)
    sel = g.selection_with(
        "skill",
        {
            "content": content,
            "fit": relations,
            "use_cases": use_cases,
            "history": history,
            "long_hints": long_hints,
        },
    )
    if content:
        # the flag contract: --content means "paths only", not "add the tree"
        sel = ["skill", "content"]
    emit("skill", payload, sel, g.target())
    return 0


@command
def step_cmd(
    name: str | None = typer.Argument(None),
    needs: bool | None = typer.Option(None, "--needs/--no-needs", "-n", help="Show step needs"),
    pool: bool | None = typer.Option(
        None, "--pool/--no-pool", "-p", help="Show uninstalled candidates"
    ),
    roster: bool = typer.Option(True, "--roster/--no-roster", "-r"),
    commands: bool = typer.Option(True, "--commands/--no-commands", "-c"),
    census: CensusOpt = None,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
) -> int:
    """Goal, needs and resolved roster for a step (default: the current one)."""
    g = Globals(census, fmt, out, force, profile, include, exclude)
    data = g.load()
    if name:
        step = next((s for s in data.lifecycle if s.step.lower() == name.lower()), None)
        if step is None:
            return _fail(f"step '{name}' not found")
    else:
        step_name = resolution.current_step(data)
        if step_name is None:
            return _fail("no current step determinable")
        step = next(s for s in data.lifecycle if s.step == step_name)
    rows = resolution.roster_rows(data, step.step)
    roster_dicts: list[dict[str, Any]] = [
        {"name": r.name, "version": r.version, "status": r.status} for r in rows
    ]
    if commands:
        roster_dicts += [{"name": c, "version": "-", "status": "command"} for c in step.commands]
    payload = {
        "step": step.step,
        "phase": step.phase,
        "goal": step.goal,
        "needs": step.needs,
        "possible_skills": step.possible_skills,
        "uninstalled_candidates": resolution.uninstalled_candidates(data, step.step),
        "commands": step.commands,
        "roster": roster_dicts if roster else [],
    }
    sel = g.selection_with("step", {"needs": needs, "possible_skills": pool})
    emit("step", payload, sel, g.target())
    return 0


@command
def next_cmd(
    count: int = typer.Option(1, "--count", "-n", min=1, help="Show N unblocked candidates"),
    reasons: bool | None = typer.Option(None, "--reasons/--no-reasons", "-r"),
    suggestion: bool | None = typer.Option(
        None, "--suggestion/--no-suggestion", "-s", help="Telemetry successor hint"
    ),
    long_hints: bool | None = typer.Option(None, "--long", "-l"),
    census: CensusOpt = None,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
) -> int:
    """Possible next steps — why each, what doing it means, and the skill-less needs."""
    g = Globals(census, fmt, out, force, profile, include, exclude)
    data = g.load()
    payload = resolution.next_candidates(data, g.db(), count=count)
    if payload["step"] is None:
        return _fail("no current step")
    sel = g.selection_with(
        "next", {"reasons": reasons, "suggestion": suggestion, "long_hints": long_hints}
    )
    emit("next", payload, sel, g.target())
    return 0


@command
def deck_cmd(
    name: str | None = typer.Argument(None),
    skills: bool | None = typer.Option(None, "--skills/--no-skills", "-s"),
    census: CensusOpt = None,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
) -> int:
    """Deck roster and metadata — all decks when no name is given."""
    g = Globals(census, fmt, out, force, profile, include, exclude)
    data = g.load()
    if name and name not in data.decks:
        return _fail(f"deck '{name}' not found")
    payload = resolution.deck_payload(data, name)
    sel = g.selection_with("deck", {"skills": skills})
    emit("deck", payload, sel, g.target())
    return 0


@command
def status_cmd(
    census: CensusOpt = None,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
) -> int:
    """Phase, current step and census counts."""
    g = Globals(census, fmt, out, force, profile, include, exclude)
    emit("status", resolution.status_payload(g.load()), g.selection_with("status"), g.target())
    return 0


@command
def list_cmd(
    brief: bool = typer.Option(False, "--brief", "-b"),
    by: str = typer.Option("name", "--by", help="name|version|type|deck|step"),
    flt: str = typer.Option("", "--filter", help="key=value[,key=value]"),
    census: CensusOpt = None,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
) -> int:
    """All skills in a table, sortable (--by) and filterable (--filter)."""
    g = Globals(census, fmt, out, force, profile, include, exclude)
    payload = resolution.list_payload(g.load(), by=by, flt=flt or None, brief=brief)
    emit("list", payload, g.selection_with("list"), g.target())
    return 0


@command
def stats_cmd(
    name: str | None = typer.Argument(None),
    since: str = typer.Option("", "--since", "-s", help="YYYY-MM-DD lower bound"),
    census: CensusOpt = None,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
) -> int:
    """Telemetry usage counts per skill (or one skill's history)."""
    g = Globals(census, fmt, out, force, profile, include, exclude)
    data = g.load()
    if name and census_ops.entry_of(data, name) is None:
        return _fail(f"skill '{name}' not in census")
    db = g.db()
    if not db.exists():
        emit(
            "stats",
            {"present": False, "skill": name, "rows": {}},
            g.selection_with("stats"),
            g.target(),
        )
        return 0
    if name:
        payload = {"present": True, "skill": name, "rows": db.skill_stats(name)}
    else:
        payload = {"present": True, "rows": db.all_stats(since or None)}
    emit("stats", payload, g.selection_with("stats"), g.target())
    return 0


@command
def patterns_cmd(
    top: int = typer.Option(15, "--top", "-t", min=1),
    census: CensusOpt = None,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
) -> int:
    """Most frequent skill-to-skill sequences from telemetry."""
    g = Globals(census, fmt, out, force, profile, include, exclude)
    assert g.load() is not None  # census presence validated for the uniform contract
    db = g.db()
    if not db.exists():
        emit("patterns", {"present": False, "top": top, "rows": []},
             g.selection_with("patterns"), g.target())
        return 0
    rows = [{"sequence": s, "count": c} for s, c in db.pairs(top)]
    emit("patterns", {"present": True, "top": top, "rows": rows}, g.selection_with("patterns"),
         g.target())
    return 0


@command
def situation_cmd(
    census: CensusOpt = None,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
) -> int:
    """The whole situation in one call: phase, step, roster, usage, next, owed decisions."""
    g = Globals(census, fmt, out, force, profile, include, exclude)
    data = g.load()
    step_name = resolution.current_step(data)
    if step_name is None:
        return _fail("no current step")
    rows = resolution.roster_rows(data, step_name)
    db = g.db()
    usage_rows: list[dict[str, object]] = db.all_stats() if db.exists() else []
    nxt = resolution.next_candidates(data, db, count=1)
    top = nxt["candidates"][0] if nxt["candidates"] else None
    payload: dict[str, Any] = {
        "phase": data.projectPhase,
        "step": step_name,
        "total": len(data.skills),
        "blocked": sum(1 for e in data.skills.values() if e.fit.blockers),
        "unclassified": len(data.unclassified),
        "roster": [{"name": r.name, "version": r.version, "status": r.status} for r in rows],
        "usage": {"present": db.exists(), "rows": usage_rows},
        "next": (
            None
            if top is None
            else {
                "skill": top["skill"],
                "when": top["when"],
                "todo": top["todo"],
                "doing": top["doing"],
                "why": top["why"],
                "reasons": top["reasons"],
                "reason_long": top["reason_long"],
            }
        ),
        "needs": list(next(s for s in data.lifecycle if s.step == step_name).needs),
        "previous": nxt["previous"],
        "open": [
            f"{f.subject}: {f.question}"
            for f in lint_core.run_lint(data, g.census_path)
            if f.question is not None
        ],
    }
    emit("situation", payload, g.selection_with("situation"), g.target())
    return 0


COMMANDS: dict[str, Callable[..., None]] = {
    "skill": skill_cmd,
    "step": step_cmd,
    "next": next_cmd,
    "deck": deck_cmd,
    "status": status_cmd,
    "situation": situation_cmd,
    "list": list_cmd,
    "ls": list_cmd,
    "stats": stats_cmd,
    "patterns": patterns_cmd,
}
