# Feature 5 — Milestone 1: Foundation

**Parent plan**: `feature5-review-ui-batch-setup.md`
**Tasks**: 1–3
**Goal**: Add dependencies, vendor HTMX, create static assets and base template

---

## Feature Context

Add a web interface to the Medici Engine for configuring/launching conversation batches and reviewing scored concepts. The UI uses server-rendered Jinja2 templates with HTMX for interactive updates — no frontend build toolchain. This milestone lays the groundwork: new pip dependencies, the vendored HTMX JS file, a minimal CSS stylesheet, and the base HTML template that all pages extend.

## User Story

As a Medici Engine operator
I want to configure and launch conversation batches from a browser, then browse and review the scored concepts
So that I can run the system at scale and make keep/discard decisions faster than via CLI output

---

## CONTEXT REFERENCES

### Relevant Codebase Files — READ BEFORE IMPLEMENTING

- `pyproject.toml` (full file) — Why: Add new dependencies here. Follow existing format for version pinning.
- `src/main.py` (full file) — Why: Understand current app structure. Static file mount will be added in Milestone 4 but the directory must exist now.
- `CLAUDE.md` — Why: Documentation requirements, dependency management rules (use uv, declare in pyproject.toml).

### Relevant Documentation — READ BEFORE IMPLEMENTING

- [FastAPI Templates](https://fastapi.tiangolo.com/advanced/templates/) — Jinja2Templates setup
- [FastAPI Static Files](https://fastapi.tiangolo.com/tutorial/static-files/) — StaticFiles mount pattern
- [HTMX Documentation](https://htmx.org/docs/) — Core attributes: hx-get, hx-post, hx-swap, hx-target, hx-trigger
- [Jinja2 Template Inheritance](https://jinja.palletsprojects.com/en/3.1.x/templates/#template-inheritance) — block/extends pattern

### New Files to Create

- `src/static/htmx.min.js` — Vendored HTMX 2.0 minified
- `src/static/style.css` — Minimal CSS for the UI
- `src/templates/base.html` — Layout template all pages extend

### Files to Modify

- `pyproject.toml` — Add `jinja2` and `python-multipart` dependencies

---

## IMPLEMENTATION PLAN

### Task 1: Add Dependencies

Add `jinja2` and `python-multipart` to `pyproject.toml` and sync.

- **UPDATE**: `pyproject.toml` — add `"jinja2>=3.1.0"` and `"python-multipart>=0.0.20"` to the `dependencies` list
- **GOTCHA**: `python-multipart` is required by FastAPI for parsing form data (`request.form()`). Without it, any HTML form POST will fail at runtime with an obscure import error.
- **VALIDATE**: `uv sync && uv run python -c "import jinja2; import multipart; print('OK')"`

### Task 2: Vendor HTMX and Create Static Assets

Download HTMX and create the minimal CSS file. Create the `src/static/` directory.

- **CREATE**: `src/static/htmx.min.js` — download HTMX 2.0.4 minified from `https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js`. Vendoring locally is better than a CDN reference because this tool may run on a local network without reliable internet.
- **CREATE**: `src/static/style.css` — minimal CSS for the UI:
  - Clean sans-serif font (system font stack)
  - Max-width container (~1000px) centered on the page
  - Table styling: borders, alternating row colors, padding
  - Form styling: labels, inputs, select dropdowns, submit button
  - Status badge colors: pending (gray), kept (green), discarded (red)
  - Score display: number with colored background based on range (0–3 red, 4–6 yellow, 7–10 green)
  - Transcript drawer: collapsible section with border, padding, monospace font for content
  - Navigation bar: horizontal links
  - No CSS framework — just enough to be clean and usable
- **VALIDATE**: `ls src/static/htmx.min.js src/static/style.css`

### Task 3: Create Base Template

Create the Jinja2 layout template that all pages extend.

- **CREATE**: `src/templates/base.html` — HTML5 layout:
  ```html
  <!DOCTYPE html>
  <html lang="en">
  <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>{% block title %}Medici Engine{% endblock %}</title>
      <link rel="stylesheet" href="/static/style.css">
      <script src="/static/htmx.min.js"></script>
  </head>
  <body>
      <nav>
          <a href="/ui/review">Review</a>
          <a href="/ui/batch">Batch Setup</a>
      </nav>
      <header>
          <h1>Medici Engine</h1>
      </header>
      <main>
          {% block content %}{% endblock %}
      </main>
  </body>
  </html>
  ```
- **PATTERN**: Standard Jinja2 template inheritance with `{% block %}` / `{% extends %}`
- **VALIDATE**: Template file exists and contains valid HTML5 structure with `{% block content %}`

---

## VALIDATION CHECKPOINT

```bash
uv sync && uv run python -c "import jinja2; import multipart; print('OK')" && ls src/static/htmx.min.js src/static/style.css src/templates/base.html
```

**Expected**: Dependencies install, all three new files exist.

```bash
uv run pytest tests/ -v
```

**Expected**: All existing tests still pass (zero regressions — no source code was modified).

---

## ACCEPTANCE CRITERIA (Milestone 1)

- [ ] `jinja2>=3.1.0` and `python-multipart>=0.0.20` added to `pyproject.toml` dependencies
- [ ] `uv sync` completes successfully
- [ ] `src/static/htmx.min.js` exists and contains HTMX 2.0 minified JS
- [ ] `src/static/style.css` exists with table, form, badge, transcript drawer, and nav styling
- [ ] `src/templates/base.html` exists with HTML5 layout, HTMX script tag, CSS link, nav links, and content block
- [ ] All existing tests still pass
