"""The curate page: arrange a series by eye, from the browser.

Served by the dev server at http://127.0.0.1:8000/_curate/ and never written
to dist/. It shows every series (published or not) with its photographs in
order. Drag to reorder, click a photograph to make it the cover, star it to
put it in the landing slideshow, and use the focal-point tool to choose
which part of a frame survives the slideshow's crop. Save writes the
result back into that series' series.yaml.

Routes (all under /_curate/):
    /_curate/               the page (scripts/photosite/curate.html)
    /_curate/data           GET  -> JSON for every series
    /_curate/save           POST <- JSON {slug, images, cover, featured, focal}
    /_curate/img/<slug>/<size>/<file>   a cached thumbnail or medium copy

The YAML is edited as text, block by block, so hand-written comments and
the order of the other keys survive.
"""

import json
import re
import urllib.parse
from pathlib import Path

from . import content as content_lib
from . import images

PAGE = Path(__file__).with_name("curate.html")


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------

def series_data(content_dir):
    """Every series as plain dicts, in section then order, including unpublished ones."""
    site = content_lib.load_site(Path(content_dir) / "site.yaml")
    section_rank = {item["slug"]: i for i, item in enumerate(site.nav)}
    result = []
    for folder in sorted(p for p in (Path(content_dir) / "series").iterdir() if p.is_dir()):
        try:
            s = content_lib.load_series(folder, include_unpublished=True)
        except content_lib.ContentError as error:
            result.append({"slug": folder.name, "error": str(error)})
            continue
        result.append({
            "slug": s.slug, "title": s.title, "section": s.section, "order": s.order,
            "tone": s.tone, "published": s.published,
            "images": s.images, "cover": s.cover, "featured": s.featured,
            "focal": s.focal, "captions": s.captions,
        })
    result.sort(key=lambda d: (section_rank.get(d.get("section"), 99), d.get("order", 0), d["slug"]))
    return {"sections": [item["slug"] for item in site.nav if item["slug"] != "about"], "series": result}


# --------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------

def yaml_block(key, value):
    """Render one top-level key the way the rest of series.yaml is written:
    indentless lists, two-space mappings, empty collections inline."""
    if isinstance(value, list):
        return f"{key}: []\n" if not value else f"{key}:\n" + "".join(f"- {v}\n" for v in value)
    if isinstance(value, dict):
        return f"{key}: {{}}\n" if not value else f"{key}:\n" + "".join(f"  {k}: '{v}'\n" for k, v in value.items())
    return f"{key}: {value}\n"


def replace_block(text, key, block):
    """Replace the top-level `key:` block in YAML text, or append it.

    A block runs from `key:` to the next top-level key (a line starting with
    a letter) or a comment line or the end. List items start with '-' and
    mapping entries are indented, so neither ends a block."""
    pattern = re.compile(rf"^{re.escape(key)}:.*?(?=^[A-Za-z_#]|\Z)", re.S | re.M)
    if pattern.search(text):
        return pattern.sub(lambda _: block, text, count=1)
    return text.rstrip("\n") + "\n" + block


def save_series(content_dir, payload):
    """Write images, cover, featured and focal into a series' YAML."""
    slug = payload["slug"]
    folder = Path(content_dir) / "series" / slug
    path = folder / "series.yaml"
    if not path.exists():
        raise ValueError(f"no such series: {slug}")
    on_disk = {p.name for p in folder.iterdir() if p.suffix.lower() in content_lib.IMAGE_SUFFIXES}
    imgs = list(payload["images"])
    if set(imgs) != on_disk:
        raise ValueError(f"{slug}: image list does not match the folder; reload the page")
    if payload["cover"] not in imgs:
        raise ValueError(f"{slug}: cover must be one of the images")
    featured = [f for f in payload.get("featured", []) if f in imgs]
    focal = {k: str(v).strip() for k, v in payload.get("focal", {}).items() if k in imgs and str(v).strip()}
    for value in focal.values():
        if not re.fullmatch(r"\d{1,3}% \d{1,3}%", value):
            raise ValueError(f"{slug}: focal point {value!r} should look like '50% 30%'")

    text = path.read_text(encoding="utf-8")
    text = replace_block(text, "cover", yaml_block("cover", payload["cover"]))
    text = replace_block(text, "featured", yaml_block("featured", featured))
    text = replace_block(text, "images", yaml_block("images", imgs))
    text = replace_block(text, "focal", yaml_block("focal", focal))
    path.write_text(text, encoding="utf-8")
    content_lib.load_series(folder, include_unpublished=True)   # re-validate what we wrote
    return {"saved": slug}


# --------------------------------------------------------------------------
# HTTP routes
# --------------------------------------------------------------------------

def routes(content_dir, cache_dir):
    """Return {path: handler} for serve.serve(extra_routes=...)."""
    content_dir = Path(content_dir)

    def send(handler, status, body, content_type):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        handler.send_response(status)
        handler.send_header("Content-Type", content_type)
        handler.send_header("Content-Length", str(len(data)))
        handler.send_header("Cache-Control", "no-store")
        handler.end_headers()
        handler.wfile.write(data)

    def page(handler):
        send(handler, 200, PAGE.read_text(encoding="utf-8"), "text/html; charset=utf-8")

    def data(handler):
        send(handler, 200, json.dumps(series_data(content_dir)), "application/json")

    def save(handler):
        length = int(handler.headers.get("Content-Length", 0))
        payload = json.loads(handler.rfile.read(length))
        try:
            result = save_series(content_dir, payload)
        except (ValueError, content_lib.ContentError, KeyError) as error:
            return send(handler, 400, json.dumps({"error": str(error)}), "application/json")
        send(handler, 200, json.dumps(result), "application/json")

    def image(handler):
        # /_curate/img/<slug>/<size>/<file>
        parts = urllib.parse.unquote(handler.path.split("?")[0]).split("/")
        try:
            _, _, _, slug, size, filename = parts
            source = content_dir / "series" / slug / filename
            if size not in images.VARIANTS or not source.is_file() or ".." in parts:
                raise ValueError
        except ValueError:
            return handler.send_error(404)
        info = images.process(source, cache_dir)        # cached after the first request
        send(handler, 200, info.variants[size]["path"].read_bytes(), "image/jpeg")

    return {"/_curate/": page, "/_curate/data": data, "/_curate/save": save, "/_curate/img/": image}
