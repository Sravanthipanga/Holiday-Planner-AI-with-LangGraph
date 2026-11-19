"""SQLite plan store round-trip."""

from holidayplanner.store import SqliteStore


def test_sqlite_roundtrip(tmp_path):
    store = SqliteStore(tmp_path / "plans.db")
    plan = {"thread_id": "abc", "brief": {"destination": "Rome"}}
    store.save("abc", "trip to Rome", plan)
    assert store.get("abc") == plan
    assert store.get("missing") is None
    store.save("abc", "trip to Rome v2", {"thread_id": "abc", "v": 2})
    assert store.get("abc")["v"] == 2
