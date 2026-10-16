from signalpost.database import save_profile, get_profile, history_for, profile_count


def sample(name="Example AS", retrieved_at="2026-10-16T10:00:00+00:00"):
    return {"org_number": "923609016", "name": name, "status": "registered", "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/923609016", "retrieved_at": retrieved_at, "evidence": {}}


def test_save_new_and_detect_change(tmp_path):
    db = tmp_path / "test.db"
    first = save_profile(sample(), db)
    assert first["is_new"] is True
    assert first["changes"] == []
    second = save_profile(sample("Example Norway AS", "2026-10-16T11:00:00+00:00"), db)
    assert second["is_new"] is False
    assert second["changes"][0]["field"] == "name"
    assert get_profile("923609016", db)["name"] == "Example Norway AS"
    assert len(history_for("923609016", db)) == 2
    assert profile_count(db) == 1
