"""
Application entry point for the Medici Engine.

Configures the FastAPI application with lifespan-managed resources
including the SQLite database connection. This module belongs to
the API layer.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite
from fastapi import FastAPI, Request

from src.api.routes import router
from src.config import settings
from src.db.schema import init_schema

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application-scoped resources.

    Creates the SQLite database connection on startup and ensures
    the schema is initialized. Closes the connection on shutdown.
    """
    # Ensure the data directory exists
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Connecting to database", extra={"path": settings.database_path})
    app.state.db = await aiosqlite.connect(settings.database_path)
    app.state.db.row_factory = aiosqlite.Row

    # Enable WAL mode for better concurrent read performance
    await app.state.db.execute("PRAGMA journal_mode=WAL")
    # SQLite does not enforce foreign keys by default
    await app.state.db.execute("PRAGMA foreign_keys=ON")

    await init_schema(app.state.db)
    logger.info("Application startup complete")

    yield

    await app.state.db.close()
    logger.info("Database connection closed")


app = FastAPI(
    title="Medici Engine",
    description="Multi-agent creative collision system",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health")
async def health(request: Request) -> dict[str, str]:
    """Return service health status with database connectivity check."""
    async with request.app.state.db.execute("SELECT 1") as cursor:
        await cursor.fetchone()
    return {"status": "ok"}
