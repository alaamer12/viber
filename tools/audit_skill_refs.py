"""Stale-skill-reference detector.

A Skill that is renamed or absorbed into another leaves its old name behind in
prose — diagrams, lifecycle docs, reference tables — long after the seed has
moved on. This tool finds those contradictions against the seed (the single
source of truth for which Skills exist) and can rewrite them to the current name.

The retired-name map is DERIVED, never hard-coded:

  * ``fit.role`` declarations — "Formerly type-up." / "Absorbs former styleup
    skill." — name the old Skill explicitly.
  * For a Skill that declares a former name, the single-token hyphenated entries
    in its description's ``Triggers:`` list that are not themselves live Skills
    are retired aliases (``style-up``, ``tier-up``). The hyphen-or-former guard
    keeps generic one-word triggers from being mistaken for Skill names.

Scope mirrors the command-surface tripwire: root README/PIPELINE/USAGE plus every
``.md`` and ``.mmd`` under ``docs/`` and ``skills/``. The seed itself, this tool,
and the tests are out of scope. ``docs/bugs`` incident reproductions quote stale
names on purpose, so only their ``## Resolution`` section is guidance. A Skill
naming its OWN former name inside its own directory is self-documentation, not a
stale reference, and is left alone.

Usage:
    python tools/audit_skill_refs.py            # report; exit 1 if any found
    python tools/audit_skill_refs.py --fix      # rewrite retired -> current
    python tools/audit_skill_refs.py --root P   # audit another checkout
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "viber.json"

FORMER = re.compile(r"(?:Formerly|Absorbs former)\s+([a-z0-9][a-z0-9-]*)")
TRIGGERS = re.compile(r"Triggers:\s*(.*)")
ALIAS = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
ROOT_DOCS = ("README.md", "PIPELINE.md", "USAGE.md")


def load_skills(seed_path: Path) -> dict:
    return json.loads(seed_path.read_text(encoding="utf-8")).get("skills", {})


def derive_retired(skills: dict) -> dict[str, str]:
    """Map each retired Skill name/alias to the live Skill that absorbed it."""
    valid = set(skills)
    retired: dict[str, str] = {}
    for name, entry in skills.items():
        role = (entry.get("fit") or {}).get("role") or ""
        formers = FORMER.findall(role)
        if not formers:
            continue
        for former in formers:
            retired[former] = name
        seg = TRIGGERS.search(entry.get("description") or "")
        if seg:
            for raw in seg.group(1).split(","):
                tok = raw.strip().rstrip(".").strip()
                if tok in valid or not ALIAS.fullmatch(tok):
                    continue
                if "-" in tok or tok in formers:
                    retired[tok] = name
    return retired


def skill_owner(path: Path, root: Path) -> str | None:
    """The Skill whose directory contains path, if any (skills/<name>/...)."""
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) >= 2 and parts[0] == "skills":
        return parts[1]
    return None


def sources(root: Path) -> list[Path]:
    found: list[Path] = []
    for name in ROOT_DOCS:
        p = root / name
        if p.is_file():
            found.append(p)
    for sub in ("docs", "skills"):
        base = root / sub
        if base.is_dir():
            found += sorted(base.rglob("*.md"))
            found += sorted(base.rglob("*.mmd"))
    return found


def _boundary(name: str) -> re.Pattern:
    return re.compile(r"(?<![a-z0-9-])" + re.escape(name) + r"(?![a-z0-9-])", re.IGNORECASE)


def _guidance(text: str, path: Path, root: Path) -> str:
    if path.parent == root / "docs" / "bugs":
        return text.partition("## Resolution\n")[2]
    return text


def scan(root: Path, retired: dict[str, str]) -> list[tuple[str, int, str, str]]:
    """Return (relpath, lineno, retired, current) for every stale reference."""
    findings: list[tuple[str, int, str, str]] = []
    patterns = {r: _boundary(r) for r in retired}
    for path in sources(root):
        owner = skill_owner(path, root)
        applicable = {r: c for r, c in retired.items() if c != owner}
        if not applicable:
            continue
        text = _guidance(path.read_text(encoding="utf-8"), path, root)
        rel = path.relative_to(root).as_posix()
        for lineno, line in enumerate(text.splitlines(), 1):
            for r, pat in patterns.items():
                if r in applicable and pat.search(line):
                    findings.append((rel, lineno, r, applicable[r]))
    return sorted(findings)


def _replace(text: str, applicable: dict[str, str]) -> str:
    for r, c in applicable.items():
        text = _boundary(r).sub(c, text)
    return text


def fix(root: Path, retired: dict[str, str]) -> list[str]:
    changed: list[str] = []
    for path in sources(root):
        owner = skill_owner(path, root)
        applicable = {r: c for r, c in retired.items() if c != owner}
        if not applicable:
            continue
        text = path.read_text(encoding="utf-8")
        if path.parent == root / "docs" / "bugs":
            head, sep, tail = text.partition("## Resolution\n")
            new = head + sep + _replace(tail, applicable)
        else:
            new = _replace(text, applicable)
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed.append(path.relative_to(root).as_posix())
    return changed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Find (and optionally fix) stale Skill references.")
    ap.add_argument("--fix", action="store_true", help="rewrite retired names to the current Skill")
    ap.add_argument("--root", type=Path, default=ROOT, help="checkout to audit (default: this repo)")
    args = ap.parse_args(argv)
    root = args.root.resolve()

    retired = derive_retired(load_skills(root / "viber.json"))
    if args.fix:
        changed = fix(root, retired)
        for rel in changed:
            print(f"fixed: {rel}")

    findings = scan(root, retired)
    if findings:
        print("STALE SKILL REFERENCES")
        for rel, lineno, r, c in findings:
            print(f"  {rel}:{lineno}: '{r}' -> '{c}'")
        print(f"{len(findings)} stale reference(s); {len(retired)} retired name(s) tracked.")
        return 1
    print(f"OK: no stale skill references ({len(retired)} retired names tracked).")
    return 0


if __name__ == "__main__":
    sys.exit(main())