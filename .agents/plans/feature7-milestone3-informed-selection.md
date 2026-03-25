# Feature 7 — Milestone 3: Informed Selection

**Parent plan**: `feature7-feedback-loop.md`
**Depends on**: Milestone 1 (analytics queries for pairing scores)
**Tasks**: 8–11
**Goal**: Add performance-weighted persona selection, batch runner integration, UI checkbox, and all tests for the informed selection path.

The following plan should be complete, but validate documentation and codebase patterns before implementing.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — READ BEFORE IMPLEMENTING

- `src/personas/library.py` (lines 853-906) — Why: `get_persona_pair()` is the function to mirror for `get_informed_persona_pair`. Same structure, different selection logic.
- `src/batch/runner.py` (lines 89-99, 189-213) — Why: Where persona selection happens per-conversation — `_select_personas` needs a new code path for informed selection.
- `src/batch/models.py` (full file) — Why: `BatchRequest` needs a new field for selection strategy.
- `src/db/queries.py` — Why: Add `get_pairing_scores()` query for the batch runner to call.
- `src/ui/routes.py` (lines 57-114) — Why: `launch_batch` form parsing — need to add `use_informed_selection` checkbox.
- `src/templates/batch.html` (full file) — Why: Add the informed selection checkbox to the form.
- `tests/test_batch.py` (full file) — Why: Pattern for batch runner tests with mocked LLM calls and settings.
- `tests/test_personas.py` — Why: Pattern for persona library tests.
- `tests/conftest.py` (full file) — Why: Shared fixtures.

### Patterns to Follow

**Persona Selection Pattern** (from `src/personas/library.py:853-906`):
```python
def get_persona_pair(
    recent_pairings: list[tuple[str, str]] | None = None,
) -> tuple[Persona, Persona]:
    """Select two personas for a conversation run."""
    # Build all pairs, filter recent, pick one, randomize order
```

**BatchRequest Field Pattern** (from `src/batch/models.py`):
```python
field_name: type = Field(
    default=default_value,
    description="Description of the field",
)
```

**Batch Runner Mock Pattern** (from `tests/test_batch.py`):
```python
with patch("src.batch.runner.get_persona_pair") as mock_pair:
    mock_pair.return_value = (PERSONAS[0], PERSONAS[1])
    runner = BatchRunner(db)
    await runner.run_batch(request, batch_id)
    mock_pair.assert_called_once()
```

---

## IMPLEMENTATION TASKS

### Task 8: Informed Persona Selection

Add a performance-weighted selection mode to the persona library.

- **ADD** to `src/personas/library.py`:
  - New function `get_informed_persona_pair(pairing_scores: dict[tuple[str, str], float], recent_pairings: list[tuple[str, str]] | None = None, exploration_rate: float = 0.2) -> tuple[Persona, Persona]`
    - `pairing_scores`: dict mapping sorted (name_a, name_b) tuples to average scores
    - Builds all possible pairings (same as `get_persona_pair`)
    - Filters out recent pairings (same as `get_persona_pair`)
    - With probability `exploration_rate`, picks a random pairing (exploration)
    - Otherwise, selects from available pairings weighted by score (exploitation)
      - Use `random.choices(population, weights=scores)` for weighted selection
      - Pairings with no score data get a neutral weight (median of known scores, or 5.0 if none)
    - Randomizes which persona goes first (same as `get_persona_pair`)
    - Returns the pair
  - This function is pure — it takes pre-computed scores as input, no DB access
- **PATTERN**: Mirror `get_persona_pair` at `src/personas/library.py:853-906`
- **GOTCHA**: `random.choices` with weights requires all weights > 0. Ensure minimum weight of 0.1.
- **GOTCHA**: If all pairings are in recent_pairings and function falls back to full library, the same weighted selection logic should still apply.
- **VALIDATE**: `uv run ruff check src/personas/library.py`

### Task 9: Analytics Query for Batch Runner

Add a lightweight query that returns pairing scores as a dict for use by the informed selection.

- **ADD** to `src/db/queries.py` in the analytics section:
  - `get_pairing_scores(db, domain: str | None = None) -> dict[tuple[str, str], float]`
    - Simpler version of `get_pairing_performance` — just returns `{(name_a, name_b): avg_score}` dict
    - Only includes pairings that have at least one scored concept
    - Names are sorted (consistent with `record_pairing`)
    - Used by BatchRunner to pass into `get_informed_persona_pair`
- **PATTERN**: Similar SQL to `get_pairing_performance` but simpler — just the average
- **VALIDATE**: `uv run ruff check src/db/queries.py`

### Task 10: Batch Runner Integration

Add informed selection as an option in the batch runner and batch request.

- **UPDATE** `src/batch/models.py`:
  - Add field `use_informed_selection: bool = Field(default=False, description="Use performance-weighted persona selection instead of random")`
- **UPDATE** `src/batch/runner.py`:
  - Import `get_informed_persona_pair` from `src.personas.library`
  - Import `get_pairing_scores` from `src.db.queries`
  - In `_select_personas`: when `request.persona_pairs is None` and `request.use_informed_selection is True`:
    - Call `get_pairing_scores(self._db, domain.name)` to get historical scores
    - Call `get_informed_persona_pair(scores, recent_pairings)` instead of `get_persona_pair(recent_pairings)`
  - Pass `domain` to `_select_personas` (currently not passed — add it as parameter)
  - Update the call site in `run_batch` to pass `domain` to `_select_personas`
- **UPDATE** `src/ui/routes.py`:
  - In `launch_batch`: parse `use_informed_selection` from form checkbox
    - HTML checkboxes send the value only when checked, so: `use_informed_selection = bool(form.get("use_informed_selection", ""))`
  - Pass it through to `BatchRequest`
- **UPDATE** `src/templates/batch.html`:
  - Add checkbox in Run Configuration fieldset (after the num_conversations input):
    ```html
    <label>
        <input type="checkbox" name="use_informed_selection" id="use_informed_selection" value="1">
        Use performance-informed persona selection
    </label>
    ```
- **PATTERN**: Follow existing `BatchRequest` field patterns and form parsing in `launch_batch`
- **GOTCHA**: `_select_personas` currently doesn't receive the domain or request's `use_informed_selection`. Need to thread both through. Simplest: pass the full `request` and `domain` to `_select_personas`.
- **GOTCHA**: HTML checkbox sends nothing when unchecked — `form.get("use_informed_selection")` returns `None`, not `False`. Use truthiness check.
- **VALIDATE**: `uv run ruff check src/batch/ src/ui/routes.py`

### Task 11: Informed Selection Tests

Add tests for the informed persona selection and batch runner integration.

- **ADD** to `tests/test_personas.py` (pure selection logic tests):
  - `test_informed_selection_with_no_scores_falls_back_to_random` — empty dict = equivalent to random, just verify it returns a valid pair
  - `test_informed_selection_favors_high_scoring_pairings` — create scores dict with one pairing scored 9.0 and others at 1.0, run 100 times, verify high-scoring pairing selected significantly more often (e.g., > 40% of the time)
  - `test_informed_selection_respects_exploration_rate` — with `exploration_rate=1.0`, distribution should be roughly uniform
  - `test_informed_selection_avoids_recent_pairings` — recent pairings excluded from selection
  - `test_informed_selection_handles_all_recent` — falls back to full library when all pairings are recent
- **ADD** to `tests/test_insights.py` (query tests):
  - `test_get_pairing_scores_returns_dict` — verify dict format with seeded data
  - `test_get_pairing_scores_empty_db` — returns empty dict
- **ADD** to `tests/test_batch.py`:
  - `test_batch_with_informed_selection` — mock `get_informed_persona_pair` and `get_pairing_scores`, set `use_informed_selection=True` on BatchRequest, verify `get_informed_persona_pair` is called instead of `get_persona_pair`
- **ADD** to `tests/test_ui.py`:
  - `test_batch_form_with_informed_selection` — POST to `/ui/batch` with `use_informed_selection=1`, verify it's parsed and passed to BatchRunner
  - `test_insights_page_renders_empty` — GET `/ui/insights`, verify 200 status and empty state text
  - `test_insights_page_renders_with_data` — seed data, GET `/ui/insights`, verify pairing and shared object data appears
  - `test_insights_pairing_rows_fragment` — GET `/ui/insights/pairings`, verify fragment without full layout
  - `test_insights_shared_object_rows_fragment` — GET `/ui/insights/shared-objects`, verify fragment
- **PATTERN**: Follow `tests/test_batch.py` mock patterns
- **VALIDATE**: `uv run pytest tests/ -v --tb=short`

---

## VALIDATION CHECKPOINT

```bash
# Must all pass before moving to Milestone 4
uv run ruff check .
uv run ruff format --check .
uv run pytest tests/ -v --tb=short
```

**Done when**: Full test suite passes including all new informed selection, batch, UI, and query tests. Informed selection is available via batch setup checkbox.

---

## ACCEPTANCE CRITERIA (Milestone 3)

- [ ] `get_informed_persona_pair()` weights selection by historical score data
- [ ] Informed selection has configurable exploration rate (default 20%)
- [ ] Pairings with no score data get a neutral weight (not excluded)
- [ ] Informed selection avoids recent pairings (same as random selection)
- [ ] `get_pairing_scores()` returns correct dict of pairing → avg_score
- [ ] Batch setup UI has checkbox for informed persona selection
- [ ] BatchRunner uses informed selection when flag is set
- [ ] BatchRunner uses random selection when flag is not set (default behavior unchanged)
- [ ] All new tests pass
- [ ] No regressions in existing tests

---

## NOTES

### Design Decision: Pure Selection Function

`get_informed_persona_pair` takes pre-computed scores as a dict input rather than accessing the database directly. This keeps the personas module pure (no DB imports, no LLM calls — per CLAUDE.md architectural boundaries) and makes it independently testable.

### Design Decision: Exploration Rate

A fixed exploration rate (default 20%) ensures the system continues discovering new pairings rather than converging entirely on historically high-scoring ones. This matches the project philosophy that "variance is a feature" and prevents the feedback loop from becoming too conservative.

### Design Decision: Optional, Not Default

Informed selection is opt-in via a checkbox/flag, not the default behavior. This preserves the existing random selection for users who prefer maximum variance, and avoids changing behavior for existing workflows.
