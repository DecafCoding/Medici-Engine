"""
Jacket copy generation for the Medici Engine.

Transforms a concept's raw premise into a polished back-cover blurb.
Supports two backends: the remote OpenAI API (default) and the local
Claude Code CLI. The active backend is selected via the
JACKET_COPY_PROVIDER environment variable. This module sits at the
same architectural level as synthesis and scoring.
"""

from src.config import settings
from src.jacket_copy.claude_cli_generator import ClaudeCliJacketCopyGenerator
from src.jacket_copy.generator import GenerationError, JacketCopyGenerator


def get_jacket_copy_generator() -> JacketCopyGenerator | ClaudeCliJacketCopyGenerator:
    """Return the configured jacket copy generator.

    Returns:
        ClaudeCliJacketCopyGenerator if JACKET_COPY_PROVIDER is 'claude-cli',
        otherwise JacketCopyGenerator (OpenAI API).
    """
    if settings.jacket_copy_provider == "claude-cli":
        return ClaudeCliJacketCopyGenerator()
    return JacketCopyGenerator()


__all__ = [
    "GenerationError",
    "get_jacket_copy_generator",
]
