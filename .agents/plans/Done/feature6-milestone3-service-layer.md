# Feature 6 — Milestone 3: Service Layer

**Tasks:** 7–10
**Goal:** Synthesizer, scorer, batch runner, CLI all domain-aware
**Validation checkpoint:** All imports succeed, batch runner can be instantiated, CLI `--list-domains` works
**Depends on:** Milestone 1 (domain config + model factory) and Milestone 2 (new query models)

---

## Prerequisites

Read the parent plan for full context: [feature6-domain-expansion.md](feature6-domain-expansion.md)

### Relevant Codebase Files — MUST READ BEFORE IMPLEMENTING

- `src/synthesis/synthesizer.py` (full file) — Why: Must refactor to accept DomainConfig, use dynamic models
- `src/synthesis/models.py` (full file) — Why: `ConceptExtraction` to be removed
- `src/scoring/scorer.py` (full file) — Why: Must refactor to accept DomainConfig, use dynamic models
- `src/scoring/models.py` (full file) — Why: `ConceptScoring` to be removed, `AxisScore` kept
- `src/batch/runner.py` (full file) — Why: Must wire domain through the full pipeline
- `scripts/run_conversation.py` (full file) — Why: Must add domain-aware CLI flags and dynamic display

### Patterns to Follow

**Structured Output Pattern (from src/synthesis/synthesizer.py:126):**
```python
response = await self._client.beta.chat.completions.parse(
    model=settings.synthesis_model,
    messages=messages,
    response_format=ConceptExtraction,  # Will become dynamic model
    temperature=0.4,
)
result = response.choices[0].message.parsed
```

---

## IMPLEMENTATION TASKS

### Task 7: Synthesis Layer Refactor

Make the synthesizer domain-aware.

- **UPDATE** `src/synthesis/synthesizer.py`:
  - Remove the hardcoded `SYNTHESIS_PROMPT` constant
  - Change `Synthesizer.__init__()` to accept a `DomainConfig` parameter and store it
  - Change `synthesize()` to use `self._domain.synthesis_prompt` as the system message
  - Use `create_extraction_model(self._domain)` to build the response_format dynamically
  - Return the parsed result as a `dict[str, str]` (the extraction fields) instead of `ConceptExtraction`
  - Keep `_format_transcript()` and `_build_messages()` — they are domain-agnostic
  - Update `_build_messages()` to use domain prompt

- **UPDATE** `src/synthesis/models.py`:
  - Remove `ConceptExtraction` class (replaced by dynamic models)
  - File may become empty or contain only docstring — that's fine, keep it for the module structure

- **IMPORTS**: `from src.domains.models import DomainConfig, create_extraction_model`
- **GOTCHA**: The dynamic model must satisfy OpenAI strict mode. All fields required, no Optional.
- **VALIDATE**: `uv run python -c "from src.synthesis.synthesizer import Synthesizer; print('Import OK')"`

### Task 8: Scoring Layer Refactor

Make the scorer domain-aware.

- **UPDATE** `src/scoring/scorer.py`:
  - Remove the hardcoded `SCORING_PROMPT` constant
  - Change `Scorer.__init__()` to accept a `DomainConfig` parameter
  - Change `score()` to accept `fields: dict[str, str]` instead of `title, premise, originality`
  - Use `create_scoring_model(self._domain)` to build the response_format dynamically
  - Use `self._domain.scoring_prompt` as the system message
  - Build user content from all fields in the dict: format as `**{label}:** {value}` for each field (look up label from `self._domain.extraction_fields` by name)
  - Return result as `list[AxisScoreRecord]` (from `src/db/queries`) by mapping the parsed response's AxisScore fields to AxisScoreRecord objects with label from domain config

- **UPDATE** `src/scoring/models.py`:
  - Keep `AxisScore` as-is (used by dynamic scoring models)
  - Remove `ConceptScoring` class (replaced by dynamic models)

- **IMPORTS**: `from src.domains.models import DomainConfig, create_scoring_model`
- **VALIDATE**: `uv run python -c "from src.scoring.scorer import Scorer; print('Import OK')"`

### Task 9: Batch Runner Refactor

Wire domain config through the batch pipeline.

- **UPDATE** `src/batch/runner.py`:
  - Import `get_active_domain` from `src/domains/registry`
  - In `run_batch()`, get the active domain config at the start: `domain = get_active_domain()`
  - Pass `domain` to `Synthesizer(domain)` and `Scorer(domain)`
  - Update `_run_synthesis()` (or equivalent method):
    - `Synthesizer(domain)` instead of `Synthesizer()`
    - Map extraction result (dict) to `ConceptCreate` with `domain=domain.name`, `title=extraction[domain.primary_field]`, `fields=extraction`
  - Update `_run_scoring()` (or equivalent method):
    - `Scorer(domain)` instead of `Scorer()`
    - Pass `concept.fields` to `scorer.score(fields=concept.fields)`
    - Map result (list of AxisScoreRecord) to `ScoreCreate(concept_id=..., axes=result)`

- **UPDATE** `src/batch/models.py` — No changes needed (persona pairs, shared objects, turn count are domain-agnostic)
- **VALIDATE**: `uv run python -c "from src.batch.runner import BatchRunner; print('Import OK')"`

### Task 10: CLI Script Refactor

Update the CLI runner for domain-aware operation.

- **UPDATE** `scripts/run_conversation.py`:
  - Import `get_active_domain` and `get_all_domains` from `src/domains/registry`
  - Add `--domain` argument (optional, overrides `ACTIVE_DOMAIN` env var)
  - Add `--list-domains` flag to list available domains
  - In `run()`: resolve domain from `--domain` arg or `get_active_domain()`
  - In `_run_synthesis()`: Pass domain to Synthesizer, map result to ConceptCreate with `domain=domain.name`, `title=extraction[domain.primary_field]`, `fields=extraction`
  - In `_run_scoring()`: Pass domain to Scorer, pass `concept.fields` to `score()`, display axes dynamically:
    ```python
    for axis_score in result:
        print(f"{axis_score.label}:  {axis_score.score}/10")
        print(f"  → {axis_score.reasoning}\n")
    ```
  - In `_run_synthesis()` print: iterate over domain extraction fields to display each field by label
  - Update `_synthesis_only()` and `_score_only()` to resolve domain

- **VALIDATE**: `uv run python scripts/run_conversation.py --list-domains`

---

## MILESTONE VALIDATION

```bash
# All imports succeed
uv run python -c "from src.synthesis.synthesizer import Synthesizer; print('Synthesis OK')"
uv run python -c "from src.scoring.scorer import Scorer; print('Scoring OK')"
uv run python -c "from src.batch.runner import BatchRunner; print('Batch OK')"

# CLI domain list works
uv run python scripts/run_conversation.py --list-domains

# Lint must still pass
uv run ruff check .
uv run ruff format --check .
```

**Note:** Existing tests will be broken after this milestone because test files still use the old APIs (Synthesizer(), Scorer(), old model shapes). This is expected — tests are updated in Milestone 5.
