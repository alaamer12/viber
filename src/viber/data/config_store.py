"""Config file IO: layer location, warn-tolerant reads, atomic strict writes.

Reads of a damaged file degrade to "layer ignored" + a warning (the doctrine forbids
hand-editing, so a hard-fail would force exactly that). Writes refuse to damage a
file they cannot parse first.
"""

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from viber.models.config import ViberConfig

PROJECT_REL = Path(".viber") / ".data" / "config.json"
USER_FILE = "config.json"


class ConfigError(Exception):
    """Unparseable write target or refused mutation; CLI maps to exit code 1."""


@dataclass(frozen=True)
class ConfigPaths:
    project: Path
    user: Path
    project_plugins: Path
    user_plugins: Path


def locate(env: Mapping[str, str]) -> ConfigPaths:
    override = env.get("VIBER_CONFIG")
    project = Path(override) if override else Path.cwd() / PROJECT_REL
    home = env.get("VIBER_CONFIG_HOME")
    if home:
        user_dir = Path(home)
    else:
        import typer

        user_dir = Path(typer.get_app_dir("viber"))
    return ConfigPaths(
        project,
        user_dir / USER_FILE,
        Path.cwd() / ".viber" / "plugins",
        user_dir / "plugins",
    )


def load_file(path: Path) -> tuple[ViberConfig | None, list[str]]:
    if not path.is_file():
        return None, []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("root is not a JSON object")
        return ViberConfig.model_validate(raw), []
    except (OSError, ValueError, ValidationError):
        return None, [f"config layer ignored (unreadable): {path}"]


@dataclass(frozen=True)
class Loaded:
    project: ViberConfig | None
    user: ViberConfig | None
    warnings: tuple[str, ...]


def load(env: Mapping[str, str]) -> Loaded:
    paths = locate(env)
    project, w1 = load_file(paths.project)
    user, w2 = load_file(paths.user)
    return Loaded(project=project, user=user, warnings=(*w1, *w2))


def _read_raw(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ConfigError(f"cannot write into unreadable config {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"config root is not a JSON object: {path}")
    return raw


def _atomic_dump(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    os.replace(tmp, path)


def set_value(path: Path, key: str, value: Any) -> None:
    raw = _read_raw(path)
    raw[key] = value
    _atomic_dump(path, raw)


def unset_value(path: Path, key: str) -> bool:
    raw = _read_raw(path)
    if key not in raw:
        return False
    del raw[key]
    _atomic_dump(path, raw)
    return True
