#!/usr/bin/env python
"""Golden-trip evaluation for Holiday Planner AI with LangGraph.

Runs 10 canned requests through the full LangGraph workflow and checks
(a) the parsed brief against expected fields and (b) plan invariants:
day count matches the brief, no activity is scheduled before the flight
lands on day 1, no day is empty, no day is overstuffed, and the budget
math is honest (status 'ok' implies total <= budget; 'over_budget_flagged'
implies total > budget).

Usage:  .venv/bin/python evals/run_eval.py
Exits 0 when all cases pass, 1 otherwise.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.pop("GROQ_API_KEY", None)  # evals must be deterministic

from holidayplanner.graph import run_plan  # noqa: E402


def check_case(idx: int, case: dict) -> list[str]:
    failures: list[str] = []
    plan = run_plan(case["request"], thread_id=f"eval-{idx}")
    brief, expect = plan["brief"], case["expect"]

    for field in ("destination_iata", "origin_iata", "days", "travelers", "budget_usd", "vibe"):
        if field in expect and brief.get(field) != expect[field]:
            failures.append(f"brief.{field}: expected {expect[field]!r}, got {brief.get(field)!r}")
    if "start_month" in expect:
        month = int(brief["start_date"][5:7])
        if month != expect["start_month"]:
            failures.append(f"brief.start month: expected {expect['start_month']}, got {month}")

    days = plan["days"]
    if len(days) != brief["days"]:
        failures.append(f"day count {len(days)} != brief days {brief['days']}")

    arrive = datetime.fromisoformat(plan["flight_pick"]["arrive"])
    for day in days:
        filled = [s for s in (day["morning"], day["afternoon"], day["evening"]) if s]
        if not filled:
            failures.append(f"day {day['day_number']} is empty")
        if day["paid_activities"] > 3:
            failures.append(f"day {day['day_number']} overstuffed ({day['paid_activities']} paid)")
    if days:
        first = days[0]
        if first["morning"] and not first["morning"].startswith("Arrive in"):
            failures.append("day 1 morning is not the arrival slot")
        if arrive.hour >= 18 and first["afternoon"]:
            failures.append("day 1 has an afternoon activity despite a late arrival")

    budget = plan["budget"]
    if budget["budget_usd"] is not None:
        if budget["status"] == "ok" and budget["grand_total"] > budget["budget_usd"]:
            failures.append("status ok but grand_total exceeds budget")
        if budget["status"] == "over_budget_flagged" and budget["grand_total"] <= budget["budget_usd"]:
            failures.append("flagged over budget but grand_total is within budget")
    return failures


def main() -> int:
    cases = json.loads((Path(__file__).parent / "golden_trips.json").read_text())
    passed = 0
    for i, case in enumerate(cases, start=1):
        failures = check_case(i, case)
        if failures:
            print(f"FAIL [{i}] {case['request']}")
            for f in failures:
                print(f"       - {f}")
        else:
            passed += 1
            print(f"PASS [{i}] {case['request']}")
    print(f"\nEval summary: {passed}/{len(cases)} golden trips passed")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
