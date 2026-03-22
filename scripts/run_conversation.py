"""
CLI runner for the Medici Engine.

Runs a single conversation between two persona agents with a shared
object, stores the transcript in the database, optionally synthesizes
a concept from the transcript, and prints results. This is the primary
interface for Features 1-4.

Usage:
    uv run python scripts/run_conversation.py
    uv run python scripts/run_conversation.py --turns 3
    uv run python scripts/run_conversation.py --no-synthesis
    uv run python scripts/run_conversation.py --synthesis-only <run-id>
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
    ConceptCreate,
    RunCreate,
    complete_run,
    create_concept,
    create_run,
    fail_run,
    get_run_by_id,
    record_pairing,
)
from src.db.schema import init_schema
from src.engine.conversation import ConversationError, ConversationRunner
from src.engine.models import ConversationConfig, ConversationRequest
from src.personas.library import (
    get_all_personas,
    get_all_shared_objects,
    get_persona_by_name,
    get_persona_pair,
    get_random_shared_object,
)
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
        "--shared-object",
        type=int,
        default=None,
        help="Index of the shared object to use (default: random)",
    )
    parser.add_argument(
        "--list-personas",
        action="store_true",
        help="List all available personas and exit",
    )
    parser.add_argument(
        "--list-objects",
        action="store_true",
        help="List all available shared objects and exit",
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
    return parser.parse_args()


async def _run_synthesis(
    db: aiosqlite.Connection,
    run_record_id: UUID,
    transcript: list,
    persona_a_name: str,
    persona_b_name: str,
    shared_object_text: str,
) -> None:
    """Run synthesis on a transcript and persist the extracted concept.

    Synthesis failure is logged but does not raise — the conversation
    transcript is already saved and synthesis can be retried later.

    Args:
        db: Database connection.
        run_record_id: ID of the run to attach the concept to.
        transcript: Ordered list of conversation turns.
        persona_a_name: Name of the first persona.
        persona_b_name: Name of the second persona.
        shared_object_text: The shared object that seeded the conversation.
    """
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not set — skipping synthesis")
        print("\n⚠ Synthesis skipped: OPENAI_API_KEY not configured")
        return

    print(f"\n{'─' * 60}")
    print("SYNTHESIS")
    print(f"{'─' * 60}\n")

    try:
        synthesizer = Synthesizer()
        extraction = await synthesizer.synthesize(
            transcript=transcript,
            persona_a_name=persona_a_name,
            persona_b_name=persona_b_name,
            shared_object_text=shared_object_text,
        )

        concept = await create_concept(
            db,
            ConceptCreate(
                run_id=run_record_id,
                title=extraction.title,
                premise=extraction.premise,
                originality=extraction.originality,
            ),
        )

        print(f"Title:       {concept.title}")
        print(f"Premise:     {concept.premise}")
        print(f"Originality: {concept.originality}")
        print(f"Concept ID:  {concept.id}")

    except SynthesisError as e:
        logger.error("Synthesis failed: %s", e)
        print(f"\n⚠ Synthesis failed: {e}")
        print("The conversation transcript has been saved. You can retry with:")
        print(
            f"  uv run python scripts/run_conversation.py"
            f" --synthesis-only {run_record_id}"
        )


async def _synthesis_only(db: aiosqlite.Connection, run_id_str: str) -> None:
    """Run synthesis on an existing completed run.

    Args:
        db: Database connection.
        run_id_str: String UUID of the run to synthesize.
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
    print(f"{'=' * 60}")

    await _run_synthesis(
        db=db,
        run_record_id=run_record.id,
        transcript=run_record.transcript,
        persona_a_name=run_record.persona_a_name,
        persona_b_name=run_record.persona_b_name,
        shared_object_text=run_record.shared_object_text,
    )


async def run(args: argparse.Namespace) -> None:
    """Execute a conversation run with the given arguments."""
    # Handle list commands
    if args.list_personas:
        for persona in get_all_personas():
            print(f"  {persona.name}: {persona.title}")
        return

    if args.list_objects:
        for i, obj in enumerate(get_all_shared_objects()):
            print(f"  [{i}] ({obj.object_type}) {obj.text[:80]}...")
        return

    # Connect to database
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(settings.database_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    await init_schema(db)

    try:
        # Handle synthesis-only mode
        if args.synthesis_only:
            await _synthesis_only(db, args.synthesis_only)
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

        # Select shared object
        if args.shared_object is not None:
            objects = get_all_shared_objects()
            if args.shared_object < 0 or args.shared_object >= len(objects):
                logger.error(
                    "Shared object index out of range: %d (0-%d)",
                    args.shared_object,
                    len(objects) - 1,
                )
                sys.exit(1)
            shared_object = objects[args.shared_object]
        else:
            shared_object = get_random_shared_object()

        # Create run record
        run_record = await create_run(
            db,
            RunCreate(
                persona_a_name=persona_a.name,
                persona_b_name=persona_b.name,
                shared_object_text=shared_object.text,
                shared_object_type=shared_object.object_type,
                turns_per_agent=args.turns,
            ),
        )

        print(f"\n{'=' * 60}")
        print("MEDICI ENGINE — Conversation Run")
        print(f"{'=' * 60}")
        print(f"Run ID:         {run_record.id}")
        print(f"Persona A:      {persona_a.title}")
        print(f"Persona B:      {persona_b.title}")
        print(f"Shared Object:  {shared_object.text[:80]}...")
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
            shared_object=shared_object,
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
        if not args.no_synthesis:
            await _run_synthesis(
                db=db,
                run_record_id=run_record.id,
                transcript=turns,
                persona_a_name=persona_a.name,
                persona_b_name=persona_b.name,
                shared_object_text=shared_object.text,
            )

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
