"""Core research orchestration."""

import asyncio
import re
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

    async def research(
        self,
        query: str,
        team_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> ResearchResult:
        """Perform complete research on a query.

        Args:
            query: Search phrase to research
            team_id: Slack team ID (optional, for user auth)
            user_id: Slack user ID (optional, for user auth)

        Returns:
            Complete research results
        """
        print(f"Starting research for: {query}")

        # Fetch Reddit data
        posts = await self.reddit.search_posts(
            query=query,
            limit=100,
            time_filter="month",
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
