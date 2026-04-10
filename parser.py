import logging
import re
from urllib.parse import urlparse
from markdownify import markdownify as turndown

logger = logging.getLogger(__name__)

NOTION_MAX_TEXT_LENGTH = 2000
_LINK_RE = re.compile(r'^\[(.+?)]\((.+?)\)$')
_IMAGE_RE = re.compile(r'^!\[(.*?)\]\((.+?)\)$')
_NUMBERED_LIST_RE = re.compile(r'^\d+\.\s')

_SUPPORTED_IMAGE_EXTENSIONS = (
    ".bmp", ".gif", ".heic", ".jpeg", ".jpg",
    ".png", ".svg", ".tif", ".tiff", ".webp"
)


def html_to_markdown(html_content: str) -> str:
    try:
        return turndown(html_content)
    except Exception as e:
        logger.error("Error converting HTML to Markdown: %s", e)
        return ""


def _truncate(text: str, max_len: int = NOTION_MAX_TEXT_LENGTH) -> str:
    return text[:max_len] if len(text) > max_len else text


def _make_rich_text(content: str, *, link: str | None = None, **annotations) -> list[dict]:
    text_obj: dict = {"content": _truncate(content)}
    if link:
        text_obj["link"] = {"url": link}

    entry: dict = {"type": "text", "text": text_obj}
    if annotations:
        entry["annotations"] = annotations
    return [entry]


def _make_block(block_type: str, rich_text: list[dict]) -> dict:
    return {"type": block_type, block_type: {"rich_text": rich_text}}


def _is_likely_direct_image_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        return (parsed.path or "").lower().endswith(_SUPPORTED_IMAGE_EXTENSIONS)
    except Exception:
        return False


def _make_image_block(url: str, caption: str = "") -> dict:
    return {
        "type": "image",
        "image": {
            "type": "external",
            "external": {"url": url},
            "caption": _make_rich_text(caption) if caption else [],
        }
    }


def markdown_to_notion_blocks(markdown_content: str) -> list[dict]:
    blocks: list[dict] = []

    for raw_line in markdown_content.split("\n"):
        line = raw_line.strip()
        if not line:
            continue

        image_match = _IMAGE_RE.match(line)
        if image_match:
            alt_text, image_url = image_match.groups()
            if _is_likely_direct_image_url(image_url):
                blocks.append(_make_image_block(image_url, alt_text))
            else:
                text = alt_text or image_url
                blocks.append(_make_block("paragraph", _make_rich_text(text, link=image_url)))
            continue

        if line.startswith("### "):
            blocks.append(_make_block("heading_3", _make_rich_text(line[4:])))
        elif line.startswith("## "):
            blocks.append(_make_block("heading_2", _make_rich_text(line[3:])))
        elif line.startswith("# "):
            blocks.append(_make_block("heading_1", _make_rich_text(line[2:])))
        elif line.startswith("- ") or line.startswith("* "):
            blocks.append(_make_block("bulleted_list_item", _make_rich_text(line[2:])))
        elif _NUMBERED_LIST_RE.match(line):
            text = _NUMBERED_LIST_RE.sub("", line, count=1)
            blocks.append(_make_block("numbered_list_item", _make_rich_text(text)))
        elif line.startswith("**") and line.endswith("**") and len(line) > 4:
            blocks.append(_make_block("paragraph", _make_rich_text(line[2:-2], bold=True)))
        elif line.startswith("*") and line.endswith("*") and len(line) > 2:
            blocks.append(_make_block("paragraph", _make_rich_text(line[1:-1], italic=True)))
        elif line.startswith("`") and line.endswith("`") and len(line) > 2:
            blocks.append(_make_block("paragraph", _make_rich_text(line[1:-1], code=True)))
        elif line.startswith("http://") or line.startswith("https://"):
            blocks.append(_make_block("paragraph", _make_rich_text(line, link=line)))
        else:
            link_match = _LINK_RE.match(line)
            if link_match:
                text_part, url_part = link_match.groups()
                blocks.append(_make_block("paragraph", _make_rich_text(text_part, link=url_part)))
            else:
                blocks.append(_make_block("paragraph", _make_rich_text(line)))

    return blocks


def html_to_notion_blocks(html_content: str) -> list[dict]:
    markdown = html_to_markdown(html_content)
    return markdown_to_notion_blocks(markdown)
