"""
CLI runner for the Medici Engine.

Runs a single conversation between two persona agents with a shared
object, stores the transcript in the database, and prints results.
This is the primary interface for Features 1-4.

Usage:
    uv run python scripts/run_conversation.py
    uv run python scripts/run_conversation.py --turns 3
    uv run python scripts/run_conversation.py \\
        --persona-a quantum_information_theorist \\
        --persona-b medieval_master_builder
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import aiosqlite

from src.config import settings
from src.db.queries import (
    RunCreate,
    complete_run,
    create_run,
    fail_run,
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
    return parser.parse_args()


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
