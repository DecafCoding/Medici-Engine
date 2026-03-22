# PBI 4: Conversation Engine

**Feature**: 1 — Core Conversation Engine
**Tasks**: 12–14 of 28
**Dependencies**: PBI 1 (config), PBI 3 (persona models)
**Estimated Complexity**: High — this is the core of Feature 1

---

## Objective

Build the conversation runner — the heart of the Medici Engine. The ConversationRunner takes two personas and a shared object, manages alternating turns via the local vLLM server (OpenAI-compatible API), and returns a complete transcript. This is the component that turns persona specifications into actual creative collisions.

## User Story

As a creative researcher
I want two AI personas to have a genuine multi-turn conversation about a shared object
So that productive friction and creative misunderstandings can emerge from their different worldviews

## Preconditions

- PBI 1 complete (`src/config.py` with vLLM settings)
- PBI 3 complete (`src/personas/models.py` with `Persona.to_system_prompt()`)
- `Turn` model available from `src/db/queries.py` (PBI 2)

## Context References — READ BEFORE IMPLEMENTING

- `CLAUDE.md` — Engine boundary: communicates with vLLM **only**, no Anthropic API imports
- `CLAUDE.md` — Async patterns: all I/O as `async`, never synchronous blocking
- `CLAUDE.md` — Error handling: custom exceptions, structured logging
- `.agents/DevPlan.md` (lines 35-43) — Feature 1 definition: two agents, shared object, fixed turns, transcripts logged
- `.agents/DevPlan.md` (lines 109-115) — Turn count: 5 per agent (10 total), configurable
- `.agents/DevPlan.md` (lines 139-151) — vLLM with OpenAI-compatible API, MythoMax-L2-13B, temperature 0.65-0.8, repetition penalty 1.05-1.2

### Technical Patterns

**vLLM via AsyncOpenAI**:
```python
client = AsyncOpenAI(base_url=settings.vllm_base_url, api_key="unused")
```

**repetition_penalty** is vLLM-specific — must use `extra_body`:
```python
response = await client.chat.completions.create(
    model=settings.conversation_model,
    messages=messages,
    temperature=0.9,
    max_tokens=512,
    extra_body={"repetition_penalty": 1.15},
)
```

**Error types** from the openai SDK:
- `APIConnectionError` — vLLM server down/unreachable
- `APITimeoutError` — request exceeded timeout
- `APIStatusError` — 4xx/5xx (bad model name, context overflow)

**Message construction**: Each turn is generated from the active persona's perspective. The system prompt is the persona's `to_system_prompt()`. Previous turns are replayed as `assistant` (own turns) and `user` (other persona's turns).

---

## TASKS

### Task 12: CREATE `src/engine/__init__.py`

- **IMPLEMENT**: Empty file (package marker).
- **VALIDATE**: `test -f src/engine/__init__.py && echo "exists"`

---

### Task 13: CREATE `src/engine/models.py`

Engine-layer Pydantic models for configuration and requests.

- **IMPLEMENT**:

```python
"""
Data models for the conversation engine.

Defines the structures used by the ConversationRunner to manage
turn-taking and produce transcripts. This module belongs to the
Engine layer.
"""

from pydantic import BaseModel, Field

from src.personas.models import Persona, SharedObject


class ConversationConfig(BaseModel):
    """Configuration for a single conversation run.

    Controls turn count and inference parameters. Defaults come
    from application settings but can be overridden per-run.
    """

    turns_per_agent: int = Field(default=5, description="Number of turns per agent")
    temperature: float = Field(default=0.9, description="Sampling temperature")
    repetition_penalty: float = Field(
        default=1.15, description="vLLM repetition penalty"
    )
    max_tokens: int = Field(default=512, description="Max tokens per turn")


class ConversationRequest(BaseModel):
    """Complete specification for a conversation run.

    Bundles the two personas, shared object, and generation config
    into a single request object.
    """

    persona_a: Persona
    persona_b: Persona
    shared_object: SharedObject
    config: ConversationConfig = Field(default_factory=ConversationConfig)
```

- **PATTERN**: Engine models hold config and request shape. The `Turn` model lives in `src/db/queries.py` — single definition, no duplication.
- **VALIDATE**: `uv run python -c "from src.engine.models import ConversationRequest; print('Engine models loaded')"`

---

### Task 14: CREATE `src/engine/conversation.py`

The core conversation runner.

- **IMPLEMENT**:

```python
"""
Conversation runner for the Medici Engine.

Manages turn-taking between two persona agents given a shared object,
producing a full conversation transcript. This module belongs to the
Engine layer and communicates with the local vLLM inference server
via an OpenAI-compatible API.
"""

import logging

import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
)

from src.config import settings
from src.db.queries import Turn
from src.engine.models import ConversationConfig, ConversationRequest
from src.personas.models import Persona, SharedObject

logger = logging.getLogger(__name__)


class ConversationError(Exception):
    """Raised when the conversation runner encounters a non-recoverable error."""


class InferenceError(ConversationError):
    """Raised when the local vLLM server fails to respond."""


class ConversationRunner:
    """Orchestrates a multi-turn conversation between two persona agents.

    Takes two fully specified personas and a shared object, manages
    turn-taking for a configurable number of exchanges, and returns
    the complete transcript. Communicates with the local inference
    server via the OpenAI-compatible client.
    """

    def __init__(self) -> None:
        """Initialize the conversation runner with a vLLM client."""
        # vLLM serves an OpenAI-compatible API, so we use the standard client
        # with a base_url override
        self._client = AsyncOpenAI(
            base_url=settings.vllm_base_url,
            api_key="unused",
            timeout=httpx.Timeout(120.0, connect=5.0),
            max_retries=2,
        )

    async def run(self, request: ConversationRequest) -> list[Turn]:
        """Run a full conversation between two personas on a shared object.

        Alternates turns between persona_a and persona_b, building up
        a shared message history. Each agent sees the full conversation
        so far from their own perspective.

        Args:
            request: Complete conversation specification including
                personas, shared object, and generation config.

        Returns:
            Ordered list of conversation turns.

        Raises:
            ConversationError: If the conversation cannot be completed.
            InferenceError: If the vLLM server fails to respond.
        """
        persona_a = request.persona_a
        persona_b = request.persona_b
        shared_object = request.shared_object
        config = request.config

        logger.info(
            "Starting conversation",
            extra={
                "persona_a": persona_a.name,
                "persona_b": persona_b.name,
                "shared_object_type": shared_object.object_type,
                "turns_per_agent": config.turns_per_agent,
            },
        )

        turns: list[Turn] = []
        total_turns = config.turns_per_agent * 2

        for turn_number in range(1, total_turns + 1):
            # Alternate between personas: odd turns = A, even turns = B
            is_persona_a = turn_number % 2 == 1
            active_persona = persona_a if is_persona_a else persona_b
            other_persona = persona_b if is_persona_a else persona_a

            try:
                content = await self._generate_turn(
                    active_persona=active_persona,
                    other_persona=other_persona,
                    shared_object=shared_object,
                    turns=turns,
                    turn_number=turn_number,
                    config=config,
                )
            except InferenceError:
                logger.error(
                    "Aborting conversation due to inference failure",
                    extra={
                        "turn_number": turn_number,
                        "persona": active_persona.name,
                    },
                )
                raise

            turn = Turn(
                turn_number=turn_number,
                persona_name=active_persona.name,
                content=content,
            )
            turns.append(turn)

            logger.debug(
                "Turn completed",
                extra={
                    "turn_number": turn_number,
                    "persona": active_persona.name,
                    "content_length": len(content),
                },
            )

        logger.info(
            "Conversation completed",
            extra={
                "persona_a": persona_a.name,
                "persona_b": persona_b.name,
                "total_turns": len(turns),
            },
        )

        return turns

    async def _generate_turn(
        self,
        active_persona: Persona,
        other_persona: Persona,
        shared_object: SharedObject,
        turns: list[Turn],
        turn_number: int,
        config: ConversationConfig,
    ) -> str:
        """Generate a single conversation turn from the vLLM server.

        Builds the message history from the active persona's perspective
        and calls the local inference server.

        Args:
            active_persona: The persona generating this turn.
            other_persona: The other persona in the conversation.
            shared_object: The shared object being discussed.
            turns: All previous turns in the conversation.
            turn_number: Current turn number (1-indexed).
            config: Generation parameters.

        Returns:
            The generated text content for this turn.

        Raises:
            InferenceError: If the vLLM server fails to respond.
        """
        messages = self._build_messages(
            active_persona=active_persona,
            other_persona=other_persona,
            shared_object=shared_object,
            turns=turns,
            turn_number=turn_number,
        )

        try:
            response = await self._client.chat.completions.create(
                model=settings.conversation_model,
                messages=messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                extra_body={"repetition_penalty": config.repetition_penalty},
            )
        except APIConnectionError as e:
            raise InferenceError(
                f"Cannot reach vLLM server at {settings.vllm_base_url}: {e}"
            ) from e
        except APITimeoutError as e:
            raise InferenceError(
                f"vLLM request timed out on turn {turn_number}: {e}"
            ) from e
        except APIStatusError as e:
            raise InferenceError(
                f"vLLM returned status {e.status_code} on turn {turn_number}: "
                f"{e.message}"
            ) from e

        content = response.choices[0].message.content
        if not content:
            raise InferenceError(
                f"vLLM returned empty content on turn {turn_number}"
            )

        return content.strip()

    def _build_messages(
        self,
        active_persona: Persona,
        other_persona: Persona,
        shared_object: SharedObject,
        turns: list[Turn],
        turn_number: int,
    ) -> list[dict[str, str]]:
        """Build the chat messages array for a turn.

        Constructs the message history from the active persona's
        perspective: their system prompt, the shared object as the
        opening user message, then alternating assistant/user roles
        for previous turns.

        Args:
            active_persona: The persona generating this turn.
            other_persona: The other persona in the conversation.
            shared_object: The shared object being discussed.
            turns: All previous turns in the conversation.
            turn_number: Current turn number.

        Returns:
            List of message dicts ready for the OpenAI chat API.
        """
        messages: list[dict[str, str]] = [
            {"role": "system", "content": active_persona.to_system_prompt()},
        ]

        # Opening context: present the shared object and conversation framing
        opening = (
            f"You are in a conversation with someone very different from you — "
            f"{other_persona.title}. You have both been presented with the following "
            f"and asked to react to it from your own perspective:\n\n"
            f"---\n{shared_object.text}\n---\n\n"
        )

        if turn_number == 1:
            # First turn: persona A reacts to the shared object
            opening += (
                "Give your initial reaction to this. What does it make you think of? "
                "What questions does it raise? Respond naturally as yourself."
            )
            messages.append({"role": "user", "content": opening})
        else:
            messages.append({"role": "user", "content": opening})

            # Replay conversation history with correct role mapping
            for turn in turns:
                if turn.persona_name == active_persona.name:
                    role = "assistant"
                else:
                    role = "user"
                messages.append({"role": role, "content": turn.content})

        return messages
```

- **PATTERN**: Engine imports only `AsyncOpenAI` — no Anthropic SDK. Custom exceptions defined in this module. `extra_body` for vLLM-specific params.
- **GOTCHA**: `repetition_penalty` must go through `extra_body`. Do NOT combine with `frequency_penalty`/`presence_penalty`. The `httpx` import is needed for `Timeout` configuration. Empty content check catches degenerate model responses.
- **VALIDATE**: `uv run python -c "from src.engine.conversation import ConversationRunner; print('ConversationRunner loaded')"`

---

## FILES CREATED

| File | Purpose |
|------|---------|
| `src/engine/__init__.py` | Package marker |
| `src/engine/models.py` | ConversationConfig, ConversationRequest |
| `src/engine/conversation.py` | ConversationRunner — turn-taking loop, vLLM communication |

## VALIDATION COMMANDS

```bash
# Modules import cleanly
uv run python -c "from src.engine.models import ConversationRequest; print('models ok')"
uv run python -c "from src.engine.conversation import ConversationRunner, InferenceError; print('engine ok')"

# Lint
uv run ruff check src/engine/
uv run ruff format --check src/engine/

# Verify no Anthropic imports (boundary check)
uv run python -c "
import ast
from pathlib import Path
for f in Path('src/engine').rglob('*.py'):
    tree = ast.parse(f.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert 'anthropic' not in alias.name, f'Boundary violation in {f}'
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert 'anthropic' not in node.module, f'Boundary violation in {f}'
print('No boundary violations in src/engine/')
"
```

## DONE WHEN

- [ ] `ConversationRunner` manages turn-taking between two personas
- [ ] Odd turns = persona_a, even turns = persona_b
- [ ] Message history builds correctly (system prompt + opening + replayed turns)
- [ ] Each persona sees the other's turns as `user` and their own as `assistant`
- [ ] `InferenceError` raised on connection failure, timeout, HTTP error, or empty response
- [ ] `repetition_penalty` passed via `extra_body` (not top-level kwarg)
- [ ] No `anthropic` imports in `src/engine/`
- [ ] Ruff passes on `src/engine/`

## KEY RISKS

- **Chat template mismatch**: MythoMax-L2-13B uses Llama 2 chat template. If vLLM doesn't apply it correctly, output will be garbled. Verify with `--chat-template` flag when launching vLLM.
- **Context window overflow**: 10 turns × 512 tokens + system prompts ≈ 6K tokens. MythoMax has 4K default context. Monitor for 400 errors and adjust `max_tokens` or `turns_per_agent` if needed.
- **Persona bleed**: Model may not maintain persona voice across all turns. Strong system prompts + repetition penalty help but this is an inherent model capability limit.
