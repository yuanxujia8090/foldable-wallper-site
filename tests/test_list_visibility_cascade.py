#!/usr/bin/env python3
"""STATIC cascade regression for list/category scroll visibility.

This is a stylesheet cascade check, not a browser computed-style or paint test.
It cannot replace a real browser. Do not launch a browser from here.

Behavior under test (not a required selector spelling):
when JS is enabled on the document element and a list/category scroll region
(#find, #sheet) is in the in-view state that the page script applies, author
CSS in the default (non-reduced-motion) cascade must not resolve that region
to opacity 0.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    "en": ROOT / "public" / "index.html",
    "zh": ROOT / "public" / "zh" / "index.html",
}
APP_JS = ROOT / "public" / "app.js"
REGION_IDS = ("find", "sheet")


# --- minimal static cascade (top-level rules only; @media / @keyframes skipped)


def _strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def extract_style(html: str) -> str:
    match = re.search(r"<style>(.*?)</style>", html, flags=re.S)
    if not match:
        raise SystemExit("FAIL: no <style> block")
    return match.group(1)


def iter_top_level_rules(css: str):
    css = _strip_comments(css)
    i, n = 0, len(css)
    while i < n:
        while i < n and css[i].isspace():
            i += 1
        if i >= n:
            break
        if css.startswith("@", i):
            # skip at-rule; consume to ; or balanced block
            j = i + 1
            while j < n and css[j] not in "{;":
                j += 1
            if j < n and css[j] == ";":
                i = j + 1
                continue
            depth = 0
            while j < n:
                if css[j] == "{":
                    depth += 1
                elif css[j] == "}":
                    depth -= 1
                    if depth == 0:
                        j += 1
                        break
                j += 1
            i = j
            continue
        # style rule
        brace = css.find("{", i)
        if brace < 0:
            break
        prelude = css[i:brace].strip()
        depth = 0
        j = brace
        while j < n:
            if css[j] == "{":
                depth += 1
            elif css[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        body = css[brace + 1 : j]
        yield prelude, body, i
        i = j + 1


def parse_decls(body: str) -> list[tuple[str, str, bool]]:
    decls = []
    for raw in body.split(";"):
        raw = raw.strip()
        if not raw or ":" not in raw:
            continue
        prop, _, value = raw.partition(":")
        prop = prop.strip().lower()
        value = value.strip()
        important = False
        if value.lower().endswith("!important"):
            important = True
            value = value[: -len("!important")].rstrip().rstrip().strip()
            if value.endswith("!important"):
                pass
            value = re.sub(r"\s*!important\s*$", "", value, flags=re.I).strip()
            important = True
        decls.append((prop, value, important))
    return decls


@dataclass
class El:
    tag: str
    el_id: str
    classes: set[str]
    parent: "El | None" = None


def parse_simple(seq: str) -> dict:
    """Parse a compound simple selector (no combinators)."""
    tag = None
    el_id = None
    classes: set[str] = set()
    pseudos: list[str] = []
    i, n = 0, len(seq)
    if n == 0:
        return {"tag": None, "id": None, "classes": classes, "pseudos": pseudos, "ok": False}
    if seq[0] not in ".#:[*" and (seq[0].isalpha() or seq[0] == "_"):
        m = re.match(r"[A-Za-z_][\w-]*", seq)
        tag = m.group(0).lower()
        i = m.end()
    elif seq[0] == "*":
        tag = "*"
        i = 1
    while i < n:
        ch = seq[i]
        if ch == ".":
            m = re.match(r"\.(-?[_a-zA-Z]+[\w-]*)", seq[i:])
            if not m:
                return {"tag": tag, "id": el_id, "classes": classes, "pseudos": pseudos, "ok": False}
            classes.add(m.group(1))
            i += m.end()
        elif ch == "#":
            m = re.match(r"#(-?[_a-zA-Z]+[\w-]*)", seq[i:])
            if not m:
                return {"tag": tag, "id": el_id, "classes": classes, "pseudos": pseudos, "ok": False}
            el_id = m.group(1)
            i += m.end()
        elif ch == ":":
            # skip pseudo-class / pseudo-element, record name
            if i + 1 < n and seq[i + 1] == ":":
                i += 2
            else:
                i += 1
            m = re.match(r"[A-Za-z_-][\w-]*", seq[i:])
            if not m:
                return {"tag": tag, "id": el_id, "classes": classes, "pseudos": pseudos, "ok": False}
            name = m.group(0).lower()
            i += m.end()
            if i < n and seq[i] == "(":
                depth = 0
                while i < n:
                    if seq[i] == "(":
                        depth += 1
                    elif seq[i] == ")":
                        depth -= 1
                        i += 1
                        if depth == 0:
                            break
                        continue
                    i += 1
            # state-based pseudos do not match the default fixture
            if name not in {"root", "not", "nth-child", "nth-of-type", "first-child", "last-child", "only-child"}:
                if name in {"hover", "focus", "focus-visible", "active", "visited", "focus-within"}:
                    pseudos.append(name)
                else:
                    # unknown / element-state: treat as not matching the static fixture
                    if name not in {"root"}:
                        pseudos.append(name)
        elif ch == "[":
            close = seq.find("]", i)
            if close < 0:
                return {"tag": tag, "id": el_id, "classes": classes, "pseudos": pseudos, "ok": False}
            # attribute selectors: no attributes on the fixture unless we add them
            pseudos.append("attr")
            i = close + 1
        else:
            return {"tag": tag, "id": el_id, "classes": classes, "pseudos": pseudos, "ok": False}
    return {"tag": tag, "id": el_id, "classes": classes, "pseudos": pseudos, "ok": True}


def specificity(simples: list[dict]) -> tuple[int, int, int]:
    a = b = c = 0
    for s in simples:
        if s["id"]:
            a += 1
        b += len(s["classes"])
        # count pseudos that are like classes except :not / :root quirks
        for p in s["pseudos"]:
            if p != "attr":
                b += 1
            else:
                b += 1
        if s["tag"] and s["tag"] != "*":
            c += 1
    return (a, b, c)


def tokenize_selector(selector: str) -> list[tuple[str, str]] | None:
    selector = re.sub(r"\s+", " ", selector.strip())
    if not selector:
        return None
    tokens: list[tuple[str, str]] = []
    buf = []
    i, n = 0, len(selector)
    combinators = {">", "+", "~"}
    while i < n:
        ch = selector[i]
        if ch in combinators:
            if buf:
                tokens.append(("simple", "".join(buf).strip()))
                buf = []
            tokens.append(("comb", ch))
            i += 1
            while i < n and selector[i] == " ":
                i += 1
            continue
        if ch == " ":
            if buf:
                tokens.append(("simple", "".join(buf).strip()))
                buf = []
            # descendant unless next is combinator
            j = i
            while j < n and selector[j] == " ":
                j += 1
            if j < n and selector[j] in combinators:
                i = j
                continue
            tokens.append(("comb", " "))
            i = j
            continue
        buf.append(ch)
        i += 1
    if buf:
        tokens.append(("simple", "".join(buf).strip()))
    return tokens


def matches_simple(el: El, parsed: dict) -> bool:
    if not parsed["ok"]:
        return False
    if parsed["pseudos"] and any(p in {"hover", "focus", "focus-visible", "active", "visited", "focus-within", "attr"} or p not in {"root"} for p in parsed["pseudos"] if p not in {"root"}):
        # default fixture has no hover/focus/attr
        if any(p != "root" for p in parsed["pseudos"]):
            return False
    if parsed["tag"] == "html" or (parsed.get("pseudos") and "root" in parsed["pseudos"]):
        if el.tag != "html":
            # :root only matches html
            if parsed["tag"] and parsed["tag"] not in {"*", "html"} and "root" in parsed["pseudos"]:
                return False
            if "root" in parsed["pseudos"] and el.tag != "html":
                return False
    if parsed["tag"] and parsed["tag"] not in {"*", None}:
        if "root" in parsed["pseudos"] and parsed["tag"] is None:
            pass
        elif el.tag != parsed["tag"]:
            return False
    if parsed["id"] and el.el_id != parsed["id"]:
        return False
    if parsed["classes"] and not parsed["classes"].issubset(el.classes):
        return False
    if "root" in parsed["pseudos"] and el.tag != "html":
        return False
    return True


def matches_selector(el: El, selector: str) -> bool:
    tokens = tokenize_selector(selector)
    if not tokens:
        return False
    # reject unsupported (comma already split)
    simples = []
    combs = []
    for typ, val in tokens:
        if typ == "simple":
            parsed = parse_simple(val)
            if not parsed["ok"]:
                return False
            simples.append(parsed)
        else:
            if val != " ":
                # child/sibling: only support descendant for this fixture
                # but '>' can be treated if we walk parent exactly once
                combs.append(val)
            else:
                combs.append(" ")
    if len(simples) != len(combs) + 1:
        return False

    def walk(node: El | None, si: int) -> bool:
        if node is None:
            return False
        if si == 0:
            # match first simple against some ancestor-or-self depending on last comb? handled below
            return matches_simple(node, simples[0]) or walk(node.parent, 0)
        # match simples[si] at node, then previous via combinator combs[si-1]
        if not matches_simple(node, simples[si]):
            return False
        comb = combs[si - 1]
        if comb == " ":
            anc = node.parent
            while anc:
                if walk(anc, si - 1) or (si - 1 == 0 and matches_simple(anc, simples[0]) and _prefix_ok(anc, 0)):
                    # simpler: search ancestors for remainder
                    pass
                anc = anc.parent
            # remainder must match some ancestor
            anc = node.parent
            while anc:
                if _match_from(anc, si - 1):
                    return True
                anc = anc.parent
            return False
        if comb == ">":
            return bool(node.parent) and _match_from(node.parent, si - 1)
        return False

    def _prefix_ok(node, si):
        return _match_from(node, si)

    def _match_from(node: El | None, si: int) -> bool:
        if node is None:
            return False
        if not matches_simple(node, simples[si]):
            return False
        if si == 0:
            return True
        comb = combs[si - 1]
        if comb == ">":
            return _match_from(node.parent, si - 1)
        if comb == " ":
            anc = node.parent
            while anc:
                if _match_from(anc, si - 1):
                    return True
                anc = anc.parent
            return False
        return False

    return _match_from(el, len(simples) - 1)


def resolved_opacity(css: str, el: El) -> tuple[float | None, list[dict]]:
    """Return winning opacity (float or None if unset) and competing declarations."""
    hits: list[dict] = []
    order = 0
    for prelude, body, pos in iter_top_level_rules(css):
        decls = parse_decls(body)
        opacities = [d for d in decls if d[0] == "opacity"]
        if not opacities:
            order += 1
            continue
        for sel in [s.strip() for s in prelude.split(",") if s.strip()]:
            if not matches_selector(el, sel):
                continue
            parsed_parts = []
            tokens = tokenize_selector(sel) or []
            for typ, val in tokens:
                if typ == "simple":
                    parsed_parts.append(parse_simple(val))
            spec = specificity(parsed_parts)
            for _prop, value, important in opacities:
                hits.append(
                    {
                        "selector": sel,
                        "value": value,
                        "important": important,
                        "specificity": spec,
                        "order": order,
                    }
                )
        order += 1
    if not hits:
        return None, hits
    hits.sort(key=lambda h: (h["important"], h["specificity"], h["order"]))
    win = hits[-1]
    try:
        val = float(win["value"])
    except ValueError:
        return None, hits
    return val, hits


def discover_inview_class(app_js: str) -> str:
    """The in-view class is whatever entrances() adds, not a required CSS spelling."""
    # Prefer the add() inside IntersectionObserver callback, then any add("is-in")
    names = re.findall(r'classList\.add\("([^"]+)"\)', app_js)
    for name in names:
        if name not in {"is-open", "is-lit", "is-dragging", "is-dimming", "js"}:
            # first remaining add in file order after those UI states is the entrance hook
            if name == "is-in" or "in" in name:
                return name
    for name in names:
        if name not in {"is-open", "is-lit", "is-dragging", "is-dimming", "js"}:
            return name
    raise SystemExit("FAIL: could not discover in-view class from app.js")


def parse_element_tag(html: str, el_id: str) -> El:
    m = re.search(rf'<(section|div|article|main)\b[^>]*\bid="{re.escape(el_id)}"[^>]*>', html)
    if not m:
        m = re.search(rf'<(section|div|article|main)\b[^>]*\bid=\'{re.escape(el_id)}\'[^>]*>', html)
    if not m:
        raise SystemExit(f"FAIL: #{el_id} not found")
    tag_html = m.group(0)
    tag = m.group(1).lower()
    cm = re.search(r'\bclass="([^"]*)"', tag_html) or re.search(r"\bclass='([^']*)'", tag_html)
    classes = set(cm.group(1).split()) if cm else set()
    return El(tag=tag, el_id=el_id, classes=classes)


def build_fixture(page_html: str, el_id: str, inview: str) -> El:
    region = parse_element_tag(page_html, el_id)
    region.classes = set(region.classes)
    region.classes.add(inview)
    html = El(tag="html", el_id="", classes={"js"}, parent=None)
    body = El(tag="body", el_id="", classes=set(), parent=html)
    region.parent = body
    return region


def parse_opacity(value: str) -> float:
    return float(value)


def run_engine_selfcheck() -> list[str]:
    """Prove the static engine on synthetic CSS; these selectors are fixtures, not site requirements."""
    failures = []
    later_hidden = """
    .reveal.is-in { opacity: 1; }
    .js .reveal { opacity: 0; }
    """
    html = El("html", "", {"js"})
    body = El("body", "", set(), html)
    el = El("section", "sheet", {"sheet", "reveal", "is-in"}, body)
    val, hits = resolved_opacity(later_hidden, el)
    if val != 0.0:
        failures.append(f"engine: later same-specificity hidden rule should win, got {val} hits={hits}")
    earlier_hidden = """
    .js .reveal { opacity: 0; }
    .reveal.is-in { opacity: 1; }
    """
    val, hits = resolved_opacity(earlier_hidden, el)
    if val != 1.0:
        failures.append(f"engine: later same-specificity visible rule should win, got {val} hits={hits}")
    more_specific = """
    .reveal.is-in { opacity: 1; }
    .js .reveal { opacity: 0; }
    .js .reveal.is-in { opacity: 1; }
    """
    val, hits = resolved_opacity(more_specific, el)
    if val != 1.0:
        failures.append(f"engine: higher specificity visible rule should win, got {val} hits={hits}")
    return failures


def main() -> int:
    print("STATIC cascade check — not a browser computed-style test; not a substitute for real rendering.")
    failures = run_engine_selfcheck()
    if failures:
        for item in failures:
            print("FAIL", item)
        return 1
    print("PASS engine self-check (synthetic cascade)")

    app_js = APP_JS.read_text(encoding="utf-8")
    inview = discover_inview_class(app_js)
    print(f"discovered in-view class from app.js: {inview!r}")

    all_ok = True
    for locale, path in PAGES.items():
        html = path.read_text(encoding="utf-8")
        css = extract_style(html)
        for el_id in REGION_IDS:
            el = build_fixture(html, el_id, inview)
            val, hits = resolved_opacity(css, el)
            # initial opacity is 1 if unset — that would be visible
            effective = 1.0 if val is None else val
            status = "PASS" if effective > 0 else "FAIL"
            if effective <= 0:
                all_ok = False
            print(
                f"{status} {locale} #{el_id} static-opacity={effective} "
                f"classes={sorted(el.classes)} competing={[(h['selector'], h['value'], h['specificity'], h['order']) for h in hits]}"
            )
    if not all_ok:
        print("FAIL list/category regions resolve to opacity 0 in the default static cascade.")
        return 1
    print("PASS list/category in-view regions are not opacity 0 in the static cascade.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
