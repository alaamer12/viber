"""Project registry: a short path fingerprint identifies a project, and a
user-level `projects.json` maps id -> location so `viber --project <id>` resumes it
from anywhere.

The fingerprint is a convenience, not a guarantee: it is derived from the directory
path, so a project that moves needs re-linking (`viber project link`). That registry
is the single mutable record — never hand-edited; every mutation is atomic.
"""

import hashlib
import json
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECTS_FILE = "projects.json"
CENSUS_REL = Path(".viber") / ".data" / "viber.json"


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def normalize_dir(dir: Path | str) -> str:
    """Location-stable key: absolute, forward-slashes, lowercase (Windows-safe)."""
    return str(Path(dir).expanduser().resolve()).replace("\\", "/").lower()


def project_id(dir: Path | str) -> str:
    return hashlib.sha256(normalize_dir(dir).encode()).hexdigest()[:12]


def project_dir_for_census(census_path: Path | str) -> Path:
    """The project folder a census file belongs to (walks up out of `.viber/.data`).

    A committed `.viber/.data/viber.json` can be checked out with a `project_id`
    baked from a different machine/path, so the operational id is always derived
    from the real location, not the stored value — branch switches and commits
    cannot make it drift.
    """
    p = Path(census_path)
    return p.parents[2] if p.parent.name == ".data" else p.parent


def id_for_census(census_path: Path | str) -> str:
    return project_id(project_dir_for_census(census_path))


def registry_path(env: Mapping[str, str]) -> Path:
    from viber.data.config_store import locate

    return locate(env).user.parent / PROJECTS_FILE


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    os.replace(tmp, path)


def register_project(
    env: Mapping[str, str], id: str, dir: Path | str, name: str
) -> dict[str, Any]:
    entry = {
        "dir": str(Path(dir)),
        "name": name,
        "created": _today(),
        "last_used": None,
    }
    data = _read(registry_path(env))
    data[id] = entry
    _write(registry_path(env), data)
    return entry


def lookup_project(env: Mapping[str, str], id: str) -> dict[str, Any] | None:
    return _read(registry_path(env)).get(id)


def all_projects(env: Mapping[str, str]) -> dict[str, Any]:
    return _read(registry_path(env))


def unlink_project(env: Mapping[str, str], id: str) -> bool:
    data = _read(registry_path(env))
    if id not in data:
        return False
    del data[id]
    _write(registry_path(env), data)
    return True


def touch_used(env: Mapping[str, str], id: str) -> None:
    data = _read(registry_path(env))
    if id in data:
        data[id]["last_used"] = _today()
        _write(registry_path(env), data)
