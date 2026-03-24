# Feature 6 — Milestone 1: Domain Configuration Foundation

**Tasks:** 1–4
**Goal:** Domain models, two built-in domains, registry, config integration, dynamic model factory
**Validation checkpoint:** Both domains load from registry, dynamic models produce valid JSON schemas, `ACTIVE_DOMAIN` setting exists

---

## Prerequisites

Read the parent plan for full context: [feature6-domain-expansion.md](feature6-domain-expansion.md)

### Relevant Codebase Files — MUST READ BEFORE IMPLEMENTING

- `src/config.py` (full file) — Why: Must add domain loading; currently has zero domain config
- `src/synthesis/synthesizer.py` (lines 27-59) — Why: `SYNTHESIS_PROMPT` to move into sci-fi domain config
- `src/scoring/scorer.py` (lines 27-58) — Why: `SCORING_PROMPT` to move into sci-fi domain config
- `src/scoring/models.py` (lines 13-25) — Why: `AxisScore` model reused by dynamic scoring models
- `.env.example` — Why: Must add `ACTIVE_DOMAIN` entry

### New Files to Create

- `src/domains/__init__.py` — Domain module init
- `src/domains/models.py` — Domain configuration Pydantic models + dynamic model factory
- `src/domains/registry.py` — Domain registry: loads domain configs, provides access by name
- `src/domains/sci_fi_concepts.py` — Built-in sci-fi book concepts domain definition
- `src/domains/product_design.py` — Built-in product design domain definition

### Relevant Documentation

- [Pydantic create_model](https://docs.pydantic.dev/latest/concepts/models/#dynamic-model-creation) — Why: `pydantic.create_model()` to build ConceptExtraction and ConceptScoring dynamically
- [OpenAI Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs) — Why: Dynamic models must satisfy structured output strict mode constraints

### Design Decisions (from parent plan)

- **D2**: Domain configs are Python modules with Pydantic models, not YAML/JSON files
- **D3**: Dynamic Pydantic models via `create_model()` for OpenAI structured output
- **D4**: `ACTIVE_DOMAIN` env var selects the active domain
- **D6**: Second domain is product design concepts

---

## IMPLEMENTATION TASKS

### Task 1: Domain Configuration Models

Create the domain configuration schema that all other tasks depend on.

- **CREATE** `src/domains/__init__.py` — empty init, module docstring
- **CREATE** `src/domains/models.py`:
  - `ExtractionField(BaseModel)`: `name: str`, `label: str`, `description: str`
  - `ScoringAxis(BaseModel)`: `name: str`, `label: str`, `description: str` (the axis definition; score/reasoning are always the same structure)
  - `DomainConfig(BaseModel)`: `name: str`, `label: str`, `description: str`, `extraction_fields: list[ExtractionField]`, `primary_field: str` (which extraction field to use as the primary label in list views, must be one of extraction_fields names), `scoring_axes: list[ScoringAxis]`, `synthesis_prompt: str`, `scoring_prompt: str`
  - Validator on DomainConfig: `primary_field` must exist in `extraction_fields` names
  - Validator: at least one extraction field and one scoring axis
- **VALIDATE**: `uv run python -c "from src.domains.models import DomainConfig; print('OK')"`

### Task 2: Built-in Domain Definitions

Define the two concrete domains.

- **CREATE** `src/domains/sci_fi_concepts.py`:
  - Define `SCI_FI_CONCEPTS` as a `DomainConfig` instance
  - Extraction fields: title, premise, originality (mirrors current hardcoded fields)
  - Scoring axes: uniqueness, plausibility, compelling_factor (mirrors current axes)
  - `primary_field`: "title"
  - Move `SYNTHESIS_PROMPT` from `src/synthesis/synthesizer.py` here
  - Move `SCORING_PROMPT` from `src/scoring/scorer.py` here
- **CREATE** `src/domains/product_design.py`:
  - Define `PRODUCT_DESIGN` as a `DomainConfig` instance
  - Extraction fields: `product_name` ("Product Name"), `value_proposition` ("Value Proposition"), `target_insight` ("Target Insight", description: "The non-obvious user need or behavior this product addresses")
  - Scoring axes: `novelty` ("Novelty", "How unprecedented is this product concept"), `feasibility` ("Feasibility", "Could this be built with current technology and reasonable resources"), `market_potential` ("Market Potential", "Is there a real audience that would pay for this")
  - `primary_field`: "product_name"
  - Write synthesis prompt tailored to product design extraction
  - Write scoring prompt tailored to product design evaluation
- **VALIDATE**: `uv run python -c "from src.domains.sci_fi_concepts import SCI_FI_CONCEPTS; from src.domains.product_design import PRODUCT_DESIGN; print(SCI_FI_CONCEPTS.name, PRODUCT_DESIGN.name)"`

### Task 3: Domain Registry and Config Integration

Build the registry and wire it into config.

- **CREATE** `src/domains/registry.py`:
  - `_DOMAINS: dict[str, DomainConfig]` — internal registry
  - `register_domain(config: DomainConfig) -> None` — add to registry
  - `get_domain(name: str) -> DomainConfig` — look up by name, raise `ValueError` if not found
  - `get_all_domains() -> list[DomainConfig]` — list all registered
  - `get_active_domain() -> DomainConfig` — shortcut that reads `settings.active_domain` and returns the config
  - Auto-register built-in domains on module import (import sci_fi_concepts and product_design at module level)
- **UPDATE** `src/config.py`:
  - Add `active_domain: str = Field(default="sci-fi-concepts", description="Active domain configuration name")`
- **UPDATE** `.env.example`:
  - Add `ACTIVE_DOMAIN=sci-fi-concepts` with comment
- **GOTCHA**: The domain registry must not import from `src/config` (circular import). `get_active_domain()` imports settings lazily or accepts the domain name as parameter.
- **VALIDATE**: `uv run python -c "from src.domains.registry import get_domain, get_all_domains; print([d.name for d in get_all_domains()])"`

### Task 4: Dynamic Pydantic Model Factory

Build the factory that creates OpenAI-compatible Pydantic models from domain config.

- **ADD** to `src/domains/models.py`:
  - `def create_extraction_model(domain: DomainConfig) -> type[BaseModel]` — uses `pydantic.create_model()` to build a model with fields from `domain.extraction_fields`. Each field is `(str, Field(description=field.description))`. Model name: `f"{domain.name.replace('-', '_')}_extraction"` in PascalCase.
  - `def create_scoring_model(domain: DomainConfig) -> type[BaseModel]` — builds a model with one `AxisScore` field per scoring axis. Each field is `(AxisScore, Field(description=axis.description))`. Reuse the existing `AxisScore` from `src/scoring/models.py`. Model name: similar pattern.
- **GOTCHA**: OpenAI structured output strict mode requires all fields to be required (no defaults). `create_model()` fields must be `(type, Field(...))` not `(type, Field(default=...))`.
- **GOTCHA**: `AxisScore` already has `axis`, `score`, `reasoning` fields — keep this model as-is. The scoring model has one AxisScore per axis name.
- **VALIDATE**: `uv run python -c "from src.domains.models import create_extraction_model, create_scoring_model; from src.domains.sci_fi_concepts import SCI_FI_CONCEPTS; E = create_extraction_model(SCI_FI_CONCEPTS); S = create_scoring_model(SCI_FI_CONCEPTS); print(E.model_json_schema()); print(S.model_json_schema())"`

---

## MILESTONE VALIDATION

```bash
# All four validations must pass
uv run python -c "from src.domains.models import DomainConfig; print('OK')"
uv run python -c "from src.domains.sci_fi_concepts import SCI_FI_CONCEPTS; from src.domains.product_design import PRODUCT_DESIGN; print(SCI_FI_CONCEPTS.name, PRODUCT_DESIGN.name)"
uv run python -c "from src.domains.registry import get_domain, get_all_domains; print([d.name for d in get_all_domains()])"
uv run python -c "from src.domains.models import create_extraction_model, create_scoring_model; from src.domains.sci_fi_concepts import SCI_FI_CONCEPTS; E = create_extraction_model(SCI_FI_CONCEPTS); S = create_scoring_model(SCI_FI_CONCEPTS); print(E.model_json_schema()); print(S.model_json_schema())"

# Lint must still pass
uv run ruff check .
uv run ruff format --check .
```
