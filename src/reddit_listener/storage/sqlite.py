"""SQLite-based token storage with encryption."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiosqlite
from cryptography.fernet import Fernet

from .base import TokenData, TokenStore


class SQLiteTokenStore(TokenStore):
    """SQLite implementation of token storage with AES encryption."""

    def __init__(self, db_path: str, encryption_key: str):
        """Initialize SQLite token store.

        Args:
            db_path: Path to SQLite database file
            encryption_key: Hex-encoded encryption key (32 bytes = 64 hex chars)
        """
        self.db_path = db_path
        # Convert hex key to Fernet-compatible format
        key_bytes = bytes.fromhex(encryption_key)
        # Fernet requires base64-encoded 32-byte key
        import base64
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        self.cipher = Fernet(fernet_key)
        self._connection: Optional[aiosqlite.Connection] = None

    async def _get_connection(self) -> aiosqlite.Connection:
        """Get or create database connection."""
        if self._connection is None:
            # Ensure directory exists
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)

            self._connection = await aiosqlite.connect(self.db_path)
            await self._initialize_db()

        return self._connection

    async def _initialize_db(self) -> None:
        """Create tables if they don't exist."""
        if self._connection is None:
            raise RuntimeError("Database connection not established")

        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tokens (
                team_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                encrypted_data TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (team_id, user_id)
            )
            """
        )
        await self._connection.commit()

    def _encrypt(self, data: str) -> str:
        """Encrypt data."""
        return self.cipher.encrypt(data.encode()).decode()

    def _decrypt(self, encrypted_data: str) -> str:
        """Decrypt data."""
        return self.cipher.decrypt(encrypted_data.encode()).decode()

    async def save_token(
        self, team_id: str, user_id: str, token_data: TokenData
    ) -> None:
        """Save or update a token for a user."""
        conn = await self._get_connection()

        # Serialize token data to JSON
        data_dict = {
            "access_token": token_data.access_token,
            "refresh_token": token_data.refresh_token,
            "expires_at": token_data.expires_at.isoformat(),
            "scope": token_data.scope,
        }
        json_data = json.dumps(data_dict)

        # Encrypt the data
        encrypted_data = self._encrypt(json_data)

        # Save to database
        await conn.execute(
            """
            INSERT INTO tokens (team_id, user_id, encrypted_data, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(team_id, user_id) DO UPDATE SET
                encrypted_data = excluded.encrypted_data,
                updated_at = excluded.updated_at
            """,
            (team_id, user_id, encrypted_data, datetime.utcnow().isoformat()),
        )
        await conn.commit()

    async def get_token(self, team_id: str, user_id: str) -> Optional[TokenData]:
        """Retrieve a token for a user."""
        conn = await self._get_connection()

        cursor = await conn.execute(
            "SELECT encrypted_data FROM tokens WHERE team_id = ? AND user_id = ?",
            (team_id, user_id),
        )
        row = await cursor.fetchone()

        if not row:
            return None

        # Decrypt and deserialize
        encrypted_data = row[0]
        json_data = self._decrypt(encrypted_data)
        data_dict = json.loads(json_data)

        return TokenData(
            access_token=data_dict["access_token"],
            refresh_token=data_dict["refresh_token"],
            expires_at=datetime.fromisoformat(data_dict["expires_at"]),
            scope=data_dict["scope"],
        )

    async def delete_token(self, team_id: str, user_id: str) -> bool:
        """Delete a token for a user."""
        conn = await self._get_connection()

        cursor = await conn.execute(
            "DELETE FROM tokens WHERE team_id = ? AND user_id = ?",
            (team_id, user_id),
        )
        await conn.commit()

        return cursor.rowcount > 0

    async def close(self) -> None:
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
