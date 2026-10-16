"""Fetch and verify company facts from Norway's official entity register."""
from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

import requests

API_BASE = "https://data.brreg.no/enhetsregisteret/api"
SOURCE_BASE = f"{API_BASE}/enheter"
USER_AGENT = "SignalpostStudentProject/1.0 (company research; contact: project maintainer)"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def validate_org_number(org_number: str) -> str:
    """Return normalized 9-digit Norwegian organization number or raise ValueError."""
    normalized = re.sub(r"[\s-]", "", str(org_number))
    if not re.fullmatch(r"\d{9}", normalized):
        raise ValueError("Enter a Norwegian organization number containing exactly 9 digits.")
    # Norwegian organization numbers use a mod-11 checksum.
    weights = (3, 2, 7, 6, 5, 4, 3, 2)
    remainder = sum(int(digit) * weight for digit, weight in zip(normalized[:8], weights)) % 11
    check_digit = 11 - remainder
    if check_digit == 11:
        check_digit = 0
    if check_digit == 10 or check_digit != int(normalized[8]):
        raise ValueError("The organization number failed the Norwegian mod-11 checksum.")
    return normalized


def _text(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, dict):
        return value.get("beskrivelse") or value.get("navn") or value.get("kode")
    return str(value)


def normalize_company(raw: dict[str, Any], retrieved_at: str | None = None) -> dict[str, Any]:
    """Normalize official registry JSON into a stable, evidence-backed profile."""
    org_number = str(raw.get("organisasjonsnummer", "")).strip()
    if not re.fullmatch(r"\d{9}", org_number):
        raise ValueError("Registry response did not contain a valid organization number.")
    source_url = f"{SOURCE_BASE}/{org_number}"
    observed_at = retrieved_at or utc_now()
    address = raw.get("forretningsadresse") or raw.get("postadresse") or {}
    street = address.get("adresse")
    if isinstance(street, list):
        street = ", ".join(str(part) for part in street if part)
    address_parts = [street, address.get("postnummer"), address.get("poststed"), address.get("land")]
    address_text = ", ".join(str(part) for part in address_parts if part)
    industry = raw.get("naeringskode1")
    profile = {
        "org_number": org_number,
        "name": _text(raw.get("navn")),
        "organization_form": _text(raw.get("organisasjonsform")),
        "status": "deleted" if raw.get("slettedato") else ("under_liquidation" if raw.get("underAvvikling") or raw.get("underTvangsavviklingEllerTvangsopplosning") else ("bankruptcy" if raw.get("konkurs") else "registered")),
        "address": address_text or None,
        "industry_code": _text(industry.get("kode")) if isinstance(industry, dict) else None,
        "industry": _text(industry.get("beskrivelse")) if isinstance(industry, dict) else None,
        "website": _text(raw.get("hjemmeside")),
        "employee_count": raw.get("antallAnsatte"),
        "vat_registered": raw.get("registrertIMvaregisteret"),
        "founded_date": _text(raw.get("stiftelsesdato")),
        "registered_date": _text(raw.get("registreringsdatoEnhetsregisteret")),
        "latest_accounts_year": raw.get("sisteInnsendteAarsregnskap"),
        "retrieved_at": observed_at,
        "source_url": source_url,
        "evidence": {},
    }
    for key, value in profile.items():
        if key not in {"evidence", "source_url", "retrieved_at", "org_number"} and value is not None:
            profile["evidence"][key] = {"source_url": source_url, "retrieved_at": observed_at, "source_field": key}
    return profile


class CompanyAgent:
    """Small deterministic agent; no LLM is needed to assert factual fields."""
    def __init__(self, timeout: int = 15, session: requests.Session | None = None):
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})

    def fetch(self, org_number: str) -> dict[str, Any]:
        org_number = validate_org_number(org_number)
        url = f"{SOURCE_BASE}/{org_number}"
        response = self.session.get(url, timeout=self.timeout)
        if response.status_code == 404:
            raise LookupError("No company was found for that organization number.")
        if response.status_code == 410:
            raise LookupError("The registry reports that this entity has been removed from publication.")
        response.raise_for_status()
        raw = response.json()
        # Identity guard: never publish a response for a different company number.
        if str(raw.get("organisasjonsnummer", "")) != org_number:
            raise ValueError("Company identity mismatch: registry response number differs from requested number.")
        return normalize_company(raw)
