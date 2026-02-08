"""Slack Block Kit UI formatters."""

from typing import Any, Dict, List

from ..analysis.llm import ContentIdea, PainPoint
from ..core.research import ResearchResult


def format_research_results(result: ResearchResult) -> List[Dict[str, Any]]:
    """Format research results as Slack Block Kit blocks.

    Args:
        result: Research results to format

    Returns:
        List of Slack Block Kit blocks
    """
    blocks = []

    # Header
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"📊 Research Results: {result.query}",
        }
    })

    blocks.append({"type": "divider"})

    # Section 1: Top Questions
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*🤔 Top 10 Questions People Are Asking:*"
        }
    })

    if result.questions:
        questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(result.questions)])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": questions_text
            }
        })
    else:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "_No questions found_"
            }
        })

    blocks.append({"type": "divider"})

    # Section 2: Keywords
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*🔑 Top Keywords & Phrases:*"
        }
    })

    if result.keywords:
        keywords_text = " • ".join([f"`{k}`" for k in result.keywords])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": keywords_text
            }
        })
    else:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "_No keywords found_"
            }
        })

    blocks.append({"type": "divider"})

    # Section 3: Pain Points
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*😰 Top 10 Pain Points & Community Solutions:*"
        }
    })

    if result.pain_points:
        for i, pp in enumerate(result.pain_points, 1):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*{i}. {pp.description}* (↑ {pp.upvotes})\n"
                        f"💡 _Solution:_ {pp.solution_summary}"
                    )
                }
            })
    else:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "_No pain points identified_"
            }
        })

    blocks.append({"type": "divider"})

    # Section 4: Content Ideas
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*✍️ Content Ideas:*"
        }
    })

    if result.content_ideas:
        for i, idea in enumerate(result.content_ideas, 1):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*{i}. {idea.title}*\n"
                        f"{idea.description}\n"
                        f"_Why:_ {idea.rationale}"
                    )
                }
            })
    else:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "_No content ideas generated_"
            }
        })

    blocks.append({"type": "divider"})

    # Footer
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": "📡 _Powered by Reddit API & Minimax M2.1_"
            }
        ]
    })

    return blocks


def format_error_message(error: str) -> List[Dict[str, Any]]:
    """Format an error message as Slack blocks.

    Args:
        error: Error message

    Returns:
        List of Slack Block Kit blocks
    """
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"❌ *Error:* {error}"
            }
        }
    ]


def format_processing_message(query: str) -> List[Dict[str, Any]]:
    """Format a processing message as Slack blocks.

    Args:
        query: Search query being processed

    Returns:
        List of Slack Block Kit blocks
    """
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🔍 Researching *{query}* on Reddit...\n_This may take 30-60 seconds..._"
            }
        }
    ]


def format_auth_required_message() -> List[Dict[str, Any]]:
    """Format a message prompting for Reddit authorization.

    Returns:
        List of Slack Block Kit blocks
    """
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "🔐 *Reddit Authorization Required*\n"
                "Please connect your Reddit account first using `/connect-reddit`"
            }
        }
    ]


def format_auth_success_message() -> List[Dict[str, Any]]:
    """Format a successful authorization message.

    Returns:
        List of Slack Block Kit blocks
    """
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "✅ *Successfully connected to Reddit!*\n"
                "You can now use `/research <query>` to research topics."
            }
        }
    ]
