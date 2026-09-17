#!/usr/bin/env python3
"""Import the galleries from the live Squarespace site into content/series/.

Run once, from the repo root, before the Squarespace subscription is cancelled:

    .venv/bin/python scripts/migrate_squarespace.py

For every gallery listed in MAPPING it:

  1. fetches the gallery page and reads its slides in page order
     (the order you arranged on Squarespace is the order that ends up in
     series.yaml);
  2. downloads each image from its bare CDN URL, which returns the stored
     upload at full resolution (checked 2026-09-13: 2500px long edge);
  3. measures how colourful the images are to set the series `tone`;
  4. writes content/series/<slug>/series.yaml.

It also seeds content/about/about.md and portrait.jpg from the About page,
and marks as `featured` every image that is in the current landing slideshow.

It never overwrites a file that already exists, so it is safe to re-run after
a partial download. Delete a series folder to re-import it from scratch.

Only the standard library plus Pillow and PyYAML are used. Everything the
script knows about the Squarespace markup is in the two parse_* functions.
"""

import html
import re
import statistics
import sys
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

import yaml
from PIL import Image, ImageOps, ImageStat

SITE = "https://christinasunphoto.com"
REPO = Path(__file__).resolve().parent.parent
CONTENT = REPO / "content"
USER_AGENT = "Mozilla/5.0 (Macintosh) photo-website migration script"

# Source slug on Squarespace -> where it lands here. `order` positions the series
# within its section index (lower first). `skip` drops individual files.
# `keep_statement` is False where the old meta description should not be reused.
# `tone` is measured from the images unless given here explicitly.
MAPPING = {
    # Landscape
    "landscape-color": dict(
        slug="alpenglow", title="Alpenglow", section="landscape", order=10,
        skip=["000033810003-Edit.jpg"], keep_statement=False),
    "landscape-monochrome": dict(
        slug="storm-light", title="Storm Light", section="landscape", order=20,
        keep_statement=False),
    "sand-and-stone": dict(
        slug="sand-and-stone", title="Sand and Stone", section="landscape", order=30),
    "from-the-mountains-to-the-sea": dict(
        slug="the-mountains-are-calling", title="The Mountains are Calling",
        section="landscape", order=40),
    # People
    "from-the-earth-to-the-stars": dict(
        slug="from-the-earth-to-the-stars", title="From the Earth to the Stars",
        section="people", order=10),
    "instant-of-forever": dict(
        slug="an-instant-of-forever", title="An Instant of Forever",
        section="people", order=20),
    "love-on-the-coast": dict(
        slug="love-on-the-coast", title="Love on the Coast", section="people", order=30),
    "tide-and-timber": dict(
        slug="tide-and-timber", title="Tide and Timber", section="people", order=40),
    "graduations": dict(
        slug="graduations", title="Graduations", section="people", order=50),
    # Interludes
    "quiet-days": dict(
        slug="quiet-days", title="Quiet Days", section="interludes", order=10),
    # Archive
    "meditation-on-solitude": dict(
        slug="meditation-on-solitude", title="Meditation on Solitude",
        section="archive", order=10),
    "nightfall": dict(slug="nightfall", title="Nightfall", section="archive", order=20),
    "outskirts": dict(slug="outskirts", title="Outskirts", section="archive", order=30),
    "panoramic-streets-monochrome": dict(
        slug="panoramic-streets-monochrome", title="Panoramic Streets: Monochrome",
        section="archive", order=40),
    "panoramic-streets-color": dict(
        slug="panoramic-streets-color", title="Panoramic Streets: Color",
        section="archive", order=50),
    "new-gallery-1": dict(
        slug="streets-of-sacramento", title="Streets of Sacramento",
        section="archive", order=60),
    "uc-davis-symphony-orchestra": dict(
        slug="uc-davis-symphony-orchestra", title="UC Davis Symphony Orchestra",
        section="archive", order=70),
    "sanfrancisco": dict(
        slug="the-city-by-the-sea", title="The City by the Sea",
        section="archive", order=80),
    "animal-companions": dict(
        slug="animal-companions", title="Animal Companions", section="archive", order=90),
    # Orphaned on the old site: keep the files, build nothing (see TODO.md)
    "streets-of-davis": dict(
        slug="streets-of-davis", title="Streets of Davis", section="archive",
        order=100, published=False),
    "life-and-adventure": dict(
        slug="life-and-adventure", title="Life and Adventure", section="archive",
        order=110, published=False),
    "adventure": dict(
        slug="adventure", title="Adventure", section="archive", order=120,
        published=False),
}

# Below this mean HSV saturation (0-255 scale) an image counts as monochrome.
# Film scans of black-and-white negatives come in around 5-15; colour work
# is usually above 40.
MONOCHROME_THRESHOLD = 20


# --------------------------------------------------------------------------
# Fetching
# --------------------------------------------------------------------------

def fetch(url):
    """Return the body of a URL as bytes. Squarespace blocks the default
    urllib user agent, so we send a browser-like one."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def fetch_text(url):
    return fetch(url).decode("utf-8", errors="replace")


# --------------------------------------------------------------------------
# Parsing the Squarespace markup
# --------------------------------------------------------------------------

def parse_gallery(page_html):
    """Return the slides of a Squarespace 7.0 gallery page, in display order.

    Each slide is a dict with `url`, `alt`, `width`, `height`. The Pacific
    template renders the slides twice (a "stacked" block and a "strip"
    block); we read only the first block and de-duplicate by URL to be safe.
    """
    match = re.search(r'<div class="slideshow stacked">(.*?)<div class="slideshow strip',
                      page_html, re.S)
    block = match.group(1) if match else page_html
    slides = []
    seen = set()
    for img in re.finditer(r"<img\s[^>]*data-src=\"([^\"]+)\"[^>]*>", block):
        tag = img.group(0)
        url = img.group(1)
        if url in seen:
            continue
        seen.add(url)
        alt = re.search(r'alt="([^"]*)"', tag)
        dims = re.search(r'data-image-dimensions="(\d+)x(\d+)"', tag)
        slides.append(dict(
            url=url,
            alt=html.unescape(alt.group(1)).strip() if alt else "",
            width=int(dims.group(1)) if dims else None,
            height=int(dims.group(2)) if dims else None,
        ))
    return slides


def parse_meta_description(page_html):
    match = re.search(r'<meta name="description" content="([^"]*)"', page_html)
    if not match:
        return ""
    text = match.group(1)
    while html.unescape(text) != text:      # Squarespace escapes some descriptions twice
        text = html.unescape(text)
    return " ".join(text.replace("\xa0", " ").split())


def parse_about(page_html):
    """Turn the About page's text blocks into Markdown.

    Squarespace wraps every text block in <div class="sqs-html-content">.
    We keep the blocks that are about the photographer and drop the two
    form headings and the Squarespace footer. Links are preserved.
    """
    blocks = re.findall(r'<div class="sqs-html-content"[^>]*>(.*?)</div>', page_html, re.S)
    quotes = re.findall(r"<blockquote[^>]*>(.*?)</blockquote>\s*(?:<figcaption[^>]*>(.*?)</figcaption>)?",
                        page_html, re.S)
    drop = ("General Inquiries", "Newsletter Signup", "Powered by")
    parts = []
    for block in blocks:
        if any(word in block for word in drop):
            continue
        parts.append(html_to_markdown(block))
    for quote, source in quotes:
        text = html_to_markdown(quote).strip()
        parts.append(f"> {text}\n>\n> {html_to_markdown(source).strip()}")
    return "\n\n".join(part for part in parts if part.strip()) + "\n"


def html_to_markdown(fragment):
    """A tiny HTML-to-Markdown converter covering the tags the About page uses:
    headings, paragraphs, line breaks, links, emphasis."""
    text = fragment
    text = re.sub(r"<h[1-3][^>]*>(.*?)</h[1-3]>", r"\n\n## \1\n\n", text, flags=re.S)
    text = re.sub(r"<a [^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", r"[\2](\1)", text, flags=re.S)
    text = re.sub(r"<(strong|b)>(.*?)</\1>", r"**\2**", text, flags=re.S)
    text = re.sub(r"<(em|i)>(.*?)</\1>", r"*\2*", text, flags=re.S)
    text = re.sub(r"<br\s*/?>", "  \n", text)
    text = re.sub(r"</p>", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text).replace("\xa0", " ")
    # collapse runs of blank lines and trailing spaces on each line
    lines = [line.rstrip() if not line.endswith("  ") else line for line in text.splitlines()]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_image_urls(page_html):
    """Every CDN image URL on a page, first occurrence first. Used on the
    landing page to learn which images are in the current slideshow."""
    urls = []
    for url in re.findall(r"https://images\.squarespace-cdn\.com/content/v1/[^\"'\s?]+", page_html):
        url = html.unescape(url)
        if url not in urls:
            urls.append(url)
    return urls


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def filename_from_url(url):
    """Squarespace keeps the uploaded filename as the last path segment, with
    spaces encoded as '+'. We keep the name but replace spaces with dashes so
    it is safe in URLs and shells."""
    name = urllib.parse.unquote(url.rsplit("/", 1)[-1]).replace("+", " ")
    name = re.sub(r"\s+", "-", name.strip())
    return name


def mean_saturation(image_bytes):
    """Mean saturation (0-255) of a small copy of the image."""
    image = ImageOps.exif_transpose(Image.open(BytesIO(image_bytes)))
    image.thumbnail((200, 200))
    saturation = image.convert("RGB").convert("HSV").split()[1]
    return ImageStat.Stat(saturation).mean[0]


def looks_like_filename(alt, name):
    """True when the alt text is just the filename in some spelling.

    Squarespace fills alt with the upload name unless you type a title, so
    'Trillium Lake Milky Way Pano v2 Orton-Web.jpg' is a filename while
    'Impending Storm' is a title. Compare with punctuation and extension removed.
    """
    def squash(text):
        stem = re.sub(r"-\d+$", "", Path(text).stem)   # ignore a -2 collision suffix
        return re.sub(r"[^a-z0-9]", "", stem.lower())
    return squash(alt) == squash(name)


def write_yaml(path, data):
    """Write a dict as YAML in insertion order, with a short header comment."""
    header = ("# Series metadata. `images` is the display order; edit it here or\n"
              "# with the curate page (python scripts/build.py --serve, then /_curate/).\n")
    body = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=88)
    path.write_text(header + body, encoding="utf-8")


# --------------------------------------------------------------------------
# Main steps
# --------------------------------------------------------------------------

def migrate_series(source_slug, spec, featured_names):
    folder = CONTENT / "series" / spec["slug"]
    yaml_path = folder / "series.yaml"
    if yaml_path.exists():
        print(f"  {spec['slug']}: series.yaml exists, skipping")
        return
    folder.mkdir(parents=True, exist_ok=True)

    page = fetch_text(f"{SITE}/{source_slug}")
    slides = parse_gallery(page)
    if not slides:
        sys.exit(f"No slides found on /{source_slug}; the markup may have changed.")

    images, captions, saturations = [], {}, []
    for slide in slides:
        name = filename_from_url(slide["url"])
        if name in spec.get("skip", []):
            print(f"    skip {name}")
            continue
        target = folder / name
        if name in images:
            # Same filename twice in one gallery. Either the same photo was
            # uploaded twice (skip it) or two different photos share a name
            # (keep both, suffixing the second one -2, -3, ...).
            data = fetch(slide["url"])
            if target.read_bytes() == data:
                print(f"    {name}: identical duplicate, skipped")
                continue
            stem, suffix = Path(name).stem, Path(name).suffix
            n = 2
            while True:
                target = folder / f"{stem}-{n}{suffix}"
                if target.name in images or (target.exists() and target.read_bytes() != data):
                    n += 1
                    continue
                break
            name = target.name
            if not target.exists():
                target.write_bytes(data)
        elif target.exists():
            data = target.read_bytes()
        else:
            data = fetch(slide["url"])
            target.write_bytes(data)
        images.append(name)
        saturations.append(mean_saturation(data))
        # Alt text that is not just the filename is a real title: keep it.
        alt = slide["alt"]
        if alt and not looks_like_filename(alt, name):
            captions[name] = alt
        print(f"    {name}  {len(data) // 1024} KB")

    tone = spec.get("tone")
    if tone is None:
        tone = "monochrome" if statistics.median(saturations) < MONOCHROME_THRESHOLD else "color"
    statement = parse_meta_description(page) if spec.get("keep_statement", True) else ""
    featured = [name for name in images if name in featured_names]

    data = {
        "title": spec["title"],
        "section": spec["section"],
        "order": spec["order"],
        "tone": tone,
        "layout": "column",
        "published": spec.get("published", True),
        "statement": statement,
        "cover": images[0],
        "featured": featured,
        "images": images,
        "captions": captions,
    }
    write_yaml(yaml_path, data)
    print(f"  {spec['slug']}: {len(images)} images, tone={tone} "
          f"(median saturation {statistics.median(saturations):.0f}), "
          f"{len(featured)} featured, {len(captions)} captions")


def migrate_about():
    folder = CONTENT / "about"
    folder.mkdir(parents=True, exist_ok=True)
    md_path = folder / "about.md"
    portrait_path = folder / "portrait.jpg"
    page = fetch_text(f"{SITE}/about")
    if md_path.exists():
        print("  about.md exists, skipping")
    else:
        md_path.write_text(parse_about(page), encoding="utf-8")
        print("  wrote about.md")
    if portrait_path.exists():
        print("  portrait.jpg exists, skipping")
    else:
        urls = parse_image_urls(page)
        portraits = [u for u in urls if "favicon" not in u]
        if not portraits:
            sys.exit("No portrait image found on /about")
        portrait_path.write_bytes(fetch(portraits[0]))
        print(f"  wrote portrait.jpg from {filename_from_url(portraits[0])}")


def main():
    print("Reading the landing slideshow for featured images...")
    landing = parse_image_urls(fetch_text(SITE + "/"))
    featured_names = {filename_from_url(u) for u in landing if "favicon" not in u}
    print(f"  {len(featured_names)} images in the current slideshow")

    print("Migrating series...")
    for source_slug, spec in MAPPING.items():
        print(f"/{source_slug} -> {spec['slug']}")
        migrate_series(source_slug, spec, featured_names)

    print("Migrating the About page...")
    migrate_about()
    print("Done.")


if __name__ == "__main__":
    main()
