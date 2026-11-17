"""Census file IO: path resolution, validated load, atomic save."""

import json
import os
from pathlib import Path
from typing import Any

from viber.models.schema import Census

DEFAULT_DATA_DIR = Path(".viber") / ".data"
CENSUS_NAME = "viber.json"


class CensusError(Exception):
    """Raised for missing/invalid census files; CLI maps to exit code 1."""


class CensusUsageError(Exception):
    """Raised for invalid command usage; CLI maps to exit code 2."""


def resolve_census_path(census_opt: str | None) -> Path:
    if census_opt:
        return Path(census_opt)
    per_project = Path.cwd() / DEFAULT_DATA_DIR / CENSUS_NAME
    if not per_project.is_file():
        # the seed repo keeps its census at the root; fall back so it works in place
        root_seed = Path.cwd() / CENSUS_NAME
        if root_seed.is_file():
            return root_seed
    return per_project


def load_census(path: Path) -> Census:
    if not path.is_file():
        raise CensusError(f"census not found: {path}")
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CensusError(f"cannot read census: {exc}") from exc
    try:
        return Census.model_validate(raw)
    except Exception as exc:  # pydantic ValidationError
        raise CensusError(f"invalid census: {exc}") from exc


def dump_census(census: Census) -> str:
    payload = census.model_dump(mode="json", by_alias=True)
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def save_census(path: Path, census: Census) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(dump_census(census), encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def census_dict(census: Census) -> dict[str, Any]:
    """Full by-alias dump — the base payload every output layer selects keys from."""
    result: dict[str, Any] = census.model_dump(mode="json", by_alias=True)
    return result
