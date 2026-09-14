#!/usr/bin/env python3
"""Generate the site's favicons into static/.

The mark is a plain near-black disc on the site's off-white: a sun, for
Sun. It is drawn once here, not on every build, and the results are
committed. Run from the repo root:

    .venv/bin/python scripts/make_favicons.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

STATIC = Path(__file__).resolve().parent.parent / "static"
BG = (0xFB, 0xFB, 0xF9)
INK = (0x1A, 0x1A, 0x1A)


def disc(size, background=BG):
    """A disc filling ~64% of the canvas, drawn 8x large and downsampled
    so the edge is smooth."""
    scale = 8
    big = size * scale
    image = Image.new("RGBA", (big, big), background + (255,))
    draw = ImageDraw.Draw(image)
    r = big * 0.32
    c = big / 2
    draw.ellipse((c - r, c - r, c + r, c + r), fill=INK + (255,))
    return image.resize((size, size), Image.Resampling.LANCZOS)


def main():
    # SVG: crisp at every size, preferred by modern browsers.
    (STATIC / "favicon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<rect width="64" height="64" fill="#fbfbf9"/>'
        '<circle cx="32" cy="32" r="20.5" fill="#1a1a1a"/></svg>\n')
    # ICO for older browsers and some tools; holds 16, 32 and 48px.
    disc(48).save(STATIC / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    # Apple touch icon: iOS rounds the corners itself.
    disc(180).convert("RGB").save(STATIC / "apple-touch-icon.png")
    for name in ("favicon.svg", "favicon.ico", "apple-touch-icon.png"):
        print(f"wrote static/{name}  {(STATIC / name).stat().st_size} bytes")


if __name__ == "__main__":
    main()
