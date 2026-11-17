"""Config store: layer location, warn-tolerant reads, atomic strict writes."""

import json
from pathlib import Path
from typing import Any

import pytest

from viber.data import config_store
from viber.data.config_store import ConfigError


def env_home(tmp_path: Path) -> dict[str, str]:
    return {"VIBER_CONFIG_HOME": str(tmp_path / "home")}


class TestLocate:
    def test_defaults_are_cwd_and_home(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        paths = config_store.locate(env_home(tmp_path))
        assert paths.project == tmp_path / ".viber" / ".data" / "config.json"
        assert paths.user == tmp_path / "home" / "config.json"
        assert paths.project_plugins == tmp_path / ".viber" / "plugins"
        assert paths.user_plugins == tmp_path / "home" / "plugins"

    def test_viber_config_override_wins(self, tmp_path: Path) -> None:
        custom = tmp_path / "elsewhere.json"
        paths = config_store.locate({"VIBER_CONFIG": str(custom), **env_home(tmp_path)})
        assert paths.project == custom


class TestLoad:
    def test_missing_layers_are_silent(self, tmp_path: Path) -> None:
        cfg, warnings = config_store.load_file(tmp_path / "nope.json")
        assert cfg is None and warnings == []

    def test_garbage_warns_and_ignores_layer(self, tmp_path: Path) -> None:
        p = tmp_path / "config.json"
        p.write_text("{oops", encoding="utf-8")
        cfg, warnings = config_store.load_file(p)
        assert cfg is None and len(warnings) == 1 and "ignored" in warnings[0]

    def test_non_object_root_ignored(self, tmp_path: Path) -> None:
        p = tmp_path / "config.json"
        p.write_text("[1, 2]", encoding="utf-8")
        cfg, warnings = config_store.load_file(p)
        assert cfg is None and warnings

    def test_unknown_keys_survive_parse(self, tmp_path: Path) -> None:
        p = tmp_path / "config.json"
        p.write_text('{"profile": "full", "zzz": 7}', encoding="utf-8")
        cfg, _ = config_store.load_file(p)
        assert cfg is not None
        assert "profile" in cfg.model_fields_set and "zzz" in cfg.model_fields_set

    def test_load_walks_both_layers(self, tmp_path: Path) -> None:
        env = {"VIBER_CONFIG": str(tmp_path / "p.json"), **env_home(tmp_path)}
        paths = config_store.locate(env)
        paths.project.write_text('{"profile": "minimal"}', encoding="utf-8")
        loaded = config_store.load(env)
        assert loaded.project is not None and loaded.user is None


class TestWrites:
    def test_set_creates_parents(self, tmp_path: Path) -> None:
        p = tmp_path / "deep" / "deeper" / "config.json"
        config_store.set_value(p, "profile", "full")
        assert json.loads(p.read_text(encoding="utf-8")) == {"profile": "full"}

    def test_set_preserves_unknown_keys_and_order(self, tmp_path: Path) -> None:
        p = tmp_path / "config.json"
        p.write_text('{"zzz": 1, "profile": "minimal"}', encoding="utf-8")
        config_store.set_value(p, "telemetry", False)
        raw: Any = json.loads(p.read_text(encoding="utf-8"))
        assert list(raw) == ["zzz", "profile", "telemetry"]

    def test_atomic_leaves_no_tmp(self, tmp_path: Path) -> None:
        p = tmp_path / "config.json"
        config_store.set_value(p, "plugins", True)
        assert not (tmp_path / "config.json.tmp").exists()

    def test_unset_removes_only_target_key(self, tmp_path: Path) -> None:
        p = tmp_path / "config.json"
        p.write_text('{"profile": "full", "format": "json"}', encoding="utf-8")
        assert config_store.unset_value(p, "profile") is True
        assert json.loads(p.read_text(encoding="utf-8")) == {"format": "json"}
        assert config_store.unset_value(p, "profile") is False

    def test_write_into_garbage_refuses(self, tmp_path: Path) -> None:
        p = tmp_path / "config.json"
        p.write_text("{broken", encoding="utf-8")
        with pytest.raises(ConfigError):
            config_store.set_value(p, "profile", "full")
        assert p.read_text(encoding="utf-8") == "{broken"
