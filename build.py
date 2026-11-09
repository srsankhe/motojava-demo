#!/usr/bin/env python3
"""Build the MotoJava demo site from data/*.json and templates/ into docs/."""
from __future__ import annotations

import html
import json
import shutil
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
TEMPLATES = ROOT / "templates"
PARTIALS = TEMPLATES / "partials"
SRC = ROOT / "src"
DOCS = ROOT / "docs"

NAV_KEYS = ("bikes", "service", "about", "visit")


def load_json(path: Path) -> dict | list:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def render(template: str, ctx: dict) -> str:
    """Fill ${key} placeholders; unknown keys are left as-is."""
    return Template(template).safe_substitute(ctx)


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def hours_rows(site: dict) -> str:
    rows = []
    for h in site["hours"]:
        value = h.get("note") or f'{h["open"]} to {h["close"]}'
        rows.append(f'  <div data-day="{h["day"]}"><dt>{h["day"]}</dt><dd>{esc(value)}</dd></div>')
    return "\n".join(rows)


def partner_links(site: dict) -> str:
    return "\n".join(
        f'      <a class="footer-link" href="{esc(p["url"])}" target="_blank" rel="noopener">{esc(p["name"])}</a>'
        for p in site["partners"]
    )


def base_context(site: dict, root: str, page: str) -> dict:
    ctx = {
        "root": root,
        "page": page,
        "tagline": esc(site["tagline"]),
        "phone": esc(site["phone"]),
        "tel": site["tel"],
        "sms": site["sms"],
        "email": site["email"],
        "address_1": esc(site["address"][0]),
        "address_2": esc(site["address"][1]),
        "landmarks": esc(site["landmarks"]),
        "maps_url": esc(site["maps_url"]),
        "updated": esc(site["updated"]),
        "hours_rows": hours_rows(site),
        "partner_links": partner_links(site),
        "callbar": "",
        "extra_scripts": "",
        "description": "Used motorcycles and scooters in San Francisco, inspected and serviced. Demonstration site.",
    }
    for key in NAV_KEYS:
        ctx[f"nav_{key}"] = "active" if key == page else ""
    return ctx


def partials(ctx: dict) -> dict:
    out = {}
    # hours first so footer can include it
    hours = render(read(PARTIALS / "hours.html"), ctx)
    ctx = {**ctx, "partial_hours": hours}
    out["partial_hours"] = hours
    for p in sorted(PARTIALS.glob("*.html")):
        if p.stem == "hours":
            continue
        out[f"partial_{p.stem}"] = render(read(p), ctx)
    return out


def page(template_name: str, ctx: dict, out_path: Path) -> Path:
    body = render(read(TEMPLATES / template_name), ctx)
    full_ctx = {**ctx, **partials(ctx), "content": body}
    html_out = render(read(TEMPLATES / "base.html"), full_ctx)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_out, encoding="utf-8")
    return out_path


def copy_assets() -> list[Path]:
    written = []
    for sub in ("css", "js"):
        dest = DOCS / sub
        dest.mkdir(parents=True, exist_ok=True)
        for f in (SRC / sub).glob("*"):
            if f.is_file():
                shutil.copy2(f, dest / f.name)
                written.append(dest / f.name)
    return written


def build(root: Path = ROOT) -> list[Path]:
    site = load_json(DATA / "site.json")
    bikes = load_json(DATA / "bikes.json")  # used from Task 5 on
    written: list[Path] = []

    ctx = base_context(site, root="", page="bikes")
    ctx["title"] = "Used bikes in San Francisco"
    written.append(page("index.html", ctx, DOCS / "index.html"))

    written.extend(copy_assets())
    return written


if __name__ == "__main__":
    for p in build():
        print(p.relative_to(ROOT))
