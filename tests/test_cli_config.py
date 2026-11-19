"""config command family: writes the chain, reads it back, proves wiring."""

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from viber.app import build_app

runner = CliRunner()


@pytest.fixture(scope="module")
def app() -> Any:
    return build_app()


@pytest.fixture()
def project_cfg(tmp_path: Path, monkeypatch: Any) -> Path:
    cfg = tmp_path / "project-config.json"
    monkeypatch.setenv("VIBER_CONFIG", str(cfg))
    return cfg


def call(app: Any, args: list[str]) -> Any:
    return runner.invoke(app, args)


class TestSetGet:
    def test_set_writes_project_layer(self, app: Any, project_cfg: Path) -> None:
        r = call(app, ["config", "set", "profile", "minimal"])
        assert r.exit_code == 0
        assert json.loads(project_cfg.read_text(encoding="utf-8")) == {"profile": "minimal"}

    def test_set_changes_read_output(
        self, app: Any, project_cfg: Path, census_file: Path
    ) -> None:
        call(app, ["config", "set", "profile", "minimal"])
        r = call(app, ["skill", "steering", "-C", str(census_file)])
        assert "description" not in r.output

    def test_get_reports_value_and_source(self, app: Any, project_cfg: Path) -> None:
        project_cfg.write_text('{"telemetry": false}', encoding="utf-8")
        r = call(app, ["config", "get", "telemetry"])
        assert r.exit_code == 0
        assert "false" in r.output and "project" in r.output

    def test_set_user_layer(self, app: Any, tmp_path: Path, monkeypatch: Any) -> None:
        home = tmp_path / "cfg-home"
        monkeypatch.setenv("VIBER_CONFIG_HOME", str(home))
        r = call(app, ["config", "set", "format", "json", "--user"])
        assert r.exit_code == 0
        assert json.loads((home / "config.json").read_text(encoding="utf-8")) == {"format": "json"}

    def test_rejects_non_configurable_key(self, app: Any) -> None:
        r = call(app, ["config", "set", "force", "true"])
        assert r.exit_code == 2

    def test_rejects_bad_bool(self, app: Any, project_cfg: Path) -> None:
        r = call(app, ["config", "set", "telemetry", "maybe"])
        assert r.exit_code == 2
        assert not project_cfg.exists()

    def test_unset_reveals_lower_layer(
        self, app: Any, project_cfg: Path, tmp_path: Path, monkeypatch: Any
    ) -> None:
        home = tmp_path / "home2"
        home.mkdir()
        (home / "config.json").write_text('{"profile": "full"}', encoding="utf-8")
        monkeypatch.setenv("VIBER_CONFIG_HOME", str(home))
        project_cfg.write_text('{"profile": "minimal"}', encoding="utf-8")
        r = call(app, ["config", "unset", "profile"])
        assert r.exit_code == 0
        assert "full" in r.output and "(user)" in r.output


class TestListPath:
    def test_list_json_has_every_key(self, app: Any, project_cfg: Path) -> None:
        r = call(app, ["config", "list", "-f", "json"])
        assert r.exit_code == 0
        rows = json.loads(r.output)["keys"]
        assert {row["key"] for row in rows} == {
            "census",
            "project",
            "profile",
            "format",
            "telemetry",
            "plugins",
        }
        assert all("source" in row and "default" in row for row in rows)  # fmt: skip

    def test_path_lists_layers(self, app: Any, project_cfg: Path) -> None:
        r = call(app, ["config", "path"])
        assert r.exit_code == 0
        assert "absent" in r.output and "plugins" in r.output
