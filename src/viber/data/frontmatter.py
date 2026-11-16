"""SKILL.md frontmatter parsing (stdlib regex, no PyYAML) and content-tree scanning."""

import re
from pathlib import Path
from typing import Any

_FM_KEY = re.compile(r"^([a-z_-]+):\s*(.*)")
_FOLD_MARKERS = (">-", ">", "|", "|-")
_SCAN_SKIP = (".git", "__pycache__", "scripts")


def parse_frontmatter(skill_md: Path) -> dict[str, str]:
    text = skill_md.read_text(encoding="utf-8-sig")
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    result: dict[str, str] = {}
    current_key: str | None = None
    current_val: list[str] = []
    for line in text[3:end].strip().split("\n"):
        m = _FM_KEY.match(line)
        if m:
            if current_key:
                result[current_key] = " ".join(current_val).strip()
            current_key = m.group(1)
            val = m.group(2).strip()
            current_val = [] if val in _FOLD_MARKERS else [val.strip("'\"")]
        elif current_key and line.startswith("  "):
            current_val.append(line.strip().strip("'\""))
    if current_key:
        result[current_key] = " ".join(current_val).strip()
    return result


def list_content(skill_dir: Path) -> dict[str, Any]:
    refs: list[str] = []
    assets: list[str] = []
    examples: list[str] = []
    targets: list[tuple[str, list[str]]] = [
        ("references", refs),
        ("assets", assets),
        ("examples", examples),
    ]
    for sub, bucket in targets:
        d = skill_dir / sub
        if d.is_dir():
            bucket.extend(
                str(f.relative_to(skill_dir)).replace("\\", "/")
                for f in sorted(d.rglob("*"))
                if f.is_file()
            )
    for sub_dir in sorted(skill_dir.iterdir()):
        if sub_dir.is_dir() and sub_dir.name not in (
            "references",
            "assets",
            "examples",
            *_SCAN_SKIP,
        ):
            for sub, bucket in targets:
                d = sub_dir / sub
                if d.is_dir():
                    bucket.extend(
                        str(f.relative_to(skill_dir)).replace("\\", "/")
                        for f in sorted(d.rglob("*"))
                        if f.is_file()
                    )
    return {"entry": "SKILL.md", "references": refs, "assets": assets, "examples": examples}
