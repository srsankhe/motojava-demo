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
# about page: derived from gallery files (3:2) or downloaded from the live site
ABOUT_GALLERY = {
    "storefront": BIKES / "2016-honda-cb500x-rally-raid" / "09.webp",
    "sidewalk": BIKES / "2014-harley-davidson-heritage-softail" / "15.webp",
}
ABOUT_LIVE = {  # kept at native size; the live site's own photos are small
    "workbench": "https://motojava.com/wp-content/uploads/2020/11/fulltune.png",
    "mike-goldwing": "https://motojava.com/wp-content/uploads/2026/02/IMG_3475-rotated.jpg",
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


BRAND = {
    "logo": "https://motojava.com/wp-content/uploads/2020/10/Logo-100.png",       # standalone wordmark, transparent
    "lockup": "https://motojava.com/wp-content/uploads/2024/11/motojava-logo-with-kymco-2.png",
}


def brand() -> None:
    """Their real wordmark as-is (PNG, keeps transparency) and the Kymco mark cropped from the lock-up."""
    (OUT / "brand").mkdir(parents=True, exist_ok=True)
    with Image.open(download(BRAND["logo"])) as im:
        im.convert("RGBA").save(OUT / "brand" / "motojava-logo.png", optimize=True)
    with Image.open(download(BRAND["lockup"])) as im:
        im = im.convert("RGB")
        w, h = im.size
        band = im.crop((0, int(h * 0.50), w, int(h * 0.82)))  # the KYMCO row, between the wordmark and the tagline
        # trim white margins
        bg = Image.new("RGB", band.size, (255, 255, 255))
        bbox = Image.eval(ImageOps.grayscale(band), lambda v: 255 - v if v < 240 else 0).getbbox()
        if bbox:
            band = band.crop(bbox)
        band.save(OUT / "brand" / "kymco.png", optimize=True)


KYMCO = {  # new-scooter cards: shop-owned photos only (kymcousa.com blocks automated fetches)
    "cv3": RAW_IMG / "IMG_1231-compressed.jpg",                 # the 2024 CV3 itself, in front of the shop
    "like": BIKES / "2019-kymco-like-150i" / "02.webp",          # same body as the 2026 Like 150i; captioned as 2019
}


def kymco() -> None:
    (OUT / "kymco").mkdir(parents=True, exist_ok=True)
    for name, src in KYMCO.items():
        if not src.exists() and name == "cv3":
            src = download("https://motojava.com/wp-content/uploads/2025/04/IMG_1231-compressed.jpg")
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            w = min(1200, im.width)
            im = ImageOps.fit(im, (w, round(w * 3 / 4)), Image.Resampling.LANCZOS)  # 4:3 like the bike cards
            save_widths(im, OUT / "kymco" / name, tuple(sorted({480, w})), 78)


def main() -> int:
    brand()
    kymco()
    (OUT / "service").mkdir(parents=True, exist_ok=True)
    (OUT / "team").mkdir(parents=True, exist_ok=True)
    for name, src in SERVICE.items():
        if not src.exists():
            print(f"missing source {src}")
            return 1
        with Image.open(src) as im:
            im = ImageOps.fit(im.convert("RGB"), (1200, 800), Image.Resampling.LANCZOS)  # 3:2 crop
            save_widths(im, OUT / "service" / name, (1200, 600), 78)
    (OUT / "about").mkdir(parents=True, exist_ok=True)
    for name, src in ABOUT_GALLERY.items():
        with Image.open(src) as im:
            im = ImageOps.fit(im.convert("RGB"), (1200, 800), Image.Resampling.LANCZOS)
            save_widths(im, OUT / "about" / name, (1200, 600), 78)
    for name, url in ABOUT_LIVE.items():
        with Image.open(download(url)) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.save(OUT / "about" / f"{name}.webp", "WEBP", quality=82, method=6)
    for name, (url, centering) in TEAM.items():
        with Image.open(download(url)) as im:
            im = ImageOps.fit(im.convert("RGB"), (320, 320), Image.Resampling.LANCZOS, centering=centering)
            im.save(OUT / "team" / f"{name}.webp", "WEBP", quality=80, method=6)
    sizes = {p.name: p.stat().st_size // 1024 for d in ("service", "team", "about", "brand") for p in (OUT / d).glob("*.*")}
    print(sizes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
