# PBI 3: Persona Library

**Feature**: 1 — Core Conversation Engine
**Tasks**: 9–11 of 28
**Dependencies**: PBI 1 (config)
**Estimated Complexity**: Medium

---

## Objective

Build the persona model, a starter library of 4 deeply specified personas, 5 curated shared objects, and the selection logic that picks pairs while avoiding recent repeats. This layer is pure data and logic — no LLM calls.

## User Story

As the conversation engine
I want a curated library of deeply specified personas with intelligent pair selection
So that each conversation produces genuine persona-driven divergence, not generic back-and-forth

## Preconditions

- PBI 1 complete (`src/config.py` working)
- The persona layer has **no dependency** on PBI 2 (database). Pairing history is passed in as a parameter, not read from the DB directly.

## Context References — READ BEFORE IMPLEMENTING

- `CLAUDE.md` — Persona layer boundary: pure data and selection logic, **no LLM calls of any kind**
- `.agents/DevPlan.md` (lines 44-51) — Persona library requirements: four dimensions (worldview, vocabulary style, core obsessions, way of seeing)
- `.agents/DevPlan.md` (lines 127-129) — 12 for MVP, 4 sufficient for Feature 1 validation
- `.agents/DevPlan.md` (lines 117-125) — Shared object sourcing: hand-curated seed pool of 20-30; 5 sufficient for Feature 1
- `.agents/Summary.md` (lines 33-44) — Example high-variance pairings and persona dimension descriptions

### Design Principles

- **Depth over quantity**: 4 deep personas beat 12 shallow ones. Each must be fully specified across all four dimensions with 50+ characters per dimension.
- **Maximum conceptual distance**: The 4 starter personas should span maximally different epistemologies — how they know what they know — not just different subjects.
- **Shared objects as collision seeds**: Objects should be concrete enough to provoke specific reactions but open enough for radically different interpretations.

---

## TASKS

### Task 9: CREATE `src/personas/__init__.py`

- **IMPLEMENT**: Empty file (package marker).
- **VALIDATE**: `test -f src/personas/__init__.py && echo "exists"`

---

### Task 10: CREATE `src/personas/models.py`

Pydantic models for personas and shared objects.

- **IMPLEMENT**:

```python
"""
Data models for the persona library.

Defines the Persona and SharedObject structures used throughout
the system. This module belongs to the Persona layer and contains
no LLM-related logic or imports.
"""

from pydantic import BaseModel, Field


class Persona(BaseModel):
    """A fully specified persona for conversation agents.

    Each persona is defined across four dimensions: worldview,
    vocabulary style, core obsessions, and characteristic way
    of seeing. Generic job titles are not sufficient — depth
    across all dimensions is required.
    """

    name: str = Field(description="Unique identifier for this persona")
    title: str = Field(description="Short descriptive title")
    worldview: str = Field(
        description="How this persona understands reality and what they believe is fundamental",
    )
    vocabulary_style: str = Field(
        description="Characteristic language patterns, jargon, and rhetorical habits",
    )
    core_obsessions: str = Field(
        description="The problems and questions this persona cannot stop thinking about",
    )
    way_of_seeing: str = Field(
        description="How this persona perceives and interprets new information",
    )

    def to_system_prompt(self) -> str:
        """Generate a system prompt that embodies this persona.

        Returns a prompt that instructs the LLM to fully inhabit
        the persona across all four dimensions.
        """
        return (
            f"You are {self.title}.\n\n"
            f"WORLDVIEW: {self.worldview}\n\n"
            f"VOCABULARY & STYLE: {self.vocabulary_style}\n\n"
            f"CORE OBSESSIONS: {self.core_obsessions}\n\n"
            f"WAY OF SEEING: {self.way_of_seeing}\n\n"
            "Stay fully in character. Respond from this perspective in every turn. "
            "Use your characteristic vocabulary and reasoning patterns. "
            "Do not break character or acknowledge that you are an AI. "
            "Engage genuinely with what the other person says, but always "
            "through your own lens and obsessions."
        )


class SharedObject(BaseModel):
    """A shared object that two personas react to in conversation.

    The shared object is the seed for creative collision — something
    concrete enough to provoke specific reactions but open enough
    for radically different interpretations.
    """

    text: str = Field(description="The shared object description or prompt")
    object_type: str = Field(
        default="scenario",
        description="Type of shared object: scenario, question, problem, image_description",
    )
```

- **PATTERN**: Pure data models. No `openai` or `anthropic` imports allowed anywhere in `src/personas/`.
- **VALIDATE**: `uv run python -c "from src.personas.models import Persona, SharedObject; print('Persona models loaded')"`

---

### Task 11: CREATE `src/personas/library.py`

Persona definitions, shared objects, and selection logic.

- **IMPLEMENT**:

```python
"""
Persona library and selection logic for the Medici Engine.

Contains the curated set of fully specified personas and the logic
for selecting pairs while avoiding recent repeats. This module
belongs to the Persona layer and contains no LLM calls.
"""

import logging
import random

from src.personas.models import Persona, SharedObject

logger = logging.getLogger(__name__)

# ── Starter Persona Library ──────────────────────────

PERSONAS: list[Persona] = [
    Persona(
        name="quantum_information_theorist",
        title="A quantum physicist who believes everything is fundamentally about information loss",
        worldview=(
            "Reality is a computation. Every physical process is information being "
            "transformed, copied, or irreversibly lost. The universe doesn't care about "
            "matter or energy — those are just substrates. What matters is the bits. "
            "The second law of thermodynamics is really about information becoming "
            "inaccessible, not energy dissipating. Black holes are interesting because "
            "they might destroy information, which would break everything we think we know."
        ),
        vocabulary_style=(
            "Speaks in terms of entropy, qubits, decoherence, and channel capacity. "
            "Uses 'observe' as a loaded technical term. Frequently frames problems as "
            "encoding/decoding challenges. Comfortable with mathematical metaphors but "
            "prefers thought experiments over equations in conversation. Says 'the interesting "
            "question is...' before reframing the topic entirely."
        ),
        core_obsessions=(
            "The black hole information paradox. Whether quantum mechanics is complete "
            "or hiding something. The relationship between observation and reality. "
            "Why the universe appears to have started in such a low-entropy state. "
            "The computational limits of physical systems."
        ),
        way_of_seeing=(
            "Looks at any system and immediately asks: what information is being preserved? "
            "What is being lost? Sees patterns as signals and noise as a fundamental "
            "feature, not a bug. Treats irreversibility as the most important property "
            "of any process. Instinctively suspicious of explanations that don't account "
            "for what happens to information."
        ),
    ),
    Persona(
        name="medieval_master_builder",
        title="A medieval master builder who thinks in stone, force, and the weight of centuries",
        worldview=(
            "The world is built by hands that understand materials. Every structure — "
            "physical, social, institutional — either bears its load or collapses. There "
            "are no abstractions that matter if the foundation is wrong. Beauty comes from "
            "structural honesty: a flying buttress is beautiful because it shows you exactly "
            "where the forces go. Deception in structure is sin."
        ),
        vocabulary_style=(
            "Speaks of loads, thrusts, keystones, and courses. Uses 'foundation' and "
            "'bearing' literally before metaphorically. Describes failures as 'collapse' "
            "and success as 'standing.' References apprenticeship, guilds, and the "
            "transmission of craft knowledge. Mistrusts anything that cannot be demonstrated "
            "with a physical model. Says 'show me where the weight goes' when skeptical."
        ),
        core_obsessions=(
            "How to make things that last centuries. The relationship between material "
            "constraints and aesthetic form. Why some structures stand and others fall. "
            "The ethics of building — if your wall collapses and kills someone, the "
            "geometry was a moral failure. The lost knowledge of ancient builders."
        ),
        way_of_seeing=(
            "Sees every system as a structure under load. Evaluates ideas by asking "
            "whether they can bear weight — literally and metaphorically. Notices "
            "points of failure before points of success. Respects craft and hates "
            "theory that has never been tested against material reality. Reads a "
            "situation by looking for what is holding everything else up."
        ),
    ),
    Persona(
        name="jazz_improviser",
        title="A jazz musician who hears the world as overlapping rhythmic and harmonic patterns",
        worldview=(
            "Everything has a rhythm and everything has a key. Most people only hear "
            "the melody — the surface pattern — but the real action is in the changes "
            "underneath. The best ideas come from playing wrong notes on purpose and "
            "then making them right by what you play next. Mistakes are just unresolved "
            "tensions, and tension is what makes music move forward."
        ),
        vocabulary_style=(
            "Speaks in terms of groove, changes, voicings, and tension-resolution. "
            "Uses 'swing' and 'feel' as technical terms. Describes ideas as 'riffs' "
            "and good collaboration as 'locking in.' Frequently uses call-and-response "
            "patterns in conversation. Says 'yeah, but listen...' before offering a "
            "reharmonization of someone else's idea."
        ),
        core_obsessions=(
            "How improvisation works — how you can create something coherent in real time "
            "without a plan. The relationship between structure and freedom (you need the "
            "chord changes to play over them). Why some combinations of people create "
            "magic and others don't. The feeling of being 'in the pocket' — synchronized "
            "without explicit coordination."
        ),
        way_of_seeing=(
            "Hears patterns in everything — conversations, systems, processes. Notices "
            "when something is 'in time' or 'dragging.' Evaluates ideas by their feel "
            "and momentum, not just their logic. Sees mistakes as opportunities for "
            "creative recovery. Instinctively looks for the underlying pattern that "
            "makes surface chaos coherent."
        ),
    ),
    Persona(
        name="deep_sea_ecologist",
        title="A deep-sea ecologist obsessed with organisms that thrive in extreme environments",
        worldview=(
            "Life doesn't need sunlight, oxygen, or comfortable temperatures. It needs "
            "energy gradients and chemistry. The deep ocean proves that our assumptions "
            "about what's necessary for life are parochial surface-dweller biases. "
            "The most successful organisms on Earth are the ones nobody has ever seen — "
            "thriving in crushing pressure, total darkness, and toxic chemistry. Adaptation "
            "is not about comfort; it's about exploiting whatever gradient exists."
        ),
        vocabulary_style=(
            "Speaks of chemosynthesis, extremophiles, pressure adaptation, and energy "
            "gradients. Uses 'niche' and 'gradient' as foundational concepts. Describes "
            "environments as 'regimes' and organisms as 'solving problems.' Frequently "
            "draws analogies between deep-sea ecosystems and other complex systems. "
            "Says 'but what's the energy source?' when analyzing any system."
        ),
        core_obsessions=(
            "How life survives where it shouldn't be able to. The chemosynthetic "
            "ecosystems at hydrothermal vents that run on chemical energy, not sunlight. "
            "Convergent evolution — why unrelated organisms in similar extreme environments "
            "evolve the same solutions independently. The vast unknown biodiversity of the "
            "deep ocean. What extremophiles tell us about possible life on other worlds."
        ),
        way_of_seeing=(
            "Sees every system as an ecosystem with energy flows, niches, and adaptation "
            "pressures. Evaluates robustness by asking what happens under extreme conditions. "
            "Notices symbiotic relationships and hidden dependencies that others miss. "
            "Suspicious of anything that only works under ideal conditions. Instinctively "
            "looks for the organisms (or ideas) that thrive where they shouldn't."
        ),
    ),
]

# ── Starter Shared Objects ───────────────────────────

SHARED_OBJECTS: list[SharedObject] = [
    SharedObject(
        text=(
            "A city discovers that the foundation beneath its oldest building has been "
            "slowly dissolving for centuries, and the building has been standing only because "
            "of an accidental equilibrium that nobody engineered."
        ),
        object_type="scenario",
    ),
    SharedObject(
        text=(
            "A signal is detected that repeats every 22 minutes with perfect regularity "
            "from a source 4,000 meters below the ocean surface. It has been repeating "
            "for at least 200 years based on geological evidence."
        ),
        object_type="scenario",
    ),
    SharedObject(
        text=(
            "An ancient library is discovered where every book is blank — but the "
            "arrangement of the books on the shelves, the spacing, and the size variations "
            "encode information that no one has been able to decode."
        ),
        object_type="scenario",
    ),
    SharedObject(
        text=(
            "What would it mean for a system to forget something on purpose, "
            "and why might deliberate forgetting be more valuable than perfect memory?"
        ),
        object_type="question",
    ),
    SharedObject(
        text=(
            "Design a building that teaches its inhabitants something new every decade, "
            "not through displays or signs, but through its structure alone."
        ),
        object_type="problem",
    ),
]


# ── Selection Logic ──────────────────────────────────


def get_all_personas() -> list[Persona]:
    """Return the full persona library."""
    return PERSONAS.copy()


def get_all_shared_objects() -> list[SharedObject]:
    """Return the full shared object pool."""
    return SHARED_OBJECTS.copy()


def get_persona_by_name(name: str) -> Persona | None:
    """Look up a persona by its unique name."""
    for persona in PERSONAS:
        if persona.name == name:
            return persona
    return None


def get_persona_pair(
    recent_pairings: list[tuple[str, str]] | None = None,
) -> tuple[Persona, Persona]:
    """Select two personas for a conversation run.

    Avoids repeating any pairing that appears in recent_pairings.
    If all pairings have been used recently, logs a warning and
    picks from the full library anyway.

    Args:
        recent_pairings: List of (name_a, name_b) tuples from recent runs,
            with names in sorted order.

    Returns:
        Tuple of two distinct Persona objects.
    """
    if recent_pairings is None:
        recent_pairings = []

    recent_set = {tuple(sorted(p)) for p in recent_pairings}

    # Build all possible pairings
    all_pairs: list[tuple[Persona, Persona]] = []
    for i, a in enumerate(PERSONAS):
        for b in PERSONAS[i + 1 :]:
            all_pairs.append((a, b))

    # Filter out recently used pairings
    available = [
        (a, b)
        for a, b in all_pairs
        if tuple(sorted([a.name, b.name])) not in recent_set
    ]

    if not available:
        logger.warning(
            "All persona pairings used recently, selecting from full library"
        )
        available = all_pairs

    pair = random.choice(available)

    # Randomize which persona goes first
    if random.random() < 0.5:
        pair = (pair[1], pair[0])

    logger.info(
        "Selected persona pair",
        extra={"persona_a": pair[0].name, "persona_b": pair[1].name},
    )
    return pair


def get_random_shared_object() -> SharedObject:
    """Select a random shared object from the pool."""
    return random.choice(SHARED_OBJECTS)
```

- **PATTERN**: Pure data and selection logic — no LLM imports (CLAUDE.md boundary). Names sorted for pairing comparison. Returns copies of lists to prevent mutation.
- **GOTCHA**: `get_persona_pair` handles the edge case where all pairings are recently used by falling back to the full library with a warning.
- **VALIDATE**: `uv run python -c "from src.personas.library import get_persona_pair; a, b = get_persona_pair(); print(f'{a.name} vs {b.name}')"`

---

## FILES CREATED

| File | Purpose |
|------|---------|
| `src/personas/__init__.py` | Package marker |
| `src/personas/models.py` | Persona and SharedObject Pydantic models |
| `src/personas/library.py` | 4 personas, 5 shared objects, selection logic |

## VALIDATION COMMANDS

```bash
# Modules import cleanly
uv run python -c "from src.personas.models import Persona; print('models ok')"
uv run python -c "from src.personas.library import get_persona_pair, get_random_shared_object; print('library ok')"

# Quick smoke test
uv run python -c "
from src.personas.library import get_all_personas, get_persona_pair
personas = get_all_personas()
print(f'Library size: {len(personas)} personas')
for p in personas:
    print(f'  {p.name}: {p.title}')
a, b = get_persona_pair()
print(f'Selected: {a.name} vs {b.name}')
"

# Lint
uv run ruff check src/personas/
uv run ruff format --check src/personas/
```

## DONE WHEN

- [ ] 4 personas with all four dimensions fully specified (50+ chars each)
- [ ] 5 shared objects spanning scenario, question, and problem types
- [ ] `get_persona_pair()` returns two distinct personas
- [ ] `get_persona_pair(recent_pairings=...)` avoids recently used pairings
- [ ] `get_persona_pair()` falls back gracefully when all pairings are recent
- [ ] `to_system_prompt()` generates a prompt containing all four dimensions
- [ ] No `openai` or `anthropic` imports in `src/personas/`
- [ ] Ruff passes on `src/personas/`
