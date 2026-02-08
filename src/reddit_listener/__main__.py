"""Main entry point for Reddit Listener."""

import asyncio

from .slack.app import start_bot


def main() -> None:
    """Main entry point."""
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("\n👋 Shutting down Reddit Listener...")


if __name__ == "__main__":
    main()
