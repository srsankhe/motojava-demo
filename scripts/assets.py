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
# Sources are the RAW originals (not the resized gallery files) from the three galleries shot at
# 1800-2560px: 2021 Rebel 500, 2014 CBR500R, 2022 KLR650. Everything else in the library is 480-640px.
RAW_GALLERY = {  # slug -> list of raw filenames in gallery order, filled by load_raw()
}


def load_raw() -> None:
    import json
    raw = [x for x in json.loads((ROOT / "data" / "raw" / "bikes.raw.json").read_text()) if x["section"] == "inventory"]
    bikes = [b for b in json.loads((ROOT / "data" / "bikes.json").read_text()) if b["status"] in ("for-sale", "pending")]
    for r, b in zip(raw, bikes):
        RAW_GALLERY[b["slug"]] = [RAW_IMG / u.rsplit("/", 1)[-1] for u in r["images"]]


def raw_photo(slug: str, n: int) -> Path:
    if not RAW_GALLERY:
        load_raw()
    return RAW_GALLERY[slug][n - 1]


SERVICE = {  # (slug, photo number) in the hi-res galleries
    "engine": ("2021-honda-rebel-500", 3),
    "brake": ("2014-honda-cbr500r", 11),
    "dash": ("2022-kawasaki-klr650", 11),
    "wheel": ("2014-honda-cbr500r", 12),
}
# about page: derived from gallery files (3:2) or downloaded from the live site
ABOUT_GALLERY = {  # (slug, photo number) in the hi-res galleries
    "storefront": ("2022-kawasaki-klr650", 2),
    "sidewalk": ("2021-honda-rebel-500", 2),
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


KYMCO = {  # 2026 product cutouts captured from kymcousa.com in the user's browser (credited on the page)
    "cv3": RAW_IMG / "kymco-cv3-2026.png",
    "like": RAW_IMG / "kymco-like-150i-2026.png",
    "people": RAW_IMG / "kymco-people-s-150i-2026.png",
}


def trim_white(im: Image.Image, threshold: int = 245) -> Image.Image:
    """Crop away the white margins around a product cutout."""
    gray = ImageOps.grayscale(im)
    mask = gray.point(lambda v: 255 if v < threshold else 0)
    bbox = mask.getbbox()
    return im.crop(bbox) if bbox else im


def kymco() -> None:
    (OUT / "kymco").mkdir(parents=True, exist_ok=True)
    for name, src in KYMCO.items():
        with Image.open(src) as im:
            im = trim_white(im.convert("RGB"))
            # pad (never crop) onto white to 4:3, with breathing room, so the whole scooter shows in the card
            w = min(1200, int(im.width * 1.12))
            canvas = Image.new("RGB", (w, round(w * 3 / 4)), (255, 255, 255))
            scale = min((w * 0.9) / im.width, (canvas.height * 0.86) / im.height)
            fitted = im.resize((round(im.width * scale), round(im.height * scale)), Image.Resampling.LANCZOS)
            canvas.paste(fitted, ((w - fitted.width) // 2, (canvas.height - fitted.height) // 2))
            save_widths(canvas, OUT / "kymco" / name, (w, 480) if w > 480 else (480,), 80)


def main() -> int:
    brand()
    kymco()
    (OUT / "service").mkdir(parents=True, exist_ok=True)
    (OUT / "team").mkdir(parents=True, exist_ok=True)
    for name, (slug, n) in SERVICE.items():
        src = raw_photo(slug, n)
        if not src.exists():
            print(f"missing source {src}")
            return 1
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            assert min(im.size) >= 1200, f"{name}: source {src.name} is only {im.size}"
            im = ImageOps.fit(im, (1200, 800), Image.Resampling.LANCZOS)  # 3:2 crop
            save_widths(im, OUT / "service" / name, (1200, 600), 78)
    (OUT / "about").mkdir(parents=True, exist_ok=True)
    for name, (slug, n) in ABOUT_GALLERY.items():
        with Image.open(raw_photo(slug, n)) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            assert min(im.size) >= 1200, f"{name}: source is only {im.size}"
            # the band is wide; a 2:1 crop from the square originals keeps signs and bike
            size = (1600, 800) if name == "storefront" else (1200, 800)
            im = ImageOps.fit(im, size, Image.Resampling.LANCZOS, centering=(0.5, 0.55))
            save_widths(im, OUT / "about" / name, (size[0], 800) if size[0] > 800 else (800,), 78)
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
