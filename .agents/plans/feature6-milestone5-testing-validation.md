# Feature 6 — Milestone 5: Testing & Validation

**Tasks:** 13–17
**Goal:** All test files updated, full suite passes, lint/format clean
**Validation checkpoint:** `uv run pytest -v` all green, `uv run ruff check .` zero errors
**Depends on:** All previous milestones (1–4)

---

## Prerequisites

Read the parent plan for full context: [feature6-domain-expansion.md](feature6-domain-expansion.md)

### Relevant Codebase Files — MUST READ BEFORE IMPLEMENTING

- `tests/conftest.py` (full file) — Why: Fixtures hardcode sci-fi-specific test data and removed models
- `tests/test_synthesis.py` (full file) — Why: Tests assert sci-fi-specific fields and use removed ConceptExtraction
- `tests/test_scoring.py` (full file) — Why: Tests assert 3 specific axis names and use removed ConceptScoring
- `tests/test_db.py` (full file) — Why: Tests use hardcoded score field names
- `tests/test_ui.py` (full file) — Why: Tests check hardcoded HTML content
- `tests/test_batch.py` (full file) — Why: Tests use hardcoded score field names
- `tests/test_boundaries.py` (full file) — Why: Must add domain boundary test
- `tests/test_config.py` (full file) — Why: Must add active_domain test

### New Files to Create

- `tests/test_domains.py` — Tests for domain config loading and validation

---

## IMPLEMENTATION TASKS

### Task 13: Update Tests — Conftest and Domain Fixtures

Update shared test fixtures for domain-aware testing.

- **UPDATE** `tests/conftest.py`:
  - Remove `test_concept_extraction` fixture (ConceptExtraction model is removed)
  - Add `test_extraction_result` fixture returning a `dict[str, str]`: `{"title": "The Architecture of Forgetting", "premise": "...", "originality": "..."}`
  - Remove `test_concept_scoring` fixture (ConceptScoring model is removed)
  - Add `test_scoring_result` fixture returning `list[AxisScoreRecord]` with 3 axes matching sci-fi domain:
    ```python
    [
        AxisScoreRecord(axis="uniqueness", label="Uniqueness", score=8.5, reasoning="..."),
        AxisScoreRecord(axis="plausibility", label="Scientific Plausibility", score=6.0, reasoning="..."),
        AxisScoreRecord(axis="compelling_factor", label="Compelling Factor", score=7.5, reasoning="..."),
    ]
    ```
  - Update `mock_parse_response` to work with dynamic models (return a mock whose `.parsed` is a dynamically created model instance built from `create_extraction_model()`)
  - Add `mock_scoring_parse_response` similarly for scoring dynamic models
  - Add `test_domain` fixture that returns the sci-fi domain config: `from src.domains.sci_fi_concepts import SCI_FI_CONCEPTS`
  - Remove imports of `ConceptExtraction` and `ConceptScoring`
  - Add import of `AxisScoreRecord` from `src/db/queries`

- **CREATE** `tests/test_domains.py`:
  - `test_sci_fi_domain_has_required_fields()` — validate sci-fi config has 3 extraction fields and 3 scoring axes
  - `test_product_design_domain_has_required_fields()` — validate product design config has 3 extraction fields and 3 scoring axes
  - `test_domain_registry_returns_all_domains()` — at least 2 domains registered
  - `test_get_domain_raises_for_unknown()` — `ValueError` for "nonexistent"
  - `test_create_extraction_model_produces_valid_schema()` — model has all fields from config, all required
  - `test_create_scoring_model_produces_valid_schema()` — model has AxisScore fields per axis
  - `test_domain_config_validates_primary_field()` — primary_field must be in extraction_fields, raises ValidationError otherwise
  - `test_domain_config_requires_at_least_one_field()` — empty extraction_fields raises ValidationError

- **VALIDATE**: `uv run pytest tests/test_domains.py -v`

### Task 14: Update Tests — Synthesis and Scoring

Adapt synthesis and scoring tests for domain-aware APIs.

- **UPDATE** `tests/test_synthesis.py`:
  - Import sci-fi domain config: `from src.domains.sci_fi_concepts import SCI_FI_CONCEPTS`
  - Import `create_extraction_model` from `src.domains.models`
  - Update `test_synthesizer_extracts_concept_from_transcript()`:
    - Create `Synthesizer(SCI_FI_CONCEPTS)` instead of `Synthesizer()`
    - Build dynamic model: `ExtractionModel = create_extraction_model(SCI_FI_CONCEPTS)`
    - Mock `.parse()` to return a mock whose `.parsed` is `ExtractionModel(title="...", premise="...", originality="...")`
    - Assert result is a dict with expected keys (`"title"`, `"premise"`, `"originality"`)
  - Update refusal and error tests: pass domain to Synthesizer
  - Update `test_synthesis_prompt_contains_extraction_instructions()` — check `SCI_FI_CONCEPTS.synthesis_prompt` content instead of module-level constant
  - Update `test_synthesizer_builds_messages_with_system_and_user()` — system message comes from domain config

- **UPDATE** `tests/test_scoring.py`:
  - Import sci-fi domain config and `create_scoring_model`
  - Create `Scorer(SCI_FI_CONCEPTS)` in all tests
  - Update `test_scorer_returns_concept_scoring_on_success()`:
    - Build dynamic model: `ScoringModel = create_scoring_model(SCI_FI_CONCEPTS)`
    - Mock `.parse()` to return instance with AxisScore fields
    - Assert result is a `list[AxisScoreRecord]` with 3 entries
  - Update `score()` calls: pass `fields={"title": "...", "premise": "...", "originality": "..."}` instead of positional args
  - Update refusal and error tests: pass domain to Scorer, pass fields dict
  - Update `test_scoring_prompt_contains_evaluation_instructions()` — check `SCI_FI_CONCEPTS.scoring_prompt` content
  - Update score range test to iterate over result list

- **VALIDATE**: `uv run pytest tests/test_synthesis.py tests/test_scoring.py -v`

### Task 15: Update Tests — Database and Queries

Adapt DB tests for new schema.

- **UPDATE** `tests/test_db.py`:
  - Import `AxisScoreRecord` from `src/db/queries`
  - Update `test_create_concept()` — use new `ConceptCreate` with `domain="sci-fi-concepts"`, `title="The Architecture of Forgetting"`, `fields={"title": "...", "premise": "...", "originality": "..."}`
  - Update `test_create_score()` — use new `ScoreCreate` with `axes=[AxisScoreRecord(...), ...]`
  - Assert `score.axes` is a list with expected length and values
  - Assert `score.overall_score` is computed correctly
  - Update `test_get_concepts_with_scores()` — check `overall_score` field from the join
  - Update `test_get_score_by_concept_id()` — check `axes` list
  - Update `_create_test_concept()` helper to use new model shapes
  - Update all concept creation calls throughout the file
  - Update all score creation calls throughout the file

- **VALIDATE**: `uv run pytest tests/test_db.py -v`

### Task 16: Update Tests — Batch, UI, Boundaries, and Remaining

Adapt remaining test files.

- **UPDATE** `tests/test_batch.py`:
  - Mock `get_active_domain` to return sci-fi domain config in all batch tests (or use a fixture)
  - Patch `src.batch.runner.get_active_domain` to return `SCI_FI_CONCEPTS`
  - Update `mock_synthesizer` fixture: mock return value should be a dict instead of ConceptExtraction
  - Update `mock_scorer` fixture: mock return value should be a list of AxisScoreRecord
  - Update concept assertions to use `fields` dict pattern (e.g., `concepts[0].fields["title"]`)
  - Update score assertions to use `axes` list pattern

- **UPDATE** `tests/test_ui.py`:
  - Update `_seed_review_data()`:
    - Use new `ConceptCreate` with `domain`, `title`, `fields` dict
    - Use new `ScoreCreate` with `axes` list of `AxisScoreRecord`
  - Mock `get_active_domain` where templates need domain context (patch `src.ui.routes.get_active_domain`)
  - Update assertions that check for specific score values in HTML — scores are now rendered in a loop, but the actual numbers should still appear
  - Update assertions for concept fields — "premise" and "originality" labels come from domain config

- **UPDATE** `tests/test_boundaries.py`:
  - Add `test_domains_has_no_llm_imports()`:
    ```python
    def test_domains_has_no_llm_imports() -> None:
        """Verify the domains module makes no LLM calls."""
        domains_dir = Path("src/domains")
        if not domains_dir.exists():
            return
        imports = _get_all_imports_in_dir(domains_dir)
        assert "openai" not in imports, (
            "src/domains/ must not import openai — it is pure configuration"
        )
    ```
  - Existing boundary tests should still pass (synthesis/scoring still use openai_api_key, still don't use vllm_base_url)

- **UPDATE** `tests/test_config.py` — Add test for `active_domain` setting:
  ```python
  def test_active_domain_default():
      """Verify the active_domain setting defaults to sci-fi-concepts."""
      assert settings.active_domain == "sci-fi-concepts"
  ```

- **VALIDATE**: `uv run pytest -v`

### Task 17: Full Validation and Cleanup

Run the complete validation suite and clean up any dead code.

- **VALIDATE**: `uv run ruff check .`
- **VALIDATE**: `uv run ruff format --check .`
- **VALIDATE**: `uv run pytest -v`
- **REMOVE** any dead code:
  - Old `SYNTHESIS_PROMPT` constant in `src/synthesis/synthesizer.py` if still present
  - Old `SCORING_PROMPT` constant in `src/scoring/scorer.py` if still present
  - Old `ConceptExtraction` in `src/synthesis/models.py` if still present
  - Old `ConceptScoring` in `src/scoring/models.py` if still present
  - Any unused imports across the codebase
- **VERIFY**: Run `uv run python -c "from src.domains.registry import get_all_domains; [print(f'{d.name}: {len(d.extraction_fields)} fields, {len(d.scoring_axes)} axes') for d in get_all_domains()]"` to confirm both domains load

---

## TESTING STRATEGY SUMMARY

### Unit Tests
- **Domain config tests** (`test_domains.py`): Validate domain models, registry, dynamic model creation, field validation
- **Synthesis tests** (`test_synthesis.py`): Mock OpenAI API, verify dynamic model is passed as response_format, verify extraction returns dict
- **Scoring tests** (`test_scoring.py`): Mock OpenAI API, verify dynamic model, verify list of AxisScoreRecord returned
- **DB tests** (`test_db.py`): Verify JSON storage/retrieval roundtrips, overall score computation, concept-with-score join

### Integration Tests
- **Batch tests** (`test_batch.py`): Full pipeline with mocked LLM calls, verify domain flows through to DB records
- **UI tests** (`test_ui.py`): Verify templates render dynamically based on domain config
- **Boundary tests** (`test_boundaries.py`): Verify `src/domains/` has no LLM imports

### Edge Cases to Cover
- Domain with 1 extraction field (minimum)
- Domain with 5+ scoring axes
- Concept created with one domain, viewed when active domain has changed (should still render from stored data)
- Score with 0.0 values
- Missing score (concept without scores)

---

## MILESTONE VALIDATION

```bash
# Full test suite
uv run pytest -v

# Lint and format
uv run ruff check .
uv run ruff format --check .

# Both domains load correctly
uv run python -c "from src.domains.registry import get_all_domains; [print(f'{d.name}: {len(d.extraction_fields)} fields, {len(d.scoring_axes)} axes') for d in get_all_domains()]"

# Dynamic models work
uv run python -c "from src.domains.models import create_extraction_model, create_scoring_model; from src.domains.registry import get_domain; d = get_domain('sci-fi-concepts'); print(create_extraction_model(d).model_json_schema()); print(create_scoring_model(d).model_json_schema())"

# CLI works
uv run python scripts/run_conversation.py --list-domains
```

All commands must pass with zero errors.
