# Medici Engine

A multi-agent creative collision system that pairs AI agents embodying radically different personas, gives them a shared object to react to, and mines the productive misunderstandings for novel ideas.

A synthesizer agent extracts structured output from the conversation, a scoring model rates it with reasoning, and a human makes the final keep/discard call.

> This is a serendipity surface area expander — a machine for making lucky accidents more likely.

## AI Development

All the code in this repo was created by Claude Code. I have been a C# developer for 20 years, not a single day on Python. So using Claude Code to develop Python pushes me to focus more on the overall process like planning, communication, and testing versus just looking at the code to determine quality of the application. This is an application I intend to use regularly. If it benefits you, let me know.

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
| Persona Library | `src/personas/` | Curated persona definitions, selection logic, performance-informed pairing |
| Synthesizer | `src/synthesis/` | Transcript analysis, structured concept extraction via OpenAI API |
| Scorer | `src/scoring/` | Concept evaluation across domain axes via OpenAI API |
| Domains | `src/domains/` | Domain-agnostic configuration registry (extraction fields, scoring axes, prompts) |
| Batch Runner | `src/batch/` | Full pipeline orchestration: selection → conversation → synthesis → scoring |
| Data Layer | `src/db/` | SQLite storage, schema, typed queries, analytics aggregation |
| API | `src/api/` | REST endpoints for runs, concepts, and scores |
| UI | `src/ui/` | HTMX-based batch setup, concept review, and insights dashboard |

## Tech Stack

- **Python 3.12** with async-native patterns throughout
- **FastAPI** — API and server-rendered UI
- **Pydantic** — structured models and OpenAI structured output
- **Jinja2 + HTMX** — server-rendered UI with interactive updates, no frontend build
- **vLLM** — local model inference (OpenAI-compatible API)
- **OpenAI API** — synthesis and scoring (models configurable via env vars)
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

## Domains

The system is domain-agnostic — the domain defines what the synthesizer extracts and how the scorer evaluates, not the engine itself. Two built-in domains ship today:

- **Sci-Fi Concepts** — Extracts a working title, core premise, and what makes it original. Scores on uniqueness, scientific plausibility, and compelling factor.
- **Product Design** — Extracts a product name, problem statement, and proposed solution. Scores on novelty, feasibility, and market potential.

Adding a new domain is a configuration change: define the extraction fields, scoring axes, and prompts in a Python module and register it.

## Feedback Loop

The system tracks which persona pairings and shared objects produce the best results. An insights dashboard (`/ui/insights`) surfaces:

- **Pairing performance** — average scores, kept rates, and run counts per persona pair
- **Shared object performance** — which seeds generate the most generative collisions

Batch runs can optionally use **performance-informed selection**, which weights persona pairing toward historically higher-scoring combinations while maintaining an exploration rate (default 20%) to keep discovering new pairings.

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
uv run uvicorn src.main:app --reload
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
| `ACTIVE_DOMAIN` | `sci-fi-concepts` | Active domain (`sci-fi-concepts`, `product-design`) |
| `DATABASE_PATH` | `data/yield_engine.db` | SQLite database path |

## License

All rights reserved.
