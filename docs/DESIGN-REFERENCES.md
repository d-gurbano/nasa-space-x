## Showcase sites

Researched Nov 14-15 2026. Browsed one page at a time, read-only. Screenshots are in `/Users/rahmanbazarov/.aside/u/0/sessions/2026-11-14_wmIxRqhiLmHckXbM/tmp/design-refs/`.

Honest limits: the gallery sites (Awwwards, Godly, SiteInspire, Minimal Gallery, Lapa Ninja, One Page Love) lazy-load their thumbnails, so my screenshots showed empty grids. Lapa Ninja and One Page Love space URLs returned 404. I list them as places to browse by hand, not as references. Everything in the table below was actually opened. Rows 10-14 were only seen at the landing or index level, so their notes are lighter.

### Ranked references

| Rank | Name | URL | What to borrow | Screenshot |
|---|---|---|---|---|
| 1 | NASA Eyes on Asteroids | https://eyes.nasa.gov/apps/asteroids/ | The closest match. Thousands of asteroid dots, labeled named bodies, orbit lines colored by planet, one bottom time slider with a big date readout and a green LIVE chip, tiny top nav (Learn / Asteroid Watch / Filters), search box with a one-result dropdown. | tmp/design-refs/01-eyes-asteroids.png, 16-eyes-asteroids-apophis-panel.png |
| 2 | NASA Eyes on Asteroids, mobile layout | https://eyes.nasa.gov/apps/asteroids/ (390 px wide) | Mobile pattern: 3D fills the screen, time slider sits just above a bottom tab bar (Learn / Asteroid Watch / Filters), date text gets bigger, search opens as a full-width card. Copy this for Rewind mobile. | tmp/design-refs/17-eyes-asteroids-mobile.png |
| 3 | NASA Eyes on the Solar System | https://eyes.nasa.gov/apps/solar-system/ | Left rail of story cards (title, big image, gold spaced date) for "featured events". Good model for Rewind's "discovery stories" list. Right-side icon stack (info, layers, zoom, contrast, fullscreen, settings). Time control is a round knob on an arc with a REAL RATE label. | tmp/design-refs/02-eyes-solar-system.png |
| 4 | Google 100,000 Stars | https://stars.chromeexperiments.com/ | Onboarding: a single italic caption at the bottom over the scene ("This is a visualization of over 100,000 nearby stars.") plus a Skip link. One sentence per step, scene keeps moving behind it. Also shows how fast a 100k point cloud can feel with additive glow and star color. | tmp/design-refs/09-100k-stars.png |
| 5 | JPL Small-Body Database Lookup | https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html | The real source of uncertainty. Every orbital element has a 1-sigma value, plus first/last observation date, number of observations and data-arc span (Eros: 9130 obs, arc 127.53 years, first obs 1893). Use these numbers to size the fuzzy cloud and to show "arc grew by N years". Do not copy its dense table; show 3 numbers only. Also has an embedded Orbit Viewer. | tmp/design-refs/18-jpl-sbdb.png |
| 6 | Stellarium Web | https://stellarium-web.org/ | Clean floating chrome: round menu button top left, pill search top center, row of toggle icons at bottom, small time/date chip bottom right. Everything is translucent so the sky stays the hero. Good "is it there?" metaphor: tap a spot, get the name. | tmp/design-refs/10-stellarium-web.png |
| 7 | NASA Eyes on Exoplanets | https://eyes.nasa.gov/apps/exo/ | Welcome modal pattern: "Did you know?" fact, "How to explore" in 3 lines, two buttons (Explore Now / Watch Tutorial), checkbox "do not show again". Also a live "You are 3,020 light-years from Earth" readout and a filter tray. Avoid: the modal is a wall of text on first load. Keep Rewind's to 2 lines. | tmp/design-refs/19-eyes-exoplanets.png |
| 8 | Bruno Simon portfolio | https://bruno-simon.com/ | Proof that a three.js scene can carry a whole site, with a glowing ring target and a dot grid that gives scale and motion cues. Borrow the glow ring idea for the "beam flash" and for a selected-object marker. Avoid: it asks users to drive a car, far too slow for a student judge or a phone. | tmp/design-refs/06-bruno-simon.png |
| 9 | Solar System Scope | https://www.solarsystemscope.com/ | Big single START button on a hero image that loads the 3D model, so the heavy scene only loads on intent. Borrow for a fast landing page on mobile. Avoid: sci-fi hex buttons, heavy header, ad and app buttons crowding the hero. | tmp/design-refs/05-solar-system-scope.png |
| 10 | Neal.fun The Size of Space | https://neal.fun/size-of-space/ | Start screen is one line and one Start button, then a guided scroll. Good model for a 20-second "rewind demo" intro. I only saw the start screen. | tmp/design-refs/04-neal-size-of-space.png |
| 11 | three.js examples index | https://threejs.org/examples/ | Source of ready code: logarithmicdepthbuffer (needed for huge distance ranges), points/sprites, camera tween, LOD, batch. I only opened the index. | tmp/design-refs/11-threejs-examples.png |
| 12 | React Three Fiber examples | https://r3f.docs.pmnd.rs/getting-started/examples | Showcase list includes Bruno Simon and Lusion style sites plus helpers (drei, postprocessing). Use if the team picks React. I only opened the index. | tmp/design-refs/14-r3f-examples.png |
| 13 | Codrops Creative Hub | https://tympanus.net/codrops/hub/ | Fresh WebGL and GSAP demos (hover reveals, three.js, glsl) with source. Good for the beam flash and photo pop-in transitions. Index only. | tmp/design-refs/12-codrops-demos.png |
| 14 | Spline Community | https://community.spline.design/ | Remixable 3D scenes, useful for quick planet or asteroid models. Avoid exporting full Spline scenes to production on mobile, they are heavy. Index only. | tmp/design-refs/15-spline-community.png |

Gallery places to browse by hand (screenshots saved but thumbnails did not load, so not ranked): Awwwards three.js tag (https://www.awwwards.com/websites/three-js/, 2,368 sites) and search "space"; SiteInspire; Minimal Gallery; Godly (redirected to recent.design). Look for Sites of the Day with scrolling-camera space scenes. Screenshots: 07, 08, 21, 22.

### Patterns to avoid

- Long first-load modals with paragraphs (Exoplanets welcome). Keep to 2 lines.
- Dense data tables in the main view (JPL). Show 3 numbers and link out.
- Drive-a-car or heavy game controls (Bruno Simon). Too slow for judges and phones.
- Sci-fi chrome, hex buttons, ad badges around the 3D hero (Solar System Scope).
- A time slider that is hidden or tiny. On Eyes it works because date text is large and always visible.
- Too many labels at once. Eyes on Asteroids labels about 25 bodies and dims the rest; do the same.

### Rewind design recipe

1. Layout: full-screen 3D scene, almost no chrome. Top: tiny logo and a search pill. Bottom: one wide time slider with a large date readout. Nothing else on screen at first.
2. Time control: copy the Eyes bottom slider (big monospace date, round knob), but make the left side clearly "past" with year ticks and a "back to today" chip where Eyes has LIVE. Dragging back moves objects along real orbits.
3. Onboarding: Google 100,000 Stars style. One italic caption at a time over the live scene, 3 steps max ("This is the solar system today", "Drag time backward", "Watch for a flash"), with a Skip link. No modal wall.
4. Dots and labels: thousands of faint points for the crowd, labels only for about 20 named objects, orbit lines colored per body. Dim everything not selected.
5. Beam flash: a glowing ring or pulse at the object (Bruno Simon ring idea) plus a thin line to the photo card, then the real SPHEREx photo slides in. Flash once, then leave a small pin on the slider at that date.
6. Fly-to and panel: click an object, camera eases to it, and a side panel opens (bottom sheet on mobile). Tabs inside: Old photos, Is it there? quiz, What it is made of, Discovery story. Use the Eyes solar-system story cards style for the discovery list (title, image, spaced gold date).
7. Uncertainty: draw the orbit as a soft translucent tube whose width equals the real 1-sigma from JPL SBDB, and shrink it to a thin line as old photos are added. Show one caption: "Observed for 127 years, 9,130 measurements" using the data-arc and observation counts SBDB publishes.
8. Mobile: Eyes mobile pattern. Slider just above a bottom tab bar, panels as bottom sheets, search as a full-width card, labels cut to 8-10, pinch and drag only, no hover states.
9. Performance: load the heavy scene only after a Start tap on mobile (Solar System Scope idea), render crowd as one Points object, use a logarithmic depth buffer for distance range (three.js example), lower pixel ratio on phones.
10. Look: black space, thin white-grey orbit lines, one cool blue for the crowd, one warm gold for dates and highlights (Eyes palette), one clean sans font, large numerals for dates. Translucent dark panels like Stellarium.

## X and indie communities

Researched Nov 14-15 2026. 9 X searches at one per 40-60 seconds, no rate limits or challenges seen. Read-only. Product Hunt and Indie Hackers were not checked (time cap), so that is still open. Most "three.js solar system" posts on X right now are one-prompt AI demos with generic looks; the ranking below favors real data, time control and real-image reveals. Screenshots are in `tmp/design-refs/` of the research session (`/Users/rahmanbazarov/.aside/u/0/sessions/2026-11-14_wmIxRqhiLmHckXbM/tmp/design-refs/`).

| Rank | Name / author | Post URL | Site URL | What to borrow (1 line) | Screenshot |
|---|---|---|---|---|---|
| 1 | NASA Eyes on Asteroids (shown via @Ammar1176708, 440 likes, 57k views) | https://x.com/Ammar1176708/status/2121365965988671995 | https://eyes.nasa.gov/apps/asteroids/ | Bottom time scrubber with LIVE pill and date, dense dot cloud of objects, labels only on named ones, thin orbit lines | x-04-eyes-on-asteroids.png, x-04b-eyes-asteroids-site.png |
| 2 | Watched by @armaangupt0 (214 likes, 58.9k views) | https://x.com/armaangupt0/status/2119843864060051725 | https://watched.earth | Globe plus real satellite photos popping up for a place and time: same "real photo appears" beat as the SPHEREx reveal; mono UTC clock, large serif headline, GPU Kepler solve for 17,000 objects | x-02-watched-satellites.png, x-02b-watched-site.png |
| 3 | NASA Solar System simulator, Voyager 1 post (@NASASolarSystem, 2,598 likes, 90k views) | https://x.com/NASASolarSystem/status/2121282705736515837 | https://eyes.nasa.gov/apps/solar-system | Track one object through time, show light travel time, "re-create its tour" replay; good model for a guided rewind | x-01-nasa-eyes-voyager.png |
| 4 | Real-shape helical solar system, @Astro_horizon00 (243 likes, 8.3k views) | https://x.com/Astro_horizon00/status/2120845217645605143 | not given in post | Real Kepler elements and J2000 mean anomalies drive the motion, so a time slider stays honest | x-05-helical-kepler.png |
| 5 | Solar system vortex fact-check, @alexboge (209 likes, 345k views) | https://x.com/alexboge/status/2120947646642708899 | link in a reply, not captured | Story-first framing ("it looks wrong, here is the real data"); calm zoom-out sequence with credits to NASA/JPL | x-03-alexboge-vortex-sim.png |
| 6 | Endless Panels, @nagasawa_item (936 likes, 31.8k views) | https://x.com/nagasawa_item/status/2119372840977977491 | https://item-demo-466.pages.dev/endless-panels/?preset=whi... | Performance tricks: instanced draws, CPU writes slots and timestamps while GPU animates, floating origin to keep float32 precise at huge scale | x-06-endless-panels-perf.png |
| 7 | Cinematic orrery, @shxwat (15 likes, 1.5k views) | https://x.com/shxwat/status/2087547796765528559 | https://solar-orrery-3d.vercel.app (showed a Vercel login page when opened, so may be private now) | Smooth planet fly-ins, cinematic mode toggle, lens effects | x-07-cinematic-orrery.png, x-07b-orrery-site.png |
| 8 | Cosmic Atlas, @yash_yk45 (22 likes, 5.3k views) | https://x.com/yash_yk45/status/2089423535127269884 | https://threejs-ruddy-six.vercel.app | Camera hops between bodies with GSAP, Kepler orbits, real texture maps | x-08-cosmic-atlas.png |
| 9 | Aguacero 3D weather volumes, @aguacerowx (474 likes, 42k views) | https://x.com/aguacerowx/status/2120555255469351267 | http://aguacerowx.com/app | Desktop and mobile 3D with a mobile "Map tools" sheet, drag a box then tap "Use this view"; orbit and tilt while a model run plays | x-09-weather-3d-mobile.png |
| 10 | Stellar Atlas, @simxnm (7 likes, 573 views) | https://x.com/simxnm/status/2119603545452544492 | link in a reply, not captured | Search any object and fly to it, plot routes with trip time readout | x-10-stellar-atlas.png |

Not screenshotted but seen in search: @dzhohola ORBITAL (177 likes, https://x.com/dzhohola/status/2096339041679442428), @kickscosmo solar system map with asteroid belt and comet (https://x.com/kickscosmo/status/2053816488100872547), @UniverseOneSim engine clip (17k likes, https://x.com/UniverseOneSim/status/2119157989810782463, video only, no site to study).

### Takeaways

- The strongest "time" UI is the NASA Eyes pattern: one thin scrubber at the bottom, a big date readout, and a LIVE pill to snap back to now. Copy that for the Rewind slider and add a "now" button.
- Watched proves the reveal works: a real image appearing when the data says a satellite passed. Use the same restraint for the SPHEREx beam: one flash, one photo card, the date and sensor in small mono text.
- Show thousands of objects as a dim dot cloud and label only the few that matter. Eyes on Asteroids does this; it keeps the scene readable and cheap.
- Performance and mobile: instanced draws, GPU Kepler solving, and floating origin (nagasawa, Watched). Aguacero shows a bottom sheet for tools on phones instead of shrinking the desktop UI.
- Avoid: the one-prompt AI solar systems flooding X (generic textures, tiny fixed UI, no data meaning), "cinematic mode" effects that hide the data, and fixed fantasy spirals that are not real scale (the vortex video Alex Boge debunked). Also avoid labelling everything at once.
