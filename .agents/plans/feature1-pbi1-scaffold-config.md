# PBI 1: Project Scaffold & Configuration

**Feature**: 1 — Core Conversation Engine
**Tasks**: 1–5 of 28
**Dependencies**: None (first PBI)
**Estimated Complexity**: Medium

---

## Objective

Bootstrap the Medici Engine project from zero: initialize uv, install all dependencies, configure Ruff and Pytest, create the `.env` setup, and implement the configuration module that all other modules depend on.

## User Story

As a developer
I want a fully configured Python 3.12 project with all tooling in place
So that subsequent PBIs can focus on application logic without setup friction

## Pre-Implementation Reading

- `CLAUDE.md` — All coding conventions, naming rules, documentation requirements
- `.agents/DevPlan.md` (lines 139-160) — Resolved decisions on models, storage, run trigger

---

## STEP-BY-STEP TASKS

### Task 1: CREATE `pyproject.toml`

Initialize the project and configure all tooling.

- **IMPLEMENT**: Run `uv init` or create `pyproject.toml` manually with the following structure:

```toml
[project]
name = "yield-engine"
version = "0.1.0"
description = "Multi-agent creative collision system for generating novel ideas"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "openai>=1.60.0",
    "aiosqlite>=0.21.0",
    "pydantic>=2.10.0",
    "python-dotenv>=1.0.0",
]

[dependency-groups]
dev = [
    "ruff>=0.9.0",
    "pytest>=8.3.0",
    "pytest-asyncio>=0.25.0",
    "httpx>=0.28.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.backends"

# ── Ruff ──────────────────────────────────────────────
[tool.ruff]
target-version = "py312"
line-length = 88
src = ["src"]

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort
    "N",      # pep8-naming
    "UP",     # pyupgrade (modern Python syntax)
    "B",      # flake8-bugbear
    "SIM",    # flake8-simplify
    "ASYNC",  # flake8-async
]

[tool.ruff.lint.isort]
known-first-party = ["src"]

# ── Pytest ────────────────────────────────────────────
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- **GOTCHA**: Use `uv add` commands after creating this file to generate `uv.lock`. Alternatively, create the file manually then run `uv sync` to resolve and lock dependencies. Either approach works — the lock file must be committed.
- **GOTCHA**: `pydantic-settings` is a separate package from `pydantic` since Pydantic v2. You must add it as a dependency: `uv add pydantic-settings`. Without it, `BaseSettings` will not be available.
- **VALIDATE**: `uv sync && echo "Dependencies resolved successfully"`

---

### Task 2: CREATE `.gitignore`

- **IMPLEMENT**: Standard Python gitignore plus project-specific entries:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
*.egg

# Virtual environment
.venv/

# Environment variables
.env

# Database
data/*.db

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# uv
.python-version

# Testing
.pytest_cache/
.coverage
htmlcov/
```

- **VALIDATE**: `cat .gitignore | head -5`

---

### Task 3: CREATE `.env.example`

- **IMPLEMENT**: Document all environment variables with defaults and descriptions:

```env
# ── vLLM Local Inference ──────────────────────────────
# Base URL for the local vLLM server (must include /v1 path)
VLLM_BASE_URL=http://localhost:8000/v1

# Model name served by vLLM (must match --served-model-name)
CONVERSATION_MODEL=MythoMax-L2-13B

# ── OpenAI API (not used in Feature 1) ─────────────────
# API key for synthesis and scoring (Features 3-4)
OPENAI_API_KEY=

# Model for synthesis (Feature 3)
SYNTHESIS_MODEL=gpt-4o

# Model for scoring (Feature 4)
SCORING_MODEL=o3

# ── Database ──────────────────────────────────────────
# Path to SQLite database file
DATABASE_PATH=data/yield_engine.db

# ── Conversation Defaults ─────────────────────────────
# Default number of turns per agent (10 total exchanges)
DEFAULT_TURNS=5

# ── Inference Parameters ──────────────────────────────
# Temperature for conversation generation (0.0-2.0)
CONVERSATION_TEMPERATURE=0.9

# Repetition penalty for vLLM (1.0 = no penalty)
CONVERSATION_REPETITION_PENALTY=1.15

# Maximum tokens per turn
CONVERSATION_MAX_TOKENS=512
```

- **VALIDATE**: `cat .env.example | grep -c "="`  (should show ~10 variables)

---

### Task 4: CREATE `src/__init__.py`

- **IMPLEMENT**: Empty file (package marker).
- **VALIDATE**: `test -f src/__init__.py && echo "exists"`

---

### Task 5: CREATE `src/config.py`

Single source of truth for all configuration. Other modules import from here — they never read `os.getenv` directly.

- **IMPLEMENT**:

```python
"""
Configuration module for the Medici Engine.

Loads all settings from environment variables via python-dotenv.
This is the single source of truth for configuration — no other
module should read os.getenv directly. This module is the lowest
layer in the dependency hierarchy.
"""

import logging
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# Load .env file from project root
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All configuration flows through this class. Values are read from
    environment variables with fallback defaults suitable for local
    development.
    """

    # vLLM local inference
    vllm_base_url: str = Field(
        default="http://localhost:8000/v1",
        description="Base URL for the local vLLM server",
    )
    conversation_model: str = Field(
        default="MythoMax-L2-13B",
        description="Model name served by vLLM",
    )

    # OpenAI API (not used in Feature 1)
    openai_api_key: str = Field(
        default="",
        description="API key for OpenAI (synthesis and scoring)",
    )
    synthesis_model: str = Field(
        default="gpt-4o",
        description="OpenAI model for synthesis",
    )
    scoring_model: str = Field(
        default="o3",
        description="OpenAI model for scoring",
    )

    # Database
    database_path: str = Field(
        default="data/yield_engine.db",
        description="Path to SQLite database file",
    )

    # Conversation defaults
    default_turns: int = Field(
        default=5,
        description="Default number of turns per agent",
    )

    # Inference parameters
    conversation_temperature: float = Field(
        default=0.9,
        description="Temperature for conversation generation",
    )
    conversation_repetition_penalty: float = Field(
        default=1.15,
        description="Repetition penalty for vLLM",
    )
    conversation_max_tokens: int = Field(
        default=512,
        description="Maximum tokens per conversation turn",
    )

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
```

- **IMPORTS**: `pydantic`, `pydantic-settings`, `python-dotenv`
- **GOTCHA**: `pydantic-settings` is a separate package from `pydantic` since Pydantic v2. Must be added as dependency.
- **VALIDATE**: `uv run python -c "from src.config import settings; print(settings.vllm_base_url)"`

---

## Files Created

```
├── .env.example
├── .gitignore
├── pyproject.toml
├── uv.lock                  (generated by uv sync)
├── data/
│   └── .gitkeep
└── src/
    ├── __init__.py
    └── config.py
```

Also create `data/.gitkeep` (empty file to ensure the data directory is tracked).

---

## Validation Commands

```bash
# Dependencies resolve
uv sync

# Config loads
uv run python -c "from src.config import settings; print(settings.model_dump())"

# Ruff runs (no source to lint yet beyond config.py)
uv run ruff check src/
uv run ruff format --check src/
```

## Done When

- [ ] `uv sync` resolves all dependencies without errors
- [ ] `uv.lock` is generated and committed
- [ ] `src/config.py` loads all settings with correct defaults
- [ ] `uv run ruff check src/` passes with 0 errors
- [ ] `uv run ruff format --check src/` passes with 0 errors
