#!/usr/bin/env bash
# Local fake publish + publishedOnly assertion (no R2 keys required)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
JSON="$ROOT/public/data/wallpapers.json"
BACKUP="$JSON.smoke.bak"
cp "$JSON" "$BACKUP"
trap 'mv "$BACKUP" "$JSON"' EXIT

python3 - << PY
import json
from pathlib import Path
p = Path("$JSON")
doc = json.loads(p.read_text())
fake = {
    "id": "wp-smoke-local",
    "title": "Smoke local fake",
    "cdn_url": "https://picsum.photos/id/1015",
    "status": "published",
    "w": 1600,
    "h": 900,
    "ratio": "desktop",
    "style": "nature",
    "device_tags": ["desktop"],
    "tags": ["smoke"],
    "created_at": "2026-11-01",
    "batch_id": "smoke-local",
    "object_key": "wallpapers/wp-smoke-local/fake.png",
}
items = doc.get("items", [])
items = [i for i in items if i.get("id") != "wp-smoke-local"]
items.append(fake)
# ensure unlisted sample exists
if not any(i.get("id") == "wp-draft" for i in items):
    items.append({
        "id": "wp-draft",
        "title": "Draft (unlisted sample)",
        "cdn_url": "https://picsum.photos/id/999",
        "status": "unlisted",
        "w": 1600, "h": 900, "ratio": "desktop",
        "style": "minimal", "device_tags": ["desktop"], "tags": ["draft"],
        "created_at": "2026-10-29", "batch_id": "smoke-local", "object_key": "",
    })
doc["items"] = items
p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
print("wrote fake published + ensured wp-draft unlisted")
PY

# Assert publishedOnly logic (mirrors wallpapers.js)
node -e '
const fs = require("fs");
const doc = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
function publishedOnly(items) {
  return (items || []).filter(it => !it.status || it.status === "published");
}
const items = Array.isArray(doc) ? doc : (doc.items || []);
const pub = publishedOnly(items);
const ids = new Set(pub.map(i => i.id));
if (!ids.has("wp-smoke-local")) { console.error("FAIL: smoke published missing"); process.exit(1); }
if (ids.has("wp-draft")) { console.error("FAIL: unlisted wp-draft leaked"); process.exit(1); }
const draft = items.find(i => i.id === "wp-draft");
if (!draft || draft.status !== "unlisted") { console.error("FAIL: wp-draft missing"); process.exit(1); }
console.log("PASS publishedOnly: published=" + pub.length + " total=" + items.length + " excluded=wp-draft");
' "$JSON"

# src() full-URL vs picsum
node -e '
function isFullImageUrl(url) {
  if (!url || typeof url !== "string") return false;
  if (!/^https?:\/\//i.test(url)) return false;
  if (/r2\.dev/i.test(url)) return true;
  if (/\.(jpe?g|png|webp)(\?|#|$)/i.test(url)) return true;
  return false;
}
function src(item) {
  var full = item.cdn_url_full || item.cdn_url_preview || (isFullImageUrl(item.cdn_url) ? item.cdn_url : null);
  if (full) return full;
  return (item.cdn_url || "") + "/" + (item.w||1600) + "/" + (item.h||900);
}
const r2 = src({cdn_url:"https://pub.example.r2.dev/wallpapers/a/x.png", w:100, h:100});
const pic = src({cdn_url:"https://picsum.photos/id/1", w:1600, h:900});
if (r2 !== "https://pub.example.r2.dev/wallpapers/a/x.png") { console.error("FAIL r2", r2); process.exit(1); }
if (pic !== "https://picsum.photos/id/1/1600/900") { console.error("FAIL picsum", pic); process.exit(1); }
console.log("PASS src() full URL vs picsum");
'

echo "smoke_local OK"
