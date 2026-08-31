"""
Configuration settings for Game Master V3
"""
import os
from pathlib import Path
from typing import Any, ClassVar, Optional

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    app_name: str = "Game Master V3"
    app_version: str = "3.0.0"
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    app_debug: bool = Field(default=True)
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("APP_ENVIRONMENT", "environment"),
    )

    # LLM Configuration
    openai_api_key: Optional[str] = Field(default=None)
    llm_model: str = Field(  # Better quality model
        default="gpt-4.1-nano",
        validation_alias=AliasChoices("MAIN_MODEL", "llm_model"),
    )
    llm_max_tokens: int = Field(default=8000)  # More tokens for quality
    # llm_temperature: float = Field(default=0.7)

    # LLM provider selection. Every supported provider speaks the OpenAI
    # protocol, so one client and one set of prompts serve all of them and
    # a provider differs only by key, base URL, model and a few request
    # parameters. "auto" picks the first configured provider in
    # LLM_PROVIDER_PRIORITY order.
    llm_provider: str = Field(default="auto")  # auto | openai | gemini | nvidia

    # Gemini through its OpenAI-compatible endpoint. A "lite" model on
    # purpose: the free tier meters requests per day per model, and the
    # full flash models allow only 20 — about a dozen game commands.
    gemini_api_key: Optional[str] = Field(default=None)
    gemini_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    gemini_model: str = Field(default="gemini-3.1-flash-lite")

    # NVIDIA's hosted inference, also OpenAI-compatible. Measured on a full
    # game command: nemotron 16-18s (occasionally 503), its lightning
    # variant 8-55s, and the hosted DeepSeek models ~19s after a 228s
    # warm-up — usable, but slower and less predictable than Gemini.
    nvidia_api_key: Optional[str] = Field(default=None)
    nvidia_base_url: str = Field(default="https://integrate.api.nvidia.com/v1")
    nvidia_model: str = Field(default="nvidia/nemotron-3-super-120b-a12b")

    # Consulted when llm_provider is "auto": the first one holding a key
    # wins. Gemini leads on measured latency for a full game command
    # (8-12s, against 8-55s for NVIDIA's fastest) and on consistency.
    LLM_PROVIDER_PRIORITY: ClassVar[tuple[str, ...]] = ("gemini", "nvidia", "openai")

    def _providers(self) -> dict[str, dict[str, Any]]:
        """Everything that distinguishes one provider from another.

        Adding a provider means adding an entry here plus its three
        settings fields — no changes anywhere in the AI service. Each entry
        supplies the key, the endpoint, the model and whatever request
        parameters that provider needs on every call.
        """
        return {
            "openai": {
                "key": self.openai_api_key,
                "base_url": None,  # the SDK's own default endpoint
                "model": self.llm_model,
                "extras": {},
            },
            "gemini": {
                "key": self.gemini_api_key,
                "base_url": self.gemini_base_url,
                "model": self.gemini_model,
                # Gemini 3.x reasons before answering; without this a small
                # token budget is spent entirely on reasoning and the reply
                # comes back empty.
                "extras": {"reasoning_effort": "none"},
            },
            "nvidia": {
                "key": self.nvidia_api_key,
                "base_url": self.nvidia_base_url,
                "model": self.nvidia_model,
                "extras": self._nvidia_extras(),
            },
        }

    def _nvidia_extras(self) -> dict[str, Any]:
        """Turn chain-of-thought off, in the spelling this model family uses.

        Same intent as Gemini's reasoning_effort. NVIDIA passes it through
        the chat template, and the flag is named per family: nemotron reads
        `enable_thinking`, deepseek reads `thinking`. A model that accepts
        neither is covered by the retry in AIService._create_completion.
        """
        flag = "enable_thinking" if "nemotron" in self.nvidia_model.lower() else "thinking"
        return {"extra_body": {"chat_template_kwargs": {flag: False}}}

    @model_validator(mode="after")
    def _resolve_llm_provider(self) -> "Settings":
        """Settle the provider once so model, key and base URL agree."""
        providers = self._providers()

        provider = self.llm_provider
        if provider == "auto":
            provider = next(
                (
                    name
                    for name in self.LLM_PROVIDER_PRIORITY
                    if providers.get(name, {}).get("key")
                ),
                "openai",
            )
        self.llm_provider = provider

        # llm_model is what the rest of the app reads, so point it at the
        # chosen provider's model. MAIN_MODEL configures the OpenAI
        # provider; the others each have their own *_MODEL setting.
        config = providers.get(provider, providers["openai"])
        self.llm_model = str(config["model"])

        return self

    @property
    def llm_api_key(self) -> Optional[str]:
        """API key for the provider in use."""
        key = self._providers()[self.llm_provider]["key"]
        return str(key) if key else None

    @property
    def llm_base_url(self) -> Optional[str]:
        """Base URL override; None means the OpenAI default endpoint."""
        base_url = self._providers()[self.llm_provider]["base_url"]
        return str(base_url) if base_url else None

    @property
    def llm_extra_params(self) -> dict[str, Any]:
        """Provider-specific request parameters applied to every completion."""
        extras: dict[str, Any] = self._providers()[self.llm_provider]["extras"]
        return extras

    # Graph Database (Neo4j)
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="gamemaster123")
    neo4j_database: str = Field(default="neo4j")

    # Vector Database (Qdrant)
    qdrant_host: str = Field(default="localhost")
    qdrant_port: int = Field(default=6333)
    qdrant_collection_name: str = Field(default="gamemaster_world")
    qdrant_docs_collection_name: str = Field(default="gamemaster_docs")

    # Cache (Redis)
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)

    # Operations Database (PostgreSQL)
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="gamemaster")
    postgres_user: str = Field(default="gm_user")
    postgres_password: str = Field(default="gm_password")

    # Performance Settings - OPTIMIZED FOR QUALITY
    context_max_tokens: int = Field(default=8000)  # Increased for quality
    graph_traversal_max_depth: int = Field(default=3)  # Deeper traversal
    graph_traversal_max_width: int = Field(default=15)  # More entities
    cache_ttl_seconds: int = Field(default=3600)

    # AI Optimization Settings - QUALITY FOCUSED
    ai_context_optimization: bool = Field(default=True)
    ai_max_context_entities: int = Field(default=20)  # More context

    # Security
    jwt_secret_key: str = Field(default="dev_secret_change_in_production")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=60)

    # Feature Flags
    enable_hallucination_detection: bool = Field(default=True)
    enable_auto_rollback: bool = Field(default=True)
    enable_monitoring: bool = Field(default=True)
    enable_cost_optimization: bool = Field(default=True)

    # Logging
    log_level: str = Field(default="INFO")
    log_file_path: Optional[str] = Field(default="logs/gamemaster.log")

    @property
    def postgres_url(self) -> str:
        """PostgreSQL connection URL"""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def redis_url(self) -> str:
        """Redis connection URL"""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env


# Global settings instance
settings = Settings()
