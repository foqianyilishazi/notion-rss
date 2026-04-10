import xml.etree.ElementTree as ET


def parse_opml(opml_path: str) -> list[dict]:
    """
    Parse OPML subscriptions into a flat list of feed dicts.

    Returns:
        [
            {
                "title": "少数派",
                "feed_url": "https://sspai.com/feed",
                "site_url": "https://sspai.com",
                "category": "Tech",
                "subcategory": "中文"
            }
        ]
    """
    tree = ET.parse(opml_path)
    root = tree.getroot()
    body = root.find("body")
    if body is None:
        return []

    feeds: list[dict] = []

    def walk(node, parents=None):
        if parents is None:
            parents = []

        for outline in node.findall("outline"):
            text = outline.attrib.get("text") or outline.attrib.get("title") or ""
            xml_url = outline.attrib.get("xmlUrl")
            html_url = outline.attrib.get("htmlUrl")

            if xml_url:
                feeds.append({
                    "title": text or xml_url,
                    "feed_url": xml_url,
                    "site_url": html_url or "",
                    "category": parents[0] if len(parents) > 0 else "",
                    "subcategory": parents[1] if len(parents) > 1 else "",
                })
            else:
                next_parents = parents + ([text] if text else [])
                walk(outline, next_parents)

    walk(body)
    return feeds
