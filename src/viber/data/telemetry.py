"""SQLite telemetry repository — schema-versioned, context-managed connections."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS invocations (
    id INTEGER PRIMARY KEY,
    skill TEXT NOT NULL,
    ts TEXT NOT NULL,
    step TEXT,
    phase TEXT,
    outcome TEXT,
    note TEXT
);
CREATE INDEX IF NOT EXISTS idx_skill_ts ON invocations(skill, ts);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class TelemetryDB:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def exists(self) -> bool:
        return self.db_path.is_file()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.executescript(_SCHEMA)
            conn.execute(
                "INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )
            conn.commit()
            yield conn
        finally:
            conn.close()

    def record_invocation(self, skill: str, ts: str, step: str | None, phase: str | None) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO invocations (skill, ts, step, phase) VALUES (?, ?, ?, ?)",
                (skill, ts, step, phase),
            )
            conn.commit()

    def close_open(self, skill: str, outcome: str, note: str | None) -> int | None:
        """Set the outcome of the newest open invocation of skill; returns its id or None."""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id FROM invocations WHERE skill=? AND outcome IS NULL"
                " ORDER BY id DESC LIMIT 1",
                (skill,),
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                "UPDATE invocations SET outcome=?, note=? WHERE id=?", (outcome, note, row[0])
            )
            conn.commit()
            result: int = row[0]
            return result

    def skill_stats(self, skill: str) -> dict[str, object]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*), MAX(ts),"
                " SUM(CASE WHEN outcome='ok' THEN 1 ELSE 0 END),"
                " SUM(CASE WHEN outcome='fail' THEN 1 ELSE 0 END),"
                " SUM(CASE WHEN outcome='skip' THEN 1 ELSE 0 END)"
                " FROM invocations WHERE skill=?",
                (skill,),
            ).fetchone()
        total, last, ok, fail, skip = row
        return {
            "skill": skill,
            "count": total or 0,
            "lastUsed": last,
            "ok": ok or 0,
            "fail": fail or 0,
            "skip": skip or 0,
        }

    def all_stats(self, since: str | None = None) -> list[dict[str, object]]:
        where: str = ""
        params: tuple[str, ...] = ()
        if since:
            where, params = "WHERE ts >= ?", (since,)
        with self.connect() as conn:
            rows = conn.execute(
                f"SELECT skill, COUNT(*) as c, MAX(ts),"
                f" SUM(CASE WHEN outcome='ok' THEN 1 ELSE 0 END),"
                f" SUM(CASE WHEN outcome='fail' THEN 1 ELSE 0 END)"
                f" FROM invocations {where} GROUP BY skill ORDER BY c DESC",
                params,
            ).fetchall()
        return [
            {"skill": r[0], "count": r[1], "lastUsed": r[2], "ok": r[3] or 0, "fail": r[4] or 0}
            for r in rows
        ]

    def sequence(self, limit: int | None = None) -> list[str]:
        with self.connect() as conn:
            if limit:
                rows = conn.execute(
                    "SELECT skill FROM invocations ORDER BY id DESC LIMIT ?", (limit,)
                ).fetchall()
                return [r[0] for r in reversed(rows)]
            rows = conn.execute("SELECT skill FROM invocations ORDER BY id").fetchall()
            return [r[0] for r in rows]

    def successor(self, skill: str, window: int = 50) -> tuple[str, int] | None:
        seq = self.sequence(limit=window)
        successors: dict[str, int] = {}
        for i, s in enumerate(seq[:-1]):
            if s == skill:
                nxt = seq[i + 1]
                successors[nxt] = successors.get(nxt, 0) + 1
        if not successors:
            return None
        top = max(successors, key=lambda k: successors[k])
        return top, successors[top]

    def pairs(self, top: int = 15) -> list[tuple[str, int]]:
        seq = self.sequence()
        counts: dict[str, int] = {}
        for i in range(len(seq) - 1):
            pair = f"{seq[i]} -> {seq[i + 1]}"
            counts[pair] = counts.get(pair, 0) + 1
        return sorted(counts.items(), key=lambda x: -x[1])[:top]
