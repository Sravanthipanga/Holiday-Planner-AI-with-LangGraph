"""Pytest bootstrap: deterministic environment for the whole suite.

Forces the simulated providers (no live API keys), a throwaway SQLite
store, and makes the project package importable from the repo root.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))

os.environ["HOLIDAYPLANNER_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
for var in ("GROQ_API_KEY", "TAVILY_API_KEY", "AVIATIONSTACK_API_KEY", "DATABASE_URL"):
    os.environ.pop(var, None)
