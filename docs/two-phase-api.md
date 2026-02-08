# Two-Phase Research API Usage Examples

## Overview

The two-phase API optimizes Reddit data fetching by:
- **Batching**: Fetches posts in small increments (default: 5 at a time)
- **Early stopping**: Stops when enough relevant posts are found (default: 3)
- **Reduced API calls**: Avoids fetching unnecessary data

This typically reduces discovery time by 50-80% when relevant content is found early.

## For Flask/Synchronous Environments

```python
from reddit_listener import SyncResearchService

# Initialize service (uses environment variables by default)
service = SyncResearchService()

# Phase 1: Discover content ideas (with optimized batching)
discovery = service.discover_ideas(
    query="artificial intelligence",
    time_filter="month",
    limit=100,  # Maximum to fetch
    batch_size=5,  # Fetch 5 posts at a time (default: 5)
    min_relevant=3  # Stop after finding 3 relevant posts (default: 3)
)

print(f"Found {len(discovery.content_ideas)} content ideas")
print(f"Top idea: {discovery.content_ideas[0].title}")

# Phase 2: Get detailed context for a specific idea
context = service.get_idea_context(
    query="artificial intelligence",
    idea_title=discovery.content_ideas[0].title
)

print(f"Emotional tone: {context.emotional_aspect}")
print(f"Knowledge level: {context.knowledge_depth}")
print(f"Category: {context.category}")
print(f"Full analysis: {context.full_post_and_comment_analysis[:500]}...")

# Clean up
service.close()
```

## For Async Environments

```python
import asyncio
from reddit_listener import ResearchService, RedditClient, LLMAnalyzer, SQLiteTokenStore

async def main():
    # Initialize components
    token_store = SQLiteTokenStore(
        db_path="tokens.db",
        encryption_key="your-encryption-key"
    )
    
    reddit_client = RedditClient(
        client_id="your-client-id",
        client_secret="your-client-secret",
        user_agent="your-app:v1.0.0",
        redirect_uri="http://localhost:8080/callback",
        token_store=token_store
    )
    
    llm_analyzer = LLMAnalyzer(
        api_key="your-openrouter-key",
        model="minimax/minimax-m2.1"
    )
    
    service = ResearchService(
        reddit_client=reddit_client,
        llm_analyzer=llm_analyzer
    )
    
    # Phase 1: Discover ideas
    discovery = await service.discover_ideas(
        query="machine learning",
        time_filter="week",
        limit=50
    )
    
    # Phase 2: Get detailed context
    context = await service.get_idea_context(
        query="machine learning",
        idea_title=discovery.content_ideas[0].title
    )
    
    # Use the context for content generation
    print(context.full_post_and_comment_analysis)
    
    # Clean up
    await reddit_client.close()
    await llm_analyzer.close()
    await token_store.close()

asyncio.run(main())
```

## Flask Integration Example

```python
from flask import Flask, jsonify, request
from reddit_listener import SyncResearchService

app = Flask(__name__)
service = SyncResearchService()

@app.route('/api/discover', methods=['POST'])
def discover_ideas():
    """Phase 1: Discover content ideas from Reddit"""
    data = request.json
    query = data.get('query')
    
    if not query:
        return jsonify({'error': 'query is required'}), 400
    
    try:
        discovery = service.discover_ideas(
            query=query,
            time_filter=data.get('time_filter', 'month'),
            limit=data.get('limit', 100)
        )
        
        return jsonify({
            'query': discovery.query,
            'content_ideas': [
                {
                    'title': idea.title,
                    'description': idea.description,
                    'rationale': idea.rationale
                }
                for idea in discovery.content_ideas
            ],
            'pain_points': [
                {
                    'description': pp.description,
                    'solution_summary': pp.solution_summary,
                    'upvotes': pp.upvotes
                }
                for pp in discovery.pain_points
            ],
            'questions': discovery.questions,
            'keywords': discovery.keywords
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/context', methods=['POST'])
def get_context():
    """Phase 2: Get detailed context for a specific idea"""
    data = request.json
    query = data.get('query')
    idea_title = data.get('idea_title')
    
    if not query or not idea_title:
        return jsonify({'error': 'query and idea_title are required'}), 400
    
    try:
        context = service.get_idea_context(query, idea_title)
        
        return jsonify({
            'idea_title': context.idea_title,
            'idea_description': context.idea_description,
            'full_analysis': context.full_post_and_comment_analysis,
            'emotional_aspect': context.emotional_aspect,
            'controversial_aspect': context.controversial_aspect,
            'engagement_signals': context.engagement_signals,
            'knowledge_depth': context.knowledge_depth,
            'category': context.category
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
```

## Search Specific Subreddits

```python
from reddit_listener import SyncResearchService

service = SyncResearchService()

# Search only in specific subreddits
discovery = service.discover_ideas(
    query="python best practices",
    subreddits=["python", "learnpython", "programming"]
)

# The search will only look in r/python, r/learnpython, and r/programming
print(f"Found {len(discovery.content_ideas)} ideas from Python subreddits")
```

## Batch Fetching Performance Tuning

Customize batch behavior based on your needs:

```python
from reddit_listener import SyncResearchService

service = SyncResearchService()

# Fast discovery: smaller batches, stop early
# Best for: Quick responses, high confidence in finding relevant content
discovery = service.discover_ideas(
    query="machine learning",
    batch_size=5,
    min_relevant=2  # Stop after just 2 relevant posts
)

# Thorough discovery: larger batches, more relevant posts
# Best for: Comprehensive analysis, niche topics
discovery = service.discover_ideas(
    query="rust programming",
    batch_size=10,
    min_relevant=5  # Gather 5 relevant posts before stopping
)

# Maximum throughput: fetch all at once (legacy behavior)
# Best for: When you need all posts regardless of relevance
discovery = service.discover_ideas(
    query="web development",
    limit=100,
    batch_size=100,  # Fetch everything in one batch
    min_relevant=100  # Don't stop early
)
```

### Performance Characteristics

| Batch Size | Min Relevant | Use Case | Typical Speed |
|------------|--------------|----------|---------------|
| 5 | 2-3 | Quick lookups, common topics | Fast (2-5s) |
| 10 | 5 | Balanced discovery | Medium (5-10s) |
| 20 | 10 | Comprehensive research | Slower (10-20s) |
| 100 | 100 | Full dataset fetch | Slowest (20-40s) |

## Data Serialization

All dataclasses can be easily serialized:

```python
from dataclasses import asdict
from reddit_listener import SyncResearchService

service = SyncResearchService()
discovery = service.discover_ideas("climate change")

# Convert to dictionary
discovery_dict = asdict(discovery)

# Save to JSON
import json
with open('discovery_results.json', 'w') as f:
    json.dump(discovery_dict, f, indent=2)

# Get context and serialize
context = service.get_idea_context(
    query="climate change",
    idea_title=discovery.content_ideas[0].title
)
context_dict = asdict(context)

with open('context.json', 'w') as f:
    json.dump(context_dict, f, indent=2)
```

## Cache Management

The discovery cache expires after 15 minutes:

```python
service = SyncResearchService()

# Phase 1: Discovery (cached for 15 minutes)
discovery = service.discover_ideas("web development")

# Phase 2: Get context (uses cache)
context1 = service.get_idea_context("web development", discovery.content_ideas[0].title)
context2 = service.get_idea_context("web development", discovery.content_ideas[1].title)

# ... 15+ minutes later ...

# This will raise ValueError: cache expired
try:
    context3 = service.get_idea_context("web development", discovery.content_ideas[2].title)
except ValueError as e:
    print(f"Cache expired: {e}")
    # Re-run discovery
    discovery = service.discover_ideas("web development")
    context3 = service.get_idea_context("web development", discovery.content_ideas[2].title)
```
