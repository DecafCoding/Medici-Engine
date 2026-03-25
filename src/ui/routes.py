"""
UI routes for the Medici Engine.

Provides HTML endpoints for batch configuration, batch progress
monitoring, and concept review. Uses Jinja2 templates with HTMX
for interactive updates without a frontend build toolchain.
This module belongs to the API layer.
"""

import logging
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.batch.models import BatchRequest
from src.batch.runner import BatchRunner
from src.db.queries import (
    BatchCreate,
    create_batch,
    get_batch_by_id,
    get_concept_by_id,
    get_concepts_with_scores,
    get_pairing_performance,
    get_run_by_id,
    get_score_by_concept_id,
    get_shared_object_performance,
    update_concept_status,
)
from src.domains.registry import get_active_domain, get_all_domains
from src.personas.library import get_all_personas, get_all_shared_objects

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ui", tags=["ui"])

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@router.get("/batch")
async def batch_setup(request: Request):
    """Render the batch setup form with persona and shared object options."""
    personas = get_all_personas()
    shared_objects = get_all_shared_objects()
    return templates.TemplateResponse(
        "batch.html",
        {
            "request": request,
            "personas": personas,
            "shared_objects": shared_objects,
        },
    )


@router.post("/batch")
async def launch_batch(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Handle batch setup form submission and launch the batch.

    Parses form data, creates a batch record, and launches the
    BatchRunner as a background task. Returns the batch status
    fragment for HTMX to display progress.
    """
    form = await request.form()
    db = request.app.state.db

    # Parse form values (strings from HTML form)
    num_conversations = int(form.get("num_conversations", "1"))
    turns_per_agent = int(form.get("turns_per_agent", "5"))

    # Parse persona selections (empty string = random)
    persona_a = str(form.get("persona_a", ""))
    persona_b = str(form.get("persona_b", ""))

    persona_pairs: list[tuple[str, str]] | None = None
    if persona_a and persona_b:
        persona_pairs = [(persona_a, persona_b)]

    # Parse shared object selection (empty string = random)
    shared_object_str = str(form.get("shared_object", ""))
    shared_object_indices: list[int] | None = None
    if shared_object_str:
        shared_object_indices = [int(shared_object_str)]

    # Create batch record
    batch = await create_batch(db, BatchCreate(total_runs=num_conversations))

    # Build request and launch background task
    batch_request = BatchRequest(
        persona_pairs=persona_pairs,
        shared_object_indices=shared_object_indices,
        num_conversations=num_conversations,
        turns_per_agent=turns_per_agent,
    )

    runner = BatchRunner(db)
    background_tasks.add_task(runner.run_batch, batch_request, batch.id)

    logger.info(
        "Batch launched",
        extra={
            "batch_id": str(batch.id),
            "num_conversations": num_conversations,
        },
    )

    return templates.TemplateResponse(
        "fragments/batch_status.html",
        {"request": request, "batch": batch},
    )


@router.get("/batch/{batch_id}/status")
async def batch_status(request: Request, batch_id: UUID):
    """Return the batch progress fragment for HTMX polling."""
    db = request.app.state.db
    batch = await get_batch_by_id(db, batch_id)
    return templates.TemplateResponse(
        "fragments/batch_status.html",
        {"request": request, "batch": batch},
    )


# ── Review Endpoints ─────────────────────────────────


@router.get("/review")
async def review_list(
    request: Request,
    status: str | None = None,
    sort: str = "date_desc",
    limit: int = 50,
):
    """Render the concept review list with filter and sort controls."""
    db = request.app.state.db
    concepts = await get_concepts_with_scores(
        db, status=status, sort_by=sort, limit=limit
    )
    domain = get_active_domain()
    return templates.TemplateResponse(
        "review.html",
        {
            "request": request,
            "concepts": concepts,
            "current_status": status,
            "current_sort": sort,
            "domain": domain,
        },
    )


@router.get("/review/rows")
async def review_rows(
    request: Request,
    status: str | None = None,
    sort: str = "date_desc",
    limit: int = 50,
):
    """Return the concept table body fragment for HTMX swap."""
    db = request.app.state.db
    concepts = await get_concepts_with_scores(
        db, status=status, sort_by=sort, limit=limit
    )
    return templates.TemplateResponse(
        "fragments/concept_rows.html",
        {"request": request, "concepts": concepts},
    )


@router.get("/review/{concept_id}")
async def review_detail(request: Request, concept_id: UUID):
    """Render the concept detail page with scores and run info."""
    db = request.app.state.db

    concept = await get_concept_by_id(db, concept_id)
    if concept is None:
        return HTMLResponse("Concept not found", status_code=404)

    score = await get_score_by_concept_id(db, concept_id)
    run = await get_run_by_id(db, concept.run_id)
    domain = get_active_domain()

    return templates.TemplateResponse(
        "detail.html",
        {
            "request": request,
            "concept": concept,
            "score": score,
            "run": run,
            "domain": domain,
        },
    )


@router.get("/review/{concept_id}/transcript")
async def review_transcript(request: Request, concept_id: UUID):
    """Return the transcript fragment for lazy loading via HTMX."""
    db = request.app.state.db

    concept = await get_concept_by_id(db, concept_id)
    if concept is None:
        return HTMLResponse("Concept not found", status_code=404)

    run = await get_run_by_id(db, concept.run_id)
    transcript = run.transcript if run else None

    return templates.TemplateResponse(
        "fragments/transcript.html",
        {"request": request, "transcript": transcript, "run": run},
    )


@router.patch("/review/{concept_id}/status")
async def review_toggle_status(request: Request, concept_id: UUID):
    """Toggle a concept's review status and return the updated badge."""
    db = request.app.state.db
    form = await request.form()
    status = str(form.get("status", "pending"))

    updated = await update_concept_status(db, concept_id, status)
    return templates.TemplateResponse(
        "fragments/concept_status.html",
        {"request": request, "concept": updated},
    )


# ── Insights Endpoints ──────────────────────────────


@router.get("/insights")
async def insights_page(request: Request, domain: str | None = None):
    """Render the insights page with pairing and shared object performance."""
    db = request.app.state.db
    domains = get_all_domains()
    pairings = await get_pairing_performance(db, domain=domain)
    shared_objects = await get_shared_object_performance(db, domain=domain)
    return templates.TemplateResponse(
        "insights.html",
        {
            "request": request,
            "pairings": pairings,
            "shared_objects": shared_objects,
            "current_domain": domain,
            "domains": domains,
        },
    )


@router.get("/insights/pairings")
async def insights_pairing_rows(request: Request, domain: str | None = None):
    """Return the pairing performance table body fragment for HTMX swap."""
    db = request.app.state.db
    pairings = await get_pairing_performance(db, domain=domain)
    return templates.TemplateResponse(
        "fragments/pairing_rows.html",
        {"request": request, "pairings": pairings},
    )


@router.get("/insights/shared-objects")
async def insights_shared_object_rows(request: Request, domain: str | None = None):
    """Return the shared object performance table body fragment for HTMX swap."""
    db = request.app.state.db
    shared_objects = await get_shared_object_performance(db, domain=domain)
    return templates.TemplateResponse(
        "fragments/shared_object_rows.html",
        {"request": request, "shared_objects": shared_objects},
    )
