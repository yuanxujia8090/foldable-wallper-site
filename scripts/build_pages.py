#!/usr/bin/env python3
"""Rebuild the page-embedded wallpaper payload (``#app-data``) from the data files.

The two language pages (``public/index.html`` = en, ``public/zh/index.html`` =
zh-Hans) each ship their own strings plus an inline ``items`` array. Publishing
(``scripts/publish.py``) only rewrites ``public/data/*.json``, so run this after
every publish/unpublish to make the change visible to visitors.

Scope: this script rewrites the ``items`` array only. Page markup, translatable
strings, devices/styles/ratios and language links stay hand-written; entries
already present in the page are kept verbatim (their search haystacks are
hand-written), new entries are generated from the data files.

    python3 scripts/build_pages.py            # write pages
    python3 scripts/build_pages.py --check    # verify pages are in sync
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
PAGES = {
    "en": PUBLIC / "index.html",
    "zh-Hans": PUBLIC / "zh" / "index.html",
}
DATA = {
    "en": PUBLIC / "data" / "wallpapers.json",
    "zh-Hans": PUBLIC / "data" / "wallpapers.zh-Hans.json",
}

APP_DATA_RE = re.compile(
    r'(<script type="application/json" id="app-data">)(.*?)(</script>)', re.S
)

# Thumbnail placeholder widths used by the contact sheet, by item ratio.
THUMB_W = {"desktop": 213, "phone-portrait": 68, "foldable": 144}

# zh-Hans synonyms added to the search haystack so Chinese queries hit.
ZH_LABELS = {
    "styles": {"dark": "暗色", "minimal": "极简", "nature": "自然", "abstract": "抽象"},
    "ratios": {"phone-portrait": "手机", "desktop": "桌面", "foldable": "折叠屏"},
    "devices": {"iphone": "iPhone", "pixel": "Pixel", "foldable": "折叠屏"},
}


def is_published(item: dict) -> bool:
    return item.get("status", "published") == "published"


def image_urls(item: dict) -> dict:
    """Pick the three URLs the UI needs; new items ship an ``img`` block, old ones do not."""
    raw_img = item.get("img")
    img = raw_img if isinstance(raw_img, dict) else {}
    full = item.get("cdn_url_full") or item.get("cdn_url_preview") or item.get("cdn_url") or ""
    full = img.get("full") or full
    thumb = img.get("thumb") or full
    strip = img.get("strip") or thumb
    return {"thumb": thumb, "strip": strip, "full": full}


def search_haystack(item: dict, zh: dict | None) -> str:
    zh = zh or {}
    parts = [item.get("title", ""), zh.get("title", ""), item.get("id", "")]
    parts += item.get("tags", [])
    parts += zh.get("searchTerms", [])
    parts.append(item.get("style", ""))
    parts.append(ZH_LABELS["styles"].get(item.get("style", ""), ""))
    parts.append(item.get("ratio", ""))
    parts.append(ZH_LABELS["ratios"].get(item.get("ratio", ""), ""))
    for device in item.get("device_tags", []):
        parts.append(device)
        parts.append(ZH_LABELS["devices"].get(device, ""))
    return " ".join(part for part in parts if part).lower()


def build_item(item: dict, zh: dict | None) -> dict:
    zh = zh or {}
    urls = image_urls(item)
    if not urls["full"]:
        raise SystemExit(f"item {item.get('id')!r} has no image URL")
    return {
        "id": item["id"],
        "title": zh.get("title") or item.get("title") or item["id"],
        "alt": zh.get("alt") or item.get("alt") or item.get("title") or item["id"],
        "ratio": item.get("ratio", "desktop"),
        "style": item.get("style", "minimal"),
        "device_tags": item.get("device_tags", []),
        "tags": item.get("tags", []),
        "created_at": item.get("created_at", ""),
        "w": item.get("w", 0),
        "h": item.get("h", 0),
        "img": urls,
        "download_filename": item.get("download_filename", ""),
        "thumbW": THUMB_W.get(item.get("ratio", "desktop"), 213),
        "search": search_haystack(item, zh),
    }


def load_json(path: Path):
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as err:
        raise SystemExit(f"cannot read {path}: {err}") from err


def page_payload(html: str) -> dict:
    match = APP_DATA_RE.search(html)
    if not match:
        raise SystemExit("no #app-data block found")
    try:
        return json.loads(match.group(2))
    except json.JSONDecodeError as err:
        raise SystemExit(f"#app-data is not valid JSON: {err}") from err


def render_page(path: Path, items: list[dict]) -> str:
    html = path.read_text(encoding="utf-8")
    payload = page_payload(html)
    payload["items"] = items
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return APP_DATA_RE.sub(lambda m: m.group(1) + blob + m.group(3), html, count=1)


def build_items(lang: str, existing: dict[str, dict]) -> list[dict]:
    data = load_json(DATA["en"])
    zh_map = load_json(DATA["zh-Hans"]) if (lang == "zh-Hans" and DATA["zh-Hans"].exists()) else {}
    items: list[dict] = []
    for item in data.get("items", []):
        if not is_published(item):
            continue
        if item["id"] in existing:
            items.append(existing[item["id"]])
        else:
            items.append(build_item(item, zh_map.get(item["id"])))
    return items


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="only report drift")
    args = parser.parse_args(argv)

    drift = 0
    for lang, page in PAGES.items():
        html = page.read_text(encoding="utf-8")
        existing_list = page_payload(html).get("items", [])
        existing = {item["id"]: item for item in existing_list if item.get("id")}
        items = build_items(lang, existing)
        rendered = render_page(page, items)
        changed = rendered != html
        drift += 1 if changed else 0
        if args.check:
            print(f"{page.relative_to(ROOT)}: {'drift' if changed else 'in sync'} ({len(items)} items)")
        elif changed:
            page.write_text(rendered, encoding="utf-8")
            print(f"{page.relative_to(ROOT)}: wrote {len(items)} items")
        else:
            print(f"{page.relative_to(ROOT)}: unchanged ({len(items)} items)")

    if args.check and drift:
        print("run: python3 scripts/build_pages.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
