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
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageCms, ImageOps, ImageStat

# Variant name -> long-edge size in pixels. `medium` is what most visitors
# download on a desktop in column layout, so it is the one to keep an eye on.
VARIANTS = {"thumb": 480, "medium": 1600, "large": 2400}
JPEG_QUALITY = 82

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
    folder = Path(cache_dir) / digest
    meta_path = folder / "meta.json"

    if meta_path.exists():
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
            # blurry version early; optimize=True shaves a few percent.
            copy.save(out, "JPEG", quality=JPEG_QUALITY, progressive=True, optimize=True)
            variants[name] = {"width": copy.width, "height": copy.height, "path": out}

    meta = {
        "width": width, "height": height, "average_color": color,
        "variants": {name: {"width": v["width"], "height": v["height"]} for name, v in variants.items()},
    }
    meta_path.write_text(json.dumps(meta, indent=1))
    return ImageInfo(digest, width, height, color, variants)


def publish(info, dest_dir, stem):
    """Copy an image's cached variants into the output folder.

    Files are named <stem>-<variant>.jpg. Returns {variant name: filename}.
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    names = {}
    for name, variant in info.variants.items():
        target = dest_dir / f"{stem}-{name}.jpg"
        if not target.exists() or target.stat().st_size != variant["path"].stat().st_size:
            shutil.copyfile(variant["path"], target)
        names[name] = target.name
    return names
