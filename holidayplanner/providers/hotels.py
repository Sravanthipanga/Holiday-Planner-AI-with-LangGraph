"""Hotel providers.

SimulatedHotels (default) builds deterministic, vibe-tagged options from
per-city name/neighborhood banks and a city price index. TavilyHotels uses
Tavily web search when TAVILY_API_KEY is set (names/ratings from search
results, nightly prices estimated from the city index and flagged); any
failure falls back to the simulated engine with a note.
"""

from __future__ import annotations

import os
import random
from typing import Protocol

from ..gazetteer import city_by_name
from ..models import HotelOption, TripBrief

NEIGHBORHOODS: dict[str, list[str]] = {
    "Paris": ["Le Marais", "Saint-Germain", "Montmartre", "Latin Quarter"],
    "Tokyo": ["Shinjuku", "Asakusa", "Ginza", "Shibuya"],
    "New York": ["Midtown", "Williamsburg", "Upper West Side", "SoHo"],
    "London": ["Soho", "Shoreditch", "South Kensington", "Bloomsbury"],
    "Rome": ["Trastevere", "Monti", "Prati", "Centro Storico"],
    "Sydney": ["The Rocks", "Surry Hills", "Bondi", "Circular Quay"],
    "Dubai": ["Downtown", "Jumeirah", "Deira", "Dubai Marina"],
    "Bali": ["Ubud", "Seminyak", "Canggu", "Uluwatu"],
}
GENERIC_NEIGHBORHOODS = ["Old Town", "City Center", "Riverside", "Arts District"]

NAME_PATTERNS = [
    "Hotel {adj} {noun}", "The {noun} House", "{hood} {noun} Hotel",
    "Maison {adj}", "{adj} {noun} Suites",
]
ADJECTIVES = ["Golden", "Velvet", "Azure", "Amber", "Willow", "Juniper", "Scarlet", "Ivory"]
NOUNS = ["Lantern", "Compass", "Voyager", "Atlas", "Meridian", "Harbor", "Saffron", "Juniper"]

TIER_SPECS = [
    # (tier, stars, rating base, price multiplier, vibe flavor)
    ("boutique", 3.5, 8.4, 0.78),
    ("comfort", 4.0, 8.8, 1.0),
    ("luxury", 5.0, 9.4, 1.65),
]

VIBE_BLURBS = {
    "foodie": "Steps from beloved bistros and morning markets.",
    "adventure": "Trail-savvy concierge and early breakfasts for big days out.",
    "relax": "Quiet courtyard, spa on site, and famously slow mornings.",
    "beach": "Barefoot distance from the sand with sunset-facing terraces.",
    "business": "Fast wifi, a real desk, and express laundry.",
    "family": "Family rooms, a pool, and staff who actually like kids.",
    "culture": "In the historic quarter, surrounded by museums and bookshops.",
}


class HotelProvider(Protocol):
    name: str

    def search(self, brief: TripBrief, preference: str = "recommended") -> tuple[list[HotelOption], str | None]:
        ...


def _rng_for(brief: TripBrief) -> random.Random:
    return random.Random(f"hotels|{brief.destination_iata}|{brief.start_date.isoformat()}")


class SimulatedHotels:
    name = "simulated"

    def search(self, brief: TripBrief, preference: str = "recommended") -> tuple[list[HotelOption], str | None]:
        city = city_by_name(brief.destination)
        base = city.hotel_base_usd if city else 130.0
        hoods = NEIGHBORHOODS.get(brief.destination, GENERIC_NEIGHBORHOODS)
        rng = _rng_for(brief)
        options: list[HotelOption] = []
        used_names: set[str] = set()
        for tier, stars, rating_base, mult in TIER_SPECS:
            hood = hoods[rng.randrange(len(hoods))]
            for _ in range(10):  # find an unused name
                pattern = NAME_PATTERNS[rng.randrange(len(NAME_PATTERNS))]
                name = pattern.format(
                    adj=ADJECTIVES[rng.randrange(len(ADJECTIVES))],
                    noun=NOUNS[rng.randrange(len(NOUNS))],
                    hood=hood,
                )
                if name not in used_names:
                    used_names.add(name)
                    break
            nightly = round(base * mult * rng.uniform(0.9, 1.14), 2)
            tags = [brief.vibe, "culture"] if tier != "luxury" else [brief.vibe, "relax"]
            options.append(
                HotelOption(
                    name=name,
                    neighborhood=hood,
                    tier=tier,  # type: ignore[arg-type]
                    stars=stars,
                    rating=round(min(9.9, rating_base + rng.uniform(0, 0.5)), 1),
                    nightly_usd=nightly,
                    vibe_tags=sorted(set(tags)),
                    blurb=VIBE_BLURBS.get(brief.vibe, VIBE_BLURBS["culture"]),
                    source="simulated",
                )
            )
        return options, None


class TavilyHotels:
    name = "tavily"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._fallback = SimulatedHotels()

    def search(self, brief: TripBrief, preference: str = "recommended") -> tuple[list[HotelOption], str | None]:
        import httpx

        try:
            resp = httpx.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.api_key,
                    "query": f"best {brief.vibe} hotels in {brief.destination} neighborhoods to stay",
                    "max_results": 8,
                    "search_depth": "basic",
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            results = resp.json().get("results") or []
            if not results:
                raise ValueError("Tavily returned no hotel results")
            simulated, _ = self._fallback.search(brief, preference)
            options: list[HotelOption] = []
            for sim, result in zip(simulated, results):
                title = (result.get("title") or sim.name).split(" - ")[0].split(" | ")[0].strip()
                options.append(
                    sim.model_copy(
                        update={
                            "name": title[:60] or sim.name,
                            "source": "tavily (nightly rate estimated)",
                        }
                    )
                )
            return options, None
        except Exception as exc:
            options, _ = self._fallback.search(brief, preference)
            return options, f"Tavily hotel search failed ({type(exc).__name__}); simulated hotels used instead."


def pick_hotel(
    options: list[HotelOption],
    brief: TripBrief,
    preference: str = "recommended",
) -> HotelOption:
    """Pick the recommended hotel.

    "cheapest" (budget guardian) picks the lowest nightly rate. Otherwise:
    vibe match first, then best rating-per-dollar, biased toward the
    per-night hotel cap implied by the trip budget when one is set.
    """
    if preference == "cheapest":
        return min(options, key=lambda h: h.nightly_usd)
    cap: float | None = None
    if brief.budget_usd:
        cap = (brief.budget_usd * 0.35) / max(1, brief.nights)

    def score(h: HotelOption) -> float:
        s = (2.0 if brief.vibe in h.vibe_tags else 0.0) + h.rating / 10.0
        s -= h.nightly_usd / 400.0
        if cap is not None and h.nightly_usd > cap:
            s -= 1.5  # over the implied nightly cap: deprioritize
        return s

    return max(options, key=score)


def get_hotel_provider() -> HotelProvider:
    key = os.environ.get("TAVILY_API_KEY")
    if key:
        return TavilyHotels(key)
    return SimulatedHotels()
