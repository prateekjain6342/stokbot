# Reddit Listener

A Reddit research tool with Slack Bot integration that extracts real-time insights using Reddit's official API and AI-powered analysis.

Transform Reddit discussions into actionable insights with automated topic research, question extraction, keyword analysis, and AI-generated content ideas—all accessible through Slack.

## ✨ Features

- 🔍 **Reddit Research**: Extract real-time information from Reddit on any topic
- 🤔 **Question Detection**: Identify top 10 questions people are asking
- 🔑 **Keyword Extraction**: Discover relevant keywords and phrases
- 😰 **Pain Point Analysis**: Find community pain points with top-voted solutions
- ✍️ **Content Ideas**: AI-generated content ideas based on Reddit insights
- 💬 **Slack Bot**: Easy-to-use Slack integration with Block Kit UI
- 🔐 **Dual Auth**: Server-side or user OAuth2 authentication with Reddit
- ⚡ **Async Architecture**: Non-blocking I/O with rate limiting and retry logic

## 🚀 Quick Start

### Prerequisites

You'll need API credentials from three services:

1. **Reddit App** (https://www.reddit.com/prefs/apps)
2. **Slack App** (https://api.slack.com/apps)
3. **OpenRouter API** (https://openrouter.ai)

### Installation

1. **Clone and navigate to the repository:**
   ```bash
   git clone <your-repo-url>
   cd reddit_listener
   ```

2. **Create and activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install the package:**
   ```bash
   pip install -e .
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   ```

5. **Generate encryption key and configure `.env`:**
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   
   Add the generated key and your API credentials to `.env`. See [Setup Guide](docs/setup.md) for detailed instructions.

### Running the Bot

Start the bot with:
```bash
python -m reddit_listener
```

Or use the CLI command:
```bash
reddit-listener
```

The bot connects to Slack via Socket Mode (WebSocket) - no public URL needed!

## 💡 Usage

### Slack Commands

**Research a topic:**
```
/research artificial intelligence trends
/research python web frameworks
/research startup marketing strategies
```

**Connect Reddit account (optional):**
```
/connect-reddit
```

**Get help:**
```
@reddit-listener help
```

### What You Get

Each research query returns four sections:

1. **❓ Top 10 Questions**: Questions people are actively asking about your topic
2. **🔑 Top 10 Keywords**: Relevant keywords and phrases for SEO and content targeting
3. **😰 Top 10 Pain Points**: Community problems with summarized top-voted solutions
4. **✍️ Content Ideas**: AI-generated content ideas with rationale based on Reddit insights

Results are formatted using Slack Block Kit for an interactive experience.

**Processing time:** 30-90 seconds depending on topic complexity.

See the [Usage Guide](docs/usage.md) for detailed examples and best practices.

## 🏗️ Architecture

Built with Python 3.9+ and designed for serverless deployment:

- **Reddit API**: `asyncpraw` with intelligent rate limiting and exponential backoff
- **LLM Analysis**: OpenRouter API (default: Minimax M2.1, configurable via `OPENROUTER_MODEL`) for pain point extraction and content ideation
- **Slack Bot**: Socket Mode integration with Block Kit UI (no public URL required)
- **Token Storage**: Encrypted SQLite (local) or DynamoDB (production)
- **Security**: AES-256 encryption for OAuth tokens, environment-based secrets management

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Language | Python 3.9+ | Core application |
| Async Framework | asyncio | Non-blocking I/O |
| Reddit Client | asyncpraw | Async Reddit API wrapper |
| Slack Framework | Slack Bolt | Bot event handling |
| LLM Gateway | OpenRouter | Multi-model AI access |
| Storage | SQLite/DynamoDB | Encrypted token storage |
| Encryption | cryptography | AES-256 token encryption |

See the [Architecture Guide](docs/architecture.md) for detailed system design.

## 📁 Project Structure

```
reddit_listener/
├── src/reddit_listener/
│   ├── __main__.py           # Entry point
│   ├── config.py             # Configuration management
│   ├── reddit/               # Reddit API client
│   │   ├── client.py         # Main Reddit client
│   │   ├── rate_limiter.py   # Token bucket rate limiting
│   │   └── retry.py          # Exponential backoff retry
│   ├── analysis/             # LLM analysis
│   │   └── llm.py            # OpenRouter integration
│   ├── core/                 # Core business logic
│   │   └── research.py       # Research orchestration
│   ├── storage/              # Token storage
│   │   ├── base.py           # Abstract interface
│   │   └── sqlite.py         # SQLite implementation
│   └── slack/                # Slack integration
│       ├── app.py            # Bot event handlers
│       └── blocks.py         # Block Kit formatters
├── docs/                     # Documentation
├── tests/                    # Test suite
├── pyproject.toml           # Project configuration
└── .env.example             # Environment template
```

## 🛠️ Development

### Install Development Dependencies

```bash
pip install -e ".[dev]"
```

This includes:
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `black` - Code formatting
- `ruff` - Fast Python linter
- `mypy` - Static type checking

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black src/

# Lint
ruff check src/

# Type check
mypy src/
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linters
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 🚢 Deployment

### Option 1: Simple Hosting (Recommended for Starters)

Deploy on any platform that supports Python applications:

- **Railway** (https://railway.app)
- **Render** (https://render.com)
- **Fly.io** (https://fly.io)

**Requirements:**
- Socket Mode enabled
- Environment variables configured
- Python 3.9+ runtime

### Option 2: AWS Lambda (Production)

For serverless deployment with auto-scaling:

1. Switch Slack app to HTTP mode
2. Migrate token storage to DynamoDB
3. Configure Lambda Function URLs
4. Set up AWS Secrets Manager for credentials
5. Add provisioned concurrency for cold start mitigation

See the [Deployment Guide](docs/deployment.md) for step-by-step instructions.

## 🔒 Security

This project implements several security best practices:

- ✅ **Encrypted Storage**: OAuth tokens encrypted at rest with AES-256
- ✅ **Environment Secrets**: No credentials committed to version control
- ✅ **CSRF Protection**: OAuth flows protected against cross-site attacks
- ✅ **Rate Limiting**: Prevents API abuse and respects service limits
- ✅ **Secure Logging**: No credentials exposed in logs or error messages

See the [Security Guide](docs/security.md) for more details.

## 🐛 Troubleshooting

### Bot Not Responding in Slack

- Verify `SLACK_APP_TOKEN` starts with `xapp-`
- Check Socket Mode is enabled in Slack app settings
- Ensure bot is invited to the channel where you're testing
- Check bot process is running without errors

### Reddit API Errors

- Verify rate limiting (max 60 requests/minute with OAuth)
- Check `REDDIT_USER_AGENT` follows format: `app_name:version (by /u/username)`
- Ensure `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` are correct
- Confirm redirect URI matches your app configuration

### OpenRouter Timeout or Errors

- The default model (Minimax M2.1) can take 30-60 seconds for complex analysis
- You can change the model via `OPENROUTER_MODEL` environment variable (e.g., `OPENROUTER_MODEL=anthropic/claude-3-sonnet`)
- Check your OpenRouter account has sufficient credits
- Verify `OPENROUTER_API_KEY` is valid
- Check OpenRouter status page for service issues

### Encryption Key Issues

- Ensure `ENCRYPTION_KEY` is exactly 64 hexadecimal characters
- Generate a new key if needed: `python -c "import secrets; print(secrets.token_hex(32))"`
- Note: Changing the key will invalidate existing stored tokens

For more help, see the detailed documentation or open an issue.

## 📚 Documentation

- [Setup Guide](docs/setup.md) - Detailed installation instructions
- [Usage Guide](docs/usage.md) - How to use the bot effectively
- [Architecture](docs/architecture.md) - System design and technical details
- [Reddit Integration](docs/reddit-integration.md) - Reddit API implementation
- [LLM Analysis](docs/llm-analysis.md) - AI analysis pipeline
- [Slack Bot](docs/slack-bot.md) - Slack integration details
- [Security](docs/security.md) - Security best practices
- [Storage](docs/storage.md) - Token storage implementation
- [Deployment](docs/deployment.md) - Deployment options and guides

## 🤝 Contributing

Contributions are welcome! Whether it's bug reports, feature requests, or code contributions, please feel free to open an issue or pull request.

### Development Setup

1. Fork and clone the repository
2. Install development dependencies: `pip install -e ".[dev]"`
3. Make your changes
4. Run tests: `pytest`
5. Check code quality: `black src/ && ruff check src/ && mypy src/`
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [asyncpraw](https://asyncpraw.readthedocs.io/) for Reddit API access
- Powered by [OpenRouter](https://openrouter.ai/) for LLM analysis
- Integrated with [Slack Bolt](https://slack.dev/bolt-python/) for bot functionality
- Uses [cryptography](https://cryptography.io/) for secure token storage

## 📧 Support

- **Issues**: Open a GitHub issue for bug reports or feature requests
- **Documentation**: Check the [docs/](docs/) folder for detailed guides
- **Email**: For private inquiries, contact prateekjain6342@gmail.com

