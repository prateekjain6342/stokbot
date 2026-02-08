# Development Guide

Development workflows, project structure, testing, and code quality guidelines.

## Development Setup

### Quick Start

```bash
# Clone and navigate
cd /Users/prateek/Areas/Business/Find\ Your\ N/Projects/reddit_listener

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env
# Edit .env with your credentials

# Run the bot
python -m reddit_listener
```

### Development Dependencies

```toml
# pyproject.toml
[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "black>=23.7.0",
    "ruff>=0.0.285",
    "mypy>=1.5.0",
    "pre-commit>=3.3.3"
]
```

## Project Structure

```
reddit_listener/
├── .env                      # Local config (not committed)
├── .env.example              # Config template
├── .gitignore               # Git ignore rules
├── .github/                 # GitHub workflows
│   └── workflows/
│       └── ci.yml           # CI/CD pipeline
├── README.md                # Project overview
├── pyproject.toml           # Project configuration
├── docs/                    # Documentation
│   ├── README.md            # Docs index
│   ├── setup.md
│   ├── usage.md
│   └── ...
├── src/
│   └── reddit_listener/
│       ├── __init__.py
│       ├── __main__.py      # CLI entry point
│       ├── config.py        # Configuration
│       ├── reddit/          # Reddit integration
│       │   ├── __init__.py
│       │   ├── client.py
│       │   ├── rate_limiter.py
│       │   └── retry.py
│       ├── analysis/        # LLM analysis
│       │   ├── __init__.py
│       │   └── llm.py
│       ├── core/            # Business logic
│       │   ├── __init__.py
│       │   └── research.py
│       ├── storage/         # Token storage
│       │   ├── __init__.py
│       │   ├── base.py
│       │   └── sqlite.py
│       └── slack/           # Slack bot
│           ├── __init__.py
│           ├── app.py
│           └── blocks.py
└── tests/
    ├── __init__.py
    ├── conftest.py          # Shared fixtures
    ├── unit/
    │   ├── test_reddit.py
    │   ├── test_llm.py
    │   └── test_storage.py
    └── integration/
        └── test_research.py
```

## Code Style

### Formatting with Black

```bash
# Format all code
black src/ tests/

# Check formatting
black --check src/ tests/

# Format specific file
black src/reddit_listener/core/research.py
```

**Configuration:**
```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py39']
include = '\.pyi?$'
```

### Linting with Ruff

```bash
# Lint all code
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/

# Lint specific file
ruff check src/reddit_listener/core/research.py
```

**Configuration:**
```toml
# pyproject.toml
[tool.ruff]
line-length = 100
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]
ignore = [
    "E501",  # line too long (handled by black)
]
```

### Type Checking with Mypy

```bash
# Type check all code
mypy src/

# Check specific module
mypy src/reddit_listener/core/
```

**Configuration:**
```toml
# pyproject.toml
[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

## Testing

### Test Structure

```python
# tests/unit/test_storage.py
import pytest
from reddit_listener.storage.sqlite import SQLiteTokenStorage

@pytest.fixture
async def storage():
    """Fixture providing in-memory storage"""
    key = b"0" * 32  # Test key
    storage = SQLiteTokenStorage(":memory:", key)
    await storage.initialize()
    yield storage

@pytest.mark.asyncio
async def test_store_and_retrieve(storage):
    """Test basic storage operations"""
    token_data = {"access_token": "test123"}
    
    await storage.store_token("user1", token_data)
    retrieved = await storage.get_token("user1")
    
    assert retrieved == token_data
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=reddit_listener --cov-report=html

# Run specific test file
pytest tests/unit/test_storage.py

# Run specific test
pytest tests/unit/test_storage.py::test_store_and_retrieve

# Run with verbose output
pytest -v

# Run and stop at first failure
pytest -x
```

### Test Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "slow: Slow tests",
]
```

### Writing Good Tests

**Arrange-Act-Assert pattern:**
```python
async def test_reddit_search():
    # Arrange: Set up test data and mocks
    client = MockRedditClient()
    query = "test query"
    
    # Act: Perform the action
    results = await client.search_posts(query)
    
    # Assert: Verify the outcome
    assert len(results) > 0
    assert results[0].title is not None
```

**Use fixtures for common setup:**
```python
# tests/conftest.py
import pytest
from reddit_listener.config import Config

@pytest.fixture
def config():
    """Test configuration"""
    return Config(
        reddit_client_id="test_id",
        reddit_client_secret="test_secret",
        # ... other test config
    )
```

**Mock external APIs:**
```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_reddit_api_call():
    with patch('asyncpraw.Reddit') as mock_reddit:
        # Configure mock
        mock_reddit.return_value.subreddit.return_value.search = AsyncMock(
            return_value=[MockPost()]
        )
        
        # Test code that uses Reddit
        client = RedditClient(mock_reddit.return_value)
        results = await client.search_posts("test")
        
        assert len(results) == 1
```

## Git Workflow

### Branching Strategy

```bash
# Main branches
main          # Production-ready code
develop       # Integration branch

# Feature branches
feature/reddit-integration
feature/slack-blocks
fix/rate-limiting
docs/setup-guide
```

### Commit Messages

**Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

**Examples:**
```bash
git commit -m "feat(reddit): add rate limiting to API client"
git commit -m "fix(storage): handle encryption errors gracefully"
git commit -m "docs(setup): add Redis installation instructions"
```

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

**Configuration:**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.0.285
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

## Debugging

### Local Debugging

```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or with ipdb (better)
import ipdb; ipdb.set_trace()
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Different log levels
logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.exception("Error with traceback")  # Use in except blocks
```

### Environment-specific Logging

```python
# config.py
import logging
import os

def setup_logging():
    level = logging.DEBUG if os.getenv('DEBUG') == 'true' else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('reddit_listener.log')
        ]
    )
```

## Performance Optimization

### Profiling

```bash
# Profile CPU usage
python -m cProfile -o profile.stats -m reddit_listener

# Analyze results
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumtime').print_stats(20)"
```

### Memory Profiling

```bash
pip install memory_profiler

# Decorate function
from memory_profiler import profile

@profile
async def analyze_content(data):
    # Your code here
    pass
```

### Async Performance

```python
import asyncio
import time

async def benchmark():
    start = time.time()
    
    # Run concurrent operations
    results = await asyncio.gather(
        fetch_reddit_data(),
        analyze_with_llm(),
        format_results()
    )
    
    duration = time.time() - start
    print(f"Total time: {duration:.2f}s")
```

## Documentation

### Docstrings

```python
def search_posts(query: str, limit: int = 100) -> list[Post]:
    """
    Search Reddit posts matching the query.
    
    Args:
        query: Search term or phrase
        limit: Maximum number of results (default: 100)
    
    Returns:
        List of Post objects matching the query
    
    Raises:
        RedditAPIException: If API call fails
        RateLimitExceeded: If rate limit is hit
    
    Example:
        >>> posts = await search_posts("python tutorials", limit=50)
        >>> print(len(posts))
        50
    """
    pass
```

### Type Hints

```python
from typing import Optional, List, Dict, Any

async def analyze_content(
    query: str,
    posts: List[Dict[str, Any]],
    max_tokens: Optional[int] = None
) -> Dict[str, List[str]]:
    """Analyze Reddit content with type hints"""
    pass
```

## CI/CD

### GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      
      - name: Lint with ruff
        run: ruff check src/ tests/
      
      - name: Format check with black
        run: black --check src/ tests/
      
      - name: Type check with mypy
        run: mypy src/
      
      - name: Run tests
        run: pytest --cov=reddit_listener
```

## Best Practices

1. **Write tests first** - TDD helps design better APIs
2. **Keep functions small** - Single responsibility principle
3. **Use type hints** - Catch errors early
4. **Document complex logic** - Future you will thank you
5. **Review your own code** - Read diffs before committing
6. **Update docs with code** - Keep them in sync
7. **Handle errors gracefully** - User-friendly messages
8. **Log appropriately** - Debug info vs. user info
9. **Commit often** - Small, atomic commits
10. **Ask for review** - Fresh eyes catch issues

## Next Steps

- Review [Architecture](architecture.md) for system design
- Explore [Testing Strategy](troubleshooting.md) for debugging
- Check [Deployment](deployment.md) for production setup
