from __future__ import annotations

import sqlite3
from pathlib import Path


class Store:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    text TEXT NOT NULL,
                    score REAL NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def log_event(self, kind: str, text: str) -> None:
        with self._connect() as conn:
            conn.execute("INSERT INTO events (kind, text) VALUES (?, ?)", (kind, text))

    def add_turn(self, role: str, text: str) -> None:
        with self._connect() as conn:
            conn.execute("INSERT INTO turns (role, text) VALUES (?, ?)", (role, text))

    def maybe_write_memory(self, text: str, score: float, kind: str = "semantic") -> bool:
        if score < 0.6:
            return False
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO memories (kind, text, score) VALUES (?, ?, ?)",
                (kind, text, score),
            )
        return True

    def memory_count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM memories").fetchone()
            return int(row["n"])

    def recent_turns(self, n: int = 12) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT role, text FROM turns ORDER BY id DESC LIMIT ?",
                (n,),
            ).fetchall()
        return [{"role": r["role"], "text": r["text"]} for r in reversed(list(rows))]
