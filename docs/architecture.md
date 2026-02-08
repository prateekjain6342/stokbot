# Architecture

System design, technology stack, and architectural decisions for Reddit Listener.

## Overview

Reddit Listener is built with Python 3.9+ and designed as an async, event-driven application optimized for serverless deployment.

## Technology Stack

### Core Languages & Frameworks
- **Python 3.9+** - Primary language
- **asyncio** - Asynchronous I/O for concurrent operations
- **asyncpraw** - Async Reddit API wrapper

### External Services
- **Reddit API** - Data source for research
- **Slack API** - Bot interface and notifications
- **OpenRouter** - LLM API gateway (configurable model, default: Minimax M2.1)

### Storage
- **SQLite** - Local encrypted token storage (Phase 1)
- **DynamoDB** - Planned for serverless deployment (Phase 2)

### Security
- **cryptography** - AES-256 encryption for tokens
- **OAuth2** - Authentication flows for Reddit and Slack

## System Architecture

```
┌─────────────┐
│ Slack User  │
└──────┬──────┘
       │ /research command
       ▼
┌─────────────────┐
│  Slack Bot      │ ◄── Socket Mode WebSocket
│  (Socket Mode)  │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│  Research           │
│  Orchestrator       │
└────┬────────────┬───┘
     │            │
     ▼            ▼
┌─────────┐  ┌──────────┐
│ Reddit  │  │   LLM    │
│ Client  │  │ Analysis │
└────┬────┘  └────┬─────┘
     │            │
     ▼            ▼
┌─────────┐  ┌──────────┐
│ Reddit  │  │OpenRouter│
│   API   │  │   API    │
└─────────┘  └──────────┘
     │
     ▼
┌─────────────────┐
│ Token Storage   │
│ (Encrypted)     │
└─────────────────┘
```

## Component Architecture

### 1. Slack Bot Layer
**Location:** `src/reddit_listener/slack/`

- **app.py** - Slack Bolt application, event handlers
- **blocks.py** - Block Kit UI formatters

**Responsibilities:**
- Handle slash commands and events
- Format responses using Block Kit
- Manage user interactions
- Defer long-running operations

**Design patterns:**
- Event-driven architecture
- Message queue pattern for async processing
- Decorator-based route handling

### 2. Research Orchestrator
**Location:** `src/reddit_listener/core/`

- **research.py** - Main orchestration logic

**Responsibilities:**
- Coordinate Reddit data fetching
- Manage LLM analysis pipeline
- Aggregate and format results
- Handle errors and retries

**Flow:**
```
1. Receive research query
2. Search Reddit (multiple subreddits)
3. Filter and rank results
4. Extract content for analysis
5. Send to LLM for insights
6. Parse and structure output
7. Return formatted results
```

### 3. Reddit Client
**Location:** `src/reddit_listener/reddit/`

- **client.py** - Main Reddit API client
- **rate_limiter.py** - Token bucket rate limiting
- **retry.py** - Exponential backoff retry logic

**Responsibilities:**
- Authenticate with Reddit (OAuth2)
- Search posts and comments
- Fetch subreddit data
- Handle rate limiting (60 req/min)
- Retry failed requests

**Features:**
- Async/await for non-blocking I/O
- Token bucket rate limiting
- Exponential backoff (base 2s, max 32s)
- Automatic token refresh

### 4. LLM Analysis
**Location:** `src/reddit_listener/analysis/`

- **llm.py** - OpenRouter integration

**Responsibilities:**
- Format prompts for LLM
- Call OpenRouter API (model configurable via `OPENROUTER_MODEL`)
- Parse structured responses
- Extract questions, keywords, pain points, content ideas

**Prompt engineering:**
- Structured output format (JSON)
- Few-shot examples
- Clear task instructions
- Token optimization

### 5. Storage Layer
**Location:** `src/reddit_listener/storage/`

- **base.py** - Abstract storage interface
- **sqlite.py** - SQLite implementation

**Responsibilities:**
- Store OAuth tokens securely
- Encrypt/decrypt sensitive data (AES-256)
- Support multiple storage backends
- Handle token lifecycle

**Encryption:**
- AES-256 in CBC mode
- Random IV per encryption
- PBKDF2 key derivation
- Encrypted at rest, decrypted in memory

## Project Structure

```
src/reddit_listener/
├── __init__.py
├── __main__.py           # Entry point (CLI)
├── config.py             # Configuration management
│
├── reddit/               # Reddit API client
│   ├── __init__.py
│   ├── client.py         # Main Reddit client
│   ├── rate_limiter.py   # Token bucket rate limiting
│   └── retry.py          # Exponential backoff retry
│
├── analysis/             # LLM analysis
│   ├── __init__.py
│   └── llm.py            # OpenRouter integration
│
├── core/                 # Core business logic
│   ├── __init__.py
│   └── research.py       # Research orchestration
│
├── storage/              # Token storage
│   ├── __init__.py
│   ├── base.py           # Abstract interface
│   └── sqlite.py         # SQLite implementation
│
└── slack/                # Slack integration
    ├── __init__.py
    ├── app.py            # Slack Bot handlers
    └── blocks.py         # Block Kit formatters
```

## Design Principles

### 1. Async First
All I/O operations use `async/await` for maximum concurrency and resource efficiency.

### 2. Separation of Concerns
Clear boundaries between components:
- Slack handles UI/UX
- Reddit client handles data fetching
- LLM handles analysis
- Storage handles persistence

### 3. Dependency Injection
Components receive dependencies via constructors, enabling:
- Easy testing with mocks
- Swappable implementations
- Clear dependency graph

### 4. Configuration as Code
Environment-based configuration with type safety:
- Centralized in `config.py`
- Validated at startup
- No hardcoded secrets

### 5. Fail-Safe Design
Graceful degradation and error handling:
- Retry logic for transient failures
- Rate limiting to prevent abuse
- Detailed error messages
- No silent failures

## Data Flow

### Research Query Flow

```
User → Slack → Research Orchestrator → Reddit Client → Reddit API
                      ↓
                 LLM Analysis ← OpenRouter API
                      ↓
                 Format Results
                      ↓
                  Slack Response → User
```

### OAuth Token Flow

```
User → /connect-reddit → OAuth URL
                          ↓
                    Reddit Authorization
                          ↓
                    Callback Handler
                          ↓
                   Encrypt Token → Storage
```

## Performance Considerations

- **Async I/O:** Non-blocking operations for concurrent requests
- **Rate limiting:** Respect API limits without manual delays
- **Caching:** Token reuse, connection pooling
- **Lazy loading:** Load dependencies only when needed
- **Streaming:** Process large responses incrementally

## Scalability

### Current (Phase 1)
- **Deployment:** Single instance (Railway, Render, Fly.io)
- **Connections:** Socket Mode (WebSocket)
- **Storage:** SQLite (local file)
- **Concurrency:** Process-level (asyncio)

### Future (Phase 2)
- **Deployment:** AWS Lambda (serverless)
- **Connections:** HTTP mode with Lambda Function URLs
- **Storage:** DynamoDB (distributed)
- **Concurrency:** Request-level (Lambda auto-scaling)

## Technology Choices Rationale

| Technology | Why Chosen | Alternatives Considered |
|------------|-----------|------------------------|
| **asyncpraw** | Async Reddit API, well-maintained | praw (sync), direct API calls |
| **Slack Bolt** | Official SDK, Socket Mode support | slack-sdk (low-level), custom |
| **OpenRouter** | Multi-model access, competitive pricing | Direct OpenAI, Anthropic |
| **SQLite** | Simple, serverless, encrypted | PostgreSQL, Redis |
| **Socket Mode** | No public URL, easy local dev | HTTP webhooks, ngrok |

## Next Steps

- Review [Reddit Integration](reddit-integration.md) details
- Understand [LLM Analysis](llm-analysis.md) pipeline
- Explore [Deployment](deployment.md) options
