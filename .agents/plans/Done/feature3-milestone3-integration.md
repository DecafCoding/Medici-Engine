# Feature 3 — Milestone 3: Integration

**Parent feature**: [feature3-synthesizer-agent.md](feature3-synthesizer-agent.md)
**Tasks**: 5–6
**Goal**: Wire synthesis into the CLI runner and add API endpoints
**Depends on**: Milestone 1 (DB queries) and Milestone 2 (Synthesizer class)

---

## CONTEXT REFERENCES

### Relevant Codebase Files — MUST READ BEFORE IMPLEMENTING

- `scripts/run_conversation.py` (lines 160-196) — Why: Shows where synthesis should be called — after `complete_run()` and `record_pairing()`. The transcript is available as `turns` (list of `Turn`).
- `src/api/routes.py` (lines 1-38) — Why: Shows route pattern — `router = APIRouter(prefix="/api")`, dependency injection via `request.app.state.db`. New synthesis endpoints follow this pattern.
- `src/config.py` (lines 40-44) — Why: `openai_api_key` field — CLI must check this is set before attempting synthesis.

### Files to Modify

- `scripts/run_conversation.py` — Wire synthesis after conversation completion
- `src/api/routes.py` — Add concept endpoints

---

## IMPLEMENTATION PLAN

### Task 5: Wire synthesis into the CLI runner

Add synthesis as an optional step after conversation completion in the CLI.

- **UPDATE**: `scripts/run_conversation.py`:
  - Add imports: `from src.synthesis.synthesizer import Synthesizer, SynthesisError` and `from src.synthesis.models import ConceptExtraction` and `from src.db.queries import ConceptCreate, create_concept`
  - Add `--no-synthesis` flag to argparse (default: synthesis runs)
  - After `complete_run()` and `record_pairing()` (around line 179), if synthesis is enabled:
    1. Create a `Synthesizer` instance
    2. Call `synthesizer.synthesize(turns, persona_a.name, persona_b.name, shared_object.text)`
    3. Create a `ConceptCreate` from the extraction result and `run_record.id`
    4. Call `create_concept(db, concept_create)` to persist
    5. Print the concept (title, premise, originality)
  - Wrap synthesis in try/except `SynthesisError` — log the error but don't fail the run (the transcript is already saved)
  - Add a `--synthesis-only` flag that takes a run ID and runs synthesis on an existing completed run (useful for re-running synthesis on old transcripts)
- **PATTERN**: Follow the existing error handling in `run_conversation.py:198-201` — catch domain exceptions, log, and exit
- **GOTCHA**: Synthesis failure should NOT cause the CLI to exit with error code 1 — the conversation was successful, synthesis is an additional step. Log the error, print a warning, continue.
- **GOTCHA**: Check `settings.openai_api_key` is set before attempting synthesis. If empty, skip synthesis with a warning.
- **VALIDATE**: `uv run python scripts/run_conversation.py --help` (verify new flags appear)

### Task 6: Add concept API endpoints

Extend the API with endpoints for listing and viewing concepts.

- **UPDATE**: `src/api/routes.py`:
  - Add `GET /api/concepts` — list concepts with optional status filter and limit
  - Add `GET /api/concepts/{concept_id}` — get a single concept by ID
  - Add `GET /api/runs/{run_id}/concept` — get the concept for a specific run (convenience)
- **PATTERN**: Mirror the exact structure of `list_runs()` and `get_run()` endpoints (lines 23-37)
- **IMPORTS**: Add `from src.db.queries import Concept, get_concepts, get_concept_by_run_id` (and the single-concept getter if needed)
- **GOTCHA**: Follow the existing route pattern — use `request.app.state.db` for database access
- **VALIDATE**: `uv run python -c "from src.api.routes import router; print([r.path for r in router.routes])"`

---

## NOTES

**Failure isolation.** Synthesis failure must NOT lose the conversation transcript. The transcript is already saved before synthesis runs. If synthesis fails (API down, rate limit, refusal), the run remains `completed` with its transcript, and synthesis can be retried later via `--synthesis-only`.

---

## VALIDATION CHECKPOINT

Before proceeding to Milestone 4, verify:

```bash
# CLI accepts new flags
uv run python scripts/run_conversation.py --help

# API routes include concept endpoints
uv run python -c "from src.api.routes import router; paths = [r.path for r in router.routes]; print(paths); assert '/concepts' in str(paths)"

# Lint passes
uv run ruff check scripts/ src/api/
uv run ruff format --check scripts/ src/api/
```

**Expected**: All commands pass with exit code 0
