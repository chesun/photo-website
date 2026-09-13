# christinasunphoto.com

The photography portfolio of Christina Sun, built as a static site by a small Python script and hosted on GitHub Pages. It replaces a Squarespace site.

Three documents describe the project:

- `SPEC.md` — what the site is and how it is built. The source of truth.
- `DECISIONS.md` — why each choice was made, with dates.
- `TODO.md` — open questions and future work.

## Setup

Requires Python 3.11 or newer.

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Building and previewing

```
.venv/bin/python scripts/build.py            # build once into dist/
.venv/bin/python scripts/build.py --serve    # build, then serve at http://127.0.0.1:8000/
.venv/bin/python scripts/build.py --clean    # start over: delete dist/ and the image cache
```

With `--serve`, any change under `content/`, `templates/`, or `static/` triggers a rebuild. Reload the browser to see it. A change to anything under `scripts/` restarts the server, because Python does not reload code it has already imported. Image processing is cached by file content in `.cache/`, so a rebuild that changes no photos takes well under a second.

## How the content is organised

Everything the site shows lives under `content/`:

```
content/
  site.yaml                 title, tagline, navigation, links
  series/<slug>/            one folder per series
    series.yaml             title, section, order, tone, statement, image order
    *.jpg                   the photographs, web-resolution
  about/
    about.md                the About page text, in Markdown
    portrait.jpg
```

A *series* is a titled, sequenced body of work. It belongs to one of four sections: `landscape`, `people`, `interludes`, or `archive`. The folder name is the URL slug, so `content/series/sand-and-stone/` becomes `/landscape/sand-and-stone/`.

## Adding a series

1. Export the photographs from Lightroom: JPEG, sRGB, long edge about 2500px, quality about 80.
2. Make a folder `content/series/<slug>/` and put the JPEGs in it.
3. Add a `series.yaml` next to them. Copy one from another series and edit it. The keys:

```yaml
title: Sand and Stone
section: landscape        # landscape | people | interludes | archive
order: 30                 # position within the section index; lower first
tone: monochrome          # color | monochrome
layout: column            # column (default) | grid
published: true           # false keeps the files but builds nothing
statement: One or two sentences shown above the photographs.
cover: 000038580006.jpg   # shown on the section index
featured:                 # optional; images for the landing slideshow
  - 000038580006.jpg
images:                   # the display order
  - 000038580006.jpg
  - 000038570010.jpg
captions:                 # optional, filename: caption
  000038580006.jpg: Alabama Hills
```

4. Build. Any JPEG in the folder that is not listed under `images` is appended to the end with a warning, so you can drop files in first and arrange later.

The build stops with a clear message if a listed image is missing, a key is misspelled, or a non-image file is in a series folder.

## Arranging the order

Edit the `images` list in `series.yaml`, or use the curate page: run `--serve` and open http://127.0.0.1:8000/_curate/ (phase 3, not built yet).

## Moving, retitling, or hiding a series

- **Move to another section:** change `section`. The URL changes with it.
- **Retitle:** change `title`. To change the URL too, rename the folder.
- **Hide:** set `published: false`. The files stay in the repo; no page is built.

## Migrating from Squarespace

`scripts/migrate_squarespace.py` imports every gallery from the live site once, in the order they were arranged there, and seeds the About page. Run it before cancelling Squarespace; the images disappear with the subscription. It is safe to re-run.

## Deploying

Phase 4, not written yet. See `SPEC.md`.
