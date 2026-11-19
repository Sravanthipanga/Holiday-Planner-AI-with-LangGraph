"""City gazetteer: ~27 major cities with IATA codes and coordinates.

Used by the brief parser (name matching) and by the simulated flight
provider (haversine distance -> duration / price model).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class City:
    name: str
    iata: str
    country: str
    lat: float
    lon: float
    aliases: tuple[str, ...] = field(default_factory=tuple)
    # Rough mid-range nightly hotel price (USD) for the simulated hotel engine.
    hotel_base_usd: float = 130.0


CITIES: list[City] = [
    City("Chicago", "ORD", "USA", 41.878, -87.630, ("chicago", "chi-town"), 150),
    City("New York", "JFK", "USA", 40.713, -74.006, ("new york", "nyc", "new york city"), 220),
    City("Los Angeles", "LAX", "USA", 34.052, -118.243, ("los angeles", "la", "l.a."), 180),
    City("San Francisco", "SFO", "USA", 37.775, -122.419, ("san francisco", "sf"), 210),
    City("Miami", "MIA", "USA", 25.762, -80.192, ("miami",), 170),
    City("Seattle", "SEA", "USA", 47.606, -122.332, ("seattle",), 160),
    City("Boston", "BOS", "USA", 42.360, -71.059, ("boston",), 190),
    City("Denver", "DEN", "USA", 39.739, -104.990, ("denver",), 140),
    City("Austin", "AUS", "USA", 30.267, -97.743, ("austin",), 150),
    City("Las Vegas", "LAS", "USA", 36.170, -115.140, ("las vegas", "vegas"), 120),
    City("Honolulu", "HNL", "USA", 21.307, -157.858, ("honolulu", "hawaii", "oahu"), 240),
    City("Toronto", "YYZ", "Canada", 43.653, -79.383, ("toronto",), 160),
    City("London", "LHR", "United Kingdom", 51.507, -0.128, ("london",), 200),
    City("Paris", "CDG", "France", 48.857, 2.352, ("paris",), 185),
    City("Rome", "FCO", "Italy", 41.903, 12.496, ("rome", "roma"), 150),
    City("Madrid", "MAD", "Spain", 40.417, -3.704, ("madrid",), 130),
    City("Barcelona", "BCN", "Spain", 41.387, 2.170, ("barcelona",), 140),
    City("Amsterdam", "AMS", "Netherlands", 52.370, 4.895, ("amsterdam",), 165),
    City("Berlin", "BER", "Germany", 52.520, 13.405, ("berlin",), 120),
    City("Dublin", "DUB", "Ireland", 53.350, -6.260, ("dublin",), 155),
    City("Reykjavik", "KEF", "Iceland", 64.147, -21.940, ("reykjavik", "iceland"), 170),
    City("Tokyo", "HND", "Japan", 35.676, 139.650, ("tokyo",), 145),
    City("Seoul", "ICN", "South Korea", 37.567, 126.978, ("seoul",), 120),
    City("Bangkok", "BKK", "Thailand", 13.756, 100.502, ("bangkok",), 80),
    City("Singapore", "SIN", "Singapore", 1.352, 103.820, ("singapore",), 175),
    City("Sydney", "SYD", "Australia", -33.869, 151.209, ("sydney",), 170),
    City("Dubai", "DXB", "UAE", 25.205, 55.271, ("dubai",), 160),
    City("Bali", "DPS", "Indonesia", -8.650, 115.217, ("bali", "denpasar"), 90),
]

_BY_IATA = {c.iata: c for c in CITIES}
_BY_NAME = {c.name.lower(): c for c in CITIES}


def city_by_iata(iata: str) -> City:
    return _BY_IATA[iata.upper()]


def city_by_name(name: str) -> City | None:
    return _BY_NAME.get(name.lower())


def haversine_km(a: City, b: City) -> float:
    """Great-circle distance between two gazetteer cities, in kilometres."""
    r = 6371.0
    p1, p2 = math.radians(a.lat), math.radians(b.lat)
    dphi = math.radians(b.lat - a.lat)
    dlmb = math.radians(b.lon - a.lon)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def find_cities(text: str) -> list[tuple[City, int, int]]:
    """Find gazetteer city mentions in text.

    Returns a list of (city, start, end) spans, longest aliases first so
    'New York City' wins over 'New York'. Overlapping spans are de-duped.
    """
    lowered = text.lower()
    matches: list[tuple[City, int, int]] = []
    candidates: list[tuple[str, City]] = []
    for city in CITIES:
        for alias in (city.name.lower(), *city.aliases):
            candidates.append((alias, city))
    candidates.sort(key=lambda t: -len(t[0]))
    claimed: list[tuple[int, int]] = []
    for alias, city in candidates:
        for m in re.finditer(r"(?<![a-z])" + re.escape(alias) + r"(?![a-z])", lowered):
            s, e = m.start(), m.end()
            if any(s < ce and e > cs for cs, ce in claimed):
                continue
            claimed.append((s, e))
            matches.append((city, s, e))
    matches.sort(key=lambda t: t[1])
    return matches
