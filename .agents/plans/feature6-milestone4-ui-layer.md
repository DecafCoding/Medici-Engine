# Feature 6 — Milestone 4: UI Layer

**Tasks:** 11–12
**Goal:** Routes pass domain config to templates, templates render dynamically
**Validation checkpoint:** Server starts, `/ui/review` renders without errors
**Depends on:** Milestone 2 (new query models) and Milestone 3 (service layer domain-aware)

---

## Prerequisites

Read the parent plan for full context: [feature6-domain-expansion.md](feature6-domain-expansion.md)

### Relevant Codebase Files — MUST READ BEFORE IMPLEMENTING

- `src/ui/routes.py` (full file) — Why: Must pass domain config to templates, remove hardcoded score calculation
- `src/templates/detail.html` (full file) — Why: Hardcoded concept field labels and score axis cards
- `src/templates/review.html` (full file) — Why: Hardcoded table column headers
- `src/templates/fragments/concept_rows.html` (full file) — Why: Hardcoded concept field references
- `src/templates/fragments/concept_status.html` (full file) — Why: Domain-agnostic, no changes expected
- `src/templates/fragments/transcript.html` (full file) — Why: Domain-agnostic, no changes expected
- `src/templates/fragments/batch_status.html` (full file) — Why: Domain-agnostic, no changes expected
- `src/templates/base.html` (full file) — Why: No changes expected, but read for context
- `src/templates/batch.html` (full file) — Why: No changes expected (batch setup is domain-agnostic)

---

## IMPLEMENTATION TASKS

### Task 11: UI Routes Refactor

Pass domain config to templates.

- **UPDATE** `src/ui/routes.py`:
  - Import `get_active_domain` from `src/domains/registry`
  - In `review_detail()`:
    - Get domain config: `domain = get_active_domain()`
    - Pass `domain` to template context (for field labels and axis rendering)
    - Remove hardcoded overall score calculation (now stored in `score.overall_score`)
    - Pass score object directly (its `axes` field is already a list of AxisScoreRecord)
  - In `review_list()` and `review_rows()`:
    - Pass `domain` to template context (for column headers if needed)

- **GOTCHA**: The `Score` model's `axes` field is a list of `AxisScoreRecord` Pydantic models. When passed to Jinja2, access them as objects (`axis_score.label`, `axis_score.score`). If Jinja2 has issues with Pydantic models, convert to dicts first with `[a.model_dump() for a in score.axes]`.
- **VALIDATE**: `uv run python -c "from src.ui.routes import router; print('Import OK')"`

### Task 12: Template Refactor

Make templates render domain-specific fields dynamically.

- **UPDATE** `src/templates/detail.html`:
  - Replace hardcoded "Premise" / "Originality" sections with a loop over domain extraction fields:
    ```jinja2
    {% for field in domain.extraction_fields %}
    {% if field.name != domain.primary_field %}
    <h3 class="mt-2">{{ field.label }}</h3>
    <p>{{ concept.fields[field.name] }}</p>
    {% endif %}
    {% endfor %}
    ```
  - Replace hardcoded score axis cards with a loop over score axes:
    ```jinja2
    {% for axis_score in score.axes %}
    <div class="score-card">
        <h4>{{ axis_score.label }} <span class="score {% if axis_score.score >= 7 %}score-high{% elif axis_score.score >= 4 %}score-mid{% else %}score-low{% endif %}">{{ "%.1f"|format(axis_score.score) }}</span></h4>
        <p class="text-sm">{{ axis_score.reasoning }}</p>
    </div>
    {% endfor %}
    ```
  - Overall score: use `score.overall_score` passed from route context

- **UPDATE** `src/templates/review.html`:
  - Column headers can stay generic: "Title", "Summary", "Score", "Status", "Date"
  - The "Premise" header becomes "Summary" — a generic label that works for any domain

- **UPDATE** `src/templates/fragments/concept_rows.html`:
  - Title column: `{{ c.title }}` (unchanged — denormalized primary field)
  - Summary column: Show a snippet from the second field in `c.fields`. Approach:
    ```jinja2
    {% set field_values = c.fields.values()|list %}
    {% if field_values|length > 1 %}
    {% set summary = field_values[1] %}
    {{ summary[:100] }}{% if summary|length > 100 %}...{% endif %}
    {% endif %}
    ```
    Note: dict ordering is guaranteed in Python 3.7+ so fields_json insertion order is preserved.

- **VALIDATE**: Start the server and manually check `/ui/review` renders correctly

---

## MILESTONE VALIDATION

```bash
# Routes import cleanly
uv run python -c "from src.ui.routes import router; print('Import OK')"

# Server starts without import errors (Ctrl+C to stop)
uv run python -c "from src.main import app; print('App OK')"

# Lint must still pass
uv run ruff check .
uv run ruff format --check .
```

**Note:** Full UI testing requires the test fixtures to be updated (Milestone 5). Manual validation by starting the server is the primary check for this milestone.
