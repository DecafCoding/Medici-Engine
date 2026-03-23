"""
API routes for the Medici Engine.

Provides REST endpoints for managing conversation runs, viewing
extracted concepts, and reviewing results. This module belongs
to the API layer.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Request

from src.db import queries

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["runs"])


# ── Run Endpoints ────────────────────────────────────


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


@router.get("/runs/{run_id}/concept")
async def get_run_concept(request: Request, run_id: UUID) -> queries.Concept | None:
    """Fetch the concept extracted from a specific run."""
    db = request.app.state.db
    return await queries.get_concept_by_run_id(db, run_id)


# ── Concept Endpoints ────────────────────────────────


@router.get("/concepts")
async def list_concepts(
    request: Request,
    status: str | None = None,
    limit: int = 20,
) -> list[queries.Concept]:
    """List concepts, optionally filtered by review status."""
    db = request.app.state.db
    return await queries.get_concepts(db, status=status, limit=limit)


@router.get("/concepts/{concept_id}")
async def get_concept(request: Request, concept_id: UUID) -> queries.Concept | None:
    """Fetch a single concept by ID."""
    db = request.app.state.db
    return await queries.get_concept_by_id(db, concept_id)


@router.get("/concepts/{concept_id}/scores")
async def get_concept_scores(
    request: Request, concept_id: UUID
) -> queries.Score | None:
    """Fetch the scores for a specific concept."""
    db = request.app.state.db
    return await queries.get_score_by_concept_id(db, concept_id)


# ── Score Endpoints ─────────────────────────────────


@router.get("/scores")
async def list_scores(
    request: Request,
    limit: int = 20,
) -> list[queries.Score]:
    """List recent scores across all concepts."""
    db = request.app.state.db
    return await queries.get_scores(db, limit=limit)
