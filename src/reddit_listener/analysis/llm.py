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


@dataclass
class DetailedContext:
    """Detailed context for a specific content idea."""

    idea_title: str
    idea_description: str
    full_post_and_comment_analysis: str
    emotional_aspect: str
    controversial_aspect: Dict[str, Any]  # {"is_controversial": bool, "for_against_split": str}
    engagement_signals: Dict[str, Any]  # {"popularity": str, "virality_potential": str}
    knowledge_depth: str  # "beginner-friendly" / "intermediate" / "expert"
    category: str


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
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        response_format: Dict[str, Any] = None
    ) -> str:
        """Make a request to OpenRouter API.

        Args:
            messages: List of message objects with role and content
            temperature: Sampling temperature
            response_format: Optional response format specification for structured output

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
        
        # Add response_format if provided
        if response_format:
            payload["response_format"] = response_format

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

Return your analysis as a JSON array containing up to 10 pain point objects."""

        messages = [
            {
                "role": "system",
                "content": "You are an expert at analyzing community discussions and identifying key pain points with their solutions. Return structured JSON data.",
            },
            {"role": "user", "content": prompt},
        ]

        # Define JSON schema for structured output
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "pain_points_analysis",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "pain_points": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "description": {
                                        "type": "string",
                                        "description": "Clear description of the pain point"
                                    },
                                    "solution_summary": {
                                        "type": "string",
                                        "description": "Summary of top-voted community solutions"
                                    },
                                    "upvotes": {
                                        "type": "integer",
                                        "description": "Total upvotes for related posts"
                                    }
                                },
                                "required": ["description", "solution_summary", "upvotes"],
                                "additionalProperties": False
                            },
                            "maxItems": 10
                        }
                    },
                    "required": ["pain_points"],
                    "additionalProperties": False
                }
            }
        }

        response = await self._make_request(messages, temperature=0.3, response_format=response_format)

        # Parse JSON response
        try:
            data = json.loads(response)
            pain_points_data = data.get("pain_points", [])
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

Return your analysis as a JSON object containing up to 10 content ideas."""

        messages = [
            {
                "role": "system",
                "content": "You are an expert content strategist who creates engaging content ideas based on community insights. Return structured JSON data.",
            },
            {"role": "user", "content": prompt},
        ]

        # Define JSON schema for structured output
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "content_ideas_generation",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "content_ideas": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {
                                        "type": "string",
                                        "description": "Compelling content title"
                                    },
                                    "description": {
                                        "type": "string",
                                        "description": "Brief description of content coverage"
                                    },
                                    "rationale": {
                                        "type": "string",
                                        "description": "Why this is valuable based on insights"
                                    }
                                },
                                "required": ["title", "description", "rationale"],
                                "additionalProperties": False
                            },
                            "maxItems": 10
                        }
                    },
                    "required": ["content_ideas"],
                    "additionalProperties": False
                }
            }
        }

        response = await self._make_request(messages, temperature=0.7, response_format=response_format)

        # Parse JSON response
        try:
            data = json.loads(response)
            content_ideas_data = data.get("content_ideas", [])
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

    async def generate_detailed_context(
        self,
        idea_title: str,
        idea_description: str,
        posts_data: List[Dict[str, Any]],
    ) -> DetailedContext:
        """Generate detailed context for a specific content idea.

        This provides comprehensive, case-study-level analysis of Reddit discussions
        for downstream content generation. The analysis is exhaustive and captures
        nuances, debates, emotions, and community dynamics.

        Args:
            idea_title: Title of the content idea
            idea_description: Brief description of the idea
            posts_data: List of post data from Reddit

        Returns:
            Detailed context with comprehensive analysis
        """
        posts_text = self._format_posts_for_analysis(posts_data, max_posts=100)

        prompt = f"""You are analyzing Reddit discussions to provide exhaustive context for this content idea:

**Content Idea:** {idea_title}
**Description:** {idea_description}

**Your Task:**
Provide a comprehensive, case-study-level analysis of the Reddit discussions below. This analysis will be the ONLY context available to downstream content generators (LinkedIn posts, Twitter threads, blog articles), so it must be extremely detailed and capture ALL relevant information.

**Reddit Discussions:**
{posts_text}

**Analysis Requirements:**

1. **Full Post & Comment Analysis** (Most Important):
   - Transform the Reddit data into a richly detailed narrative
   - Go far beyond summarization — provide point-by-point contextualized analysis
   - Capture: motivations, challenges, debates, opposing viewpoints, technical/cultural context
   - Document: recurring issues, sentiment shifts, community consensus, minority opinions
   - Include: specific examples, quotes (paraphrased), concrete scenarios
   - Identify: underlying problems, attempted solutions, what worked/didn't work
   - Write like a comprehensive case study that could stand alone
   - Minimum 500 words, maximum 2000 words

2. **Emotional Aspect**: 
   - Identify the dominant emotional tone (e.g., "frustrated", "excited", "concerned", "hopeful", "angry", "curious")

3. **Controversial Aspect**:
   - Determine if the topic is controversial
   - If yes, estimate the split (e.g., "60% supportive, 40% critical")

4. **Engagement Signals**:
   - Assess popularity level ("high", "medium", "low")
   - Estimate virality potential ("high", "medium", "low")

5. **Knowledge Depth**:
   - Classify as "beginner-friendly", "intermediate", or "expert"

6. **Category**:
   - Primary content category (e.g., "Tutorial", "Opinion", "Analysis", "Case Study", "Guide", "News", "Discussion")

Focus on extracting maximum value and context from the Reddit discussions."""

        messages = [
            {
                "role": "system",
                "content": "You are an expert Reddit and social media content analyst who provides exhaustive, case-study-level analysis. You extract maximum context and nuance from discussions to enable high-quality content generation downstream.",
            },
            {"role": "user", "content": prompt},
        ]

        # Define JSON schema for structured output
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "detailed_context_analysis",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "idea_title": {
                            "type": "string",
                            "description": "The content idea title"
                        },
                        "idea_description": {
                            "type": "string",
                            "description": "Brief description of the idea"
                        },
                        "full_post_and_comment_analysis": {
                            "type": "string",
                            "description": "Exhaustive case-study-like narrative analysis (500-2000 words)"
                        },
                        "emotional_aspect": {
                            "type": "string",
                            "description": "Dominant emotional tone"
                        },
                        "controversial_aspect": {
                            "type": "object",
                            "properties": {
                                "is_controversial": {
                                    "type": "boolean",
                                    "description": "Whether the topic is controversial"
                                },
                                "for_against_split": {
                                    "type": "string",
                                    "description": "Percentage split if controversial"
                                }
                            },
                            "required": ["is_controversial", "for_against_split"],
                            "additionalProperties": False
                        },
                        "engagement_signals": {
                            "type": "object",
                            "properties": {
                                "popularity": {
                                    "type": "string",
                                    "description": "Popularity level: high, medium, or low"
                                },
                                "virality_potential": {
                                    "type": "string",
                                    "description": "Virality potential: high, medium, or low"
                                }
                            },
                            "required": ["popularity", "virality_potential"],
                            "additionalProperties": False
                        },
                        "knowledge_depth": {
                            "type": "string",
                            "description": "Target audience level: beginner-friendly, intermediate, or expert"
                        },
                        "category": {
                            "type": "string",
                            "description": "Primary content category"
                        }
                    },
                    "required": [
                        "idea_title",
                        "idea_description",
                        "full_post_and_comment_analysis",
                        "emotional_aspect",
                        "controversial_aspect",
                        "engagement_signals",
                        "knowledge_depth",
                        "category"
                    ],
                    "additionalProperties": False
                }
            }
        }

        response = await self._make_request(messages, temperature=0.5, response_format=response_format)

        # Parse JSON response
        try:
            data = json.loads(response)
            return DetailedContext(
                idea_title=data["idea_title"],
                idea_description=data["idea_description"],
                full_post_and_comment_analysis=data["full_post_and_comment_analysis"],
                emotional_aspect=data["emotional_aspect"],
                controversial_aspect=data["controversial_aspect"],
                engagement_signals=data["engagement_signals"],
                knowledge_depth=data["knowledge_depth"],
                category=data["category"],
            )
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing detailed context response: {e}")
            print(f"Response: {response}")
            # Return a minimal context on error
            return DetailedContext(
                idea_title=idea_title,
                idea_description=idea_description,
                full_post_and_comment_analysis="Error generating detailed analysis.",
                emotional_aspect="unknown",
                controversial_aspect={"is_controversial": False, "for_against_split": "N/A"},
                engagement_signals={"popularity": "unknown", "virality_potential": "unknown"},
                knowledge_depth="unknown",
                category="unknown",
            )

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
