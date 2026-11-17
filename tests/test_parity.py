"""Seed round-trip parity: the real viber.json must load, dump, and match exactly —
byte-for-byte — and the topological roster must reproduce the curated seed order."""

import json
import subprocess
from typing import Any

import pytest
from conftest import SEED_PATH
from typer.testing import CliRunner

from viber.app import build_app
from viber.data.store import dump_census, load_census

pytestmark = pytest.mark.skipif(not SEED_PATH.is_file(), reason="seed not present")

_app = build_app()
_cli = CliRunner()


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


def _new_json(args: list[str]) -> Any:
    r = _cli.invoke(_app, args + ["-P", "full", "-f", "json", "-C", str(SEED_PATH)])
    assert r.exit_code == 0, r.output
    return json.loads(r.output)


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
        new_roster = [r["name"] for r in _new_json(["step", step["step"]])["roster"]
                      if r["status"] != "command"]
        assert [c for c in curated if c in new_roster] == new_roster, step["step"]
