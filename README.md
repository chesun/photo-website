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

1. Export the photographs from Lightroom: JPEG, sRGB, long edge about 2500px, quality about 80. Filenames should be plain: letters, digits, dashes, dots.
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
focal:                    # optional, filename: where to anchor a cropped frame
  000038580006.jpg: 50% 30%
```

`focal` matters on the landing slideshow, where every photograph is cropped to fill the screen. The value is a CSS `object-position`: `50% 50%` is the centre (the default), `50% 30%` keeps the upper part of a tall frame, `30% 50%` keeps the left of a wide one. Set it on a featured image whose crop looks wrong.

4. Build. Any JPEG in the folder that is not listed under `images` is appended to the end with a warning, so you can drop files in first and arrange later.

The build stops with a clear message if a listed image is missing, a key is misspelled, or a non-image file is in a series folder.

## The curate page

Run `--serve` and open http://127.0.0.1:8000/_curate/. It is the place to arrange the site by eye, and it can add and remove photographs too. Every change goes straight into `content/`, the site rebuilds on its own, and `git status` shows what changed so you can commit when you are happy.

- **Landing slideshow strip** at the top, in the order the show will run. Click a slide to set its focal point.
- **Drag** a photograph to reorder it, or focus it and use the arrow keys.
- **◧** makes it the cover shown on the section index. **★** adds or removes it from the landing slideshow. **⌖** opens the focal-point tool: drag the ring to where the crop should be anchored while the outline shows exactly what the desktop or phone slideshow will keep; arrow keys nudge.
- **⋯** moves the photograph to another series (its caption and focal point travel with it) or removes it. Removed files are not deleted; they go to `content/_removed/<series>/`. The last photograph of a published series cannot be removed; set `published: false` first.
- **Add photos** on a series uploads JPEGs into its folder and appends them to the order. Filenames are kept, with spaces turned into dashes; a name already in use gets a `-2` suffix. Anything that is not a JPEG is refused.
- **Holding** at the bottom lists the files in `content/_removed/` and `content/_unplaced/`. Place one into any series, or delete it for good (choose Delete twice).
- **New series** in the top bar creates `content/series/<slug>/series.yaml` for an empty, unpublished series. Add photographs, arrange them, then set `published: true` in the YAML when it is ready.
- **Save** writes `images`, `cover`, `featured`, and `focal` for a series (or **Save all**). Everything else in the file, including comments, is left as it was. A series with unsaved changes must be saved before photos are added or moved.

Nothing of the page goes into `dist/`. You can always edit the YAML by hand instead.

## The landing slideshow

The landing page cycles through every image listed under `featured` in any published series, in section order (Landscape, People, Interludes, Archive) and then series order. Add or remove filenames there to change the show. The first slide is preloaded; the rest load one ahead as the show runs.

## Column or grid

`layout: column` (the default) shows one photograph per row, sized to the viewport. `layout: grid` packs them into justified rows of equal height, for high-volume galleries where scanning matters more than sequence.

## Moving, retitling, or hiding a series

- **Move to another section:** change `section`. The URL changes with it.
- **Retitle:** change `title`. To change the URL too, rename the folder.
- **Hide:** set `published: false`. The files stay in the repo; no page is built.

## Fonts and favicons

The two typefaces, Inter and Newsreader, are self-hosted from `static/fonts/` as Latin-subset woff2 files downloaded from the Google Fonts API; `fonts.css` next to them declares the faces. The favicons in `static/` are generated once by `scripts/make_favicons.py`.

## Migrating from Squarespace

`scripts/migrate_squarespace.py` imports every gallery from the live site once, in the order they were arranged there, and seeds the About page. Run it before cancelling Squarespace; the images disappear with the subscription. It is safe to re-run.

## Deploying

The site lives at https://github.com/chesun/photo-website and is published by GitHub Pages. Every push to `main` runs `.github/workflows/deploy.yml`, which builds the site exactly as `scripts/build.py` does locally and publishes `dist/`. Image variants are cached between runs, so a text-only change deploys in about a minute; a change to photographs takes a couple of minutes longer.

So the publishing routine is: arrange things in the curate page or edit the YAML, look at the local preview, then

```
git add -A
git commit -m "Add the Lost Coast series"
git push
```

The Actions tab on GitHub shows the run. Nothing else is needed.

### Pointing christinasunphoto.com at GitHub Pages

The domain is registered at Squarespace, which also runs its DNS. GitHub Pages already knows the domain (the build writes a `CNAME` file and the repository's Pages settings name it), so the only step is to change the DNS records at Squarespace once you are ready to switch. Until then visitors keep seeing the Squarespace site.

In Squarespace: Settings, Domains, christinasunphoto.com, DNS settings. Remove the Squarespace records for the domain and add:

| Type | Host | Value |
|---|---|---|
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |
| CNAME | www | chesun.github.io |

Within an hour or so GitHub's Pages settings for the repository will show the domain as verified and will issue an HTTPS certificate; then tick **Enforce HTTPS** there. Keep the domain itself registered at Squarespace (a domain-only plan) or transfer it later; either is fine.

After the switch, cancel the Squarespace site subscription. Everything from it is already in this repository, including the eight images in `content/_unplaced/`.
