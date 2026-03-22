# Feature 3 — Synthesizer Agent

The following plan should be complete, but validate documentation and codebase patterns before implementing. Pay special attention to naming of existing utils, types, and models. Import from the right files.

## Feature Description

Add a synthesizer agent that reads completed conversation transcripts and extracts structured creative concepts. The synthesizer is a third agent — separate from the two persona agents — that identifies transferable principles, unexpected reframings, and novel compound concepts that emerged from the collision between personas. It produces a structured artifact: a working title, core premise, and what makes it original (for the sci-fi domain).

The synthesizer uses the remote OpenAI API (GPT-4o) with structured output parsing to guarantee well-formed Pydantic model output. It runs once per completed conversation, not per turn.

## User Story

As a creative researcher
I want completed conversations automatically synthesized into structured concept artifacts
So that I can review novel ideas without reading full transcripts

## Problem Statement

Completed conversations produce raw transcripts but no structured output. A human would need to read every transcript to find interesting ideas. The synthesizer automates the extraction step, distilling each conversation into a reviewable concept with title, premise, and originality assessment.

## Solution Statement

Create a `src/synthesis/` module containing a `Synthesizer` class that accepts a completed transcript and returns a structured `Concept` via the OpenAI API's structured output feature (`client.beta.chat.completions.parse()` with a Pydantic model as `response_format`). Add a `concepts` table to the database. Extend the query layer to store and retrieve concepts. Wire synthesis into the CLI runner and add an API endpoint. Add boundary tests verifying the synthesis module only uses the remote OpenAI API (not vLLM).

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium
**Primary Systems Affected**: `src/synthesis/` (new), `src/db/`, `src/api/`, `scripts/run_conversation.py`
**Dependencies**: OpenAI API key with GPT-4o access, `openai>=1.60.0` (already installed)

---

## CONTEXT REFERENCES

### Relevant Codebase Files — MUST READ BEFORE IMPLEMENTING

- `src/config.py` (lines 40-52) — Why: Already defines `openai_api_key`, `synthesis_model` ("gpt-4o"). Synthesizer must use these settings.
- `src/engine/conversation.py` (lines 36-55, 180-206) — Why: Shows the pattern for wrapping `AsyncOpenAI` client. Mirror this structure for the synthesizer's client setup (timeout, max_retries). Also shows error class pattern (`ConversationError`, `InferenceError`).
- `src/engine/models.py` — Why: Shows Pydantic model pattern for engine data structures. Mirror this for synthesis models.
- `src/db/queries.py` (lines 1-101) — Why: Shows the complete pattern for typed queries — `_row_to_model()` helper, `transaction()` context manager, model definitions (`Turn`, `Run`, `RunCreate`). New concept queries must follow this exact pattern.
- `src/db/schema.py` (lines 15-44) — Why: Shows how schema DDL is defined. New `concepts` table DDL must be appended to `SCHEMA_SQL`.
- `src/api/routes.py` (lines 1-38) — Why: Shows route pattern — `router = APIRouter(prefix="/api")`, dependency injection via `request.app.state.db`. New synthesis endpoints follow this pattern.
- `scripts/run_conversation.py` (lines 160-196) — Why: Shows where synthesis should be called — after `complete_run()` and `record_pairing()`. The transcript is available as `turns` (list of `Turn`).
- `tests/conftest.py` (lines 75-87) — Why: Shows `mock_openai_response` fixture pattern. A similar fixture is needed for mock synthesis responses.
- `tests/test_engine.py` (lines 16-41) — Why: Shows how vLLM calls are mocked — `patch.object(runner._client.chat.completions, "create", mock_create)`. Synthesis tests must mock `client.beta.chat.completions.parse` similarly.
- `tests/test_boundaries.py` (lines 34-49) — Why: Shows boundary test pattern. Need to add a test verifying synthesis uses `openai_api_key` (remote API) and does NOT reference `vllm_base_url`.
- `.agents/DevPlan.md` (lines 54-62) — Why: Feature 3 definition and "done when" criteria.
- `.agents/Summary.md` (lines 53-63) — Why: Describes what the synthesizer should extract: transferable principles, unexpected reframings, novel compound concepts.
- `CLAUDE.md` (Architectural Boundaries table) — Why: Synthesis module communicates with OpenAI API only — no vLLM calls. Must not import from engine layer (synthesis is above engine in the hierarchy).

### New Files to Create

- `src/synthesis/__init__.py` — Package init for synthesis module
- `src/synthesis/models.py` — Pydantic models for structured concept output
- `src/synthesis/synthesizer.py` — Synthesizer class with OpenAI API integration
- `tests/test_synthesis.py` — Unit tests for the synthesizer

### Files to Modify

- `src/db/schema.py` — Add `concepts` table DDL
- `src/db/queries.py` — Add `Concept` model and concept CRUD queries
- `src/api/routes.py` — Add concept endpoints
- `scripts/run_conversation.py` — Wire synthesis after conversation completion
- `tests/conftest.py` — Add mock synthesis response fixture
- `tests/test_boundaries.py` — Add synthesis boundary tests
- `tests/test_db.py` — Add concept query tests

### Relevant Documentation

- [OpenAI Structured Outputs Guide](https://platform.openai.com/docs/guides/structured-outputs)
  - Section: Using with Pydantic models
  - Why: Core API pattern for the synthesizer's output parsing
- [OpenAI Python SDK - Structured Outputs](https://github.com/openai/openai-python#structured-outputs-parsing-helpers)
  - Section: `client.beta.chat.completions.parse()` usage
  - Why: Exact method signature and return type details

### Patterns to Follow

**Client Initialization (from `src/engine/conversation.py:45-54`):**
```python
self._client = AsyncOpenAI(
    api_key=settings.openai_api_key,  # Remote API, not "unused"
    timeout=httpx.Timeout(60.0, connect=5.0),
    max_retries=3,
)
```

**Error Class Pattern (from `src/engine/conversation.py:28-33`):**
```python
class SynthesisError(Exception):
    """Raised when synthesis encounters a non-recoverable error."""

class ExtractionError(SynthesisError):
    """Raised when the OpenAI API fails to extract concepts."""
```

**Query Layer Pattern (from `src/db/queries.py:71-89`):**
```python
def _row_to_concept(row: aiosqlite.Row) -> Concept:
    """Map a database row to a Concept model."""
    return Concept(
        id=UUID(row["id"]),
        run_id=UUID(row["run_id"]),
        # ... remaining fields
    )
```

**Structured Output API Pattern (OpenAI SDK >= 1.60.0):**
```python
response = await self._client.beta.chat.completions.parse(
    model=settings.synthesis_model,
    messages=[...],
    response_format=ConceptExtractionResult,  # Pydantic class, not instance
    temperature=0.4,
)
result = response.choices[0].message.parsed
if result is None:
    refusal = response.choices[0].message.refusal
    raise ExtractionError(f"Model refused: {refusal}")
```

**Naming Convention:** `snake_case` for modules and functions, `PascalCase` for classes, matching existing codebase.

**Logging Pattern (from `src/engine/conversation.py`):**
```python
logger = logging.getLogger(__name__)
logger.info("Extracting concepts", extra={"run_id": str(run_id)})
```

---

## IMPLEMENTATION PLAN — Milestone Breakdown

This feature is split into 4 milestone files for incremental execution. Each milestone has its own validation checkpoint.

| Milestone | File | Tasks | Focus |
|-----------|------|-------|-------|
| 1 | [feature3-milestone1-data-foundation.md](feature3-milestone1-data-foundation.md) | 1–3 | Synthesis models, DB schema, concept queries |
| 2 | [feature3-milestone2-synthesizer-core.md](feature3-milestone2-synthesizer-core.md) | 4 | Synthesizer class with OpenAI API integration |
| 3 | [feature3-milestone3-integration.md](feature3-milestone3-integration.md) | 5–6 | CLI runner wiring + API endpoints |
| 4 | [feature3-milestone4-testing-validation.md](feature3-milestone4-testing-validation.md) | 7–8 | All tests + full validation suite |

Execute milestones in order — each depends on the previous.

---

## ACCEPTANCE CRITERIA

- [ ] `src/synthesis/` module exists with `models.py` and `synthesizer.py`
- [ ] `ConceptExtraction` Pydantic model with `title`, `premise`, `originality` fields
- [ ] `Synthesizer` class uses `client.beta.chat.completions.parse()` with structured output
- [ ] `Synthesizer` handles refusals and API errors with clear exception types
- [ ] `concepts` table added to SQLite schema with run foreign key
- [ ] `Concept`, `ConceptCreate` models in `src/db/queries.py`
- [ ] Concept CRUD queries (`create_concept`, `get_concepts`, `get_concept_by_run_id`, `update_concept_status`)
- [ ] CLI runner calls synthesis after conversation completion (with `--no-synthesis` opt-out)
- [ ] CLI gracefully handles missing API key (warns, skips synthesis)
- [ ] API endpoints: `GET /api/concepts`, `GET /api/runs/{run_id}/concept`
- [ ] Synthesis prompt instructs model to extract transferable principles, reframings, novel compounds
- [ ] All synthesis tests pass with mocked OpenAI calls
- [ ] Boundary tests verify synthesis uses remote API (not vLLM) and doesn't import engine
- [ ] `uv run ruff check .` passes with 0 errors
- [ ] `uv run ruff format --check .` passes with 0 errors
- [ ] `uv run pytest -v` passes with all tests green
- [ ] No real LLM calls in tests

---

## EXECUTION STRATEGY

**Recommended approach**: Milestones

**Rationale**: 8 tasks with clear layer dependencies — data models → database → service → integration → tests. Tasks within each layer are tightly coupled, but layers are loosely coupled. Medium complexity with OpenAI API integration adds risk, so validation checkpoints between milestones catch issues early.

### Milestones

**Milestone 1: Data Foundation** (Tasks 1–3)
- Create synthesis models, extend database schema, add concept queries
- **Validation checkpoint**: `uv run python -c "from src.synthesis.models import ConceptExtraction; from src.db.queries import Concept, ConceptCreate; print('OK')"` and schema contains concepts table

**Milestone 2: Synthesizer Core** (Task 4)
- Implement the Synthesizer class with OpenAI API integration
- **Validation checkpoint**: `uv run python -c "from src.synthesis.synthesizer import Synthesizer, SynthesisError, ExtractionError; print('OK')"` and synthesis prompt is well-formed

**Milestone 3: Integration** (Tasks 5–6)
- Wire synthesis into CLI runner and API endpoints
- **Validation checkpoint**: CLI `--help` shows new flags, API routes include concept endpoints

**Milestone 4: Testing & Validation** (Tasks 7–8)
- Add all tests, run full validation suite
- **Validation checkpoint**: `uv run pytest -v` all green, `uv run ruff check .` clean

---

## NOTES

**Synthesis prompt design is critical.** The prompt should NOT ask the model to summarize the conversation. It should instruct the model to find the collision points — moments where the two personas fundamentally talked past each other in interesting ways — and extract the novel idea that lives in the gap. The DevPlan and Summary are explicit: the synthesizer identifies "transferable principles, unexpected reframings, and novel compound concepts."

**Domain-specific output.** For the sci-fi domain (first application), the structured output is: working title, core premise, and what makes it original. The `ConceptExtraction` model encodes this. When Feature 6 (Domain Expansion) arrives, this model may become domain-configurable, but for now it's hardcoded for sci-fi.

**Structured output guarantees.** Using `client.beta.chat.completions.parse()` with a Pydantic model as `response_format` guarantees the API returns valid JSON matching the schema exactly. The SDK's strict mode ensures no missing fields and correct types. This means we don't need defensive JSON parsing — the `ConceptExtraction` model is always fully populated.

**Temperature trade-off.** Conversations use temperature 0.9 (creative generation). Synthesis should use lower temperature (~0.4) because we want consistent, accurate extraction — not creative reinterpretation of the transcript.

**Failure isolation.** Synthesis failure must NOT lose the conversation transcript. The transcript is already saved before synthesis runs. If synthesis fails (API down, rate limit, refusal), the run remains `completed` with its transcript, and synthesis can be retried later via `--synthesis-only`.

**Layer dependency.** The synthesis module (`src/synthesis/`) sits above the engine layer but below the API layer. It imports from `src/config` and `src/db/queries` (data layer). It must NOT import from `src/engine/` — this would violate the architectural boundaries defined in CLAUDE.md.
