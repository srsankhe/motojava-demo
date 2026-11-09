# MotoJava demo

A static demonstrator of a redesigned motojava.com, built from the public site's content.
Not a production site: no CMS, no backend, no indexing.

Build: `python3 build.py` writes the site to `docs/`.
Data: `data/site.json` (business info) and `data/bikes.json` (inventory).
Photos: `python3 scripts/images.py` fetches and resizes once into `docs/img/`.
Preview: `python3 -m http.server 8080 -d docs`.

Design tokens: `src/css/tokens.css` is the single source of values for every component.
