"""Synchronous wrapper for ResearchService for Flask/sync environments."""

import asyncio
from typing import Optional

from ..analysis.llm import DetailedContext, LLMAnalyzer
from ..config import Config, get_config
from ..reddit.client import RedditClient
from ..storage.sqlite import SQLiteTokenStore
from .research import DiscoveryResult, ResearchResult, ResearchService


class SyncResearchService:
    """Synchronous wrapper around ResearchService for Flask and other sync frameworks.
    
    This class provides blocking methods that internally manage the asyncio event loop,
    making it easy to use the Reddit research capabilities in synchronous contexts.
    
    Example:
        ```python
        from reddit_listener import SyncResearchService
        
        # Initialize service
        service = SyncResearchService()
        
        # Discover content ideas
        discovery = service.discover_ideas("artificial intelligence")
        print(f"Found {len(discovery.content_ideas)} ideas")
        
        # Get detailed context for a specific idea
        context = service.get_idea_context(
            query="artificial intelligence",
            idea_title=discovery.content_ideas[0].title
        )
        print(context.full_post_and_comment_analysis)
        
        # Clean up
        service.close()
        ```
    """

    def __init__(
        self,
        reddit_client_id: Optional[str] = None,
        reddit_client_secret: Optional[str] = None,
        reddit_user_agent: Optional[str] = None,
        reddit_redirect_uri: Optional[str] = None,
        openrouter_api_key: Optional[str] = None,
        openrouter_model: Optional[str] = None,
        encryption_key: Optional[str] = None,
        database_path: Optional[str] = None,
    ):
        """Initialize synchronous research service.
        
        Args:
            reddit_client_id: Reddit OAuth app client ID (defaults to env REDDIT_CLIENT_ID)
            reddit_client_secret: Reddit OAuth app client secret (defaults to env REDDIT_CLIENT_SECRET)
            reddit_user_agent: Reddit user agent (defaults to env REDDIT_USER_AGENT)
            reddit_redirect_uri: Reddit OAuth redirect URI (defaults to env REDDIT_REDIRECT_URI)
            openrouter_api_key: OpenRouter API key (defaults to env OPENROUTER_API_KEY)
            openrouter_model: OpenRouter model (defaults to env OPENROUTER_MODEL or "minimax/minimax-m2.1")
            encryption_key: Encryption key for token storage (defaults to env ENCRYPTION_KEY)
            database_path: Database path for token storage (defaults to env DATABASE_PATH or "./data/tokens.db")
        """
        # Load config
        config = get_config()
        
        # Use provided values or fall back to config
        self._reddit_client_id = reddit_client_id or config.reddit_client_id
        self._reddit_client_secret = reddit_client_secret or config.reddit_client_secret
        self._reddit_user_agent = reddit_user_agent or config.reddit_user_agent
        self._reddit_redirect_uri = reddit_redirect_uri or config.reddit_redirect_uri
        self._openrouter_api_key = openrouter_api_key or config.openrouter_api_key
        self._openrouter_model = openrouter_model or config.openrouter_model
        self._encryption_key = encryption_key or config.encryption_key
        self._database_path = database_path or config.database_path
        
        # Initialize async components
        self._loop = None
        self._service = None
        self._initialized = False

    def _ensure_initialized(self):
        """Ensure async components are initialized."""
        if not self._initialized:
            # Create event loop if needed
            try:
                self._loop = asyncio.get_event_loop()
                if self._loop.is_closed():
                    self._loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self._loop)
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
            
            # Initialize async service
            token_store = SQLiteTokenStore(
                db_path=self._database_path,
                encryption_key=self._encryption_key,
            )
            
            reddit_client = RedditClient(
                client_id=self._reddit_client_id,
                client_secret=self._reddit_client_secret,
                user_agent=self._reddit_user_agent,
                redirect_uri=self._reddit_redirect_uri,
                token_store=token_store,
            )
            
            llm_analyzer = LLMAnalyzer(
                api_key=self._openrouter_api_key,
                model=self._openrouter_model,
            )
            
            self._service = ResearchService(
                reddit_client=reddit_client,
                llm_analyzer=llm_analyzer,
            )
            
            self._initialized = True

    def research(
        self,
        query: str,
        team_id: Optional[str] = None,
        user_id: Optional[str] = None,
        time_filter: str = "month",
        limit: int = 100,
    ) -> ResearchResult:
        """Perform complete research on a query (synchronous).
        
        Args:
            query: Search phrase to research
            team_id: Slack team ID (optional, for user auth)
            user_id: Slack user ID (optional, for user auth)
            time_filter: Time filter for search ("hour", "day", "week", "month", "year", "all")
            limit: Maximum number of posts to fetch
            
        Returns:
            Complete research results
        """
        self._ensure_initialized()
        return self._loop.run_until_complete(
            self._service.research(query, team_id, user_id, time_filter, limit)
        )

    def discover_ideas(
        self,
        query: str,
        team_id: Optional[str] = None,
        user_id: Optional[str] = None,
        time_filter: str = "month",
        limit: int = 100,
        batch_size: int = 5,
        min_relevant: int = 3,
    ) -> DiscoveryResult:
        """Phase 1: Discover content ideas from Reddit discussions (synchronous).
        
        This method performs the complete research flow and caches the results
        for later detailed context generation. Cache expires after 15 minutes.
        
        Fetches posts incrementally in batches to optimize performance:
        - Fetches posts in batches (default 5 at a time)
        - Checks relevance after each batch
        - Stops early if enough relevant posts are found
        - Reduces unnecessary API calls
        
        Args:
            query: Search phrase to research
            team_id: Slack team ID (optional, for user auth)
            user_id: Slack user ID (optional, for user auth)
            time_filter: Time filter for search ("hour", "day", "week", "month", "year", "all")
            limit: Maximum number of posts to fetch
            batch_size: Number of posts to fetch in each batch (default: 5)
            min_relevant: Minimum relevant posts to proceed (default: 3)
            
        Returns:
            Discovery results with content ideas and cached context data
        """
        self._ensure_initialized()
        return self._loop.run_until_complete(
            self._service.discover_ideas(query, team_id, user_id, time_filter, limit, batch_size, min_relevant)
        )

    def get_idea_context(self, query: str, idea_title: str) -> DetailedContext:
        """Phase 2: Get detailed context for a specific content idea (synchronous).
        
        Retrieves cached discovery data and generates in-depth analysis for the
        selected idea. This provides rich context for downstream content generation.
        
        Args:
            query: Original search query used in discover_ideas()
            idea_title: Title of the content idea to get context for
            
        Returns:
            Detailed context with comprehensive analysis
            
        Raises:
            ValueError: If no cached discovery data found for query or if cache expired
        """
        self._ensure_initialized()
        return self._loop.run_until_complete(
            self._service.get_idea_context(query, idea_title)
        )

    def close(self):
        """Close all async connections and clean up resources."""
        if self._service:
            self._loop.run_until_complete(self._service.reddit.close())
            self._loop.run_until_complete(self._service.llm.close())
            self._loop.run_until_complete(self._service.reddit.token_store.close())
