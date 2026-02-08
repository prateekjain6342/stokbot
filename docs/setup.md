# Setup Guide

Complete installation and configuration guide for Reddit Listener.

## Prerequisites

### 1. Reddit App Setup

Create a Reddit application to access the API:

1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Fill in the form:
   - **Name**: Your app name (e.g., "Reddit Listener")
   - **App type**: Select "web app"
   - **Description**: Optional
   - **About URL**: Optional
   - **Redirect URI**: `http://localhost:8080/callback` (for local development)
4. Click "Create app"
5. Note the following credentials:
   - **Client ID**: String under your app name
   - **Client Secret**: String labeled "secret"

### 2. Slack App Setup

Create a Slack app for bot integration:

1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Enter app name and select workspace
4. Configure the app:

   **Socket Mode:**
   - Go to "Socket Mode" in sidebar
   - Enable Socket Mode
   - Generate App-Level Token with `connections:write` scope
   - Copy the token (starts with `xapp-`)

   **OAuth & Permissions:**
   - Add Bot Token Scopes:
     - `commands` - Create slash commands
     - `chat:write` - Send messages
     - `app_mentions:read` - Read mentions
   - Install app to workspace
   - Copy the "Bot User OAuth Token" (starts with `xoxb-`)

   **Slash Commands:**
   - Create `/research` command
     - Description: "Research a topic on Reddit"
     - Usage hint: `[topic]`
   - Create `/connect-reddit` command
     - Description: "Connect your Reddit account"

   **Event Subscriptions:**
   - Enable Events
   - Subscribe to bot events: `app_mention`

   **App Credentials:**
   - Go to "Basic Information"
   - Copy "Signing Secret"

### 3. OpenRouter API Setup

Get API access for LLM analysis:

1. Go to https://openrouter.ai
2. Sign up for an account
3. Navigate to API Keys section
4. Generate a new API key
5. Add credits to your account
6. Ensure access to your desired model (default: Minimax M2.1)
   - You can change the model using the `OPENROUTER_MODEL` environment variable

## Installation

### Step 1: Clone Repository

```bash
cd /Users/prateek/Areas/Business/Find\ Your\ N/Projects/reddit_listener
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Package

```bash
pip install -e .
```

For development with testing tools:
```bash
pip install -e ".[dev]"
```

### Step 4: Configure Environment

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Generate encryption key:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

3. Edit `.env` with your credentials:
   ```bash
   # Reddit API
   REDDIT_CLIENT_ID=your_client_id
   REDDIT_CLIENT_SECRET=your_client_secret
   REDDIT_USER_AGENT=reddit_listener:v1.0.0 (by /u/your_username)
   REDDIT_REDIRECT_URI=http://localhost:8080/callback

   # Slack API
   SLACK_BOT_TOKEN=xoxb-your-bot-token
   SLACK_APP_TOKEN=xapp-your-app-token
   SLACK_SIGNING_SECRET=your_signing_secret

   # OpenRouter API
   OPENROUTER_API_KEY=your_openrouter_key

   # Security
   ENCRYPTION_KEY=your_generated_encryption_key

   # Optional: Server-side Reddit auth
   REDDIT_USERNAME=your_reddit_username
   REDDIT_PASSWORD=your_reddit_password
   ```

## Running the Bot

### Socket Mode (Recommended)

Start the bot with WebSocket connection (no public URL needed):

```bash
python -m reddit_listener
```

Or using the CLI command:
```bash
reddit-listener
```

The bot will connect to Slack and start listening for commands.

### Verification

1. Open Slack workspace where the app is installed
2. Try the command: `/research test`
3. You should see a response from the bot

## Next Steps

- Read the [Usage Guide](usage.md) to learn how to use the bot
- Review [Security](security.md) best practices
- Check [Troubleshooting](troubleshooting.md) if you encounter issues

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `REDDIT_CLIENT_ID` | Yes | Reddit app client ID |
| `REDDIT_CLIENT_SECRET` | Yes | Reddit app client secret |
| `REDDIT_USER_AGENT` | Yes | User agent string for Reddit API |
| `REDDIT_REDIRECT_URI` | Yes | OAuth redirect URI |
| `REDDIT_USERNAME` | No | For server-side Reddit auth |
| `REDDIT_PASSWORD` | No | For server-side Reddit auth |
| `SLACK_BOT_TOKEN` | Yes | Slack bot user OAuth token |
| `SLACK_APP_TOKEN` | Yes | Slack app-level token for Socket Mode |
| `SLACK_SIGNING_SECRET` | Yes | Slack request signing secret |
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key for LLM |
| `OPENROUTER_MODEL` | No | OpenRouter model to use (default: `minimax/minimax-m2.1`) |
| `ENCRYPTION_KEY` | Yes | AES-256 encryption key (64 hex chars) |
