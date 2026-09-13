"""Turn loaded content into HTML pages with Jinja2 templates.

The templates in templates/ never touch the filesystem or Pillow; they get
plain dicts and lists prepared here (the "view model"). Keeping that
preparation in Python makes the templates short and the logic testable.
"""

from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import images

# How wide a photo may be on the page, and how tall. These must match the CSS
# variables --content-width and --frame-max-height in static/css/site.css,
# because the `sizes` attribute tells the browser which srcset file to fetch
# before any CSS has been read.
CONTENT_WIDTH_PX = 1600
FRAME_MAX_VH = 88
GUTTER_PX = 16


class Renderer:
    def __init__(self, templates_dir, content, dist_dir):
        self.content = content
        self.site = content.site
        self.dist = Path(dist_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html"]),
            trim_blocks=True, lstrip_blocks=True,
        )
        # Values every template can use without being passed them explicitly.
        self.env.globals.update(site=self.site, sections=content.sections)

    # ----------------------------------------------------------------------
    # Writing pages
    # ----------------------------------------------------------------------

    def write(self, url, template, **context):
        """Render `template` to dist/<url>/index.html (or dist/<url> if it ends in .html)."""
        page = self.env.get_template(template).render(url=url, **context)
        if url.endswith(".html"):
            target = self.dist / url.lstrip("/")
        else:
            target = self.dist / url.strip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
        return target

    # ----------------------------------------------------------------------
    # View models
    # ----------------------------------------------------------------------

    def frame(self, series, filename, info, published, position):
        """Everything the template needs to place one photograph."""
        ratio = info.aspect_ratio
        variants = info.variants
        img_url = f"/img/{series.slug}/"
        srcset = ", ".join(f"{img_url}{published[name]} {variants[name]['width']}w"
                           for name in ("thumb", "medium", "large"))
        # The frame is as wide as the content column, unless that would make
        # it taller than FRAME_MAX_VH of the viewport. Mirrors the CSS rule.
        sizes = (f"min(calc(100vw - {2 * GUTTER_PX}px), {CONTENT_WIDTH_PX}px, "
                 f"calc({FRAME_MAX_VH}vh * {ratio:.4f}))")
        return {
            "filename": filename,
            "src": img_url + published["medium"],
            "srcset": srcset,
            "sizes": sizes,
            "large": img_url + published["large"],
            "large_width": variants["large"]["width"],
            "large_height": variants["large"]["height"],
            "width": info.width,
            "height": info.height,
            "ratio": f"{ratio:.4f}",
            "color": info.average_color,
            "caption": series.captions.get(filename, ""),
            "alt": series.captions.get(filename) or f"{series.title}, photograph {position}",
            # The first frames are visible on load: fetch them eagerly.
            "eager": position <= 2,
        }

    def cover(self, series, info, published):
        """A series cover as shown on index pages."""
        return {
            "title": series.title,
            "url": series.url,
            "tone": series.tone,
            "src": f"/img/{series.slug}/{published['medium']}",
            "srcset": ", ".join(f"/img/{series.slug}/{published[n]} {info.variants[n]['width']}w"
                                for n in ("thumb", "medium")),
            "width": info.width,
            "height": info.height,
            "ratio": f"{info.aspect_ratio:.4f}",
            "color": info.average_color,
            "count": len(series.images),
        }


def cover_rows(covers, target_height=0.36, gap=0.02):
    """Arrange covers into justified rows of equal image height.

    All sizes are fractions of the container width, so the layout scales
    with the viewport. Covers are added to a row until, at `target_height`,
    they would fill the width; the row's height is then solved so the covers
    plus gaps fill it exactly. Panoramas therefore share a row with fewer
    neighbours than portraits do, and nothing ends up as a sliver. A trailing
    partial row keeps the target height (or the previous row's, if lower)
    rather than stretching to fill the width.
    """
    rows, row, previous_height = [], [], target_height

    def solved(items, height=None):
        ratios = [float(c["ratio"]) for c in items]
        if height is None:
            height = (1 - gap * (len(items) - 1)) / sum(ratios)
        return height, [{**c, "width_pct": f"{height * r * 100:.3f}"} for c, r in zip(items, ratios)]

    for cover in covers:
        row.append(cover)
        width_at_target = sum(float(c["ratio"]) for c in row) * target_height + gap * (len(row) - 1)
        if width_at_target >= 1:
            previous_height, items = solved(row)
            rows.append(items)
            row = []
    if row:
        rows.append(solved(row, height=min(target_height, previous_height))[1])
    return rows


def markdown_to_html(text):
    return markdown.markdown(text, extensions=["smarty"])
