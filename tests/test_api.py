"""FastAPI surface: pages, JSON API, persistence, static artwork."""

from fastapi.testclient import TestClient

from holidayplanner.app import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_home_page_has_art_and_form():
    r = client.get("/")
    assert r.status_code == 200
    html = r.text
    assert "Holiday Planner AI with LangGraph" in html
    assert "/static/img/art-1.jpg" in html
    assert "/static/img/art-2.jpg" in html
    assert "/static/img/art-3.jpg" in html
    assert "foodie trip from Chicago to Paris" in html  # a sample chip


def test_api_plan_and_saved_trip_roundtrip():
    r = client.post("/api/plan", json={
        "request": "Weekend getaway to Miami from Chicago, budget $900",
        "thread_id": "api-test-1",
    })
    assert r.status_code == 200
    plan = r.json()
    assert plan["brief"]["destination"] == "Miami"
    assert len(plan["days"]) == 3
    r2 = client.get("/api/trips/api-test-1")
    assert r2.status_code == 200
    assert r2.json()["brief"]["destination"] == "Miami"


def test_saved_trip_404():
    assert client.get("/api/trips/does-not-exist").status_code == 404


def test_form_plan_page_renders_cards():
    r = client.post("/plan", data={
        "trip_request": "4-day culture trip from Chicago to London, budget $1,800 for 2",
    })
    assert r.status_code == 200
    html = r.text
    assert "London" in html
    assert "Flight pick" in html
    assert "Hotel pick" in html
    assert "Day by day" in html
    assert "/static/img/art-1.jpg" in html  # plan-page header art


def test_artwork_is_served():
    for name in ("art-1.jpg", "art-2.jpg", "art-3.jpg"):
        r = client.get(f"/static/img/{name}")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("image/")
