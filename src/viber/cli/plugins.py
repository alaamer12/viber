"""Drop-in command plugins — the internal extension surface, off by default.

Trust boundary, stated plainly: a plugin file is Python executed with the invoking
user's permissions on every viber run. That is why `plugins` defaults to false and
must be turned on through the visible settings chain (`viber config set plugins true`
or VIBER_PLUGINS), never automatically. Failure policy is skip-and-warn: a broken
plugin never bricks the CLI.
"""

import importlib.util
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

PACKAGE_PREFIX = "viber_plugins."


def _load(path: Path) -> tuple[dict[str, Callable[..., int]] | None, str | None]:
    spec = importlib.util.spec_from_file_location(PACKAGE_PREFIX + path.stem, path)
    if spec is None or spec.loader is None:
        return None, f"{path.name}: cannot build import spec — skipped"
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 — skip-and-warn is the documented policy
        return None, f"{path.name}: import failed ({type(exc).__name__}: {exc}) — skipped"
    raw: Any = getattr(module, "COMMANDS", None)
    if not isinstance(raw, dict) or not all(callable(v) for v in raw.values()):
        return None, f"{path.name}: no COMMANDS dict of callables — skipped"
    return dict(raw), None


def collect(
    dirs: Iterable[Path],
) -> tuple[list[tuple[str, dict[str, Callable[..., int]]]], list[str]]:
    found: list[tuple[str, dict[str, Callable[..., int]]]] = []
    warnings: list[str] = []
    for directory in dirs:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.py")):
            commands, warning = _load(path)
            if warning:
                warnings.append(warning)
            if commands:
                found.append((str(path), commands))
    return found, warnings
