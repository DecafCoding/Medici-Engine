# Feature 4 — Milestone 4: Testing & Validation

**Parent plan**: `feature4-scoring-layer.md`
**Tasks**: 7–11
**Goal**: Add all test fixtures, unit tests, boundary tests; run full suite with zero regressions

---

## Feature Context

Add a scoring layer that evaluates concepts extracted by the synthesizer. This milestone adds comprehensive test coverage for all scoring functionality — the scorer module, database queries, API endpoints, and architectural boundary verification.

## User Story

As a human reviewer of Medici Engine output
I want each concept scored across multiple axes with written reasoning
So that I can make faster, better-informed keep/discard decisions without reading the full transcript

---

## CONTEXT REFERENCES

### Relevant Codebase Files — READ BEFORE IMPLEMENTING

- `tests/test_synthesis.py` (full file) — Why: Scoring tests mirror these exactly — mock `beta.chat.completions.parse`, test success/refusal/connection error.
- `tests/conftest.py` (full file) — Why: New fixtures for scoring follow the same patterns as synthesis fixtures.
- `tests/test_boundaries.py` (full file) — Why: Must add boundary tests for the scoring module (uses remote API, no vLLM, no engine imports).
- `tests/test_db.py` (full file) — Why: Score query tests follow the same patterns as concept query tests.
- `tests/test_api.py` (full file) — Why: Score endpoint tests follow the same patterns as concept endpoint tests.
- `src/scoring/scorer.py` (created in Milestone 2) — Why: The module under test.
- `src/scoring/models.py` (created in Milestone 1) — Why: Models used in fixtures.

### New Files to Create

- `tests/test_scoring.py` — Unit tests for scorer module

### Files to Modify

- `tests/conftest.py` — Add scoring-related fixtures
- `tests/test_boundaries.py` — Add scoring boundary tests
- `tests/test_db.py` — Add score query tests
- `tests/test_api.py` — Add score endpoint tests

### Patterns to Follow

**Mock Pattern** (from `tests/test_synthesis.py`):
```python
synthesizer = Synthesizer()
mock_parse = AsyncMock(
    return_value=mock_parse_response(extraction=test_concept_extraction),
)
with patch.object(synthesizer._client.beta.chat.completions, "parse", mock_parse):
    result = await synthesizer.synthesize(...)
```

**Fixture Pattern** (from `tests/conftest.py`):
```python
@pytest.fixture
def mock_parse_response():
    """Create a factory for mock OpenAI structured output parse responses."""
    def _make_response(extraction=None, refusal=None):
        response = MagicMock()
        choice = MagicMock()
        choice.message.parsed = extraction
        choice.message.refusal = refusal
        response.choices = [choice]
        return response
    return _make_response
```

**Boundary Test Pattern** (from `tests/test_boundaries.py`):
```python
def test_synthesis_uses_remote_openai_api() -> None:
    synthesis_dir = Path("src/synthesis")
    for py_file in synthesis_dir.rglob("*.py"):
        source = py_file.read_text()
        if "AsyncOpenAI" in source:
            assert "openai_api_key" in source, (...)
```

---

## IMPLEMENTATION PLAN

### Task 7: Add test fixtures for scoring

Add shared fixtures that scoring tests will use.

- **UPDATE**: `tests/conftest.py`
- **PATTERN**: Follow `mock_parse_response` and `test_concept_extraction` fixtures (lines 91-125)
- **IMPLEMENT**:
  - Import `ConceptScoring` and `AxisScore` from `src.scoring.models`
  - `mock_scoring_response()` fixture — factory for mock parse responses with `ConceptScoring`. Reuse the same `_make_response` pattern as `mock_parse_response` but the factory accepts a `ConceptScoring | None` for the parsed field.
  - `test_concept_scoring()` fixture — sample `ConceptScoring` with realistic scores and reasoning across all three axes
- **VALIDATE**: `uv run ruff check tests/conftest.py`

### Task 8: Write scorer unit tests

Test the scorer module — all OpenAI calls mocked.

- **CREATE**: `tests/test_scoring.py`
- **MIRROR**: `tests/test_synthesis.py` — same test structure, same mocking approach
- **IMPLEMENT**:
  - `test_scorer_returns_concept_scoring_on_success` — mock parse, verify all three axes returned with score and reasoning
  - `test_scorer_raises_on_refusal` — mock parse with refusal, verify `EvaluationError`
  - `test_scorer_raises_on_api_connection_error` — mock `APIConnectionError`, verify `EvaluationError`
  - `test_scorer_builds_messages_with_system_and_user` — verify message structure (2 messages, system + user, concept data in user message)
  - `test_scoring_prompt_contains_evaluation_instructions` — verify `SCORING_PROMPT` contains axis names and scoring instructions
  - `test_scorer_scores_are_within_range` — verify returned scores are 0.0-10.0 (test against the fixture data)
- **PATTERN**: Mock `scorer._client.beta.chat.completions` parse method using `patch.object`
- **VALIDATE**: `uv run pytest tests/test_scoring.py -v`

### Task 9: Write database and API tests for scores

Test the score query layer and API endpoints.

- **UPDATE**: `tests/test_db.py` — add score query tests
- **UPDATE**: `tests/test_api.py` — add score endpoint tests
- **IMPLEMENT** (test_db.py):
  - `test_create_score` — create a run, create a concept, create a score linked to concept, verify all fields
  - `test_get_score_by_concept_id` — create score, fetch by concept_id, verify match
  - `test_get_score_by_concept_id_returns_none_for_missing` — verify `None` for nonexistent concept_id
- **IMPLEMENT** (test_api.py):
  - `test_get_concept_scores` — seed run + concept + score, verify `GET /api/concepts/{id}/scores` returns score data
  - `test_list_scores` — seed data, verify `GET /api/scores` returns list
- **PATTERN**: Follow existing test patterns in both files — use `db` fixture, create prerequisite records, assert on response
- **IMPORTS** (test_db.py): Add `ScoreCreate`, `create_score`, `get_score_by_concept_id`, `get_scores` from `src.db.queries`
- **IMPORTS** (test_api.py): Add `ScoreCreate`, `create_score` from `src.db.queries`
- **VALIDATE**: `uv run pytest tests/test_db.py tests/test_api.py -v`

### Task 10: Add scoring boundary tests

Verify the scoring module respects architectural boundaries.

- **UPDATE**: `tests/test_boundaries.py`
- **PATTERN**: Follow synthesis boundary tests (lines 83-128)
- **IMPLEMENT**:
  - `test_scoring_uses_remote_openai_api` — verify scoring source references `openai_api_key`
  - `test_scoring_does_not_use_vllm` — verify scoring source does NOT reference `vllm_base_url`
  - `test_scoring_does_not_import_engine` — verify no `from src.engine` or `import src.engine` in scoring source
  - `test_scoring_does_not_import_synthesis` — verify no `from src.synthesis` or `import src.synthesis` in scoring source (scoring sits above synthesis in the hierarchy, so it should not import from it — it receives data, not modules)
- **VALIDATE**: `uv run pytest tests/test_boundaries.py -v`

### Task 11: Full validation pass

Run the complete test suite and linting to ensure zero regressions.

- **VALIDATE**: `uv run ruff check . && uv run ruff format --check . && uv run pytest -v`

---

## TESTING STRATEGY

### Unit Tests

- **Scorer tests** (`tests/test_scoring.py`): Mock all OpenAI API calls. Test success path, refusal handling, connection errors, message structure, prompt content.
- **DB query tests** (`tests/test_db.py`): Use in-memory SQLite. Test score CRUD, concept-score linking, missing concept handling.
- **API tests** (`tests/test_api.py`): Use httpx AsyncClient with FastAPI test app. Test score endpoints with seeded data.

### Edge Cases

- Model refuses to score (refusal response) — verify `EvaluationError`
- API connection failure — verify `EvaluationError` with descriptive message
- API timeout — verify `EvaluationError`
- Scoring a concept that already has scores — depends on UNIQUE constraint behavior
- Missing `OPENAI_API_KEY` — CLI skips scoring with warning (like synthesis)

---

## VALIDATION CHECKPOINT

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest -v
```

**Expected**: All tests pass, zero regressions, zero linting errors.

---

## ACCEPTANCE CRITERIA (Milestone 4)

- [ ] `tests/conftest.py` has `mock_scoring_response` and `test_concept_scoring` fixtures
- [ ] `tests/test_scoring.py` covers success, refusal, connection error, message structure, prompt content
- [ ] `tests/test_db.py` covers score CRUD operations
- [ ] `tests/test_api.py` covers score API endpoints
- [ ] `tests/test_boundaries.py` verifies scoring uses remote API, no vLLM, no engine/synthesis imports
- [ ] All OpenAI calls mocked in tests — no real inference
- [ ] Full test suite passes with zero regressions
- [ ] Ruff check and format pass with zero errors
- [ ] All code follows project conventions (docstrings, type hints, logging, error handling)

---

## COMPLETION CHECKLIST (Full Feature 4)

- [ ] All tasks (1–11) completed in order
- [ ] Each milestone validation checkpoint passed
- [ ] All validation commands executed:
  - [ ] Level 1: `uv run ruff check .` and `uv run ruff format --check .`
  - [ ] Level 2: `uv run pytest tests/test_scoring.py tests/test_db.py tests/test_api.py tests/test_boundaries.py -v`
  - [ ] Level 3: `uv run pytest -v`
  - [ ] Level 4: `uv run python scripts/run_conversation.py --help` (manual)
- [ ] No linting errors
- [ ] No formatting errors
- [ ] All acceptance criteria from parent plan met
