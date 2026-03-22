# Feature 4 — Milestone 2: Scorer Core

**Parent plan**: `feature4-scoring-layer.md`
**Tasks**: 4
**Goal**: Build the Scorer class with OpenAI o3 integration

---

## Feature Context

Add a scoring layer that evaluates concepts extracted by the synthesizer. A higher-capability model (OpenAI o3) scores each concept across domain-specific axes — uniqueness, scientific plausibility, and compelling factor — with written reasoning for each score.

## User Story

As a human reviewer of Medici Engine output
I want each concept scored across multiple axes with written reasoning
So that I can make faster, better-informed keep/discard decisions without reading the full transcript

---

## CONTEXT REFERENCES

### Relevant Codebase Files — READ BEFORE IMPLEMENTING

- `src/synthesis/synthesizer.py` (full file) — Why: The scoring module mirrors this pattern exactly — same OpenAI client setup, same structured output via `beta.chat.completions.parse`, same error hierarchy. This is the primary pattern to follow.
- `src/scoring/models.py` (created in Milestone 1) — Why: The `ConceptScoring` model is the `response_format` for the API call.
- `src/config.py` (lines 48-52) — Why: `scoring_model` setting already exists (default `o3`). No config changes needed.
- `CLAUDE.md` — Why: Architectural boundaries, documentation requirements.

### New Files to Create

- `src/scoring/scorer.py` — `Scorer` class with OpenAI o3 integration

### Patterns to Follow

**OpenAI Structured Output Pattern** (from `src/synthesis/synthesizer.py`):
```python
response = await self._client.beta.chat.completions.parse(
    model=settings.scoring_model,
    messages=messages,
    response_format=ConceptScoring,  # Pydantic model
    temperature=0.3,  # Lower than synthesis — scoring should be more deterministic
)
result = response.choices[0].message.parsed
if result is None:
    refusal = response.choices[0].message.refusal
    raise EvaluationError(f"Model refused to score concept: {refusal}")
```

**Client Initialization Pattern** (from `src/synthesis/synthesizer.py`):
```python
self._client = AsyncOpenAI(
    api_key=settings.openai_api_key,
    timeout=httpx.Timeout(60.0, connect=5.0),
    max_retries=3,
)
```

**Error Hierarchy Pattern** (from `src/synthesis/synthesizer.py`):
```python
class ScoringError(Exception):
    """Raised when scoring encounters a non-recoverable error."""

class EvaluationError(ScoringError):
    """Raised when the OpenAI API fails to score."""
```

**Naming Conventions:**
- Module: `scorer.py` (noun, like `synthesizer.py`)
- Class: `Scorer` (like `Synthesizer`)
- Method: `score()` (like `synthesize()`)
- Errors: `ScoringError`, `EvaluationError` (like `SynthesisError`, `ExtractionError`)

**Logging Pattern:**
```python
logger = logging.getLogger(__name__)
logger.info("Scoring concept", extra={"concept_title": title})
```

---

## IMPLEMENTATION PLAN

### Task 4: Build the scorer module

Create the `Scorer` class that sends concepts to o3 for evaluation.

- **CREATE**: `src/scoring/scorer.py`
- **MIRROR**: `src/synthesis/synthesizer.py` — same class structure, client init, error handling, message building
- **IMPLEMENT**:
  - Module docstring explaining the scoring layer's role
  - `SCORING_PROMPT` constant — system prompt instructing o3 to evaluate across three axes with reasoning. The prompt must:
    - Establish o3 as an evaluator of novel creative concepts
    - Define each axis clearly: uniqueness (has this been done before?), scientific plausibility (could the science work, even speculatively?), compelling factor (would someone want to read this?)
    - Instruct scoring on 0.0-10.0 scale
    - Require reasoning that explains the score — not just a number
    - Instruct that reasoning should help a human reviewer make a faster decision
  - `ScoringError(Exception)` and `EvaluationError(ScoringError)` — error hierarchy
  - `Scorer` class:
    - `__init__`: create `AsyncOpenAI` client with `settings.openai_api_key`
    - `async def score(self, title: str, premise: str, originality: str) -> ConceptScoring`: main entry point
    - `def _build_messages(self, title, premise, originality) -> list[dict[str, str]]`: build system + user messages
  - Use `settings.scoring_model` (already configured as `o3`)
  - Temperature: `0.3` — scoring should be more deterministic than synthesis
- **IMPORTS**: `logging`, `httpx`, `openai` (APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI), `src.config.settings`, `src.scoring.models.ConceptScoring`
- **GOTCHA**: The scoring layer must NOT import from `src.engine` or reference `vllm_base_url`. It uses the remote OpenAI API only.
- **VALIDATE**: `uv run ruff check src/scoring/ && uv run ruff format --check src/scoring/`

---

## VALIDATION CHECKPOINT

```bash
uv run ruff check src/scoring/ && uv run ruff format --check src/scoring/
```

**Expected**: Module imports cleanly, follows synthesis pattern, linting passes.

---

## ACCEPTANCE CRITERIA (Milestone 2)

- [ ] `src/scoring/scorer.py` implements `Scorer` class using OpenAI o3 with structured output
- [ ] `SCORING_PROMPT` constant defines evaluation criteria for all three axes
- [ ] `ScoringError` and `EvaluationError` exception hierarchy defined
- [ ] Scorer uses `settings.scoring_model` and `settings.openai_api_key`
- [ ] Scorer does NOT import from `src.engine` or reference `vllm_base_url`
- [ ] Ruff check and format pass

---

## NOTES

- **Scoring model (o3)** is already configured in `src/config.py` as `settings.scoring_model`. No config changes needed.
- **Temperature 0.3** for scoring — lower than synthesis (0.4) because scoring should be more consistent. Still non-zero to allow nuanced reasoning.
- **The scoring layer sits above synthesis in the dependency hierarchy** (`API → Scoring → Synthesis → Engine → ...`). The scorer must NOT import from `src.synthesis/` — it receives concept data as plain arguments, not synthesis module objects.
