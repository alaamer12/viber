"""Rich-layout builders: payload in, display Parts out. No rich imports here —
this module only composes `display.Part` specs; the display layer renders them.
Plain mode never reaches this file (emit routes it straight to render_text).

A command with no builder degrades to the plain renderer: a missing presentation
path must never become an error path.
"""

from collections.abc import Callable
from typing import Any, Final

from viber.output.display import (
    Display,
    KVPart,
    PanelPart,
    Part,
    TablePart,
    TextPart,
    render_parts,
)
from viber.output.render import render_text

Builder = Callable[[dict[str, Any], list[str]], list[Part]]

_STATUS_STYLE: Final = {
    "ready": "green",
    "blocked": "red",
    "command": "cyan",
    "candidate": "yellow",
}
_SEV_STYLE: Final = {
    "error": "bold red",
    "warning": "yellow",
    "question": "bold bright_yellow",
}

_SKILL_IDENTS: Final = ("skill", "version", "type", "deck", "path", "owned", "step")
_FIT_LINES: Final = (
    "role",
    "when",
    "doing",
    "why",
    "serves",
    "produces",
    "consumes",
    "blockers",
)
_DECK_LINES: Final = (
    "deck",
    "name",
    "description",
    "mutability",
    "registry",
    "remote",
    "skills_count",
)


def _sel(sel: list[str], key: str) -> bool:
    return key in sel


def _content_files(content: dict[str, Any]) -> list[str]:
    entry = str(content.get("entry", "SKILL.md"))
    files: list[str] = [entry]
    for group in ("references", "assets", "examples"):
        files += [str(f) for f in content.get(group, [])]
    return files


def _status_cell(status: object) -> TextPart:
    text = str(status)
    return TextPart(text, _STATUS_STYLE.get(text, ""))


def _roster_table(rows: list[dict[str, Any]]) -> TablePart:
    return TablePart(
        ["Skill", "Version", "Status"],
        [[str(r["name"]), str(r["version"]), _status_cell(r["status"])] for r in rows],
    )


def _skill(payload: dict[str, Any], sel: list[str]) -> list[Part]:
    parts: list[Part] = [
        KVPart(
            [
                (k, str(payload.get(k) if payload.get(k) is not None else "-"))
                for k in _SKILL_IDENTS
                if _sel(sel, k)
            ]
        )
    ]
    if _sel(sel, "description") and payload.get("description"):
        parts.append(PanelPart(str(payload["description"]), "description"))
    if _sel(sel, "use_cases") and payload.get("use_cases"):
        parts.append(TextPart("use-cases", "bold"))
        parts += [TextPart(f"• {u}") for u in payload["use_cases"]]
    fit = payload.get("fit") or {}
    if _sel(sel, "fit"):
        pairs = [
            (f"fit.{k}", ", ".join(fit[k]) if isinstance(fit[k], list) else str(fit[k]))
            for k in _FIT_LINES
            if fit.get(k)
        ]
        if pairs:
            parts.append(KVPart(pairs))
        rels: list[Part] = []
        show_long = _sel(sel, "long_hints")
        for kind in ("after", "before", "with"):
            style = "magenta" if kind == "with" else "blue"
            for rel in fit.get(kind, []):
                hint = f" — {rel['hint']}" if rel.get("hint") else ""
                rels.append(TextPart(f"[{kind}] {rel.get('skill', '')}{hint}", style))
                if show_long and rel.get("long_hint"):
                    rels.append(TextPart(f"      {rel['long_hint']}", "dim italic"))
        if rels:
            parts.append(TextPart("relations", "bold"))
            parts += rels
    content = payload.get("content") or {}
    if _sel(sel, "content") and content:
        parts.append(TextPart("content", "bold"))
        files = "\n".join(f"  {f}" for f in _content_files(content))
        parts.append(TextPart(files, "dim"))
    return parts


def _step(payload: dict[str, Any], sel: list[str]) -> list[Part]:
    phase = f"  [{payload.get('phase') or 'any'}]" if _sel(sel, "phase") else ""
    parts: list[Part] = [TextPart(f"{payload['step']}{phase}", "bold")]
    if _sel(sel, "roster"):
        parts.append(_roster_table(payload.get("roster", [])))
    if _sel(sel, "goal") and payload.get("goal"):
        parts.append(TextPart(f"goal: {payload['goal']}", "green"))
    if _sel(sel, "needs") and payload.get("needs"):
        parts.append(TextPart("needs", "bold"))
        parts += [TextPart(f"- {n}") for n in payload["needs"]]
    cands = payload.get("uninstalled_candidates")
    if _sel(sel, "possible_skills") and cands:
        joined = ", ".join(cands)
        parts.append(
            TextPart(f"candidates (not installed — suggest to user): {joined}", "yellow")
        )
    return parts


def _candidate_parts(c: dict[str, Any], sel: list[str], index: int, total: int) -> list[Part]:
    head = f"next: {c['skill']} ({index} of {total} unblocked)"
    parts: list[Part] = [TextPart(head, "bold green")]
    if _sel(sel, "reasons"):
        parts.append(TextPart("why this might be next:", "dim"))
        longs = c.get("reason_long", [])
        for j, reason in enumerate(c.get("reasons", [])):
            parts.append(TextPart(f"  • {reason}"))
            if j < len(longs) and longs[j]:
                parts.append(TextPart(f"      {longs[j]}", "dim italic"))
    if c.get("why"):
        parts.append(TextPart(f"why it exists here: {c['why']}"))
    if c.get("todo"):
        parts.append(TextPart(f"do: {c['todo']}", "bold"))
    if _sel(sel, "suggestion") and c.get("suggestion"):
        parts.append(TextPart(f"suggestion: {c['suggestion']}", "cyan"))
    consumes = ", ".join(c.get("consumes", [])) or "-"
    parts.append(TextPart(f"consumes: {consumes}", "dim"))
    return parts


def _previous_lines(payload: dict[str, Any]) -> list[Part]:
    prev = payload.get("previous")
    if prev:
        line = f"last: {prev['skill']} — {prev['outcome']} at {prev['ts']}"
        return [TextPart(line, "cyan")]
    return [TextPart("last: (no previous step recorded)", "dim")]


def _needs_and_commands(payload: dict[str, Any], sel: list[str]) -> list[Part]:
    parts: list[Part] = [
        TextPart("(no unblocked skill — what this step needs does not wait for one)")
    ]
    if _sel(sel, "needs") and payload.get("needs"):
        parts.append(TextPart("needs still open:", "bold"))
        parts += [TextPart(f"  • {n}") for n in payload["needs"]]
    if _sel(sel, "commands") and payload.get("commands"):
        joined = ", ".join(payload["commands"])
        parts.append(TextPart(f"v-commands callable now (slash skills): {joined}", "cyan"))
    return parts


def _blocked_parts(payload: dict[str, Any], sel: list[str]) -> list[Part]:
    if not (_sel(sel, "blocked") and payload.get("blocked")):
        return []
    rows = [[str(b["skill"]), str(b["blockers"])] for b in payload["blocked"]]
    return [TextPart("blocked:", "red"), TablePart(["Skill", "Blockers"], rows)]


def _next(payload: dict[str, Any], sel: list[str]) -> list[Part]:
    header = "POSSIBLE NEXT STEPS"
    if _sel(sel, "step") and payload.get("step"):
        header += f"  (step: {payload['step']})"
    parts: list[Part] = [TextPart(header, "bold")]
    if _sel(sel, "previous"):
        parts += _previous_lines(payload)
    candidates = payload.get("candidates", [])
    if candidates:
        for i, c in enumerate(candidates, start=1):
            parts.append(TextPart(""))
            parts += _candidate_parts(c, sel, i, len(candidates))
    else:
        parts += _needs_and_commands(payload, sel)
    parts += _blocked_parts(payload, sel)
    return parts


def _status(payload: dict[str, Any], sel: list[str]) -> list[Part]:
    labels = (
        ("phase", "phase"),
        ("step", "step"),
        ("total", "skills"),
        ("blocked", "blocked"),
        ("unclassified", "unclassified"),
    )
    return [KVPart([(lab, str(payload.get(k, "-"))) for k, lab in labels if _sel(sel, k)])]


def _usage_parts(payload: dict[str, Any], sel: list[str]) -> list[Part]:
    parts: list[Part] = [TextPart("usage", "bold")]
    usage = payload.get("usage") or {}
    if not usage.get("present"):
        return parts + [TextPart("(no telemetry yet)", "dim")]
    if not usage.get("rows"):
        return parts + [TextPart("(nothing recorded yet)", "dim")]
    rows = [
        [
            str(r["skill"]),
            str(r["count"]),
            str(r["lastUsed"] or "-"),
            str(r["ok"]),
            str(r["fail"]),
        ]
        for r in usage["rows"]
    ]
    return parts + [TablePart(["Skill", "Uses", "Last Used", "OK", "Fail"], rows)]


def _open_decisions(payload: dict[str, Any]) -> list[Part]:
    parts: list[Part] = [TextPart("open decisions", "bold")]
    opens = payload.get("open") or []
    if opens:
        parts += [TextPart(f"ASK USER — {q}", "bold bright_yellow") for q in opens]
    else:
        parts.append(TextPart("(none)", "dim"))
    return parts


def _situation(payload: dict[str, Any], sel: list[str]) -> list[Part]:
    parts: list[Part] = [
        KVPart([("phase", str(payload.get("phase", "-"))), ("step", str(payload.get("step", "-")))])
    ]  # fmt: skip
    bits = f"skills: {payload.get('total', 0)} · blocked: {payload.get('blocked', 0)}"
    if _sel(sel, "unclassified"):
        bits += f" · unclassified: {payload.get('unclassified', 0)}"
    parts.append(TextPart(bits, "cyan"))
    if _sel(sel, "previous"):
        parts += _previous_lines(payload)
    if _sel(sel, "roster") and payload.get("roster"):
        parts += [TextPart("step roster", "bold"), _roster_table(payload["roster"])]
    if _sel(sel, "usage"):
        parts += _usage_parts(payload, sel)
    parts.append(TextPart("POSSIBLE NEXT STEP", "bold"))
    nxt = payload.get("next")
    if nxt is None:
        parts.append(TextPart("(no unblocked skill — needs stand on their own)"))
        parts += [TextPart(f"  • {n}") for n in payload.get("needs", [])]
    else:
        parts += _candidate_parts(nxt, sel, 1, 1)
    parts += _open_decisions(payload)
    return parts


def _deck(payload: dict[str, Any], sel: list[str]) -> list[Part]:
    if "decks" in payload:
        rows = [
            [d["name"], d["mutability"], str(d["skills_count"]), d["registry"]]
            for d in payload["decks"]
        ]
        return [TablePart(["Deck", "Mutability", "Skills", "Registry"], rows)]
    pairs = [
        (k, str(payload.get(k)))
        for k in _DECK_LINES
        if _sel(sel, k) and payload.get(k) not in (None, "")
    ]
    return [KVPart(pairs)]


def _list(payload: dict[str, Any], sel: list[str]) -> list[Part]:
    rows = payload.get("skills", [])
    if payload.get("brief"):
        return [TablePart(["Skill", "Version"], [[r["name"], r["version"]] for r in rows])]
    full = [
        [
            str(r["name"]),
            str(r["version"]),
            str(r.get("type", "-")),
            str(r["deck"]),
            str(r["step"]),
            "owned" if r.get("owned") else "",
        ]
        for r in rows
    ]
    return [TablePart(["Skill", "Version", "Type", "Deck", "Step", "Owned"], full)]


def _stats(payload: dict[str, Any], sel: list[str]) -> list[Part]:
    if not payload.get("present", True):
        return [TextPart("no telemetry data yet", "dim")]
    rows = payload.get("rows")
    if isinstance(rows, dict):
        return [KVPart([(str(k), str(v)) for k, v in rows.items()])]
    table = [
        [
            str(r["skill"]),
            str(r["count"]),
            str(r["lastUsed"] or "-"),
            str(r["ok"]),
            str(r["fail"]),
        ]
        for r in rows or []
    ]
    return [TablePart(["Skill", "Uses", "Last Used", "OK", "Fail"], table)]


def _patterns(payload: dict[str, Any], sel: list[str]) -> list[Part]:
    if not payload.get("present", True):
        return [TextPart("no telemetry data yet", "dim")]
    rows = [[r["sequence"], str(r["count"])] for r in payload.get("rows", [])]
    return [TablePart(["Sequence", "Count"], rows)]


def _lint(payload: dict[str, Any], sel: list[str]) -> list[Part]:
    parts: list[Part] = []
    findings = payload.get("findings", [])
    if findings:
        rows: list[list[str | TextPart]] = []
        for f in findings:
            sev = str(f.get("severity", "?"))
            label = "ASK USER — " if f.get("ask_user") or sev == "question" else ""
            detail = label + str(f.get("question") or f.get("detail") or "")
            rows.append(
                [
                    TextPart(sev.upper(), _SEV_STYLE.get(sev, "")),
                    str(f.get("check", "")),
                    str(f.get("subject", "")),
                    detail,
                ]
            )
        parts.append(TablePart(["Severity", "Check", "Subject", "Detail"], rows))
    else:
        parts.append(TextPart("census consistent — no findings", "green"))
    s = payload.get("summary", {})
    total = (
        f"lint: {s.get('errors', 0)} errors, {s.get('warnings', 0)} warnings, "
        f"{s.get('questions', 0)} decisions"
    )
    noisy = any(int(s.get(k, 0)) for k in ("errors", "warnings", "questions"))
    parts.append(TextPart(total, "bold" if noisy else "dim"))
    return parts


def _config(payload: dict[str, Any], sel: list[str]) -> list[Part]:
    if "keys" in payload:
        rows = [
            [k["key"], str(k["value"]), str(k["source"]), str(k["default"])]
            for k in payload["keys"]
        ]
        return [TablePart(["Key", "Value", "Source", "Default"], rows)]
    if "project" in payload and "key" not in payload:
        pairs: list[tuple[str, str]] = [
            ("project", str(payload["project"])),
            ("user", str(payload["user"])),
        ]
        pairs += [("plugin dir", str(p)) for p in payload.get("plugin_dirs", [])]
        return [KVPart(pairs)]
    single: list[tuple[str, str]] = [
        (str(payload.get("key")), str(payload.get("value")))
    ]
    if _sel(sel, "source"):
        single.append(("source", str(payload.get("source"))))
    if _sel(sel, "default"):
        single.append(("default", str(payload.get("default"))))
    return [KVPart(single)]


def _fields(payload: dict[str, Any], sel: list[str]) -> list[Part]:
    detail = payload.get("detail")
    if detail is not None:
        return [KVPart([(k, str(v)) for k, v in detail.items()])]
    if "fields" not in payload and payload.get("groups"):
        rows = [[r["group"], str(r["fields"])] for r in payload["groups"]]
        return [TablePart(["Group", "Fields"], rows)]
    rows = [
        [r["field"], r["type"], "yes" if r["required"] else "no", str(r["limit"]), r["meaning"]]
        for r in payload.get("fields", [])
    ]
    parts: list[Part] = []
    flt = payload.get("filter")
    if flt:
        bits = " ".join(f"{k}={v}" for k, v in flt.items() if v)
        head = f"fields {bits}"
        if _sel(sel, "count"):
            head += f" — {payload.get('count', 0)} of {payload.get('total', 0)}"
        parts.append(TextPart(head, "bold"))
    parts.append(TablePart(["Field", "Type", "Req", "Limit", "Meaning"], rows))
    return parts


def _init(payload: dict[str, Any], sel: list[str]) -> list[Part]:
    pairs = [(key, str(payload[key])) for key in ("census", "created", "resolved") if key in sel]
    return [TextPart("CENSUS INITIALIZATION", "bold"), KVPart(pairs), *_lint(payload, sel)]


def _registry(payload: dict[str, Any], sel: list[str]) -> list[Part]:
    parts: list[Part] = [TextPart("SKILL METADATA", "bold")]
    if "skills" in sel:
        rows = [
            [str(skill[key] or "untagged") for key in
             ("name", "description", "when_to_use", "source", "viber")]
            for skill in payload["skills"]
        ]
        parts.append(TablePart(["Skill", "Purpose", "When to use", "Source", "Viber"], rows))
    if "conflicts" in sel:
        for conflict in payload["conflicts"]:
            parts.append(TextPart(
                f"ASK USER — source conflict for {conflict['name']}: "
                + "; ".join(conflict["sources"]), "bold yellow",
            ))
    return parts


RICH_BUILDERS: Final[dict[str, Builder]] = {
    "init": _init,
    "registry": _registry,
    "skill": _skill,
    "step": _step,
    "next": _next,
    "status": _status,
    "situation": _situation,
    "deck": _deck,
    "list": _list,
    "stats": _stats,
    "patterns": _patterns,
    "lint": _lint,
    "fields": _fields,
    "config": _config,
}


def render_command(
    command: str, payload: dict[str, Any], selection: list[str], display: Display
) -> str:
    """Rich path for structured commands; anything unknown degrades to plain text."""
    builder = RICH_BUILDERS.get(command)
    if builder is None:
        return render_text(command, payload, selection)
    return render_parts(display, builder(payload, selection))
