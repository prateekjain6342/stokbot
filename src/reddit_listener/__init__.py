"""Reddit Listener: Reddit research tool with Slack Bot integration.

Public API:
    - SyncResearchService: Synchronous wrapper for Flask/sync environments
    - ResearchService: Async orchestrator for Reddit research
    - ResearchResult: Complete research results data structure
    - DiscoveryResult: Phase 1 discovery results with content ideas
    - DetailedContext: Phase 2 detailed context for a specific idea
    - RedditClient: Reddit API client with OAuth support
    - LLMAnalyzer: LLM-powered content analysis
    - TokenStore: Abstract storage interface
    - SQLiteTokenStore: SQLite token storage implementation
    - TokenData: Token data structure
    - PainPoint, ContentIdea: Analysis result structures
    - RelevanceScorer, ScoredPost: Post relevance filtering
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("reddit-listener")
except PackageNotFoundError:
    # Package not installed, use development version
    __version__ = "0.0.0.dev"

# Core research functionality
from .core import DiscoveryResult, ResearchResult, ResearchService, SyncResearchService
from .reddit import RedditClient, RelevanceScorer, ScoredPost
from .analysis import ContentIdea, DetailedContext, LLMAnalyzer, PainPoint

# Storage interfaces and implementations
from .storage import SQLiteTokenStore, TokenStore
from .storage.base import TokenData

# Configuration
from .config import Config, LLMConfig, RedditConfig, SlackConfig, StorageConfig

__all__ = [
    # Version
    "__version__",
    # Core services
    "SyncResearchService",
    "ResearchService",
    "ResearchResult",
    "DiscoveryResult",
    "DetailedContext",
    "RedditClient",
    "LLMAnalyzer",
    # Storage
    "TokenStore",
    "SQLiteTokenStore",
    "TokenData",
    # Analysis results
    "PainPoint",
    "ContentIdea",
    # Relevance filtering
    "RelevanceScorer",
    "ScoredPost",
    # Configuration
    "Config",
    "SlackConfig",
    "RedditConfig",
    "LLMConfig",
    "StorageConfig",
]
