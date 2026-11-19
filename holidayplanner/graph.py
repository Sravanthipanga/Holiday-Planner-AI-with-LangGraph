"""LangGraph workflow assembly for HolidayPlanner.

    brief_agent -> flight_scout -> hotel_scout -> itinerary_weaver
        -> budget_guardian --(swap requested)--> back to flight_scout
        -> plan_critic --(issues, revisions left)--> back to itinerary_weaver
        -> responder

The graph is compiled with an in-memory checkpointer keyed by thread_id.
Durable plan persistence lives in holidayplanner.store (SQLite by default,
PostgreSQL when DATABASE_URL is set).
"""

from __future__ import annotations

import operator
import uuid
from typing import Annotated, Optional, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from .agents import nodes
from .store import get_store


class TripState(TypedDict, total=False):
    request: str
    thread_id: str
    brief: dict
    flights: list
    flight_pick: dict
    hotels: list
    hotel_pick: dict
    days: list
    budget: dict
    budget_status: str
    budget_revisions: int
    critic_revisions: int
    critic_issues: list
    flight_preference: str
    hotel_preference: str
    trim_paid: bool
    swap_pending: bool
    critic_loop: bool
    notes: Annotated[list, operator.add]
    plan: dict


def build_graph():
    g = StateGraph(TripState)
    g.add_node("brief_agent", nodes.brief_agent)
    g.add_node("flight_scout", nodes.flight_scout)
    g.add_node("hotel_scout", nodes.hotel_scout)
    g.add_node("itinerary_weaver", nodes.itinerary_weaver)
    g.add_node("budget_guardian", nodes.budget_guardian)
    g.add_node("plan_critic", nodes.plan_critic)
    g.add_node("responder", nodes.responder)

    g.add_edge(START, "brief_agent")
    g.add_edge("brief_agent", "flight_scout")
    g.add_edge("flight_scout", "hotel_scout")
    g.add_edge("hotel_scout", "itinerary_weaver")
    g.add_edge("itinerary_weaver", "budget_guardian")
    g.add_conditional_edges(
        "budget_guardian",
        nodes.route_after_budget,
        {"revise": "flight_scout", "critic": "plan_critic"},
    )
    g.add_conditional_edges(
        "plan_critic",
        nodes.route_after_critic,
        {"revise": "itinerary_weaver", "respond": "responder"},
    )
    g.add_edge("responder", END)
    return g.compile(checkpointer=MemorySaver())


_GRAPH = None


def get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH


def run_plan(request: str, thread_id: Optional[str] = None) -> dict:
    """Run the full workflow for one request and persist the result."""
    thread_id = thread_id or uuid.uuid4().hex[:16]
    graph = get_graph()
    result = graph.invoke(
        {"request": request, "thread_id": thread_id},
        config={"configurable": {"thread_id": thread_id}},
    )
    plan = result["plan"]
    get_store().save(thread_id, request, plan)
    return plan
