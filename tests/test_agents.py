"""Agent node behavior: weaver arrival rules, guardian loop, critic checks."""

from holidayplanner.agents import nodes
from holidayplanner.models import DayPlan, TripBrief
from holidayplanner.parser import parse_brief_rules


def _flight_pick(arrive: str, price: float = 400.0) -> dict:
    return {
        "airline": "United", "flight_no": "UA100", "origin_iata": "ORD",
        "destination_iata": "HND", "depart": "2027-06-01T09:00",
        "arrive": arrive, "duration_min": 600, "stops": 0,
        "price_usd": price, "tier": "standard", "source": "simulated",
    }


def _tokyo_brief(days: int = 4) -> TripBrief:
    return parse_brief_rules(f"{days}-day culture trip from Chicago to Tokyo")


def test_weaver_day_count_matches_brief():
    brief = _tokyo_brief(7)
    state = {"brief": brief.model_dump(mode="json"),
             "flight_pick": _flight_pick("2027-06-01T10:00")}
    out = nodes.itinerary_weaver(state)
    assert len(out["days"]) == 7
    dates = [d["date"] for d in out["days"]]
    assert dates == sorted(dates) and len(set(dates)) == 7


def test_weaver_late_arrival_day_is_light():
    brief = _tokyo_brief(4)
    state = {"brief": brief.model_dump(mode="json"),
             "flight_pick": _flight_pick("2027-06-01T19:40")}
    out = nodes.itinerary_weaver(state)
    day1 = out["days"][0]
    assert day1["morning"].startswith("Arrive in Tokyo")
    assert day1["afternoon"] is None  # nothing before/without settling in
    assert day1["paid_activities"] == 0


def test_weaver_morning_arrival_gets_afternoon_activity():
    brief = _tokyo_brief(4)
    state = {"brief": brief.model_dump(mode="json"),
             "flight_pick": _flight_pick("2027-06-01T08:15")}
    out = nodes.itinerary_weaver(state)
    day1 = out["days"][0]
    assert day1["afternoon"] is not None
    # departure day never has an evening activity
    assert out["days"][-1]["evening"] is None


def _guardian_state(revisions: int) -> dict:
    brief = parse_brief_rules("5-day trip from Chicago to Paris, budget $1,000 for 2")
    days = [
        DayPlan(date="2026-12-0%d" % (i + 1), day_number=i + 1, title="Day",
                morning="x", est_spend_usd=200.0).model_dump(mode="json")
        for i in range(5)
    ]
    return {
        "brief": brief.model_dump(mode="json"),
        "flight_pick": {**_flight_pick("2026-12-01T10:00", price=887.0),
                        "destination_iata": "CDG"},
        "hotel_pick": {"name": "Lux", "neighborhood": "1st", "tier": "luxury",
                       "stars": 5.0, "rating": 9.5, "nightly_usd": 321.0,
                       "vibe_tags": ["culture"], "blurb": "", "source": "simulated"},
        "days": days,
        "budget_revisions": revisions,
    }


def test_guardian_requests_revision_when_over_budget():
    out = nodes.budget_guardian(_guardian_state(0))
    assert out["swap_pending"] is True
    assert out["budget_revisions"] == 1
    assert out["flight_preference"] == "cheapest"
    assert nodes.route_after_budget(out) == "revise"


def test_guardian_flags_honestly_after_max_revisions():
    out = nodes.budget_guardian(_guardian_state(2))
    assert out["budget"]["status"] == "over_budget_flagged"
    assert out["budget"]["grand_total"] > out["budget"]["budget_usd"]
    assert out["swap_pending"] is False
    assert nodes.route_after_budget(out) == "critic"


def _critic_state(revisions: int) -> dict:
    brief = _tokyo_brief(3)
    days = [
        DayPlan(date="2027-06-01", day_number=1, title="Bad day",
                morning="Sunrise hike", afternoon="Museum", evening=None,
                paid_activities=1, est_spend_usd=50).model_dump(mode="json"),
        DayPlan(date="2027-06-02", day_number=2, title="Empty",
                paid_activities=0, est_spend_usd=0).model_dump(mode="json"),
        DayPlan(date="2027-06-03", day_number=3, title="Stuffed",
                morning="a", afternoon="b", evening="c",
                paid_activities=4, est_spend_usd=300).model_dump(mode="json"),
    ]
    return {
        "brief": brief.model_dump(mode="json"),
        "flight_pick": _flight_pick("2027-06-01T23:40"),
        "days": days,
        "critic_revisions": revisions,
    }


def test_critic_catches_clashes_and_loops_once():
    out = nodes.plan_critic(_critic_state(0))
    issues = " ".join(out["critic_issues"])
    assert "before the flight lands" in issues
    assert "empty" in issues
    assert "overstuffed" in issues
    assert out["critic_loop"] is True
    assert nodes.route_after_critic(out) == "revise"


def test_critic_accepts_after_max_revisions():
    out = nodes.plan_critic(_critic_state(1))
    assert out["critic_issues"]  # issues still reported...
    assert out["critic_loop"] is False  # ...but no second loop
    assert nodes.route_after_critic(out) == "respond"
