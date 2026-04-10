import logging
from opml_parser import parse_opml
from notion import (
    get_all_feeds_from_notion,
    create_feed_in_notion,
    update_feed_in_notion,
)

logger = logging.getLogger(__name__)


def sync_opml_to_notion(opml_path: str) -> None:
    feeds_from_opml = parse_opml(opml_path)
    existing = get_all_feeds_from_notion()
    existing_map = {item["feed_id"]: item for item in existing if item.get("feed_id")}

    created = 0
    updated = 0

    for feed in feeds_from_opml:
        feed_id = feed["feed_url"]
        old = existing_map.get(feed_id)

        if not old:
            create_feed_in_notion(feed)
            created += 1
            continue

        need_update = (
            old.get("title") != feed["title"]
            or old.get("feed_url") != feed["feed_url"]
            or old.get("site_url") != feed["site_url"]
            or old.get("category") != feed["category"]
            or old.get("subcategory") != feed["subcategory"]
        )

        if need_update:
            update_feed_in_notion(old["page_id"], feed)
            updated += 1

    logger.info("Feeds sync complete: created=%d updated=%d", created, updated)
