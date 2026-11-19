import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from viber.app import build_app
from viber.data.store import load_census

runner = CliRunner()


def install_skill(root: Path, name: str, description: str = "A useful skill.") -> Path:
    directory = root / name
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {name}\nversion: '1.0.0'\ndescription: {description}\n---\n",
        encoding="utf-8",
    )
    return directory.resolve()


@pytest.fixture
def seed(tmp_path: Path, mini: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> Path:
    from viber.core import bootstrap

    mini["projectPhase"] = "PP"
    mini["history"] = [{"date": "2026-01-01", "event": "old project"}]
    mini["skills"]["idea-md"]["fit"]["phase"] = "PP"
    mini["skills"]["idea-md"]["fit"]["doing"] = "Write the concept."
    mini["skills"]["idea-md"]["future_key"] = {"keep": True}
    path = tmp_path / "seed.json"
    path.write_text(json.dumps(mini), encoding="utf-8")
    monkeypatch.setattr(bootstrap, "load_seed", lambda: (load_census(path), path))
    return path


def test_init_command_exists() -> None:
    result = runner.invoke(build_app(), ["init", "--help"])
    assert result.exit_code == 0, result.output
    assert "--skills-root" in result.output


def test_init_resolves_paths_and_resets_only_project_state(
    tmp_path: Path, seed: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    installed = install_skill(tmp_path / "installed", "idea-md")
    target = tmp_path / "project" / ".viber" / ".data" / "viber.json"
    before = seed.read_bytes()
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(build_app(), [
        "init", "--skills-root", str(installed.parent), "-C", str(target), "-f", "json",
    ])
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["summary"]["errors"] == 0
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["skills"]["idea-md"]["path"] == installed.as_posix()
    assert data["skills"]["idea-md"]["fit"]["doing"] == "Write the concept."
    assert data["skills"]["idea-md"]["future_key"] == {"keep": True}
    assert "phase" not in data["skills"]["idea-md"]["fit"]
    assert data["projectPhase"] == "DR"
    assert data["history"] == []
    assert all(not entry["history"] for entry in data["skills"].values())
    assert data["skills"]["steering"]["path"] is None
    assert data["skills"]["steering"]["fit"]["blockers"]
    assert seed.read_bytes() == before
    lint = runner.invoke(build_app(), ["lint", "-C", str(target), "-f", "json"])
    assert lint.exit_code == 0, lint.output
    assert json.loads(lint.output)["summary"]["errors"] == 0


def test_init_default_never_overwrites_root_seed(
    tmp_path: Path, seed: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    root_seed = tmp_path / "viber.json"
    root_seed.write_bytes(seed.read_bytes())
    before = root_seed.read_bytes()
    result = runner.invoke(build_app(), ["init", "-nr"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".viber" / ".data" / "viber.json").is_file()
    assert root_seed.read_bytes() == before


def test_init_refuses_existing_census_even_with_force(tmp_path: Path, seed: Path) -> None:
    target = tmp_path / "existing.json"
    target.write_text("do not replace", encoding="utf-8")
    result = runner.invoke(build_app(), ["init", "-C", str(target), "--force", "-nr"])
    assert result.exit_code == 1, result.output
    assert "overwrite" in result.output
    assert target.read_text(encoding="utf-8") == "do not replace"


def test_init_conflicting_roots_write_nothing(tmp_path: Path, seed: Path) -> None:
    first = install_skill(tmp_path / "first", "idea-md")
    second = install_skill(tmp_path / "second", "idea-md")
    target = tmp_path / "new" / "viber.json"
    result = runner.invoke(build_app(), [
        "init", "--skills-root", str(first.parent), "--skills-root", str(second.parent),
        "-C", str(target), "-nr",
    ])
    assert result.exit_code == 1, result.output
    assert "conflict" in result.output.lower()
    assert not target.exists()


@pytest.mark.parametrize("target_kind", ["census", "seed"])
def test_init_report_cannot_replace_data(tmp_path: Path, seed: Path, target_kind: str) -> None:
    target = tmp_path / "new.json"
    before = seed.read_bytes()
    report = target if target_kind == "census" else seed
    result = runner.invoke(build_app(), [
        "init", "-C", str(target), "-o", str(report), "--force", "-nr",
    ])
    assert result.exit_code != 0
    assert not target.exists()
    assert seed.read_bytes() == before


def test_init_report_cannot_replace_packaged_seed(
    tmp_path: Path, seed: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from viber.cli import init_cmd
    from viber.core import bootstrap

    monkeypatch.setattr(bootstrap, "load_seed", lambda: (load_census(seed), None))
    monkeypatch.setattr(init_cmd, "files", lambda _: seed.parent, raising=False)
    target = tmp_path / "new.json"
    before = seed.read_bytes()
    result = runner.invoke(build_app(), [
        "init", "-C", str(target), "-o", str(seed), "--force", "-nr",
    ])
    assert result.exit_code == 1, result.output
    assert seed.read_bytes() == before
    assert not target.exists()


def test_registry_exports_fallbacks_without_a_census(tmp_path: Path) -> None:
    root = tmp_path / "deck"
    install_skill(root, "sample", "'Purpose | <safe>. Use when writing code.'")
    result = runner.invoke(build_app(), ["registry", "--skills-root", str(root), "-f", "json"])
    assert result.exit_code == 0, result.output
    row = json.loads(result.output)["skills"][0]
    assert row["when_to_use"] == "Use when writing code."
    assert row["name"] == "sample"
    assert row["source"] == (root / "sample").resolve().as_posix()
    output = tmp_path / "registry.md"
    written = runner.invoke(
        build_app(), ["registry", "--skills-root", str(root), "-o", str(output)]
    )
    assert written.exit_code == 0, written.output
    text = output.read_text(encoding="utf-8")
    assert "When to use" in text and "Use when writing code." in text
    assert "<safe>" not in text
    assert "\\|" in text or "&#124;" in text


def test_registry_reports_conflicts_and_deduplicates_identical_roots(tmp_path: Path) -> None:
    first = install_skill(tmp_path / "first", "sample")
    second = install_skill(tmp_path / "second", "sample")
    result = runner.invoke(build_app(), [
        "registry", "--skills-root", str(first.parent), "--skills-root", str(first.parent),
        "--skills-root", str(second.parent), "-f", "json",
    ])
    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert len(payload["skills"]) == 2
    assert payload["conflicts"][0]["name"] == "sample"


@pytest.mark.parametrize("layer", ["environment", "config"])
def test_init_uses_configured_destination(
    tmp_path: Path, seed: Path, monkeypatch: pytest.MonkeyPatch, layer: str,
) -> None:
    target = tmp_path / "configured" / "viber.json"
    if layer == "environment":
        monkeypatch.setenv("VIBER_CENSUS", str(target))
    else:
        config = tmp_path / "settings.json"
        config.write_text(json.dumps({"census": str(target)}), encoding="utf-8")
        monkeypatch.setenv("VIBER_CONFIG", str(config))
    result = runner.invoke(build_app(), ["init", "-nr"])
    assert result.exit_code == 0, result.output
    assert target.is_file()


def test_exclusive_creation_preserves_concurrent_winner(tmp_path: Path, seed: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    from viber.core.bootstrap import create_census
    from viber.data.store import CensusError

    target = tmp_path / "race.json"
    census = load_census(seed)

    def create() -> bool:
        try:
            create_census(target, census)
            return True
        except CensusError as exc:
            assert "overwrite" in str(exc)
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: create(), range(2)))
    assert sorted(results) == [False, True]
    assert load_census(target) == census
    assert not list(tmp_path.glob(".viber-init-*.tmp"))


def test_init_deduplicates_symlink_roots(tmp_path: Path, seed: Path) -> None:
    installed = install_skill(tmp_path / "installed", "idea-md")
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(installed.parent, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    target = tmp_path / "new.json"
    result = runner.invoke(build_app(), [
        "init", "--skills-root", str(installed.parent), "--skills-root", str(alias),
        "-C", str(target), "-f", "json",
    ])
    assert result.exit_code == 0, result.output
    assert load_census(target).skills["idea-md"].path == installed.as_posix()


def test_init_refuses_dangling_destination_symlink(tmp_path: Path, seed: Path) -> None:
    target = tmp_path / "link.json"
    missing = tmp_path / "missing.json"
    try:
        target.symlink_to(missing)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    result = runner.invoke(build_app(), ["init", "-C", str(target), "-nr"])
    assert result.exit_code == 1, result.output
    assert target.is_symlink() and not missing.exists()


def test_refresh_all_rejects_invalid_yaml_without_saving(tmp_path: Path, seed: Path) -> None:
    data = load_census(seed)
    directory = install_skill(tmp_path / "installed", "idea-md")
    (directory / "SKILL.md").write_text("---\nname: [invalid\n---\n", encoding="utf-8")
    data.skills["idea-md"].path = str(directory)
    seed.write_text(data.model_dump_json(by_alias=True), encoding="utf-8")
    before = seed.read_bytes()
    result = runner.invoke(build_app(), ["refresh", "--all", "-C", str(seed), "-nr"])
    assert result.exit_code == 1, result.output
    assert "invalid YAML" in result.output
    assert seed.read_bytes() == before


def test_registry_refuses_invalid_root(tmp_path: Path) -> None:
    result = runner.invoke(build_app(), ["registry", "--skills-root", str(tmp_path / "absent")])
    assert result.exit_code != 0
    assert "skills root" in result.output.lower()
