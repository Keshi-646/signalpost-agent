"""Collect real company profiles using the official public registry search API."""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any
import requests
from .agent import API_BASE, USER_AGENT, normalize_company
from .database import save_profile, connect


def collect_profiles(target: int = 1000, db_path: str | Path = "signalpost.db", pause: float = 0.1,
                     max_pages: int | None = None) -> dict[str, Any]:
    if target < 1:
        raise ValueError("target must be at least 1")
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/vnd.brreg.enhetsregisteret.enhet.v2+json"})
    saved = 0
    pages = 0
    db_connection = connect(db_path)
    try:
        known_numbers = {row[0] for row in db_connection.execute("SELECT org_number FROM profiles").fetchall()}
    finally:
        db_connection.close()
    errors: list[str] = []
    page = 0
    while saved < target and (max_pages is None or pages < max_pages):
        params = {"page": page, "size": min(100, target - saved), "sort": "organisasjonsnummer,ASC"}
        try:
            response = session.get(f"{API_BASE}/enheter", params=params, timeout=25)
            response.raise_for_status()
            payload = response.json()
            records = payload.get("_embedded", {}).get("enheter", [])
            if not records:
                break
            pages += 1
            for raw in records:
                try:
                    profile = normalize_company(raw)
                    if profile["org_number"] in known_numbers:
                        continue
                    save_profile(profile, db_path)
                    known_numbers.add(profile["org_number"])
                    saved += 1
                    if saved >= target:
                        break
                except (ValueError, KeyError, TypeError) as exc:
                    errors.append(f"Skipped one invalid record: {exc}")
            if not payload.get("_links", {}).get("next"):
                break
            page += 1
            if pause:
                time.sleep(pause)
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"Stopped on page {page}: {exc}")
            break
    return {"saved_this_run": saved, "pages_read": pages, "target": target, "errors": errors}


def export_profiles_json(output_path: str | Path = "profiles.json", db_path: str | Path = "signalpost.db") -> int:
    import sqlite3
    connection = sqlite3.connect(str(db_path))
    try:
        rows = connection.execute("SELECT profile_json FROM profiles ORDER BY org_number").fetchall()
        profiles = [json.loads(row[0]) for row in rows]
    finally:
        connection.close()
    Path(output_path).write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(profiles)
