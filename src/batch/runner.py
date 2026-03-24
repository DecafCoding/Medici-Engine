"""
Batch runner for the Medici Engine.

Executes multiple conversation runs as a batch, coordinating the full
pipeline: persona selection -> conversation -> synthesis -> scoring.
Tracks progress in the batches table and handles individual conversation
failures without aborting the batch. This module belongs to the API layer
and orchestrates across Engine, Synthesis, and Scoring layers.
"""

import logging
from uuid import UUID

import aiosqlite

from src.batch.models import BatchRequest
from src.config import settings
from src.db.queries import (
    ConceptCreate,
    RunCreate,
    ScoreCreate,
    complete_batch,
    complete_run,
    create_concept,
    create_run,
    create_score,
    fail_run,
    get_recent_pairings,
    increment_batch_completed,
    increment_batch_failed,
    record_pairing,
)
from src.domains.models import DomainConfig
from src.domains.registry import get_active_domain
from src.engine.conversation import ConversationRunner
from src.engine.models import ConversationConfig, ConversationRequest
from src.personas.library import (
    get_all_shared_objects,
    get_persona_by_name,
    get_persona_pair,
    get_random_shared_object,
)
from src.scoring.scorer import Scorer, ScoringError
from src.synthesis.synthesizer import SynthesisError, Synthesizer

logger = logging.getLogger(__name__)


class BatchError(Exception):
    """Raised when batch orchestration fails."""


class BatchRunner:
    """Executes a batch of conversation runs through the full pipeline.

    For each conversation in the batch: selects personas and a shared
    object, runs the conversation via vLLM, synthesizes a concept via
    the OpenAI API, and scores it. Individual conversation failures are
    logged and tracked but do not abort the batch.
    """

    def __init__(self, db: aiosqlite.Connection) -> None:
        """Initialize the batch runner with a database connection."""
        self._db = db

    async def run_batch(self, request: BatchRequest, batch_id: UUID) -> None:
        """Execute a batch of conversations through the full pipeline.

        Loops through the requested number of conversations, handling
        failures per-conversation so the batch continues even if
        individual runs fail.

        Args:
            request: Batch configuration specifying personas, shared
                objects, conversation count, and turn settings.
            batch_id: ID of the batch record to track progress against.
        """
        logger.info(
            "Starting batch",
            extra={
                "batch_id": str(batch_id),
                "num_conversations": request.num_conversations,
            },
        )

        domain = get_active_domain()
        all_shared_objects = get_all_shared_objects()

        for i in range(request.num_conversations):
            run_id: UUID | None = None
            try:
                # 1. Select persona pair
                persona_a, persona_b = await self._select_personas(request, i)

                # 2. Select shared object
                if request.shared_object_indices is not None:
                    idx = request.shared_object_indices[
                        i % len(request.shared_object_indices)
                    ]
                    if idx < 0 or idx >= len(all_shared_objects):
                        raise BatchError(f"Shared object index out of range: {idx}")
                    shared_object = all_shared_objects[idx]
                else:
                    shared_object = get_random_shared_object()

                # 3. Create run record
                run_record = await create_run(
                    self._db,
                    RunCreate(
                        persona_a_name=persona_a.name,
                        persona_b_name=persona_b.name,
                        shared_object_text=shared_object.text,
                        shared_object_type=shared_object.object_type,
                        turns_per_agent=request.turns_per_agent,
                        batch_id=batch_id,
                    ),
                )
                run_id = run_record.id

                # 4. Run conversation
                config = ConversationConfig(
                    turns_per_agent=request.turns_per_agent,
                    temperature=settings.conversation_temperature,
                    repetition_penalty=settings.conversation_repetition_penalty,
                    max_tokens=settings.conversation_max_tokens,
                )
                conv_request = ConversationRequest(
                    persona_a=persona_a,
                    persona_b=persona_b,
                    shared_object=shared_object,
                    config=config,
                )

                runner = ConversationRunner()
                turns = await runner.run(conv_request)

                # 5. Save transcript and pairing
                await complete_run(self._db, run_id, turns)
                await record_pairing(self._db, persona_a.name, persona_b.name, run_id)

                # 6. Synthesize (if API key available)
                concept = None
                if settings.openai_api_key:
                    concept = await self._run_synthesis(
                        domain=domain,
                        run_id=run_id,
                        turns=turns,
                        persona_a_name=persona_a.name,
                        persona_b_name=persona_b.name,
                        shared_object_text=shared_object.text,
                    )

                # 7. Score (if synthesis succeeded and API key available)
                if concept is not None and settings.openai_api_key:
                    await self._run_scoring(
                        domain=domain,
                        concept_id=concept.id,
                        fields=concept.fields,
                    )

                await increment_batch_completed(self._db, batch_id)

                logger.info(
                    "Conversation %d/%d completed",
                    i + 1,
                    request.num_conversations,
                    extra={"batch_id": str(batch_id), "run_id": str(run_id)},
                )

            except Exception as e:
                logger.error(
                    "Conversation %d/%d failed: %s",
                    i + 1,
                    request.num_conversations,
                    e,
                    extra={"batch_id": str(batch_id)},
                )
                if run_id is not None:
                    await fail_run(self._db, run_id, str(e))
                await increment_batch_failed(self._db, batch_id)

        await complete_batch(self._db, batch_id)

        logger.info(
            "Batch completed",
            extra={"batch_id": str(batch_id)},
        )

    async def _select_personas(self, request: BatchRequest, index: int) -> tuple:
        """Select a persona pair for a given conversation index.

        Args:
            request: Batch configuration with optional persona pairs.
            index: Current conversation index in the batch.

        Returns:
            Tuple of two Persona objects.

        Raises:
            BatchError: If a specified persona name is not found.
        """
        if request.persona_pairs is not None:
            pair = request.persona_pairs[index % len(request.persona_pairs)]
            persona_a = get_persona_by_name(pair[0])
            persona_b = get_persona_by_name(pair[1])
            if persona_a is None:
                raise BatchError(f"Persona not found: {pair[0]}")
            if persona_b is None:
                raise BatchError(f"Persona not found: {pair[1]}")
            return persona_a, persona_b

        recent = await get_recent_pairings(self._db)
        return get_persona_pair(recent)

    async def _run_synthesis(
        self,
        domain: DomainConfig,
        run_id: UUID,
        turns: list,
        persona_a_name: str,
        persona_b_name: str,
        shared_object_text: str,
    ):
        """Run synthesis on a transcript and persist the concept.

        Args:
            domain: Active domain configuration.
            run_id: ID of the run to attach the concept to.
            turns: Ordered list of conversation turns.
            persona_a_name: Name of the first persona.
            persona_b_name: Name of the second persona.
            shared_object_text: The shared object text.

        Returns:
            The created Concept if synthesis succeeds, None otherwise.
        """
        try:
            synthesizer = Synthesizer(domain)
            extraction = await synthesizer.synthesize(
                transcript=turns,
                persona_a_name=persona_a_name,
                persona_b_name=persona_b_name,
                shared_object_text=shared_object_text,
            )
            return await create_concept(
                self._db,
                ConceptCreate(
                    run_id=run_id,
                    domain=domain.name,
                    title=extraction[domain.primary_field],
                    fields=extraction,
                ),
            )
        except SynthesisError as e:
            logger.warning("Synthesis failed for run %s: %s", run_id, e)
            return None

    async def _run_scoring(
        self,
        domain: DomainConfig,
        concept_id: UUID,
        fields: dict[str, str],
    ) -> None:
        """Score a concept and persist the evaluation.

        Args:
            domain: Active domain configuration.
            concept_id: ID of the concept to score.
            fields: The concept's extracted fields.
        """
        try:
            scorer = Scorer(domain)
            result = await scorer.score(fields=fields)
            await create_score(
                self._db,
                ScoreCreate(
                    concept_id=concept_id,
                    axes=result,
                ),
            )
        except ScoringError as e:
            logger.warning("Scoring failed for concept %s: %s", concept_id, e)
