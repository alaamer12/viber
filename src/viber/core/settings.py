"""Pure precedence resolution: flag > env > project config > user config > default.

No IO, no printing: Globals feeds Flags + os.environ + the loaded config models and
prints the returned warnings. CHAIN is the single visible source of which layers a
key may come from, and it generates the config command's writable-key whitelist —
keys outside it (out/force/include/exclude) are flag-only by design: a global force
disarms the overwrite guard, a global out hijacks stdout, a global include would
ProfileError unrelated commands.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from viber.models.config import ViberConfig
from viber.models.domain import ConfigKey, FormatKind, Profile, Source

ENV_NAMES: Final[dict[str, str]] = {
    "census": "VIBER_CENSUS",
    "project": "VIBER_PROJECT",
    "profile": "VIBER_PROFILE",
    "format": "VIBER_FORMAT",
    "telemetry": "VIBER_TELEMETRY",
    "plugins": "VIBER_PLUGINS",
}

CHAIN: Final[dict[str, tuple[Source, ...]]] = {
    "census": (Source.FLAG, Source.ENV, Source.PROJECT, Source.USER),
    "project": (Source.FLAG, Source.ENV, Source.USER),
    "profile": (Source.FLAG, Source.ENV, Source.PROJECT, Source.USER),
    "format": (Source.FLAG, Source.ENV, Source.PROJECT, Source.USER),
    "telemetry": (Source.ENV, Source.PROJECT, Source.USER),
    "plugins": (Source.ENV, Source.PROJECT, Source.USER),
}

DEFAULTS: Final[dict[str, Any]] = {
    "census": None,
    "project": None,
    "profile": Profile.STANDARD,
    "format": FormatKind.TXT,
    "telemetry": True,
    "plugins": False,
}

_TRUTHY: Final = frozenset({"1", "true", "yes", "on"})
_FALSY: Final = frozenset({"0", "false", "no", "off"})


def parse_bool(raw: Any) -> bool | None:
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip().lower()
    if text in _TRUTHY:
        return True
    if text in _FALSY:
        return False
    return None


@dataclass(frozen=True)
class Flags:
    """What typer handed the handler, sentinels intact (None = not passed)."""

    census: str | None = None
    project: str | None = None
    fmt: FormatKind | None = None
    out: Path | None = None
    force: bool | None = None
    profile: Profile | None = None
    include: str | None = None
    exclude: str | None = None


@dataclass(frozen=True)
class Settings:
    census: str | None
    project: str | None
    format: FormatKind
    out: Path | None
    force: bool
    profile: Profile
    include: tuple[str, ...]
    exclude: tuple[str, ...]
    telemetry: bool
    plugins: bool
    sources: dict[str, Source]
    warnings: tuple[str, ...]


def _coerce(key: str, raw: Any, where: str, warnings: list[str]) -> Any:
    if key == "profile":
        try:
            return Profile(str(raw))
        except ValueError:
            warnings.append(f"invalid profile {raw!r} from {where} — layer skipped")
            return None
    if key == "format":
        try:
            return FormatKind(str(raw))
        except ValueError:
            warnings.append(f"invalid format {raw!r} from {where} — layer skipped")
            return None
    if key in ("telemetry", "plugins"):
        value = parse_bool(raw)
        if value is None:
            warnings.append(f"invalid bool {raw!r} for {key} from {where} — layer skipped")
        return value
    if key == "census":
        text = str(raw).strip()
        return text or None
    if key == "project":
        text = str(raw).strip()
        return text or None
    return raw


def _csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def resolve(
    flags: Flags,
    env: Mapping[str, str],
    project: ViberConfig | None,
    user: ViberConfig | None,
) -> Settings:
    warnings: list[str] = []
    sources: dict[str, Source] = {}

    flag_values: dict[str, Any] = {
        "census": flags.census,
        "project": flags.project,
        "profile": flags.profile,
        "format": flags.fmt,
    }

    def pick(key: str) -> Any:
        allowed = CHAIN[key]
        if Source.FLAG in allowed and flag_values.get(key) is not None:
            sources[key] = Source.FLAG
            return flag_values[key]
        if Source.ENV in allowed:
            name = ENV_NAMES[key]
            if env.get(name):
                value = _coerce(key, env[name], f"env {name}", warnings)
                if value is not None:
                    sources[key] = Source.ENV
                    return value
        for cfg, source in ((project, Source.PROJECT), (user, Source.USER)):
            if cfg is not None and source in allowed and key in cfg.model_fields_set:
                value = _coerce(key, getattr(cfg, key, None), f"{source.value} config", warnings)
                if value is not None:
                    sources[key] = source
                    return value
        return None

    values: dict[str, Any] = {}
    for key in (k.value for k in ConfigKey):
        picked = pick(key)
        if picked is None:
            sources[key] = Source.DEFAULT
            values[key] = DEFAULTS[key]
        else:
            values[key] = picked

    return Settings(
        census=values["census"],
        project=values["project"],
        format=values["format"],
        out=flags.out,
        force=flags.force if flags.force is not None else False,
        profile=values["profile"],
        include=_csv(flags.include) if flags.include else (),
        exclude=_csv(flags.exclude) if flags.exclude else (),
        telemetry=values["telemetry"],
        plugins=values["plugins"],
        sources=sources,
        warnings=tuple(warnings),
    )
