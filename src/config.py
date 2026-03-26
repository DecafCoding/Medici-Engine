"""
Configuration module for the Medici Engine.

Loads all settings from environment variables via python-dotenv.
This is the single source of truth for configuration — no other
module should read os.getenv directly. This module is the lowest
layer in the dependency hierarchy.
"""

import logging

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# Load .env file from project root
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All configuration flows through this class. Values are read from
    environment variables with fallback defaults suitable for local
    development.
    """

    # Application server
    app_host: str = Field(
        default="127.0.0.1",
        description="Host address for the application server",
    )
    app_port: int = Field(
        default=8080,
        description="Port for the application server",
    )

    # vLLM local inference
    vllm_base_url: str = Field(
        default="http://localhost:8000/v1",
        description="Base URL for the local vLLM server",
    )
    conversation_model: str = Field(
        default="MythoMax-L2-13B",
        description="Model name served by vLLM",
    )

    # OpenAI API (not used in Feature 1)
    openai_api_key: str = Field(
        default="",
        description="API key for OpenAI (synthesis and scoring)",
    )
    synthesis_model: str = Field(
        default="gpt-4o",
        description="OpenAI model for synthesis",
    )
    scoring_model: str = Field(
        default="o3",
        description="OpenAI model for scoring",
    )

    # Domain
    active_domain: str = Field(
        default="sci-fi-concepts",
        description="Active domain configuration name",
    )

    # Database
    database_path: str = Field(
        default="data/yield_engine.db",
        description="Path to SQLite database file",
    )

    # Conversation defaults
    default_turns: int = Field(
        default=5,
        description="Default number of turns per agent",
    )

    # Inference parameters
    conversation_temperature: float = Field(
        default=0.9,
        description="Temperature for conversation generation",
    )
    conversation_repetition_penalty: float = Field(
        default=1.15,
        description="Repetition penalty for vLLM",
    )
    conversation_max_tokens: int = Field(
        default=512,
        description="Maximum tokens per conversation turn",
    )

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
