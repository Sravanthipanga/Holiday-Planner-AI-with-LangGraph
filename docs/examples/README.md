# Example outputs (real runs)

Captured from a live local server (`uvicorn holidayplanner.app:app`) on
2026-11-19 via `POST /api/plan`, simulated providers, no API keys set.
Full JSON: `paris-foodie.json`, `tokyo-family.json`.

## 1. Paris — foodie, on a budget

Request: *“Plan a 5-day foodie trip from Chicago to Paris next month, budget $2,500 for 2 people”*

```
Chicago → Paris | 2026-12-01 to 2026-12-05 | 5 days | 2 traveler(s) | vibe foodie
Flight: Delta DL149 ($428/person) | Hotel: Saint-Germain Harbor Hotel ($142/night)
Total $2,408 vs budget $2,500 — status ok, 2 guardian revision(s)
```

Day 1: Arrive in Paris (Delta DL149), check in and freshen up · Seine river walk and bookstall browsing · Canal Saint-Martin picnic with market finds

Notes from the crew:
- Brief parsed with the rules parser.
- Flights via simulated provider (3 options).
- Hotels via simulated provider (3 options).
- Budget revision 1: plan was $2,608 vs $2,500 budget — swapping to cheapest flight and re-planning.
- Budget revision 2: plan was $2,608 vs $2,500 budget — swapping to cheapest hotel and trimmed paid activities and re-planning.
- Budget check passed: $2,408 of $2,500.
- Plan critic: no clashes found.

## 2. Tokyo — family adventure week

Request: *“Trip to Tokyo in June for 4 people, a week of adventure, around $6,000”*

```
Chicago → Tokyo | 2027-06-01 to 2027-06-07 | 7 days | 4 traveler(s) | vibe adventure
Flight: United UA236 ($619/person) | Hotel: Hotel Ivory Juniper ($103/night)
Total $5,817 vs budget $6,000 — status ok, 0 guardian revision(s)
```

Day 1: Arrive in Tokyo (United UA236), check in and freshen up · None · Shibuya crossing and Harajuku backstreets

Notes from the crew:
- Brief parsed with the rules parser.
- Flights via simulated provider (3 options).
- Hotels via simulated provider (3 options).
- Budget check passed: $5,817 of $6,000.
- Plan critic: no clashes found.
