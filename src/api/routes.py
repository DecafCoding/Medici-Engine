"""
API routes for the Medici Engine.

Provides REST endpoints for managing conversation runs and
reviewing results. This module belongs to the API layer.
Full implementation comes in Feature 5 — Feature 1 provides
a minimal set of endpoints for run management.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Request

from src.db import queries

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["runs"])


@router.get("/runs")
async def list_runs(
    request: Request,
    status: str | None = None,
    limit: int = 20,
) -> list[queries.Run]:
    """List conversation runs, optionally filtered by status."""
    db = request.app.state.db
    return await queries.get_runs(db, status=status, limit=limit)


@router.get("/runs/{run_id}")
async def get_run(request: Request, run_id: UUID) -> queries.Run | None:
    """Fetch a single conversation run by ID."""
    db = request.app.state.db
    return await queries.get_run_by_id(db, run_id)
