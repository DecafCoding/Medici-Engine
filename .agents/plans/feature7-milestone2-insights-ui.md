# Feature 7 — Milestone 2: Insights UI

**Parent plan**: `feature7-feedback-loop.md`
**Depends on**: Milestone 1 (analytics queries must exist)
**Tasks**: 5–7
**Goal**: Add insights route, templates, fragments, and nav link so the operator can view pairing and shared object performance.

The following plan should be complete, but validate documentation and codebase patterns before implementing.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — READ BEFORE IMPLEMENTING

- `src/ui/routes.py` (full file) — Why: Pattern for adding new UI endpoints and rendering templates.
- `src/db/queries.py` — Why: Import `get_pairing_performance`, `get_shared_object_performance` from here.
- `src/domains/registry.py` — Why: Import `get_all_domains` for the domain filter dropdown.
- `src/templates/base.html` (full file) — Why: Nav bar needs the new Insights link. Template inheritance pattern.
- `src/templates/review.html` (full file) — Why: Pattern for list pages with filter controls and HTMX.
- `src/templates/fragments/concept_rows.html` (full file) — Why: Pattern for HTMX table body fragments.
- `tests/test_ui.py` (full file) — Why: Pattern for UI endpoint tests with `client` fixture.
- `tests/conftest.py` (full file) — Why: Shared fixtures including `client`.

### New Files to Create

- `src/templates/insights.html` — Insights page template with pairing and shared object performance tables
- `src/templates/fragments/pairing_rows.html` — HTMX fragment for pairing performance table body
- `src/templates/fragments/shared_object_rows.html` — HTMX fragment for shared object performance table body

### Patterns to Follow

**UI Route Pattern** (from `src/ui/routes.py`):
```python
@router.get("/some-page")
async def some_page(request: Request):
    """Render the page with data."""
    db = request.app.state.db
    data = await queries.get_something(db)
    return templates.TemplateResponse(
        "some_page.html",
        {"request": request, "data": data},
    )
```

**HTMX Fragment Route Pattern** (from `src/ui/routes.py:156-171`):
```python
@router.get("/some-page/rows")
async def some_page_rows(request: Request, filter: str | None = None):
    """Return the table body fragment for HTMX swap."""
    db = request.app.state.db
    data = await queries.get_something(db, filter=filter)
    return templates.TemplateResponse(
        "fragments/some_rows.html",
        {"request": request, "data": data},
    )
```

**Template Pattern** (from `review.html`):
```html
{% extends "base.html" %}
{% block title %}Page — Medici Engine{% endblock %}
{% block heading %}Page{% endblock %}
{% block content %}
<!-- content here -->
{% endblock %}
```

**Fragment Pattern** (from `fragments/concept_rows.html`):
```html
{% if items %}
{% for item in items %}
<tr>
    <td>{{ item.field }}</td>
</tr>
{% endfor %}
{% else %}
<tr><td colspan="N">No data available.</td></tr>
{% endif %}
```

---

## IMPLEMENTATION TASKS

### Task 5: Insights UI Route

Add the insights page endpoint and HTMX fragment endpoints.

- **ADD** to `src/ui/routes.py`:
  - Import `get_pairing_performance`, `get_shared_object_performance` from `src.db.queries`
  - Import `get_all_domains` from `src.domains.registry`
  - `GET /ui/insights` — main insights page, accepts optional `domain` query param
    - Calls both analytics queries
    - Passes `pairings`, `shared_objects`, `current_domain`, `domains` to template
  - `GET /ui/insights/pairings` — HTMX fragment for pairing table body (for domain filter swap)
  - `GET /ui/insights/shared-objects` — HTMX fragment for shared object table body
- **PATTERN**: Mirror `review_list` and `review_rows` at `src/ui/routes.py:131-171`
- **VALIDATE**: `uv run ruff check src/ui/routes.py`

### Task 6: Insights Templates

Create the insights page and fragment templates.

- **CREATE** `src/templates/insights.html`:
  - Extends `base.html`
  - Title: "Insights — Medici Engine"
  - Heading: "Insights"
  - Domain filter dropdown (if multiple domains registered) with HTMX to swap both tables
    - Use `hx-get` on the select to hit both `/ui/insights/pairings` and `/ui/insights/shared-objects`
    - Or: single `hx-get="/ui/insights"` that re-renders the full content block (simpler, follows review.html pattern)
  - **Pairing Performance** section:
    - `<h2>Pairing Performance</h2>`
    - Table headers: Persona A | Persona B | Runs | Kept | Discarded | Avg Score | Max Score | Kept Rate
    - `<tbody id="pairing-table-body">{% include "fragments/pairing_rows.html" %}</tbody>`
  - **Shared Object Performance** section:
    - `<h2>Shared Object Performance</h2>`
    - Table headers: Shared Object | Type | Runs | Kept | Discarded | Avg Score | Kept Rate
    - `<tbody id="shared-object-table-body">{% include "fragments/shared_object_rows.html" %}</tbody>`
  - If no data in either table, the fragments handle the empty state
- **CREATE** `src/templates/fragments/pairing_rows.html`:
  - Loop over `pairings` — one `<tr>` per pairing
  - Color-code kept_rate: use `score-high` class if >= 0.5, `score-mid` if >= 0.25, `score-low` otherwise (reuse existing CSS classes from `style.css`)
  - Format avg_score and max_score to 1 decimal place: `{{ "%.1f"|format(p.avg_score) }}`
  - Format kept_rate as percentage: `{{ "%.0f"|format(p.kept_rate * 100) }}%`
  - Show "—" (`&mdash;`) for None values
  - Empty state: `<tr><td colspan="8">No pairing data available.</td></tr>`
- **CREATE** `src/templates/fragments/shared_object_rows.html`:
  - Loop over `shared_objects` — one `<tr>` per shared object
  - Truncate shared_object_text to 80 chars with ellipsis: `{{ s.shared_object_text[:80] }}{% if s.shared_object_text|length > 80 %}...{% endif %}`
  - Same score/rate formatting as pairing rows
  - Empty state: `<tr><td colspan="7">No shared object data available.</td></tr>`
- **PATTERN**: Follow `review.html` and `fragments/concept_rows.html` for structure and styling
- **VALIDATE**: Visual — start server and check `/ui/insights` renders

### Task 7: Navigation Update

Add the Insights link to the base template nav bar.

- **UPDATE** `src/templates/base.html` line 13:
  - Add `<a href="/ui/insights">Insights</a>` after the "Batch Setup" link
- **VALIDATE**: `uv run pytest tests/test_ui.py -v --tb=short` (existing tests should still pass)

---

## VALIDATION CHECKPOINT

```bash
# Must all pass before moving to Milestone 3
uv run ruff check src/ui/routes.py
uv run ruff format --check .
uv run pytest tests/test_ui.py -v --tb=short

# Manual check: start server and visit /ui/insights
# uv run uvicorn src.main:app --reload
```

**Done when**: `/ui/insights` renders with empty state. Nav bar shows Review | Batch Setup | Insights on all pages. All existing UI tests pass.

---

## ACCEPTANCE CRITERIA (Milestone 2)

- [ ] `/ui/insights` page renders with pairing and shared object performance tables
- [ ] Domain filter dropdown appears when multiple domains are registered
- [ ] HTMX fragments return isolated table body HTML (no full page layout)
- [ ] Empty state messages shown when no data is available
- [ ] Navigation bar includes Insights link on all pages
- [ ] Score and rate values are formatted cleanly (1 decimal, percentage)
- [ ] Shared object text is truncated at 80 characters in the table
- [ ] All existing UI tests still pass
