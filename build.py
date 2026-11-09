#!/usr/bin/env python3
"""Build the MotoJava demo site from data/*.json and templates/ into docs/."""
from __future__ import annotations

import html
import json
import shutil
import urllib.parse
from functools import lru_cache
from pathlib import Path
from string import Template

from PIL import Image

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


@lru_cache(maxsize=None)
def img_size(rel: str) -> tuple[int, int]:
    """(width, height) of a file under docs/img, read once per build."""
    with Image.open(DOCS / "img" / rel) as im:
        return im.size


def photo_srcset(slug: str, index: int, root: str) -> str:
    """srcset with the real width of each variant, smallest first."""
    parts, seen = [], set()
    for suffix in ("-480", "-800", ""):
        rel = f"bikes/{slug}/{index:02d}{suffix}.webp"
        if not (DOCS / "img" / rel).exists():
            continue
        w = img_size(rel)[0]
        if w in seen:  # source photo smaller than the variant size: same pixels, skip the duplicate
            continue
        seen.add(w)
        parts.append(f"{root}img/{rel} {w}w")
    return ", ".join(parts)


SMS = ""  # set in build() from site.json


def card_html(bike: dict, root: str, eager: bool = False) -> str:
    soon = bike["status"] == "coming-soon"
    chip_class, chip_text = CHIP[bike["status"]]
    title = esc(title_of(bike))
    if soon:
        photo = SOON_SVG
        price_html = fmt_price(bike["price"]) if isinstance(bike.get("price"), int) else "Price on arrival"
        body = urllib.parse.quote(f"Hi MotoJava, is the {title_of(bike)} ready yet?")
        cta_html = f'<a class="btn btn-ghost btn-sm" href="sms:{SMS}?&body={body}">Ask ›</a>'
    else:
        cta_html = '<span class="btn btn-ghost btn-sm">Details ›</span>'
    if not soon:
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
        "cta_html": cta_html,
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
        f'        <button type="button" role="listitem" data-full="{root}img/bikes/{bike["slug"]}/{i:02d}.webp" '
        f'data-srcset="{photo_srcset(bike["slug"], i, root)}" aria-label="Photo {i} of {n}">'
        f'<img src="{root}img/bikes/{bike["slug"]}/{i:02d}-480.webp" width="480" height="360" alt="" loading="lazy"></button>'
        for i in range(1, n + 1)
    )
    main_w, main_h = img_size(f'bikes/{bike["slug"]}/01.webp')
    notes = f'<p class="notes">{esc(bike["notes"])}</p>' if bike.get("notes") else ""
    sms_body = urllib.parse.quote(f"Hi MotoJava, I'm interested in the {title}.")
    ctx.update({
        "title": esc(title),
        "description": f"{esc(title)} at MotoJava, San Francisco. {fmt_price(bike['price'])}.",
        "slug": bike["slug"],
        "photo_count": str(n),
        "thumbs": thumbs,
        "main_srcset": photo_srcset(bike["slug"], 1, root),
        "main_w": str(main_w),
        "main_h": str(main_h),
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


ICONS = {
    "check": '<path d="M20 6L9 17l-5-5"/>',
    "list": '<path d="M9 5h11M9 12h11M9 19h11M4 5h.01M4 12h.01M4 19h.01"/>',
    "drop": '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
    "wrench": '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    "tire": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/><path d="M12 3v6M12 15v6M3 12h6M15 12h6"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
    "tag": '<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><circle cx="7" cy="7" r="1"/>',
}


def icon(name: str, cls: str = "i") -> str:
    return f'<svg class="{cls}" viewBox="0 0 24 24" aria-hidden="true">{ICONS[name]}</svg>'


def service_rows(site: dict) -> str:
    return "\n".join(
        f'      <li class="menu-row"><span class="menu-icon">{icon(s["icon"])}</span>'
        f'<div class="menu-text"><h3 class="h3">{esc(s["name"])}</h3><p class="small muted">{esc(s["text"])}</p></div>'
        f'<span class="menu-price">{esc(s["price"])}<small>{esc(s.get("price_note", ""))}</small></span></li>'
        for s in site["services"]
    )


def service_facts(site: dict) -> str:
    return "\n".join(
        f'      <li><span class="fact-value">{esc(f["value"])}</span><span class="small">{esc(f["label"])}</span></li>'
        for f in site["service_facts"]
    )


def service_steps(site: dict) -> str:
    return "\n".join(
        f'      <li class="step"><span class="step-num" aria-hidden="true">{i}</span><h3 class="h3">{esc(s["title"])}</h3><p class="small muted">{esc(s["text"])}</p></li>'
        for i, s in enumerate(site["service_steps"], start=1)
    )


def stats_html(site: dict) -> str:
    return "\n".join(
        f'      <div class="stat"><span class="stat-value">{esc(s["value"])}</span><span class="label">{esc(s["label"])}</span></div>'
        for s in site["stats"]
    )


def team_html(site: dict, root: str = "../") -> str:
    out = []
    for t in site["team"]:
        if t.get("photo"):
            avatar = f'<img class="avatar avatar-photo" src="{root}img/team/{t["photo"]}" width="320" height="320" alt="{esc(t["name"])}" loading="lazy">'
        else:
            avatar = f'<span class="avatar" aria-hidden="true">{esc(t["name"][0])}</span>'
        out.append(
            f'      <div class="person">{avatar}<div class="person-text"><h3 class="h3">{esc(t["name"])}</h3>'
            f'<span class="label">{esc(t["role"])}</span><p class="small">{esc(t["bio"])}</p></div></div>'
        )
    return "\n".join(out)


def facts_list(items: list[dict]) -> str:
    return "\n".join(
        f'        <li><strong>{esc(f["lead"])}</strong> {esc(f["text"])}</li>' for f in items
    )


def list_items(items: list[str]) -> str:
    return "\n".join(f"        <li>{icon('check')}<span>{esc(i)}</span></li>" for i in items)


def directions_html(site: dict) -> str:
    return "\n".join(
        f'      <div class="svc"><h3 class="h3">{esc(d["from"])}</h3><p class="small">{esc(d["text"])}</p></div>'
        for d in site["directions"]
    )


def why_html(site: dict) -> str:
    icons = ("shield", "file", "tag")
    return "\n".join(
        f'      <div class="why"><span class="why-icon">{icon(ic, "i")}</span><h3 class="h3">{esc(w["title"])}</h3><p class="small muted">{esc(w["text"])}</p></div>'
        for w, ic in zip(site["why"], icons)
    )


def kymco_html(site: dict, root: str = "../") -> str:
    out = []
    for k in site["kymco"]:
        if k.get("photo"):
            rel = f'kymco/{k["photo"]}'
            full = rel + ".webp"
            w = img_size(full)[0]
            srcset = f'{root}img/{rel}-480.webp 480w' + (f', {root}img/{full} {w}w' if w > 480 else "")
            photo = (f'<img src="{root}img/{full}" srcset="{srcset}" sizes="(max-width: 59.99em) 100vw, 380px" '
                     f'width="{w}" height="{round(w * 3 / 4)}" alt="{esc(k["name"])}" loading="lazy">')
        else:
            photo = f'<div class="kymco-placeholder"><img src="{root}img/brand/kymco.png" alt="" width="200" height="31"></div>'
        out.append(
            f'      <div class="card kymco-card"><div class="photo">{photo}<span class="chip chip-sale">New</span></div>'
            f'<div class="card-body"><h3 class="h3">{esc(k["name"])}</h3><p class="spec">{esc(k["note"])}</p>'
            f'<div class="card-foot"><span class="price">{esc(k["price"])}</span></div>'
            f'<p class="small muted">{esc(k["fine"])}</p><p class="small muted photo-note">{esc(k.get("photo_note", ""))}</p></div></div>'
        )
    return "\n".join(out)


def content_pages(site: dict, bikes: list[dict]) -> list[tuple[str, dict, Path]]:
    pages = []
    ctx = base_context(site, root="../", page="service")
    ctx.update({
        "title": "Service and repair", "service_intro": esc(site["service_intro"]),
        "service_rows": service_rows(site), "service_facts": service_facts(site),
        "service_steps": service_steps(site), "tow_heading": esc(site["tow"]["heading"]),
        "tow_price_sf": site["tow"]["price_sf"], "tow_price_eastbay": site["tow"]["price_eastbay"],
        "tow_text": esc(site["tow"]["text"]),
    })
    pages.append(("service.html", ctx, DOCS / "service" / "index.html"))

    ctx = base_context(site, root="../", page="visit")
    ctx.update({"title": "Visit", "directions": directions_html(site)})
    pages.append(("visit.html", ctx, DOCS / "visit" / "index.html"))

    # GitHub Pages serves 404.html at the requested URL (no redirect), so relative
    # asset paths break on deep URLs; the 404 page alone uses the absolute base path.
    ctx = base_context(site, root=site.get("base_path", "/"), page="404")
    ctx.update({"title": "Page not found"})
    pages.append(("404.html", ctx, DOCS / "404.html"))
    return pages


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
        "callbar": (
            f'<div class="callbar" data-callbar><a class="btn btn-primary" href="tel:{site["tel"]}">Call</a>'
            f'<a class="btn btn-secondary" href="sms:{site["sms"]}">Text</a></div>'
            if page in ("bikes", "bike") else ""
        ),
        "hours_summary": esc(site["hours_summary"]),
        "extra_scripts": "",
        "description": "Used motorcycles and scooters in San Francisco, inspected and serviced. Demonstration site.",
    }
    for key in NAV_KEYS:
        active = key == page or (key == "bikes" and page == "bike")  # detail pages light up Bikes
        ctx[f"nav_{key}"] = "active" if active else ""
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
    full_ctx = {**ctx, **partials(ctx)}  # partials first, so body templates can include them
    body = render(read(TEMPLATES / template_name), full_ctx)
    html_out = render(read(TEMPLATES / "base.html"), {**full_ctx, "content": body})
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
    global SMS
    site = load_json(DATA / "site.json")
    SMS = site["sms"]
    bikes = load_json(DATA / "bikes.json")  # used from Task 5 on
    written: list[Path] = []

    for_sale = [b for b in bikes if b["status"] in ("for-sale", "pending")]
    soon = [b for b in bikes if b["status"] == "coming-soon"]

    # Landing page: About. The user chose identity ahead of inventory.
    ctx = base_context(site, root="", page="about")
    ctx.update({
        "title": "Used bikes, service and repair in San Francisco",
        "stats": stats_html(site), "refurbish": list_items(site["refurbish"]),
        "team": team_html(site, root=""), "mike_facts": facts_list(site["mike_facts"]),
        "citybike_source": esc(site["citybike"]["source"]),
    })
    written.append(page("about.html", ctx, DOCS / "index.html"))

    # Inventory: /bikes/
    root = "../"
    ctx = base_context(site, root=root, page="bikes")
    ctx["title"] = "Bikes for sale"
    ctx["cards"] = "\n".join(card_html(b, root) for b in for_sale)  # all lazy: the hero fills the first screen
    ctx["soon_cards"] = "\n".join(card_html(b, root) for b in soon)
    ctx["count"] = str(len(for_sale))
    ctx["filters"] = filter_chips(for_sale)
    ctx["why"] = why_html(site)
    ctx["kymco"] = kymco_html(site, root)
    ctx["kymco_credit"] = esc(site["kymco_credit"])
    ctx["extra_scripts"] = f'<script src="{root}js/filters.js" defer></script>'
    written.append(page("bikes.html", ctx, DOCS / "bikes" / "index.html"))

    for b in for_sale:
        written.append(page("bike.html", bike_page(b, bikes, site), DOCS / "bikes" / b["slug"] / "index.html"))

    for template_name, ctx, out in content_pages(site, bikes):
        written.append(page(template_name, ctx, out))

    written.extend(copy_assets())
    return written


if __name__ == "__main__":
    for p in build():
        print(p.relative_to(ROOT))
