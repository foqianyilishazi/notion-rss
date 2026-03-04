import logging
import os
from datetime import datetime

import requests

logger = logging.getLogger(__name__)


def send_to_feishu(date: str, text: str) -> bool:
    """
    Send a message to Feishu via webhook.

    Args:
        date: The date string to include in the message
        text: Markdown formatted text content (supports links, headings, etc.)

    Returns:
        bool: True if successful, False otherwise
    """
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    if not webhook_url:
        logger.error("FEISHU_WEBHOOK_URL not set in environment")
        return False

    payload = {
        "msg_type": "text",
        "content": {
            "date": date,
            "text": text
        }
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=30)
        response.raise_for_status()
        logger.info("Feishu message sent successfully at %s", datetime.now().isoformat())
        return True
    except requests.exceptions.RequestException as e:
        logger.error("Failed to send Feishu message: %s", e)
        return False


def send_feed_summary_to_feishu(feed_items: list) -> bool:
    """
    Send all feed items to Feishu in a single message.

    Args:
        feed_items: List of feed item dictionaries with 'title', 'link', 'date', etc.

    Returns:
        bool: True if successful, False otherwise
    """
    if not feed_items:
        logger.info("No feed items to send")
        return True

    today = datetime.now().strftime("%Y-%m-%d")

    lines = [f"📰 RSS Feed 摘要 ({today})", ""]

    for item in feed_items:
        title = item.get("title", "无标题")
        link = item.get("link", "")

        if link:
            lines.append(f"🔗 [{title}]({link})")
        else:
            lines.append(f"{title}")

        lines.append("")

    text_content = "\n".join(lines)

    return send_to_feishu(today, text_content)
