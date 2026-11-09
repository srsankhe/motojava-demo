#!/usr/bin/env python3
"""Build the MotoJava demo site from data/*.json and templates/ into docs/."""
from __future__ import annotations

import html
import json
import shutil
import urllib.parse
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


SOON_SVG = (
    '<svg class="i soon-icon" viewBox="0 0 24 24" aria-hidden="true">'
    '<circle cx="5.5" cy="17.5" r="3.5"/><circle cx="18.5" cy="17.5" r="3.5"/>'
    '<path d="M15 6a1 1 0 1 0 0-2 1 1 0 0 0 0 2zm-3 11.5V14l-3-3 4-3 2 3h2"/></svg>'
)
CHIP = {
    "for-sale": ("chip-sale", "For sale"),
    "pending": ("chip-pending", "Pending sale"),
    "coming-soon": ("chip-soon", "Coming soon"),
}


def fmt_price(p: int | None) -> str:
    return f"${p:,}" if isinstance(p, int) else "Call for price"


def fmt_miles(m: int | None) -> str:
    return f"{m:,} mi" if isinstance(m, int) else ""


def title_of(bike: dict) -> str:
    return f'{bike["year"]} {bike["make"]} {bike["model"]}'


def spec_line(bike: dict) -> str:
    parts = []
    if fmt_miles(bike.get("miles")):
        parts.append(fmt_miles(bike["miles"]))
    if bike.get("abs") is True:
        parts.append("ABS")
    for h in bike.get("highlights", []):
        if len(parts) >= 3:
            break
        if h not in parts and h.lower() != "abs":
            parts.append(h)
    return " · ".join(esc(p) for p in parts[:3])


def card_html(bike: dict, root: str, eager: bool = False) -> str:
    soon = bike["status"] == "coming-soon"
    chip_class, chip_text = CHIP[bike["status"]]
    title = esc(title_of(bike))
    if soon:
        photo = SOON_SVG
        price_html = fmt_price(bike["price"]) if isinstance(bike.get("price"), int) else "Price on arrival"
    else:
        src = f'{root}img/bikes/{bike["slug"]}/01-480.webp'
        loading = "eager" if eager else "lazy"
        photo = f'<img src="{src}" width="480" height="360" alt="{title}" loading="{loading}">'
        price_html = fmt_price(bike["price"])
        if isinstance(bike.get("was_price"), int):
            price_html += f' <s>{fmt_price(bike["was_price"])}</s>'
    ctx = {
        "tag": "div" if soon else "a",
        "card_mod": " card-soon" if soon else "",
        "href": "" if soon else f' href="{root}bikes/{bike["slug"]}/"',
        "type": bike["type"],
        "price_num": bike["price"] if isinstance(bike.get("price"), int) else "",
        "status": bike["status"],
        "photo_mod": " soon" if soon else "",
        "photo": photo,
        "chip_class": chip_class,
        "chip_text": chip_text,
        "title": title,
        "spec": spec_line(bike),
        "price_mod": " muted price-soon" if soon and not isinstance(bike.get("price"), int) else "",
        "price_html": price_html,
        "cta": "Ask" if soon else "Details",
    }
    return render(read(PARTIALS / "card.html"), ctx)


TYPE_LABEL = {
    "scooter": "Scooter", "standard": "Standard", "sport": "Sport", "cruiser": "Cruiser",
    "adventure": "Adventure", "dual-sport": "Dual sport", "touring": "Touring", "mini": "Mini",
}
PRICE_BANDS = (("lt3000", "Under $3k"), ("3000-5000", "$3k to $5k"), ("gt5000", "Over $5k"))


def filter_chips(bikes: list[dict]) -> str:
    types = [t for t in TYPE_LABEL if any(b["type"] == t for b in bikes)]
    out = ['<span class="label">Type</span>']
    out += [f'<button type="button" class="chip chip-filter" data-group="type" data-value="{t}" aria-pressed="false">{TYPE_LABEL[t]}</button>' for t in types]
    out.append('<span class="label">Price</span>')
    out += [f'<button type="button" class="chip chip-filter" data-group="price" data-value="{v}" aria-pressed="false">{esc(l)}</button>' for v, l in PRICE_BANDS]
    out.append('<button type="button" class="btn btn-ghost btn-sm" data-clear>Clear</button>')
    return "\n      ".join(out)


def spec_rows(bike: dict) -> str:
    rows = [("Year", str(bike["year"])), ("Make", bike["make"]), ("Model", bike["model"])]
    if isinstance(bike.get("miles"), int):
        rows.append(("Mileage", fmt_miles(bike["miles"])))
    if isinstance(bike.get("engine_cc"), int):
        rows.append(("Engine", f'{bike["engine_cc"]} cc'))
    if bike.get("abs") is not None:
        rows.append(("ABS", "Yes" if bike["abs"] else "No"))
    if bike.get("mpg"):
        rows.append(("Fuel economy", f'{bike["mpg"]} mpg'))
    if bike.get("color"):
        rows.append(("Color", bike["color"]))
    if bike.get("highlights"):
        rows.append(("Highlights", ", ".join(bike["highlights"])))
    rows.append(("Before sale", "Tune-up, 37-point inspection, safety check"))
    return "\n".join(f"        <dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in rows)


def more_bikes(bike: dict, bikes: list[dict]) -> list[dict]:
    pool = [b for b in bikes if b["status"] in ("for-sale", "pending") and b["slug"] != bike["slug"]]
    same = [b for b in pool if b["type"] == bike["type"]]
    picked = same[:3]
    if len(picked) < 3:
        picked += [b for b in pool if b not in picked][: 3 - len(picked)]
    return picked


def bike_page(bike: dict, bikes: list[dict], site: dict) -> str:
    root = "../../"
    ctx = base_context(site, root=root, page="bike")
    title = title_of(bike)
    n = len(bike["photos"])
    chip_class, chip_text = CHIP[bike["status"]]
    price_html = fmt_price(bike["price"])
    if isinstance(bike.get("was_price"), int):
        price_html += f' <s>{fmt_price(bike["was_price"])}</s>'
    thumbs = "\n".join(
        f'        <button type="button" role="listitem" data-full="{root}img/bikes/{bike["slug"]}/{i:02d}.webp" aria-label="Photo {i} of {n}">'
        f'<img src="{root}img/bikes/{bike["slug"]}/{i:02d}-480.webp" width="480" height="360" alt="" loading="lazy"></button>'
        for i in range(1, n + 1)
    )
    notes = f'<p class="notes">{esc(bike["notes"])}</p>' if bike.get("notes") else ""
    sms_body = urllib.parse.quote(f"Hi MotoJava, I'm interested in the {title}.")
    ctx.update({
        "title": esc(title),
        "description": f"{esc(title)} at MotoJava, San Francisco. {fmt_price(bike['price'])}.",
        "slug": bike["slug"],
        "photo_count": str(n),
        "thumbs": thumbs,
        "chip_class": chip_class,
        "chip_text": chip_text,
        "price_html": price_html,
        "spec": spec_line(bike),
        "sms_body": sms_body,
        "financing_text": esc(site["financing"]["text"]),
        "financing_url": esc(site["financing"]["url"]),
        "financing_cta": esc(site["financing"]["cta"]),
        "spec_rows": spec_rows(bike),
        "notes_html": notes,
        "fees_heading": esc(site["fees"]["heading"]),
        "fees_text": esc(site["fees"]["text"]),
        "count": str(sum(1 for b in bikes if b["status"] in ("for-sale", "pending"))),
        "more_cards": "\n".join(card_html(b, root) for b in more_bikes(bike, bikes)),
        "extra_scripts": f'<script src="{root}js/gallery.js" defer></script>',
    })
    return ctx


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

    for_sale = [b for b in bikes if b["status"] in ("for-sale", "pending")]
    soon = [b for b in bikes if b["status"] == "coming-soon"]

    ctx = base_context(site, root="", page="bikes")
    ctx["title"] = "Used bikes in San Francisco"
    ctx["cards"] = "\n".join(card_html(b, "", eager=i < 6) for i, b in enumerate(for_sale))
    ctx["soon_cards"] = "\n".join(card_html(b, "") for b in soon)
    ctx["count"] = str(len(for_sale))
    ctx["filters"] = filter_chips(for_sale)
    ctx["extra_scripts"] = '<script src="js/filters.js" defer></script>'
    written.append(page("index.html", ctx, DOCS / "index.html"))

    for b in for_sale:
        written.append(page("bike.html", bike_page(b, bikes, site), DOCS / "bikes" / b["slug"] / "index.html"))

    written.extend(copy_assets())
    return written


if __name__ == "__main__":
    for p in build():
        print(p.relative_to(ROOT))
