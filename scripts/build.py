#!/usr/bin/env python3
"""Build the site into dist/.

    python scripts/build.py            build once
    python scripts/build.py --serve    build, serve locally, rebuild on change
    python scripts/build.py --clean    delete dist/ and the image cache first

Reading order for the code: this file first (it is the outline), then
photosite/content.py (what the content looks like), photosite/images.py
(what happens to each photo), photosite/render.py (how pages are written).
"""

import argparse
import datetime
import shutil
import sys
import time
from pathlib import Path

# Let `import photosite` work when this file is run as a script from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from photosite import content as content_lib, images, render  # noqa: E402
from photosite.content import ContentError  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
CONTENT = REPO / "content"
TEMPLATES = REPO / "templates"
STATIC = REPO / "static"
DIST = REPO / "dist"
CACHE = REPO / ".cache" / "images"


def build():
    """One full build. Returns the loaded content (the dev server reuses it)."""
    started = time.perf_counter()
    site_content = content_lib.load_content(CONTENT)
    DIST.mkdir(parents=True, exist_ok=True)
    renderer = render.Renderer(TEMPLATES, site_content, DIST)

    pages = []                        # (url, lastmod) for the sitemap

    # 1. Photographs: resize (cached) and copy into dist/img/<series>/.
    processed = 0
    covers = {}                       # section slug -> [cover view models]
    slides = []                       # landing slideshow, in section order
    for series in site_content.series:
        frames = []
        og_image = None
        for position, filename in enumerate(series.images, start=1):
            info = images.process(series.image_path(filename), CACHE)
            published = images.publish(info, DIST / "img" / series.slug, Path(filename).stem)
            frames.append(renderer.frame(series, filename, info, published, position))
            if filename == series.cover:
                covers.setdefault(series.section, []).append(renderer.cover(series, info, published))
                og_image = "/img/" + series.slug + "/" + published["medium"]
            if filename in series.featured:
                slides.append(renderer.slide(series, filename, info, published))
            processed += 1
        # 2. One page per series. Grid layout gets justified rows solved here;
        #    column layout needs nothing more than the frames in order.
        rows = render.justified_rows(frames, target_height=0.24, gap=0.005) if series.layout == "grid" else None
        renderer.write(series.url, "series.html", series=series, frames=frames, rows=rows, og_image=og_image)
        pages.append((series.url, latest_change(series.folder)))

    # 3. Section index pages.
    for item in site_content.site.nav:
        slug = item["slug"]
        if slug == "about":
            continue
        section_covers = covers.get(slug, [])
        # Archive covers are small (about a fifth of the width tall); the
        # three main sections get large ones (about a third).
        if slug == "archive":
            rows = render.cover_rows(section_covers, target_height=0.2, gap=0.015)
        else:
            rows = render.cover_rows(section_covers, target_height=0.36, gap=0.02)
        renderer.write(f"/{slug}/", "section.html", section=slug, label=item["label"], rows=rows,
                       og_image=section_covers[0]["src"] if section_covers else None)
        pages.append((f"/{slug}/", today()))

    # 4. About, landing, 404.
    portrait = images.process(site_content.about.portrait, CACHE)
    portrait_files = images.publish(portrait, DIST / "img" / "about", "portrait")
    renderer.write("/about/", "about.html",
                   body=render.markdown_to_html(site_content.about.markdown),
                   portrait={"src": "/img/about/" + portrait_files["medium"],
                             "width": portrait.width, "height": portrait.height,
                             "color": portrait.average_color},
                   og_image="/img/about/" + portrait_files["medium"])
    pages.append(("/about/", latest_change(CONTENT / "about")))
    if not slides:
        content_lib.warn("no series has `featured` images; the landing slideshow will be empty")
    renderer.write("/", "landing.html", slides=slides, og_image=slides[0]["src"] if slides else None)
    pages.insert(0, ("/", today()))
    renderer.write("/404.html", "404.html", og_image=slides[0]["src"] if slides else None)

    # 5. Static assets (CSS, JS, fonts, PhotoSwipe), favicon at the root,
    #    sitemap and robots.txt.
    shutil.copytree(STATIC, DIST / "static", dirs_exist_ok=True)
    shutil.copyfile(STATIC / "favicon.ico", DIST / "favicon.ico")
    write_sitemap(site_content.site.base_url, pages)
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {site_content.site.base_url}/sitemap.xml\n")

    elapsed = time.perf_counter() - started
    print(f"Built {len(site_content.series)} series, {processed} photographs "
          f"in {elapsed:.1f}s -> {DIST.relative_to(REPO)}/")
    return site_content


def today():
    return datetime.date.today().isoformat()


def latest_change(folder):
    """The date of the most recently modified file in a folder, for the sitemap."""
    newest = max(p.stat().st_mtime for p in Path(folder).iterdir() if p.is_file())
    return datetime.date.fromtimestamp(newest).isoformat()


def write_sitemap(base_url, pages):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, lastmod in pages:
        lines.append(f"  <url><loc>{base_url}{url}</loc><lastmod>{lastmod}</lastmod></url>")
    lines.append("</urlset>")
    (DIST / "sitemap.xml").write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--serve", action="store_true", help="serve dist/ locally and rebuild on change")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--clean", action="store_true", help="delete dist/ and the image cache before building")
    args = parser.parse_args()

    if args.clean:
        shutil.rmtree(DIST, ignore_errors=True)
        shutil.rmtree(CACHE, ignore_errors=True)
        print("Removed dist/ and .cache/")

    try:
        build()
    except ContentError as error:
        if not args.serve:
            sys.exit(f"error: {error}")
        print(f"error: {error}\nFix it and save; the server will rebuild.", file=sys.stderr)
    except Exception:
        # While serving, a broken template or script should not take the
        # server down; keep serving the last good build and wait for a fix.
        if not args.serve:
            raise
        import traceback
        traceback.print_exc()

    if args.serve:
        from photosite import curate, serve
        serve.serve(rebuild=build, dist=DIST, watch=[CONTENT, TEMPLATES, STATIC], port=args.port,
                    restart_on=[REPO / "scripts"],
                    extra_routes=curate.routes(content_dir=CONTENT, cache_dir=CACHE))


if __name__ == "__main__":
    main()
