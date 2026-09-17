"""Resize photographs, strip their metadata, and cache the results.

For every source JPEG the site needs three sizes (see VARIANTS) plus two
facts the templates bake into the HTML: the pixel dimensions, so every image
gets an exact aspect-ratio box and the page never shifts while loading, and
the average colour, so the box is painted in a matching tone before the
photo fades in.

All of that is expensive to compute and never changes unless the file does,
so results are cached under .cache/images/<hash>/ where <hash> is the SHA-256
of the file's bytes. A rebuild with no new photos reads a few small JSON
files and copies the cached JPEGs into dist/; it does not open a single
source image.
"""

import hashlib
import io
import json
import os
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageCms, ImageOps, ImageStat

# Variant name -> long-edge size in pixels. Phones at 3x pick `small`,
# 1x desktops `medium`, retina desktops `large`; the largest file is saved
# at a slightly lower quality because it is also the heaviest.
VARIANTS = {"thumb": 480, "small": 1000, "medium": 1600, "large": 2400}
JPEG_QUALITY = {"thumb": 82, "small": 82, "medium": 82, "large": 78}

# Anything that changes the output is part of the cache key, so editing the
# settings above reprocesses every image on the next build.
SETTINGS_KEY = hashlib.sha256(json.dumps([VARIANTS, JPEG_QUALITY], sort_keys=True).encode()).hexdigest()[:8]

# Pillow's default limit guards against decompression bombs. Scans of medium
# format film can exceed it, so raise it to something still sane.
Image.MAX_IMAGE_PIXELS = 400_000_000


@dataclass
class ImageInfo:
    hash: str
    width: int              # of the source, after rotation is applied
    height: int
    average_color: str      # CSS hex, e.g. "#8a7f70"
    variants: dict          # name -> {"width": w, "height": h, "path": cached file}

    @property
    def aspect_ratio(self):
        return self.width / self.height


def file_hash(path):
    """SHA-256 of a file's bytes, shortened to 16 hex characters."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()[:16]


def to_srgb(image):
    """Convert an image to sRGB if it carries a different colour profile.

    Browsers assume sRGB when no profile is embedded, so converting once
    here lets us drop the profile (and every other bit of metadata) from
    the output while keeping the colours right.
    """
    icc = image.info.get("icc_profile")
    if icc:
        try:
            source = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            target = ImageCms.createProfile("sRGB")
            return ImageCms.profileToProfile(image, source, target, outputMode="RGB")
        except ImageCms.PyCMSError:
            pass  # unreadable profile: fall through and treat as sRGB
    return image.convert("RGB")


def average_color(image):
    """The mean colour of the image as a CSS hex string."""
    small = image.resize((32, 32), Image.Resampling.BOX)
    r, g, b = (int(round(v)) for v in ImageStat.Stat(small).mean[:3])
    return f"#{r:02x}{g:02x}{b:02x}"


def process(source, cache_dir):
    """Return ImageInfo for a source file, computing and caching it if needed."""
    source = Path(source)
    digest = file_hash(source)
    folder = Path(cache_dir) / f"{digest}-{SETTINGS_KEY}"
    meta_path = folder / "meta.json"

    if meta_path.exists() and all((folder / f"{name}.jpg").exists() for name in VARIANTS):
        meta = json.loads(meta_path.read_text())
        variants = {name: {**v, "path": folder / f"{name}.jpg"} for name, v in meta["variants"].items()}
        return ImageInfo(digest, meta["width"], meta["height"], meta["average_color"], variants)

    folder.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened)   # apply the rotation flag, then forget it
        image = to_srgb(image)
        width, height = image.size
        color = average_color(image)
        variants = {}
        for name, long_edge in VARIANTS.items():
            copy = image.copy()
            copy.thumbnail((long_edge, long_edge), Image.Resampling.LANCZOS)  # never upscales
            out = folder / f"{name}.jpg"
            # Saving a fresh RGB image writes no EXIF and no ICC profile: that
            # is the metadata strip. progressive=True makes the browser show a
            # blurry version early; optimize=True shaves a few percent. Write
            # to a temporary name and rename, so a reader never sees a half file.
            tmp = folder / f"{name}.tmp"
            copy.save(tmp, "JPEG", quality=JPEG_QUALITY[name], progressive=True, optimize=True)
            os.replace(tmp, out)
            variants[name] = {"width": copy.width, "height": copy.height, "path": out}

    meta = {
        "width": width, "height": height, "average_color": color,
        "variants": {name: {"width": v["width"], "height": v["height"]} for name, v in variants.items()},
    }
    meta_path.write_text(json.dumps(meta, indent=1))
    return ImageInfo(digest, width, height, color, variants)


def publish(info, dest_dir, stem):
    """Link an image's cached variants into the output folder.

    Files are named <stem>-<hash>-<variant>.jpg: the hash keeps two sources
    with the same stem apart and gives browsers a new URL when a photograph
    is re-exported. Hard links cost nothing, so dist/ can be rebuilt from
    scratch on every build; a copy is the fallback across filesystems.
    Returns {variant name: filename}.
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    names = {}
    for name, variant in info.variants.items():
        target = dest_dir / f"{stem}-{info.hash[:8]}-{name}.jpg"
        if not target.exists():
            try:
                os.link(variant["path"], target)
            except OSError:
                import shutil
                shutil.copyfile(variant["path"], target)
        names[name] = target.name
    return names
