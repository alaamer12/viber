"""Profile + override resolution: profile → include → exclude, with dependency
conflict validation. Returns the ordered list of selected keys per command."""

import difflib

from viber.models.domain import Profile
from viber.output.fields import specs_for


class ProfileError(Exception):
    """Invalid field selection; CLI maps to exit code 2."""


def resolve_selection(
    command: str,
    profile: Profile,
    include: tuple[str, ...] = (),
    exclude: tuple[str, ...] = (),
) -> list[str]:
    specs = {s.key: s for s in specs_for(command)}
    if profile == Profile.MINIMAL:
        base = {k for k, s in specs.items() if Profile.MINIMAL in s.profiles}
    elif profile == Profile.STANDARD:
        base = {k for k, s in specs.items() if Profile.STANDARD in s.profiles}
    else:
        base = set(specs)

    for key in (*include, *exclude):
        if key not in specs:
            close = difflib.get_close_matches(key, specs, n=3)
            hint = f" — did you mean {', '.join(close)}?" if close else ""
            raise ProfileError(f"unknown field '{key}' for command '{command}'{hint}")

    selected = base | set(include)
    selected -= set(exclude)

    for key in selected:
        for dep in specs[key].depends_on:
            if dep not in selected:
                raise ProfileError(f"field '{key}' requires '{dep}' — enable it or drop '{key}'")

    return [s.key for s in specs_for(command) if s.key in selected]
