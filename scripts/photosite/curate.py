"""The curate page: arrange, add, and remove photographs from the browser.

Served by the dev server at http://127.0.0.1:8000/_curate/ and never written
to dist/. It shows every series (published or not) with its photographs in
order, plus the landing slideshow in the order it will run. From it you can
reorder by dragging, choose the cover, star an image into the slideshow,
place a focal point, upload new photographs, move a photograph to another
series or to the holding folder, bring a held file into a series, and create
a new series. Every change is written straight into content/ and the dev
server's watcher rebuilds the site.

Routes (all under /_curate/):
    /_curate/                 the page (scripts/photosite/curate.html)
    /_curate/data             GET  -> JSON: every series, the holding folders
    /_curate/save             POST <- {slug, images, cover, featured, focal}
    /_curate/upload?slug=..   POST <- raw JPEG bytes, X-Filename header
    /_curate/move             POST <- {from: "<slug>" | "_unplaced/x" | "_removed/x",
                                        file, to: "<slug>" | "_removed"}
    /_curate/delete           POST <- {holding: "_removed/x", file}   (permanent)
    /_curate/series           POST <- {title, section, tone, order?}  (create)
    /_curate/img/<slug>/<size>/<file>            a cached thumbnail or medium copy
    /_curate/img/_holding/<size>/<group>/<file>  the same for held files

YAML is edited as text, block by block, so hand-written comments and the
order of the other keys survive. Nothing here is ever deleted except by the
explicit delete route, which only touches the holding folders.
"""

import io
import json
import re
import shutil
import urllib.parse
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from . import content as content_lib
from . import images

PAGE = Path(__file__).with_name("curate.html")
HOLDING = ("_unplaced", "_removed")      # folders under content/ the build ignores
HEADER = ("# Series metadata. `images` is the display order; edit it here or\n"
          "# with the curate page (python scripts/build.py --serve, then /_curate/).\n")


class CurateError(ValueError):
    """A request that cannot be honoured; the message goes back to the page."""


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------

def series_folder(content_dir, slug):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        raise CurateError(f"bad series name: {slug!r}")
    folder = Path(content_dir) / "series" / slug
    if not (folder / "series.yaml").exists():
        raise CurateError(f"no such series: {slug}")
    return folder


def holding_path(content_dir, group):
    """`group` looks like '_removed/alpenglow'; returns that folder."""
    parts = group.split("/")
    if len(parts) != 2 or parts[0] not in HOLDING or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", parts[1]):
        raise CurateError(f"bad holding folder: {group!r}")
    return Path(content_dir) / parts[0] / parts[1]


def series_data(content_dir):
    """Every series as plain dicts, in section then order, including unpublished ones."""
    content_dir = Path(content_dir)
    site = content_lib.load_site(content_dir / "site.yaml")
    section_rank = {item["slug"]: i for i, item in enumerate(site.nav)}
    result = []
    for folder in sorted(p for p in (content_dir / "series").iterdir() if p.is_dir()):
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

    holding = []
    for name in HOLDING:
        root = content_dir / name
        if not root.is_dir():
            continue
        for group in sorted(p for p in root.iterdir() if p.is_dir()):
            for f in sorted(p for p in group.iterdir() if p.suffix.lower() in content_lib.IMAGE_SUFFIXES):
                holding.append({"group": f"{name}/{group.name}", "file": f.name})
    return {"sections": [item["slug"] for item in site.nav if item["slug"] != "about"],
            "tones": list(content_lib.TONES), "series": result, "holding": holding}


# --------------------------------------------------------------------------
# YAML editing
# --------------------------------------------------------------------------

def yaml_scalar(value):
    """Quote a string for YAML unless it is plainly safe."""
    text = str(value)
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._\-]*", text) and not text.lower() in ("true", "false", "null", "yes", "no"):
        return text
    return "'" + text.replace("'", "''") + "'"


def yaml_block(key, value):
    """Render one top-level key the way series.yaml is written: indentless
    lists, two-space mappings, empty collections inline."""
    if isinstance(value, list):
        return f"{key}: []\n" if not value else f"{key}:\n" + "".join(f"- {yaml_scalar(v)}\n" for v in value)
    if isinstance(value, dict):
        return f"{key}: {{}}\n" if not value else f"{key}:\n" + "".join(
            f"  {yaml_scalar(k)}: {yaml_scalar(v)}\n" for k, v in value.items())
    scalar = yaml_scalar(value) if value != "" else "''"
    return f"{key}: {scalar}\n"


def replace_block(text, key, block):
    """Replace the top-level `key:` block in YAML text, or append it.

    A block runs from `key:` to the next top-level key (a line starting with
    a letter) or a comment line or the end. List items start with '-' and
    mapping entries are indented, so neither ends a block."""
    pattern = re.compile(rf"^{re.escape(key)}:.*?(?=^[A-Za-z_#]|\Z)", re.S | re.M)
    if pattern.search(text):
        return pattern.sub(lambda _: block, text, count=1)
    return text.rstrip("\n") + "\n" + block


def write_lists(folder, **blocks):
    """Rewrite the given top-level keys of a series' YAML and re-validate."""
    path = folder / "series.yaml"
    text = path.read_text(encoding="utf-8")
    for key, value in blocks.items():
        text = replace_block(text, key, yaml_block(key, value))
    path.write_text(text, encoding="utf-8")
    return content_lib.load_series(folder, include_unpublished=True)


def read_lists(folder):
    """The editable lists of a series as plain values."""
    s = content_lib.load_series(folder, include_unpublished=True)
    return {"images": list(s.images), "cover": s.cover, "featured": list(s.featured),
            "focal": dict(s.focal), "captions": dict(s.captions)}


# --------------------------------------------------------------------------
# Operations
# --------------------------------------------------------------------------

def save_series(content_dir, payload):
    """Write images, cover, featured and focal from the page."""
    slug = payload["slug"]
    folder = series_folder(content_dir, slug)
    on_disk = {p.name for p in folder.iterdir() if p.suffix.lower() in content_lib.IMAGE_SUFFIXES}
    imgs = list(payload["images"])
    if set(imgs) != on_disk or len(imgs) != len(on_disk):
        raise CurateError(f"{slug}: the image list no longer matches the folder; reload the page")
    cover = payload.get("cover") or (imgs[0] if imgs else "")
    if imgs and cover not in imgs:
        raise CurateError(f"{slug}: cover must be one of the images")
    featured = [f for f in payload.get("featured", []) if f in imgs]
    focal = {k: str(v).strip() for k, v in payload.get("focal", {}).items() if k in imgs and str(v).strip()}
    for value in focal.values():
        if not re.fullmatch(r"\d{1,3}% \d{1,3}%", value):
            raise CurateError(f"{slug}: focal point {value!r} should look like '50% 30%'")
    write_lists(folder, cover=cover, featured=featured, images=imgs, focal=focal)
    return {"saved": slug}


def safe_filename(name):
    name = Path(name).name.replace("+", " ")
    name = re.sub(r"\s+", "-", name.strip())
    name = re.sub(r"[^A-Za-z0-9._-]", "", name)
    if not name or name.startswith("."):
        raise CurateError(f"cannot use filename {name!r}")
    return name


def unique_name(folder, name):
    """`name`, or name-2, name-3, ... if it is already taken in `folder`."""
    stem, suffix = Path(name).stem, Path(name).suffix
    candidate, n = name, 2
    while (folder / candidate).exists():
        candidate = f"{stem}-{n}{suffix}"
        n += 1
    return candidate


def upload(content_dir, slug, filename, data):
    """Add one JPEG to a series and append it to `images`."""
    folder = series_folder(content_dir, slug)
    name = safe_filename(filename)
    if Path(name).suffix.lower() not in content_lib.IMAGE_SUFFIXES:
        raise CurateError(f"{name}: only JPEG files (.jpg) belong in a series")
    try:
        with Image.open(io.BytesIO(data)) as im:
            if im.format != "JPEG":
                raise CurateError(f"{name}: not a JPEG (it is {im.format})")
    except UnidentifiedImageError:
        raise CurateError(f"{name}: not an image") from None
    name = unique_name(folder, name)
    (folder / name).write_bytes(data)
    # The loader already appends any file it finds unlisted, so just make
    # that order explicit in the YAML.
    lists = read_lists(folder)
    if name not in lists["images"]:
        lists["images"].append(name)
    write_lists(folder, images=lists["images"], cover=lists["cover"] or name)
    return {"added": name, "slug": slug}


def detach(folder, name):
    """Drop `name` from every list in a series' YAML; returns its caption/focal."""
    lists = read_lists(folder)
    if name not in lists["images"]:
        raise CurateError(f"{name} is not in {folder.name}")
    lists["images"].remove(name)
    featured = [f for f in lists["featured"] if f != name]
    caption = lists["captions"].pop(name, None)
    focal = lists["focal"].pop(name, None)
    cover = lists["cover"] if lists["cover"] != name else (lists["images"][0] if lists["images"] else "")
    write_lists(folder, images=lists["images"], cover=cover, featured=featured,
                captions=lists["captions"], focal=lists["focal"])
    return caption, focal


def attach(folder, name, caption=None, focal=None):
    """Append `name` to a series' lists (the file must already be there)."""
    lists = read_lists(folder)
    if name not in lists["images"]:
        lists["images"].append(name)
    if caption:
        lists["captions"][name] = caption
    if focal:
        lists["focal"][name] = focal
    write_lists(folder, images=lists["images"], cover=lists["cover"] or name,
                captions=lists["captions"], focal=lists["focal"])


def move(content_dir, source, name, target):
    """Move a photograph from a series or holding folder to a series or to
    `_removed`. Captions and focal points travel with it between series."""
    content_dir = Path(content_dir)
    name = safe_filename(name)
    caption = focal = None
    if source.startswith(HOLDING):
        src_folder = holding_path(content_dir, source)
    else:
        src_folder = series_folder(content_dir, source)
    src = src_folder / name
    if not src.is_file():
        raise CurateError(f"{source}/{name} does not exist")

    if target == "_removed":
        if source.startswith(HOLDING):
            raise CurateError("already in a holding folder")
        dst_folder = content_dir / "_removed" / source
    else:
        dst_folder = series_folder(content_dir, target)
    if dst_folder == src_folder:
        raise CurateError("that is where it already is")
    dst_folder.mkdir(parents=True, exist_ok=True)
    dst_name = unique_name(dst_folder, name)

    if not source.startswith(HOLDING):
        caption, focal = detach(src_folder, name)
    shutil.move(str(src), str(dst_folder / dst_name))
    if target != "_removed":
        attach(dst_folder, dst_name, caption, focal)
    # tidy an emptied holding folder
    if source.startswith(HOLDING) and not any(src_folder.iterdir()):
        src_folder.rmdir()
    return {"moved": dst_name, "to": target}


def delete_held(content_dir, group, name):
    """Permanently delete a file from a holding folder. Only there."""
    folder = holding_path(content_dir, group)
    path = folder / safe_filename(name)
    if not path.is_file():
        raise CurateError(f"{group}/{name} does not exist")
    path.unlink()
    if not any(folder.iterdir()):
        folder.rmdir()
    return {"deleted": name}


def slugify(title):
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not slug:
        raise CurateError("the title needs at least one letter or digit")
    return slug


def create_series(content_dir, payload):
    """Make content/series/<slug>/series.yaml for a new, empty, unpublished series."""
    content_dir = Path(content_dir)
    title = str(payload.get("title", "")).strip()
    section, tone = payload.get("section"), payload.get("tone")
    if not title:
        raise CurateError("a title is needed")
    if section not in content_lib.SECTIONS or tone not in content_lib.TONES:
        raise CurateError("section or tone is not one of the allowed values")
    slug = slugify(title)
    folder = content_dir / "series" / slug
    if folder.exists():
        raise CurateError(f"a series folder called {slug} already exists")
    order = payload.get("order")
    if order in (None, ""):
        existing = [s["order"] for s in series_data(content_dir)["series"] if s.get("section") == section]
        order = (max(existing) + 10) if existing else 10
    folder.mkdir(parents=True)
    (folder / "series.yaml").write_text(
        HEADER + f"title: {yaml_scalar(title)}\nsection: {section}\norder: {int(order)}\ntone: {tone}\n"
        "layout: column\npublished: false\nstatement: ''\ncover: ''\nfeatured: []\nimages: []\n"
        "captions: {}\nfocal: {}\n", encoding="utf-8")
    content_lib.load_series(folder, include_unpublished=True)
    return {"created": slug}


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

    def body_of(handler):
        return handler.rfile.read(int(handler.headers.get("Content-Length", 0)))

    def json_route(fn):
        """Wrap an operation taking the parsed JSON body; errors become 400s."""
        def handle(handler):
            try:
                payload = json.loads(body_of(handler) or b"{}")
                result = fn(payload, handler)
            except (CurateError, content_lib.ContentError, KeyError, ValueError, OSError) as error:
                return send(handler, 400, json.dumps({"error": str(error)}), "application/json")
            send(handler, 200, json.dumps(result), "application/json")
        return handle

    def page(handler):
        send(handler, 200, PAGE.read_text(encoding="utf-8"), "text/html; charset=utf-8")

    def data(handler):
        send(handler, 200, json.dumps(series_data(content_dir)), "application/json")

    def upload_route(handler):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(handler.path).query)
        try:
            slug = query.get("slug", [""])[0]
            filename = urllib.parse.unquote(handler.headers.get("X-Filename", ""))
            result = upload(content_dir, slug, filename, body_of(handler))
        except (CurateError, content_lib.ContentError, OSError) as error:
            return send(handler, 400, json.dumps({"error": str(error)}), "application/json")
        send(handler, 200, json.dumps(result), "application/json")

    def image(handler):
        # /_curate/img/<slug>/<size>/<file>  or  /_curate/img/_holding/<size>/<group>/<file>
        parts = urllib.parse.unquote(handler.path.split("?")[0]).split("/")
        try:
            if ".." in parts:
                raise ValueError
            if parts[3] == "_holding":
                _, _, _, _, size, root, group, filename = parts
                source = holding_path(content_dir, f"{root}/{group}") / filename
            else:
                _, _, _, slug, size, filename = parts
                source = content_dir / "series" / slug / filename
            if size not in images.VARIANTS or not source.is_file():
                raise ValueError
        except (ValueError, CurateError):
            return handler.send_error(404)
        info = images.process(source, cache_dir)        # cached after the first request
        send(handler, 200, info.variants[size]["path"].read_bytes(), "image/jpeg")

    return {
        "/_curate/": page,
        "/_curate/data": data,
        "/_curate/save": json_route(lambda p, h: save_series(content_dir, p)),
        "/_curate/move": json_route(lambda p, h: move(content_dir, p["from"], p["file"], p["to"])),
        "/_curate/delete": json_route(lambda p, h: delete_held(content_dir, p["holding"], p["file"])),
        "/_curate/series": json_route(lambda p, h: create_series(content_dir, p)),
        "/_curate/upload": upload_route,
        "/_curate/img/": image,
    }
