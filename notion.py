import datetime
import logging
import os
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

NOTION_API_TOKEN = os.getenv("NOTION_API_TOKEN")
NOTION_READER_DATABASE_ID = os.getenv("NOTION_READER_DATABASE_ID")
NOTION_FEEDS_DATABASE_ID = os.getenv("NOTION_FEEDS_DATABASE_ID")
NOTION_API_VERSION = "2022-06-28"
NOTION_BASE_URL = "https://api.notion.com/v1"

_MAX_BLOCKS_PER_REQUEST = 100
_REQUEST_TIMEOUT = 30
_ARCHIVE_AFTER_DAYS = 30


def _get_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {NOTION_API_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }


def _query_database_with_pagination(database_id: str, payload: dict) -> list[dict]:
    url = f"{NOTION_BASE_URL}/databases/{database_id}/query"
    all_results: list[dict] = []
    has_more = True
    start_cursor = None

    while has_more:
        req_payload = dict(payload)
        if start_cursor:
            req_payload["start_cursor"] = start_cursor

        response = requests.post(
            url,
            headers=_get_headers(),
            json=req_payload,
            timeout=_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        all_results.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        start_cursor = data.get("next_cursor")

    return all_results


def get_all_feeds_from_notion() -> list[dict]:
    results = _query_database_with_pagination(NOTION_FEEDS_DATABASE_ID, {})
    feeds = []

    for item in results:
        props = item.get("properties", {})
        title_prop = props.get("Title", {}).get("title", [])
        link_prop = props.get("Link", {}).get("url")
        site_url = props.get("Site URL", {}).get("url")
        category = props.get("Category", {}).get("select", {})
        subcategory = props.get("Subcategory", {}).get("select", {})
        feed_id_parts = props.get("Feed ID", {}).get("rich_text", [])

        feeds.append({
            "page_id": item.get("id"),
            "title": title_prop[0].get("plain_text", "") if title_prop else "",
            "feed_url": link_prop or "",
            "site_url": site_url or "",
            "category": category.get("name", "") if category else "",
            "subcategory": subcategory.get("name", "") if subcategory else "",
            "feed_id": feed_id_parts[0].get("plain_text", "") if feed_id_parts else "",
        })

    return feeds


def get_feed_urls_from_notion() -> list[dict]:
    payload = {
        "filter": {
            "property": "Enabled",
            "checkbox": {"equals": True},
        }
    }
    results = _query_database_with_pagination(NOTION_FEEDS_DATABASE_ID, payload)
    feeds = []

    for item in results:
        props = item.get("properties", {})
        title_prop = props.get("Title", {}).get("title", [])
        link_prop = props.get("Link", {}).get("url")
        site_url = props.get("Site URL", {}).get("url")
        category = props.get("Category", {}).get("select", {})
        subcategory = props.get("Subcategory", {}).get("select", {})
        feed_id_parts = props.get("Feed ID", {}).get("rich_text", [])

        feeds.append({
            "title": title_prop[0].get("plain_text", "") if title_prop else "",
            "feedUrl": link_prop or "",
            "site_url": site_url or "",
            "category": category.get("name", "") if category else "",
            "subcategory": subcategory.get("name", "") if subcategory else "",
            "feed_id": feed_id_parts[0].get("plain_text", "") if feed_id_parts else "",
        })

    return feeds


def create_feed_in_notion(feed: dict) -> None:
    payload = {
        "parent": {"database_id": NOTION_FEEDS_DATABASE_ID},
        "properties": {
            "Title": {"title": [{"text": {"content": feed["title"]}}]},
            "Link": {"url": feed["feed_url"]},
            "Site URL": {"url": feed.get("site_url") or None},
            "Category": {"select": {"name": feed["category"]}} if feed.get("category") else None,
            "Subcategory": {"select": {"name": feed["subcategory"]}} if feed.get("subcategory") else None,
            "Feed ID": {"rich_text": [{"text": {"content": feed["feed_url"]}}]},
            "Enabled": {"checkbox": True},
        }
    }
    payload["properties"] = {k: v for k, v in payload["properties"].items() if v is not None}
    requests.post(
        f"{NOTION_BASE_URL}/pages",
        headers=_get_headers(),
        json=payload,
        timeout=_REQUEST_TIMEOUT,
    ).raise_for_status()


def update_feed_in_notion(page_id: str, feed: dict) -> None:
    payload = {
        "properties": {
            "Title": {"title": [{"text": {"content": feed["title"]}}]},
            "Link": {"url": feed["feed_url"]},
            "Site URL": {"url": feed.get("site_url") or None},
            "Category": {"select": {"name": feed["category"]}} if feed.get("category") else None,
            "Subcategory": {"select": {"name": feed["subcategory"]}} if feed.get("subcategory") else None,
            "Feed ID": {"rich_text": [{"text": {"content": feed["feed_url"]}}]},
        }
    }
    payload["properties"] = {k: v for k, v in payload["properties"].items() if v is not None}

    requests.patch(
        f"{NOTION_BASE_URL}/pages/{page_id}",
        headers=_get_headers(),
        json=payload,
        timeout=_REQUEST_TIMEOUT,
    ).raise_for_status()


def get_existing_items_since(days: int = 7) -> tuple[set[str], set[str], set[str]]:
    since_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    payload = {
        "filter": {
            "or": [
                {
                    "property": "Created At",
                    "date": {"on_or_after": since_date.isoformat()},
                }
            ]
        }
    }
    results = _query_database_with_pagination(NOTION_READER_DATABASE_ID, payload)

    titles, links, guids = set(), set(), set()
    for item in results:
        props = item.get("properties", {})
        title_parts = props.get("Title", {}).get("title", [])
        if title_parts:
            titles.add(title_parts[0].get("plain_text", ""))

        link_val = props.get("Link", {}).get("url")
        if link_val:
            links.add(link_val)

        guid_parts = props.get("GUID", {}).get("rich_text", [])
        if guid_parts:
            guids.add(guid_parts[0].get("plain_text", ""))

    return titles, links, guids


def add_feed_item_to_notion(notion_item: dict) -> bool:
    title = notion_item.get("title", "")
    link = notion_item.get("link", "")
    content = notion_item.get("content", [])
    source = notion_item.get("source", "")
    category = notion_item.get("category", "")
    subcategory = notion_item.get("subcategory", "")
    guid = notion_item.get("guid", "")
    published_at = notion_item.get("published_at", "")
    summary = notion_item.get("summary", "")
    cover = notion_item.get("cover", "")

    first_chunk = content[:_MAX_BLOCKS_PER_REQUEST]
    remaining_chunks = [
        content[i:i + _MAX_BLOCKS_PER_REQUEST]
        for i in range(_MAX_BLOCKS_PER_REQUEST, len(content), _MAX_BLOCKS_PER_REQUEST)
    ]

    properties = {
        "Title": {"title": [{"text": {"content": title[:2000]}}]},
        "Link": {"url": link},
        "Source": {"select": {"name": source}} if source else None,
        "Category": {"select": {"name": category}} if category else None,
        "Subcategory": {"select": {"name": subcategory}} if subcategory else None,
        "GUID": {"rich_text": [{"text": {"content": guid[:2000]}}]} if guid else None,
        "Published At": {"date": {"start": published_at}} if published_at else None,
        "Summary": {"rich_text": [{"text": {"content": summary[:2000]}}]} if summary else None,
    }
    properties = {k: v for k, v in properties.items() if v is not None}

    payload = {
        "parent": {"database_id": NOTION_READER_DATABASE_ID},
        "properties": properties,
        "children": first_chunk,
    }

    if cover:
        payload["cover"] = {
            "type": "external",
            "external": {"url": cover}
        }

    try:
        response = requests.post(
            f"{NOTION_BASE_URL}/pages",
            headers=_get_headers(),
            json=payload,
            timeout=_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        page_id = response.json().get("id")
    except requests.exceptions.RequestException as err:
        logger.error("Error adding feed item to Notion: %s", err)
        return False

    for chunk in remaining_chunks:
        try:
            resp = requests.patch(
                f"{NOTION_BASE_URL}/blocks/{page_id}/children",
                headers=_get_headers(),
                json={"children": chunk},
                timeout=_REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
        except requests.exceptions.RequestException as err:
            logger.error("Error appending blocks to page %s: %s", page_id, err)
            return False

    return True


def delete_old_unread_feed_items_from_notion() -> None:
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=_ARCHIVE_AFTER_DAYS)
    payload = {
        "filter": {
            "and": [
                {
                    "property": "Created At",
                    "date": {"on_or_before": cutoff.isoformat()},
                },
                {
                    "property": "Read",
                    "checkbox": {"equals": False},
                },
            ]
        }
    }

    results = _query_database_with_pagination(NOTION_READER_DATABASE_ID, payload)
    for item in results:
        page_id = item.get("id")
        try:
            requests.patch(
                f"{NOTION_BASE_URL}/pages/{page_id}",
                headers=_get_headers(),
                json={"archived": True},
                timeout=_REQUEST_TIMEOUT,
            ).raise_for_status()
        except requests.exceptions.RequestException as err:
            logger.error("Error archiving page %s: %s", page_id, err)
