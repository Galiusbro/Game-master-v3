"""
Configuration settings for Game Master V3
"""
import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_name: str = "Game Master V3"
    app_version: str = "3.0.0"
    app_host: str = Field(default="0.0.0.0", env="APP_HOST")
    app_port: int = Field(default=8000, env="APP_PORT")
    app_debug: bool = Field(default=True, env="APP_DEBUG")
    environment: str = Field(default="development", env="APP_ENVIRONMENT")
    
    # LLM Configuration
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    llm_model: str = Field(default="gpt-4.1-nano-2025-04-14", env="MAIN_MODEL")
    llm_max_tokens: int = Field(default=4000, env="LLM_MAX_TOKENS")
    llm_temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    
    # Graph Database (Neo4j)
    neo4j_uri: str = Field(default="bolt://localhost:7687", env="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", env="NEO4J_USER")
    neo4j_password: str = Field(default="gamemaster123", env="NEO4J_PASSWORD")
    neo4j_database: str = Field(default="neo4j", env="NEO4J_DATABASE")
    
    # Vector Database (Qdrant)
    qdrant_host: str = Field(default="localhost", env="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, env="QDRANT_PORT")
    qdrant_collection_name: str = Field(default="gamemaster_world", env="QDRANT_COLLECTION_NAME")
    
    # Cache (Redis)
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    
    # Operations Database (PostgreSQL)
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_db: str = Field(default="gamemaster", env="POSTGRES_DB")
    postgres_user: str = Field(default="gm_user", env="POSTGRES_USER")
    postgres_password: str = Field(default="gm_password", env="POSTGRES_PASSWORD")
    
    # Performance Settings
    context_max_tokens: int = Field(default=8000, env="CONTEXT_MAX_TOKENS")
    graph_traversal_max_depth: int = Field(default=3, env="GRAPH_TRAVERSAL_MAX_DEPTH")
    graph_traversal_max_width: int = Field(default=10, env="GRAPH_TRAVERSAL_MAX_WIDTH")
    cache_ttl_seconds: int = Field(default=3600, env="CACHE_TTL_SECONDS")
    
    # Security
    jwt_secret_key: str = Field(default="dev_secret_change_in_production", env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=60, env="JWT_EXPIRE_MINUTES")
    
    # Feature Flags
    enable_hallucination_detection: bool = Field(default=True, env="ENABLE_HALLUCINATION_DETECTION")
    enable_auto_rollback: bool = Field(default=True, env="ENABLE_AUTO_ROLLBACK")
    enable_monitoring: bool = Field(default=True, env="ENABLE_MONITORING")
    enable_cost_optimization: bool = Field(default=True, env="ENABLE_COST_OPTIMIZATION")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file_path: Optional[str] = Field(default="logs/gamemaster.log", env="LOG_FILE_PATH")
    
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