"""Slack Bot application using Socket Mode."""

import asyncio
import secrets
from typing import Optional

from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp

from ..analysis.llm import LLMAnalyzer
from ..config import get_config
from ..core.research import ResearchService
from ..reddit.client import RedditClient
from ..storage.sqlite import SQLiteTokenStore
from . import blocks


class SlackBot:
    """Slack Bot with Reddit research capabilities."""

    def __init__(self):
        """Initialize Slack bot."""
        self.config = get_config()

        # Initialize Slack app
        self.app = AsyncApp(
            token=self.config.slack_bot_token,
            signing_secret=self.config.slack_signing_secret,
        )

        # Initialize token store
        self.token_store = SQLiteTokenStore(
            db_path=self.config.database_path,
            encryption_key=self.config.encryption_key,
        )

        # Initialize Reddit client
        self.reddit_client = RedditClient(
            client_id=self.config.reddit_client_id,
            client_secret=self.config.reddit_client_secret,
            user_agent=self.config.reddit_user_agent,
            redirect_uri=self.config.reddit_redirect_uri,
            token_store=self.token_store,
        )

        # Initialize LLM analyzer
        self.llm_analyzer = LLMAnalyzer(
            api_key=self.config.openrouter_api_key,
            model=self.config.openrouter_model
        )

        # Initialize research service
        self.research_service = ResearchService(
            reddit_client=self.reddit_client,
            llm_analyzer=self.llm_analyzer,
        )

        # OAuth state storage (in-memory for Phase 1)
        self.oauth_states = {}

        # Register handlers
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register Slack command and event handlers."""

        @self.app.command("/research")
        async def handle_research(ack, command, respond):
            """Handle /research slash command."""
            await ack()

            query = command.get("text", "").strip()
            if not query:
                await respond(
                    blocks=blocks.format_error_message(
                        "Please provide a search query. Usage: `/research <your query>`"
                    )
                )
                return

            team_id = command["team_id"]
            user_id = command["user_id"]

            # Run research in background
            try:
                # Send processing message
                await respond(blocks=blocks.format_processing_message(query))
                
                # Note: For server-side auth, set team_id and user_id to None
                # For user auth, use actual team_id and user_id
                result = await self.research_service.research(
                    query=query,
                    team_id=None,  # Use server-side auth for now
                    user_id=None,
                )

                # Send results
                await respond(blocks=blocks.format_research_results(result))

            except ValueError as e:
                # User needs to authorize Reddit
                if "not authorized" in str(e).lower():
                    await respond(blocks=blocks.format_auth_required_message())
                else:
                    await respond(blocks=blocks.format_error_message(str(e)))
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"Error during research: {error_details}")
                await respond(
                    blocks=blocks.format_error_message(
                        f"An error occurred: {str(e)}"
                    )
                )

        @self.app.command("/connect-reddit")
        async def handle_connect_reddit(ack, command, respond):
            """Handle /connect-reddit slash command for OAuth."""
            await ack()

            team_id = command["team_id"]
            user_id = command["user_id"]

            # Generate OAuth state for CSRF protection
            state = secrets.token_urlsafe(32)
            self.oauth_states[state] = {"team_id": team_id, "user_id": user_id}

            # Generate authorization URL
            auth_url = self.reddit_client.get_auth_url(state)

            await respond(
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "🔗 *Connect your Reddit account*\n"
                            "Click the button below to authorize Reddit access:",
                        },
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "Connect Reddit"},
                                "url": auth_url,
                                "style": "primary",
                            }
                        ],
                    },
                ]
            )

        @self.app.event("app_mention")
        async def handle_app_mention(event, say):
            """Handle app mentions."""
            text = event.get("text", "")
            
            if "help" in text.lower():
                await say(
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "*Reddit Listener Bot Commands:*\n\n"
                                "`/research <query>` - Research a topic on Reddit\n"
                                "`/connect-reddit` - Connect your Reddit account (optional)\n\n"
                                "*Example:* `/research artificial intelligence trends`",
                            },
                        }
                    ]
                )
            else:
                await say("👋 Hi! Use `/research <query>` to research topics on Reddit. Type `@reddit-listener help` for more info.")

    async def start(self) -> None:
        """Start the Slack bot in Socket Mode."""
        handler = AsyncSocketModeHandler(self.app, self.config.slack_app_token)
        await handler.start_async()

    async def close(self) -> None:
        """Close all connections."""
        await self.token_store.close()
        await self.reddit_client.close()
        await self.llm_analyzer.close()


# For backward compatibility
async def start_bot() -> None:
    """Start the Slack bot."""
    bot = SlackBot()
    print("⚡️ Slack Bot is running in Socket Mode!")
    await bot.start()
