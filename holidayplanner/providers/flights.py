"""Flight providers.

SimulatedFlights (default) generates deterministic options from the
city-pair distance: same (origin, destination, date, preference) always
yields the same flights, which keeps tests and evals reproducible.

AviationStackFlights calls api.aviationstack.com when AVIATIONSTACK_API_KEY
is set. AviationStack does not publish fares, so prices are estimated with
the same distance model and flagged in the option source. Any error or
empty result falls back to the simulated engine.
"""

from __future__ import annotations

import os
import random
from datetime import datetime, timedelta
from typing import Protocol

from ..gazetteer import city_by_iata, haversine_km
from ..models import FlightOption, TripBrief

AIRLINES = [
    ("United", "UA"), ("American", "AA"), ("Delta", "DL"), ("Southwest", "WN"),
    ("JetBlue", "B6"), ("Alaska", "AS"), ("Air France", "AF"),
    ("British Airways", "BA"), ("Lufthansa", "LH"), ("ANA", "NH"),
    ("Emirates", "EK"), ("Qantas", "QF"),
]


def _seeded_rng(*parts: object) -> random.Random:
    return random.Random("|".join(str(p) for p in parts))


def _price_for(distance_km: float, tier_mult: float, rng: random.Random) -> float:
    base = 45.0 + distance_km * 0.075
    return round(base * tier_mult * rng.uniform(0.92, 1.12), 2)


def _duration_for(distance_km: float, stops: int) -> int:
    cruise = distance_km / 800.0 * 60  # ~800 km/h average
    return int(max(55, cruise + 40 + stops * 95))


class FlightProvider(Protocol):
    name: str

    def search(self, brief: TripBrief, preference: str = "recommended") -> tuple[list[FlightOption], str | None]:
        """Return (options, fallback_note). fallback_note is set when a live
        provider failed and the simulated engine answered instead."""
        ...


class SimulatedFlights:
    name = "simulated"

    def search(self, brief: TripBrief, preference: str = "recommended") -> tuple[list[FlightOption], str | None]:
        origin = city_by_iata(brief.origin_iata)
        dest = city_by_iata(brief.destination_iata)
        distance = haversine_km(origin, dest)
        rng = _seeded_rng(brief.origin_iata, brief.destination_iata, brief.start_date.isoformat())
        long_haul = distance > 5500

        specs = [
            # (tier, depart time, stops, price multiplier)
            ("budget", (6, 40), 1 if long_haul else 0, 0.78),
            ("standard", (9, 25), 0, 1.0),
            ("premium", (17, 50), 0, 1.5),
        ]
        options: list[FlightOption] = []
        for tier, (hh, mm), stops, mult in specs:
            airline, code = AIRLINES[rng.randrange(len(AIRLINES))]
            duration = _duration_for(distance, stops)
            depart = datetime.combine(brief.start_date, datetime.min.time()).replace(hour=hh, minute=mm)
            arrive = depart + timedelta(minutes=duration)
            options.append(
                FlightOption(
                    airline=airline,
                    flight_no=f"{code}{rng.randint(100, 989)}",
                    origin_iata=brief.origin_iata,
                    destination_iata=brief.destination_iata,
                    depart=depart.isoformat(timespec="minutes"),
                    arrive=arrive.isoformat(timespec="minutes"),
                    duration_min=duration,
                    stops=stops,
                    price_usd=_price_for(distance, mult, rng),
                    tier=tier,  # type: ignore[arg-type]
                    source="simulated",
                )
            )
        return options, None


class AviationStackFlights:
    name = "aviationstack"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._fallback = SimulatedFlights()

    def search(self, brief: TripBrief, preference: str = "recommended") -> tuple[list[FlightOption], str | None]:
        import httpx

        try:
            resp = httpx.get(
                "http://api.aviationstack.com/v1/flights",
                params={
                    "access_key": self.api_key,
                    "dep_iata": brief.origin_iata,
                    "arr_iata": brief.destination_iata,
                    "flight_date": brief.start_date.isoformat(),
                    "limit": 25,
                },
                timeout=12.0,
            )
            resp.raise_for_status()
            data = resp.json().get("data") or []
            options: list[FlightOption] = []
            origin = city_by_iata(brief.origin_iata)
            dest = city_by_iata(brief.destination_iata)
            distance = haversine_km(origin, dest)
            rng = _seeded_rng("aviationstack", brief.origin_iata, brief.destination_iata, brief.start_date)
            seen_routes = set()
            for item in data:
                dep = (item.get("departure") or {}).get("scheduled")
                arr = (item.get("arrival") or {}).get("scheduled")
                airline = (item.get("airline") or {}).get("name") or "Unknown airline"
                flight_no = (item.get("flight") or {}).get("iata") or "—"
                if not dep or not arr or flight_no in seen_routes:
                    continue
                seen_routes.add(flight_no)
                dep_dt = datetime.fromisoformat(dep.replace("Z", "+00:00")).replace(tzinfo=None)
                arr_dt = datetime.fromisoformat(arr.replace("Z", "+00:00")).replace(tzinfo=None)
                duration = max(30, int((arr_dt - dep_dt).total_seconds() // 60))
                options.append(
                    FlightOption(
                        airline=airline,
                        flight_no=flight_no,
                        origin_iata=brief.origin_iata,
                        destination_iata=brief.destination_iata,
                        depart=dep_dt.isoformat(timespec="minutes"),
                        arrive=arr_dt.isoformat(timespec="minutes"),
                        duration_min=duration,
                        stops=0,
                        price_usd=_price_for(distance, 1.0, rng),
                        tier="standard",
                        source="aviationstack (fare estimated)",
                    )
                )
                if len(options) >= 3:
                    break
            if not options:
                raise ValueError("AviationStack returned no usable flights")
            return options, None
        except Exception as exc:  # any failure -> simulated, honestly noted
            options, _ = self._fallback.search(brief, preference)
            return options, f"AviationStack lookup failed ({type(exc).__name__}); simulated flights used instead."


def pick_flight(options: list[FlightOption], preference: str = "recommended") -> FlightOption:
    """Choose the recommended flight.

    preference == "cheapest" (set by the budget guardian) picks the lowest
    fare; otherwise a simple value score balances price, stops and duration.
    """
    if preference == "cheapest":
        return min(options, key=lambda f: f.price_usd)

    def value(f: FlightOption) -> float:
        return f.price_usd + f.stops * 45 + f.duration_min * 0.15

    return min(options, key=value)


def get_flight_provider() -> FlightProvider:
    key = os.environ.get("AVIATIONSTACK_API_KEY")
    if key:
        return AviationStackFlights(key)
    return SimulatedFlights()
