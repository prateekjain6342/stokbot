# Slack Bot Integration

Complete guide to the Slack bot implementation, Socket Mode, and Block Kit UI.

## Overview

Reddit Listener uses Slack Bolt SDK to provide an interactive bot interface with rich formatting via Block Kit.

## Architecture

**Location:** `src/reddit_listener/slack/`

### Components

1. **app.py** - Main Slack application and event handlers
2. **blocks.py** - Block Kit UI formatters

### Socket Mode

Uses WebSocket connection instead of HTTP webhooks:

**Advantages:**
- No public URL needed
- No webhook configuration
- Easy local development
- Lower latency
- Automatic reconnection

**How it works:**
```
Slack Server ←→ WebSocket ←→ Your Bot
   (Cloud)                    (Local/Server)
```

## Slash Commands

### /research

**Handler:** `handle_research_command()`

**Flow:**
```
1. User: /research AI trends
2. Bot: "🔍 Researching AI trends..."
3. [Background processing]
4. Bot: [Formatted results with Block Kit]
```

**Implementation:**
```python
@app.command("/research")
async def handle_research_command(ack, command, say, client):
    await ack()  # Acknowledge within 3 seconds
    
    # Show processing message
    await say(f"🔍 Researching {command['text']}...")
    
    # Do research (async)
    results = await research_orchestrator.research(command['text'])
    
    # Send formatted results
    blocks = format_research_results(results)
    await say(blocks=blocks)
```

**Error handling:**
```python
try:
    results = await research_orchestrator.research(query)
except RedditAPIException as e:
    await say(f"❌ Reddit API error: {e}")
except LLMException as e:
    await say(f"❌ Analysis error: {e}")
except Exception as e:
    await say(f"❌ Unexpected error. Please try again.")
    logger.exception(e)
```

### /connect-reddit

**Handler:** `handle_connect_reddit_command()`

**Flow:**
```
1. User: /connect-reddit
2. Bot: [OAuth URL as button]
3. User: [Clicks, authorizes on Reddit]
4. Reddit: [Redirects to callback]
5. Bot: "✅ Connected successfully!"
```

**Implementation:**
```python
@app.command("/connect-reddit")
async def handle_connect_reddit_command(ack, command, say):
    await ack()
    
    user_id = command['user_id']
    oauth_url = generate_oauth_url(user_id)
    
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "Connect your Reddit account:"}
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Authorize Reddit"},
                    "url": oauth_url,
                    "style": "primary"
                }
            ]
        }
    ]
    
    await say(blocks=blocks)
```

## Event Handlers

### App Mentions

**Trigger:** `@reddit-listener help`

**Handler:**
```python
@app.event("app_mention")
async def handle_app_mention(event, say):
    text = event['text'].lower()
    
    if 'help' in text:
        await say(blocks=help_blocks())
    elif 'info' in text:
        await say(blocks=info_blocks())
    else:
        await say("Use `/research [topic]` to start researching!")
```

## Block Kit Formatting

**Location:** `src/reddit_listener/slack/blocks.py`

### Research Results Format

Uses Block Kit for rich, structured output:

```python
def format_research_results(results: Dict) -> List[Dict]:
    blocks = []
    
    # Header
    blocks.extend(header_blocks(results['query']))
    
    # Questions section
    if results['questions']:
        blocks.extend(questions_blocks(results['questions']))
    
    # Keywords section
    if results['keywords']:
        blocks.extend(keywords_blocks(results['keywords']))
    
    # Pain points section
    if results['pain_points']:
        blocks.extend(pain_points_blocks(results['pain_points']))
    
    # Content ideas section
    if results['content_ideas']:
        blocks.extend(content_ideas_blocks(results['content_ideas']))
    
    # Footer with metadata
    blocks.extend(footer_blocks(results['metadata']))
    
    return blocks
```

### Block Components

#### Header
```python
def header_blocks(query: str) -> List[Dict]:
    return [
        {"type": "header", "text": {"type": "plain_text", "text": f"📊 Research: {query}"}},
        {"type": "divider"}
    ]
```

#### Questions Section
```python
def questions_blocks(questions: List[str]) -> List[Dict]:
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*❓ Top 10 Questions*"}
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
            }
        },
        {"type": "divider"}
    ]
```

#### Keywords Section
```python
def keywords_blocks(keywords: List[str]) -> List[Dict]:
    keyword_text = " • ".join(keywords)
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*🔑 Top 10 Keywords*"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": keyword_text}
        },
        {"type": "divider"}
    ]
```

#### Pain Points Section
```python
def pain_points_blocks(pain_points: List[Dict]) -> List[Dict]:
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*😰 Top 10 Pain Points*"}
        }
    ]
    
    for i, pain_point in enumerate(pain_points, 1):
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{i}. {pain_point['problem']}*\n"
                    f"💡 Solution: {pain_point['solution']}"
                )
            }
        })
    
    blocks.append({"type": "divider"})
    return blocks
```

#### Content Ideas Section
```python
def content_ideas_blocks(ideas: List[Dict]) -> List[Dict]:
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*✍️ Content Ideas*"}
        }
    ]
    
    for i, idea in enumerate(ideas, 1):
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{i}. {idea['title']}*\n"
                    f"_{idea['rationale']}_"
                )
            }
        })
    
    blocks.append({"type": "divider"})
    return blocks
```

#### Footer
```python
def footer_blocks(metadata: Dict) -> List[Dict]:
    return [
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        f"📈 Analyzed {metadata['posts_count']} posts "
                        f"and {metadata['comments_count']} comments "
                        f"from {metadata['subreddits_count']} subreddits"
                    )
                }
            ]
        }
    ]
```

## Configuration

### Environment Variables

```bash
# Slack Bot Token (starts with xoxb-)
SLACK_BOT_TOKEN=xoxb-your-bot-token

# App-Level Token for Socket Mode (starts with xapp-)
SLACK_APP_TOKEN=xapp-your-app-token

# Signing Secret for request verification
SLACK_SIGNING_SECRET=your-signing-secret
```

### Slack App Settings

**OAuth & Permissions - Bot Token Scopes:**
- `commands` - Create and respond to slash commands
- `chat:write` - Send messages as the bot
- `app_mentions:read` - Receive app mention events

**Slash Commands:**
- `/research` - Research a topic on Reddit
- `/connect-reddit` - Connect Reddit account

**Event Subscriptions:**
- `app_mention` - When bot is mentioned

**Socket Mode:**
- Enabled with App-Level Token

## Error Handling

### User-Facing Errors

```python
async def handle_error(error: Exception, say, context: str):
    """Show user-friendly error messages"""
    
    error_messages = {
        RedditAPIException: "❌ Couldn't connect to Reddit. Please try again.",
        LLMException: "❌ Analysis service temporarily unavailable.",
        RateLimitExceeded: "⏳ Too many requests. Please wait a moment.",
        AuthenticationError: "❌ Authentication failed. Try `/connect-reddit`."
    }
    
    message = error_messages.get(type(error), "❌ Something went wrong. Please try again.")
    await say(message)
    
    # Log for debugging
    logger.error(f"Error in {context}: {error}", exc_info=True)
```

### Slack-Specific Errors

```python
try:
    await say(blocks=blocks)
except SlackApiError as e:
    if e.response['error'] == 'invalid_blocks':
        # Fallback to plain text
        await say(text=format_as_plain_text(results))
    elif e.response['error'] == 'channel_not_found':
        logger.error(f"Channel not found: {e}")
    else:
        raise
```

## Testing

### Local Testing

```bash
# Start bot
python -m reddit_listener

# In Slack, try:
/research test query
@reddit-listener help
/connect-reddit
```

### Mock Testing

```python
import pytest
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

@pytest.fixture
def mock_slack_app():
    app = App(token="xoxb-test")
    return app

def test_research_command(mock_slack_app):
    # Test command handler
    pass
```

## Performance Optimization

### Async Operations
- All handlers use `async def`
- Non-blocking I/O with `await`
- Concurrent request handling

### Response Time
- Acknowledge within 3 seconds (Slack requirement)
- Show "processing" message immediately
- Send results when ready (can take 30-90s)

### Message Chunking
```python
def chunk_blocks(blocks: List[Dict], max_blocks: int = 50) -> List[List[Dict]]:
    """Split into multiple messages if too large"""
    return [blocks[i:i+max_blocks] for i in range(0, len(blocks), max_blocks)]

async def send_chunked_results(say, blocks: List[Dict]):
    for chunk in chunk_blocks(blocks):
        await say(blocks=chunk)
```

## Best Practices

1. **Always acknowledge quickly** - Use `await ack()` within 3 seconds
2. **Show progress** - Let users know bot is working
3. **Handle errors gracefully** - User-friendly messages, log details
4. **Use Block Kit** - Rich formatting improves UX
5. **Test thoroughly** - Both success and failure cases

## Limitations

- **Block limit:** 50 blocks per message (use chunking)
- **Text limit:** 3000 chars per text block
- **Rate limits:** Tier-based (typically 1+ req/sec for bots)
- **Timeout:** 3 seconds to acknowledge commands

## Next Steps

- Learn about [Reddit Integration](reddit-integration.md)
- Explore [LLM Analysis](llm-analysis.md) pipeline
- Review [Troubleshooting](troubleshooting.md) guide
