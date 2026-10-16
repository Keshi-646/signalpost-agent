"""SQLite persistence and profile change history."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_DB = Path("signalpost.db")


def connect(db_path: str | Path = DEFAULT_DB) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    connection.execute("""CREATE TABLE IF NOT EXISTS profiles (
        org_number TEXT PRIMARY KEY, name TEXT, profile_json TEXT NOT NULL,
        source_url TEXT NOT NULL, retrieved_at TEXT NOT NULL
    )""")
    connection.execute("""CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, org_number TEXT NOT NULL,
        snapshot_json TEXT NOT NULL, source_url TEXT NOT NULL, retrieved_at TEXT NOT NULL
    )""")
    connection.commit()
    return connection


def save_profile(profile: dict[str, Any], db_path: str | Path = DEFAULT_DB) -> dict[str, Any]:
    """Save snapshot and report fields that changed since the previous observation."""
    connection = connect(db_path)
    try:
        previous_row = connection.execute("SELECT profile_json FROM profiles WHERE org_number=?", (profile["org_number"],)).fetchone()
        previous = json.loads(previous_row["profile_json"]) if previous_row else None
        ignored = {"retrieved_at", "evidence", "source_url"}
        changes = []
        if previous:
            for key, new_value in profile.items():
                if key not in ignored and previous.get(key) != new_value:
                    changes.append({"field": key, "old": previous.get(key), "new": new_value})
        encoded = json.dumps(profile, ensure_ascii=False, sort_keys=True)
        connection.execute("INSERT OR REPLACE INTO profiles(org_number,name,profile_json,source_url,retrieved_at) VALUES(?,?,?,?,?)",
                           (profile["org_number"], profile.get("name"), encoded, profile["source_url"], profile["retrieved_at"]))
        connection.execute("INSERT INTO history(org_number,snapshot_json,source_url,retrieved_at) VALUES(?,?,?,?)",
                           (profile["org_number"], encoded, profile["source_url"], profile["retrieved_at"]))
        connection.commit()
        return {"is_new": previous is None, "changes": changes}
    finally:
        connection.close()


def get_profile(org_number: str, db_path: str | Path = DEFAULT_DB) -> dict[str, Any] | None:
    connection = connect(db_path)
    try:
        row = connection.execute("SELECT profile_json FROM profiles WHERE org_number=?", (org_number,)).fetchone()
        return json.loads(row["profile_json"]) if row else None
    finally:
        connection.close()


def list_profiles(limit: int = 100, db_path: str | Path = DEFAULT_DB) -> list[dict[str, Any]]:
    connection = connect(db_path)
    try:
        rows = connection.execute("SELECT profile_json FROM profiles ORDER BY name LIMIT ?", (limit,)).fetchall()
        return [json.loads(row["profile_json"]) for row in rows]
    finally:
        connection.close()


def profile_count(db_path: str | Path = DEFAULT_DB) -> int:
    connection = connect(db_path)
    try:
        return int(connection.execute("SELECT COUNT(*) FROM profiles").fetchone()[0])
    finally:
        connection.close()


def history_for(org_number: str, db_path: str | Path = DEFAULT_DB) -> list[dict[str, Any]]:
    connection = connect(db_path)
    try:
        rows = connection.execute("SELECT snapshot_json FROM history WHERE org_number=? ORDER BY id DESC", (org_number,)).fetchall()
        return [json.loads(row["snapshot_json"]) for row in rows]
    finally:
        connection.close()
