# Feature 3 — Milestone 2: Synthesizer Core

**Parent feature**: [feature3-synthesizer-agent.md](feature3-synthesizer-agent.md)
**Tasks**: 4
**Goal**: Implement the Synthesizer class with OpenAI API structured output integration
**Depends on**: Milestone 1 (synthesis models and DB queries must exist)

---

## CONTEXT REFERENCES

### Relevant Codebase Files — MUST READ BEFORE IMPLEMENTING

- `src/config.py` (lines 40-52) — Why: Already defines `openai_api_key`, `synthesis_model` ("gpt-4o"). Synthesizer must use these settings.
- `src/engine/conversation.py` (lines 36-55, 180-206) — Why: Shows the pattern for wrapping `AsyncOpenAI` client. Mirror this structure for the synthesizer's client setup (timeout, max_retries). Also shows error class pattern (`ConversationError`, `InferenceError`).
- `src/db/queries.py` — Why: `Turn` model is imported from here (NOT from `src/engine/`). The synthesis layer is above the engine in the hierarchy and must only import from the data layer.
- `.agents/DevPlan.md` (lines 54-62) — Why: Feature 3 definition and "done when" criteria.
- `.agents/Summary.md` (lines 53-63) — Why: Describes what the synthesizer should extract: transferable principles, unexpected reframings, novel compound concepts.
- `CLAUDE.md` (Architectural Boundaries table) — Why: Synthesis module communicates with OpenAI API only — no vLLM calls. Must not import from engine layer.

### Relevant Documentation

- [OpenAI Structured Outputs Guide](https://platform.openai.com/docs/guides/structured-outputs)
  - Section: Using with Pydantic models
  - Why: Core API pattern for the synthesizer's output parsing
- [OpenAI Python SDK - Structured Outputs](https://github.com/openai/openai-python#structured-outputs-parsing-helpers)
  - Section: `client.beta.chat.completions.parse()` usage
  - Why: Exact method signature and return type details

### New Files to Create

- `src/synthesis/synthesizer.py` — Synthesizer class with OpenAI API integration

### Patterns to Follow

**Client Initialization (from `src/engine/conversation.py:45-54`):**
```python
self._client = AsyncOpenAI(
    api_key=settings.openai_api_key,  # Remote API, not "unused"
    timeout=httpx.Timeout(60.0, connect=5.0),
    max_retries=3,
)
```

**Error Class Pattern (from `src/engine/conversation.py:28-33`):**
```python
class SynthesisError(Exception):
    """Raised when synthesis encounters a non-recoverable error."""

class ExtractionError(SynthesisError):
    """Raised when the OpenAI API fails to extract concepts."""
```

**Structured Output API Pattern (OpenAI SDK >= 1.60.0):**
```python
response = await self._client.beta.chat.completions.parse(
    model=settings.synthesis_model,
    messages=[...],
    response_format=ConceptExtraction,  # Pydantic class, not instance
    temperature=0.4,
)
result = response.choices[0].message.parsed
if result is None:
    refusal = response.choices[0].message.refusal
    raise ExtractionError(f"Model refused: {refusal}")
```

**Logging Pattern (from `src/engine/conversation.py`):**
```python
logger = logging.getLogger(__name__)
logger.info("Extracting concepts", extra={"run_id": str(run_id)})
```

---

## IMPLEMENTATION PLAN

### Task 4: Create the Synthesizer class

Build the core synthesis logic that calls the OpenAI API with structured output.

- **CREATE**: `src/synthesis/synthesizer.py` with:
  - `SynthesisError(Exception)` — base exception
  - `ExtractionError(SynthesisError)` — API failure
  - `Synthesizer` class:
    - `__init__`: Create `AsyncOpenAI` client with `api_key=settings.openai_api_key`, timeout, max_retries
    - `async def synthesize(self, transcript: list[Turn], persona_a_name: str, persona_b_name: str, shared_object_text: str) -> ConceptExtraction`:
      - Format the transcript into a readable string
      - Call `self._client.beta.chat.completions.parse()` with `response_format=ConceptExtraction`
      - Handle refusal (`.parsed is None`)
      - Handle API errors (`APIConnectionError`, `APIStatusError`, `APITimeoutError`)
      - Return the parsed `ConceptExtraction`
    - `def _format_transcript(self, transcript: list[Turn]) -> str` — convert Turn list to readable text
    - `def _build_messages(self, formatted_transcript: str, persona_a_name: str, persona_b_name: str, shared_object_text: str) -> list[dict[str, str]]` — system prompt + user message
  - System prompt constant `SYNTHESIS_PROMPT` — instructs the model to:
    - Read the full conversation transcript between two radically different personas
    - Identify the most interesting collision points: transferable principles, unexpected reframings, novel compound concepts
    - Extract a single structured concept (for the sci-fi domain): working title, core premise, what makes it original
    - Focus on ideas that neither persona would have produced alone — ideas that emerge from the gap
    - The concept should stand alone — readable without needing the transcript
- **PATTERN**: Mirror `ConversationRunner` structure in `src/engine/conversation.py` — same init pattern, same error handling approach, same logging
- **IMPORTS**: `import logging`, `import httpx`, `from openai import AsyncOpenAI, APIConnectionError, APIStatusError, APITimeoutError`, `from src.config import settings`, `from src.db.queries import Turn`, `from src.synthesis.models import ConceptExtraction`
- **GOTCHA**: Use `client.beta.chat.completions.parse()` NOT `client.chat.completions.create()` — the `parse()` method handles Pydantic serialization/deserialization automatically
- **GOTCHA**: Check `response.choices[0].message.parsed is None` for refusals before accessing the result
- **GOTCHA**: Use `temperature=0.4` for synthesis — lower than conversation (0.9) because we want consistent extraction, not creative generation
- **GOTCHA**: The synthesis module must NOT import from `src/engine/` — it is above the engine in the layer hierarchy. It imports `Turn` from `src/db/queries` (data layer, which is below synthesis)
- **GOTCHA**: Do NOT pass `temperature` to reasoning models (o3). For GPT-4o this is fine. The current synthesis model is GPT-4o so temperature is safe to use.
- **VALIDATE**: `uv run python -c "from src.synthesis.synthesizer import Synthesizer, SynthesisError, ExtractionError; print('Synthesizer imports OK')"`

---

## NOTES

**Synthesis prompt design is critical.** The prompt should NOT ask the model to summarize the conversation. It should instruct the model to find the collision points — moments where the two personas fundamentally talked past each other in interesting ways — and extract the novel idea that lives in the gap. The DevPlan and Summary are explicit: the synthesizer identifies "transferable principles, unexpected reframings, and novel compound concepts."

**Domain-specific output.** For the sci-fi domain (first application), the structured output is: working title, core premise, and what makes it original. The `ConceptExtraction` model encodes this. When Feature 6 (Domain Expansion) arrives, this model may become domain-configurable, but for now it's hardcoded for sci-fi.

**Structured output guarantees.** Using `client.beta.chat.completions.parse()` with a Pydantic model as `response_format` guarantees the API returns valid JSON matching the schema exactly. The SDK's strict mode ensures no missing fields and correct types. This means we don't need defensive JSON parsing — the `ConceptExtraction` model is always fully populated.

**Temperature trade-off.** Conversations use temperature 0.9 (creative generation). Synthesis should use lower temperature (~0.4) because we want consistent, accurate extraction — not creative reinterpretation of the transcript.

---

## VALIDATION CHECKPOINT

Before proceeding to Milestone 3, verify:

```bash
# Synthesizer imports cleanly
uv run python -c "from src.synthesis.synthesizer import Synthesizer, SynthesisError, ExtractionError; print('OK')"

# Verify synthesis prompt is defined and non-empty
uv run python -c "from src.synthesis.synthesizer import SYNTHESIS_PROMPT; assert len(SYNTHESIS_PROMPT) > 100; print(f'Prompt: {len(SYNTHESIS_PROMPT)} chars')"

# Lint passes
uv run ruff check src/synthesis/
uv run ruff format --check src/synthesis/
```

**Expected**: All commands pass with exit code 0
