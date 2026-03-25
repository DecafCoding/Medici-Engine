# Feature 7 — Milestone 4: Testing & Validation

**Parent plan**: `feature7-feedback-loop.md`
**Depends on**: Milestones 1–3 (all implementation complete)
**Tasks**: 12
**Goal**: Full lint, format, and test pass. Manual validation of all UI flows. Verify no regressions.

---

## IMPLEMENTATION TASKS

### Task 12: Full Validation

Run the complete validation suite to ensure no regressions and full CLAUDE.md compliance.

- **VALIDATE**: `uv run ruff check .`
- **VALIDATE**: `uv run ruff format --check .`
- **VALIDATE**: `uv run pytest tests/ -v --tb=short`
- Review all new and modified files for CLAUDE.md compliance:
  - Every new Python file has a module-level docstring
  - Every new class has a class-level docstring
  - Every new function/method has a docstring
  - All function signatures have type hints (parameters and return types)
  - Logging uses `logging` module, not `print()`
  - No raw SQL outside `src/db/queries.py`
  - No imports crossing architectural boundaries
  - Async patterns followed (no sync blocking calls)

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

```bash
# Lint (must pass with 0 errors)
uv run ruff check .

# Format check
uv run ruff format --check .
```

**Expected**: All commands pass with exit code 0

### Level 2: Unit Tests

```bash
# Run all tests
uv run pytest tests/ -v --tb=short

# Run just the new analytics tests
uv run pytest tests/test_insights.py -v --tb=short

# Run just DB tests (includes analytics queries)
uv run pytest tests/test_db.py -v --tb=short
```

### Level 3: Integration Tests

```bash
# UI tests including insights page
uv run pytest tests/test_ui.py -v --tb=short

# Batch tests including informed selection
uv run pytest tests/test_batch.py -v --tb=short

# Persona tests including informed selection
uv run pytest tests/test_personas.py -v --tb=short
```

### Level 4: Manual Validation

1. Start server: `uv run uvicorn src.main:app --reload`
2. Navigate to `/ui/insights` — should show empty state message ("Not enough data yet...")
3. Navigate to `/ui/batch` — should show informed selection checkbox
4. Verify nav bar shows Review | Batch Setup | Insights on all pages
5. (If test data available) Seed some data, review concepts, then verify insights tables populate

---

## FINAL ACCEPTANCE CRITERIA

- [ ] `get_pairing_performance()` returns correct aggregation of persona pair outcomes
- [ ] `get_shared_object_performance()` returns correct aggregation of shared object outcomes
- [ ] Persona pairs (A,B) and (B,A) are treated as the same pairing in analytics
- [ ] `/ui/insights` page renders with pairing and shared object performance tables
- [ ] Domain filter on insights page works via HTMX
- [ ] Navigation bar includes Insights link on all pages
- [ ] `get_informed_persona_pair()` weights selection by historical score data
- [ ] Informed selection has configurable exploration rate for discovering new pairings
- [ ] Batch setup UI has checkbox for informed persona selection
- [ ] BatchRunner uses informed selection when flag is set
- [ ] All analytics queries handle empty database gracefully (no errors, empty results)
- [ ] All validation commands pass with zero errors
- [ ] No regressions in existing 111 tests
- [ ] Code follows project conventions: docstrings, type hints, logging, async patterns

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order (Tasks 1–12 across Milestones 1–4)
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully:
  - [ ] Level 1: ruff check, ruff format --check
  - [ ] Level 2: pytest (unit tests)
  - [ ] Level 3: pytest (integration tests)
  - [ ] Level 4: Manual validation
- [ ] Full test suite passes (unit + integration)
- [ ] No linting errors (`uv run ruff check .`)
- [ ] No formatting errors (`uv run ruff format --check .`)
- [ ] All acceptance criteria met
- [ ] Code reviewed for quality and maintainability
