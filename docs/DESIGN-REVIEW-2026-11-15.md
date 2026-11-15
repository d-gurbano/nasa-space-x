# Rewind design and copy review (15 Nov 2026)

This review covers the live site at rewind-spaceapps-production.up.railway.app: Home, Sky, Games, Challenge stars, Does it work, For scientists and About. It was done in a desktop browser at 1024 px and a mobile one at 375 px. No console errors showed up on any page.

**Design: B-.** The look is consistent across pages. The 3D map and the Sky flipbook show something real. The weak spots are a broken hero layout, numbers that disagree between pages, and a few overlap bugs.
**AI-slop: C+.** The copy is mostly plain and specific, which is good. A small set of phrases ("honestly", short slogans, a developer spec printed on a public page) gives away that AI wrote some of it, and those phrases sit right where judges will read.

---

## 1. Broken or wrong (fix before judging)

### H1. The home hero headline is broken, and on mobile the text is cut off
- **Desktop:** "past." floats to the right of "has a" and sits between the two lines instead of finishing the sentence.
- **Mobile (375 px):** the headline reads "Every / discovery **past.** / has a". The intro paragraph is clipped at the right edge ("…is discovered, Rewin", "taken b", "path bec").
- **Root cause:** `.op-title` is `display:flex; flex-direction:row; flex-wrap:nowrap`. In a flex row the `<br>` doesn't break the line, so `<em>past.</em>` becomes a separate flex item placed beside the text. `.op-inner` is also 394 px wide on a 375 px screen, which is why the paragraph gets clipped.
- **Fix:** set `.op-title` to `display:block` (or remove the flex), and give `.op-inner` `max-width: 100%` or `width: auto`. This is the first thing every visitor sees.

### H2. The same numbers disagree from page to page
Judges will cross-check these. Pick one definition for each and use it everywhere.

| Fact | Where | Value shown |
|---|---|---|
| Number found | Home, About, Scientists header | **8** |
| | Scientists results filter "Found" | **10** (counts the 2 known controls) |
| | Map Layers panel "Found before discovery" | **7** |
| Number searched | Everywhere | **265** |
| | Map Layers panel "Searched" | **257** |
| 2025 YH5, how early | Final-results list, Scientists table | **18 days** before discovery |
| | Pop-up card on the map | "Before discovery **8 days**" |
| | About, "How Rewind works" | "photographed it on **12 days** before its discovery" |
| 2025 YH5, photo count | Scientists table | **120** |
| | About, step 2 | **81 photos** |
| P/2026 V1 | List | **13 days** before first known observation |
| | Map card | **2 days**, photo dated **12 Sep 2026**, while the timeline showed Dec 2025 |
| Benchmark | Headline | 10 of **18** |
| | "Brighter is easier" bars | denominators add up to **23** (they include the 5 not-visible objects) |
| False-alarm test | Does it work | "0 false alarms on **22** patches" |
| | Scientists | "0 false alarms in **23 real cases and 22** decoys" |

The map card most likely shows the frame at the current timeline date, not the earliest frame. If so, label it ("This photo: 8 days before discovery · earliest: 18 days").

### H3. C/2025 W2 is labelled FOUND but wasn't seen early
It's listed as FOUND under "found in older photos", but its own line says "not before the first known observation". That contradicts the headline claim. Give it a separate badge ("Seen, not earlier") or leave it out of "found".

### H4. The team name "Team SpaceX" (About)
Next to NASA branding this reads as a link to SpaceX the company, and it puts a real company's trademark on the site. Rename it, or at least make it clearly a pun.

### H5. "Five stars NASA picked to test Rewind" (Challenge stars)
NASA picked these as challenge targets, not to test Rewind. Suggested: "The five stars named in the NASA challenge. Tap one."

### H6. The hover tooltip covers the pinned planet card (Home map)
Click a planet (e.g. Venus) and its card stays pinned. Then hover a nearby asteroid (e.g. 2026 BA8): its tooltip opens on top of the planet card and hides the card's text.
- **Cause (from the live bundle):** the map places the hover tooltip (`pickEl`, `.pk-*` content) and the pinned planet card (`pinEl`, `.planet-card`) with separate `place(el, target)` calls. Each one is put next to its own dot, and nothing checks whether the two boxes overlap.
- **Fix:** after placing both, compare their `getBoundingClientRect()`. If they overlap, first try placing the tooltip on the other side of its dot (above or to the left). If they still overlap, fade the pinned card (`opacity: 0.25; pointer-events: none`) until the tooltip goes away. Never let the tooltip sit on top of the card at full opacity.
- **Simpler fallback:** hide the hover tooltip for objects whose dot is under the pinned card. You can't usefully hover something hidden behind a card anyway.

### H1 cause, confirmed
In the live bundle, the object panel header uses `<div class="op-title">` (with `.op-title{display:flex; gap:12px; margin-right:44px}`). The home headline uses the same class name, `h1.op-title`, so the panel's flex rule also applies to the headline. Rename the panel class (e.g. `.pn-title`) and the hero headline is fixed on desktop and mobile.

### M1. A tour caption is hidden behind the detail panel (Home tour)
"Watch for the flash: SPHEREx saw it before a…" runs under the right-hand object card and gets cut off. Keep tour captions inside the space the panels leave free, or shift them left while the card is open.

### M2. Clicking Barnard's Star opens the Sun (Challenge stars)
Barnard's Star sits next to the Sun at the default zoom, and the Sun's click area wins. Make click areas smaller than the gap between stars, or pick the nearest star to the pointer. The Sun panel then shows a large empty area and a giant Sun sphere cut off by the panel.

### M3. Text slides under the header with no background (all inner pages)
On scroll, page text shows through behind the logo and search bar (seen on Sky, Games and Scientists). On Scientists, the sticky section tabs also sit over the big "10 of 18" numbers. Give the header and the sticky tabs a solid or blurred background.

### M4. A developer spec is printed on the public Scientists page (Data contract section)
Lines like *"Include every NEO… Keep the file under about 8 MB (round values sensibly)"* and `"plain": "2-4 short sentences"` are instructions to whoever builds the file. They read like a prompt. Either rewrite them as a description ("orbits.json holds every NEO, every comet and a random sample of main-belt asteroids, about 100k rows") or link to DATA-CONTRACT.md and remove the inline copy.

### M5. Orbit-impact table row breaks (Scientists)
The P/2025 Y2 note "fit did not converge: unreliable" wraps onto its own row and pushes "×1.30" into the wrong column. Put the note in a footnote, or use a dash plus a tooltip.

---

## 2. Design improvements

1. **Does it work: the result is hidden behind hover.** 23 near-identical orbit thumbnails, with the actual result only on hover. Show the key fact on each card face, e.g. "0.1″ off · S/N 120". Hover doesn't exist on phones.
2. **Does it work: the cards show unlabelled numbers.** "Rewind, blind 119.7 / True spot 126.2" don't say what they are. Label them "S/N, Rewind blind" and "S/N at true position" (the "First test" list already says "S/N").
3. **Sky: two placeholder thumbnails.** "North deep field" and "South deep field" use drawn dots while the other five cards use real photos. Both also have the same caption, "Photographed again and again". Use real stamps and different captions.
4. **Sky: the "Patch width 60″ 120″…" control** doesn't explain its unit. Add "(arcsec)" or show the size in pixels ("120″ ≈ 20 px").
5. **Games:** the cards fill about 75% of the width and leave a dead column at 1024 px. Make them full width, or put them in a 3-across row. The URL is `#/detectives` while the page is called "Games", and the downloads list says "Detectives game". Pick one name.
6. **Games, Tune the Rewind:** the compass has E on the left and W on the right. That's correct for the sky, but players will think it's a bug. Add a small note: "Sky view: east is left".
7. **Challenge stars:** two headings stacked ("Challenge stars" plus "Five stars NASA picked…" in large type). Keep one. "R Dra 400 pc" is clipped at the top edge of the map. Red dwarf and pulsating red giant use nearly the same red, so pick a clearly different colour for one of them.
8. **Home map:** the asteroid belt shows as a bright band above the Sun with no matching lower half, so it looks lopsided rather than like a ring. Check that the main-belt sample isn't limited to one longitude range. Planet labels also disappear on mobile.
9. **Scientists results table:** object names wrap ("2025 / WC14"). Give the first column `white-space: nowrap`.
10. **Every inner page has the same top:** back link, then an orange mono kicker, then a large H1. That's fine once. On every page it reads like a template. Consider dropping the kicker on 2 or 3 of the pages.
11. **Search placeholder** is cut off on mobile ("Search an asteroid o"). Use "Search objects" on small screens.

---

## 3. Copy that sounds AI-written (with replacements)

| Where | Now | Suggested |
|---|---|---|
| Home final results | "Rewind tells you honestly when an object is too faint." | "If an object is too faint to see, Rewind says so instead of guessing." |
| Does it work | Section title "The AI, honestly" | "Where we used machine learning" |
| Scientists, Orbit impact | "Rewind's value is speed." | "Old photos help most in the first days after discovery." |
| About, step 2 | "The dot adds up; the noise does not." | "Added along the asteroid's path, its faint light builds up while random noise averages out." |
| About, step 3 | "Earlier positions make where it goes next less of a guess." | "Each earlier position narrows down where it will be next year." |
| About, step 1 | "SPHEREx photographed it on 12 days before its discovery" | "SPHEREx photographed it on 12 different days, starting 18 days before its discovery." (check the numbers) |
| Games card 3 | "See old photos shrink the doubt." | "Then see how old photos narrow it down." |
| Games intro | "Each one is a job Rewind does for real." | "Each game is one step of the real pipeline." |
| Sky kicker | "SPHEREX TIME MACHINE" | "Any spot in the sky" (or drop the kicker) |
| Sky | "I'M FEELING LUCKY" (Google's phrase) | "Random spot" |
| Map hint | "TAP A GLOWING DOT TO OPEN AN ASTEROID" | "Click a glowing dot to open it" (it can also be a comet, and "tap" is wrong on desktop) |
| Challenge stars | "Click the map to zoom with the wheel" | "Scroll to zoom" |
| Does it work, 7 hint cards | "Rewind saw a signal but did not call it a find: …" (repeated 7 times) | Say the rule once above the grid; each card then gives only the reason ("Sky behind it too busy to clean") |
| Does it work, 5 cards | "…so there is no false alarm." (repeated 5 times) | Say it once in the legend |
| Scientists, "How the test was run" | "missed excludes hints. Frames listed with MOST (full orbit)." | Starts lowercase and uses jargon. "'Missed' doesn't count hints. Frame lists come from the MOST service using the full orbit." |
| Stars, Sun panel | "8.3 light-minutes from the Earth" | "from Earth" |

Keep "Every discovery has a past." It's a good line. The AI-use section on About is honest and specific, so keep that too.

**Check:** About lists DASCH glass plates, the DSS, 2MASS, Gaia, WISE and AAVSO as data sources. If the live site doesn't use them, remove them, because judges may ask where they appear. The same goes for the "SAMPLE DATA" legend: if no sample data is shown anywhere, remove the legend.

---

## 4. Quick wins (each under 30 minutes)
1. Fix the hero flex bug (H1). One CSS change fixes both desktop and mobile.
2. Make the found and searched counts the same everywhere (H2), and label the map card's "days before" as this photo versus earliest.
3. Give the header and the sticky tabs a background (M3).
4. Rewrite the 5 or 6 slop lines in section 3 and the Data contract spec text (M4).
5. Rename "Team SpaceX" and correct "NASA picked to test Rewind" (H4, H5).

*Note: the browser pane was hidden during part of this review, so how long the page fade-ins take wasn't measured reliably and isn't counted as a finding.*
