"""The seven agent nodes of the HolidayPlanner graph.

Flow: brief -> flight_scout -> hotel_scout -> itinerary_weaver ->
budget_guardian -> (loop back to flight_scout on swap instructions) ->
plan_critic -> (loop back to itinerary_weaver on issues) -> responder.

State is a plain dict (see graph.TripState); nodes return partial updates.
Pydantic models are serialized with model_dump(mode="json") so the state
stays JSON-friendly for checkpointing and persistence.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from ..models import BudgetBreakdown, DayPlan, TripBrief, TripPlan
from ..parser import parse_brief
from ..providers.activities import Activity, bank_for
from ..providers.flights import get_flight_provider, pick_flight
from ..providers.hotels import get_hotel_provider, pick_hotel

MAX_BUDGET_REVISIONS = 2
MAX_CRITIC_REVISIONS = 1
DAILY_FOOD_ALLOWANCE = 45.0  # per traveler per day, meals not in activities


def _brief(state: dict) -> TripBrief:
    return TripBrief.model_validate(state["brief"])


# ---------------------------------------------------------------- brief agent
def brief_agent(state: dict) -> dict:
    brief, parser_used = parse_brief(state["request"])
    notes = [f"Brief parsed with the {parser_used} parser."]
    return {"brief": brief.model_dump(mode="json"), "notes": notes}


# ------------------------------------------------------------ flight scout
def flight_scout(state: dict) -> dict:
    brief = _brief(state)
    provider = get_flight_provider()
    preference = state.get("flight_preference", "recommended")
    options, fallback_note = provider.search(brief, preference)
    pick = pick_flight(options, preference)
    notes = [f"Flights via {provider.name} provider ({len(options)} options)."]
    if fallback_note:
        notes.append(fallback_note)
    return {
        "flights": [f.model_dump(mode="json") for f in options],
        "flight_pick": pick.model_dump(mode="json"),
        "notes": notes,
    }


# ------------------------------------------------------------- hotel scout
def hotel_scout(state: dict) -> dict:
    brief = _brief(state)
    provider = get_hotel_provider()
    preference = state.get("hotel_preference", "recommended")
    options, fallback_note = provider.search(brief, preference)
    pick = pick_hotel(options, brief, preference)
    notes = [f"Hotels via {provider.name} provider ({len(options)} options)."]
    if fallback_note:
        notes.append(fallback_note)
    return {
        "hotels": [h.model_dump(mode="json") for h in options],
        "hotel_pick": pick.model_dump(mode="json"),
        "notes": notes,
    }


# --------------------------------------------------------- itinerary weaver
def _ranked_activities(brief: TripBrief) -> list[Activity]:
    bank = bank_for(brief.destination)
    return sorted(
        bank,
        key=lambda a: (0 if brief.vibe in a.vibes else 1, a.cost),
    )


def itinerary_weaver(state: dict) -> dict:
    brief = _brief(state)
    from ..models import FlightOption

    flight = FlightOption.model_validate(state["flight_pick"])
    arrive_dt = datetime.fromisoformat(flight.arrive)
    depart_day_flight_note = "Departure day — head to the airport in good time."
    trim_paid = bool(state.get("trim_paid", False))
    max_paid_per_day = 1 if trim_paid else 3

    pool = _ranked_activities(brief)
    used: set[str] = set()
    days: list[DayPlan] = []

    reuse_counter = [0]

    def take(slot: str, *, free_only: bool = False) -> Activity | None:
        for act in pool:  # fresh activities first
            if act.name in used or slot not in act.slots:
                continue
            if free_only and act.cost > 0:
                continue
            used.add(act.name)
            return act
        # Pool exhausted (long trips): free activities — walks, beaches,
        # parks — are naturally repeatable, so rotate through them again.
        repeats = [a for a in pool if slot in a.slots and a.cost == 0]
        if repeats:
            act = repeats[reuse_counter[0] % len(repeats)]
            reuse_counter[0] += 1
            return act
        return None

    for i in range(brief.days):
        day_date = brief.start_date + timedelta(days=i)
        is_arrival = i == 0
        is_departure = i == brief.days - 1 and brief.days > 1
        morning = afternoon = evening = None
        paid = 0
        spend = DAILY_FOOD_ALLOWANCE * brief.travelers

        def assign(slot: str, act: Activity | None) -> str | None:
            nonlocal paid, spend
            if act is None:
                return None
            if act.cost > 0:
                paid += 1
                spend += act.cost * brief.travelers
            return act.name

        if is_arrival:
            morning = f"Arrive in {brief.destination} ({flight.airline} {flight.flight_no}), check in and freshen up"
            if arrive_dt.hour >= 18:
                # Late landing: nothing scheduled before arrival, gentle evening.
                evening = assign("evening", take("evening", free_only=True)) or \
                    "Easy dinner near the hotel and an early night"
            elif arrive_dt.hour >= 12:
                afternoon = assign("afternoon", take("afternoon", free_only=True)) or \
                    "Gentle orientation walk around the neighborhood"
                evening = assign("evening", take("evening"))
            else:
                afternoon = assign("afternoon", take("afternoon"))
                evening = assign("evening", take("evening"))
        elif is_departure:
            morning = assign("morning", take("morning", free_only=True)) or \
                "Slow breakfast and souvenir stop"
            afternoon = depart_day_flight_note
        else:
            morning = assign("morning", take("morning"))
            afternoon = assign("afternoon", take("afternoon"))
            if paid > max_paid_per_day:
                evening = assign("evening", take("evening", free_only=True))
            else:
                evening = assign("evening", take("evening"))

        if not any([morning, afternoon, evening]):
            afternoon = f"Free time — wander {brief.destination} at your own pace"

        title_vibes = {
            "foodie": "Eat your way through the city",
            "adventure": "The big adventure day",
            "relax": "Slow down and soak it in",
            "beach": "Sun, sand, repeat",
            "business": "Work hard, wander after",
            "family": "Everyone's favorite day",
            "culture": "Deep-dive day",
        }
        if is_arrival:
            title = f"Touchdown in {brief.destination}"
        elif is_departure:
            title = "One last look, then home"
        else:
            title = title_vibes.get(brief.vibe, "Explore")
        days.append(
            DayPlan(
                date=day_date.isoformat(),
                day_number=i + 1,
                title=title,
                morning=morning,
                afternoon=afternoon,
                evening=evening,
                paid_activities=paid,
                est_spend_usd=round(spend, 2),
            )
        )
    return {"days": [d.model_dump(mode="json") for d in days]}


# ---------------------------------------------------------- budget guardian
def budget_guardian(state: dict) -> dict:
    brief = _brief(state)
    from ..models import FlightOption, HotelOption

    flight = FlightOption.model_validate(state["flight_pick"])
    hotel = HotelOption.model_validate(state["hotel_pick"])
    days = [DayPlan.model_validate(d) for d in state.get("days", [])]

    flights_total = round(flight.price_usd * brief.travelers, 2)
    hotel_total = round(hotel.nightly_usd * brief.nights, 2)
    activities_total = round(sum(d.est_spend_usd for d in days), 2)
    grand = round(flights_total + hotel_total + activities_total, 2)
    revisions = int(state.get("budget_revisions", 0))

    updates: dict = {"swap_pending": False}
    if brief.budget_usd is None:
        status = "no_budget_set"
        notes = ["No budget stated, so no budget enforcement was applied."]
    elif grand <= brief.budget_usd:
        status = "ok"
        notes = [f"Budget check passed: ${grand:,.0f} of ${brief.budget_usd:,.0f}."]
    elif revisions < MAX_BUDGET_REVISIONS:
        # Emit swap instructions and loop back through the scouts + weaver.
        revisions += 1
        if revisions == 1:
            updates["flight_preference"] = "cheapest"
            swap = "cheapest flight"
        else:
            updates["hotel_preference"] = "cheapest"
            updates["trim_paid"] = True
            swap = "cheapest hotel and trimmed paid activities"
        status = "ok"  # provisional; recomputed on the next pass
        notes = [
            f"Budget revision {revisions}: plan was ${grand:,.0f} vs "
            f"${brief.budget_usd:,.0f} budget — swapping to {swap} and re-planning."
        ]
        updates["budget_revisions"] = revisions
        updates["swap_pending"] = True
    else:
        status = "over_budget_flagged"
        notes = [
            f"Budget still exceeded after {MAX_BUDGET_REVISIONS} revisions: "
            f"${grand:,.0f} vs ${brief.budget_usd:,.0f}. Flagged honestly "
            "rather than fudging numbers — consider more days or a higher budget."
        ]

    breakdown = BudgetBreakdown(
        flights_total=flights_total,
        hotel_total=hotel_total,
        activities_total=activities_total,
        grand_total=grand,
        budget_usd=brief.budget_usd,
        status=status,  # type: ignore[arg-type]
        revisions=revisions,
    )
    updates["budget"] = breakdown.model_dump(mode="json")
    updates["notes"] = notes
    updates["budget_status"] = status
    return updates


def route_after_budget(state: dict) -> str:
    """Loop back to the scouts only when the guardian requested swaps."""
    return "revise" if state.get("swap_pending") else "critic"


# -------------------------------------------------------------- plan critic
def plan_critic(state: dict) -> dict:
    brief = _brief(state)
    from ..models import FlightOption

    flight = FlightOption.model_validate(state["flight_pick"])
    arrive_dt = datetime.fromisoformat(flight.arrive)
    days = [DayPlan.model_validate(d) for d in state.get("days", [])]
    issues: list[str] = []

    for day in days:
        filled = sum(1 for s in (day.morning, day.afternoon, day.evening) if s)
        if filled == 0:
            issues.append(f"Day {day.day_number} is empty.")
        if day.paid_activities > 3:
            issues.append(
                f"Day {day.day_number} is overstuffed ({day.paid_activities} paid activities)."
            )
    if days:
        first = days[0]
        if arrive_dt.hour >= 12 and first.morning and "Arrive in" not in first.morning:
            issues.append("Day 1 schedules an activity before the flight lands.")
        if arrive_dt.hour >= 18 and first.afternoon:
            issues.append("Day 1 has an afternoon activity despite a late-evening arrival.")

    revisions = int(state.get("critic_revisions", 0))
    updates: dict = {"critic_issues": issues, "critic_loop": False}
    if issues and revisions < MAX_CRITIC_REVISIONS:
        updates["critic_revisions"] = revisions + 1
        updates["critic_loop"] = True
        updates["trim_paid"] = True  # weaver re-runs in trimmed mode
        updates["notes"] = [f"Plan critic found issues and requested a revision: {'; '.join(issues)}"]
    elif issues:
        updates["notes"] = [f"Plan critic notes (accepted after max revisions): {'; '.join(issues)}"]
    else:
        updates["notes"] = ["Plan critic: no clashes found."]
    return updates


def route_after_critic(state: dict) -> str:
    """Loop back to the weaver only when the critic requested a revision."""
    return "revise" if state.get("critic_loop") else "respond"


# ---------------------------------------------------------------- responder
def responder(state: dict) -> dict:
    brief = _brief(state)
    from ..models import FlightOption, HotelOption

    flights = [FlightOption.model_validate(f) for f in state["flights"]]
    hotels = [HotelOption.model_validate(h) for h in state["hotels"]]
    pick_f = FlightOption.model_validate(state["flight_pick"])
    pick_h = HotelOption.model_validate(state["hotel_pick"])
    plan = TripPlan(
        thread_id=state["thread_id"],
        request=state["request"],
        brief=brief,
        flight_pick=pick_f,
        flight_alternates=[f for f in flights if f.flight_no != pick_f.flight_no],
        hotel_pick=pick_h,
        hotel_alternates=[h for h in hotels if h.name != pick_h.name],
        days=[DayPlan.model_validate(d) for d in state.get("days", [])],
        budget=BudgetBreakdown.model_validate(state["budget"]),
        notes=list(dict.fromkeys(state.get("notes", []))),  # dedupe, keep order
        created_at=datetime.now().isoformat(timespec="seconds"),
    )
    return {"plan": plan.model_dump(mode="json")}
