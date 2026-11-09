#!/usr/bin/env python3
"""Validate data/bikes.json against the demo spec's data model. Exit 1 on any problem."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIKES = ROOT / "data" / "bikes.json"

REQUIRED = {
    "slug", "year", "make", "model", "type", "status", "price", "was_price", "miles",
    "abs", "mpg", "engine_cc", "color", "highlights", "notes", "photos",
}
MAKES = {"Honda", "Kawasaki", "Yamaha", "Suzuki", "Triumph", "BMW", "Vespa", "Kymco", "Harley-Davidson", "Ducati"}
TYPES = {"scooter", "standard", "sport", "cruiser", "adventure", "dual-sport", "touring", "mini"}
STATUSES = {"for-sale", "pending", "coming-soon"}
CAPS_OK = {
    "ABS", "KRT", "ADV", "CB", "CBR", "KLR", "KLX", "FZ6R", "SV650", "GTS", "GTV", "LXV",
    "NC700X", "CV3", "GL1800", "BMW", "KBB", "DMV", "SF", "MPG", "KTM", "GT", "LED", "EFI",
}


def is_int_or_none(v) -> bool:
    return v is None or (isinstance(v, int) and not isinstance(v, bool))


def validate(bikes: list[dict]) -> list[str]:
    problems: list[str] = []
    slugs: set[str] = set()
    for i, b in enumerate(bikes):
        tag = f"[{i}] {b.get('slug', '?')}"
        missing = REQUIRED - set(b)
        extra = set(b) - REQUIRED
        if missing:
            problems.append(f"{tag}: missing keys {sorted(missing)}")
        if extra:
            problems.append(f"{tag}: unknown keys {sorted(extra)}")
        slug = b.get("slug", "")
        if not re.fullmatch(r"[a-z0-9-]+", slug):
            problems.append(f"{tag}: slug not kebab-case")
        if slug in slugs:
            problems.append(f"{tag}: duplicate slug")
        slugs.add(slug)
        if not (isinstance(b.get("year"), int) and 1990 <= b["year"] <= 2026):
            problems.append(f"{tag}: year out of range")
        if b.get("make") not in MAKES:
            problems.append(f"{tag}: make {b.get('make')!r} not canonical")
        if b.get("type") not in TYPES:
            problems.append(f"{tag}: type {b.get('type')!r} invalid")
        if b.get("status") not in STATUSES:
            problems.append(f"{tag}: status {b.get('status')!r} invalid")
        for k in ("price", "was_price", "miles", "engine_cc"):
            if not is_int_or_none(b.get(k)):
                problems.append(f"{tag}: {k} must be int or null")
        if b.get("abs") not in (True, False, None):
            problems.append(f"{tag}: abs must be bool or null")
        if b.get("mpg") is not None and not isinstance(b["mpg"], str):
            problems.append(f"{tag}: mpg must be string or null")
        photos = b.get("photos", [])
        if b.get("status") in ("for-sale", "pending") and not photos:
            problems.append(f"{tag}: for-sale/pending needs photos")
        if b.get("status") == "coming-soon" and photos:
            problems.append(f"{tag}: coming-soon must have photos == []")
        if len(b.get("highlights", [])) > 3:
            problems.append(f"{tag}: more than 3 highlights")
        for field in ("model", "notes", "color"):
            v = b.get(field) or ""
            if "((" in v or "))" in v or "  " in v:
                problems.append(f"{tag}: {field} has '((' , '))' or double space")
            for word in re.findall(r"[A-Z]{4,}", v):
                if word not in CAPS_OK:
                    problems.append(f"{tag}: {field} has all-caps word {word!r}")
        for hgl in b.get("highlights", []):
            for word in re.findall(r"[A-Z]{4,}", hgl):
                if word not in CAPS_OK:
                    problems.append(f"{tag}: highlight has all-caps word {word!r}")
    return problems


def main() -> int:
    bikes = json.loads(BIKES.read_text(encoding="utf-8"))
    problems = validate(bikes)
    for p in problems:
        print(p)
    if problems:
        print(f"{len(problems)} problems")
        return 1
    print(f"{len(bikes)} bikes OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
