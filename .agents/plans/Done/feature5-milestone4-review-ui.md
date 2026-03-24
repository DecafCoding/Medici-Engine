# Feature 5 — Milestone 4: Review UI

**Parent plan**: `feature5-review-ui-batch-setup.md`
**Tasks**: 7–8
**Goal**: Create concept review list, detail page, transcript drawer, status toggle, and wire everything into the app

---

## Feature Context

This milestone builds the primary review surface — the reason the UI exists. A sortable/filterable concept table lets the operator scan output quickly. The detail page shows the full concept with per-axis scores and reasoning. A transcript drawer provides drill-down access to the source conversation. Keep/discard toggle is the single action, updated via HTMX without page reload.

## User Story

As a Medici Engine operator
I want to configure and launch conversation batches from a browser, then browse and review the scored concepts
So that I can run the system at scale and make keep/discard decisions faster than via CLI output

---

## CONTEXT REFERENCES

### Relevant Codebase Files — READ BEFORE IMPLEMENTING

- `src/ui/routes.py` (created in Milestone 3) — Why: Add review endpoints to the existing UI router. Follow the same patterns established for batch endpoints.
- `src/db/queries.py` (full file) — Why: Uses `get_concepts_with_scores` (added in Milestone 2), `get_concept_by_id`, `get_run_by_id`, `get_score_by_concept_id`, `update_concept_status`. All query functions needed for the review UI are already implemented.
- `src/main.py` (full file) — Why: Wire up the UI router, static files mount, and root redirect here.
- `src/api/routes.py` (full file) — Why: Existing route patterns. The UI router mirrors this structure.
- `src/templates/base.html` (created in Milestone 1) — Why: All review templates extend this layout.
- `tests/test_api.py` (full file) — Why: Test patterns for HTTP endpoints. UI tests follow the same structure but assert on HTML content.
- `tests/conftest.py` (full file) — Why: `client` and `db` fixtures. The `_seed_score` helper in test_api.py shows how to create test data.
- `CLAUDE.md` — Why: Async patterns, type hints, docstrings, logging requirements.

### Relevant Documentation — READ BEFORE IMPLEMENTING

- [HTMX hx-get](https://htmx.org/attributes/hx-get/) — For filter/sort controls and lazy-loading transcript
- [HTMX hx-patch](https://htmx.org/attributes/hx-patch/) — For status toggle
- [HTMX hx-swap](https://htmx.org/attributes/hx-swap/) — Swap strategies: innerHTML, outerHTML
- [HTMX hx-target](https://htmx.org/attributes/hx-target/) — Target element for content swap
- [HTMX hx-trigger](https://htmx.org/attributes/hx-trigger/) — Event triggers including `click once` for lazy load
- [HTMX hx-include](https://htmx.org/attributes/hx-include/) — Include other form elements in AJAX request
- [HTMX hx-vals](https://htmx.org/attributes/hx-vals/) — Add values to AJAX request (for status toggle)
- [FastAPI Templates](https://fastapi.tiangolo.com/advanced/templates/) — `TemplateResponse` usage
- [FastAPI Static Files](https://fastapi.tiangolo.com/tutorial/static-files/) — `StaticFiles` mount

### New Files to Create

- `src/templates/review.html` — Concept review list page
- `src/templates/detail.html` — Concept detail page with scores and transcript
- `src/templates/fragments/concept_rows.html` — Table body fragment for HTMX swap
- `src/templates/fragments/transcript.html` — Transcript drawer content
- `src/templates/fragments/concept_status.html` — Status badge fragment for HTMX swap

### Files to Modify

- `src/ui/routes.py` — Add review endpoints
- `src/main.py` — Register UI router, mount static files, add root redirect

---

## IMPLEMENTATION PLAN

### Task 7: UI Routes — Concept Review

Add review endpoints to `src/ui/routes.py` and create all review templates.

**Part A — Review endpoints (add to `src/ui/routes.py`):**

- `GET /ui/review` — render concept review list:
  - Query params: `status: str | None = None`, `sort: str = "date_desc"`, `limit: int = 50`
  - Call `get_concepts_with_scores(db, status=status, sort_by=sort, limit=limit)`
  - Return `templates.TemplateResponse("review.html", {"request": request, "concepts": concepts, "current_status": status, "current_sort": sort})`

- `GET /ui/review/rows` — return just the table body fragment (for HTMX swap):
  - Same query params as above
  - Call `get_concepts_with_scores(...)` same as above
  - Return `templates.TemplateResponse("fragments/concept_rows.html", {"request": request, "concepts": concepts})`

- `GET /ui/review/{concept_id}` — render concept detail page:
  - Fetch concept via `get_concept_by_id(db, concept_id)`
  - If None, return 404
  - Fetch score via `get_score_by_concept_id(db, concept_id)`
  - Fetch run via `get_run_by_id(db, concept.run_id)` — needed for persona names, shared object text
  - Compute `overall_score` from score fields (if score exists)
  - Return `templates.TemplateResponse("detail.html", {"request": request, "concept": concept, "score": score, "run": run, "overall_score": overall_score})`

- `GET /ui/review/{concept_id}/transcript` — return transcript fragment (lazy loaded):
  - Fetch run via concept's `run_id`
  - Return `templates.TemplateResponse("fragments/transcript.html", {"request": request, "transcript": run.transcript, "run": run})`
  - If run or transcript is None, return a simple "No transcript available" fragment

- `PATCH /ui/review/{concept_id}/status` — toggle concept status:
  - Parse form data to get `status` value ("kept" or "discarded")
  - Call `update_concept_status(db, concept_id, status)`
  - Return `templates.TemplateResponse("fragments/concept_status.html", {"request": request, "concept": updated_concept})`

**Part B — Review list template:**

- **CREATE**: `src/templates/review.html` — extends `base.html`:
  - Title block: "Review — Medici Engine"
  - Filter controls row:
    - Status dropdown: `<select name="status" hx-get="/ui/review/rows" hx-target="#concept-table-body" hx-include="[name='sort']">` with options: All (value=""), Pending, Kept, Discarded
    - Sort dropdown: `<select name="sort" hx-get="/ui/review/rows" hx-target="#concept-table-body" hx-include="[name='status']">` with options: Newest First (date_desc), Oldest First (date_asc), Highest Score (score_desc), Lowest Score (score_asc)
  - Table with headers: Title | Premise | Score | Status | Date
  - Table body: `<tbody id="concept-table-body">{% include "fragments/concept_rows.html" %}</tbody>`

- **CREATE**: `src/templates/fragments/concept_rows.html` — partial:
  - Loop over `concepts`:
    ```html
    {% for c in concepts %}
    <tr>
        <td><a href="/ui/review/{{ c.id }}">{{ c.title }}</a></td>
        <td>{{ c.premise[:100] }}{% if c.premise|length > 100 %}...{% endif %}</td>
        <td>{% if c.overall_score is not none %}{{ "%.1f"|format(c.overall_score) }}{% else %}—{% endif %}</td>
        <td>{% include "fragments/concept_status.html" with context %}</td>
        <td>{{ c.created_at[:10] }}</td>
    </tr>
    {% endfor %}
    ```
  - If `concepts` is empty: `<tr><td colspan="5">No concepts found.</td></tr>`

**Part C — Detail page template:**

- **CREATE**: `src/templates/detail.html` — extends `base.html`:
  - Back link: `<a href="/ui/review">← Back to Review</a>`
  - Concept section:
    - Title (h2)
    - Status badge with keep/discard buttons:
      - `<span id="status-badge">{% include "fragments/concept_status.html" %}</span>`
      - Keep button: `<button hx-patch="/ui/review/{{ concept.id }}/status" hx-vals='{"status": "kept"}' hx-target="#status-badge" hx-swap="innerHTML">Keep</button>`
      - Discard button: same pattern with `"discarded"`
    - Premise (full text)
    - Originality (full text)
  - Scores section (if `score` is not None):
    - Overall score prominent display
    - Three score cards, one per axis:
      - Axis name, score/10, full reasoning text
    - If `score` is None: "Not yet scored"
  - Run info section:
    - Persona A name, Persona B name, Shared object text (from `run`)
  - Transcript drawer:
    - `<details>` element (or a div with click handler):
      - Summary/trigger: "View Transcript"
      - Content area: `<div hx-get="/ui/review/{{ concept.id }}/transcript" hx-trigger="click once" hx-swap="innerHTML">Click to load transcript...</div>`
      - When clicked, HTMX fetches the transcript fragment and replaces the placeholder text

**Part D — Fragment templates:**

- **CREATE**: `src/templates/fragments/transcript.html` — partial:
  - If `transcript` is not None:
    - Loop over turns: `{% for turn in transcript %}`
    - Each turn: `<div class="turn"><strong>[Turn {{ turn.turn_number }}] {{ turn.persona_name }}:</strong><p>{{ turn.content }}</p></div>`
  - Else: `<p>No transcript available.</p>`

- **CREATE**: `src/templates/fragments/concept_status.html` — partial:
  - `<span class="badge badge-{{ concept.status }}">{{ concept.status }}</span>`
  - CSS classes `badge-pending`, `badge-kept`, `badge-discarded` are defined in `style.css` (Milestone 1)

- **GOTCHA**: HTMX sends `hx-vals` as form-encoded data by default. The PATCH endpoint should parse via `await request.form()` to get the `status` value.
- **GOTCHA**: When sorting by score, concepts without scores have `overall_score = None`. In templates, check `{% if c.overall_score is not none %}` (Jinja2 uses `none` not `None`).
- **GOTCHA**: The `concept_status.html` fragment is used both in the review table rows AND in the detail page. Make sure the variable name is consistent — use `concept` (not `c`) in the fragment, and set it correctly in both calling contexts. In `concept_rows.html`, set `{% with concept=c %}{% include ... %}{% endwith %}` or pass it via template context.
- **GOTCHA**: `details` element or custom drawer — use a simple `<details><summary>` HTML element for the transcript drawer. No JS needed — HTMX handles the lazy load on first open.

- **VALIDATE**: `uv run ruff check src/ui/ && uv run ruff format --check src/ui/`

### Task 8: Wire Up App — Static Files, Templates, Router

Register the UI router and static file mount in the FastAPI app.

- **UPDATE**: `src/main.py`:
  - Add import: `from fastapi.staticfiles import StaticFiles`
  - Add import: `from fastapi.responses import RedirectResponse`
  - Add import: `from src.ui.routes import router as ui_router`
  - After `app.include_router(router)`, add: `app.include_router(ui_router)`
  - After router includes, mount static files:
    ```python
    app.mount(
        "/static",
        StaticFiles(directory=str(Path(__file__).resolve().parent / "static")),
        name="static",
    )
    ```
  - Add root redirect endpoint:
    ```python
    @app.get("/")
    async def root() -> RedirectResponse:
        """Redirect root to the review UI."""
        return RedirectResponse(url="/ui/review")
    ```

- **GOTCHA**: The `StaticFiles` mount MUST come after all `include_router` calls. FastAPI processes mounts in order — if `StaticFiles` is mounted at `/static` before routers, it won't shadow them (different prefix). But if you accidentally mount at `/`, it will catch everything. Always mount at a specific prefix.
- **GOTCHA**: Static files directory path must be absolute. `Path(__file__).resolve().parent / "static"` gives the absolute path to `src/static/`.

- **VALIDATE**: Run the app manually:
  ```bash
  uv run uvicorn src.main:app --host 0.0.0.0 --port 8080
  ```
  Then verify:
  - `http://localhost:8080/` redirects to `/ui/review`
  - `http://localhost:8080/static/style.css` returns CSS
  - `http://localhost:8080/static/htmx.min.js` returns JS
  - `http://localhost:8080/ui/batch` renders the batch setup form
  - `http://localhost:8080/ui/review` renders the review table (empty if no data)
  - `http://localhost:8080/api/runs` still returns JSON (existing API untouched)

---

## VALIDATION CHECKPOINT

```bash
uv run ruff check . && uv run ruff format --check .
```

**Expected**: All linting passes.

```bash
uv run pytest tests/ -v
```

**Expected**: All existing tests pass. (New UI tests come in Milestone 5.)

Manual: start the server and verify all pages render, HTMX interactions work (filter, sort, transcript lazy load, status toggle).

---

## ACCEPTANCE CRITERIA (Milestone 4)

- [ ] `GET /ui/review` renders concept list table with title, premise snippet, score, status, date
- [ ] `GET /ui/review/rows` returns HTML table body fragment (for HTMX filter/sort)
- [ ] Filter dropdown updates table via HTMX (status: all/pending/kept/discarded)
- [ ] Sort dropdown updates table via HTMX (score asc/desc, date asc/desc)
- [ ] `GET /ui/review/{concept_id}` renders detail page with full concept, scores, reasoning
- [ ] `GET /ui/review/{concept_id}/transcript` returns transcript fragment (lazy loaded)
- [ ] `PATCH /ui/review/{concept_id}/status` toggles status and returns updated badge
- [ ] `src/main.py` mounts static files at `/static`, includes UI router, redirects `/` to `/ui/review`
- [ ] Existing JSON API at `/api/*` still works unchanged
- [ ] All existing tests still pass (zero regressions)
- [ ] Ruff check and format pass
