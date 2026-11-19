"""Config boundary: viber's own settings files (project + user layers).

Fields are Any-typed on purpose — per-key parsing lives in core.settings so a bad
value warns and drops just that key, not the whole file. extra="allow" keeps
unknown keys alive across a `config set` round-trip.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict


class ViberConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    census: Any = None
    project: Any = None
    profile: Any = None
    format: Any = None
    telemetry: Any = None
    plugins: Any = None
