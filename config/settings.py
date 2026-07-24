"""
Configuration settings for Game Master V3
"""
import os
from pathlib import Path
from typing import Optional

from pydantic import AliasChoices, Field
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
