"""Reddit Listener: Reddit research tool with Slack Bot integration.

Public API:
    - ResearchService: Main orchestrator for Reddit research
    - ResearchResult: Research results data structure
    - RedditClient: Reddit API client with OAuth support
    - LLMAnalyzer: LLM-powered content analysis
    - TokenStore: Abstract storage interface
    - SQLiteTokenStore: SQLite token storage implementation
    - TokenData: Token data structure
    - PainPoint, ContentIdea: Analysis result structures
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("reddit-listener")
except PackageNotFoundError:
    # Package not installed, use development version
    __version__ = "0.0.0.dev"

# Core research functionality
from .core import ResearchService, ResearchResult
from .reddit import RedditClient
from .analysis import LLMAnalyzer

# Storage interfaces and implementations
from .storage import TokenStore, SQLiteTokenStore
from .storage.base import TokenData

# Analysis result types
from .analysis.llm import PainPoint, ContentIdea

# Configuration
from .config import Config, SlackConfig, RedditConfig, LLMConfig, StorageConfig

__all__ = [
    # Version
    "__version__",
    # Core services
    "ResearchService",
    "ResearchResult",
    "RedditClient",
    "LLMAnalyzer",
    # Storage
    "TokenStore",
    "SQLiteTokenStore",
    "TokenData",
    # Analysis results
    "PainPoint",
    "ContentIdea",
    # Configuration
    "Config",
    "SlackConfig",
    "RedditConfig",
    "LLMConfig",
    "StorageConfig",
]
