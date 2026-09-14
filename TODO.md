# TODO

Open questions and future work for the photography site. Decisions, once made, move to `DECISIONS.md`. Anything that changes what gets built also gets reflected in `SPEC.md`.

## Before building

- [ ] **Do not cancel Squarespace until the migration script has run and the new site has been checked page by page.** The CDN images disappear with the subscription, and for some galleries the edited web exports and their order exist only there.

## Open questions

- [ ] **Set focal points on the featured images that crop badly** on the landing page, via `focal:` in the series YAML (or the curate page once phase 3 exists).

- [ ] **Decide what to do with `content/_unplaced/`.** Eight images the old sitemap listed but the gallery pages never showed, one each for Nightfall, Streets of Sacramento, UC Davis Symphony Orchestra, The City by the Sea, and two each for Streets of Davis and Adventure. Move into a series, or delete.

- [ ] **Title of the 2019 color series.** Placeholder *Alpenglow*. Rejected so far: Vespers (too oblique), Afterglow (word disliked, "glow" liked), Heaven's Door, The Gilded Hour, Where the Sky Begins, A Brief Eternity, Earth and Sky, Fire and Snow, Water and Light, Moon and Mountain, Half Light, Moonglow, Ember, Glow. The set: alpenglow on a Glacier peak, Zabriskie Point at dusk, full moon over the high Sierra, two figures above a sea of fog under a crescent moon, Oregon coast at dusk, Lake McDonald at dawn, the Milky Way over Mount Hood, the Yosemite Falls moonbow, the sun with birds at the Yolo Bypass, storm light at Logan Pass, the cliff wrapped in cloud, the dune abstract.
- [ ] **Revisit every gallery for consolidation into thematic series.** Now that series are thematic, some existing galleries are redundant or mis-filed. Known candidates:
  - *The Mountains are Calling* (2020 Eastern Sierra color film, 6 frames) likely merges into the 2019 color series; its opening frame was already there.
  - The dune abstract and the cliff-in-cloud frame in the 2019 color series are closer to the current abstract aesthetic than to the rest of that set. Decide whether they stay or seed a new series with the 2024 to 2026 sandstone work.
  - *Nightfall*, *Outskirts*, and *Meditation on Solitude* are thematic series about human-altered landscapes and might belong in Landscape or Interludes rather than Archive.
  - *Panoramic Streets: Color* (6) and *Animal Companions* (2) and *The City by the Sea* (3) are too small to stand alone. Merge, or accept as archive stubs.
  - The three orphaned galleries (Streets of Davis, Life and Adventure, Adventure) are migrated as unpublished. Decide keep, merge, or delete.
- [ ] **Which personal frames go into Interludes.** Beach days (2022-01, 2022-09), friends on the Lost Coast, life snaps from 2023, JMT frames with people in them. Needs a pass through the library.

## After launch

- [ ] **Edit the 2024 to 2026 film scans in Lightroom and sequence them into new Landscape series.** Roughly 180 unedited scans: Sequoia and Kings Canyon (35mm mono), Great Basin and Zion (120 color, 35mm panoramic), Utah (120 color, 35mm panoramic), Grand Canyon (120 mono), Paria Canyon (120 mono), Lost Coast (120 color). The 6x6 sandstone work across Zion, Bryce, Utah, and Paria looks like one series. Grand Canyon and Paria in monochrome either join Sand and Stone or become its sequel. Lost Coast is its own thing and has people in it.
- [ ] **Replace CDN copies with Lightroom re-exports** where a better master exists. Same filename, new hash, nothing else changes.
- [ ] **Add the film pieces that are not on either site yet** from trips already shot: Zion, Bryce, Great Basin, Paria Canyon, and others.

## Maybe later

- [ ] Port the iPhone trip journals from christinasun.net into Interludes as clearly casual entries, or leave them where they are.
- [ ] Journal text for JMT 2025, the Tahoe Rim Trail, and JMT 2026 from the trail notebooks.
- [ ] Transfer the domain from Squarespace to GoDaddy, where christinasun.net already lives.
- [ ] Redirect stubs for old Squarespace URLs, if any turn out to be linked from somewhere that matters.
- [ ] Point the "My landscape portfolio" and "Personal projects" links on christinasun.net/extras at the new sections once they exist.
