"""OAuth callback server for Reddit authentication."""

import asyncio
from typing import Dict
from aiohttp import web


class OAuthCallbackServer:
    """Simple HTTP server to handle Reddit OAuth callbacks."""

    def __init__(self, port: int = 8080):
        """Initialize callback server.
        
        Args:
            port: Port to listen on (default: 8080)
        """
        self.port = port
        self.app = web.Application()
        self.app.router.add_get("/callback", self.handle_callback)
        self.runner: web.AppRunner = None
        self.site: web.TCPSite = None
        self.pending_callbacks: Dict[str, asyncio.Future] = {}

    async def handle_callback(self, request: web.Request) -> web.Response:
        """Handle OAuth callback from Reddit.
        
        Args:
            request: Incoming HTTP request with code and state parameters
            
        Returns:
            HTML response to display to user
        """
        code = request.query.get("code")
        state = request.query.get("state")
        error = request.query.get("error")

        if error:
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Reddit Connection Failed</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        max-width: 600px;
                        margin: 100px auto;
                        padding: 40px;
                        text-align: center;
                        background: #f5f5f5;
                    }}
                    .container {{
                        background: white;
                        padding: 40px;
                        border-radius: 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .error {{
                        color: #e01e5a;
                        font-size: 48px;
                        margin-bottom: 20px;
                    }}
                    h1 {{
                        color: #1a1a1a;
                        margin-bottom: 16px;
                    }}
                    p {{
                        color: #616061;
                        line-height: 1.5;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="error">❌</div>
                    <h1>Connection Failed</h1>
                    <p>Reddit authorization was denied or an error occurred: {error}</p>
                    <p>You can close this window and try again in Slack.</p>
                </div>
            </body>
            </html>
            """
            return web.Response(text=html, content_type="text/html", status=400)

        if not code or not state:
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Invalid Request</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        max-width: 600px;
                        margin: 100px auto;
                        padding: 40px;
                        text-align: center;
                        background: #f5f5f5;
                    }}
                    .container {{
                        background: white;
                        padding: 40px;
                        border-radius: 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .error {{
                        color: #e01e5a;
                        font-size: 48px;
                        margin-bottom: 20px;
                    }}
                    h1 {{
                        color: #1a1a1a;
                        margin-bottom: 16px;
                    }}
                    p {{
                        color: #616061;
                        line-height: 1.5;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="error">⚠️</div>
                    <h1>Invalid Request</h1>
                    <p>Missing authorization code or state parameter.</p>
                    <p>You can close this window and try again in Slack.</p>
                </div>
            </body>
            </html>
            """
            return web.Response(text=html, content_type="text/html", status=400)

        # Store the callback result for the pending OAuth flow
        if state in self.pending_callbacks:
            future = self.pending_callbacks[state]
            future.set_result({"code": code, "state": state})

        # Return success page
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Reddit Connected!</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    max-width: 600px;
                    margin: 100px auto;
                    padding: 40px;
                    text-align: center;
                    background: #f5f5f5;
                }
                .container {
                    background: white;
                    padding: 40px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .success {
                    color: #2eb886;
                    font-size: 48px;
                    margin-bottom: 20px;
                }
                h1 {
                    color: #1a1a1a;
                    margin-bottom: 16px;
                }
                p {
                    color: #616061;
                    line-height: 1.5;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success">✅</div>
                <h1>Reddit Connected Successfully!</h1>
                <p>Your Reddit account has been linked.</p>
                <p>You can close this window and return to Slack.</p>
            </div>
        </body>
        </html>
        """
        return web.Response(text=html, content_type="text/html")

    def register_pending_callback(self, state: str) -> asyncio.Future:
        """Register a future to track a pending OAuth callback.
        
        Args:
            state: OAuth state parameter
            
        Returns:
            Future that will be resolved when callback is received
        """
        future = asyncio.Future()
        self.pending_callbacks[state] = future
        return future

    async def start(self):
        """Start the callback server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "localhost", self.port)
        await self.site.start()
        print(f"✅ OAuth callback server started on http://localhost:{self.port}")

    async def stop(self):
        """Stop the callback server."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        print("🛑 OAuth callback server stopped")
