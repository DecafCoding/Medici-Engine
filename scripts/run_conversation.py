"""
CLI runner for the Medici Engine.

Runs a single conversation between two persona agents with a dynamically
generated situation, stores the transcript in the database, synthesizes
a concept from the transcript, scores it across evaluation axes, and
prints results. This is the primary interface for Features 1-4.

Usage:
    uv run python scripts/run_conversation.py
    uv run python scripts/run_conversation.py --turns 3
    uv run python scripts/run_conversation.py --domain product-design
    uv run python scripts/run_conversation.py --list-domains
    uv run python scripts/run_conversation.py --no-synthesis
    uv run python scripts/run_conversation.py --no-scoring
    uv run python scripts/run_conversation.py --synthesis-only <run-id>
    uv run python scripts/run_conversation.py --score-only <concept-id>
    uv run python scripts/run_conversation.py \\
        --persona-a quantum_information_theorist \\
        --persona-b medieval_master_builder
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from uuid import UUID

import aiosqlite

from src.config import settings
from src.db.queries import (
    Concept,
    ConceptCreate,
    RunCreate,
    ScoreCreate,
    complete_run,
    create_concept,
    create_run,
    create_score,
    fail_run,
    get_concept_by_id,
    get_run_by_id,
    record_pairing,
)
from src.db.schema import init_schema
from src.domains.models import DomainConfig
from src.domains.registry import get_active_domain, get_all_domains, get_domain
from src.engine.conversation import ConversationError, ConversationRunner
from src.engine.models import ConversationConfig, ConversationRequest
from src.engine.situation import SituationGenerator
from src.personas.library import (
    get_all_personas,
    get_persona_by_name,
    get_persona_pair,
)
from src.scoring.scorer import Scorer, ScoringError
from src.synthesis.synthesizer import SynthesisError, Synthesizer

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the conversation runner."""
    parser = argparse.ArgumentParser(
        description="Run a Medici Engine conversation between two persona agents.",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=settings.default_turns,
        help=f"Number of turns per agent (default: {settings.default_turns})",
    )
    parser.add_argument(
        "--persona-a",
        type=str,
        default=None,
        help="Name of the first persona (default: random selection)",
    )
    parser.add_argument(
        "--persona-b",
        type=str,
        default=None,
        help="Name of the second persona (default: random selection)",
    )
    parser.add_argument(
        "--domain",
        type=str,
        default=None,
        help="Domain name to use (overrides ACTIVE_DOMAIN env var)",
    )
    parser.add_argument(
        "--list-domains",
        action="store_true",
        help="List all available domains and exit",
    )
    parser.add_argument(
        "--list-personas",
        action="store_true",
        help="List all available personas and exit",
    )
    parser.add_argument(
        "--no-synthesis",
        action="store_true",
        help="Skip synthesis after conversation (default: synthesis runs)",
    )
    parser.add_argument(
        "--synthesis-only",
        type=str,
        default=None,
        metavar="RUN_ID",
        help="Run synthesis on an existing completed run (skip conversation)",
    )
    parser.add_argument(
        "--no-scoring",
        action="store_true",
        help="Skip scoring after synthesis (default: scoring runs)",
    )
    parser.add_argument(
        "--score-only",
        type=str,
        default=None,
        metavar="CONCEPT_ID",
        help="Score an existing concept (skip conversation and synthesis)",
    )
    return parser.parse_args()


def _resolve_domain(args: argparse.Namespace) -> DomainConfig:
    """Resolve the domain config from CLI args or environment.

    Args:
        args: Parsed command-line arguments.

    Returns:
        The resolved DomainConfig.
    """
    if args.domain:
        return get_domain(args.domain)
    return get_active_domain()


async def _run_synthesis(
    db: aiosqlite.Connection,
    domain: DomainConfig,
    run_record_id: UUID,
    transcript: list,
    persona_a_name: str,
    persona_b_name: str,
    situation_text: str,
) -> Concept | None:
    """Run synthesis on a transcript and persist the extracted concept.

    Synthesis failure is logged but does not raise — the conversation
    transcript is already saved and synthesis can be retried later.

    Args:
        db: Database connection.
        domain: Active domain configuration.
        run_record_id: ID of the run to attach the concept to.
        transcript: Ordered list of conversation turns.
        persona_a_name: Name of the first persona.
        persona_b_name: Name of the second persona.
        situation_text: The situation that seeded the conversation.

    Returns:
        The created Concept if synthesis succeeds, None otherwise.
    """
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not set — skipping synthesis")
        print("\n⚠ Synthesis skipped: OPENAI_API_KEY not configured")
        return None

    print(f"\n{'─' * 60}")
    print("SYNTHESIS")
    print(f"{'─' * 60}\n")

    try:
        synthesizer = Synthesizer(domain)
        extraction = await synthesizer.synthesize(
            transcript=transcript,
            persona_a_name=persona_a_name,
            persona_b_name=persona_b_name,
            situation_text=situation_text,
        )

        concept = await create_concept(
            db,
            ConceptCreate(
                run_id=run_record_id,
                domain=domain.name,
                title=extraction[domain.primary_field],
                fields=extraction,
            ),
        )

        # Display each extraction field with its label
        for ef in domain.extraction_fields:
            value = extraction.get(ef.name, "")
            print(f"{ef.label + ':':<16} {value}")
        print(f"{'Concept ID:':<16} {concept.id}")

        return concept

    except SynthesisError as e:
        logger.error("Synthesis failed: %s", e)
        print(f"\n⚠ Synthesis failed: {e}")
        print("The conversation transcript has been saved. You can retry with:")
        print(
            f"  uv run python scripts/run_conversation.py"
            f" --synthesis-only {run_record_id}"
        )
        return None


async def _synthesis_only(
    db: aiosqlite.Connection,
    run_id_str: str,
    domain: DomainConfig,
) -> None:
    """Run synthesis on an existing completed run.

    Args:
        db: Database connection.
        run_id_str: String UUID of the run to synthesize.
        domain: Active domain configuration.
    """
    try:
        run_id = UUID(run_id_str)
    except ValueError:
        logger.error("Invalid run ID: %s", run_id_str)
        sys.exit(1)

    run_record = await get_run_by_id(db, run_id)
    if run_record is None:
        logger.error("Run not found: %s", run_id_str)
        sys.exit(1)

    if run_record.status != "completed":
        logger.error("Run is not completed (status: %s)", run_record.status)
        sys.exit(1)

    if run_record.transcript is None:
        logger.error("Run has no transcript")
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print("MEDICI ENGINE — Synthesis Only")
    print(f"{'=' * 60}")
    print(f"Run ID:     {run_record.id}")
    print(f"Persona A:  {run_record.persona_a_name}")
    print(f"Persona B:  {run_record.persona_b_name}")
    print(f"Domain:     {domain.label}")
    print(f"{'=' * 60}")

    concept = await _run_synthesis(
        db=db,
        domain=domain,
        run_record_id=run_record.id,
        transcript=run_record.transcript,
        persona_a_name=run_record.persona_a_name,
        persona_b_name=run_record.persona_b_name,
        situation_text=run_record.situation_text,
    )

    if concept is not None:
        await _run_scoring(db=db, domain=domain, concept=concept)


async def _run_scoring(
    db: aiosqlite.Connection,
    domain: DomainConfig,
    concept: Concept,
) -> None:
    """Score a concept and persist the evaluation.

    Scoring failure is logged but does not raise — the concept is
    already saved and scoring can be retried later.

    Args:
        db: Database connection.
        domain: Active domain configuration.
        concept: The concept to score.
    """
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not set — skipping scoring")
        print("\n⚠ Scoring skipped: OPENAI_API_KEY not configured")
        return

    print(f"\n{'─' * 60}")
    print("SCORING")
    print(f"{'─' * 60}\n")

    try:
        scorer = Scorer(domain)
        result = await scorer.score(fields=concept.fields)

        await create_score(
            db,
            ScoreCreate(
                concept_id=concept.id,
                axes=result,
            ),
        )

        for axis_score in result:
            print(f"{axis_score.label}:  {axis_score.score}/10")
            print(f"  → {axis_score.reasoning}\n")

    except ScoringError as e:
        logger.error("Scoring failed: %s", e)
        print(f"\n⚠ Scoring failed: {e}")
        print("The concept has been saved. You can retry with:")
        print(f"  uv run python scripts/run_conversation.py --score-only {concept.id}")


async def _score_only(
    db: aiosqlite.Connection,
    concept_id_str: str,
    domain: DomainConfig,
) -> None:
    """Score an existing concept.

    Args:
        db: Database connection.
        concept_id_str: String UUID of the concept to score.
        domain: Active domain configuration.
    """
    try:
        concept_id = UUID(concept_id_str)
    except ValueError:
        logger.error("Invalid concept ID: %s", concept_id_str)
        sys.exit(1)

    concept = await get_concept_by_id(db, concept_id)
    if concept is None:
        logger.error("Concept not found: %s", concept_id_str)
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print("MEDICI ENGINE — Score Only")
    print(f"{'=' * 60}")
    print(f"Concept ID: {concept.id}")
    print(f"Title:      {concept.title}")
    print(f"Domain:     {domain.label}")
    print(f"{'=' * 60}")

    await _run_scoring(db=db, domain=domain, concept=concept)


async def run(args: argparse.Namespace) -> None:
    """Execute a conversation run with the given arguments."""
    # Handle list commands
    if args.list_domains:
        for d in get_all_domains():
            print(f"  {d.name}: {d.label} — {d.description}")
        return

    if args.list_personas:
        for persona in get_all_personas():
            print(f"  {persona.name}: {persona.title}")
        return

    # Resolve domain
    domain = _resolve_domain(args)

    # Connect to database
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(settings.database_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    await init_schema(db)

    try:
        # Handle score-only mode
        if args.score_only:
            await _score_only(db, args.score_only, domain)
            return

        # Handle synthesis-only mode
        if args.synthesis_only:
            await _synthesis_only(db, args.synthesis_only, domain)
            return

        # Select personas
        if args.persona_a and args.persona_b:
            persona_a = get_persona_by_name(args.persona_a)
            persona_b = get_persona_by_name(args.persona_b)
            if not persona_a:
                logger.error("Persona not found: %s", args.persona_a)
                sys.exit(1)
            if not persona_b:
                logger.error("Persona not found: %s", args.persona_b)
                sys.exit(1)
        else:
            persona_a, persona_b = get_persona_pair()

        # Generate situation from Persona A's perspective
        print(f"\n{'─' * 60}")
        print("GENERATING SITUATION")
        print(f"{'─' * 60}")
        print(f"Persona A:  {persona_a.title}")
        print("Generating situation from their perspective...\n")

        situation_gen = SituationGenerator()
        situation = await situation_gen.generate(persona_a)

        print(f"Situation generated ({len(situation.text)} chars):")
        print(f"---\n{situation.text}\n---")

        # Create run record
        run_record = await create_run(
            db,
            RunCreate(
                persona_a_name=persona_a.name,
                persona_b_name=persona_b.name,
                situation_text=situation.text,
                situation_type=situation.situation_type,
                turns_per_agent=args.turns,
            ),
        )

        print(f"\n{'=' * 60}")
        print("MEDICI ENGINE — Conversation Run")
        print(f"{'=' * 60}")
        print(f"Run ID:         {run_record.id}")
        print(f"Domain:         {domain.label}")
        print(f"Persona A:      {persona_a.title}")
        print(f"Persona B:      {persona_b.title}")
        print(f"Situation:      {situation.text[:80]}...")
        print(f"Turns/Agent:    {args.turns}")
        print(f"{'=' * 60}\n")

        # Run conversation
        config = ConversationConfig(
            turns_per_agent=args.turns,
            temperature=settings.conversation_temperature,
            repetition_penalty=settings.conversation_repetition_penalty,
            max_tokens=settings.conversation_max_tokens,
        )
        request = ConversationRequest(
            persona_a=persona_a,
            persona_b=persona_b,
            situation=situation,
            config=config,
        )

        runner = ConversationRunner()
        turns = await runner.run(request)

        # Save transcript
        await complete_run(db, run_record.id, turns)
        await record_pairing(db, persona_a.name, persona_b.name, run_record.id)

        # Print transcript
        print(f"\n{'─' * 60}")
        print("TRANSCRIPT")
        print(f"{'─' * 60}\n")
        for turn in turns:
            persona_label = (
                persona_a.title
                if turn.persona_name == persona_a.name
                else persona_b.title
            )
            print(f"[Turn {turn.turn_number}] {persona_label}:")
            print(f"{turn.content}\n")

        print(f"{'=' * 60}")
        print(f"Conversation completed. Run ID: {run_record.id}")
        print(f"{'=' * 60}")

        # Run synthesis unless explicitly disabled
        concept = None
        if not args.no_synthesis:
            concept = await _run_synthesis(
                db=db,
                domain=domain,
                run_record_id=run_record.id,
                transcript=turns,
                persona_a_name=persona_a.name,
                persona_b_name=persona_b.name,
                situation_text=situation.text,
            )

        # Run scoring if synthesis produced a concept
        if concept is not None and not args.no_scoring:
            await _run_scoring(db=db, domain=domain, concept=concept)

    except ConversationError as e:
        logger.error("Conversation failed: %s", e)
        await fail_run(db, run_record.id, str(e))
        sys.exit(1)
    finally:
        await db.close()


def main() -> None:
    """Entry point for the CLI runner."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    args = parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
