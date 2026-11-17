# TODO

Open questions and future work for the photography site. Decisions, once made, move to `DECISIONS.md`. Anything that changes what gets built also gets reflected in `SPEC.md`.

## Before building

- [x] **Do not cancel Squarespace until the migration script has run and the new site has been checked page by page.** The CDN images disappear with the subscription, and for some galleries the edited web exports and their order exist only there. Christina cancelled the website subscription on 2026-11-17; the domain stays registered at Squarespace.

## Open questions

- [ ] **Review the landing slideshow selection by eye** in the curate page once phase 3 exists. The first pass on 2026-09-14 chose eight, one or two per genre, for surviving a 16:9 crop. On 2026-11-17 Christina took The Mountains are Calling out, leaving seven: two from Alpenglow, one each from Storm Light, Sand and Stone, From the Earth to the Stars, Love on the Coast, Graduations.
- [ ] **Set focal points by eye on the landing slideshow images**, in the curate page once phase 3 exists (click on the photo to place the anchor; it writes `focal:` in the series YAML). Until then a centre crop applies.

- [ ] **Decide what to do with `content/_unplaced/`.** Eight images the old sitemap listed but the gallery pages never showed, one each for Nightfall, Streets of Sacramento, UC Davis Symphony Orchestra, The City by the Sea, and two each for Streets of Davis and Adventure. Move into a series, or delete.

- [ ] **Title of the 2019 color series.** Placeholder *Alpenglow*. Rejected so far: Vespers (too oblique), Afterglow (word disliked, "glow" liked), Heaven's Door, The Gilded Hour, Where the Sky Begins, A Brief Eternity, Earth and Sky, Fire and Snow, Water and Light, Moon and Mountain, Half Light, Moonglow, Ember, Glow. The set: alpenglow on a Glacier peak, Zabriskie Point at dusk, full moon over the high Sierra, two figures above a sea of fog under a crescent moon, Oregon coast at dusk, Lake McDonald at dawn, the Milky Way over Mount Hood, the Yosemite Falls moonbow, the sun with birds at the Yolo Bypass, storm light at Logan Pass, the cliff wrapped in cloud, the dune abstract.
- [ ] **Revisit every gallery for consolidation into thematic series.** Now that series are thematic, some existing galleries are redundant or mis-filed. Known candidates:
  - *The Mountains are Calling* (2020 Eastern Sierra color film, 6 frames) likely merges into the 2019 color series; its opening frame was already there.
  - The dune abstract and the cliff-in-cloud frame in the 2019 color series are closer to the current abstract aesthetic than to the rest of that set. Decide whether they stay or seed a new series with the 2024 to 2026 sandstone work.
  - *Panoramic Streets: Color* (6) and *Animal Companions* (2) and *The City by the Sea* (3) are too small to stand alone. Merge, or accept as archive stubs.
  - The three orphaned galleries (Streets of Davis, Life and Adventure, Adventure) are migrated as unpublished. Decide keep, merge, or delete.
- [ ] **Sort the personal frames between Journeys and Interludes.** Trips go to Journeys (friends on the Lost Coast, JMT frames with people in them); beach days (2022-01, 2022-09) and life snaps from 2023 may suit Quiet Days in Interludes. Needs a pass through the library.
- [ ] **Shape the Vermilion Cliffs journey** (`content/series/vermilion-cliffs/`, the Paria Canyon roll). All 30 edited 35mm exports from `Dropbox/Photography/Photos/2026/2026-03-22_paria-canyon/35mm/exports/` are in, at 2500px, in roll order. Choose and sequence them in the curate page, pick a cover (it defaults to the first frame), and write a statement. Decide whether the four 120 monochrome frames from the same trip (`120/scans/`) join it.
- [ ] **Split Sand and Stone.** Its statement describes one trip (Eastern Sierra and Death Valley, January 2024). Christina picks the frames that are a record of the trip rather than a statement; those become an Eastern Sierra and Death Valley entry in Journeys, and the rest stays in Landscape or joins the sandstone work.

## After launch

- [ ] **Phone-friendly featured images.** On a phone the slideshow fills a tall screen, so a 2.7:1 panorama is scaled up hard and fetched at the largest size; the review measured the landing LCP at about 5s on simulated slow 4G. Prefer frames nearer 3:2 or square for the landing, or add a phone crop later.
- [ ] **WebP variants.** The build could emit WebP beside the JPEGs (Pillow can) for roughly a third less weight per series page; the review estimated 500KB or more saved on a nine-image page.
- [ ] **iOS scroll lock behind the open mobile menu.** `overflow: hidden` on the body is not honoured by iOS Safari; a fixed-body lock would be.

- [ ] **Edit the 2024 to 2026 film scans in Lightroom and sequence them into new Landscape series.** Roughly 180 unedited scans: Sequoia and Kings Canyon (35mm mono), Great Basin and Zion (120 color, 35mm panoramic), Utah (120 color, 35mm panoramic), Grand Canyon (120 mono), Lost Coast (120 color). The 6x6 sandstone work across Zion, Bryce, Utah, and Paria looks like one series. Grand Canyon in monochrome either joins Sand and Stone or becomes its sequel. Lost Coast is its own thing and has people in it.
- [ ] **Replace CDN copies with Lightroom re-exports** where a better master exists. Same filename, new hash, nothing else changes.
- [ ] **Add the film pieces that are not on either site yet** from trips already shot: Zion, Bryce, Great Basin, and others.

## Maybe later

- [ ] Port the iPhone trip journals from christinasun.net into Journeys as clearly casual entries, or leave them where they are.
- [ ] Journal text for JMT 2025, the Tahoe Rim Trail, and JMT 2026 from the trail notebooks.
- [ ] Transfer the domain from Squarespace to GoDaddy, where christinasun.net already lives.
- [ ] Redirect stubs for old Squarespace URLs, if any turn out to be linked from somewhere that matters.
- [ ] Point the "My landscape portfolio" and "Personal projects" links on christinasun.net/extras at the new sections once they exist.
