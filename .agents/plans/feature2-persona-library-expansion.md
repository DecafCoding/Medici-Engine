# Feature 2 — Persona Library Expansion

The following plan should be complete, but validate documentation and codebase patterns before implementing. Pay special attention to naming of existing utils, types, and models. Import from the right files.

## Feature Description

Expand the persona library from 4 starter personas to the MVP target of 12 fully specified personas, and grow the shared object pool from 5 to 10+. The persona library is the single most important quality lever in the Medici Engine — shallow or generic personas produce shallow output regardless of how well everything else is built. This feature invests in persona depth and diversity to maximize the variance of creative collisions.

With 12 personas there are 66 unique pairings — more than enough to validate the system and identify which pairings are most generative. The focus is depth over quantity: each persona must be fully specified across all four dimensions (worldview, vocabulary style, core obsessions, characteristic way of seeing).

## User Story

As a creative researcher
I want a diverse library of 12 deeply specified personas spanning radically different epistemic frameworks
So that conversations produce high-variance creative collisions across many unique pairings

## Problem Statement

The current library has only 4 personas (6 unique pairings), which is too small to validate which pairings are generative or to run the system at meaningful scale. The shared object pool (5 objects) is similarly limited.

## Solution Statement

Add 8 new personas chosen to maximize conceptual distance from each other and the existing 4. Add 5+ new shared objects covering diverse types. Update tests to reflect the new minimums. No structural changes to models, selection logic, or the engine — this is purely a content and validation expansion.

## Feature Metadata

**Feature Type**: Enhancement
**Estimated Complexity**: Low-Medium
**Primary Systems Affected**: `src/personas/library.py`, `tests/test_personas.py`
**Dependencies**: None — Feature 1 is complete

---

## CONTEXT REFERENCES

### Relevant Codebase Files — MUST READ BEFORE IMPLEMENTING

- `src/personas/models.py` (lines 1-75) — Why: Defines the `Persona` and `SharedObject` Pydantic models with all required fields. Every new persona must conform to this schema.
- `src/personas/library.py` (lines 1-366) — Why: Contains the existing 4 personas (PERSONAS list) and 5 shared objects (SHARED_OBJECTS list), plus all selection logic. New entries are appended to these lists. Study the existing personas for tone, length, and specificity.
- `tests/test_personas.py` (lines 1-101) — Why: Contains the validation tests — minimum count checks, dimension length requirements, uniqueness checks, system prompt generation. The minimum count assertion on line 14 must be updated from 4 to 12.
- `tests/conftest.py` (lines 41-73) — Why: Contains test persona fixtures. These are intentionally short/minimal — do NOT change them. They serve a different purpose (test isolation) than the library personas.
- `tests/test_boundaries.py` (lines 1-80) — Why: Boundary tests verify no LLM imports in personas module. New personas must remain pure data — no imports added.
- `src/engine/conversation.py` (lines 208-263) — Why: Shows how personas are used — `to_system_prompt()` is called to build message history. Understanding this helps write personas that will produce good prompts.
- `CLAUDE.md` (Persona Library section) — Why: States "12 for MVP, 20-25 ideal" and the four-dimension specification requirement.
- `.agents/DevPlan.md` (lines 45-51) — Why: Feature 2 definition and done-when criteria.
- `.agents/Summary.md` (lines 31-43, 80-93) — Why: Explains the persona mechanism, high-variance pairing philosophy, and key techniques (asymmetric expertise gap, defamiliarization).

### New Files to Create

None. All changes go into existing files.

### Files to Modify

- `src/personas/library.py` — Add 8 personas to PERSONAS list, add 5+ shared objects to SHARED_OBJECTS list
- `tests/test_personas.py` — Update minimum persona count from 4 to 12, add shared object minimum check

### Patterns to Follow

**Persona Structure** (from existing personas in `library.py`):
```python
Persona(
    name="snake_case_identifier",          # Unique, descriptive, no spaces
    title=(                                 # Short phrase, starts with "A" or "An"
        "A [specific role] who [defining characteristic]"
    ),
    worldview=(                             # 3-6 sentences. How they understand reality.
        "..."                               # Must be specific, not generic.
    ),
    vocabulary_style=(                      # 3-6 sentences. Language patterns, jargon,
        "..."                               # catchphrases. Include a signature phrase.
    ),
    core_obsessions=(                       # 3-6 sentences. Questions they can't stop
        "..."                               # thinking about. Specific, not general.
    ),
    way_of_seeing=(                         # 3-6 sentences. How they perceive and
        "..."                               # interpret new information.
    ),
),
```

**Key constraints from existing personas:**
- Each dimension is 50+ characters (enforced by test on line 24-31 of `test_personas.py`)
- Multi-line strings use parenthesized string concatenation, NOT triple quotes
- Each string segment is indented to align and wrapped with explicit `" "` concatenation
- Names are `snake_case` identifiers (e.g., `quantum_information_theorist`, `medieval_master_builder`)
- Titles start with "A" or "An" and include a specific lens/obsession, not just a job title

**Shared Object Structure** (from existing objects in `library.py`):
```python
SharedObject(
    text=(
        "The scenario/question/problem text..."
    ),
    object_type="scenario",  # One of: scenario, question, problem, image_description
),
```

**Naming Convention**: `snake_case` for persona `name` field. Descriptive but concise — indicates the domain AND the specific angle (e.g., not `physicist` but `quantum_information_theorist`).

**String Style**: Parenthesized string concatenation with double quotes, line breaks at ~55-65 chars per segment, matching the existing persona formatting.

---

## IMPLEMENTATION PLAN

### Task 1: Design 8 new personas for maximum conceptual distance

Select 8 new personas that maximize epistemic diversity against the existing 4 (quantum physicist, medieval builder, jazz musician, deep-sea ecologist). The DevPlan and Summary emphasize the outsider advantage — pairings should create collisions between fundamentally different ways of knowing.

**Design criteria (from Summary.md):**
- Asymmetric expertise gaps — pair domains with completely different epistemologies
- Each persona must be deeply specific — not a job title but a worldview
- Four dimensions must be genuinely distinct across personas
- Vocabulary styles should produce noticeably different language

**Recommended 8 new personas** (chosen for maximum cross-domain variance):

1. **Forensic linguist** — someone who reads power, deception, and identity in word choice. Obsessed with what language reveals about the speaker, not the subject. Epistemic framework: textual/semiotic.
2. **Mycologist (fungal network researcher)** — thinks everything is a network, that the individual is an illusion, and that the real intelligence is in connections. Epistemic framework: ecological/systems.
3. **Hospice chaplain** — sits with people at the boundary of meaning-making. Obsessed with what becomes important when everything else falls away. Epistemic framework: existential/pastoral.
4. **Semiconductor fabrication engineer** — thinks at the nanometer scale about yield, contamination, and the gap between design intent and physical reality. Epistemic framework: precision engineering/manufacturing.
5. **Oral historian / griot** — knowledge lives in stories told person-to-person, not in written records. Obsessed with what gets remembered, what gets changed in the telling, and what gets lost. Epistemic framework: narrative/oral tradition.
6. **Supply chain logistics optimizer** — sees the world as flows, bottlenecks, and buffer stocks. Everything is a throughput problem. Epistemic framework: operational/quantitative.
7. **Restoration ecologist** — thinks about damaged systems and what it means to "restore" something that was never static. Obsessed with baselines, reference states, and whether you can go back. Epistemic framework: ecological/temporal.
8. **Circus aerialist / physical performer** — thinks in terms of momentum, commitment, and the instant between control and falling. Trusts the body's knowledge over the mind's theories. Epistemic framework: kinesthetic/embodied.

- **IMPLEMENT**: Write all 8 personas in the same format and depth as the existing 4 in `src/personas/library.py`
- **PATTERN**: Mirror the exact structure and string formatting of the existing personas (see `library.py:18-228`)
- **GOTCHA**: Each dimension text must be 50+ characters or the test on `test_personas.py:24-31` will fail
- **GOTCHA**: Names must be unique across all 12 — check against existing 4 names
- **GOTCHA**: Do NOT import anything new into `src/personas/library.py` — boundary tests will catch it
- **VALIDATE**: `uv run python -c "from src.personas.library import get_all_personas; ps = get_all_personas(); print(f'{len(ps)} personas'); assert len(ps) == 12"`

### Task 2: Add 5+ new shared objects to the pool

The current pool has 5 objects (3 scenarios, 1 question, 1 problem). Add at least 5 more to bring the total to 10+, covering all object types and providing more diverse collision seeds.

**Design criteria:**
- Objects should be concrete enough to provoke specific reactions but open enough for radically different interpretations
- Include at least one of each type: scenario, question, problem
- Avoid objects that are too domain-specific — they should be approachable from any persona's lens
- Should provoke genuine disagreement about what matters, not just different descriptions

- **IMPLEMENT**: Append 5+ new `SharedObject` entries to the `SHARED_OBJECTS` list in `src/personas/library.py`
- **PATTERN**: Match the existing shared object format (see `library.py:232-283`)
- **GOTCHA**: Each `text` field must be 20+ characters (enforced by `test_personas.py:99`)
- **GOTCHA**: `object_type` must be one of: `scenario`, `question`, `problem`, `image_description`
- **VALIDATE**: `uv run python -c "from src.personas.library import get_all_shared_objects; objs = get_all_shared_objects(); print(f'{len(objs)} objects'); assert len(objs) >= 10"`

### Task 3: Update test assertions for new library size

Update `tests/test_personas.py` to reflect the new minimum persona count (12) and shared object count (10).

- **UPDATE**: `tests/test_personas.py` line 14 — change `assert len(personas) >= 4` to `assert len(personas) >= 12`
- **UPDATE**: `tests/test_personas.py` line 92 — change `assert len(objects) >= 3` to `assert len(objects) >= 10`
- **GOTCHA**: Do NOT modify the test logic for dimension length checks or uniqueness — those still apply and will validate the new personas automatically
- **VALIDATE**: `uv run pytest tests/test_personas.py -v`

### Task 4: Run full test suite and lint

Verify nothing is broken across the entire project.

- **VALIDATE**: `uv run ruff check .`
- **VALIDATE**: `uv run ruff format --check .`
- **VALIDATE**: `uv run pytest -v`

---

## TESTING STRATEGY

### Unit Tests (existing, will auto-validate new content)

The existing `test_personas.py` tests are designed to scale with the library:

- `test_library_has_minimum_personas` — verifies count (update threshold to 12)
- `test_all_personas_fully_specified` — iterates ALL personas, checks all 4 dimensions are 50+ chars
- `test_persona_names_are_unique` — verifies no duplicate names across all personas
- `test_get_persona_pair_returns_two_distinct` — verifies pair selection with larger pool
- `test_get_persona_pair_avoids_recent` — verifies avoidance logic (auto-adapts to library size)
- `test_persona_generates_system_prompt` — verifies prompt generation (tests first persona, but pattern holds)
- `test_shared_objects_pool_not_empty` — update threshold to 10
- `test_get_random_shared_object_returns_valid` — validates object type enum

### Boundary Tests (existing, no changes needed)

- `test_personas_has_no_llm_imports` — ensures no openai imports sneak in
- `test_engine_does_not_use_remote_openai_api` — unaffected but run for regression
- `test_db_has_no_llm_imports` — unaffected but run for regression

### Edge Cases

- Pairing avoidance with 12 personas and 66 possible pairings — existing test covers this by marking all-but-one as recent
- System prompt generation for every new persona — the `to_system_prompt()` method is tested generically; each persona's fields are validated by the dimension check

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

```bash
# Lint (must pass with 0 errors)
uv run ruff check .

# Format check
uv run ruff format --check .
```

**Expected**: All commands pass with exit code 0

### Level 2: Persona-specific Tests

```bash
uv run pytest tests/test_personas.py -v
```

**Expected**: All persona tests pass, including updated minimum counts

### Level 3: Full Test Suite

```bash
uv run pytest -v
```

**Expected**: All tests pass. No regressions.

### Level 4: Manual Validation

```bash
# Verify persona count
uv run python -c "from src.personas.library import get_all_personas; print(f'{len(get_all_personas())} personas')"

# Verify shared object count
uv run python -c "from src.personas.library import get_all_shared_objects; print(f'{len(get_all_shared_objects())} shared objects')"

# Verify all persona names
uv run python -c "from src.personas.library import get_all_personas; [print(f'  {p.name}: {p.title}') for p in get_all_personas()]"

# Verify pair selection works with larger library
uv run python -c "from src.personas.library import get_persona_pair; a, b = get_persona_pair(); print(f'Pair: {a.name} + {b.name}')"

# Verify system prompts generate cleanly for all 12
uv run python -c "from src.personas.library import get_all_personas; [print(f'{p.name}: {len(p.to_system_prompt())} chars') for p in get_all_personas()]"
```

---

## ACCEPTANCE CRITERIA

- [ ] PERSONAS list contains exactly 12 fully specified personas
- [ ] SHARED_OBJECTS list contains at least 10 shared objects
- [ ] All 12 personas have all 4 dimensions filled with 50+ character text
- [ ] All persona names are unique snake_case identifiers
- [ ] New personas span radically different epistemic frameworks (not just different jobs)
- [ ] New shared objects cover scenario, question, and problem types
- [ ] `test_personas.py` minimum count updated to 12 personas and 10 shared objects
- [ ] `uv run ruff check .` passes with 0 errors
- [ ] `uv run ruff format --check .` passes with 0 errors
- [ ] `uv run pytest -v` passes with all tests green
- [ ] No new imports added to `src/personas/` (boundary tests pass)
- [ ] No changes to `src/personas/models.py`, `src/engine/`, `src/db/`, or `src/api/`

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully:
  - [ ] Level 1: ruff check, ruff format --check
  - [ ] Level 2: pytest tests/test_personas.py -v
  - [ ] Level 3: pytest -v (full suite)
  - [ ] Level 4: Manual validation
- [ ] Full test suite passes (all tests green)
- [ ] No linting errors
- [ ] No formatting errors
- [ ] All acceptance criteria met

---

## EXECUTION STRATEGY

**Recommended approach**: Whole Feature

**Rationale**: Low complexity, 4 tightly coupled tasks, minimal risk. Tasks 1-2 are content authoring into a single file. Task 3 is a two-line test update. Task 4 is final validation. No architectural changes, no new files, no new dependencies. The entire feature can be implemented and validated in a single pass.

---

## NOTES

**Persona quality is everything.** The DevPlan states: "12 deep personas beat 30 shallow ones." Each persona must feel like a real person with a specific lens on the world — not a Wikipedia summary of a profession. The test for quality: could you predict how this persona would react to any arbitrary shared object? If the answer is "vaguely" then the persona isn't specific enough.

**Maximizing conceptual distance.** The existing 4 personas cover: physics/information theory, medieval craft/engineering, music/improvisation, biology/ecology. New personas should NOT cluster in adjacent domains. A folklorist and a historian are too close. A folklorist and a semiconductor engineer are productively far apart.

**String formatting matters.** The codebase uses parenthesized string concatenation with explicit line breaks, NOT triple-quoted strings. Follow this pattern exactly to maintain consistent formatting across the file.

**Shared object design.** Good shared objects have an inherent tension or paradox that different epistemic frameworks will disagree about. "A building that teaches through structure alone" is good because an engineer, a musician, and a linguist will each interpret "teaches" fundamentally differently.
