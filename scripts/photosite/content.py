"""Load and validate everything under content/.

The content folder is the source of truth for the site:

    content/site.yaml            global settings (title, nav, links)
    content/series/<slug>/       one folder per series
        series.yaml              metadata and the image order
        *.jpg                    the photographs
    content/about/about.md       the About page text, in Markdown
    content/about/portrait.jpg

This module reads all of that into plain Python objects and checks it. Every
check that fails raises ContentError with a message that names the file and
the problem, so a typo in YAML shows up as one clear line, not a traceback
deep inside the build.
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

SECTIONS = ("landscape", "people", "interludes", "archive")
TONES = ("color", "monochrome")
LAYOUTS = ("column", "grid")
IMAGE_SUFFIXES = (".jpg", ".jpeg")

# Every key a series.yaml may contain, and the ones it must contain.
SERIES_KEYS = {"title", "section", "order", "tone", "layout", "published",
               "statement", "cover", "featured", "images", "captions", "focal"}
SERIES_REQUIRED = {"title", "section", "order", "tone", "cover", "images"}

SITE_KEYS = {"title", "tagline", "description", "nav", "instagram", "email",
             "base_url", "formspree_action"}


class ContentError(Exception):
    """Raised for any problem in content/ that should stop the build."""


def warn(message):
    """Print a warning to stderr. Warnings do not stop the build."""
    print(f"warning: {message}", file=sys.stderr)


@dataclass
class Series:
    slug: str
    folder: Path
    title: str
    section: str
    order: int
    tone: str
    layout: str
    published: bool
    statement: str
    cover: str
    featured: list
    images: list
    captions: dict
    focal: dict         # filename -> CSS object-position, e.g. "50% 30%"

    @property
    def url(self):
        """Site-relative URL of the series page, e.g. /landscape/sand-and-stone/."""
        return f"/{self.section}/{self.slug}/"

    def image_path(self, filename):
        return self.folder / filename


@dataclass
class Site:
    title: str
    tagline: str
    description: str
    nav: list           # list of {"slug": ..., "label": ...}
    instagram: str
    email: str
    base_url: str
    formspree_action: str

    def section_label(self, slug):
        for item in self.nav:
            if item["slug"] == slug:
                return item["label"]
        return slug.title()


@dataclass
class About:
    markdown: str
    portrait: Path


@dataclass
class Content:
    site: Site
    series: list                       # every published series, sorted
    about: About
    sections: dict = field(default_factory=dict)   # section slug -> [Series]


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

def read_yaml(path):
    """Read a YAML file into a dict, with a helpful error on bad syntax."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ContentError(f"{path}: invalid YAML\n{error}") from None
    if not isinstance(data, dict):
        raise ContentError(f"{path}: expected a mapping of keys to values")
    return data


def check_keys(path, data, allowed, required):
    """Reject unknown keys (they are almost always typos) and missing ones."""
    unknown = set(data) - allowed
    if unknown:
        raise ContentError(f"{path}: unknown key(s) {sorted(unknown)}; "
                           f"allowed keys are {sorted(allowed)}")
    missing = required - set(data)
    if missing:
        raise ContentError(f"{path}: missing required key(s) {sorted(missing)}")


def load_site(path):
    data = read_yaml(path)
    check_keys(path, data, SITE_KEYS, SITE_KEYS)
    for item in data["nav"]:
        if set(item) != {"slug", "label"}:
            raise ContentError(f"{path}: each nav item needs exactly `slug` and `label`")
    return Site(**data)


def load_series(folder, include_unpublished=False, strict=False, leaving=()):
    """Load one series folder. Returns None for an unpublished series unless
    `include_unpublished` is set (the curate page edits those too). With
    `strict`, files on disk that are not listed in `images` are an error
    instead of being appended; the curate page uses that to check what it
    just wrote, naming in `leaving` any file it is about to move out."""
    path = folder / "series.yaml"
    if not path.exists():
        raise ContentError(f"{folder}: no series.yaml")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", folder.name):
        raise ContentError(f"{folder}: folder names must be lowercase letters, digits and dashes (they become URLs)")
    data = read_yaml(path)
    check_keys(path, data, SERIES_KEYS, SERIES_REQUIRED)
    if not isinstance(data["title"], str) or not data["title"].strip():
        raise ContentError(f"{path}: title must be text")

    # Fill in defaults for the optional keys.
    data.setdefault("layout", "column")
    data.setdefault("published", True)
    data.setdefault("statement", "")
    data.setdefault("featured", [])
    data.setdefault("captions", {})
    data.setdefault("focal", {})
    data["statement"] = (data["statement"] or "").strip()
    data["featured"] = data["featured"] or []
    data["captions"] = data["captions"] or {}
    data["focal"] = data["focal"] or {}

    if data["section"] not in SECTIONS:
        raise ContentError(f"{path}: section must be one of {SECTIONS}, not {data['section']!r}")
    if data["tone"] not in TONES:
        raise ContentError(f"{path}: tone must be one of {TONES}, not {data['tone']!r}")
    if data["layout"] not in LAYOUTS:
        raise ContentError(f"{path}: layout must be one of {LAYOUTS}, not {data['layout']!r}")
    if not isinstance(data["order"], int) or isinstance(data["order"], bool):
        raise ContentError(f"{path}: order must be a whole number")
    if not isinstance(data["published"], bool):
        raise ContentError(f"{path}: published must be true or false")
    if not data["published"] and not include_unpublished:
        return None

    # The files actually in the folder.
    files = sorted(p.name for p in folder.iterdir()
                   if p.is_file() and not p.name.startswith("."))
    stray = [f for f in files if f != "series.yaml" and Path(f).suffix.lower() not in IMAGE_SUFFIXES]
    if stray:
        raise ContentError(f"{folder}: non-image file(s) {stray}; only JPEGs and series.yaml belong here")
    on_disk = [f for f in files if f != "series.yaml"]

    # Every listed image must exist. Every image on disk should be listed;
    # if not, append it so a fresh export is visible without editing YAML.
    images = list(data["images"] or [])
    duplicates = sorted({f for f in images if images.count(f) > 1})
    if duplicates:
        raise ContentError(f"{path}: image(s) listed more than once: {duplicates}")
    missing = [f for f in images if f not in on_disk]
    if missing:
        raise ContentError(f"{path}: listed image(s) not found in folder: {missing}")
    unlisted = [f for f in on_disk if f not in images and f not in leaving]
    if unlisted and strict:
        raise ContentError(f"{path}: image(s) in the folder but not in `images`: {unlisted}")
    if unlisted:
        warn(f"{path}: {len(unlisted)} image(s) not in `images`, appended at the end: {unlisted}")
        images.extend(unlisted)
    if not images and data["published"]:
        raise ContentError(f"{folder}: a published series needs at least one image")

    # A series created from the curate page starts empty and unpublished, with
    # no cover yet. Once it has images, a missing cover means the first one.
    if not data["cover"] and images:
        data["cover"] = images[0]
    references = list(data["featured"]) + list(data["captions"]) + list(data["focal"])
    if data["cover"]:
        references.insert(0, data["cover"])
    for name in references:
        if name not in images:
            raise ContentError(f"{path}: {name!r} is referenced but not in `images`")
    # A focal point is where the frame is anchored when it must be cropped
    # (the landing slideshow): "x% y%" from the top-left, so "50% 30%" keeps
    # the upper part of a tall photo. Any CSS object-position value works.
    for name, value in data["focal"].items():
        if not isinstance(value, str) or not value.strip():
            raise ContentError(f"{path}: focal point for {name!r} must be text like \"50% 30%\"")

    return Series(
        slug=folder.name, folder=folder, title=str(data["title"]),
        section=data["section"], order=data["order"], tone=data["tone"],
        layout=data["layout"], published=data["published"], statement=data["statement"],
        cover=data["cover"] or "", featured=list(data["featured"]), images=images,
        captions={k: str(v) for k, v in data["captions"].items()},
        focal={k: v.strip() for k, v in data["focal"].items()},
    )


def load_about(folder):
    md = folder / "about.md"
    portrait = folder / "portrait.jpg"
    if not md.exists():
        raise ContentError(f"{md}: missing")
    if not portrait.exists():
        raise ContentError(f"{portrait}: missing")
    return About(markdown=md.read_text(encoding="utf-8"), portrait=portrait)


def load_content(content_dir):
    """Load the whole content tree. This is the one function build.py calls."""
    content_dir = Path(content_dir)
    site = load_site(content_dir / "site.yaml")

    series_root = content_dir / "series"
    if not series_root.is_dir():
        raise ContentError(f"{series_root}: missing")
    all_series = []
    for folder in sorted(p for p in series_root.iterdir() if p.is_dir()):
        series = load_series(folder)
        if series is not None:
            all_series.append(series)
    all_series.sort(key=lambda s: (SECTIONS.index(s.section), s.order, s.title))

    sections = {slug: [] for slug in SECTIONS}
    for series in all_series:
        sections[series.section].append(series)

    about = load_about(content_dir / "about")
    return Content(site=site, series=all_series, about=about, sections=sections)
