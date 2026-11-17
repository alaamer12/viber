"""Precedence matrix for the pure resolver: flag > env > project > user > default,
plus the warning-and-fallthrough policy and the flag-only-keys guard."""

import pytest

from viber.core.settings import CHAIN, DEFAULTS, Flags, resolve
from viber.models.config import ViberConfig
from viber.models.domain import ConfigKey, FormatKind, Profile, Source


def cfg(**kv: object) -> ViberConfig:
    return ViberConfig.model_validate(dict(kv))


def test_every_config_key_has_a_chain_row() -> None:
    assert set(CHAIN) == {k.value for k in ConfigKey}


def test_flag_only_keys_are_not_chain_keys() -> None:
    for unconfigurable in ("out", "force", "include", "exclude"):
        assert unconfigurable not in CHAIN


class TestLayerWins:
    def test_profile_default(self) -> None:
        s = resolve(Flags(), {}, None, None)
        assert s.profile is Profile.STANDARD and s.sources["profile"] is Source.DEFAULT

    def test_profile_user_layer(self) -> None:
        s = resolve(Flags(), {}, None, cfg(profile="full"))
        assert s.profile is Profile.FULL and s.sources["profile"] is Source.USER

    def test_profile_project_shadows_user(self) -> None:
        s = resolve(Flags(), {}, cfg(profile="minimal"), cfg(profile="full"))
        assert s.profile is Profile.MINIMAL and s.sources["profile"] is Source.PROJECT

    def test_profile_env_shadows_files(self) -> None:
        s = resolve(Flags(), {"VIBER_PROFILE": "full"}, cfg(profile="minimal"), None)
        assert s.profile is Profile.FULL and s.sources["profile"] is Source.ENV

    def test_profile_flag_shows_all(self) -> None:
        s = resolve(
            Flags(profile=Profile.MINIMAL), {"VIBER_PROFILE": "full"}, cfg(profile="full"), None
        )
        assert s.profile is Profile.MINIMAL and s.sources["profile"] is Source.FLAG

    def test_census_chain(self) -> None:
        env = {"VIBER_CENSUS": "/env.json"}
        s = resolve(Flags(census="/flag.json"), env, cfg(census="/p.json"), cfg(census="/u.json"))
        assert s.census == "/flag.json"
        s = resolve(Flags(), env, cfg(census="/p.json"), None)
        assert s.census == "/env.json" and s.sources["census"] is Source.ENV
        s = resolve(Flags(), {}, cfg(census="/p.json"), None)
        assert s.census == "/p.json" and s.sources["census"] is Source.PROJECT

    def test_format_chain(self) -> None:
        s = resolve(Flags(fmt=FormatKind.JSON), {"VIBER_FORMAT": "txt"}, cfg(format="json"), None)
        assert s.format is FormatKind.JSON and s.sources["format"] is Source.FLAG
        s = resolve(Flags(), {}, None, cfg(format="json"))
        assert s.format is FormatKind.JSON and s.sources["format"] is Source.USER

    def test_telemetry_has_no_flag_layer(self) -> None:
        assert Source.FLAG not in CHAIN["telemetry"]
        s = resolve(Flags(), {"VIBER_TELEMETRY": "0"}, cfg(telemetry=True), None)
        assert s.telemetry is False and s.sources["telemetry"] is Source.ENV

    def test_plugins_env(self) -> None:
        s = resolve(Flags(), {"VIBER_PLUGINS": "true"}, None, None)
        assert s.plugins is True and s.sources["plugins"] is Source.ENV


class TestFallthroughAndShadowing:
    def test_empty_project_file_does_not_shadow_user(self) -> None:
        s = resolve(Flags(), {}, cfg(), cfg(profile="full"))
        assert s.profile is Profile.FULL and s.sources["profile"] is Source.USER

    def test_bad_env_value_warns_and_next_layer_wins(self) -> None:
        s = resolve(Flags(), {"VIBER_PROFILE": "bogus"}, cfg(profile="full"), None)
        assert s.profile is Profile.FULL
        assert any("bogus" in w for w in s.warnings)

    def test_bad_file_value_warns_and_default_wins(self) -> None:
        s = resolve(Flags(), {}, cfg(format="loud"), None)
        assert s.format is FormatKind.TXT
        assert any("loud" in w for w in s.warnings)

    def test_bad_bool_warns_and_default_wins(self) -> None:
        s = resolve(Flags(), {"VIBER_TELEMETRY": "maybe"}, None, None)
        assert s.telemetry is True and s.warnings

    @pytest.mark.parametrize(
        ("raw", "want"),
        [("1", True), ("yes", True), ("ON", True), ("0", False), ("No", False), ("false", False)],
    )
    def test_bool_parse_table(self, raw: str, want: bool) -> None:
        s = resolve(Flags(), {"VIBER_TELEMETRY": raw}, None, None)
        assert s.telemetry is want

    def test_empty_census_env_is_absent_not_a_path(self) -> None:
        s = resolve(Flags(), {"VIBER_CENSUS": ""}, None, None)
        assert s.census is None and s.sources["census"] is Source.DEFAULT


class TestFlagOnlyKeysAndDefaults:
    def test_out_force_ignore_env_and_files(self) -> None:
        s = resolve(Flags(), {"VIBER_OUT": "x.json"}, cfg(force=True, out="x.json"), None)
        assert s.out is None and s.force is False

    def test_include_csv_trimmed(self) -> None:
        s = resolve(Flags(include=" fit , history "), {}, None, None)
        assert s.include == ("fit", "history")

    def test_defaults_equal_legacy_literal_values(self) -> None:
        s = resolve(Flags(), {}, None, None)
        assert s.profile is Profile.STANDARD
        assert s.format is FormatKind.TXT
        assert s.telemetry is True
        assert s.plugins is False
        assert s.census is None
        assert s.force is False
        assert s.include == () and s.exclude == ()
        assert DEFAULTS["profile"] is Profile.STANDARD
