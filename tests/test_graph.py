"""End-to-end graph runs."""

from holidayplanner.graph import build_graph, run_plan


def test_graph_has_all_seven_agents():
    graph = build_graph()
    names = set(graph.get_graph().nodes)
    assert {
        "brief_agent", "flight_scout", "hotel_scout", "itinerary_weaver",
        "budget_guardian", "plan_critic", "responder",
    } <= names


def test_end_to_end_paris_plan_shape():
    plan = run_plan(
        "Plan a 5-day foodie trip from Chicago to Paris next month, budget $2,500 for 2 people",
        thread_id="test-paris",
    )
    assert plan["brief"]["destination"] == "Paris"
    assert len(plan["days"]) == 5
    assert plan["flight_pick"]["origin_iata"] == "ORD"
    assert plan["flight_pick"]["destination_iata"] == "CDG"
    assert len(plan["flight_alternates"]) == 2
    assert len(plan["hotel_alternates"]) == 2
    budget = plan["budget"]
    assert budget["status"] in ("ok", "over_budget_flagged")
    if budget["status"] == "ok":
        assert budget["grand_total"] <= budget["budget_usd"]
    # day 1 always opens with the arrival, never a pre-landing activity
    assert plan["days"][0]["morning"].startswith("Arrive in Paris")
    assert any("critic" in n.lower() for n in plan["notes"])


def test_tight_budget_ends_flagged_not_fudged():
    plan = run_plan(
        "3-day trip from Chicago to New York for 2 people, budget $300",
        thread_id="test-tight",
    )
    budget = plan["budget"]
    assert budget["status"] == "over_budget_flagged"
    assert budget["revisions"] == 2
    assert budget["grand_total"] > 300  # honest numbers, not trimmed to fit
