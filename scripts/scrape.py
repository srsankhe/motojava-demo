#!/usr/bin/env python3
"""Scrape the live motojava.com home page into data/raw/bikes.raw.json.

Output: list of {"heading": str, "images": [url, ...], "section": "inventory" | "coming-soon"}
in page order. Inventory items are Divi gallery blocks paired with the text block that
follows them. Coming-soon items are the <h1> headings in the grey "2026 is ENDING" section
that start with a four-digit year.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
URL = "https://motojava.com/"
UA = "motojava-demo-build"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def largest_from_srcset(srcset: str) -> str | None:
    best, best_w = None, -1
    for part in srcset.split(","):
        bits = part.strip().split()
        if not bits:
            continue
        url = bits[0]
        w = int(bits[1][:-1]) if len(bits) > 1 and bits[1].endswith("w") else 0
        if w > best_w:
            best, best_w = url, w
    return best


class DiviParser(HTMLParser):
    """Walk the Divi DOM tracking sections, galleries and text blocks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, set[str]]] = []
        self.section_index = -1
        self.items: list[dict] = []
        self._gallery: list[str] | None = None
        self._pending_gallery: list[str] | None = None
        self._text_depth: int | None = None
        self._text_buf: list[str] = []
        self._h1_depth: int | None = None
        self._h1_buf: list[str] = []
        self._in_gallery_depth: int | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classes = set((a.get("class") or "").split())
        self.stack.append((tag, classes))
        depth = len(self.stack)
        if "et_pb_section" in classes:
            self.section_index += 1
        if "et_pb_gallery" in classes and "et_pb_gallery_item" not in classes and self._in_gallery_depth is None:
            self._in_gallery_depth = depth
            self._gallery = []
        if self._in_gallery_depth is not None and tag == "img" and "et_pb_gallery_image" in set((a.get("class") or "").split()) or (
            self._in_gallery_depth is not None and tag == "img"
        ):
            url = largest_from_srcset(a.get("srcset", "")) or a.get("src")
            if url and self._gallery is not None:
                self._gallery.append(url)
        if "et_pb_text" in classes and "et_pb_text_inner" not in classes and self._text_depth is None:
            self._text_depth = depth
            self._text_buf = []
        if tag == "h1" and self._h1_depth is None:
            self._h1_depth = depth
            self._h1_buf = []

    def handle_endtag(self, tag):
        if not self.stack:
            return
        depth = len(self.stack)
        if self._in_gallery_depth == depth:
            self._pending_gallery = self._gallery or []
            self._gallery = None
            self._in_gallery_depth = None
        if self._text_depth == depth:
            text = re.sub(r"\s+", " ", " ".join(self._text_buf)).strip()
            if self._pending_gallery is not None and text:
                self.items.append({"heading": text, "images": self._pending_gallery, "section": "inventory"})
                self._pending_gallery = None
            self._text_depth = None
        if self._h1_depth == depth:
            text = re.sub(r"\s+", " ", " ".join(self._h1_buf)).strip()
            # a bike heading: year, then a make name; excludes "2026 is ENDING SALE"
            if self.section_index == 4 and re.match(r"^(19|20)\d{2} (?!is\b)[A-Za-z]", text):
                self.items.append({"heading": text, "images": [], "section": "coming-soon"})
            self._h1_depth = None
        self.stack.pop()

    def handle_data(self, data):
        if self._text_depth is not None:
            self._text_buf.append(data)
        if self._h1_depth is not None:
            self._h1_buf.append(data)


def parse(html: str) -> list[dict]:
    p = DiviParser()
    p.feed(html)
    return p.items


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    html_path = RAW / "home.html"
    if html_path.exists():
        html = html_path.read_text(encoding="utf-8")
    else:
        html = fetch(URL)
        html_path.write_text(html, encoding="utf-8")
    items = parse(html)
    inv = [i for i in items if i["section"] == "inventory"]
    soon = [i for i in items if i["section"] == "coming-soon"]
    n_img = sum(len(i["images"]) for i in inv)
    (RAW / "bikes.raw.json").write_text(json.dumps(items, indent=2), encoding="utf-8")
    print(f"{len(inv)} inventory, {len(soon)} coming-soon, {n_img} images")
    if len(inv) != 32 or len(soon) != 14 or n_img != 370:
        print("COUNTS DIFFER FROM EXPECTED (32 / 14 / 370). Headings found:")
        for i in items:
            print(f"  [{i['section']}] ({len(i['images'])} img) {i['heading'][:90]}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
