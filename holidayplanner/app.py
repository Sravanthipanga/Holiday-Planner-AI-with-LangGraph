"""Holiday Planner AI with LangGraph — FastAPI app: web UI (Jinja2) + JSON API.

Run:  uvicorn holidayplanner.app:app --reload
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .graph import run_plan
from .store import get_store

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Holiday Planner AI with LangGraph", version="0.1.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

SAMPLE_REQUESTS = [
    "Plan a 5-day foodie trip from Chicago to Paris next month, budget $2,500 for 2 people",
    "A relaxing beach long weekend in Bali under $2,000, just me",
    "Family of 4 adventure week in Tokyo in June, around $6,000",
    "Romantic culture trip to Rome for our honeymoon, 6 days, under $3,000",
    "Business trip to New York from June 3 to June 7",
]


class PlanRequest(BaseModel):
    request: str
    thread_id: Optional[str] = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "index.html", {"samples": SAMPLE_REQUESTS}
    )


@app.post("/plan", response_class=HTMLResponse)
def plan_page(request: Request, trip_request: str = Form(...)) -> HTMLResponse:
    plan = run_plan(trip_request)
    return templates.TemplateResponse(request, "plan.html", {"plan": plan})


@app.post("/api/plan")
def plan_api(payload: PlanRequest) -> JSONResponse:
    plan = run_plan(payload.request, payload.thread_id)
    return JSONResponse(plan)


@app.get("/api/trips/{thread_id}")
def get_trip(thread_id: str) -> JSONResponse:
    plan = get_store().get(thread_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="trip not found")
    return JSONResponse(plan)
