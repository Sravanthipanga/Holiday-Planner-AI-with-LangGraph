"""Brief parser: natural-language trip request -> TripBrief.

The default path is a deterministic, rule-based parser (gazetteer matching,
date/duration phrases, budget and traveler extraction, vibe keywords). If
GROQ_API_KEY is set, a LangChain-Groq structured-output parse is attempted
first and any failure falls back to the rule parser — the rule parser is
always the safety net and always the default in tests/CI.
"""

from __future__ import annotations

import os
import re
from datetime import date, timedelta

from .gazetteer import City, find_cities
from .models import TripBrief

DEFAULT_ORIGIN_NAME = "Chicago"

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14,
}

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
    "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12,
}

VIBE_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("foodie", ("foodie", "food", "culinary", "restaurant", "eat", "dining", "cuisine")),
    ("adventure", ("adventure", "hiking", "hike", "outdoors", "adrenaline", "climbing", "trek")),
    ("beach", ("beach", "ocean", "surf", "island", "seaside", "snorkel")),
    ("relax", ("relax", "spa", "chill", "slow", "unwind", "peaceful", "laid-back", "laid back")),
    ("business", ("business", "work trip", "conference", "meeting", "expo")),
    ("family", ("family", "kids", "children", "toddler", "child-friendly")),
    ("culture", ("culture", "cultural", "museum", "history", "historic", "art", "heritage")),
]


def _num(token: str) -> int | None:
    token = token.lower()
    if token.isdigit():
        return int(token)
    return NUMBER_WORDS.get(token)


def _parse_cities(text: str) -> tuple[City | None, City | None]:
    """Return (origin, destination) using prepositions around city mentions."""
    mentions = find_cities(text)
    lowered = text.lower()
    if not mentions:
        return None, None
    origin: City | None = None
    destination: City | None = None
    for city, start, _end in mentions:
        before = lowered[max(0, start - 12):start]
        if re.search(r"\bfrom\s*$", before) or re.search(r"\bfrom\s+\w*\s*$", before):
            if origin is None:
                origin = city
                continue
        if re.search(r"(to|in|into|visit|visiting|explore|exploring|headed to|heading to)\s+$", before):
            if destination is None:
                destination = city
                continue
    remaining = [c for c, _, _ in mentions if c is not origin and c is not destination]
    if destination is None and remaining:
        destination = remaining[-1]
    if origin is None:
        rest = [c for c, _, _ in mentions if c is not destination]
        if rest:
            origin = rest[0]
    return origin, destination


def _month_start(month: int, today: date) -> date:
    """First day of the given month, this year or next if already past."""
    year = today.year
    if (month, 1) <= (today.month, today.day):
        if month <= today.month:
            year += 1
    return date(year, month, 1)


def _parse_dates(text: str, today: date) -> tuple[date, int]:
    """Return (start_date, days)."""
    lowered = text.lower()
    days: int | None = None

    m = re.search(r"\b(\d{1,2})\s*(?:days?|nights?)\b", lowered)
    if m:
        days = int(m.group(1))
    else:
        m = re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen)\s*(?:days?|nights?)\b", lowered)
        if m:
            days = NUMBER_WORDS[m.group(1)]
    if days is None:
        m = re.search(r"\b(\d+)\s*-\s*day\b", lowered)
        if m:
            days = int(m.group(1))
    if "long weekend" in lowered:
        days = days or 4
    elif "weekend" in lowered:
        days = days or 3
    if "two weeks" in lowered or "2 weeks" in lowered:
        days = days or 14
    elif "a week" in lowered or "one week" in lowered or "1 week" in lowered:
        days = days or 7

    # Explicit dates: YYYY-MM-DD, "June 12", "12 June", "June 12 to June 17".
    explicit: list[date] = []
    for m in re.finditer(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", lowered):
        explicit.append(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
    month_names = "|".join(MONTHS)
    for m in re.finditer(rf"\b({month_names})\s+(\d{{1,2}})(?:st|nd|rd|th)?\b", lowered):
        month, day = MONTHS[m.group(1)], int(m.group(2))
        year = today.year if (month, day) >= (today.month, today.day) else today.year + 1
        explicit.append(date(year, month, day))
    for m in re.finditer(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({month_names})\b", lowered):
        day, month = int(m.group(1)), MONTHS[m.group(2)]
        year = today.year if (month, day) >= (today.month, today.day) else today.year + 1
        explicit.append(date(year, month, day))
    explicit = sorted(set(explicit))

    start: date | None = None
    if explicit:
        start = explicit[0]
        if len(explicit) >= 2:
            days = (explicit[-1] - explicit[0]).days + 1
    elif "next month" in lowered:
        year = today.year + (1 if today.month == 12 else 0)
        month = today.month % 12 + 1
        start = date(year, month, 1)
    elif "next week" in lowered:
        start = today + timedelta(days=(7 - today.weekday()))  # next Monday
    else:
        m = re.search(rf"\bin\s+({month_names})\b", lowered)
        if m:
            start = _month_start(MONTHS[m.group(1)], today)
    if start is None:
        start = today + timedelta(days=30)

    if days is None:
        days = 5
    days = max(1, min(days, 21))
    return start, days


def _parse_travelers(text: str) -> int:
    lowered = text.lower()
    if "solo" in lowered or "just me" in lowered or "on my own" in lowered:
        return 1
    if "honeymoon" in lowered or "couple" in lowered or "anniversary" in lowered:
        return 2
    m = re.search(r"family of\s+(\d+|one|two|three|four|five|six|seven|eight)", lowered)
    if m:
        return _num(m.group(1)) or 4
    m = re.search(
        r"\bfor\s+(\d+|one|two|three|four|five|six|seven|eight)\b(?!\s*(?:days?|nights?|weeks?))",
        lowered,
    )
    if m:
        return _num(m.group(1)) or 2
    m = re.search(r"\b(\d+|two|three|four|five|six)\s+(?:people|travelers|travellers|adults|persons|of us)\b", lowered)
    if m:
        return _num(m.group(1)) or 2
    m = re.search(r"\bgroup of\s+(\d+|two|three|four|five|six|seven|eight)\b", lowered)
    if m:
        return _num(m.group(1)) or 2
    return 2


def _parse_budget(text: str) -> float | None:
    m = re.search(r"\$\s*([\d,]+(?:\.\d+)?)\s*(k)?\b", text)
    if m:
        value = float(m.group(1).replace(",", ""))
        if m.group(2):
            value *= 1000
        return value
    m = re.search(
        r"(?:under|below|max(?:imum)?|budget of|around|about|up to)\s+\$?\s*([\d,]{3,}(?:\.\d+)?)",
        text.lower(),
    )
    if m:
        return float(m.group(1).replace(",", ""))
    return None


def _parse_vibe(text: str) -> str:
    lowered = text.lower()
    for vibe, keywords in VIBE_KEYWORDS:
        if any(k in lowered for k in keywords):
            return vibe
    return "culture"


def parse_brief_rules(text: str, today: date | None = None) -> TripBrief:
    """Deterministic rule-based parse (the default path)."""
    today = today or date.today()
    origin, destination = _parse_cities(text)
    from .gazetteer import city_by_name

    if destination is None:
        destination = city_by_name("Paris")
    if origin is None or origin.name == destination.name:
        origin = city_by_name(DEFAULT_ORIGIN_NAME)
        if origin.name == destination.name:
            origin = city_by_name("New York")
    start, days = _parse_dates(text, today)
    end = start + timedelta(days=days - 1)
    return TripBrief(
        origin=origin.name,
        origin_iata=origin.iata,
        destination=destination.name,
        destination_iata=destination.iata,
        start_date=start,
        end_date=end,
        days=days,
        nights=days - 1 if days > 1 else 1,
        travelers=_parse_travelers(text),
        budget_usd=_parse_budget(text),
        vibe=_parse_vibe(text),  # type: ignore[arg-type]
        raw_request=text,
    )


def parse_brief(text: str, today: date | None = None) -> tuple[TripBrief, str]:
    """Parse a request, optionally via Groq first. Returns (brief, parser_used).

    parser_used is "groq" only when the LLM path succeeded end-to-end;
    otherwise "rules". The GROQ path never raises out of this function.
    """
    if os.environ.get("GROQ_API_KEY"):
        try:
            return _parse_brief_groq(text, today), "groq"
        except Exception:
            pass  # fall through to the deterministic parser
    return parse_brief_rules(text, today), "rules"


def _parse_brief_groq(text: str, today: date | None) -> TripBrief:
    """Optional LangChain-Groq structured-output parse (requires GROQ_API_KEY)."""
    from langchain_groq import ChatGroq

    today = today or date.today()
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    structured = llm.with_structured_output(TripBrief)
    prompt = (
        f"Today is {today.isoformat()}. Parse this trip request into the "
        f"schema. Use IATA codes (Chicago=ORD, New York=JFK, Paris=CDG, "
        f"Tokyo=HND, London=LHR, Rome=FCO, Sydney=SYD, Dubai=DXB, Bali=DPS). "
        f"If no origin is stated, use Chicago (ORD). nights = days - 1 "
        f"(minimum 1). Request: {text}"
    )
    brief = structured.invoke(prompt)
    brief.raw_request = text
    return brief
