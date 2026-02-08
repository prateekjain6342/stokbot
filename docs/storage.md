# Storage

Token storage system with encryption for secure OAuth credential management.

## Overview

**Location:** `src/reddit_listener/storage/`

Provides secure, encrypted storage for OAuth tokens with support for multiple backends.

## Architecture

### Abstract Interface

**File:** `base.py`

```python
from abc import ABC, abstractmethod
from typing import Optional

class TokenStorage(ABC):
    """Abstract interface for token storage"""
    
    @abstractmethod
    async def store_token(self, user_id: str, token_data: dict) -> None:
        """Store encrypted token for user"""
        pass
    
    @abstractmethod
    async def get_token(self, user_id: str) -> Optional[dict]:
        """Retrieve and decrypt token for user"""
        pass
    
    @abstractmethod
    async def delete_token(self, user_id: str) -> None:
        """Delete token for user"""
        pass
    
    @abstractmethod
    async def has_token(self, user_id: str) -> bool:
        """Check if token exists for user"""
        pass
```

### SQLite Implementation

**File:** `sqlite.py`

Current implementation using SQLite with AES-256 encryption.

#### Schema

```sql
CREATE TABLE IF NOT EXISTS tokens (
    user_id TEXT PRIMARY KEY,
    encrypted_data BLOB NOT NULL,
    iv BLOB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_id ON tokens(user_id);
```

#### Implementation

```python
import aiosqlite
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os
import json

class SQLiteTokenStorage(TokenStorage):
    def __init__(self, db_path: str, encryption_key: bytes):
        self.db_path = db_path
        self.encryption_key = encryption_key
    
    async def initialize(self):
        """Create database and tables"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    user_id TEXT PRIMARY KEY,
                    encrypted_data BLOB NOT NULL,
                    iv BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
    
    async def store_token(self, user_id: str, token_data: dict) -> None:
        """Encrypt and store token"""
        # Serialize token data
        token_json = json.dumps(token_data)
        
        # Encrypt
        iv = os.urandom(16)
        cipher = Cipher(
            algorithms.AES(self.encryption_key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Pad data to block size
        padded_data = self._pad(token_json.encode())
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        
        # Store
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO tokens (user_id, encrypted_data, iv, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, encrypted_data, iv))
            await db.commit()
    
    async def get_token(self, user_id: str) -> Optional[dict]:
        """Retrieve and decrypt token"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT encrypted_data, iv FROM tokens WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                
                if not row:
                    return None
                
                encrypted_data, iv = row
                
                # Decrypt
                cipher = Cipher(
                    algorithms.AES(self.encryption_key),
                    modes.CBC(iv),
                    backend=default_backend()
                )
                decryptor = cipher.decryptor()
                
                decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()
                unpadded_data = self._unpad(decrypted_data)
                
                # Deserialize
                return json.loads(unpadded_data.decode())
    
    async def delete_token(self, user_id: str) -> None:
        """Delete token"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM tokens WHERE user_id = ?", (user_id,))
            await db.commit()
    
    async def has_token(self, user_id: str) -> bool:
        """Check if token exists"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT 1 FROM tokens WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row is not None
    
    @staticmethod
    def _pad(data: bytes) -> bytes:
        """PKCS7 padding"""
        padding_length = 16 - (len(data) % 16)
        return data + bytes([padding_length] * padding_length)
    
    @staticmethod
    def _unpad(data: bytes) -> bytes:
        """Remove PKCS7 padding"""
        padding_length = data[-1]
        return data[:-padding_length]
```

## Encryption Details

### Algorithm

**AES-256 in CBC Mode:**
- **Key size:** 256 bits (32 bytes)
- **Block size:** 128 bits (16 bytes)
- **Mode:** CBC (Cipher Block Chaining)
- **Padding:** PKCS7

### Key Generation

```python
import secrets

# Generate encryption key (do this once, store in .env)
encryption_key = secrets.token_hex(32)  # 64 hex chars = 32 bytes
print(f"ENCRYPTION_KEY={encryption_key}")
```

### Key Derivation (Alternative)

If deriving from passphrase:

```python
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import os

def derive_key(passphrase: str, salt: bytes = None) -> tuple[bytes, bytes]:
    """Derive encryption key from passphrase"""
    if salt is None:
        salt = os.urandom(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    
    key = kdf.derive(passphrase.encode())
    return key, salt
```

### Initialization Vector (IV)

- **Generated:** Fresh random IV for each encryption
- **Storage:** Stored alongside encrypted data
- **Purpose:** Ensures same plaintext encrypts differently each time

## Token Data Structure

### Reddit OAuth Token

```python
{
    "access_token": "abc123...",
    "refresh_token": "xyz789...",
    "expires_at": 1234567890,  # Unix timestamp
    "scope": "read submit",
    "token_type": "bearer"
}
```

### Storage Flow

```
Token Data (JSON)
    ↓
Serialize to string
    ↓
Encode to bytes
    ↓
Pad to block size (PKCS7)
    ↓
Generate random IV
    ↓
Encrypt with AES-256-CBC
    ↓
Store encrypted data + IV
```

### Retrieval Flow

```
Retrieve encrypted data + IV
    ↓
Decrypt with AES-256-CBC
    ↓
Remove padding (PKCS7)
    ↓
Decode to string
    ↓
Parse JSON
    ↓
Return token data
```

## DynamoDB Implementation (Planned)

**File:** `dynamodb.py` (future)

### Schema

```python
Table: reddit_listener_tokens

Partition Key: user_id (String)
Attributes:
  - encrypted_data (Binary)
  - iv (Binary)
  - created_at (Number) - Unix timestamp
  - updated_at (Number) - Unix timestamp
  - ttl (Number) - Auto-expire old tokens

Indexes:
  - None needed (partition key is unique)
```

### Implementation Outline

```python
import boto3
from boto3.dynamodb.conditions import Key

class DynamoDBTokenStorage(TokenStorage):
    def __init__(self, table_name: str, encryption_key: bytes):
        self.table_name = table_name
        self.encryption_key = encryption_key
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)
    
    async def store_token(self, user_id: str, token_data: dict) -> None:
        # Similar encryption logic
        # Use table.put_item()
        pass
    
    async def get_token(self, user_id: str) -> Optional[dict]:
        # Use table.get_item()
        # Similar decryption logic
        pass
```

## Security Best Practices

### Key Management

1. **Generate strong keys:** Use `secrets.token_hex(32)`
2. **Store securely:** Environment variables, never commit
3. **Rotate regularly:** Implement key rotation strategy
4. **Backup safely:** Encrypted backups only

### Access Control

1. **Principle of least privilege:** Only authorized code can access storage
2. **Audit logging:** Log all token access (without exposing data)
3. **Rate limiting:** Prevent brute force attacks
4. **Secure deletion:** Overwrite data before deleting

### Encryption Best Practices

1. **Random IVs:** Never reuse IVs
2. **Authenticated encryption:** Consider AES-GCM for AEAD
3. **Secure padding:** PKCS7 prevents padding oracle attacks
4. **Key derivation:** Use strong KDF if deriving from passphrase

## Error Handling

### Common Errors

```python
class StorageError(Exception):
    """Base storage error"""
    pass

class EncryptionError(StorageError):
    """Encryption/decryption failed"""
    pass

class DatabaseError(StorageError):
    """Database operation failed"""
    pass

# Usage
try:
    await storage.store_token(user_id, token_data)
except EncryptionError as e:
    logger.error(f"Encryption failed: {e}")
    raise
except DatabaseError as e:
    logger.error(f"Database error: {e}")
    raise
```

### Graceful Degradation

```python
async def get_token_with_fallback(user_id: str) -> Optional[dict]:
    """Try to get token, handle corruption gracefully"""
    try:
        return await storage.get_token(user_id)
    except EncryptionError:
        logger.warning(f"Corrupted token for user {user_id}, deleting")
        await storage.delete_token(user_id)
        return None
```

## Testing

### Unit Tests

```python
import pytest
from reddit_listener.storage.sqlite import SQLiteTokenStorage

@pytest.fixture
async def storage():
    key = os.urandom(32)
    storage = SQLiteTokenStorage(":memory:", key)
    await storage.initialize()
    return storage

@pytest.mark.asyncio
async def test_store_and_retrieve(storage):
    token_data = {"access_token": "test123"}
    
    await storage.store_token("user1", token_data)
    retrieved = await storage.get_token("user1")
    
    assert retrieved == token_data

@pytest.mark.asyncio
async def test_delete_token(storage):
    await storage.store_token("user1", {"token": "test"})
    await storage.delete_token("user1")
    
    assert not await storage.has_token("user1")
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_token_encryption():
    """Ensure tokens are actually encrypted on disk"""
    key = os.urandom(32)
    storage = SQLiteTokenStorage("test.db", key)
    await storage.initialize()
    
    token_data = {"access_token": "sensitive_data"}
    await storage.store_token("user1", token_data)
    
    # Read raw database
    async with aiosqlite.connect("test.db") as db:
        async with db.execute(
            "SELECT encrypted_data FROM tokens WHERE user_id = ?",
            ("user1",)
        ) as cursor:
            row = await cursor.fetchone()
            encrypted = row[0]
    
    # Verify data is actually encrypted
    assert b"sensitive_data" not in encrypted
```

## Migration Strategy

### SQLite to DynamoDB

```python
async def migrate_tokens(
    source: SQLiteTokenStorage,
    dest: DynamoDBTokenStorage
):
    """Migrate tokens from SQLite to DynamoDB"""
    async with aiosqlite.connect(source.db_path) as db:
        async with db.execute("SELECT user_id FROM tokens") as cursor:
            async for row in cursor:
                user_id = row[0]
                token_data = await source.get_token(user_id)
                await dest.store_token(user_id, token_data)
                logger.info(f"Migrated token for user {user_id}")
```

## Performance

### SQLite

- **Read latency:** <1ms
- **Write latency:** <5ms
- **Concurrent reads:** Excellent
- **Concurrent writes:** Serialized (sqlite limitation)
- **Suitable for:** Single instance deployments

### DynamoDB (Planned)

- **Read latency:** ~10ms
- **Write latency:** ~10ms
- **Concurrent operations:** Unlimited
- **Auto-scaling:** Yes
- **Suitable for:** Serverless, multi-instance deployments

## Monitoring

### Metrics to Track

```python
import time

class MonitoredTokenStorage:
    """Wrapper adding monitoring"""
    
    def __init__(self, storage: TokenStorage):
        self.storage = storage
        self.metrics = {
            'reads': 0,
            'writes': 0,
            'deletes': 0,
            'errors': 0
        }
    
    async def store_token(self, user_id: str, token_data: dict):
        start = time.time()
        try:
            await self.storage.store_token(user_id, token_data)
            self.metrics['writes'] += 1
        except Exception as e:
            self.metrics['errors'] += 1
            raise
        finally:
            duration = time.time() - start
            logger.info(f"Token write took {duration:.3f}s")
```

## Next Steps

- Review [Security](security.md) for comprehensive security practices
- Explore [Reddit Integration](reddit-integration.md) for token usage
- Check [Deployment](deployment.md) for production considerations
