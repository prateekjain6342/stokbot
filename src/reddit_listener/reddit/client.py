"""Reddit API client with OAuth support."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from urllib.parse import urlencode

import asyncpraw
from asyncpraw.models import Submission, Subreddit

from ..storage.base import TokenData, TokenStore
from .rate_limiter import TokenBucketRateLimiter
from .retry import async_retry_with_backoff


class RedditClient:
    """Async Reddit API client with dual authentication modes."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        user_agent: str,
        redirect_uri: str,
        token_store: Optional[TokenStore] = None,
    ):
        """Initialize Reddit client.

        Args:
            client_id: Reddit OAuth app client ID
            client_secret: Reddit OAuth app client secret
            user_agent: User agent string for API requests
            redirect_uri: OAuth redirect URI
            token_store: Token storage for user OAuth tokens
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self.redirect_uri = redirect_uri
        self.token_store = token_store

        # Rate limiter: 1 request per second with burst of 10
        self.rate_limiter = TokenBucketRateLimiter(rate_per_second=1.0, burst=10)

        # Server-side Reddit instance (for direct backend calls)
        self._server_reddit: Optional[asyncpraw.Reddit] = None

    def get_auth_url(self, state: str) -> str:
        """Generate OAuth authorization URL for user.

        Args:
            state: Random state string for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "state": state,
            "redirect_uri": self.redirect_uri,
            "duration": "permanent",
            "scope": "read identity mysubreddits",
        }
        return f"https://www.reddit.com/api/v1/authorize?{urlencode(params)}"

    async def exchange_code(self, code: str, team_id: str, user_id: str) -> TokenData:
        """Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback
            team_id: Slack team ID
            user_id: Slack user ID

        Returns:
            TokenData with access and refresh tokens
        """
        reddit = asyncpraw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            user_agent=self.user_agent,
        )

        try:
            # Exchange code for token
            await reddit.auth.authorize(code)

            # Get token expiration (Reddit tokens typically last 1 hour)
            expires_at = datetime.utcnow() + timedelta(hours=1)

            token_data = TokenData(
                access_token=reddit._core._authorizer.access_token,
                refresh_token=reddit._core._authorizer.refresh_token or "",
                expires_at=expires_at,
                scope="read identity mysubreddits",
            )

            # Store token
            if self.token_store:
                await self.token_store.save_token(team_id, user_id, token_data)

            return token_data
        finally:
            await reddit.close()

    async def _refresh_token_if_needed(
        self, team_id: str, user_id: str, token_data: TokenData
    ) -> TokenData:
        """Refresh token if expired.

        Args:
            team_id: Slack team ID
            user_id: Slack user ID
            token_data: Current token data

        Returns:
            Updated token data
        """
        # Check if token is expired or will expire soon (within 5 minutes)
        if datetime.utcnow() + timedelta(minutes=5) < token_data.expires_at:
            return token_data

        # Refresh the token
        reddit = asyncpraw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            user_agent=self.user_agent,
            refresh_token=token_data.refresh_token,
        )

        try:
            # Refresh will happen automatically on next request
            await reddit.user.me()

            expires_at = datetime.utcnow() + timedelta(hours=1)
            new_token_data = TokenData(
                access_token=reddit._core._authorizer.access_token,
                refresh_token=reddit._core._authorizer.refresh_token
                or token_data.refresh_token,
                expires_at=expires_at,
                scope=token_data.scope,
            )

            # Update stored token
            if self.token_store:
                await self.token_store.save_token(team_id, user_id, new_token_data)

            return new_token_data
        finally:
            await reddit.close()

    async def _get_user_reddit(self, team_id: str, user_id: str) -> asyncpraw.Reddit:
        """Get Reddit instance for a specific user.

        Args:
            team_id: Slack team ID
            user_id: Slack user ID

        Returns:
            Authenticated Reddit instance

        Raises:
            ValueError: If user has not authorized Reddit access
        """
        if not self.token_store:
            raise ValueError("Token store not configured")

        token_data = await self.token_store.get_token(team_id, user_id)
        if not token_data:
            raise ValueError(
                "User has not authorized Reddit access. Use /connect-reddit first."
            )

        # Refresh token if needed
        token_data = await self._refresh_token_if_needed(team_id, user_id, token_data)

        return asyncpraw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            user_agent=self.user_agent,
            refresh_token=token_data.refresh_token,
        )

    async def _get_server_reddit(self) -> asyncpraw.Reddit:
        """Get server-side Reddit instance (for backend calls).

        Returns:
            Reddit instance with server-side auth
        """
        if self._server_reddit is None:
            self._server_reddit = asyncpraw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
            )
        return self._server_reddit

    @async_retry_with_backoff(
        max_retries=3,
        retryable_exceptions=(Exception,),
    )
    async def search_posts(
        self,
        query: str,
        limit: int = 100,
        time_filter: str = "month",
        team_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Submission]:
        """Search Reddit posts.

        Args:
            query: Search query
            limit: Maximum number of posts to return
            time_filter: Time filter (hour, day, week, month, year, all)
            team_id: Slack team ID (for user auth)
            user_id: Slack user ID (for user auth)

        Returns:
            List of Reddit submissions
        """
        await self.rate_limiter.acquire()

        # Use user auth if provided, otherwise server auth
        if team_id and user_id:
            reddit = await self._get_user_reddit(team_id, user_id)
        else:
            reddit = await self._get_server_reddit()

        try:
            subreddit = await reddit.subreddit("all")
            posts = []

            async for submission in subreddit.search(
                query, time_filter=time_filter, limit=limit
            ):
                posts.append(submission)

            return posts
        finally:
            # Only close if it's a user-specific instance
            if team_id and user_id:
                await reddit.close()

    async def get_post_comments(
        self,
        post: Submission,
        limit: int = 50,
    ) -> List:
        """Get comments from a post.

        Args:
            post: Reddit submission
            limit: Maximum number of comments to fetch

        Returns:
            List of comments (empty list if comments unavailable)
        """
        await self.rate_limiter.acquire()

        try:
            # Check if comments exist
            if not hasattr(post, 'comments') or post.comments is None:
                return []
            
            await post.comments.replace_more(limit=0)
            comments = post.comments.list()
            
            if comments is None:
                return []
                
            return comments[:limit]
        except Exception as e:
            # Silently skip posts without accessible comments
            return []

    async def close(self) -> None:
        """Close all Reddit connections."""
        if self._server_reddit:
            await self._server_reddit.close()
            self._server_reddit = None
