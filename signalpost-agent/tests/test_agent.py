import pytest
from signalpost.agent import normalize_company, validate_org_number

# The checksum helper tests a syntactically valid example generated for the test suite.
def test_validate_rejects_wrong_length():
    with pytest.raises(ValueError):
        validate_org_number("12345")

def test_validate_rejects_bad_checksum():
    with pytest.raises(ValueError):
        validate_org_number("123456789")

def test_normalize_company_keeps_source_evidence():
    raw = {
        "organisasjonsnummer": "923609016",
        "navn": "Example AS",
        "organisasjonsform": {"kode": "AS", "beskrivelse": "Aksjeselskap"},
        "forretningsadresse": {"adresse": ["Testgata 1"], "postnummer": "0150", "poststed": "Oslo", "land": "Norge"},
        "naeringskode1": {"kode": "62.010", "beskrivelse": "Programming services"},
        "registrertIMvaregisteret": True,
    }
    profile = normalize_company(raw, "2026-10-16T00:00:00+00:00")
    assert profile["org_number"] == "923609016"
    assert profile["name"] == "Example AS"
    assert profile["source_url"].endswith("/923609016")
    assert profile["evidence"]["name"]["source_url"] == profile["source_url"]
    assert profile["retrieved_at"].startswith("2026-")

def test_missing_fields_remain_none():
    profile = normalize_company({"organisasjonsnummer": "923609016", "navn": "Example AS"})
    assert profile["website"] is None
    assert profile["employee_count"] is None
