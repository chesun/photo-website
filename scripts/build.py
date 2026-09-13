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

    # 1. Photographs: resize (cached) and copy into dist/img/<series>/.
    processed = 0
    covers = {}                       # section slug -> [cover view models]
    for series in site_content.series:
        frames = []
        for position, filename in enumerate(series.images, start=1):
            info = images.process(series.image_path(filename), CACHE)
            published = images.publish(info, DIST / "img" / series.slug, Path(filename).stem)
            frames.append(renderer.frame(series, filename, info, published, position))
            if filename == series.cover:
                covers.setdefault(series.section, []).append(renderer.cover(series, info, published))
            processed += 1
        # 2. One page per series.
        if series.layout == "grid":
            content_lib.warn(f"{series.slug}: layout 'grid' is not built yet (phase 2); rendering as column")
        renderer.write(series.url, "series.html", series=series, frames=frames)

    # 3. Section index pages.
    for item in site_content.site.nav:
        slug = item["slug"]
        if slug == "about":
            continue
        # Archive covers are small (about a fifth of the width tall); the
        # three main sections get large ones (about a third).
        if slug == "archive":
            rows = render.cover_rows(covers.get(slug, []), target_height=0.2, gap=0.015)
        else:
            rows = render.cover_rows(covers.get(slug, []), target_height=0.36, gap=0.02)
        renderer.write(f"/{slug}/", "section.html", section=slug,
                       label=item["label"], rows=rows)

    # 4. About, landing.
    portrait = images.process(site_content.about.portrait, CACHE)
    portrait_files = images.publish(portrait, DIST / "img" / "about", "portrait")
    renderer.write("/about/", "about.html",
                   body=render.markdown_to_html(site_content.about.markdown),
                   portrait={"src": "/img/about/" + portrait_files["medium"],
                             "width": portrait.width, "height": portrait.height,
                             "color": portrait.average_color})
    renderer.write("/", "landing.html", covers=covers)

    # 5. Static assets (CSS, JS, fonts, PhotoSwipe).
    shutil.copytree(STATIC, DIST / "static", dirs_exist_ok=True)

    elapsed = time.perf_counter() - started
    print(f"Built {len(site_content.series)} series, {processed} photographs "
          f"in {elapsed:.1f}s -> {DIST.relative_to(REPO)}/")
    return site_content


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
        sys.exit(f"error: {error}")

    if args.serve:
        from photosite import serve
        serve.serve(rebuild=build, dist=DIST, watch=[CONTENT, TEMPLATES, STATIC], port=args.port,
                    restart_on=[REPO / "scripts"])


if __name__ == "__main__":
    main()
