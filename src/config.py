"""
Configuration management for Granzion Lab.
Loads settings from environment variables with validation.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, ConfigDict
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Application
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    debug: bool = Field(default=True, alias="DEBUG")
    
    # PostgreSQL
    postgres_host: str = Field(default="postgres", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="granzion_lab", alias="POSTGRES_DB")
    postgres_user: str = Field(default="granzion", alias="POSTGRES_USER")
    postgres_password: str = Field(default="changeme_in_production", alias="POSTGRES_PASSWORD")
    
    # Keycloak
    keycloak_host: str = Field(default="keycloak", alias="KEYCLOAK_HOST")
    keycloak_port: int = Field(default=8080, alias="KEYCLOAK_PORT")
    keycloak_realm: str = Field(default="granzion-lab", alias="KEYCLOAK_REALM")
    keycloak_admin: str = Field(default="admin", alias="KEYCLOAK_ADMIN")
    keycloak_admin_password: str = Field(default="admin_changeme", alias="KEYCLOAK_ADMIN_PASSWORD")
    keycloak_client_id: str = Field(default="granzion-lab-client", alias="KEYCLOAK_CLIENT_ID")
    keycloak_client_secret: str = Field(default="changeme_client_secret", alias="KEYCLOAK_CLIENT_SECRET")
    
    # LiteLLM
    # Can be either local (http://litellm:4000) or external cloud proxy
    litellm_url: str = Field(default="http://litellm:4000", alias="LITELLM_URL")
    litellm_api_key: str = Field(default="sk-1234567890abcdef", alias="LITELLM_API_KEY")
    
    # Default model to use (can be overridden per agent)
    # For cloud LiteLLM proxies, use the full model path (e.g., "openai/azure/gpt-4")
    # For local LiteLLM, use standard model names (e.g., "gpt-4", "claude-3-opus")
    default_model: str = Field(default="gpt-4", alias="DEFAULT_MODEL")
    
    # LLM Provider API Keys (only needed for local LiteLLM)
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    
    # PuppyGraph (official image: Web UI 8081, Gremlin 8182)
    puppygraph_host: str = Field(default="puppygraph", alias="PUPPYGRAPH_HOST")
    puppygraph_port: int = Field(default=8182, alias="PUPPYGRAPH_PORT")  # Gremlin endpoint (official image: 8182)
    puppygraph_web_port: int = Field(default=8081, alias="PUPPYGRAPH_WEB_PORT")  # Web UI (official image: 8081)
    
    # API & TUI
    tui_port: int = Field(default=8000, alias="TUI_PORT")
    api_port: int = Field(default=8001, alias="API_PORT")
    
    @property
    def postgres_url(self) -> str:
        """Construct PostgreSQL connection URL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    @property
    def keycloak_url(self) -> str:
        """Construct Keycloak base URL."""
        return f"http://{self.keycloak_host}:{self.keycloak_port}"
    
    @property
    def puppygraph_url(self) -> str:
        """Construct PuppyGraph Gremlin endpoint URL."""
        return f"ws://{self.puppygraph_host}:{self.puppygraph_port}/gremlin"
    
    @property
    def puppygraph_web_url(self) -> str:
        """Construct PuppyGraph web UI URL."""
        return f"http://{self.puppygraph_host}:{self.puppygraph_web_port}"
    
    @property
    def DEFAULT_MODEL(self) -> str:
        """Alias for default_model (for backward compatibility)."""
        return self.default_model
    
    @property
    def LITELLM_URL(self) -> str:
        """Alias for litellm_url (for backward compatibility)."""
        return self.litellm_url
    
    @property
    def LITELLM_API_KEY(self) -> str:
        """Alias for litellm_api_key (for backward compatibility)."""
        return self.litellm_api_key
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level is one of the standard levels."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
