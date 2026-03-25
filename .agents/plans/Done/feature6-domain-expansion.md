# Feature 6: Domain Expansion

Make the Medici Engine domain-agnostic so that swapping between application domains (sci-fi book concepts, product design ideas, research questions, etc.) is a configuration change, not a code change.

---

## User Story

As a Medici Engine operator
I want to switch the system's target domain by changing configuration
So that I can use the same creative collision pipeline for different types of output without modifying code.

## Feature Metadata

**Feature Type**: Refactor + Enhancement
**Estimated Complexity**: High
**Primary Systems Affected**: `src/config.py`, `src/db/`, `src/synthesis/`, `src/scoring/`, `src/batch/`, `src/ui/`, `src/templates/`, `scripts/`, all tests
**Dependencies**: No new external packages required

---

## Solution Overview

1. **Domain configuration system** — Pydantic models defining extraction fields, scoring axes, and prompt templates per domain
2. **Dynamic Pydantic models** — `create_model()` builds OpenAI-compatible response_format models from domain config
3. **JSON storage** — Concept fields and score axes stored as JSON in SQLite instead of fixed columns
4. **Two built-in domains** — `sci-fi-concepts` (current) and `product-design` (new)
5. **`ACTIVE_DOMAIN` env var** — Selects which domain is active at runtime

---

## Design Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D1 | JSON storage for domain-specific data | Different domains have different field counts; avoids schema migrations |
| D2 | Domain configs as Python modules | Pydantic validation at import time; no YAML/TOML dependency |
| D3 | Dynamic Pydantic models via `create_model()` | OpenAI structured output requires Pydantic models as response_format |
| D4 | `ACTIVE_DOMAIN` env var | Simple config, consistent with existing env var pattern |
| D5 | Schema recreation (no migration) | Pre-v1.0, existing comment already says to delete and recreate |
| D6 | Second domain: product design concepts | Different enough to validate domain-agnosticism |

---

## Milestones

| Milestone | Tasks | File | Summary |
|-----------|-------|------|---------|
| 1 | 1–4 | [feature6-milestone1-domain-config.md](feature6-milestone1-domain-config.md) | Domain models, two built-in domains, registry, dynamic model factory |
| 2 | 5–6 | [feature6-milestone2-data-layer.md](feature6-milestone2-data-layer.md) | Schema migration to JSON storage, query layer refactor |
| 3 | 7–10 | [feature6-milestone3-service-layer.md](feature6-milestone3-service-layer.md) | Synthesizer, scorer, batch runner, CLI all domain-aware |
| 4 | 11–12 | [feature6-milestone4-ui-layer.md](feature6-milestone4-ui-layer.md) | Routes pass domain config to templates, templates render dynamically |
| 5 | 13–17 | [feature6-milestone5-testing-validation.md](feature6-milestone5-testing-validation.md) | All test files updated, full suite passes, lint/format clean |

---

## New Files to Create

- `src/domains/__init__.py` — Domain module init
- `src/domains/models.py` — Domain configuration Pydantic models + dynamic model factory
- `src/domains/registry.py` — Domain registry: loads domain configs, provides access by name
- `src/domains/sci_fi_concepts.py` — Built-in sci-fi book concepts domain definition
- `src/domains/product_design.py` — Built-in product design domain definition
- `tests/test_domains.py` — Tests for domain config loading and validation

---

## Acceptance Criteria

- [ ] Two domain configurations exist: `sci-fi-concepts` and `product-design`
- [ ] `ACTIVE_DOMAIN` env var selects which domain is active
- [ ] Synthesis uses domain-specific prompt and extraction fields
- [ ] Scoring uses domain-specific prompt and evaluation axes
- [ ] Database stores concept fields and score axes as JSON
- [ ] UI templates render extraction fields and score axes dynamically
- [ ] CLI runner supports `--domain` and `--list-domains` flags
- [ ] All validation commands pass with zero errors
- [ ] No regressions in existing test suite
- [ ] Adding a third domain requires only creating a new Python module and registering it
- [ ] Architectural boundaries preserved (domains module has no LLM imports)

---

## Validation Commands

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -v
uv run python scripts/run_conversation.py --list-domains
uv run python -c "from src.domains.registry import get_all_domains; [print(f'{d.name}: {len(d.extraction_fields)} fields, {len(d.scoring_axes)} axes') for d in get_all_domains()]"
```

---

## Notes

- **Breaking change**: Existing `data/yield_engine.db` must be deleted and recreated (pre-v1.0, consistent with existing schema comments)
- **Performance**: `overall_score` denormalized column mitigates JSON sort performance concern
- **Future extensibility**: Third domain = one new Python module + registry entry. Zero changes elsewhere.
