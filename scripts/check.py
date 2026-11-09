#!/usr/bin/env python3
"""Quality checks over docs/: links, images, robots meta, budgets. Exit 1 on any problem."""
from __future__ import annotations

import gzip
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

HTML_GZIP_MAX = 30 * 1024
CSS_RAW_MAX = 25 * 1024
JS_RAW_MAX = 10 * 1024
ATF_IMG_MAX = 150 * 1024
PHONE_DEVICE_PX = 780  # 390 CSS px at DPR 2


class Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.imgs: list[tuple[str, bool, bool]] = []  # (phone candidate src, eager, inside <picture> with <source>)
        self.has_robots = False
        self.viewport = ""
        self.sources: list[str] = []
        self._in_picture_with_source = False

    def handle_endtag(self, tag):
        if tag == "picture":
            self._in_picture_with_source = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag == "img" and a.get("src"):
            # phone candidate: what a 390px DPR-2 phone (780 device px, sizes=100vw) selects:
            # the smallest srcset width >= 780, else the largest available
            src = a["src"]
            if a.get("srcset"):
                cands = []
                for part in a["srcset"].split(","):
                    bits = part.strip().split()
                    w = int(bits[1][:-1]) if len(bits) > 1 and bits[1].endswith("w") else 0
                    cands.append((w, bits[0]))
                big_enough = [c for c in cands if c[0] >= PHONE_DEVICE_PX]
                src = min(big_enough)[1] if big_enough else max(cands)[1]
            self.imgs.append((src, a.get("loading") != "lazy", self._in_picture_with_source))
        elif tag == "picture":
            self._in_picture_with_source = False
        elif tag == "source" and a.get("srcset"):
            self._in_picture_with_source = True
            self.sources.append(a["srcset"].split()[0])
        elif tag == "meta" and a.get("name") == "robots" and "noindex" in (a.get("content") or ""):
            self.has_robots = True
        elif tag == "meta" and a.get("name") == "viewport":
            self.viewport = a.get("content") or ""
        elif tag in ("link", "script") and (a.get("href") or a.get("src")):
            self.links.append(a.get("href") or a.get("src"))


def base_path() -> str:
    import json
    site = json.loads((ROOT / "data" / "site.json").read_text(encoding="utf-8"))
    return site.get("base_path", "/")


BASE = base_path()


def resolve(page: Path, ref: str) -> Path | None:
    if re.match(r"^(https?:|mailto:|tel:|sms:|data:|#)", ref):
        return None
    path = unquote(urlsplit(ref).path)
    if not path:
        return None
    if path.startswith(BASE):  # absolute links on the 404 page are served under the Pages base path
        path = "/" + path[len(BASE):]
    target = (DOCS / path.lstrip("/")) if path.startswith("/") else (page.parent / path)
    target = target.resolve()
    if target.is_dir():
        target = target / "index.html"
    return target


def main() -> int:
    problems: list[str] = []
    pages = sorted(DOCS.rglob("*.html"))
    for page in pages:
        rel = page.relative_to(DOCS)
        c = Collector()
        c.feed(page.read_text(encoding="utf-8"))
        if not c.has_robots:
            problems.append(f"{rel}: missing robots noindex")
        if c.viewport != "width=device-width, initial-scale=1":
            problems.append(f"{rel}: viewport meta is {c.viewport!r}")
        for ref in c.links:
            t = resolve(page, ref)
            if t is not None and not t.exists():
                problems.append(f"{rel}: broken link {ref}")
        atf = 0
        # phone above-the-fold: eager images, using the <source> variant when a <picture> has one
        eager_imgs = [s for s, eager, in_pic in c.imgs if eager and not in_pic] + c.sources
        for src, _, _ in c.imgs:
            t = resolve(page, src)
            if t is not None and not t.exists():
                problems.append(f"{rel}: missing image {src}")
        for src in eager_imgs:
            t = resolve(page, src)
            if t is not None and t.exists():
                atf += t.stat().st_size
        if atf > ATF_IMG_MAX:
            problems.append(f"{rel}: above-the-fold images {atf // 1024} KB > {ATF_IMG_MAX // 1024} KB")
        gz = len(gzip.compress(page.read_bytes()))
        if gz > HTML_GZIP_MAX:
            problems.append(f"{rel}: html gzip {gz // 1024} KB > {HTML_GZIP_MAX // 1024} KB")
    for css in (DOCS / "css").glob("*.css"):
        if css.stat().st_size > CSS_RAW_MAX:
            problems.append(f"css/{css.name}: {css.stat().st_size // 1024} KB > {CSS_RAW_MAX // 1024} KB")
    for js in (DOCS / "js").glob("*.js"):
        if js.stat().st_size > JS_RAW_MAX:
            problems.append(f"js/{js.name}: {js.stat().st_size // 1024} KB > {JS_RAW_MAX // 1024} KB")
    robots = DOCS / "robots.txt"
    if not robots.exists() or "Disallow: /" not in robots.read_text():
        problems.append("robots.txt missing or not disallowing")
    for p in problems:
        print(p)
    print(f"{len(problems)} problems across {len(pages)} pages")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
