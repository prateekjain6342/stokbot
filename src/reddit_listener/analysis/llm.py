"""LLM analysis using OpenRouter with Minimax model."""

import json
from dataclasses import dataclass
from typing import Any, Dict, List

import httpx

from ..reddit.retry import async_retry_with_backoff


@dataclass
class PainPoint:
    """A pain point identified from Reddit discussions."""

    description: str
    solution_summary: str
    upvotes: int


@dataclass
class ContentIdea:
    """Content idea generated from Reddit insights."""

    title: str
    description: str
    rationale: str


class LLMAnalyzer:
    """OpenRouter LLM analyzer using Minimax M2.1 model."""

    def __init__(self, api_key: str, model: str = "minimax/minimax-m2.1"):
        """Initialize LLM analyzer.

        Args:
            api_key: OpenRouter API key
            model: OpenRouter model to use (defaults to minimax/minimax-m2.1)
        """
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = model
        self.client = httpx.AsyncClient(timeout=120.0)

    @async_retry_with_backoff(
        max_retries=3,
        retryable_exceptions=(httpx.HTTPError, httpx.TimeoutException),
    )
    async def _make_request(
        self, messages: List[Dict[str, str]], temperature: float = 0.7
    ) -> str:
        """Make a request to OpenRouter API.

        Args:
            messages: List of message objects with role and content
            temperature: Sampling temperature

        Returns:
            Response content from the model
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/findyourn/reddit-listener",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        response = await self.client.post(
            self.base_url,
            headers=headers,
            json=payload,
        )

        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"]

    def _extract_json_from_response(self, response: str) -> str:
        """Extract JSON from response, handling markdown code blocks.

        Args:
            response: Raw response string

        Returns:
            Cleaned JSON string
        """
        # Remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]  # Remove ```json
        elif response.startswith("```"):
            response = response[3:]  # Remove ```
        
        if response.endswith("```"):
            response = response[:-3]  # Remove trailing ```
        
        response = response.strip()
        
        # Fix common JSON issues
        # Fix double quotes at end of strings (e.g., "text."" -> "text.")
        import re
        response = re.sub(r'\.""(\s*\n)', r'."\\1', response)
        
        return response

    async def analyze_pain_points(
        self, query: str, posts_data: List[Dict[str, Any]]
    ) -> List[PainPoint]:
        """Analyze Reddit posts to extract pain points and solutions.

        Args:
            query: Original search query for relevance filtering
            posts_data: List of post data with title, body, comments, upvotes

        Returns:
            List of top 10 pain points with community solutions
        """
        # Format posts for the prompt
        posts_text = self._format_posts_for_analysis(posts_data)

        prompt = f"""Analyze the following Reddit discussions and identify the TOP 10 pain points that people are discussing.

For EACH pain point:
1. Describe the pain point clearly
2. Summarize the TOP community-voted solutions (based on upvotes and quality)
3. Note the general sentiment/priority

IMPORTANT: Only include pain points that are DIRECTLY related to "{query}". 
Ignore tangential discussions or unrelated topics that may have appeared in search results.

Reddit Discussions:
{posts_text}

Return your analysis as a JSON array with this EXACT structure:
[
  {{
    "description": "Clear description of the pain point",
    "solution_summary": "Summary of top-voted community solutions",
    "upvotes": <total upvotes for related posts>
  }}
]

Return ONLY the JSON array, no additional text or markdown formatting."""

        messages = [
            {
                "role": "system",
                "content": "You are an expert at analyzing community discussions and identifying key pain points with their solutions. Always return valid JSON without markdown code blocks.",
            },
            {"role": "user", "content": prompt},
        ]

        response = await self._make_request(messages, temperature=0.3)

        # Parse JSON response
        try:
            # Clean response from markdown formatting
            json_str = self._extract_json_from_response(response)
            pain_points_data = json.loads(json_str)
            pain_points = [
                PainPoint(
                    description=pp["description"],
                    solution_summary=pp["solution_summary"],
                    upvotes=pp.get("upvotes", 0),
                )
                for pp in pain_points_data[:10]
            ]
            return pain_points
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing pain points response: {e}")
            print(f"Response: {response}")
            return []

    async def generate_content_ideas(
        self, query: str, posts_data: List[Dict[str, Any]], pain_points: List[PainPoint]
    ) -> List[ContentIdea]:
        """Generate content ideas based on Reddit insights.

        Args:
            query: Original search query
            posts_data: List of post data
            pain_points: Identified pain points

        Returns:
            List of up to 10 content ideas
        """
        posts_text = self._format_posts_for_analysis(posts_data[:50])
        pain_points_text = "\n".join(
            [f"- {pp.description}" for pp in pain_points[:10]]
        )

        prompt = f"""Based on the following Reddit research about "{query}", generate 10 compelling content ideas.

Pain Points Identified:
{pain_points_text}

Sample Reddit Discussions:
{posts_text}

For EACH content idea, provide:
1. A compelling title
2. A brief description of what the content would cover
3. Why this would be valuable based on the Reddit insights

IMPORTANT: Only generate content ideas that are DIRECTLY related to "{query}".
Do not include ideas about unrelated topics that happened to appear in the data.

Return your analysis as a JSON array with this EXACT structure:
[
  {{
    "title": "Compelling content title",
    "description": "Brief description of content coverage",
    "rationale": "Why this is valuable based on insights"
  }}
]

Return ONLY the JSON array, no additional text or markdown formatting."""

        messages = [
            {
                "role": "system",
                "content": "You are an expert content strategist who creates engaging content ideas based on community insights. Always return valid JSON without markdown code blocks.",
            },
            {"role": "user", "content": prompt},
        ]

        response = await self._make_request(messages, temperature=0.7)

        # Parse JSON response
        try:
            # Clean response from markdown formatting
            json_str = self._extract_json_from_response(response)
            content_ideas_data = json.loads(json_str)
            content_ideas = [
                ContentIdea(
                    title=ci["title"],
                    description=ci["description"],
                    rationale=ci["rationale"],
                )
                for ci in content_ideas_data[:10]
            ]
            return content_ideas
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing content ideas response: {e}")
            print(f"Response: {response}")
            return []

    def _format_posts_for_analysis(
        self, posts_data: List[Dict[str, Any]], max_posts: int = 50
    ) -> str:
        """Format posts for LLM analysis.

        Args:
            posts_data: List of post data
            max_posts: Maximum posts to include

        Returns:
            Formatted text
        """
        formatted = []
        for i, post in enumerate(posts_data[:max_posts], 1):
            title = post.get("title", "")
            body = post.get("body", "")[:500]  # Limit body length
            upvotes = post.get("upvotes", 0)
            comments_preview = []

            for comment in post.get("comments", [])[:3]:
                comments_preview.append(
                    f"  → {comment.get('body', '')[:200]} (↑{comment.get('upvotes', 0)})"
                )

            post_text = f"""
Post {i}: {title} (↑{upvotes})
{body}
Top Comments:
{chr(10).join(comments_preview)}
---"""
            formatted.append(post_text)

        return "\n".join(formatted)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
