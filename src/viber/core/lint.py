"""Lint: cross-checks over the validated census. Schema/enum validity is already
guaranteed by pydantic at load; what remains is referential integrity, disk drift,
the conflicts that need a human decision, and — on --remote — deck git remotes.
"""

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any, Final

from viber.core.census_ops import entry_of, rels
from viber.core.mutations import skill_dir_on_disk
from viber.data.frontmatter import parse_frontmatter
from viber.models.domain import Finding, Severity
from viber.models.limits import LIMITS
from viber.models.schema import Census


def run_limit_checks(census: Census) -> list[Finding]:
    """Caps never reject an already-written census at load (that would brick every
    command and force the forbidden hand-edit); they surface here as errors with the
    cataloged identity, the received count, and the recovery line."""
    findings: list[Finding] = []
    for name, entry in census.skills.items():
        findings += _over_chars("name", name, f"skill '{name}'")
        for field in ("description", "path", "version"):
            value = getattr(entry, field, None)
            if value:
                findings += _over_chars(field, str(value), f"{name}.{field}")
        findings += _over_items("use_cases", entry.use_cases, f"{name}.use_cases")
        for item in entry.use_cases:
            findings += _over_chars("use_case", item, f"{name}.use_cases[]")
        findings += _over_items("blockers", entry.fit.blockers, f"{name}.fit.blockers")
        for item in entry.fit.blockers:
            findings += _over_chars("blocker", item, f"{name}.fit.blockers[]")
        findings += _over_items("serves", entry.fit.serves, f"{name}.fit.serves")
        findings += _over_items("produces", entry.fit.produces, f"{name}.fit.produces")
        findings += _over_items("consumes", entry.fit.consumes, f"{name}.fit.consumes")
        for art in entry.fit.produces + entry.fit.consumes:
            findings += _over_chars("artifact", str(art), f"{name}.fit.artifact")
        findings += _over_items("history", entry.history, f"{name}.history")
        for record in entry.history:
            findings += _over_chars("event", str(record.get("event", "")), f"{name}.history[]")
        for field in ("role", "when", "doing", "why"):
            value = getattr(entry.fit, field, "")
            if value:
                findings += _over_chars(field, str(value), f"{name}.fit.{field}")
        for kind in ("after", "before", "with"):
            rel_list = rels(entry, kind)
            findings += _over_items(kind, rel_list, f"{name}.fit.{kind}")
            for rel in rel_list:
                findings += _over_chars("hint", rel.hint, f"{name}.fit.{kind}[{rel.skill}].hint")
                findings += _over_chars(
                    "long_hint", rel.long_hint, f"{name}.fit.{kind}[{rel.skill}].long_hint"
                )
    findings += _over_items("skills", list(census.skills), "census.skills")
    findings += _over_items("unclassified", list(census.unclassified), "census.unclassified")
    findings += _over_items("lifecycle", list(census.lifecycle), "census.lifecycle")
    for step in census.lifecycle:
        findings += _over_chars("step_name", step.step, f"step '{step.step}'")
        findings += _over_chars("goal", step.goal, f"step '{step.step}'.goal")
        findings += _over_items("needs", step.needs, f"step '{step.step}'.needs")
        for need in step.needs:
            findings += _over_chars("artifact", str(need), f"step '{step.step}'.needs[]")
        findings += _over_items(
            "possible_skills", step.possible_skills, f"step '{step.step}'.possible_skills"
        )
        findings += _over_items("commands", step.commands, f"step '{step.step}'.commands")
    for dname, deck in census.decks.items():
        findings += _over_chars("deck_name", str(deck.name or dname), f"deck '{dname}'.name")
        findings += _over_chars("registry", deck.registry, f"deck '{dname}'.registry")
        findings += _over_chars("deck_description", deck.description, f"deck '{dname}'.description")
        findings += _over_items("deck.skills", deck.skills, f"deck '{dname}'.skills")
    findings += _over_items("history", census.history, "census.history")
    for record in census.history:
        findings += _over_chars("event", str(record.get("event", "")), "census.history[]")
    for field in ("name", "version", "created", "createdBy"):
        value = getattr(census, field, "")
        if value:
            findings += _over_chars(field, str(value), f"census.{field}")
    return findings


def _over_chars(field: str, value: str, where: str) -> list[Finding]:
    lim = LIMITS[field]
    if len(value) > lim.cap:
        return [Finding(Severity.ERROR, "limit-violation", where, lim.message(len(value)))]
    return []


def _over_items(field: str, values: list[object] | object, where: str) -> list[Finding]:
    lim = LIMITS[field]
    if len(values) > lim.cap:  # type: ignore[arg-type]
        return [Finding(Severity.ERROR, "limit-violation", where, lim.message(len(values)))]  # type: ignore[arg-type]
    return []

RunGit = Callable[[list[str], str], tuple[int, str]]

_GIT_TIMEOUT: Final = 15


def _default_run_git(args: list[str], cwd: str) -> tuple[int, str]:
    try:
        res = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=_GIT_TIMEOUT
        )
        return res.returncode, res.stdout
    except (OSError, subprocess.TimeoutExpired):
        return 128, ""


def _parse_symref_head(out: str) -> tuple[str, str] | None:
    """From `ls-remote --symref origin HEAD`: (branch, upstream sha)."""
    branch = sha = ""
    for line in out.splitlines():
        if line.startswith("ref:"):
            _, _, rest = line.partition("refs/heads/")
            branch = rest.split()[0] if rest else ""
        elif "\tHEAD" in line:
            sha = line.split("\t")[0].strip()
    return (branch, sha) if branch and sha else None


def check_deck_remotes(
    census: Census, census_dir: Path, run_git: RunGit = _default_run_git
) -> list[Finding]:
    """Opt-in network truth: for decks declaring a remote whose registry IS a local
    clone, compare the clone HEAD with upstream HEAD. Offline or non-clone registries
    become warnings, never failures — a missing network must not look like a broken
    census, and pointer registries (.viber/registry.md, marketplace) cannot be checked."""
    findings: list[Finding] = []

    def warn(check: str, subject: str, detail: str) -> None:
        findings.append(Finding(Severity.WARNING, check, subject, detail))

    for name, deck in census.decks.items():
        if not deck.remote:
            continue
        reg = Path(deck.registry or "")
        if not reg.is_absolute():
            reg = census_dir / reg
        if reg.suffix or not reg.is_dir():
            warn(
                "remote-no-clone",
                name,
                f"declares remote {deck.remote} but its registry "
                f"'{deck.registry}' is not a local clone directory — nothing to check",
            )
            continue
        if run_git(["rev-parse", "--git-dir"], str(reg))[0] != 0:
            warn("remote-no-clone", name, f"registry '{deck.registry}' is not a git repository")
            continue
        code, out = run_git(["ls-remote", "--symref", "origin", "HEAD"], str(reg))
        parsed = _parse_symref_head(out) if code == 0 else None
        if parsed is None:
            warn(
                "remote-unreachable",
                name,
                "could not read origin HEAD (offline or no remote configured) "
                "— upstream state unknown",
            )
            continue
        branch, up_sha = parsed
        local = run_git(["rev-parse", "HEAD"], str(reg))[1].strip()
        if local and local != up_sha:
            warn(
                "remote-differs",
                name,
                f"clone at {local[:8]} differs from origin/{branch} at "
                f"{up_sha[:8]} — git pull in {reg}, then: viber refresh --all",
            )
    return findings


def run_lint(
    census: Census,
    census_path: Path,
    remote: bool = False,
    run_git: RunGit = _default_run_git,
) -> list[Finding]:
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

    if remote:
        findings.extend(check_deck_remotes(census, census_path.parent, run_git))

    findings.extend(run_limit_checks(census))
    return findings


def summarize(findings: list[Finding]) -> dict[str, int]:
    return {
        "errors": sum(1 for f in findings if f.severity is Severity.ERROR),
        "warnings": sum(1 for f in findings if f.severity is Severity.WARNING),
        "questions": sum(1 for f in findings if f.severity is Severity.QUESTION),
    }
