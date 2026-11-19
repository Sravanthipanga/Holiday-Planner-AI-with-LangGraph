"""Provider determinism, picking logic, and live-provider fallback."""

import httpx
import pytest

from holidayplanner.parser import parse_brief_rules
from holidayplanner.providers.flights import (
    AviationStackFlights,
    SimulatedFlights,
    pick_flight,
)
from holidayplanner.providers.hotels import SimulatedHotels, TavilyHotels, pick_hotel

BRIEF = parse_brief_rules("5-day foodie trip from Chicago to Paris, budget $2,500 for 2")


def test_simulated_flights_deterministic():
    a, _ = SimulatedFlights().search(BRIEF)
    b, _ = SimulatedFlights().search(BRIEF)
    assert [f.model_dump() for f in a] == [f.model_dump() for f in b]
    assert len(a) == 3
    assert {f.tier for f in a} == {"budget", "standard", "premium"}


def test_simulated_hotels_deterministic():
    a, _ = SimulatedHotels().search(BRIEF)
    b, _ = SimulatedHotels().search(BRIEF)
    assert [h.model_dump() for h in a] == [h.model_dump() for h in b]
    assert len(a) == 3
    assert all(BRIEF.vibe in h.vibe_tags for h in a)


def test_pick_flight_cheapest():
    options, _ = SimulatedFlights().search(BRIEF)
    pick = pick_flight(options, "cheapest")
    assert pick.price_usd == min(f.price_usd for f in options)


def test_pick_hotel_cheapest():
    options, _ = SimulatedHotels().search(BRIEF)
    pick = pick_hotel(options, BRIEF, "cheapest")
    assert pick.nightly_usd == min(h.nightly_usd for h in options)


def test_aviationstack_failure_falls_back(monkeypatch):
    def boom(*args, **kwargs):
        raise httpx.ConnectError("no network", request=httpx.Request("GET", "http://x"))

    monkeypatch.setattr(httpx, "get", boom)
    options, note = AviationStackFlights("bad-key").search(BRIEF)
    assert len(options) == 3
    assert all(f.source == "simulated" for f in options)
    assert note and "simulated" in note


def test_tavily_failure_falls_back(monkeypatch):
    def boom(*args, **kwargs):
        raise httpx.ConnectError("no network", request=httpx.Request("POST", "http://x"))

    monkeypatch.setattr(httpx, "post", boom)
    options, note = TavilyHotels("bad-key").search(BRIEF)
    assert len(options) == 3
    assert all(h.source == "simulated" for h in options)
    assert note and "simulated" in note


def test_flight_times_are_coherent():
    options, _ = SimulatedFlights().search(BRIEF)
    for f in options:
        assert f.arrive > f.depart
        assert f.duration_min >= 55
        assert f.price_usd > 0
