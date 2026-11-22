"""FastAPI application entry point for NiveshSetu.

Run locally on Windows PowerShell:
    uvicorn app.main:app --reload
Then open interactive API docs at:
    http://localhost:8000/docs
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.ai import router as ai_router
from app.routes.core import router as core_router

app = FastAPI(
    title="NiveshSetu API",
    description=(
        "21-Day Investor Resilience Simulator backend — deterministic market simulation, "
        "9-habit behavioural scoring, and 3-layer guardrailed Sarvam AI coaching."
    ),
    version="1.0.0",
)

# Support local React dev server plus comma-separated production origins (e.g. Vercel URL)
default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]
extra_origins = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=default_origins + extra_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(core_router)
app.include_router(ai_router)
