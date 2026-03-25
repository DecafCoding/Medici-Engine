# Feature 7: Feedback Loop

## Feature Description

Build a lightweight mechanism for human review decisions (kept/discarded) to inform future runs. The system surfaces analytics on which persona pairings produce the highest-rated output and which shared objects seed the most generative conversations. This is not an ML feedback system — it is a structured analytics layer that a human can review to manually tune persona selection and conversation seeding, plus an optional auto-informed persona selection mode.

## User Story

As a Medici Engine operator
I want to see which persona pairings and shared objects produce the best-rated concepts
So that I can make better-informed choices when configuring future batch runs

## Problem Statement

After running the system enough times, there is no structured way to answer: "which persona pairings are most generative?" or "which shared objects produce the best concepts?" The human reviewer keeps/discards concepts, and the scorer rates them, but this data is never aggregated or surfaced. Persona selection remains random or manual without learning from past outcomes.

## Solution Statement

Add three capabilities:

1. **Analytics queries** — New database queries that aggregate review outcomes and scores by persona pairing and by shared object. These answer the core questions about what works.

2. **Insights UI page** — A new `/ui/insights` page that displays pairing performance and shared object performance tables, giving the operator a data-driven view of which configurations produce the best results.

3. **Informed persona selection** — An optional "smart" selection mode in `get_persona_pair` that weights pairings by historical performance, plus a batch setup option to use informed selection instead of random.

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium
**Primary Systems Affected**: `src/db/queries.py`, `src/personas/library.py`, `src/ui/routes.py`, `src/batch/runner.py`, templates
**Dependencies**: No new external libraries required

---

## EXECUTION STRATEGY

**Recommended approach**: Milestones

**Rationale**: Feature has 12 tasks across 4 natural phases: data layer, UI layer, integration layer, and final validation. Each phase builds on the previous and has a clean validation checkpoint. Task count (12) is too many for single-pass, but tasks within each phase are tightly coupled and should be done together.

### Milestones

**Milestone 1: Analytics Data Layer** (Tasks 1–4) — [`feature7-milestone1-analytics-data-layer.md`](feature7-milestone1-analytics-data-layer.md)
- Add analytics Pydantic models, pairing performance query, shared object performance query, and their tests
- **Validation checkpoint**: `uv run pytest tests/test_insights.py tests/test_db.py -v` passes

**Milestone 2: Insights UI** (Tasks 5–7) — [`feature7-milestone2-insights-ui.md`](feature7-milestone2-insights-ui.md)
- Add insights route, templates, fragments, and nav link
- **Validation checkpoint**: `uv run pytest tests/test_ui.py -v` passes, `/ui/insights` renders

**Milestone 3: Informed Selection** (Tasks 8–11) — [`feature7-milestone3-informed-selection.md`](feature7-milestone3-informed-selection.md)
- Add informed persona selection function, pairing scores query, batch runner integration, UI checkbox, and all tests
- **Validation checkpoint**: `uv run pytest tests/ -v` — full suite passes

**Milestone 4: Testing & Validation** (Task 12) — [`feature7-milestone4-testing-validation.md`](feature7-milestone4-testing-validation.md)
- Full lint, format, and test pass. Manual validation of all UI flows.
- **Validation checkpoint**: All validation commands at all levels pass. No regressions.

---

## KEY DESIGN DECISIONS

### No New Database Tables

The existing schema already contains all necessary data. Runs have persona names and shared object text. Concepts have run_id, domain, and status. Scores have concept_id and overall_score. The analytics queries join these existing tables — no migrations needed.

### Pure Selection Function

`get_informed_persona_pair` takes pre-computed scores as a dict input rather than accessing the database directly. This keeps the personas module pure (no DB imports, no LLM calls — per CLAUDE.md architectural boundaries) and makes it independently testable.

### Exploration Rate

A fixed exploration rate (default 20%) ensures the system continues discovering new pairings rather than converging entirely on historically high-scoring ones. This matches the project philosophy that "variance is a feature" and prevents the feedback loop from becoming too conservative.

### Optional, Not Default

Informed selection is opt-in via a checkbox/flag, not the default behavior. This preserves the existing random selection for users who prefer maximum variance, and avoids changing behavior for existing workflows.

### Persona Order Normalization

The `runs` table stores personas in assignment order (A speaks first), not sorted order. The `pairing_history` table stores sorted order. Analytics queries must normalize using `MIN/MAX` on persona names to treat (A,B) and (B,A) as the same pairing. This is critical for correct aggregation.

---

## ACCEPTANCE CRITERIA

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
