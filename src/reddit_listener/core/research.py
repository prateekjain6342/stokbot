"""Core research orchestration."""

import asyncio
import re
import time
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from asyncpraw.models import Submission

from ..analysis.llm import ContentIdea, LLMAnalyzer, PainPoint
from ..reddit.client import RedditClient
from ..reddit.relevance import RelevanceScorer


@dataclass
class ResearchResult:
    """Complete research results."""

    query: str
    questions: List[str]
    keywords: List[str]
    pain_points: List[PainPoint]
    content_ideas: List[ContentIdea]


@dataclass
class DiscoveryResult:
    """Discovery phase results with content ideas and cached data."""

    query: str
    content_ideas: List[ContentIdea]
    pain_points: List[PainPoint]
    questions: List[str]
    keywords: List[str]
    _posts_data: List[Dict[str, Any]]  # Internal cache for context generation


@dataclass
class DiscoveryCacheEntry:
    """Cache entry for discovery results."""

    result: DiscoveryResult
    timestamp: float


class ResearchService:
    """Orchestrates Reddit research and LLM analysis."""

    def __init__(self, reddit_client: RedditClient, llm_analyzer: LLMAnalyzer):
        """Initialize research service.

        Args:
            reddit_client: Reddit API client
            llm_analyzer: LLM analyzer for insights
        """
        self.reddit = reddit_client
        self.llm = llm_analyzer
        self.relevance_scorer = RelevanceScorer(min_threshold=0.3)
        self._discovery_cache: Dict[str, DiscoveryCacheEntry] = {}
        self._cache_ttl = 900  # 15 minutes in seconds

    async def research(
        self,
        query: str,
        team_id: Optional[str] = None,
        user_id: Optional[str] = None,
        time_filter: str = "month",
        limit: int = 100,
    ) -> ResearchResult:
        """Perform complete research on a query.

        Args:
            query: Search phrase to research
            team_id: Slack team ID (optional, for user auth)
            user_id: Slack user ID (optional, for user auth)
            time_filter: Time filter for search ("hour", "day", "week", "month", "year", "all")
            limit: Maximum number of posts to fetch

        Returns:
            Complete research results
        """
        print(f"Starting research for: {query}")

        # Fetch Reddit data
        posts = await self.reddit.search_posts(
            query=query,
            limit=limit,
            time_filter=time_filter,
            team_id=team_id,
            user_id=user_id,
        )

        print(f"Found {len(posts)} posts")

        # Filter posts for relevance
        relevant_posts, filtered_out = self.relevance_scorer.filter_posts(posts, query)
        print(f"Relevance filtering: {len(relevant_posts)} relevant, {len(filtered_out)} removed")
        
        # Extract just the posts from scored results
        posts = [sp.post for sp in relevant_posts]

        # Fetch comments for top posts (in parallel)
        top_posts = sorted(posts, key=lambda p: p.score, reverse=True)[:20]
        comment_tasks = [self.reddit.get_post_comments(post, limit=20) for post in top_posts]
        all_comments = await asyncio.gather(*comment_tasks)

        # Map comments to posts
        posts_with_comments = []
        for post, comments in zip(top_posts, all_comments):
            posts_with_comments.append({"post": post, "comments": comments})

        print(f"Fetched comments for {len(posts_with_comments)} top posts")

        # Extract insights (in parallel)
        questions_task = asyncio.create_task(self._extract_questions(posts))
        keywords_task = asyncio.create_task(self._extract_keywords(posts))

        # Prepare data for LLM analysis
        posts_data = self._prepare_posts_data(posts_with_comments)

        # Run LLM analysis (in parallel)
        pain_points_task = asyncio.create_task(self.llm.analyze_pain_points(query, posts_data))

        # Wait for all tasks
        questions = await questions_task
        keywords = await keywords_task
        pain_points = await pain_points_task

        print(f"Extracted {len(questions)} questions, {len(keywords)} keywords, {len(pain_points)} pain points")

        # Generate content ideas based on all insights
        content_ideas = await self.llm.generate_content_ideas(query, posts_data, pain_points)

        print(f"Generated {len(content_ideas)} content ideas")

        return ResearchResult(
            query=query,
            questions=questions[:10],
            keywords=keywords[:10],
            pain_points=pain_points[:10],
            content_ideas=content_ideas[:10],
        )

    async def discover_ideas(
        self,
        query: str,
        team_id: Optional[str] = None,
        user_id: Optional[str] = None,
        time_filter: str = "month",
        limit: int = 100,
        batch_size: int = 5,
        min_relevant: int = 3,
    ) -> DiscoveryResult:
        """Phase 1: Discover content ideas from Reddit discussions.

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
        print(f"Starting discovery for: {query}")

        # Fetch Reddit data in batches
        all_posts = []
        relevant_posts = []
        batches_fetched = 0
        
        while len(all_posts) < limit:
            batch_limit = min(batch_size, limit - len(all_posts))
            
            # Fetch next batch
            batch_posts = await self.reddit.search_posts(
                query=query,
                limit=batch_limit,
                time_filter=time_filter,
                team_id=team_id,
                user_id=user_id,
                skip=len(all_posts),  # Skip already fetched posts
            )
            
            if not batch_posts:
                # No more posts available
                break
                
            all_posts.extend(batch_posts)
            batches_fetched += 1
            
            # Filter this batch for relevance
            batch_relevant, _ = self.relevance_scorer.filter_posts(batch_posts, query)
            relevant_posts.extend(batch_relevant)
            
            print(f"Batch {batches_fetched}: fetched {len(batch_posts)} posts, {len(batch_relevant)} relevant (total relevant: {len(relevant_posts)})")
            
            # Stop if we have enough relevant posts
            if len(relevant_posts) >= min_relevant:
                print(f"Found {len(relevant_posts)} relevant posts - stopping early")
                break

        print(f"Discovery complete: {len(all_posts)} total posts, {len(relevant_posts)} relevant")
        
        # Extract just the posts from scored results
        posts = [sp.post for sp in relevant_posts]

        # Fetch comments for top posts (in parallel)
        top_posts = sorted(posts, key=lambda p: p.score, reverse=True)[:20]
        comment_tasks = [self.reddit.get_post_comments(post, limit=20) for post in top_posts]
        all_comments = await asyncio.gather(*comment_tasks)

        # Map comments to posts
        posts_with_comments = []
        for post, comments in zip(top_posts, all_comments):
            posts_with_comments.append({"post": post, "comments": comments})

        print(f"Fetched comments for {len(posts_with_comments)} top posts")

        # Extract insights (in parallel)
        questions_task = asyncio.create_task(self._extract_questions(posts))
        keywords_task = asyncio.create_task(self._extract_keywords(posts))

        # Prepare data for LLM analysis
        posts_data = self._prepare_posts_data(posts_with_comments)

        # Run LLM analysis (in parallel)
        pain_points_task = asyncio.create_task(self.llm.analyze_pain_points(query, posts_data))

        # Wait for all tasks
        questions = await questions_task
        keywords = await keywords_task
        pain_points = await pain_points_task

        print(f"Extracted {len(questions)} questions, {len(keywords)} keywords, {len(pain_points)} pain points")

        # Generate content ideas based on all insights
        content_ideas = await self.llm.generate_content_ideas(query, posts_data, pain_points)

        print(f"Generated {len(content_ideas)} content ideas")

        # Create discovery result with cached posts data
        result = DiscoveryResult(
            query=query,
            content_ideas=content_ideas[:10],
            pain_points=pain_points[:10],
            questions=questions[:10],
            keywords=keywords[:10],
            _posts_data=posts_data,
        )

        # Cache the result
        self._discovery_cache[query] = DiscoveryCacheEntry(
            result=result,
            timestamp=time.time(),
        )

        # Clean expired cache entries
        self._clean_expired_cache()

        return result

    async def get_idea_context(self, query: str, idea_title: str) -> "DetailedContext":
        """Phase 2: Get detailed context for a specific content idea.

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
        # Import here to avoid circular dependency
        from ..analysis.llm import DetailedContext

        # Check cache
        cache_entry = self._discovery_cache.get(query)
        if not cache_entry:
            raise ValueError(
                f"No cached discovery data found for query: '{query}'. "
                "Please call discover_ideas() first."
            )

        # Check if cache expired
        if time.time() - cache_entry.timestamp > self._cache_ttl:
            del self._discovery_cache[query]
            raise ValueError(
                f"Cached discovery data expired for query: '{query}'. "
                "Please call discover_ideas() again."
            )

        # Find the matching content idea to get description
        matching_idea = None
        for idea in cache_entry.result.content_ideas:
            if idea.title == idea_title:
                matching_idea = idea
                break

        if not matching_idea:
            # Fuzzy match - find closest title
            for idea in cache_entry.result.content_ideas:
                if idea_title.lower() in idea.title.lower() or idea.title.lower() in idea_title.lower():
                    matching_idea = idea
                    break

        if not matching_idea:
            raise ValueError(
                f"Content idea with title '{idea_title}' not found in discovery results. "
                f"Available ideas: {[idea.title for idea in cache_entry.result.content_ideas]}"
            )

        # Generate detailed context
        print(f"Generating detailed context for idea: {idea_title}")
        detailed_context = await self.llm.generate_detailed_context(
            idea_title=matching_idea.title,
            idea_description=matching_idea.description,
            posts_data=cache_entry.result._posts_data,
        )

        return detailed_context

    def _clean_expired_cache(self) -> None:
        """Remove expired entries from discovery cache."""
        current_time = time.time()
        expired_keys = [
            key
            for key, entry in self._discovery_cache.items()
            if current_time - entry.timestamp > self._cache_ttl
        ]
        for key in expired_keys:
            del self._discovery_cache[key]
            print(f"Removed expired cache entry for query: {key}")

    async def _extract_questions(self, posts: List[Submission]) -> List[str]:
        """Extract top questions from posts.

        Args:
            posts: List of Reddit submissions

        Returns:
            List of top 10 questions
        """
        questions: List[tuple[str, int]] = []
        seen: Set[str] = set()

        # Question patterns
        question_words = ["what", "why", "how", "when", "where", "who", "which", "can", "should", "would", "is", "are", "do", "does"]
        question_pattern = re.compile(
            r"^(" + "|".join(question_words) + r")\b.*\?$",
            re.IGNORECASE
        )

        for post in posts:
            # Check title
            if "?" in post.title:
                # Split on sentence boundaries
                sentences = re.split(r'[.!]\s+', post.title)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if "?" in sentence and question_pattern.match(sentence):
                        normalized = sentence.lower().strip()
                        if normalized not in seen and len(sentence) > 10:
                            questions.append((sentence, post.score))
                            seen.add(normalized)

            # Check selftext (post body)
            if hasattr(post, "selftext") and post.selftext:
                sentences = re.split(r'[.!]\s+', post.selftext)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if "?" in sentence and question_pattern.match(sentence):
                        normalized = sentence.lower().strip()
                        if normalized not in seen and len(sentence) > 10:
                            questions.append((sentence, post.score))
                            seen.add(normalized)

        # Sort by score (upvotes) and return top 10
        questions.sort(key=lambda x: x[1], reverse=True)
        return [q[0] for q in questions[:10]]

    async def _extract_keywords(self, posts: List[Submission]) -> List[str]:
        """Extract top keywords and phrases from posts.

        Args:
            posts: List of Reddit submissions

        Returns:
            List of top 10 keywords/phrases
        """
        # Collect all text
        all_text = []
        for post in posts:
            all_text.append(post.title)
            if hasattr(post, "selftext") and post.selftext:
                all_text.append(post.selftext[:500])  # Limit length

        combined_text = " ".join(all_text).lower()

        # Remove common words (basic stopwords)
        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
            "be", "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "must", "can", "i", "you", "he",
            "she", "it", "we", "they", "me", "him", "her", "us", "them", "this",
            "that", "these", "those", "what", "which", "who", "when", "where",
            "why", "how", "all", "each", "every", "both", "few", "more", "most",
            "other", "some", "such", "no", "not", "only", "own", "same", "so",
            "than", "too", "very", "just", "my", "your", "their"
        }

        # Extract words and bigrams
        words = re.findall(r'\b[a-z]{3,}\b', combined_text)
        
        # Count word frequency (excluding stopwords)
        word_counts = Counter([w for w in words if w not in stopwords])

        # Extract common bigrams (two-word phrases)
        bigrams = []
        for i in range(len(words) - 1):
            if words[i] not in stopwords or words[i + 1] not in stopwords:
                bigrams.append(f"{words[i]} {words[i + 1]}")
        
        bigram_counts = Counter(bigrams)

        # Combine and get top keywords
        top_words = [word for word, _ in word_counts.most_common(7)]
        top_bigrams = [bigram for bigram, _ in bigram_counts.most_common(3)]

        # Mix words and phrases
        keywords = top_bigrams + top_words
        return keywords[:10]

    def _prepare_posts_data(
        self, posts_with_comments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Prepare posts data for LLM analysis.

        Args:
            posts_with_comments: List of posts with their comments

        Returns:
            Formatted data for LLM
        """
        posts_data = []
        for item in posts_with_comments:
            post = item["post"]
            comments = item["comments"]

            post_data = {
                "title": post.title,
                "body": getattr(post, "selftext", "")[:1000],
                "upvotes": post.score,
                "comments": [
                    {
                        "body": getattr(comment, "body", "")[:500],
                        "upvotes": getattr(comment, "score", 0),
                    }
                    for comment in comments[:10]
                ],
            }
            posts_data.append(post_data)

        return posts_data
