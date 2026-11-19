"""Shared Pydantic models for HolidayPlanner.

These models are the contract between agents: the brief agent produces a
TripBrief, the scouts produce FlightOption / HotelOption lists, the weaver
produces DayPlans, the budget guardian produces a BudgetBreakdown, and the
responder assembles everything into a TripPlan.
"""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

Vibe = Literal[
    "foodie", "adventure", "relax", "beach", "business", "family", "culture"
]


class TripBrief(BaseModel):
    """Structured trip request produced by the brief agent."""

    origin: str
    origin_iata: str
    destination: str
    destination_iata: str
    start_date: date
    end_date: date
    days: int
    nights: int
    travelers: int = 2
    budget_usd: Optional[float] = None
    vibe: Vibe = "culture"
    raw_request: str = ""


class FlightOption(BaseModel):
    airline: str
    flight_no: str
    origin_iata: str
    destination_iata: str
    depart: str  # ISO datetime
    arrive: str  # ISO datetime
    duration_min: int
    stops: int
    price_usd: float
    tier: Literal["budget", "standard", "premium"]
    source: str = "simulated"


class HotelOption(BaseModel):
    name: str
    neighborhood: str
    tier: Literal["boutique", "comfort", "luxury"]
    stars: float
    rating: float
    nightly_usd: float
    vibe_tags: list[str] = Field(default_factory=list)
    blurb: str = ""
    source: str = "simulated"


class DayPlan(BaseModel):
    date: str  # ISO date
    day_number: int
    title: str
    morning: Optional[str] = None
    afternoon: Optional[str] = None
    evening: Optional[str] = None
    paid_activities: int = 0
    est_spend_usd: float = 0.0


class BudgetBreakdown(BaseModel):
    flights_total: float
    hotel_total: float
    activities_total: float
    grand_total: float
    budget_usd: Optional[float] = None
    status: Literal["ok", "over_budget_flagged", "no_budget_set"]
    revisions: int = 0


class TripPlan(BaseModel):
    thread_id: str
    request: str
    brief: TripBrief
    flight_pick: FlightOption
    flight_alternates: list[FlightOption] = Field(default_factory=list)
    hotel_pick: HotelOption
    hotel_alternates: list[HotelOption] = Field(default_factory=list)
    days: list[DayPlan] = Field(default_factory=list)
    budget: BudgetBreakdown
    notes: list[str] = Field(default_factory=list)
    created_at: str = ""
