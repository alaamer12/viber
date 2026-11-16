"""Seed round-trip parity: the real viber.json must load, dump, and match exactly;
and the new system must expose everything the legacy CLI exposed (information, not shape)."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from conftest import SEED_PATH
from typer.testing import CliRunner

from viber.app import build_app
from viber.data.store import dump_census, load_census

pytestmark = pytest.mark.skipif(not SEED_PATH.is_file(), reason="seed not present")


@pytest.fixture(scope="module")
def seed_text() -> str:
    return SEED_PATH.read_text(encoding="utf-8")


def test_seed_roundtrip_exact() -> None:
    original = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    census = load_census(SEED_PATH)
    assert json.loads(dump_census(census)) == original


def test_seed_text_byte_identity(seed_text: str) -> None:
    """Not just semantic: indentation, key order and trailing newline match the seed."""
    census = load_census(SEED_PATH)
    assert dump_census(census) == seed_text


def test_seed_counts() -> None:
    census = load_census(SEED_PATH)
    assert len(census.skills) == 42
    assert len(census.lifecycle) == 5
    assert set(census.decks) == {"author", "opensource", "project"}


LEGACY = Path(__file__).parent / "fixtures" / "legacy_viber.py"
_app = build_app()
_cli = CliRunner()


def legacy_json(args: list[str]) -> Any:
    out = subprocess.run([sys.executable, str(LEGACY), *args, "--census", str(SEED_PATH), "--json"],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def new_json(args: list[str]) -> Any:
    r = _cli.invoke(_app, args + ["-P", "full", "-f", "json", "-C", str(SEED_PATH)])
    assert r.exit_code == 0, r.output
    return json.loads(r.output)


_SEED_SKILLS = sorted(json.loads(SEED_PATH.read_text(encoding="utf-8"))["skills"])


@pytest.mark.parametrize("name", _SEED_SKILLS)
def test_skill_full_superset_of_legacy(name: str) -> None:
    old = legacy_json(["skill", name])
    new = new_json(["skill", name])
    assert set(old) <= set(new), set(old) - set(new)
    for key in set(old) & set(new):
        if key != "fit":
            assert old[key] == new[key], f"{name}.{key}"
    old_fit, new_fit = old["fit"], new["fit"]
    assert set(old_fit) <= set(new_fit)
    for key in set(old_fit) & set(new_fit):
        assert old_fit[key] == new_fit[key], f"{name}.fit.{key}"


def test_list_names_superset() -> None:
    old = set(legacy_json(["list"]))
    new = {r["name"] for r in new_json(["list"])["skills"]}
    assert old <= new


def test_status_values_mapped() -> None:
    old = legacy_json(["status"])
    new = new_json(["status"])
    mapping = {"projectPhase": "phase", "currentStep": "step", "totalSkills": "total",
               "blockedSkills": "blocked", "unclassified": "unclassified"}
    for okey, nkey in mapping.items():
        assert old[okey] == new[nkey], okey


def test_deck_values_preserved() -> None:
    for d in ("author", "opensource", "project"):
        old = legacy_json(["deck", d])
        new = new_json(["deck", d])
        assert set(old) <= set(new)
        for key in set(old) & set(new):
            assert old[key] == new[key], f"{d}.{key}"


def test_roster_order_equals_curated_order() -> None:
    """The curated per-step skill lists live in the seed's first commit (pre-serves
    shape); topological order must reproduce them exactly."""
    blob = subprocess.run(["git", "show", "HEAD:viber.json"], cwd=SEED_PATH.parent,
                          capture_output=True, text=True)
    if blob.returncode:
        pytest.skip("no git blob")
    historical = json.loads(blob.stdout)
    for step in historical["lifecycle"]:
        curated = step.get("skills")
        if curated is None:
            continue
        new_roster = [r["name"] for r in new_json(["step", step["step"]])["roster"]
                      if r["status"] != "command"]
        assert [c for c in curated if c in new_roster] == new_roster, step["step"]
