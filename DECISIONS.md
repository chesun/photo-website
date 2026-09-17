# Decisions

A dated log of decisions about the photography site and the reasoning behind them. Newest at the bottom. When a decision changes, add a new entry rather than editing the old one, so the reasoning is preserved.

## 2026-09-12

**Migrate off Squarespace to a static site built by a Python script.**
Squarespace is too expensive for what it does. The two things it did well, arranging photos by eye and the full-bleed landing slideshow, are both reproducible: the slideshow in the spec, the arranging via a local curate page. Static output on GitHub Pages is free and fast. Python because I am learning it, coming from Stata.

**Survey of the current site, for the record.**
Squarespace 7.0, Pacific template, Futura PT. Root is a Cover Page slideshow with five direct links. Inner nav: Landscape (Color, Monochrome), People (5 galleries), Adventures (2 empty blog collections), Anthology (12 galleries), About. Gallery pages are Pacific's horizontal filmstrip, no captions. Bloat outside the nav: a demo print store with lorem ipsum, a one-post blog from 2019, a stale `/home`, duplicate `/landscape` and `/anthology` pages, three orphaned galleries. The cover-page email link is malformed. About 22 galleries and 330 images in total.

**The iPhone trip galleries on christinasun.net are not portfolio work.**
They were shot on a phone and are not the best work. They stay on the academic site for now. The film photos from those same trips, which are not yet on either site, are what goes on the photography site next.

**Do not merge landscape work across eras into one page.**
The 2019 digital work (Glacier, Yosemite, Death Valley, Oregon) and the 2024 to 2026 film work differ in palette, aspect ratio, subject, and composition. But the 2019 work includes photographs I am proud of and does not go to Archive. Resolution: the Landscape section holds several series, each internally coherent; only the index page, a grid of covers, shows them side by side.

## 2026-09-13

**The series is the content unit. No grouping by format, trip, or year.**
Grouping the film work by strand (square, panoramic, monochrome) was proposed and rejected as unsophisticated. The model that works is already on the site: Sand and Stone, Meditation on Solitude, Nightfall, Outskirts, Quiet Days are titled, sequenced series with a statement and a central thesis. Every gallery becomes one of these. Poetic names add value because they present a thesis.

**Color and monochrome are tags on a series, not a level of the hierarchy.**
"Landscape: Color" was an umbrella meaning all color photos including film, and "Monochrome" the same. Keeping them as levels would either mix eras on one page or add a third level of nesting for five series. As a tag on the series they survive as a filter without either cost.

**Five sections: Landscape, People, Interludes, Archive, About.**
A third body of work exists that is neither commissioned nor landscape: select frames from beach days, friends on the coast, quiet rolls. It needs its own section so it neither dilutes People nor gets buried in Archive. The tagline (nature, people, everything in between) is the thesis for the three-way split. "In Between" as a section name was rejected as boring; "Interludes" chosen.

**Retitle the 2019 digital galleries as thematic series.**
"Landscape: Color" and "Landscape: Monochrome" are category labels, not series titles, and are inconsistent with the series model. Titles must be in the register of Sand and Stone: plain visible nouns or a single plain word, with the abstraction coming from the pairing, not from an obscure word. "Vespers" rejected for that reason. Every frame on both pages was reviewed individually before proposing titles. The monochrome set (five Glacier storm frames plus fog trees) is *Storm Light*. The color set (eleven of thirteen frames are the sky at the edge of the day) is unresolved; *Afterglow* was rejected, *Alpenglow* is the placeholder, and the question stays open in TODO.md.

**Move the film panorama out of the 2019 color series.**
`000033810003-Edit.jpg` is 2020 Eastern Sierra film and is already the opening frame of *The Mountains are Calling*. It leaves the color series, which becomes purely digital.

**The Mountains are Calling and Sand and Stone move up from Anthology into Landscape.**
Both are landscape film series and were only hidden by the Anthology label. Quiet Days moves to Interludes. The remaining nine Anthology galleries go to Archive at launch, pending the gallery revisit in TODO.md.

**Column layout, not a justified grid.**
A grid makes the photographs small and reads as a contact sheet. One image per row, sized to the viewport, gives visual impact and makes the sequence matter, which is the point of a series. Grid stays available per series but unused at launch. Pairs layout was offered and not adopted.

**Real content from day one, pulled from the Squarespace CDN.**
The live images are full quality (the bare CDN URL returns the stored 2500px upload). Placeholder gradients are unnecessary. Lightroom originals exist for everything and can replace CDN copies later through the hash cache. The 2024 to 2026 film scans are unedited; those series arrive after editing, so the site launches without them.

**Ordering via YAML list plus a local curate page.**
Drag-and-drop matters less than having a clear way to arrange order, but visual flow is very important. The curate page from the academic site (`chesun.github.io/bin/curate.py`) already does this and is ported rather than reinvented.

**About page: keep bio, exhibitions list, academic link, Lange quote. Drop Facebook, newsletter, blog, print store.**

**Domain stays at Squarespace as domain-only for now.**
Squarespace is registrar and DNS for christinasunphoto.com and christinasun.org (which redirects to the photo site). christinasun.net is at GoDaddy. Transfer is a separate later task. No redirects from old gallery URLs are needed.

**Fonts: Futura does not matter.**
The current wordmark is Futura PT, which is not self-hostable. Any deliberately chosen light grotesque is fine; the uppercase letterspaced treatment is the continuity, not the face.

**Canonical contact email is `christinasunphotography@gmail.com`.**
Both addresses on the old site exist. The About-page one is canonical; `chesunphotography@gmail.com` stays off the site.

**Phase 1 built (2026-09-13): content model, migration, image pipeline, series pages, lightbox, dev server.**
Choices made while building, all reversible:

- Series `tone` is measured from the images at migration time (median HSV saturation, threshold 20 of 255) rather than guessed. Every result matched expectation on inspection.
- The Squarespace sitemap lists one image per gallery that the gallery page does not display (six cases). Those files are downloaded to `content/_unplaced/`, which the build ignores, so nothing is lost when Squarespace is cancelled.
- The landing slideshow's sixteen images on the old site are carried over as the `featured` lists, so the existing curation is not lost.
- Section indexes use justified rows computed at build time instead of a fixed grid, because covers with different aspect ratios in a grid leave titles at uneven heights, and two portrait covers in a two-column grid become enormous.
- Image variants are 480, 1600, and 2400px on the long edge at JPEG quality 82. On a retina display the browser picks the 2400px file for column layout, so a series page is heavy; revisit in the phase 4 performance pass.
- The dev server restarts itself when a build script changes, since Python does not reload imported modules.

## 2026-09-14

**Photographs stay in git.**
Keeping the JPEGs out of the repository was tried and reversed the same day. Out of git, the images would need their own backup, a fresh clone could not build, and deployment would have to run from the one machine that has them instead of from GitHub Actions. The cost of keeping them in is repository size, about 225MB now, growing with each re-export; GitHub's limits (1GB recommended, 100MB per file) are far off. The repository stays the complete source of truth.

**Typefaces: Newsreader and Inter.**
Hanken Grotesk and Fraunces were the phase 1 placeholders. A comparison sheet of ten serifs and nine sans faces, rendered with the site's real words and sizes, plus a live switcher on a real series page, led to Newsreader for titles and statements and Inter for wordmark, nav, captions, and body. Both are open source and self-hosted. Newsreader's optical-size axis is left on automatic; its 400 weight is not shipped because nothing uses it.

**Phase 2 built (2026-09-14): landing slideshow, 404, favicons, sitemap, OpenGraph, grid layout.**
The slideshow ships only the first slide's `src` and loads each next slide one ahead, pauses when the tab is hidden, and holds the first frame under reduced motion. The scrim is a radial gradient behind the text block only. The header floats transparent and white over the hero; a backdrop-filter on the header would clip the mobile overlay, so it is dropped while the menu is open. Grid layout reuses the justified-row solver written for the index pages.

**Landing navigation lives in the hero, not the header.**
With the header floating over the slideshow, the top-right links disappeared against light skies. The landing page now has no header at all; wordmark, tagline, and the five section links sit centred inside one scrim, as on the old Squarespace cover page. Inner pages keep the header.

**Per-image focal points.**
Slides are cropped to the viewport, and some frames were framed awkwardly by a centre crop. `series.yaml` gains an optional `focal` map, filename to a CSS `object-position`, the same idea as Squarespace's focal point picker. It applies to the slideshow and to cover images; the curate page in phase 3 should let it be set by clicking.

## 2026-09-17

**Phase 3 built: the curate page.**
A single HTML page served by the dev server with four JSON and image routes behind it. Two choices worth recording: the YAML is edited as text, block by block, rather than round-tripped through PyYAML, so comments and key order in `series.yaml` survive a save; and thumbnails are served from the image cache through the dev server rather than from `dist/`, so unpublished series can be curated before they are ever built. The first migration run had written filename-only captions for Graduations and Quiet Days (the check was fixed while that run was in progress); those were stripped.

**The curate page also adds, moves, and removes photographs, and creates series.**
Christina asked for add and remove after trying the first version. Removal moves a file to `content/_removed/<series>/` rather than deleting it, and permanent deletion exists only for the holding folders, with a confirm step, so a slip on a page that edits the source of truth is always reversible. Uploads accept JPEG only, matching the Lightroom export the site is built around. New series start unpublished and empty so photographs can be gathered before anything is built; the content loader was relaxed to allow that one case.

