"""Configuration management for Reddit Listener."""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class SlackConfig:
    """Slack-specific configuration."""

    app_token: str
    bot_token: str
    signing_secret: str


@dataclass
class RedditConfig:
    """Reddit API configuration."""

    client_id: str
    client_secret: str
    user_agent: str
    redirect_uri: str


@dataclass
class LLMConfig:
    """LLM API configuration."""

    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "minimax/minimax-m2.1"


@dataclass
class StorageConfig:
    """Storage configuration."""

    encryption_key: str
    database_path: str = "./data/tokens.db"


@dataclass
class Config:
    """Application configuration from environment variables."""

    # Slack
    slack_app_token: str
    slack_bot_token: str
    slack_signing_secret: str

    # Reddit
    reddit_client_id: str
    reddit_client_secret: str
    reddit_user_agent: str
    reddit_redirect_uri: str

    # OpenRouter
    openrouter_api_key: str
    openrouter_model: str = "minimax/minimax-m2.1"

    # Security
    encryption_key: str

    # Database
    database_path: str = "./data/tokens.db"

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables with validation."""
        missing = []

        # Required variables
        required_vars = {
            "SLACK_APP_TOKEN": "slack_app_token",
            "SLACK_BOT_TOKEN": "slack_bot_token",
            "SLACK_SIGNING_SECRET": "slack_signing_secret",
            "REDDIT_CLIENT_ID": "reddit_client_id",
            "REDDIT_CLIENT_SECRET": "reddit_client_secret",
            "REDDIT_USER_AGENT": "reddit_user_agent",
            "REDDIT_REDIRECT_URI": "reddit_redirect_uri",
            "OPENROUTER_API_KEY": "openrouter_api_key",
            "ENCRYPTION_KEY": "encryption_key",
        }

        config_values = {}
        for env_var, field_name in required_vars.items():
            value = os.getenv(env_var)
            if not value:
                missing.append(env_var)
            else:
                config_values[field_name] = value

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Please check your .env file or environment configuration."
            )

        # Optional variables with defaults
        config_values["database_path"] = os.getenv("DATABASE_PATH", "./data/tokens.db")
        config_values["openrouter_model"] = os.getenv("OPENROUTER_MODEL", "minimax/minimax-m2.1")

        # Validate encryption key format (should be hex string)
        encryption_key = config_values.get("encryption_key", "")
        if encryption_key:
            try:
                bytes.fromhex(encryption_key)
                if len(encryption_key) != 64:  # 32 bytes = 64 hex chars
                    raise ValueError("ENCRYPTION_KEY must be 64 hex characters (32 bytes)")
            except ValueError as e:
                raise ValueError(
                    f"Invalid ENCRYPTION_KEY format: {e}\n"
                    "Generate a valid key with: python -c \"import secrets; print(secrets.token_hex(32))\""
                ) from e

        return cls(**config_values)


# Global config instance (lazy loaded)
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config
