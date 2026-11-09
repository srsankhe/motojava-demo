#!/usr/bin/env python3
"""Fetch bike photos once from motojava.com and write resized WebP files into docs/img/.

For each for-sale/pending bike (in bikes.json order), the i-th raw inventory gallery
provides the URLs. Output per photo: NN.webp (max 1200px wide, q80) and NN-480.webp
(480px wide, q75). Also writes the hero image at 1600px and 800px.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RAW_IMG = RAW / "img"
OUT = ROOT / "docs" / "img"
UA = "motojava-demo-build"
HERO_URL = "https://motojava.com/wp-content/uploads/2025/04/IMG_1231-compressed.jpg"


def download(url: str) -> Path:
    RAW_IMG.mkdir(parents=True, exist_ok=True)
    dest = RAW_IMG / url.rsplit("/", 1)[-1]
    if not dest.exists():
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=120) as r, dest.open("wb") as f:
            f.write(r.read())
    return dest


def resize_to_width(im: Image.Image, width: int) -> Image.Image:
    if im.width <= width:
        return im.copy()
    h = round(im.height * width / im.width)
    return im.resize((width, h), Image.Resampling.LANCZOS)


def fit_box(im: Image.Image, size: int) -> Image.Image:
    """Fit the longer side to `size`, so portrait thumbs do not carry extra pixels."""
    if max(im.size) <= size:
        return im.copy()
    scale = size / max(im.size)
    return im.resize((round(im.width * scale), round(im.height * scale)), Image.Resampling.LANCZOS)


VARIANTS = ((1200, "", 78), (800, "-800", 75), (480, "-480", 75))  # (longest side, suffix, quality)


def process(url: str, out_dir: Path, index: int) -> list[Path]:
    """Write NN.webp (≤1200 on the longer side), NN-800.webp and NN-480.webp."""
    src = download(url)
    out_dir.mkdir(parents=True, exist_ok=True)
    outs = [out_dir / f"{index:02d}{suffix}.webp" for _, suffix, _ in VARIANTS]
    if all(p.exists() for p in outs):
        return outs
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        for (size, _, q), out in zip(VARIANTS, outs):
            fit_box(im, size).save(out, "WEBP", quality=q, method=6)
    return outs


def hero(url: str) -> None:
    src = download(url)
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        resize_to_width(im, 1600).save(OUT / "hero.webp", "WEBP", quality=80, method=6)
        resize_to_width(im, 800).save(OUT / "hero-800.webp", "WEBP", quality=75, method=6)


def main() -> int:
    raw = [x for x in json.loads((RAW / "bikes.raw.json").read_text()) if x["section"] == "inventory"]
    bikes = [b for b in json.loads((ROOT / "data" / "bikes.json").read_text()) if b["status"] in ("for-sale", "pending")]
    if len(raw) != len(bikes):
        print(f"count mismatch: {len(raw)} raw galleries vs {len(bikes)} for-sale/pending bikes")
        return 1
    n_img = 0
    for r, b in zip(raw, bikes):
        if r["heading"][:4] != str(b["year"]):
            print(f"order mismatch at {b['slug']}: raw heading {r['heading'][:60]!r}")
            return 1
        if len(r["images"]) != len(b["photos"]):
            print(f"photo count mismatch at {b['slug']}: {len(r['images'])} raw vs {len(b['photos'])} in bikes.json")
            return 1
        out_dir = OUT / "bikes" / b["slug"]
        for i, url in enumerate(r["images"], start=1):
            process(url, out_dir, i)
            n_img += 1
        print(f"  {b['slug']}: {len(r['images'])} photos", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    hero(HERO_URL)
    total = sum(p.stat().st_size for p in OUT.rglob("*.webp")) / 1048576
    print(f"{len(bikes)} bikes, {n_img} images, {total:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
