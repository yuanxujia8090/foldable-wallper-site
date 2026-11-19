#!/usr/bin/env python3
"""STATIC order/specificity/opacity check for #find/#sheet in-view state.
Not a browser test or a substitute for rendering. Supports only type, #id,
.class, and descendants. Unknown forms that may apply, or no matching opacity
declaration, fail closed; unset opacity is not treated as 1."""
import re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PAGES = (("en", "public/index.html"), ("zh", "public/zh/index.html"))
SIMPLE = re.compile(r"^(?:([a-z][\w-]*)|(?=[.#]))(\#[A-Za-z_][\w-]*)?((?:\.[A-Za-z_][\w-]*)*)$")
class Fail(Exception): pass
def load(rev, path):
    return (subprocess.check_output(["git", "-C", str(ROOT), "show", f"{rev}:{path}"], text=True)
            if rev else (ROOT / path).read_text(encoding="utf-8"))
def css_of(html):
    m = re.search(r"<style>(.*?)</style>", html, re.S)
    if not m: raise Fail("no <style> block")
    return re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S)
def rules(css):
    i, n, order = 0, len(css), 0
    while i < n:
        while i < n and css[i].isspace(): i += 1
        if i >= n: return
        at, j = css.startswith("@", i), i
        while j < n and css[j] not in "{;": j += 1
        prelude = css[i:j].strip()
        if j < n and css[j] == ";":
            yield prelude, "", order, at; order += 1; i = j + 1; continue
        depth, k = 0, j
        while k < n:
            depth += (css[k] == "{") - (css[k] == "}"); k += 1
            if depth == 0: break
        yield prelude, css[j + 1:k - 1], order, at; order += 1; i = k
def simple(tok):
    m = SIMPLE.fullmatch(tok or "")
    if not m: return None
    return m.group(1), (m.group(2) or "")[1:] or None, set(re.findall(r"\.([A-Za-z_][\w-]*)", m.group(3) or ""))
def compiled(sel):
    parts = [simple(t) for t in sel.split()] if not re.search(r"[>+~]", sel) else [None]
    return parts if parts and all(parts) else None
def matches(chain, parts):
    ok = lambda el, p: ((not p[0] or el["tag"] == p[0]) and (not p[1] or el["id"] == p[1]) and p[2] <= el["classes"])
    node = len(chain) - 1
    for step, part in enumerate(reversed(parts)):
        while node >= 0 and not ok(chain[node], part):
            if step == 0: return False
            node -= 1
        if node < 0: return False
        node -= 1
    return True
def may_apply(el, sel):
    bare = re.sub(r"::?[A-Za-z_-][\w-]*(\([^)]*\))?", "", re.split(r"[>+~\s]", sel.strip())[-1])
    parsed = simple(bare) if bare else None
    if parsed is None: return True
    tag, ident, classes = parsed
    if (tag and el["tag"] != tag) or (ident and el["id"] != ident): return False
    return not (classes and not classes <= el["classes"])
def region(html, el_id):
    m = re.search(rf"<(section|div|article|main)\b[^>]*\bid=\"{re.escape(el_id)}\"[^>]*>", html)
    if not m: raise Fail(f"#{el_id} not found")
    cm = re.search(r'\bclass="([^"]*)"', m.group(0))
    return {"tag": m.group(1).lower(), "id": el_id, "classes": set(cm.group(1).split() if cm else [])}
def inview_of(js):
    for name in re.findall(r'classList\.add\("([^"]+)"\)', js):
        if name not in {"is-open", "is-lit", "is-dragging", "is-dimming", "js"}: return name
    raise Fail("could not discover in-view class from app.js")
def winning(css, chain):
    el, hits, problems = chain[-1], [], []
    for prelude, body, order, at in rules(css):
        if at:
            if body and "opacity" in body.lower() and "prefers-reduced-motion" not in prelude.lower(): problems.append(f"unevaluated @-rule opacity: {prelude!r}")
            continue
        ops = [(re.sub(r"\s*!important\s*$", "", m.group(1), flags=re.I).strip(),
                bool(re.search(r"!important\s*$", m.group(1), re.I)))
               for m in re.finditer(r"(?i)(?:^|;)\s*opacity\s*:\s*([^;}]+)", body)]
        if not ops: continue
        for sel in (s.strip() for s in prelude.split(",") if s.strip()):
            parts = compiled(sel)
            if parts is not None and matches(chain, parts):
                sp = (sum(bool(p[1]) for p in parts), sum(len(p[2]) for p in parts), sum(bool(p[0]) for p in parts))
                hits.extend((imp, sp, order, val, sel) for val, imp in ops)
            elif parts is None and may_apply(el, sel):
                problems.append(f"unsupported selector that may apply: {sel!r}")
    if problems: raise Fail("; ".join(problems))
    if not hits: raise Fail("no matching opacity declaration (fail closed, not default 1)")
    hits.sort(); *_, value, sel = hits[-1]
    try: return float(value), hits
    except ValueError as exc: raise Fail(f"non-numeric opacity {value!r} from {sel}") from exc
def selfcheck():
    chain = [{"tag": "html", "id": "", "classes": {"js"}}, {"tag": "body", "id": "", "classes": set()},
             {"tag": "section", "id": "sheet", "classes": {"sheet", "reveal", "is-in"}}]
    for css, val in ((".reveal.is-in{opacity:1}.js .reveal{opacity:0}", 0),
                     (".js .reveal{opacity:0}.reveal.is-in{opacity:1}", 1)):
        if winning(css, chain)[0] != val: raise Fail("selfcheck: same-specificity order")
    for css, label in ((".js .reveal:where(){opacity:0}", "unsupported may-apply"),
                       (".unrelated{color:red}", "no opacity")):
        try: winning(css, chain)
        except Fail: continue
        raise Fail(f"selfcheck: {label} should fail closed")
def main():
    rev = sys.argv[2] if sys.argv[1:2] == ["--from-git"] else None
    print("STATIC cascade check — not a browser test; not a substitute for rendering.")
    print("fixtures:", f"git {rev}" if rev else "worktree")
    selfcheck(); print("PASS engine self-check")
    inview = inview_of(load(rev, "public/app.js"))
    print(f"in-view class from app.js: {inview!r}")
    failed, base = 0, [{"tag": "html", "id": "", "classes": {"js"}}, {"tag": "body", "id": "", "classes": set()}]
    for loc, path in PAGES:
        html = load(rev, path); css = css_of(html)
        for el_id in ("find", "sheet"):
            el = region(html, el_id); el["classes"] = set(el["classes"]) | {inview}
            try:
                val, hits = winning(css, base + [el]); win, ok = hits[-1], val > 0
                print(f"{'PASS' if ok else 'FAIL'} {loc} #{el_id} static-opacity={val} winner={win[4]!r} spec={win[1]} order={win[2]}")
                failed += not ok
            except Fail as exc:
                print(f"FAIL {loc} #{el_id} {exc}"); failed += 1
    print("FAIL list/category in-view opacity check." if failed else "PASS list/category in-view regions are not opacity 0 in the static cascade.")
    return 1 if failed else 0
if __name__ == "__main__": sys.exit(main())
