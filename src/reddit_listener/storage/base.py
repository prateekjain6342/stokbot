"""Abstract base class for token storage."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TokenData:
    """Stored token information."""

    access_token: str
    refresh_token: str
    expires_at: datetime
    scope: str


class TokenStore(ABC):
    """Abstract interface for storing and retrieving OAuth tokens."""

    @abstractmethod
    async def save_token(
        self, team_id: str, user_id: str, token_data: TokenData
    ) -> None:
        """Save or update a token for a user.

        Args:
            team_id: Slack team/workspace ID
            user_id: Slack user ID
            token_data: Token information to store
        """
        pass

    @abstractmethod
    async def get_token(self, team_id: str, user_id: str) -> Optional[TokenData]:
        """Retrieve a token for a user.

        Args:
            team_id: Slack team/workspace ID
            user_id: Slack user ID

        Returns:
            TokenData if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete_token(self, team_id: str, user_id: str) -> bool:
        """Delete a token for a user.

        Args:
            team_id: Slack team/workspace ID
            user_id: Slack user ID

        Returns:
            True if token was deleted, False if not found
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close any open connections/resources."""
        pass
