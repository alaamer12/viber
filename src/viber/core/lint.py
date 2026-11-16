"""Lint: cross-checks over the validated census. Schema/enum validity is already
guaranteed by pydantic at load; what remains is referential integrity, disk drift,
and the conflicts that need a human decision."""

from pathlib import Path
from typing import Any

from viber.core.census_ops import entry_of, rels
from viber.core.mutations import skill_dir_on_disk
from viber.data.frontmatter import parse_frontmatter
from viber.models.domain import Finding, Severity
from viber.models.schema import Census


def run_lint(census: Census, census_path: Path) -> list[Finding]:
    findings: list[Finding] = []

    def add(
        severity: Severity, check: str, subject: str, detail: str, question: str | None = None
    ) -> None:
        findings.append(
            Finding(
                severity=severity, check=check, subject=subject, detail=detail, question=question
            )
        )

    step_names = {s.step for s in census.lifecycle}

    for name, entry in census.skills.items():
        if entry.deck not in census.decks:
            add(Severity.ERROR, "deck", name, f"deck '{entry.deck}' not defined")
        elif name not in census.decks[entry.deck].skills:
            add(
                Severity.WARNING,
                "membership",
                name,
                f"claims deck '{entry.deck}' but not in its skills list",
            )
        in_decks = [d for d, dv in census.decks.items() if name in dv.skills]
        if len(in_decks) > 1:
            add(
                Severity.QUESTION,
                "deck-conflict",
                name,
                f"present in multiple decks: {', '.join(in_decks)}",
                question=f"'{name}' is claimed by decks {in_decks} — versions or sources may "
                f"differ. Ask the user which deck wins, then record it: set {name} deck <chosen>",
            )
        for kind in ("after", "before", "with"):
            for rel in rels(entry, kind):
                if rel.skill not in census.skills:
                    add(
                        Severity.ERROR,
                        "dangling-relation",
                        name,
                        f"{kind} -> '{rel.skill}' not in census",
                    )
        for s in entry.fit.serves:
            if s not in step_names:
                add(Severity.ERROR, "dangling-serves", name, f"serves unknown step '{s}'")
        if entry.path is None:
            if not entry.fit.blockers:
                add(Severity.WARNING, "null-path", name, "no path and no blockers recorded")
        else:
            skill_dir = skill_dir_on_disk(census, census_path, entry)
            if skill_dir is None or not (skill_dir / "SKILL.md").is_file():
                add(Severity.ERROR, "broken-path", name, f"SKILL.md not found at {skill_dir}")
            else:
                disk = parse_frontmatter(skill_dir / "SKILL.md").get("version")
                if disk and entry.version and disk != entry.version:
                    add(
                        Severity.WARNING,
                        "version-drift",
                        name,
                        f"census says v{entry.version}, disk says v{disk} — run: refresh {name}",
                    )

    for step in census.lifecycle:
        for c in step.commands:
            if entry_of(census, c) is None:
                add(
                    Severity.WARNING,
                    "command-missing",
                    step.step,
                    f"command '{c}' not registered as skill",
                )
        for cand in step.possible_skills:
            if cand not in census.skills:
                add(
                    Severity.WARNING,
                    "candidate-not-installed",
                    step.step,
                    f"'{cand}' declared possible but absent from census — "
                    f"agent should suggest installing it",
                )

    for u in census.unclassified:
        uname: Any = u.get("name") if isinstance(u, dict) else u
        if uname in census.skills or any(uname in dv.skills for dv in census.decks.values()):
            add(
                Severity.WARNING,
                "unclassified-overlap",
                str(uname),
                "listed unclassified but also classified",
            )

    return findings


def summarize(findings: list[Finding]) -> dict[str, int]:
    return {
        "errors": sum(1 for f in findings if f.severity is Severity.ERROR),
        "warnings": sum(1 for f in findings if f.severity is Severity.WARNING),
        "questions": sum(1 for f in findings if f.severity is Severity.QUESTION),
    }
