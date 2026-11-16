#!/usr/bin/env python3
"""Viber CLI launcher — keeps `python viber.py <cmd> ...` working from any project.

Resolution order: (1) run in-process if viber + deps import here; (2) exec via
this project's .venv python; (3) exec via uv against this project; (4) print exact
bootstrap commands and exit 2. Never installs anything, never touches user site-packages.
"""

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARGS = sys.argv[1:]


def _in_process() -> int:
    sys.path.insert(0, str(HERE / "src"))
    try:
        from viber.app import main
    except ImportError:
        return -1
    main(ARGS)
    return 0


def _exec(cmd: list[str]) -> int:
    return subprocess.run(cmd, cwd=HERE).returncode


def main() -> int:
    rc = _in_process()
    if rc >= 0:
        return rc
    venv_py = HERE / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if venv_py.is_file():
        return _exec([str(venv_py), "-m", "viber", *ARGS])
    if _which("uv"):
        return _exec(["uv", "run", "--project", str(HERE), "viber", *ARGS])
    sys.stderr.write(
        "error: viber dependencies not found. Bootstrap once (uv only, project-local):\n"
        f"  cd \"{HERE}\"\n  uv sync\n"
    )
    return 2


def _which(exe: str) -> str | None:
    from shutil import which
    return which(exe)


if __name__ == "__main__":
    raise SystemExit(main())
