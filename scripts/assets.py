#!/usr/bin/env python3
"""Derived image assets: service-page photo strip from existing gallery files, team portraits."""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
BIKES = ROOT / "docs" / "img" / "bikes"
OUT = ROOT / "docs" / "img"
RAW_IMG = ROOT / "data" / "raw" / "img"
UA = "motojava-demo-build"

# service page: (output name, source gallery file)
SERVICE = {
    "engine": BIKES / "2012-honda-shadow-750-phantom" / "09.webp",
    "brake": BIKES / "2014-honda-cbr500r" / "11.webp",
    "dash": BIKES / "2024-kawasaki-ninja-500-krt" / "14.webp",
    "wheel": BIKES / "2007-suzuki-sv650" / "12.webp",
}
TEAM = {  # name: (url, crop centering as fractions of width/height)
    "mike": ("https://motojava.com/wp-content/uploads/2020/06/Mike.png", (0.62, 0.22)),
    "kim": ("https://motojava.com/wp-content/uploads/2020/06/Kim.png", (0.5, 0.4)),
}


def download(url: str) -> Path:
    RAW_IMG.mkdir(parents=True, exist_ok=True)
    dest = RAW_IMG / url.rsplit("/", 1)[-1]
    if not dest.exists():
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=120) as r, dest.open("wb") as f:
            f.write(r.read())
    return dest


def save_widths(im: Image.Image, stem: Path, widths: tuple[int, ...], quality: int) -> None:
    for w in widths:
        out = im if im.width <= w else im.resize((w, round(im.height * w / im.width)), Image.Resampling.LANCZOS)
        suffix = "" if w == max(widths) else f"-{w}"
        out.save(stem.with_name(f"{stem.name}{suffix}.webp"), "WEBP", quality=quality, method=6)


def main() -> int:
    (OUT / "service").mkdir(parents=True, exist_ok=True)
    (OUT / "team").mkdir(parents=True, exist_ok=True)
    for name, src in SERVICE.items():
        if not src.exists():
            print(f"missing source {src}")
            return 1
        with Image.open(src) as im:
            im = ImageOps.fit(im.convert("RGB"), (1200, 800), Image.Resampling.LANCZOS)  # 3:2 crop
            save_widths(im, OUT / "service" / name, (1200, 600), 78)
    for name, (url, centering) in TEAM.items():
        with Image.open(download(url)) as im:
            im = ImageOps.fit(im.convert("RGB"), (320, 320), Image.Resampling.LANCZOS, centering=centering)
            im.save(OUT / "team" / f"{name}.webp", "WEBP", quality=80, method=6)
    sizes = {p.name: p.stat().st_size // 1024 for p in list((OUT / "service").glob("*.webp")) + list((OUT / "team").glob("*.webp"))}
    print(sizes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
