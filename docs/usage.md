# Usage Guide

How to use the Reddit Listener Slack bot and understand the outputs.

## Slack Commands

### /research - Research a Topic

Extract real-time insights from Reddit on any topic.

**Syntax:**
```
/research [your topic]
```

**Examples:**
```
/research artificial intelligence trends
/research python web frameworks
/research startup marketing strategies
/research remote work productivity tips
```

**What happens:**
1. Bot acknowledges your request
2. Searches Reddit for relevant discussions
3. Analyzes content using AI
4. Returns formatted insights

**Processing time:** 30-90 seconds depending on topic complexity.

### /connect-reddit - Connect Reddit Account

Connect your personal Reddit account for user-specific authentication (optional).

**Syntax:**
```
/connect-reddit
```

**Flow:**
1. Bot sends you an OAuth authorization link
2. Click the link to authorize on Reddit
3. You'll be redirected back with confirmation
4. Your token is encrypted and stored securely

**Note:** This is optional. The bot can work with server-side credentials.

### @mention - Get Help

Mention the bot to get help or information.

**Examples:**
```
@reddit-listener help
@reddit-listener info
```

## Output Format

Each research query returns four sections:

### 1. Top 10 Questions

Questions people are actively asking about your topic on Reddit.

**Example output:**
```
❓ Top 10 Questions

1. "How do I get started with machine learning in 2024?"
2. "What's the best Python library for NLP?"
3. "Is a CS degree necessary for AI careers?"
...
```

**Use cases:**
- Content creation topics
- FAQ development
- Understanding user concerns

### 2. Top 10 Keywords

Relevant keywords and phrases extracted from discussions.

**Example output:**
```
🔑 Top 10 Keywords

• machine learning
• neural networks
• TensorFlow
• data preprocessing
• model training
...
```

**Use cases:**
- SEO optimization
- Content targeting
- Trend analysis

### 3. Top 10 Pain Points

Community pain points with summarized top-voted solutions.

**Example output:**
```
😰 Top 10 Pain Points

1. **Difficulty understanding mathematical concepts**
   💡 Solution: Start with Andrew Ng's course, focus on intuition before math
   
2. **Lack of quality datasets for practice**
   💡 Solution: Use Kaggle, UCI ML Repository, or create synthetic data
...
```

**Use cases:**
- Product development
- Content addressing real problems
- Market research

### 4. Content Ideas

AI-generated content ideas based on Reddit insights.

**Example output:**
```
✍️ Content Ideas

1. **"5 Machine Learning Projects for Absolute Beginners"**
   Rationale: High demand for beginner-friendly tutorials with practical projects
   
2. **"Why Your ML Model Isn't Working: Common Debugging Steps"**
   Rationale: Debugging is a frequent pain point with few comprehensive guides
...
```

**Use cases:**
- Blog post planning
- Video content ideas
- Course curriculum development

## Best Practices

### Effective Search Queries

**Good queries:**
- Specific topics: `SaaS pricing strategies`
- Trending subjects: `AI coding assistants 2024`
- Niche interests: `sustainable fashion startups`

**Less effective queries:**
- Too broad: `business`
- Single words: `programming`
- Very obscure: `extremely-niche-tech-from-1990`

### Rate Limits

- **Slack commands:** No built-in limit, but consider team usage
- **Reddit API:** 60 requests/minute with OAuth (handled automatically)
- **OpenRouter:** Depends on your plan (check OpenRouter dashboard)

### Interpreting Results

**High confidence results:**
- Multiple corroborating data points
- Recent discussions (past 30 days)
- High engagement (upvotes, comments)

**Lower confidence results:**
- Limited Reddit discussion
- Older content
- Niche or emerging topics

## CLI Usage

If running locally, you can also use the CLI:

```bash
reddit-listener --help
```

**Direct research (without Slack):**
```bash
reddit-listener research "your topic"
```

## Tips & Tricks

1. **Combine keywords:** Use multiple related terms for broader coverage
2. **Time-sensitive topics:** Add year for current information (e.g., "AI trends 2024")
3. **Compare perspectives:** Research similar topics to find patterns
4. **Export results:** Copy from Slack or redirect CLI output to file
5. **Regular monitoring:** Set up recurring research for trend tracking

## Limitations

- **Language:** Primarily English-language Reddit content
- **Recency:** Results based on recent Reddit activity (algorithm-dependent)
- **Subreddit coverage:** Searches across multiple subreddits, may miss private/niche ones
- **AI analysis:** LLM output quality depends on input data quality

## Privacy & Data

- Your queries are processed but not stored long-term
- Reddit OAuth tokens are encrypted at rest
- No personal Reddit data is shared with other users
- See [Security](security.md) for details

## Next Steps

- Learn about [Reddit Integration](reddit-integration.md) details
- Explore [LLM Analysis](llm-analysis.md) capabilities
- Check [Troubleshooting](troubleshooting.md) for common issues
