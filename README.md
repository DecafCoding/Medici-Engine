# Medici Engine

A multi-agent creative collision system that pairs AI agents embodying radically different personas, gives them a shared object to react to, and mines the productive misunderstandings for novel ideas.

A synthesizer agent extracts structured output from the conversation, a scoring model rates it with reasoning, and a human makes the final keep/discard call.

> This is a serendipity surface area expander — a machine for making lucky accidents more likely.

## How It Works

1. **Persona Assignment** — Two agents are each given a deeply specific persona: a worldview, vocabulary, core obsessions, and characteristic way of seeing. The further apart conceptually, the higher the variance.

2. **Shared Object** — Both agents react to a concrete shared object (a problem, scenario, or question) through their own domain lens. The collision happens in the interpretation gap.

3. **Conversation** — The agents converse for a fixed number of turns. The key artifact isn't agreement — it's productive friction, where two personas fundamentally talk past each other in interesting ways.

4. **Synthesis** — A third agent reads the transcript and extracts transferable principles, unexpected reframings, and novel compound concepts that emerged from the collision.

5. **Scoring** — A higher-capability model scores the synthesizer's output across domain-specific axes with reasoning — not just numbers.

6. **Human Review** — A review UI surfaces concepts and scores for a human to make the final call. Automation increases surface area; recognition of value still requires a human.

## Architecture

| Component | Module | Description |
|---|---|---|
| Conversation Engine | `src/engine/` | Turn-taking, transcript generation, vLLM communication |
| Persona Library | `src/personas/` | Curated persona definitions, selection logic, pairing history |
| Synthesizer | `src/synthesis/` | Transcript analysis, structured concept extraction (Claude Sonnet) |
| Scorer | `src/scoring/` | Concept evaluation across domain axes (Claude Opus) |
| Data Layer | `src/db/` | SQLite storage, schema, typed queries |
| API / UI | `src/api/` | FastAPI endpoints for review UI and batch setup |

## Tech Stack

- **Python 3.12** with async-native patterns throughout
- **FastAPI** — API and review UI
- **Pydantic AI** — structured agent output
- **vLLM** — local model inference (OpenAI-compatible API)
- **OpenAI API** — synthesis (GPT-4o) and scoring (o3)
- **SQLite** (aiosqlite) — zero-infrastructure persistence
- **Ruff** — linting and formatting
- **uv** — package management

## Infrastructure

- **4x NVIDIA 5060Ti** (16GB VRAM each, 64GB total) for local conversation model inference via vLLM
- **Starting model:** MythoMax-L2-13B — fits on a single GPU, enabling up to 4 parallel conversations
- **Graduation path:** 13B (4x parallel) → ~27B (2x parallel) → 103B (serial) as quality demands increase

## Expected Yield

The system is honest about how creativity works:

- ~60% produce nothing useful
- ~30% produce interesting-but-not-actionable observations
- ~10% produce something worth developing further
- ~1-2% produce a genuinely surprising reframe or concept

This is the design intent, not a failure mode.

## First Domain

**Sci-fi book concepts.** The synthesizer produces a working title, core premise, and what makes it original. The scoring model rates each concept on uniqueness, scientific plausibility, and compelling factor — each with reasoning.

## Setup

```bash
# Install dependencies
uv sync

# Copy environment config
cp .env.example .env
# Edit .env with your OpenAI API key and vLLM settings

# Run tests
uv run pytest

# Start the API server
uv run uvicorn src.api.main:app --reload
```

## Configuration

Key environment variables (see `.env.example` for the full list):

| Variable | Default | Description |
|---|---|---|
| `VLLM_BASE_URL` | `http://localhost:8000/v1` | Local vLLM server endpoint |
| `CONVERSATION_MODEL` | `MythoMax-L2-13B` | Model served by vLLM |
| `OPENAI_API_KEY` | — | API key for synthesis and scoring |
| `SYNTHESIS_MODEL` | `gpt-4o` | Model for concept extraction |
| `SCORING_MODEL` | `o3` | Model for concept evaluation |
| `DATABASE_PATH` | `data/yield_engine.db` | SQLite database path |

## License

All rights reserved.
