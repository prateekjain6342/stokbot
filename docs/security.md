# Security

Comprehensive security best practices and implementation details.

## Overview

Reddit Listener implements multiple security layers to protect sensitive data and prevent unauthorized access.

## Encryption

### Token Encryption

**Algorithm:** AES-256-CBC

**Implementation:**
- **Key size:** 256 bits (32 bytes)
- **Block size:** 128 bits
- **Mode:** CBC with random IV per encryption
- **Padding:** PKCS7

**Why AES-256:**
- Industry standard
- NIST approved
- No known practical attacks
- Hardware acceleration available

### Key Management

**Generation:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**Storage:**
- Environment variable: `ENCRYPTION_KEY`
- Never committed to version control
- Unique per environment
- Rotated periodically

**Access:**
- Loaded at startup only
- Kept in memory, never logged
- Not exposed via API
- Process-isolated

### Future Enhancement: Key Rotation

```python
async def rotate_encryption_key(
    old_key: bytes,
    new_key: bytes,
    storage: TokenStorage
):
    """Rotate encryption key for all stored tokens"""
    # 1. Create temporary storage with new key
    new_storage = SQLiteTokenStorage("new.db", new_key)
    
    # 2. For each token:
    #    - Decrypt with old key
    #    - Re-encrypt with new key
    #    - Store in new storage
    
    # 3. Swap databases atomically
    # 4. Securely delete old database
```

## Authentication

### Reddit OAuth2

**Flow:** Authorization Code Grant

**Process:**
1. Generate state token (CSRF protection)
2. Redirect user to Reddit authorization
3. Validate state on callback
4. Exchange code for access token
5. Encrypt and store token

**Security measures:**
- State validation prevents CSRF
- HTTPS required for redirect URI (production)
- Short-lived authorization codes
- Automatic token refresh

**Implementation:**
```python
import secrets

def generate_oauth_url(user_id: str) -> str:
    state = secrets.token_urlsafe(32)
    
    # Store state temporarily (5 min TTL)
    await redis.setex(f"oauth_state:{state}", 300, user_id)
    
    return (
        f"https://www.reddit.com/api/v1/authorize?"
        f"client_id={REDDIT_CLIENT_ID}&"
        f"response_type=code&"
        f"state={state}&"
        f"redirect_uri={REDDIT_REDIRECT_URI}&"
        f"duration=permanent&"
        f"scope=read submit"
    )

async def handle_oauth_callback(code: str, state: str):
    # Validate state
    user_id = await redis.get(f"oauth_state:{state}")
    if not user_id:
        raise InvalidStateError()
    
    # Delete state (one-time use)
    await redis.delete(f"oauth_state:{state}")
    
    # Exchange code for token
    token = await exchange_code_for_token(code)
    
    # Encrypt and store
    await storage.store_token(user_id, token)
```

### Slack Authentication

**Token types:**
- **Bot token** (`xoxb-`): Bot identity and permissions
- **App token** (`xapp-`): Socket Mode connection
- **Signing secret**: Request verification

**Security measures:**
- Token stored in environment variables
- Request signature verification
- Socket Mode (no public webhooks)
- Scoped permissions (least privilege)

**Request verification:**
```python
import hmac
import hashlib
import time

def verify_slack_request(
    timestamp: str,
    body: str,
    signature: str,
    signing_secret: str
) -> bool:
    # Prevent replay attacks (5 min window)
    if abs(time.time() - int(timestamp)) > 300:
        return False
    
    # Verify signature
    sig_basestring = f"v0:{timestamp}:{body}"
    expected_signature = "v0=" + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)
```

## API Security

### Rate Limiting

**Purpose:** Prevent abuse and respect API limits

**Implementation:**
- Token bucket algorithm
- Per-endpoint limits
- User-level quotas (future)

**Configuration:**
```python
RATE_LIMITS = {
    'reddit_api': {'rate': 60, 'period': 60},      # 60/min
    'openrouter_api': {'rate': 100, 'period': 60}, # 100/min
    'slack_api': {'rate': 50, 'period': 60}        # 50/min (conservative)
}
```

### API Key Protection

**Storage:**
- Environment variables only
- Never in code or logs
- Separate keys per environment
- Minimal exposure

**Usage:**
```python
# Good: Key loaded once at startup
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

headers = {
    'Authorization': f'Bearer {OPENROUTER_API_KEY}'
}

# Bad: Never log API keys
logger.info(f"Using key: {key}")  # DON'T DO THIS
```

### Request/Response Filtering

**Sanitize inputs:**
```python
import re

def sanitize_query(query: str) -> str:
    """Remove potentially harmful characters"""
    # Remove special chars that could break parsing
    query = re.sub(r'[<>\"\'`]', '', query)
    
    # Limit length
    query = query[:200]
    
    # Normalize whitespace
    query = ' '.join(query.split())
    
    return query
```

**Sanitize outputs:**
```python
def sanitize_llm_output(text: str) -> str:
    """Remove sensitive patterns from LLM output"""
    # Remove potential PII
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED]', text)  # SSN
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
    
    return text
```

## Data Protection

### Data Minimization

**Principles:**
- Only collect what's needed
- Don't store Reddit content long-term
- Delete tokens when disconnected
- No user tracking/analytics

**Implementation:**
```python
# Don't store full Reddit content
# Store only aggregated insights

async def research_topic(query: str):
    # Fetch Reddit data
    reddit_data = await fetch_reddit_data(query)
    
    # Analyze (in memory)
    insights = await analyze_data(reddit_data)
    
    # Return insights, discard raw data
    return insights
    # reddit_data goes out of scope, garbage collected
```

### Secure Logging

**Never log:**
- API keys or tokens
- User passwords
- Encrypted data (before encryption)
- Personal information

**Safe logging:**
```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Good: Log events without sensitive data
logger.info(f"User {user_id[:4]}... started research")
logger.error(f"API call failed: {sanitize_error(error)}")

# Bad: Never do this
logger.info(f"Token: {token}")  # DON'T DO THIS
logger.debug(f"Password: {password}")  # DON'T DO THIS
```

### Secure Error Messages

**User-facing errors:**
```python
# Good: Generic but helpful
"Authentication failed. Please reconnect your Reddit account."

# Bad: Too much detail
"Invalid refresh token: xyz123... expired at 2024-01-01"
```

**Internal errors:**
```python
# Log detailed errors internally
logger.error(
    f"Token refresh failed for user {user_id}",
    exc_info=True,
    extra={'token_expires_at': expires_at}
)

# Show generic error to user
await say("❌ Authentication error. Please try again.")
```

## Infrastructure Security

### Environment Variables

**.env file (development):**
```bash
# Never commit .env to version control
# Add to .gitignore

REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
SLACK_BOT_TOKEN=...
ENCRYPTION_KEY=...
```

**.env.example (committed):**
```bash
# Template without actual secrets

REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
SLACK_BOT_TOKEN=xoxb-your-bot-token
ENCRYPTION_KEY=generate_with_secrets_module
```

**Production (AWS Secrets Manager):**
```python
import boto3
import json

def get_secret(secret_name: str) -> dict:
    """Retrieve secrets from AWS Secrets Manager"""
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# Usage
secrets = get_secret('reddit-listener/prod')
REDDIT_CLIENT_SECRET = secrets['reddit_client_secret']
```

### Network Security

**HTTPS:**
- Required for OAuth callbacks (production)
- Required for all API calls
- Certificate validation enabled

**Firewall rules:**
- Outbound: Allow HTTPS to Reddit, Slack, OpenRouter
- Inbound: None needed (Socket Mode)
- No open ports required

### Dependency Security

**Vulnerability scanning:**
```bash
# Check for known vulnerabilities
pip install safety
safety check

# Update dependencies
pip list --outdated
pip install --upgrade <package>
```

**Pinned versions:**
```toml
# pyproject.toml
[project.dependencies]
asyncpraw = "==7.7.1"  # Pin to specific version
cryptography = ">=41.0.0,<42.0.0"  # Allow patches
```

## Access Control

### Principle of Least Privilege

**Slack bot scopes:**
- `commands` - Only what's needed
- `chat:write` - Only what's needed
- No `admin` scopes
- No unnecessary permissions

**Reddit API scopes:**
- `read` - Read posts/comments
- `submit` - Optional (not currently used)
- No `modposts`, `modself`, etc.

**Database access:**
- Application: Read/write to tokens table only
- No DDL permissions in production
- Separate admin credentials

### User Isolation

**Token storage:**
```python
# Each user's tokens isolated by user_id
await storage.store_token(user_id, token)

# Can only access own tokens
my_token = await storage.get_token(my_user_id)

# Cannot access other users' tokens
other_token = await storage.get_token(other_user_id)  # Returns None if not authorized
```

## Incident Response

### Security Monitoring

**What to monitor:**
- Failed authentication attempts
- API rate limit hits
- Encryption/decryption errors
- Unusual access patterns

**Alerting:**
```python
async def monitor_security_event(event_type: str, details: dict):
    """Log and alert on security events"""
    logger.warning(
        f"Security event: {event_type}",
        extra={'details': details}
    )
    
    # Alert for critical events
    if event_type in ['auth_failure', 'encryption_error']:
        await send_alert(event_type, details)
```

### Breach Response Plan

**If API key compromised:**
1. Immediately rotate key in provider dashboard
2. Update environment variables
3. Restart application
4. Audit recent usage
5. Investigate source of leak

**If encryption key compromised:**
1. Generate new encryption key
2. Rotate all stored tokens (re-encrypt)
3. Audit database access logs
4. Notify affected users (if applicable)

**If token database compromised:**
1. Delete all tokens
2. Force users to re-authenticate
3. Rotate encryption keys
4. Investigate breach vector
5. Implement additional safeguards

## Compliance & Privacy

### Data Retention

**Current policy:**
- OAuth tokens: Until user disconnects
- Research results: Not stored
- Logs: 30 days (configurable)
- Temporary data: Cleared immediately

**Implementation:**
```python
# Auto-delete old logs
async def cleanup_old_logs():
    """Delete logs older than 30 days"""
    cutoff = datetime.now() - timedelta(days=30)
    # Delete old log files
```

### GDPR Considerations

**User rights:**
- **Access:** Users can see their connected status
- **Deletion:** `/disconnect-reddit` removes all data
- **Portability:** No personal data collected to export
- **Consent:** Explicit OAuth consent flow

**Implementation:**
```python
@app.command("/disconnect-reddit")
async def handle_disconnect(ack, command):
    await ack()
    
    user_id = command['user_id']
    
    # Delete all user data
    await storage.delete_token(user_id)
    await delete_user_logs(user_id)
    
    await say("✅ Reddit account disconnected. All data deleted.")
```

## Security Checklist

### Development
- [ ] No secrets in code
- [ ] No secrets in version control
- [ ] `.env` in `.gitignore`
- [ ] Use `.env.example` for templates
- [ ] Enable linters and security scanners

### Deployment
- [ ] HTTPS enabled
- [ ] Environment variables set
- [ ] Encryption key generated
- [ ] API keys rotated from defaults
- [ ] Minimal permissions configured
- [ ] Logging configured (no sensitive data)
- [ ] Monitoring and alerts set up

### Ongoing
- [ ] Regular dependency updates
- [ ] Security vulnerability scanning
- [ ] Log monitoring
- [ ] Incident response plan tested
- [ ] Key rotation (quarterly)

## Next Steps

- Review [Storage](storage.md) for encryption details
- Explore [Deployment](deployment.md) for production security
- Check [Troubleshooting](troubleshooting.md) for security-related issues
