"""Compact plain-text renderers: information-dense, section-grouped, no box-drawing.

Payload contract: core builds one dict per command whose top-level keys match the
field registry for that command; the renderer emits only selected keys, in registry
order, grouped under section titles. Values are plain JSON-ready types.
"""

from collections.abc import Callable
from typing import Any, Final

from viber.output.fields import specs_for

Renderer = Callable[[dict[str, Any], list[str]], str]


def _selected(selection: list[str], key: str) -> bool:
    return key in selection


def _table(rows: list[list[str]], columns: list[str]) -> list[str]:
    if not rows:
        return ["(none)"]
    widths = [len(c) for c in columns]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    out = [
        "  ".join(c.ljust(widths[i]) for i, c in enumerate(columns)),
        "  ".join("-" * w for w in widths),
    ]
    out += ["  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)) for row in rows]
    return out


def _relation_lines(rels: list[dict[str, Any]], kind: str, long_hints: bool) -> list[str]:
    lines: list[str] = []
    for rel in rels:
        line = f"[{kind}] {rel['skill']}"
        if rel.get("hint"):
            line += f" — {rel['hint']}"
        lines.append(line)
        if long_hints and rel.get("long_hint"):
            lines.append(f"    {rel['long_hint']}")
    return lines


def render_skill(p: dict[str, Any], sel: list[str]) -> str:
    lines: list[str] = []
    ident = [
        f"{k}: {p.get(k, '-') if p.get(k) is not None else '-'}"
        for k in ("skill", "version", "type", "deck", "path", "owned", "step")
        if _selected(sel, k)
    ]
    lines += ident
    if _selected(sel, "description") and p.get("description"):
        lines += ["", "description", str(p["description"])]
    if _selected(sel, "use_cases") and p.get("use_cases"):
        lines += ["", "use-cases"] + [f"- {u}" for u in p["use_cases"]]
    fit = p.get("fit") or {}
    if _selected(sel, "fit"):
        for k in ("role", "when", "serves", "produces", "consumes", "blockers"):
            if fit.get(k):
                val = ", ".join(fit[k]) if isinstance(fit[k], list) else str(fit[k])
                lines.append(f"fit.{k}: {val}")
        if not any(fit.get(k) for k in ("after", "before", "with")):
            pass
        else:
            lines.append("")
            lines.append("relations")
            long_hints = _selected(sel, "long_hints")
            for kind in ("after", "before", "with"):
                lines += _relation_lines(fit.get(kind, []), kind, long_hints)
    content = p.get("content") or {}
    if _selected(sel, "content") and content:
        files = (
            [content.get("entry", "SKILL.md")]
            + content.get("references", [])
            + content.get("assets", [])
            + content.get("examples", [])
        )
        lines += ["", "content"] + [f"- {f}" for f in files]
    history = p.get("history") or []
    if _selected(sel, "history") and history:
        lines += ["", "history"] + [f"- {h.get('date', '?')} {h.get('event', '')}" for h in history]
    return "\n".join(lines)


def render_step(p: dict[str, Any], sel: list[str]) -> str:
    head = f"{p['step']}" + (f" [{p.get('phase') or 'any'}]" if _selected(sel, "phase") else "")
    lines = [head, ""]
    rows = [[r["name"], r["version"], r["status"]] for r in p.get("roster", [])]
    lines += _table(rows, ["Skill", "Version", "Status"])
    if _selected(sel, "goal") and p.get("goal"):
        lines += ["", f"goal: {p['goal']}"]
    if _selected(sel, "needs") and p.get("needs"):
        lines += ["", "needs"] + [f"- {n}" for n in p["needs"]]
    if _selected(sel, "possible_skills") and p.get("uninstalled_candidates"):
        lines += ["", "candidates (not installed — suggest to user)"] + [
            f"- {c}" for c in p["uninstalled_candidates"]
        ]
    return "\n".join(lines)


def render_next(p: dict[str, Any], sel: list[str]) -> str:
    lines: list[str] = []
    long_hints = _selected(sel, "long_hints")
    show_reasons = _selected(sel, "reasons")
    show_suggestion = _selected(sel, "suggestion")
    for c in p.get("candidates", []):
        lines.append(
            f"next: {c['skill']}" + (f" (step {p.get('step')})" if _selected(sel, "step") else "")
        )
        lines.append("")
        if show_reasons:
            for reason in c.get("reasons", []):
                lines.append(f"- {reason}")
            if long_hints and c.get("reason_long"):
                for rl in c["reason_long"]:
                    lines.append(f"    {rl}")
        lines.append(f"when: {c.get('when') or '-'}")
        if show_suggestion and c.get("suggestion"):
            lines.append(f"suggestion: {c['suggestion']}")
        lines.append(f"produces: {', '.join(c.get('produces', [])) or '-'}")
        lines.append(f"consumes: {', '.join(c.get('consumes', [])) or '-'}")
    if _selected(sel, "blocked") and p.get("blocked"):
        lines += ["", "blocked:"] + [f"- {b['skill']}: {b['blockers']}" for b in p["blocked"]]
    return "\n".join(lines)


def render_deck(p: dict[str, Any], sel: list[str]) -> str:
    if _selected(sel, "decks") and "decks" in p:
        rows = [
            [d["name"], d["mutability"], str(d["skills_count"]), d["registry"]] for d in p["decks"]
        ]
        return "\n".join(_table(rows, ["Deck", "Mutability", "Skills", "Registry"]))
    lines = [f"deck: {p.get('deck', '')}"]
    for k in ("name", "description", "mutability", "registry", "remote"):
        if _selected(sel, k) and p.get(k) not in (None, ""):
            lines.append(f"{k}: {p[k]}")
    if _selected(sel, "skills_count"):
        lines.append(f"skills: {p.get('skills_count', 0)}")
    if _selected(sel, "skills") and p.get("skills"):
        lines += [""] + [f"- {s}" for s in p["skills"]]
    return "\n".join(lines)


def render_status(p: dict[str, Any], sel: list[str]) -> str:
    lines = []
    for k, label in (
        ("phase", "phase"),
        ("step", "step"),
        ("total", "skills"),
        ("blocked", "blocked"),
        ("unclassified", "unclassified"),
    ):
        if _selected(sel, k):
            lines.append(f"{label}: {p.get(k, '-')}")
    return "\n".join(lines)


def render_situation(p: dict[str, Any], sel: list[str]) -> str:
    lines = [f"phase: {p.get('phase', '-')}", f"step: {p.get('step', '-')}"]
    if _selected(sel, "total"):
        bits = [f"skills: {p.get('total', 0)}", f"blocked: {p.get('blocked', 0)}"]
        if _selected(sel, "unclassified"):
            bits.append(f"unclassified: {p.get('unclassified', 0)}")
        lines.append(" · ".join(bits))
    if _selected(sel, "roster") and p.get("roster"):
        rows = [[r["name"], r["version"], r["status"]] for r in p["roster"]]
        lines += ["", "step roster"] + _table(rows, ["Skill", "Version", "Status"])
    if _selected(sel, "usage"):
        usage = p.get("usage") or {}
        lines += ["", "usage"]
        if not usage.get("present"):
            lines.append("(no telemetry yet)")
        elif not usage.get("rows"):
            lines.append("(nothing recorded yet)")
        else:
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
            lines += _table(rows, ["Skill", "Uses", "Last Used", "OK", "Fail"])
    if _selected(sel, "next"):
        nxt = p.get("next")
        lines += ["", "next"]
        if nxt is None:
            lines.append("(nothing unblocked)")
        else:
            lines.append(f"{nxt['skill']} — {nxt.get('when') or '-'}")
            lines += [f"- {r}" for r in nxt.get("reasons", [])]
    if _selected(sel, "open"):
        open_items = p.get("open") or []
        lines += ["", "open decisions"]
        lines += [f"ASK USER — {q}" for q in open_items] if open_items else ["(none)"]
    return "\n".join(lines)


def render_list(p: dict[str, Any], sel: list[str]) -> str:
    rows = p.get("skills", [])
    if p.get("brief"):
        table = [[r["name"], r["version"]] for r in rows]
        return "\n".join(_table(table, ["Skill", "Version"]))
    table = [
        [
            r["name"],
            r["version"],
            r.get("type", "-"),
            r["deck"],
            r["step"],
            "owned" if r.get("owned") else "",
        ]
        for r in rows
    ]
    return "\n".join(_table(table, ["Skill", "Version", "Type", "Deck", "Step", "Owned"]))


def render_stats(p: dict[str, Any], sel: list[str]) -> str:
    if not p.get("present", True):
        return "no telemetry data yet"
    if "skill" in p:
        return (
            "\n".join(f"{k}: {v}" for k, v in p["rows"].items())
            if isinstance(p.get("rows"), dict)
            else "\n".join(f"{k}: {v}" for k, v in p.items() if k not in ("present",))
        )
    table = [
        [str(r["skill"]), str(r["count"]), str(r["lastUsed"] or "-"), str(r["ok"]), str(r["fail"])]
        for r in p.get("rows", [])
    ]
    return "\n".join(_table(table, ["Skill", "Uses", "Last Used", "OK", "Fail"]))


def render_patterns(p: dict[str, Any], sel: list[str]) -> str:
    if not p.get("present", True):
        return "no telemetry data yet"
    table = [[r["sequence"], str(r["count"])] for r in p.get("rows", [])]
    return "\n".join(_table(table, ["Sequence", "Count"]))


def render_config(p: dict[str, Any], sel: list[str]) -> str:
    if "keys" in p:
        rows = [
            [k["key"], str(k["value"]), k["source"], str(k["default"])] for k in p["keys"]
        ]
        return "\n".join(_table(rows, ["Key", "Value", "Source", "Default"]))
    if "project" in p and "key" not in p:
        lines = [f"project: {p['project']}", f"user: {p['user']}"]
        if _selected(sel, "plugin_dirs") and p.get("plugin_dirs"):
            lines += ["", "plugin dirs (loading gated by the 'plugins' key, default off)"]
            lines += [f"- {d}" for d in p["plugin_dirs"]]
        return "\n".join(lines)
    lines = [f"{p['key']}: {p['value']}"]
    if _selected(sel, "source"):
        lines.append(f"source: {p.get('source', '-')}")
    if _selected(sel, "default"):
        lines.append(f"default: {p.get('default', '-')}")
    return "\n".join(lines)


def render_lint(p: dict[str, Any], sel: list[str]) -> str:
    lines: list[str] = []
    findings = p.get("findings", [])
    for sev in ("error", "warning", "question"):
        group = [f for f in findings if f["severity"] == sev]
        if not group:
            continue
        lines += [sev + "s" if sev != "question" else "decisions for the user", ""]
        for f in group:
            prefix = "ASK USER — " if sev == "question" else ""
            lines.append(
                f"  {f['check']} {f['subject']}: " + prefix + (f.get("question") or f["detail"])
            )
        lines.append("")
    if not lines:
        lines = ["census consistent — no findings"]
    if _selected(sel, "summary"):
        s = p.get("summary", {})
        lines.append(
            f"lint: {s.get('errors', 0)} errors, {s.get('warnings', 0)} warnings, "
            f"{s.get('questions', 0)} decisions"
        )
    return "\n".join(lines).rstrip("\n")


def render_write_ack(p: dict[str, Any], sel: list[str]) -> str:
    lines = [f"ok: {p['message']}"]
    if p.get("show"):
        lines.append("")
        lines.append(render_skill(p["show"], ["skill", "version", "type", "deck", "step"]))
    return "\n".join(lines)


def render_ack(p: dict[str, Any], sel: list[str]) -> str:
    return f"ok: {p['message']}"


def render_drift(p: dict[str, Any], sel: list[str]) -> str:
    table = [[d["name"], d["census_version"], d["disk_version"]] for d in p.get("drift", [])]
    return "\n".join(_table(table, ["Skill", "Census", "Disk"]))


RENDERERS: Final[dict[str, Renderer]] = {
    "skill": render_skill,
    "step": render_step,
    "next": render_next,
    "deck": render_deck,
    "status": render_status,
    "situation": render_situation,
    "list": render_list,
    "stats": render_stats,
    "patterns": render_patterns,
    "lint": render_lint,
    "config": render_config,
    "ack": render_ack,
    "ack-show": render_write_ack,
    "drift": render_drift,
}


def render_text(command: str, payload: dict[str, Any], selection: list[str]) -> str:
    renderer = RENDERERS[command]
    return renderer(payload, selection)


def registry_order(command: str) -> list[str]:
    return [s.key for s in specs_for(command)]
