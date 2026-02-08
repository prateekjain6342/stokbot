"""Relevance scoring for filtering Reddit posts."""

import re
from dataclasses import dataclass
from typing import Any, List, Tuple


@dataclass
class ScoredPost:
    """A post with its relevance score."""

    post: Any  # Reddit Submission
    relevance_score: float
    match_reasons: List[str]


class RelevanceScorer:
    """Scores posts for relevance to a query."""

    def __init__(self, min_threshold: float = 0.3):
        """Initialize relevance scorer.

        Args:
            min_threshold: Minimum relevance score (0-1) to include a post.
                          Default 0.3 = moderate strictness.
        """
        self.min_threshold = min_threshold

    def score_post(self, post: Any, query: str) -> ScoredPost:
        """Score a single post for relevance to query.

        Args:
            post: Reddit submission
            query: User's search query

        Returns:
            ScoredPost with relevance score and match reasons
        """
        score = 0.0
        reasons = []

        # Normalize query and content
        query_lower = query.lower().strip()
        query_words = set(query_lower.split())
        query_phrases = self._extract_phrases(query_lower)

        title = getattr(post, "title", "").lower()
        body = getattr(post, "selftext", "").lower() if hasattr(post, "selftext") else ""

        # 1. Exact phrase match in title (highest weight: 0.5)
        for phrase in query_phrases:
            if phrase in title:
                score += 0.5
                reasons.append(f"Exact phrase '{phrase}' in title")
                break  # Only count once

        # 2. Exact phrase match in body (weight: 0.25)
        for phrase in query_phrases:
            if phrase in body:
                score += 0.25
                reasons.append(f"Exact phrase '{phrase}' in body")
                break

        # 3. All query words appear in title (weight: 0.3)
        title_words = set(re.findall(r'\b[a-z]+\b', title))
        if query_words and query_words.issubset(title_words):
            score += 0.3
            reasons.append("All query words in title")
        # 4. Partial word match in title (weight: 0.15)
        elif query_words:
            matching_words = query_words.intersection(title_words)
            if matching_words:
                partial_score = 0.15 * (len(matching_words) / len(query_words))
                score += partial_score
                reasons.append(f"Partial match: {len(matching_words)}/{len(query_words)} words")

        # 5. All query words in body (weight: 0.15)
        body_words = set(re.findall(r'\b[a-z]+\b', body))
        if query_words and query_words.issubset(body_words):
            score += 0.15
            reasons.append("All query words in body")

        # 6. Query appears in subreddit name (weight: 0.1)
        subreddit = getattr(post, "subreddit", None)
        if subreddit:
            subreddit_name = str(subreddit).lower()
            for phrase in query_phrases:
                phrase_condensed = phrase.replace(" ", "")
                if phrase_condensed in subreddit_name or phrase in subreddit_name:
                    score += 0.1
                    reasons.append(f"Query in subreddit: r/{subreddit}")
                    break

        # Cap score at 1.0
        score = min(score, 1.0)

        return ScoredPost(post=post, relevance_score=score, match_reasons=reasons)

    def filter_posts(
        self, posts: List[Any], query: str
    ) -> Tuple[List[ScoredPost], List[ScoredPost]]:
        """Filter and score posts for relevance.

        Args:
            posts: List of Reddit submissions
            query: User's search query

        Returns:
            Tuple of (relevant_posts, filtered_out_posts)
        """
        scored_posts = [self.score_post(post, query) for post in posts]

        relevant = [sp for sp in scored_posts if sp.relevance_score >= self.min_threshold]
        filtered_out = [sp for sp in scored_posts if sp.relevance_score < self.min_threshold]

        # Sort by relevance score * upvotes (combined ranking)
        relevant.sort(
            key=lambda sp: sp.relevance_score * max(getattr(sp.post, "score", 1), 1),
            reverse=True,
        )

        return relevant, filtered_out

    def _extract_phrases(self, query: str) -> List[str]:
        """Extract meaningful phrases from query.

        Args:
            query: Search query

        Returns:
            List of phrases to match (full query + sub-phrases)
        """
        phrases = [query]  # Full query is always a phrase

        # If query has multiple words, also try consecutive pairs
        words = query.split()
        if len(words) >= 2:
            for i in range(len(words) - 1):
                phrases.append(f"{words[i]} {words[i+1]}")

        return phrases
