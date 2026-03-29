"""
Claude CLI jacket copy generator for the Medici Engine.

Takes a concept's raw premise and transforms it into a polished
back-cover blurb by shelling out to the Claude Code CLI. Uses
asyncio.create_subprocess_exec to remain non-blocking within the
async application. This module belongs to the Jacket Copy layer.
"""

import asyncio
import logging

from src.config import settings
from src.jacket_copy.generator import GenerationError
from src.jacket_copy.prompt import JACKET_COPY_PROMPT

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 120


class ClaudeCliJacketCopyGenerator:
    """Generates back-cover blurb text via the local Claude Code CLI.

    Shells out to `claude -p --model <model>` with the prompt on stdin.
    Uses asyncio.create_subprocess_exec so the call does not block the
    event loop. Raises GenerationError on CLI failure or empty output,
    matching the interface of JacketCopyGenerator.
    """

    def __init__(self) -> None:
        """Initialize the generator with the configured CLI model."""
        self._model = settings.claude_cli_model
        self._timeout = _DEFAULT_TIMEOUT

    async def generate(self, premise: str) -> str:
        """Generate a jacket copy from a concept premise via the Claude CLI.

        Args:
            premise: The raw premise text to expand into a jacket copy.

        Returns:
            The generated jacket copy text.

        Raises:
            GenerationError: If the CLI call fails, times out, or returns no content.
        """
        logger.info(
            "Generating jacket copy via Claude CLI",
            extra={"model": self._model, "premise_length": len(premise)},
        )

        # Combine system instructions and user premise into a single stdin prompt
        prompt = f"{JACKET_COPY_PROMPT}\n\n{premise}"

        try:
            proc = await asyncio.create_subprocess_exec(
                "claude",
                "-p",
                "--model",
                self._model,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=prompt.encode()),
                timeout=self._timeout,
            )
        except TimeoutError as e:
            raise GenerationError(
                f"Claude CLI timed out after {self._timeout}s"
            ) from e
        except FileNotFoundError as e:
            raise GenerationError("Claude CLI executable not found") from e

        if proc.returncode != 0:
            stderr = stderr_bytes.decode().strip()
            raise GenerationError(f"Claude CLI error: {stderr}")

        content = stdout_bytes.decode().strip()
        if not content:
            raise GenerationError("Claude CLI returned empty jacket copy")

        logger.info(
            "Jacket copy generated via Claude CLI",
            extra={"output_length": len(content)},
        )

        return content
