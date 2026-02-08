# Reddit Integration

Detailed documentation for Reddit API integration, authentication, and data fetching.

## Overview

Reddit Listener uses the official Reddit API via `asyncpraw` (Async Python Reddit API Wrapper) to fetch real-time data from Reddit.

## Authentication

### Dual Authentication Modes

#### 1. Server-Side Authentication (Default)
Uses app credentials with optional Reddit account:

**Configuration:**
```bash
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USERNAME=your_reddit_username  # Optional
REDDIT_PASSWORD=your_reddit_password  # Optional
```

**Pros:**
- No user interaction needed
- Simpler for backend operations
- Consistent identity

**Cons:**
- Limited to single Reddit account
- Requires storing credentials

#### 2. User OAuth2 (Per-User)
Each Slack user connects their own Reddit account:

**Flow:**
1. User runs `/connect-reddit` in Slack
2. Bot sends OAuth authorization URL
3. User authorizes on Reddit
4. Callback receives token
5. Token encrypted and stored per user

**Pros:**
- User-specific content access
- No shared credentials
- Better for personalization

**Cons:**
- Requires user action
- Token management complexity

## Reddit Client

**Location:** `src/reddit_listener/reddit/client.py`

### Core Features

#### Search Functionality
```python
async def search_posts(
    query: str,
    subreddits: List[str] = None,
    time_filter: str = "month",
    limit: int = 100
) -> List[Post]
```

**Parameters:**
- `query`: Search term
- `subreddits`: List of subreddits or None for all
- `time_filter`: "hour", "day", "week", "month", "year", "all"
- `limit`: Max results (Reddit caps at ~1000)

**Returns:** List of Post objects with:
- `title`, `selftext`, `score`, `num_comments`
- `author`, `subreddit`, `created_utc`
- `url`, `permalink`, `id`

#### Comment Fetching
```python
async def fetch_comments(
    post_id: str,
    limit: int = 100
) -> List[Comment]
```

**Features:**
- Fetches top-level and nested comments
- Includes comment text, score, author
- Sorts by "best" (algorithm-determined relevance)

#### Subreddit Discovery
```python
async def get_related_subreddits(
    query: str,
    limit: int = 10
) -> List[str]
```

Finds relevant subreddits for a topic to expand search coverage.

## Rate Limiting

**Location:** `src/reddit_listener/reddit/rate_limiter.py`

### Token Bucket Algorithm

Implements token bucket for smooth rate limiting:

**Reddit API Limits:**
- **OAuth:** 60 requests/minute
- **Script apps:** 10 requests/minute
- **No auth:** Very limited

**Implementation:**
```python
class RateLimiter:
    def __init__(self, rate: int = 60, period: int = 60):
        self.rate = rate          # Tokens per period
        self.period = period      # Period in seconds
        self.tokens = rate        # Current tokens
        self.last_update = time()
```

**Behavior:**
- Tokens refill at constant rate (1 per second for 60/min)
- Request consumes 1 token
- If no tokens available, waits until refill
- Smooths bursts over time

### Usage
```python
rate_limiter = RateLimiter(rate=60, period=60)

async def make_request():
    async with rate_limiter:
        # Make API request
        pass
```

## Retry Logic

**Location:** `src/reddit_listener/reddit/retry.py`

### Exponential Backoff

Handles transient API failures gracefully:

**Configuration:**
```python
@retry_with_backoff(
    max_retries=3,
    base_delay=2.0,
    max_delay=32.0,
    exceptions=(RequestException, ServerError)
)
async def api_call():
    pass
```

**Backoff schedule:**
- Attempt 1: Immediate
- Attempt 2: 2 seconds
- Attempt 3: 4 seconds
- Attempt 4: 8 seconds
- Max delay: 32 seconds

**Retry conditions:**
- HTTP 429 (Too Many Requests)
- HTTP 500-599 (Server errors)
- Network timeouts
- Connection errors

**No retry:**
- HTTP 400-499 (Client errors, except 429)
- Authentication failures
- Permanent errors

## Data Processing Pipeline

### 1. Query Preprocessing
```python
def preprocess_query(query: str) -> str:
    # Remove special chars
    # Normalize whitespace
    # Extract keywords
    return cleaned_query
```

### 2. Subreddit Selection
```python
async def select_subreddits(query: str) -> List[str]:
    # Option 1: User-specified
    # Option 2: Auto-discover relevant subreddits
    # Option 3: Search all (use None)
    return subreddit_list
```

### 3. Post Fetching & Filtering
```python
async def fetch_and_filter(query: str) -> List[Post]:
    posts = await search_posts(query, limit=100)
    
    # Filter criteria:
    # - Minimum score (e.g., 5 upvotes)
    # - Minimum comments (e.g., 3 comments)
    # - Recency (past month)
    # - Relevance score
    
    return filtered_posts[:50]  # Top 50
```

### 4. Comment Extraction
```python
async def extract_top_comments(post: Post, limit: int = 20):
    comments = await fetch_comments(post.id, limit=limit)
    
    # Sort by score
    # Filter by length (avoid one-liners)
    # Return structured data
    
    return top_comments
```

### 5. Content Aggregation
```python
def aggregate_content(posts: List[Post], comments: List[Comment]) -> Dict:
    return {
        "posts": [{"title": p.title, "text": p.selftext, ...} for p in posts],
        "comments": [{"text": c.body, "score": c.score, ...} for c in comments],
        "metadata": {
            "total_posts": len(posts),
            "total_comments": len(comments),
            "subreddits": list(set(p.subreddit for p in posts))
        }
    }
```

## Best Practices

### 1. Efficient Searching
- Use specific subreddits when possible (faster, more relevant)
- Set appropriate time filters (recent = more relevant)
- Limit results to what you'll actually process

### 2. Respecting Rate Limits
- Use built-in rate limiter (automatic)
- Batch operations when possible
- Cache results when appropriate

### 3. Error Handling
```python
try:
    posts = await reddit_client.search_posts(query)
except RedditAPIException as e:
    # Handle Reddit-specific errors
    logger.error(f"Reddit API error: {e}")
except RateLimitExceeded:
    # Handle rate limiting
    logger.warning("Rate limit exceeded, backing off")
except Exception as e:
    # Handle unexpected errors
    logger.error(f"Unexpected error: {e}")
```

### 4. Data Quality
- Filter low-quality posts (low score, few comments)
- Check for removed/deleted content
- Validate text length and format
- Remove duplicates

## API Quotas & Costs

### Reddit API
- **Cost:** Free (OAuth)
- **Rate limit:** 60 requests/minute
- **Daily cap:** None specified (respect rate limits)

### Typical Usage
For a single research query:
- Subreddit search: 1-3 requests
- Post search: 1-5 requests
- Comment fetching: 5-20 requests
- **Total:** ~10-30 requests per query

**Daily capacity:** 
- 60 req/min × 60 min = 3,600 requests/hour
- Can handle ~120-360 queries/hour

## Troubleshooting

### Common Issues

**"Invalid credentials" error:**
- Verify `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET`
- Ensure Reddit app type is "web app"
- Check redirect URI matches

**Rate limit exceeded:**
- Check if multiple instances are running
- Reduce `limit` parameters in searches
- Increase delays between operations

**No results returned:**
- Query may be too specific
- Try broader search terms
- Check time_filter (e.g., "month" vs "year")
- Verify subreddits exist and are accessible

**Timeout errors:**
- Reddit API may be slow/down
- Retry logic should handle automatically
- Check network connectivity

## Advanced Features

### Custom Sorting
```python
# Sort by relevance (default)
posts = await search_posts(query, sort="relevance")

# Sort by recency
posts = await search_posts(query, sort="new")

# Sort by engagement
posts = await search_posts(query, sort="hot")
```

### Filtering by Flair
```python
# Search posts with specific flair
posts = await search_posts(
    query=f"{topic} flair:Discussion",
    subreddits=["Python"]
)
```

### Getting Post Details
```python
# Fetch full post with all comments
post = await reddit_client.get_post(post_id, fetch_comments=True)
```

## Security Considerations

- OAuth tokens stored encrypted (see [Security](security.md))
- User agent identifies your app to Reddit
- No personal data shared across users
- Tokens expire and auto-refresh
- Rate limiting prevents abuse

## Next Steps

- Learn about [LLM Analysis](llm-analysis.md) of Reddit data
- Review [Storage](storage.md) for token management
- Check [Troubleshooting](troubleshooting.md) for issues
