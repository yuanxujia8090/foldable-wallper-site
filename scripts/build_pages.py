#!/usr/bin/env python3
"""Rebuild the page-embedded payload (``#app-data``), the hero strip and the crawl files.

The two language pages (``public/index.html`` = en, ``public/zh/index.html`` =
zh-Hans) each ship their own strings plus an inline ``items`` array. Publishing
(``scripts/publish.py``) only rewrites ``public/data/*.json``, so run this after
every publish/unpublish to make the change visible to visitors.

Scope: this script rewrites these generated regions and nothing else.

* ``#app-data`` items — page markup, translatable strings, devices/styles/ratios
  and language links stay hand-written; entries already present in the page are
  kept verbatim (their search haystacks are hand-written), new entries are
  generated from the data files.
* the hero strip figures, the contact-sheet grid and the "One lifted" row — all
  picked from published items, so no hand-written image ever ships as a
  placeholder and a new wallpaper can reach every row without editing HTML.
* ``#countLine`` and ``#showNote`` — counts and caption text that used to be
  hand-written and drifted from the data.
* ``public/robots.txt`` and ``public/sitemap.xml`` — built from the single origin
  in ``public/config/site.json``.

A build refuses to write a page that still references ``picsum.photos``.

    python3 scripts/build_pages.py            # write pages
    python3 scripts/build_pages.py --check    # verify pages are in sync
"""

from __future__ import annotations

import argparse
import html
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
SITE_CONFIG = PUBLIC / "config" / "site.json"
ROBOTS = PUBLIC / "robots.txt"
SITEMAP = PUBLIC / "sitemap.xml"

# Crawlable routes, in sitemap order. The two language home pages plus the legal pages.
SITEMAP_PATHS = ["/", "/zh/", "/privacy/", "/copyright/"]

APP_DATA_RE = re.compile(
    r'(<script type="application/json" id="app-data">)(.*?)(</script>)', re.S
)
HERO_RE = re.compile(r'(<div class="hero-strip"[^>]*>)(.*?)(\n[ \t]*</div>)', re.S)
SHEET_RE = re.compile(r'(<div class="sheet-grid" id="sheetGrid">)(.*?)(\n[ \t]*</div>)', re.S)
SHOWCASE_RE = re.compile(r'(<div class="showcase-run" id="showRun">)(.*?)(\n[ \t]*</div>)', re.S)
COUNT_RE = re.compile(r'(<p class="count-line[^"]*" id="countLine"[^>]*>)(.*?)(</p>)', re.S)
SHOW_NOTE_RE = re.compile(r'(<p class="showcase-note" id="showNote"[^>]*>)(.*?)(</p>)', re.S)
PLACEHOLDER_HOST = "picsum.photos"

# Thumbnail placeholder widths used by the contact sheet, by item ratio.
THUMB_W = {"desktop": 213, "phone-portrait": 68, "foldable": 144}
# Contact-sheet cards are laid out at a fixed 120px box height.
CARD_HEIGHT = 120
# "One lifted" row: how many frames and which one is emphasised.
SHOWCASE_COUNT = 7
SHOWCASE_LIFTED = 2
SHOWCASE_HEIGHT = 340

# Hero frames are laid out at a fixed 340px box height; width is derived per item.
HERO_HEIGHT = 340
HERO_COUNT = 14
# Ratio rhythm the hand-written strip used, so the row keeps its alternating shape.
HERO_RATIO_ORDER = [
    "foldable", "phone-portrait", "desktop", "foldable", "phone-portrait",
    "desktop", "foldable", "phone-portrait", "foldable", "desktop",
    "phone-portrait", "foldable", "desktop", "phone-portrait",
]
FALLBACK_W = {"desktop": 480, "phone-portrait": 191, "foldable": 320}

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


def hero_figures(items: list[dict]) -> str:
    """Render the hero strip frames from published items.

    Real photographs win over the picsum placeholders: if enough non-placeholder
    items exist, the strip never shows a stand-in. Items are ordered newest first
    so the latest batch reaches the first screen on the next build.
    """
    usable = [item for item in items if item.get("img", {}).get("thumb")]
    real = [item for item in usable if "picsum.photos" not in item["img"]["thumb"]]
    pool = real if len(real) >= HERO_COUNT else usable
    pool = sorted(pool, key=lambda item: (item.get("created_at", ""), item["id"]), reverse=True)
    if not pool:
        return ""

    by_ratio: dict[str, list[dict]] = {}
    for item in pool:
        by_ratio.setdefault(item.get("ratio", "desktop"), []).append(item)

    picked: list[dict] = []
    for ratio in HERO_RATIO_ORDER:
        bucket = by_ratio.get(ratio)
        if not bucket:
            continue
        picked.append(bucket.pop(0))
        if len(picked) >= HERO_COUNT:
            break
    if len(picked) < HERO_COUNT:
        for item in pool:
            if item in picked:
                continue
            picked.append(item)
            if len(picked) >= HERO_COUNT:
                break

    frames = []
    for index, item in enumerate(picked):
        height = HERO_HEIGHT
        iw, ih = item.get("w") or 0, item.get("h") or 0
        if iw and ih:
            width = max(60, round(HERO_HEIGHT * iw / ih))
        else:
            width = FALLBACK_W.get(item.get("ratio", "desktop"), 480)
        attrs = [
            f'data-id="{html.escape(item["id"], quote=True)}"',
        ]
        if index == 4:
            attrs.append('class="is-lit"')
        img_attrs = [
            f'src="{html.escape(item["img"]["thumb"], quote=True)}"',
            f'alt="{html.escape(item.get("alt") or item.get("title") or item["id"], quote=True)}"',
            f'width="{width}"',
            f'height="{height}"',
        ]
        if index:
            img_attrs.append('loading="lazy"')
        frames.append(f'<figure {" ".join(attrs)}><img {" ".join(img_attrs)}></figure>')
    return "\n".join(frames)


def thumb_width(item: dict) -> int:
    return item.get("thumbW") or THUMB_W.get(item.get("ratio", "desktop"), 213)


def sheet_frames(items: list[dict], strings: dict) -> str:
    """Render the no-JS fallback for the contact sheet from published items."""
    open_template = strings.get("sheet.open") or "Open {title}"
    frames = []
    for item in items:
        if not item.get("img", {}).get("thumb"):
            continue
        title = item.get("title") or item["id"]
        label = open_template.replace("{title}", title)
        frames.append(
            '<figure class="frame" tabindex="0" role="button" data-id="{id}" aria-label="{label}">'
            '<img src="{src}" alt="{alt}" width="{w}" height="{h}" loading="lazy"></figure>'.format(
                id=html.escape(item["id"], quote=True),
                label=html.escape(label, quote=True),
                src=html.escape(item["img"]["thumb"], quote=True),
                alt=html.escape(item.get("alt") or title, quote=True),
                w=thumb_width(item),
                h=CARD_HEIGHT,
            )
        )
    return "\n".join(frames)


def showcase_items(items: list[dict]) -> list[dict]:
    usable = [item for item in items if item.get("img", {}).get("thumb")]
    pool = sorted(usable, key=lambda item: (item.get("created_at", ""), item["id"]), reverse=True)
    return pool[:SHOWCASE_COUNT]


def showcase_frames(picked: list[dict], strings: dict) -> str:
    rows = []
    for index, item in enumerate(picked):
        iw, ih = item.get("w") or 0, item.get("h") or 0
        width = max(60, round(SHOWCASE_HEIGHT * iw / ih)) if iw and ih else FALLBACK_W.get(item.get("ratio", "desktop"), 480)
        ratio_short = strings.get("ratioShort." + item.get("ratio", "")) or item.get("ratio", "")
        cls = ' class="is-lifted"' if index == SHOWCASE_LIFTED else ""
        rows.append(
            '<div><figure data-id="{id}"{cls}><img src="{src}" alt="{alt}" width="{w}" height="{h}" loading="lazy"></figure>'
            '<div class="frame-cap"><span>{title}</span><span>{ratio}</span></div></div>'.format(
                id=html.escape(item["id"], quote=True),
                cls=cls,
                src=html.escape(item["img"]["thumb"], quote=True),
                alt=html.escape(item.get("alt") or item.get("title") or item["id"], quote=True),
                w=width,
                h=SHOWCASE_HEIGHT,
                title=html.escape(item.get("title") or item["id"]),
                ratio=html.escape(ratio_short),
            )
        )
    return "\n".join(rows)


def showcase_note(picked: list[dict], strings: dict) -> str:
    if not picked:
        return ""
    lifted = picked[min(SHOWCASE_LIFTED, len(picked) - 1)]
    style = strings.get("style." + lifted.get("style", "")) or lifted.get("style", "")
    ratio = strings.get("ratio." + lifted.get("ratio", "")) or lifted.get("ratio", "")
    template = strings.get("showcase.noteWith") or "{title} — {style}, {ratio}."
    return template.replace("{title}", lifted.get("title") or lifted["id"]).replace(
        "{style}", style).replace("{ratio}", ratio)


def count_line(items: list[dict], strings: dict) -> str:
    template = strings.get("find.count") or "{visible} of {total} frames in view"
    total = f"{len(items):,}"
    return template.replace("{visible}", total).replace("{total}", total)


def rel(path: Path) -> Path | str:
    """Path relative to ROOT for messages; falls back to the raw path."""
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return path


def render_page(path: Path, items: list[dict]) -> str:
    html_text = path.read_text(encoding="utf-8")
    payload = page_payload(html_text)
    payload["items"] = items
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    rendered = APP_DATA_RE.sub(lambda m: m.group(1) + blob + m.group(3), html_text, count=1)
    if not HERO_RE.search(rendered):
        raise SystemExit(f"{path.relative_to(ROOT)}: no hero-strip block found")
    hero = hero_figures(items)
    rendered = HERO_RE.sub(lambda m: m.group(1) + "\n" + hero + m.group(3), rendered, count=1)

    strings = payload.get("strings") or {}
    for pattern, replacement, label in (
        (SHEET_RE, sheet_frames(items, strings), "sheet-grid"),
        (SHOWCASE_RE, showcase_frames(showcase_items(items), strings), "showcase-run"),
        (COUNT_RE, count_line(items, strings), "countLine"),
        (SHOW_NOTE_RE, showcase_note(showcase_items(items), strings), "showNote"),
    ):
        if not pattern.search(rendered):
            raise SystemExit(f"{path.relative_to(ROOT)}: no {label} block found")
        rendered = pattern.sub(lambda m, r=replacement: m.group(1) + r + m.group(3), rendered, count=1)

    if PLACEHOLDER_HOST in rendered:
        raise SystemExit(
            f"{rel(path)}: output still references {PLACEHOLDER_HOST}; "
            "unpublish the placeholder items or fix the data before deploying"
        )
    return rendered


def site_origin() -> str:
    config = load_json(SITE_CONFIG)
    origin = str(config.get("origin") or "").rstrip("/")
    if not origin.startswith("https://"):
        raise SystemExit(f"{SITE_CONFIG.relative_to(ROOT)}: origin must be an https URL")
    return origin


def render_crawl_files(origin: str) -> dict[Path, str]:
    sitemap = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    sitemap += [f"  <url><loc>{origin}{path}</loc></url>" for path in SITEMAP_PATHS]
    sitemap.append("</urlset>")
    robots = "User-agent: *\nAllow: /\n\nSitemap: " + origin + "/sitemap.xml\n"
    return {ROBOTS: robots, SITEMAP: "\n".join(sitemap) + "\n"}


def write_or_check(paths: dict[Path, str], check: bool) -> int:
    drift = 0
    for path, content in paths.items():
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        changed = current != content
        if changed:
            drift += 1
        if check:
            print(f"{path.relative_to(ROOT)}: {'drift' if changed else 'in sync'}")
        elif changed:
            path.write_text(content, encoding="utf-8")
            print(f"{path.relative_to(ROOT)}: wrote")
        else:
            print(f"{path.relative_to(ROOT)}: unchanged")
    return drift


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
        html_text = page.read_text(encoding="utf-8")
        existing_list = page_payload(html_text).get("items", [])
        existing = {item["id"]: item for item in existing_list if item.get("id")}
        items = build_items(lang, existing)
        rendered = render_page(page, items)
        changed = rendered != html_text
        drift += 1 if changed else 0
        if args.check:
            print(f"{page.relative_to(ROOT)}: {'drift' if changed else 'in sync'} ({len(items)} items)")
        elif changed:
            page.write_text(rendered, encoding="utf-8")
            print(f"{page.relative_to(ROOT)}: wrote {len(items)} items")
        else:
            print(f"{page.relative_to(ROOT)}: unchanged ({len(items)} items)")

    drift += write_or_check(render_crawl_files(site_origin()), args.check)

    if args.check and drift:
        print("run: python3 scripts/build_pages.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
