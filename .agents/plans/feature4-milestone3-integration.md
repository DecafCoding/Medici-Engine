# Feature 4 — Milestone 3: Integration

**Parent plan**: `feature4-scoring-layer.md`
**Tasks**: 5–6
**Goal**: Wire scoring into API endpoints and CLI runner

---

## Feature Context

Add a scoring layer that evaluates concepts extracted by the synthesizer. Scores and reasoning are persisted in the database and exposed via API endpoints. The CLI runner is updated to invoke scoring after synthesis.

## User Story

As a human reviewer of Medici Engine output
I want each concept scored across multiple axes with written reasoning
So that I can make faster, better-informed keep/discard decisions without reading the full transcript

---

## CONTEXT REFERENCES

### Relevant Codebase Files — READ BEFORE IMPLEMENTING

- `src/api/routes.py` (full file) — Why: New score endpoints follow the same pattern — router prefix, `request.app.state.db` access, typed return values.
- `scripts/run_conversation.py` (lines 108-170) — Why: The `_run_synthesis` function is the pattern for `_run_scoring` — same try/except structure, same graceful failure with retry instructions.
- `src/db/queries.py` — Why: Import the new score query functions (`get_score_by_concept_id`, `get_scores`, `create_score`, `ScoreCreate`).
- `src/scoring/scorer.py` (created in Milestone 2) — Why: Import `Scorer` and `ScoringError`.
- `CLAUDE.md` — Why: Architectural boundaries, documentation requirements.

### Files to Modify

- `src/api/routes.py` — Add score-related API endpoints
- `scripts/run_conversation.py` — Add `_run_scoring` step after synthesis

### Patterns to Follow

**API Endpoint Pattern** (from `src/api/routes.py`):
```python
@router.get("/concepts/{concept_id}")
async def get_concept(request: Request, concept_id: UUID) -> queries.Concept | None:
    """Fetch a single concept by ID."""
    db = request.app.state.db
    return await queries.get_concept_by_id(db, concept_id)
```

**CLI Integration Pattern** (from `scripts/run_conversation.py` `_run_synthesis`):
```python
async def _run_scoring(db, concept_id, title, premise, originality) -> None:
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not set — skipping scoring")
        print("\n⚠ Scoring skipped: OPENAI_API_KEY not configured")
        return
    # ... try/except ScoringError ...
```

---

## IMPLEMENTATION PLAN

### Task 5: Add score API endpoints

Expose scores through the REST API.

- **UPDATE**: `src/api/routes.py`
- **PATTERN**: Follow existing concept endpoints pattern (lines 49-68)
- **IMPLEMENT**:
  - `GET /api/concepts/{concept_id}/scores` — fetch scores for a concept (returns `queries.Score | None`)
  - `GET /api/scores` — list recent scores (returns `list[queries.Score]`)
- **IMPORTS**: Add `get_score_by_concept_id`, `get_scores` from `src.db.queries`
- **VALIDATE**: `uv run ruff check src/api/`

### Task 6: Integrate scoring into CLI runner

Add scoring as a step after synthesis in the CLI pipeline.

- **UPDATE**: `scripts/run_conversation.py`
- **MIRROR**: The `_run_synthesis` function (lines 108-170) — same structure for `_run_scoring`
- **IMPLEMENT**:
  - `_run_scoring(db, concept_id, title, premise, originality) -> None`: async function
    - Check `settings.openai_api_key` — skip if not set (same as synthesis)
    - Create `Scorer`, call `scorer.score(title, premise, originality)`
    - Persist via `create_score(db, ScoreCreate(...))`
    - Print scores and reasoning to console
    - On `ScoringError`: log, print warning, do not raise (scoring can be retried)
  - Call `_run_scoring` after synthesis succeeds (inside the existing `_run_synthesis` function's success path, or as a separate call after `_run_synthesis` returns)
  - Add `--no-scoring` CLI flag (similar to `--no-synthesis`)
  - Add `--score-only <concept-id>` flag for re-scoring existing concepts
- **IMPORTS**: Add `Scorer`, `ScoringError` from `src.scoring.scorer`; `ScoreCreate`, `create_score`, `get_concept_by_id` from `src.db.queries`
- **GOTCHA**: Scoring depends on synthesis output. If synthesis fails, scoring should not run. Handle the dependency in the flow: synthesis returns the concept, then scoring receives it. The `_run_synthesis` function currently returns `None` — consider having it return the created `Concept` so `_run_scoring` can receive it, or call `_run_scoring` separately after synthesis with the concept data.
- **VALIDATE**: `uv run ruff check scripts/ && uv run python scripts/run_conversation.py --help`

---

## VALIDATION CHECKPOINT

```bash
uv run ruff check . && uv run ruff format --check . && uv run python scripts/run_conversation.py --help
```

**Expected**: Linting passes, CLI help shows `--no-scoring` and `--score-only` flags.

---

## ACCEPTANCE CRITERIA (Milestone 3)

- [ ] `GET /api/concepts/{concept_id}/scores` endpoint returns score data for a concept
- [ ] `GET /api/scores` endpoint returns list of recent scores
- [ ] CLI runner invokes scoring after synthesis (skippable with `--no-scoring`)
- [ ] CLI supports `--score-only <concept-id>` for re-scoring existing concepts
- [ ] Missing `OPENAI_API_KEY` gracefully skips scoring with warning
- [ ] Scoring failure logs error but does not crash the run
- [ ] Ruff check and format pass
