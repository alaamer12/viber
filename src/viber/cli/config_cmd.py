"""Config commands: list, get, set, unset, path — the sole writer of viber settings.

Handlers share the uniform global-option contract; every value lands through the
chain (flag > env > project > user > default), so `get` reports not just the value
but the layer it came from. Writes go to the project layer unless --user/--path.
"""

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import typer

from viber.cli.deps import (
    CensusOpt,
    ExcludeOpt,
    ForceOpt,
    FormatOpt,
    Globals,
    IncludeOpt,
    OutOpt,
    ProfileOpt,
    command,
)
from viber.core.settings import DEFAULTS, Flags, parse_bool, resolve
from viber.data import config_store
from viber.models.domain import ConfigKey, FormatKind, Profile

_USER_HELP = "Write the user layer instead of the project layer"
_PATH_HELP = "Write this specific config file instead"


def _display(value: Any) -> str:
    if value is None:
        return "auto (not set)"
    if isinstance(value, (Profile, FormatKind)):
        return value.value
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _settings(g: Globals) -> Any:
    return g.settings


def _coerce(key: ConfigKey, raw: str) -> Any:
    if key in (ConfigKey.TELEMETRY, ConfigKey.PLUGINS):
        value = parse_bool(raw)
        if value is None:
            raise ValueError(f"not a bool: {raw!r} (use true/false/1/0/yes/no)")
        return value
    if key == ConfigKey.PROFILE:
        return Profile(raw).value
    if key == ConfigKey.FORMAT:
        return FormatKind(raw).value
    if not raw.strip():
        raise ValueError("empty value — use unset to remove a key")
    return raw


def _target(user: bool, path: str | None) -> Path:
    paths = config_store.locate(os.environ)
    if path:
        return Path(path)
    return paths.user if user else paths.project


@command
def list_cmd(
    census: CensusOpt = None,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
) -> int:
    """Every settings key: value, source layer, default."""
    g = Globals(census, fmt, out, force, profile, include, exclude)
    st = _settings(g)
    rows = [
        {
            "key": k.value,
            "value": _display(getattr(st, k.value)),
            "source": st.sources[k.value].value,
            "default": _display(DEFAULTS[k.value]),
        }
        for k in ConfigKey
    ]
    emit_rows(g, {"keys": rows})
    return 0


@command
def get_cmd(
    key: ConfigKey,
    census: CensusOpt = None,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
) -> int:
    """Effective value of one key and the layer it came from."""
    g = Globals(census, fmt, out, force, profile, include, exclude)
    st = _settings(g)
    payload = {
        "key": key.value,
        "value": _display(getattr(st, key.value)),
        "source": st.sources[key.value].value,
        "default": _display(DEFAULTS[key.value]),
    }
    emit_rows(g, payload)
    return 0


@command
def set_cmd(
    key: ConfigKey,
    value: str,
    user: bool = typer.Option(False, "--user", "-u", help=_USER_HELP),
    path: str | None = typer.Option(None, "--path", "-p", help=_PATH_HELP),
    census: CensusOpt = None,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
) -> int:
    """Write one settings key to the project layer (or --user / --path)."""
    g = Globals(census, fmt, out, force, profile, include, exclude)
    target = _target(user, path)
    coerced = _coerce(key, value)
    config_store.set_value(target, key.value, coerced)
    emit_rows(g, {"message": f"{key.value} -> {_display(coerced)} ({target})"}, ack=True)
    return 0


@command
def unset_cmd(
    key: ConfigKey,
    user: bool = typer.Option(False, "--user", "-u", help=_USER_HELP),
    path: str | None = typer.Option(None, "--path", "-p", help=_PATH_HELP),
    census: CensusOpt = None,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
) -> int:
    """Remove a key from one layer; the ack names what takes over."""
    g = Globals(census, fmt, out, force, profile, include, exclude)
    target = _target(user, path)
    if not config_store.unset_value(target, key.value):
        emit_rows(g, {"message": f"nothing to unset for {key.value} in {target}"}, ack=True)
        return 0
    loaded = config_store.load(os.environ)
    st = resolve(Flags(), os.environ, loaded.project, loaded.user)
    now = _display(getattr(st, key.value))
    emit_rows(
        g,
        {"message": f"unset {key.value} — now {now} ({st.sources[key.value].value})"},
        ack=True,
    )
    return 0


@command
def path_cmd(
    census: CensusOpt = None,
    fmt: FormatOpt = None,
    out: OutOpt = None,
    force: ForceOpt = None,
    profile: ProfileOpt = None,
    include: IncludeOpt = None,
    exclude: ExcludeOpt = None,
) -> int:
    """Show the config files and plugin dirs, with exists/absent marks."""
    g = Globals(census, fmt, out, force, profile, include, exclude)
    paths = config_store.locate(os.environ)

    def mark(p: Path) -> str:
        return f"{p} (exists)" if p.is_file() else f"{p} (absent)"

    payload = {
        "project": mark(paths.project),
        "user": mark(paths.user),
        "plugin_dirs": [str(paths.project_plugins), str(paths.user_plugins)],
    }
    emit_rows(g, payload)
    return 0


def emit_rows(g: Globals, payload: dict[str, Any], ack: bool = False) -> None:
    from viber.output.emit import emit

    emit("ack" if ack else "config", payload, [] if ack else g.selection_with("config"), g.target())


COMMANDS: dict[str, Callable[..., None]] = {
    "list": list_cmd,
    "get": get_cmd,
    "set": set_cmd,
    "unset": unset_cmd,
    "path": path_cmd,
}
