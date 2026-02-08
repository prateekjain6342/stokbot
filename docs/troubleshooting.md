# Troubleshooting

Common issues, solutions, and debugging strategies for Reddit Listener.

## Quick Diagnostic Checklist

When something isn't working:

1. Check environment variables are set correctly
2. Verify API credentials are valid
3. Review recent logs for errors
4. Test network connectivity
5. Confirm bot permissions in Slack
6. Check rate limit status

## Slack Bot Issues

### Bot Not Responding in Slack

**Symptoms:**
- Slash commands don't trigger responses
- Bot appears offline
- No acknowledgment from bot

**Solutions:**

1. **Verify Socket Mode is enabled:**
   - Go to https://api.slack.com/apps → Your App → Socket Mode
   - Ensure "Enable Socket Mode" is ON
   - Confirm App-Level Token is generated (starts with `xapp-`)

2. **Check environment variables:**
   ```bash
   echo $SLACK_BOT_TOKEN    # Should start with xoxb-
   echo $SLACK_APP_TOKEN    # Should start with xapp-
   ```

3. **Verify bot is running:**
   ```bash
   # Check process
   ps aux | grep reddit_listener
   
   # Check logs
   tail -f reddit_listener.log
   ```

4. **Test bot locally:**
   ```bash
   python -m reddit_listener
   # Look for "⚡️ Bolt app is running!"
   ```

5. **Reinstall bot to workspace:**
   - Slack App Settings → OAuth & Permissions
   - Click "Reinstall to Workspace"

### Slash Commands Not Working

**Symptoms:**
- `/research` or `/connect-reddit` shows "Command not found"

**Solutions:**

1. **Create slash commands:**
   - Slack App Settings → Slash Commands → Create New Command
   - `/research` - Description: "Research a topic on Reddit"
   - `/connect-reddit` - Description: "Connect Reddit account"

2. **Verify command is installed:**
   - Type `/` in Slack and look for your commands in the list

3. **Check bot scopes:**
   - OAuth & Permissions → Bot Token Scopes
   - Ensure `commands` scope is added
   - Reinstall bot if you added it

### Bot Acknowledgment Timeout

**Symptoms:**
- "Timed out" message in Slack
- Bot eventually responds but too late

**Cause:** Slack requires acknowledgment within 3 seconds

**Solutions:**

1. **Ensure `await ack()` is called first:**
   ```python
   @app.command("/research")
   async def handle_research(ack, command, say):
       await ack()  # MUST be first
       # ... rest of logic
   ```

2. **Move slow operations after ack:**
   ```python
   @app.command("/research")
   async def handle_research(ack, command, say):
       await ack()  # Immediate
       
       # Show processing message
       await say("🔍 Researching...")
       
       # Then do slow work
       results = await research_topic(command['text'])
       await say(results)
   ```

## Reddit API Issues

### Authentication Errors

**Symptoms:**
- "Invalid credentials" error
- "401 Unauthorized" responses
- OAuth flow fails

**Solutions:**

1. **Verify Reddit app credentials:**
   - Go to https://www.reddit.com/prefs/apps
   - Check Client ID (below app name)
   - Regenerate Secret if needed
   - Ensure app type is "web app"

2. **Check environment variables:**
   ```bash
   echo $REDDIT_CLIENT_ID
   echo $REDDIT_CLIENT_SECRET
   echo $REDDIT_USER_AGENT
   ```

3. **Validate redirect URI:**
   - Must exactly match what's configured in Reddit app
   - For local: `http://localhost:8080/callback`
   - For production: `https://your-domain.com/callback`

4. **Test credentials manually:**
   ```python
   import asyncpraw
   
   reddit = asyncpraw.Reddit(
       client_id="your_id",
       client_secret="your_secret",
       user_agent="test_agent"
   )
   
   # Should not raise error
   print(await reddit.user.me())
   ```

### Rate Limit Exceeded

**Symptoms:**
- "429 Too Many Requests" errors
- Requests failing intermittently
- Slow responses

**Solutions:**

1. **Check current rate limit:**
   - OAuth: 60 requests/minute
   - Script apps: 10 requests/minute
   - Confirm you're using OAuth

2. **Verify rate limiter is working:**
   ```python
   # Should see rate limiter logs
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

3. **Reduce concurrent requests:**
   ```python
   # Limit concurrent API calls
   semaphore = asyncio.Semaphore(5)  # Max 5 concurrent
   
   async with semaphore:
       await reddit_client.search_posts(query)
   ```

4. **Add delays between requests:**
   ```python
   for query in queries:
       results = await client.search_posts(query)
       await asyncio.sleep(1)  # 1 second delay
   ```

### No Search Results Returned

**Symptoms:**
- Empty results list
- "No results found" message

**Solutions:**

1. **Broaden search query:**
   ```python
   # Too specific
   results = await search_posts("very specific niche topic")
   
   # Better
   results = await search_posts("niche topic")
   ```

2. **Adjust time filter:**
   ```python
   # May be too restrictive
   results = await search_posts(query, time_filter="day")
   
   # Try broader
   results = await search_posts(query, time_filter="month")
   ```

3. **Check subreddit availability:**
   ```python
   # Subreddit may be private/banned
   results = await search_posts(query, subreddits=["AskReddit"])
   ```

4. **Verify Reddit is accessible:**
   ```bash
   curl -I https://www.reddit.com
   # Should return 200 OK
   ```

## LLM Analysis Issues

### OpenRouter Timeout

**Symptoms:**
- "Analysis timed out" error
- Requests taking >2 minutes
- No response from LLM

**Solutions:**

1. **Check OpenRouter status:**
   - Visit https://status.openrouter.ai
   - Check for service outages

2. **Verify API key:**
   ```bash
   curl https://openrouter.ai/api/v1/models \
     -H "Authorization: Bearer $OPENROUTER_API_KEY"
   # Should return list of models
   ```

3. **Increase timeout:**
   ```python
   async with session.post(
       url,
       json=payload,
       timeout=aiohttp.ClientTimeout(total=180)  # 3 minutes
   ) as response:
       ...
   ```

4. **Reduce input size:**
   ```python
   # Trim content to reduce processing time
   posts = posts[:10]  # Only top 10 posts
   comments = comments[:30]  # Only top 30 comments
   ```

5. **Try different model:**
   ```bash
   # In your .env file, change the model
   OPENROUTER_MODEL=anthropic/claude-3-haiku  # Faster and cheaper
   # Or try other models
   OPENROUTER_MODEL=openai/gpt-4-turbo
   ```

### Invalid JSON Response from LLM

**Symptoms:**
- "Failed to parse LLM response" error
- Malformed output
- Missing required fields

**Solutions:**

1. **Check response format:**
   ```python
   logger.debug(f"LLM response: {response}")
   # Manually inspect what LLM returned
   ```

2. **Improve prompt:**
   ```python
   # Make JSON requirement explicit
   prompt = """
   IMPORTANT: Respond ONLY with valid JSON. No additional text.
   
   Format:
   {
     "questions": [...],
     "keywords": [...],
     ...
   }
   """
   ```

3. **Strip markdown:**
   ```python
   # LLM may wrap in ```json ... ```
   response = response.strip()
   if response.startswith("```json"):
       response = response[7:-3]
   ```

4. **Add validation:**
   ```python
   try:
       data = json.loads(response)
       validate_structure(data)
   except json.JSONDecodeError:
       logger.error(f"Invalid JSON: {response[:200]}")
       # Fall back to default structure
       data = get_default_structure()
   ```

### Low Quality LLM Output

**Symptoms:**
- Generic/vague insights
- Duplicate items
- Irrelevant content

**Solutions:**

1. **Improve prompt specificity:**
   ```python
   # Vague
   prompt = "Analyze this Reddit data"
   
   # Specific
   prompt = """
   Analyze Reddit discussions about {topic}.
   Extract SPECIFIC, ACTIONABLE insights.
   Avoid generic terms like "various" or "different".
   """
   ```

2. **Provide examples:**
   ```python
   prompt += """
   Example good keyword: "machine learning frameworks"
   Example bad keyword: "various tools"
   """
   ```

3. **Filter output:**
   ```python
   # Remove generic keywords
   generic_terms = ['general', 'various', 'different', 'some']
   keywords = [
       k for k in keywords 
       if not any(g in k.lower() for g in generic_terms)
   ]
   ```

## Storage Issues

### Encryption Errors

**Symptoms:**
- "Encryption failed" error
- "Decryption failed" error
- Unable to store/retrieve tokens

**Solutions:**

1. **Verify encryption key:**
   ```bash
   echo $ENCRYPTION_KEY
   # Should be 64 hex characters (32 bytes)
   ```

2. **Generate new key if needed:**
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

3. **Check key format:**
   ```python
   # Key must be bytes, not string
   key = bytes.fromhex(os.getenv('ENCRYPTION_KEY'))
   # len(key) should be 32
   ```

4. **Test encryption/decryption:**
   ```python
   from reddit_listener.storage.sqlite import SQLiteTokenStorage
   
   key = bytes.fromhex(os.getenv('ENCRYPTION_KEY'))
   storage = SQLiteTokenStorage(":memory:", key)
   await storage.initialize()
   
   # Test
   test_data = {"test": "data"}
   await storage.store_token("test_user", test_data)
   retrieved = await storage.get_token("test_user")
   assert retrieved == test_data
   ```

### Database Locked Error

**Symptoms:**
- "database is locked" error (SQLite)
- Write operations failing

**Solutions:**

1. **Check for multiple instances:**
   ```bash
   ps aux | grep reddit_listener
   # Kill duplicate processes
   ```

2. **Increase timeout:**
   ```python
   async with aiosqlite.connect(db_path, timeout=10.0) as db:
       # Increased from default 5.0
       ...
   ```

3. **Use WAL mode:**
   ```python
   async with aiosqlite.connect(db_path) as db:
       await db.execute("PRAGMA journal_mode=WAL")
       await db.commit()
   ```

## Environment Issues

### Missing Environment Variables

**Symptoms:**
- "Environment variable not set" error
- Bot fails to start

**Solutions:**

1. **List all required variables:**
   ```bash
   # Check if set
   env | grep REDDIT
   env | grep SLACK
   env | grep OPENROUTER
   env | grep ENCRYPTION
   ```

2. **Source .env file:**
   ```bash
   # Load environment variables
   export $(cat .env | xargs)
   
   # Or
   source .env  # If formatted as shell commands
   ```

3. **Verify .env location:**
   ```bash
   # Must be in working directory
   ls -la .env
   pwd
   ```

4. **Check .env format:**
   ```bash
   # Should be:
   VARIABLE_NAME=value
   
   # NOT:
   export VARIABLE_NAME=value
   ```

## Network Issues

### Connection Timeout

**Symptoms:**
- "Connection timed out" errors
- API calls hanging

**Solutions:**

1. **Test connectivity:**
   ```bash
   # Test Reddit
   curl -I https://www.reddit.com
   
   # Test OpenRouter
   curl -I https://openrouter.ai
   
   # Test Slack
   curl -I https://slack.com
   ```

2. **Check firewall:**
   ```bash
   # Ensure HTTPS (443) is allowed outbound
   # Check corporate proxy settings
   ```

3. **Verify DNS:**
   ```bash
   nslookup reddit.com
   nslookup openrouter.ai
   ```

4. **Use proxy if needed:**
   ```python
   # Configure proxy
   async with aiohttp.ClientSession() as session:
       async with session.get(
           url,
           proxy="http://proxy.example.com:8080"
       ) as response:
           ...
   ```

### SSL Certificate Errors

**Symptoms:**
- "SSL: CERTIFICATE_VERIFY_FAILED" error
- HTTPS requests failing

**Solutions:**

1. **Update certificates:**
   ```bash
   # macOS
   /Applications/Python\ 3.9/Install\ Certificates.command
   
   # Linux
   sudo update-ca-certificates
   ```

2. **Check system time:**
   ```bash
   date
   # Incorrect system time can cause certificate errors
   ```

3. **Temporary workaround (not recommended for production):**
   ```python
   import ssl
   
   ssl_context = ssl.create_default_context()
   ssl_context.check_hostname = False
   ssl_context.verify_mode = ssl.CERT_NONE
   
   # Use with caution
   ```

## Performance Issues

### Slow Response Times

**Symptoms:**
- Research queries taking >2 minutes
- Timeout errors
- Poor user experience

**Solutions:**

1. **Profile performance:**
   ```python
   import time
   
   start = time.time()
   results = await research_topic(query)
   print(f"Research took {time.time() - start:.2f}s")
   ```

2. **Optimize Reddit searches:**
   ```python
   # Reduce limits
   posts = await search_posts(query, limit=50)  # Instead of 100
   comments = await fetch_comments(post_id, limit=20)  # Instead of 50
   ```

3. **Parallel operations:**
   ```python
   # Run concurrently
   reddit_task = fetch_reddit_data(query)
   llm_task = analyze_with_llm(data)
   
   reddit_results, llm_results = await asyncio.gather(
       reddit_task, llm_task
   )
   ```

4. **Cache frequent queries:**
   ```python
   # Simple in-memory cache
   cache = {}
   
   async def cached_research(query):
       if query in cache:
           return cache[query]
       
       results = await research_topic(query)
       cache[query] = results
       return results
   ```

## Logging & Debugging

### Enable Debug Logging

```bash
# Set environment variable
export LOG_LEVEL=DEBUG

# Or in .env
LOG_LEVEL=DEBUG
```

```python
# In code
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Viewing Logs

**Local:**
```bash
tail -f reddit_listener.log
```

**Railway:**
```bash
railway logs --follow
```

**Render:**
- View in Render dashboard under "Logs" tab

**AWS Lambda:**
```bash
aws logs tail /aws/lambda/reddit-listener --follow
```

### Log Analysis

```bash
# Search for errors
grep ERROR reddit_listener.log

# Count error types
grep ERROR reddit_listener.log | sort | uniq -c

# Last 100 lines
tail -100 reddit_listener.log
```

## Getting Help

If issues persist:

1. **Check logs thoroughly** - Often contains the answer
2. **Search GitHub issues** - Someone may have had same problem
3. **Create detailed issue:**
   - Environment (OS, Python version)
   - Steps to reproduce
   - Expected vs actual behavior
   - Relevant logs (sanitize secrets!)
   - Configuration (without secrets)

4. **Contact support:** support@findyourn.com

## Next Steps

- Review [Development](development.md) for debugging techniques
- Check [Security](security.md) if security-related
- See [Deployment](deployment.md) for infrastructure issues
