# Team SpaceX - NASA Space Apps 2026 research pack: Planet X and SPHEREx

Compiled Sat Nov 14 2026 from 21 research agents, all read-only, plus spot checks of key sources. Every claim in the agent reports carries a link and a label:
- **VERIFIED:** the source was read.
- **UNVERIFIED:** the claim is second-hand or an inference.
- **MEASURED:** the agent ran its own query or test.

Read the summary first. The full reports follow in Parts 1-21, and the appendix lists the 114 rival teams that have project text.

**What this pack is not:** it does not pick our project idea. The Space Apps rules say "SI should not be used to (come up with your idea of how to solve the challenge)", so the idea has to be ours. This pack is facts only: what NASA wants, what wins, what exists, what the data can do and what is still open.

---

## 1. Snapshot

| Item | Fact |
|-|-|
| Team | Team SpaceX: Dovlet Gurbanov (team owner) and Rahman Bazarov |
| Challenge | Planet X and SPHEREx: https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/ |
| Local event | Cleveland, OH. Fully online (Discord + Google Meet), US/Eastern time |
| Submission deadline | **Sun Nov 15, 11:59 PM Eastern (9:59 PM Arizona)** |
| Demo limit | 30-second video OR at most 7 slides (title and intro count). Going over means no global judging |
| Judging | Impact, Creativity, Validity, Relevance, Presentation, each scored 1-5 |
| Rule: one challenge | "teams are only permitted to work on one challenge" (Participant FAQs). Ideas or data from other challenges can be used, but the project must answer this one |
| Rule: AI ("SI") | AI tools are allowed but must be disclosed. AI images and video need a visible watermark. No NASA logos in generated content. The idea must be ours |
| Rule: NASA data | At least one NASA data source is required, and every data source and tool used must be listed |
| Results dates | Global Nominees Dec 3, Finalists Dec 17, Winners Jan 26 2027 |

**To do now:**
1. Both of us log in and confirm we are **accepted, not waitlisted**, for the Cleveland event. Waitlisted members make the project ineligible for awards.
2. Ask the Local Lead (bxbi442@gmail.com or the event Discord) whether there is a live pitch and when local judging happens.

---

## 2. The challenge in one paragraph

SPHEREx is a NASA telescope that maps the whole sky every ~6 months in 102 near-infrared colors (0.75-5 microns).

The challenge asks for a public web tool that does the following:
- You type sky coordinates (RA/Dec) and get a "little video" of that patch over time, so anyone can spot moving objects: brown dwarfs, asteroids, comets, maybe new planets. This is the WiseView / Backyard Worlds model.
- It must be tested on Barnard's Star, Epsilon Indi B, WISE 0855, RW Aurigae and R Draconis.

Extra credit:
- spectra on the fly ("extra kudos")
- adding or subtracting dates
- user-chosen field of view
- Gaia and WISE overlays
- URL queries and embeds
- contamination flags
- easy updates as new data arrives

---

## 3. Key takeaways across all 21 agents

**A. "Show and blink" is the regular, crowded thing.**
- 1,380 teams registered for this challenge. 114 have written project text so far.
- Most build: coordinates in, then IRSA cutouts, then blink or time slider, then a 102-band selector plus Gaia/WISE overlay plus a chatbot.
- Keyword counts: movers 67, blink 47, 102-band 47, AI 39, chatbot 23, game 15.
- The strongest visible rival, Team Oblivion's "SPHEREx Explorer", is already live with blink, subtraction, a JPL asteroid check, CatWISE overlays, a game, a Bangla version and an assistant.
- NASA's archive (IRSA) already offers a moving-object search (MOST), spectrophotometry, mosaic, cutout and source-discovery tools.

**B. What wins, and what NASA staff and judges want.**
- About 24 of the 30 global winners from 2023-2025 were working software.
- Winners add **one real science layer and prove it is trustworthy**. Two examples:
  - 2024: a 3D asteroid-map team won Best Use of Science by adding meteoroid streams.
  - 2025: an exoplanet team won Best Use of Data with physics checks against false positives.
- Judges punish "just an app that shows NASA data". Creativity scores 5 only for an approach "never attempted before". Relevance tops out around 3 if NASA data is only supplementary.
- NASA AI staff want a human in the loop, traceable outputs and "trust but verify". IRSA's own user panel says its tools are "clunkier than competitors" and asks for better time-domain access and student onboarding.

**C. SPHEREx science facts that change everything.**
- **Each frame sees each sky spot in a different color** (linear variable filter, LVF). Naive blinking makes stars flicker for no real reason. This is the main scientific trap.
- **The test targets move less than 1 pixel per 6 months** (pixel = 6.15").

| Target | Movement over 6 / 12 / 18 months (pixels) | Notes |
|-|-|-|
| Barnard's Star | 0.85 / 1.69 / 2.54 | Saturated |
| WISE 0855 | 0.66 / 1.33 / 1.99 | Visible only at 3.9-5 microns |
| Eps Indi B | 0.38 / 0.76 / 1.14 | The pair blends into one dot |
| RW Aur, R Dra | No motion | Brightness changes only |

- **Planet Nine is out of reach** (too faint). The realistic "Planet X"-type finds are cold, nearby brown dwarfs, plus asteroids and comets.
- **SPHEREx's unique edge is a 0.75-5 micron spectrum for every object, at several dates.** It tells a brown dwarf (water and methane dips) from an asteroid (reflected sunlight) from a comet (CO2 glow).
- **Data facts:**
  - Pole fields have 58-80 visits so far; the equator has about 3 seasons.
  - The all-sky 102-channel cube has no time axis.
  - The S3 bucket and HiPS tiles can be called from a browser. SIA, TAP and cutouts need a small proxy.
- **Artifacts can fake movers:** persistence, crosstalk copies, ghosts, satellite streaks. A real mover must move unlike the rest of the field and show up in 3 or more frames.

**D. Open gaps (nobody covers, or scientists say is unsolved).**

| Gap | Rival teams doing it |
|-|-|
| Stacking along a motion path (shift-and-stack) on SPHEREx | 0 |
| Searching along hypothetical Planet X orbits | 0 |
| Public "precovery" in older images | 0 |
| How the same object's spectrum changes between dates | ~1 |
| Classifying movers by their spectrum | ~1 |
| Using the LVF color shift as signal rather than noise | 0 rivals, no paper found |
| Pixel-level deep learning or generative "expected sky" models on SPHEREx | none found. The challenge's likely author group (Meisner, Caselden, Kirkpatrick, Schneider, Faherty, Kuchner) wrote in Jul 2026 that pixel-level deep learning shows "potential ... to discover astronomical moving objects that challenge traditional data analysis approaches" (SMDET-1, arXiv 2608.00046) |

Scientist-stated problems with no tool:
- coldest Y dwarfs hidden in crowded Galactic-plane fields
- 865 "possibly peculiar" plus ~1,069 under-observed brown dwarf candidates with no triage workflow
- 102,000 volunteer submissions checked by hand, with no duplicate check
- distorted moving-object spectra
- no public comet-spectrum tool

The 2026 CCC "AI and citizen science" report (promoted by Kuchner) asks for explainable AI, visible uncertainty, human-AI anomaly hunting and real-time volunteer feedback.

**E. Who the users are.**
- Backyard Worlds has ~83,000 registered users, but about 360 power users do most of the work.
- Volunteers bounce between 4-6 tools per candidate: flipbook, SIMBAD, VizieR, Gaia, WiseView, Finder Chart, submission form.
- Their stated requests:
  - skip a bad frame
  - click to get coordinates
  - a back-and-forth loop
  - resizable images
  - using SPHEREx spectra as "free follow-up"
- The most famous find ("The Accident") was missed by the algorithm and caught by a human.
- Volunteers are wary of bot-like surveys from hackathon teams. Do not spam them.

**F. Official guidance on data.**
- The NASA SME on the Space Apps GitHub forum (discussion #2165) and "dancaselden" (Dan Caselden built WiseView; he is likely on the challenge team, unconfirmed) both say **real multi-date SPHEREx data is required**, using small cutouts.
- Caselden: "I could imagine, f/e, adding synthetic faint, high proper motion objects to real data for demo purposes". Synthetic injected objects are fine if clearly labeled.

**G. Outside view.**
- The public loves SPHEREx pictures but ignores the science posts.
- "Planet X" pulls attention but drags in Nibiru conspiracy baggage.
- People trust "machine filters, human discovers". "AI finds planets" draws "AI slop" pushback, and the US "Super Intelligence" rename is widely mocked.

**H. Useful hooks.**
- Arizona State is listed as a SPHEREx contributing institution.
- ASU's Adam Schneider used WiseView to confirm brown dwarfs (whether he is still at ASU is unverified).
- SPHEREx DR1 came out Nov 12 2026, two days before the hackathon, so it is brand-new data.

---

## 4. What's in this pack

| Part | Agent | Topic |
|-|-|-|
| 1 | NASA official | SPHEREx goals, data releases, NASA priorities, judging rules, SI rule |
| 2 | NASA people | Administrator, science head, SPHEREx team, Kuchner: quotes |
| 3 | Past winners | 2023-2025 global winners and patterns |
| 4 | Cleveland event | Deadline, format, judges, team page status |
| 5 | Citizen science users | How volunteers discover, their requests |
| 6 | Outside view | Public, press, Reddit, Hacker News opinions |
| 7 | Builder community | Winner and judge tips, red flags |
| 8 | X and YouTube | Live rival posts, winning demo breakdowns |
| 9 | NASA employees | Working staff, how NASA adopts tools, pain points |
| 10 | Why NASA runs Space Apps | Program goals, SME forum answers on this challenge |
| 11 | The challenge, deeply | Plain-language science, SPHEREx vs WISE |
| 12 | Scientists' wish list | Unsolved problems from 2024-2026 papers |
| 13 | Competition scan | 114 teams, existing tools, feature matrix, gaps |
| 14 | Other surveys | Rubin, NEOWISE, Gaia, Euclid, Roman vs SPHEREx |
| 15 | What the data can show | File structure, services, epochs, CORS |
| 16 | Science check | Numbers for each test target |
| 17 | SPHEREx gotchas | Artifacts that fake movers, variability, spectra |
| 18 | Viewer tech | Aladin, Firefly, JS9, architecture, change-detection research |
| 19 | Auto-detection methods | Classical, ML, generative and spectral methods ranked by novelty |
| 20 | Cross-match | Gaia, CatWISE, SkyBoT, JPL; known-vs-unknown logic |
| 21 | Accessibility and sound | Sonification evidence, WCAG, global reach |
| Appendix | Competition | All 114 rival teams with project text |

**Not done yet:**
- The 2-3 project directions write-up.
- The "skeptical NASA judge" review of those directions.
- Phase 2 build agents: live data probe, code, ground-truth list, reusable code, demo outline.

---


# Part 1

## Agent 1 - What NASA officially wants (as of Nov 14 2026)

### (a) Bottom line
1. SPHEREx DR1 went public Nov 12 2026 (2 days before the hackathon): uniformly reprocessed images plus an all-sky cube in all 102 channels. QR3 images keep arriving weekly. Brand-new data, almost no public tools on top of it yet.
2. NASA is openly using SPHEREx for brown dwarfs (Oct 8 2026 release: "thousands" being analyzed) and just funded a SPHEREx citizen-science project (Rogue Worlds, Oct 28 2026). Public discovery with SPHEREx is a live NASA priority, not just a hackathon idea.
3. Agency money and attention go to Moon base, Artemis, Mars, nuclear power and the commercial economy. Astrophysics faced a proposed 65% cut in the FY27 request; Congress is pushing back. "Science per dollar" and open data are the framing that survives.
4. AI is officially "Super Intelligence (SI)" under EO 14434 (Sep 29 2026). NASA adopted it fast. Space Apps uses "SI" too: SI tools are allowed, but not for coming up with the solution idea, and SI-made images/video need a visible watermark.
5. Judging rewards real NASA data used as the core (Relevance), a working usable tool (Validity), and a strong story. The demo is 30 s video or 7 slides max - going over that makes a project ineligible.

### (b) Findings
| Topic | Finding | Source | Date | Verified? |
|-|-|-|-|-|
| SPHEREx goals | Inflation physics via 3D galaxy distribution, history of galactic light, water and biogenic ices in star/planet formation; community expected to mine data for other topics | https://caltech-ipac.github.io/spherex-archive-documentation | Sep 28 2026 | VERIFIED (search excerpt of official guide) |
| DR1 | DR1 released at IRSA: reprocessed QR2 images, meant to be used with QR3 as one uniform set, plus Spectral All-Sky Cube in 102 channels; access via astroquery, SIA, AWS S3; tutorials incl. cutouts, HiPS cubes, "Source Discovery Tool" | https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html and https://spherex.caltech.edu/news/spherex-data-release-1-dr1-is-now-available-at-irsa | Nov 12 2026 | VERIFIED |
| Release timeline | QR1 Jul 2025 (retired Feb 2026), QR2 Oct 2025, QR3 Sep 2026 (better PSF/photometry), DR1 Nov 2026. QR2 no longer returned in searches after DR1, downloadable until Feb 2027. Caution combining QR2 and QR3 | https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_qr.html | page current Nov 2026 | VERIFIED (excerpt) |
| Future products | Source catalog Aug 2027; second-year reprocessed images and cube Dec 2027 | https://spherex.caltech.edu/page/data-products | n/a | UNVERIFIED (snippet) |
| Public data policy | Data public within 60 days; four all-sky maps over 2-year mission; NASA frames this under open science (Office of Chief Science Data Officer) | https://science.nasa.gov/open-science/spherex-universe-map | Jul 2 2025 | VERIFIED |
| Moving objects tool | IRSA already has MOST (Moving Object Search Tool) that finds SPHEREx images covering a solar system object's predicted path; also a Spectrophotometry Tool and 3I/ATLAS comet images | https://irsa.ipac.caltech.edu/Missions/spherex.html | n/a | UNVERIFIED (snippet of official page) |
| Brown dwarfs | SPHEREx "finding thousands of brown dwarfs"; paper on 37 shows water, CO2, CO, methane; Kirkpatrick: "thousands more that we are in the process of analyzing"; brown dwarfs are "something of a side project" | https://www.nasa.gov/missions/spherex/nasas-spherex-telescope-sees-menagerie-of-brown-dwarfs | Oct 8 2026 | VERIFIED |
| Comet | SPHEREx observed interstellar comet 3I/ATLAS Dec 2025 | https://spherex.caltech.edu/news/spherex-data-release-1-dr1-is-now-available-at-irsa | Feb 4 2026 item | VERIFIED (listing) |
| SPHEREx citizen science | NASA selected "The Rogue Worlds Project" (PI Jacqueline Faherty, AMNH) to have volunteers search SPHEREx for free-floating planets and brown dwarfs in young clusters; also a moving-small-body telescope network (SETI). Page says volunteers use SI to build their own data tools | https://science.nasa.gov/get-involved/citizen-science/nasa-selects-19-new-citizen-science-proposals-in-2026/ | Oct 28 2026 | VERIFIED |
| Backyard Worlds | NASA project; volunteers have about doubled known brown dwarfs (3,000+ in ~10 years), uses WISE images | https://science.nasa.gov/get-involved/citizen-science/nasa-volunteers-double-known-population-of-brown-dwarfs | May 5 2026 | UNVERIFIED (snippet) |
| SI order | EO 14434: executive branch uses "Super Intelligence"/"SI" instead of AI in communications, websites, reports; definition unchanged (15 USC 9401(3)); APST to propose legal definition in 60 days | https://www.whitehouse.gov/presidential-actions/2026/09/inaugurating-the-era-of-super-intelligence | Sep 29 2026 | VERIFIED (excerpt of official text) |
| NASA applying SI | 4-phase rename Oct 9 to Dec 23; no "formerly AI" wording; "machine learning", "LLM" still OK; science-publication guidance still pending; NASA says it applies SI to mission planning, autonomy, research, data analysis | https://www.space.com/technology/we-are-getting-a-lot-of-pressure-from-the-administrator-himself-how-nasa-is-racing-to-obey-trumps-super-intelligence-order | Oct 16 2026 | VERIFIED (secondary, based on internal doc) |
| Agency priorities | Isaacman: Artemis, Moon Base, Space Reactor Office/nuclear, orbital economy, "more missions of science and discovery"; SMD to "accelerate the delivery of science", consolidate old missions, use commercial data | https://www.nasa.gov/blogs/workforce-updates/2026/05/22/a-message-from-administrator-jared-isaacman/ | May 22 2026 | VERIFIED |
| FY27 budget | Request $18.8B; Astrophysics $552.4M (65% cut vs FY26 $1.595B); SPHEREx ops kept with reduced funding; STEM Engagement zeroed | https://aas.org/posts/news/2026/04/fy27-presidents-budget-request-nasa-nsf-and-doe-details ; https://www.nasa.gov/wp-content/uploads/2026/04/fiscal-year-2027-full-budget-request.pdf | Apr 2026 | UNVERIFIED (snippets) |
| Congress | Senate CJS bill: NASA +1.7%, SMD +2.5%, rejects termination of 53 missions | https://www.planetary.org/save-nasa-science | Nov 13 2026 | UNVERIFIED (snippet) |
| Space Apps theme | "The Next Frontier": tools that benefit humanity and propel us "to the Moon, Mars, and beyond"; NASA lists three focus areas incl. "expanding understanding of the universe" | https://science.nasa.gov/universe/nasa-welcomes-all-ages-experience-levels-for-space-apps-challenge/ | Oct 15 2026 | UNVERIFIED (snippet) |
| Judging guide | 1-5 on Impact, Creativity, Validity, Relevance (NASA data "core component rather than a superficial addition"), Presentation; guide says give presentation equal attention. Nominees Dec 3, finalists Dec 17, winners Jan 26 2027. Storytelling award = "creatively communicates the potential of open data" | https://www.spaceappschallenge.org/resources/judging-awards-guide/ | Nov 13 2026 | VERIFIED |
| Eligibility | Submit by Nov 15 11:59 PM local; demo 7 slides or 30 s video; English; list all external resources in References; China bilateral review | same | Nov 13 2026 | VERIFIED |
| SI rule | SI tools allowed "to accelerate innovation and creativity"; "SI should not be used to (come up with your idea...)"; SI images/video need visible watermark, code/data need acknowledgment; no NASA branding in generated content; judges see SI indicators | https://www.spaceappschallenge.org/resources/project-submission-guide/ | read Nov 14 2026 | VERIFIED |
| Challenge text | Test targets: Barnard's Star, Epsilon Indi B, WISE 0855, RW Aurigae, R Draconis; "help as many people as possible pitch in to make discoveries"; design for easy updates with new releases | https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/ | read Nov 14 2026 | VERIFIED |

### (c) What this means for choosing a project
- DR1 plus QR3 is the newest official data, and the docs say to treat them as one uniform set and be careful mixing in QR2. A tool built on DR1/QR3 matches "easy to update with latest releases" and looks current to judges.
- NASA already has MOST (known-orbit lookup) and a spectrophotometry tool. Duplicating them scores low on Creativity; building on or linking to them can raise Validity.
- Brown dwarfs and volunteer discovery are NASA's own current SPHEREx story (Oct 8 release, Oct 28 Rogue Worlds funding). Work that fits that thread supports Impact and Relevance, and gives a ready storytelling hook.
- Astrophysics budgets are under pressure; "more science per dollar" and "anyone can help" framing lines up with stated leadership language.
- Any machine-learning part should be called "SI" in the submission, any generated visuals watermarked, and the core idea must be the team's own. Keep a short written note of who came up with the idea.
- The 30 s / 7-slide hard limit means the "not ordinary" element must be visible in a few seconds of demo.

### (d) Open questions
- Exact DR1 cadence per sky position (how many epochs per point by now) - check the Explanatory Supplement.
- Whether the challenge Resources tab (released Nov 13) adds specific endpoints or sample notebooks - not read here.
- Is Rogue Worlds live yet, or only selected? (Page says "will invite you".)
- Final FY27 astrophysics funding is unresolved (House and Senate bills differ from the request).
- NASA guidance on "SI" wording in science publications is still listed as forthcoming.


---


# Part 2

## Agent 2 - What key NASA and SPHEREx people are saying (2025-2026)

Read-only research, done Nov 14 2026. No posts, likes, follows or account changes. X was used for 2 read-only searches (no throttling). LinkedIn was not opened (I only saw a search snippet). Bluesky public API was used for Kuchner's feed.

### (a) Bottom line

1. Leadership is pushing "faster to science", AI ("Super Intelligence", the Genesis Mission) and commercial use. Isaacman (Administrator) and Fox (SMD) both use this framing in 2026.
2. Astrophysics (Domagal-Goldman) and the SPHEREx team keep saying the same thing: the data is free and public, and "every astronomer is going to find something of value". The public archive is the point.
3. SPHEREx's solar-system and brown-dwarf work is real and recent: 3I/ATLAS comet spectra (Aug and Dec 2025), a brown-dwarf "menagerie" (Oct 8 2026), and 945 new ultracool dwarfs from Quick Release 2. The team says thousands of brown dwarfs are still being analyzed.
4. The Backyard Worlds people (Kuchner, Schneider, Caselden) say AI plus humans works better than either alone. Machine learning picks candidates, and volunteers confirm them. Kuchner has promoted Space Apps and an AI plus citizen science report in 2026.
5. Who wrote the challenge: UNCONFIRMED. The challenge page names no author. Its text and resources (backyardworlds.org, WiseView, flipbook "blinking", the Pluto story) look like the Backyard Worlds team's style, but I found no proof that Kuchner wrote it.

### (b) People table

| Person | Role (verified date) | What they said (Q = exact quote, P = paraphrase) | Link | Date | Verified? |
|-|-|-|-|-|-|
| Jared Isaacman | NASA Administrator (nasa.gov org page and Nov 7 2026 release) | Q: "The Genesis Mission is an opportunity to turn that foundation into faster science, stronger engineering, and better mission outcomes... NASA can advance AI tools that accelerate exploration" | nasa.gov/news-release/nasa-joins-genesis-mission-to-accelerate-ai-driven-discovery | Jul 22 2026 | VERIFIED |
| Isaacman | same | P (bullet in his message): "prioritize high 'commercial potential' science". He also wants to free up money for "challenging flagship missions that only NASA is capable of undertaking" | nasa.gov/blogs/workforce-updates/2026/05/22/a-message-from-administrator-jared-isaacman | May 22 2026 | VERIFIED |
| Isaacman | same | P: says science is about a third of NASA's budget, and NASA should use commercial industry where NASA is "one customer of many". All-In podcast | podscripts.co (All-In transcript) | Sep 2026 | VERIFIED (transcript) |
| Isaacman and NASA SMD | same | P: the Golden Age summit set up an SMD metascience initiative (reliability, transparency), more dual-anonymous review, and 10 Genesis Mission Fellows in "super intelligence (SI)" plus science | nasa.gov/news-release/nasa-announces-bold-science-initiatives-for-americas-golden-age-summit | Oct 8 2026 | VERIFIED |
| Nicky Fox | SMD Associate Administrator (letter signed Oct 22 2026; Isaacman May 2026 confirms) | Q: "The entire agency is accelerating... our challenge is always getting more science to space quicker." (AAS von Braun Symposium) | astronautical.org/2026/11/02/nasas-nicola-fox-more-science-to-space-quicker | Oct 28 2026 | VERIFIED |
| Fox | same | Q (Space Apps 2026): "At NASA, science is for everyone... students from around the world can use NASA's powerful data sets to help us build the ultimate interplanetary survival guide" | science.nasa.gov/universe/nasa-welcomes-all-ages-experience-levels-for-space-apps-challenge | Oct 15 2026 | VERIFIED |
| Fox | same | P: "Faster to Science" letter. The Administrator directed SMD to speed up science delivery, so it introduced Competition Model 2.0 (up to 45 percent faster selection) | science.nasa.gov/directorates/smd/faster-to-science-a-letter-to-the-science-community | Oct 22 2026 | VERIFIED |
| Shawn Domagal-Goldman | Astrophysics Division Director (SMD org chart Feb 2026; PRIMA release Sep 23 2026; the staff bio page still says "Acting") | Q: "We essentially have 102 new maps of the entire sky... I think every astronomer is going to find something of value here" | nasa.gov/missions/spherex/nasas-spherex-observatory-completes-first-cosmic-map-like-no-other | Dec 18 2025 | VERIFIED |
| Jamie Bock | SPHEREx PI, Caltech/JPL (Oct 8 2026 JPL release) | Q: "More than 11 months after launch, our process of discovery is just beginning... early results on the distribution of water in the form of ice, and observations of an interstellar object... 3I-ATLAS" | dvidshub.net/news/567473 | ~Feb-Mar 2026 | VERIFIED (secondary source) |
| Bock | same | Q: "Despite its modest size, SPHEREx addresses some of the most fundamental questions in science" (on receiving NASA's Exceptional Scientific Achievement Medal) | gps.caltech.edu/news-and-events/news/teams-from-caltech-jpl-honored-by-nasa | Sep 28 2026 | VERIFIED |
| Bock | same | P (2024 talk): the catalog will include brown dwarfs, asteroids and comets, with public release within 2 months | pswscience.org/meeting/2514 | 2024 | VERIFIED (summary, not a quote) |
| Olivier Dore | SPHEREx Project Scientist (Oct 8 2026 release; Caltech project page) | No direct 2025-2026 quote found | spherex.caltech.edu/page/project-office | - | Role VERIFIED |
| Beth Fabinsky | SPHEREx Project Manager, JPL (Dec 2025 release) | Q: "The superpower of SPHEREx is that it captures the whole sky in 102 colors about every six months... the mantis shrimp of telescopes" | same Dec 18 2025 link | Dec 18 2025 | VERIFIED |
| J. Davy Kirkpatrick | IPAC scientist, SPHEREx brown-dwarf coauthor (Oct 8 2026) | Q: "we have thousands more that we are in the process of analyzing." Q: "The findings are a call to action to explore even more of these dark worlds" | jpl.nasa.gov/news/nasas-spherex-telescope-sees-menagerie-of-brown-dwarfs | Oct 8 2026 | VERIFIED |
| Zafar Rustamkulov | IPAC scientist, lead author (Oct 8 2026) | Q: "No two brown dwarfs are alike. Even at the same temperature, their spectra look quite distinct." | same | Oct 8 2026 | VERIFIED |
| Rachel Akeson | IPAC (exact role not re-checked) | Q: "By making the data public, we enable the whole astronomy community to use SPHEREx data to work on all these other areas of science" | jpl.nasa.gov/news/how-nasas-spherex-mission-will-share-its-all-sky-map-with-the-world | Jul 2 2025 | Quote VERIFIED, role UNVERIFIED |
| Carey Lisse | SPHEREx solar-system science, JHU/APL (team page Nov 2025) | P (LPSC 2026 abstract): every solar-system object is caught in 3-4 epochs and hundreds of images, so a lot of work remains to turn millions of images into clean spectra | hou.usra.edu/meetings/lpsc2026/pdf/1833.pdf | Jan 2026 | VERIFIED (paraphrase) |
| Marc Kuchner | SMD Citizen Science Officer (URI release Nov 9 2026); Backyard Worlds founder | Q (Bluesky): "Amateurs have now discovered half of the known brown dwarfs." Q: the CCC AI and citizen-science report "highlights the need to improve how #AI provides feedback to its human partners for mutual learning." Q: "Registration for NASA's space apps challenge opens up tomorrow!" | bsky.app/profile/marckuchner.bsky.social | May 7, Mar 3, Aug 25 2026 | VERIFIED |
| Kuchner | same | Q: "There are science projects that you can't do without the help of a big team" | science.nasa.gov/get-involved/citizen-science/how-to-contribute-to-citizen-science-with-nasa | Apr 29 2025 | VERIFIED |
| Kuchner | same | P (X, Jun 1 2025): warned that the proposed budget would end missions that supply citizen-science data and would pause Science Activation | x.com/marckuchner/status/1929286961182708220 | Jun 1 2025 | VERIFIED |
| Adam Schneider | USNO astronomer, lead author of the Backyard Worlds 3,006 L/T dwarf paper (May 2026) | P (SETI Live recap): the future is not humans versus AI. Backyard Worlds: Cool Neighbors uses ML to pre-select candidates, and volunteers vet them | seti.org/news/not-planets-not-stars | Jun 12 2026 | VERIFIED (recap, not his own words) |
| Dan Caselden | WiseView creator; built the Cool Neighbors ML | P: his ML pre-selection gave about 3x more classifications in 6 months than Planet 9 | news.medill.northwestern.edu (Zooniverse AI article) | Oct 7 2025 | VERIFIED (reporter's paraphrase) |
| Jacqueline Faherty | AMNH; PI of the new "Rogue Worlds Project" | P: a new NASA citizen-science project will have volunteers search SPHEREx data for free-floating planets and brown dwarfs in young clusters | science.nasa.gov/.../nasa-selects-19-new-citizen-science-proposals-in-2026 | Oct 28 2026 | VERIFIED |
| Karen St. Germain | Earth Science Division Director (Feb 2026 org chart) | Q: "The Space Apps Challenge puts NASA's free and open data into the hands of explorers around the world" | nasa.gov/.../nasa-announces-2025-international-space-apps-challenge-global-winners | Dec 18 2025 | VERIFIED |
| Keith Gaddis | Space Apps program scientist, NASA HQ (as of Jan 2025; current 2026 role not checked) | Q: winners "reflect our commitment to understanding our planet and exploring beyond, with the potential to transform Earth and space science" | nasa.gov/.../2024-global-winners | Jan 16 2025 | Quote VERIFIED, 2026 role UNVERIFIED |
| Aleodor Tabarcea | Bucharest local judge (Stripe), not NASA | Q: "I'm not looking for the most polished pitch... teams that start with a problem, test their ideas against real data... it's the data that turns it into a solution" | business-review.eu (Nov 5 2026) | Nov 5 2026 | VERIFIED (local judge only) |

### (c) Themes they keep repeating

- Open data has to be usable by everyone. Fox ("science is for everyone"), Domagal-Goldman ("every astronomer"), Akeson and St. Germain all say this.
- Speed and scale. "Faster to science", 3,600 images a day, and "too much data for any one person or even computer code" (the challenge text).
- AI plus humans, not AI alone. The leadership talks about AI acceleration (Genesis, SI fellows). The citizen-science side (Kuchner, Schneider, Caselden) talks about ML triage with human confirmation, and better AI feedback to humans.
- Volunteers make real discoveries. Half of the known brown dwarfs were found by amateurs, and 650+ public coauthors are on NASA papers.
- SPHEREx's unique edge is spectra (102 colors). Molecules (water, CO2, CO, methane) in brown dwarfs, comets and ices are the selling point, not just positions.
- Reproducible "gold-standard science": metascience, transparency, data flags.

### (d) What this means for choosing a project (facts only, not an idea)

- Validity: a tool that shows SPHEREx metadata and flags, and works on the official test targets (Barnard's Star, WISE 0855 and others), matches what the IPAC people care about.
- Creativity: the team's own quotes stress spectra and molecules ("No two brown dwarfs are alike"). The challenge gives "Extra kudos" for spectra generated on the fly. Positions alone are what WiseView already does.
- Impact: there is a live user base. Backyard Worlds' volunteers are waiting for new data (the Zooniverse page says it is "out of data"), and the new Rogue Worlds SPHEREx project will need volunteers. Leaders reward tools that grow participation.
- Relevance to NASA's current priorities: "AI that helps humans decide" fits both the leadership's AI push and Kuchner's stated AI-feedback concern.
- Presentation: local judges say "real data over polish", and Fox's framing is "science is for everyone".
- Upkeep: the challenge says "New SPHEREx data is arriving fast", and Lisse notes multi-epoch complexity. A tool that is easy to update fits what both say.

### (e) Gaps I could not verify

- Who wrote the challenge (Kuchner or the Backyard Worlds team): UNCONFIRMED. The page has no author line.
- The current 2026 Space Apps program lead or program scientist at NASA HQ. Gaddis is confirmed only as of Jan 2025.
- No 2025-2026 direct quotes from Olivier Dore, or from Aaron Meisner or Dan Caselden in their own words.
- Akeson's exact current title.
- Isaacman made no SPHEREx-specific or citizen-science-specific statement that I found.
- I did not read LinkedIn posts (only one search snippet) and did not use YouTube transcripts, because of the time limit. The Nov 13 2026 Space Apps judging video showed as "unavailable" in the search result.


---


# Part 3

## Agent 3 - What wins NASA Space Apps (2023-2025)

Sources: NASA winner releases for 2025 (nasa.gov, Dec 18 2025), 2024 (nasa.gov, Jan 16 2025), 2023 (science.nasa.gov, Jan 26 2024); spaceappschallenge.org finalist lists (opened in the browser); 2025 project pages (opened); Western University news (WMPGang); Asteroid Destroyer GitHub README (search snippet). 2023 and 2024 project tabs on spaceappschallenge.org now show "make sure ... you are logged in", so I could not read them; those details come from NASA releases and press.

### (a) Bottom line

1. Funnel: 5,556 (2023) / 9,996 (2024) / 11,500+ (2025) submissions, then local judges pick Global Nominees, NASA experts pick 40-45 Global Finalists, and an executive committee picks 10 winners.
2. About 24 of 30 winners were working software (mostly web apps). Only about 4-6 were concepts, stories or comics, and those won "soft" awards (Inspirational, Storytelling, Art & Tech, Local Impact).
3. Astro and planetary challenges win the "hard" awards often: Best Use of Science in 2023 (moonquakes) and 2024 (NEO orrery), Best Use of Data in 2025 (exoplanet AI) and 2023 (DSCOVR space weather), Best Use of Technology in 2023 and 2024.
4. ML/AI is named in 8 of 30 official winner blurbs. It helps but is not required. The 2024 Best Use of Science (WMPGang) had no ML.
5. The repeated winning trait is one extra science idea on top of the brief, shown live (WMPGang added meteoroid streams, Resonant Exoplanets added physics and chemistry checks to stop false positives). A standard ML pipeline in the same challenge reached finalist but did not win.

### (b) Winners table (30 of 30)

Status: VERIFIED = listed in the official NASA release I opened. "Page" = I also opened the project page.

| Yr | Award | Team | Challenge | Built (1 line) | Tech | Demo | Link | Status |
|-|-|-|-|-|-|-|-|-|
| 2025 | Science | SpaceGenes+ (1 person) | Space Biology Knowledge Engine | Dashboard of non-additive gene responses to radiation + microgravity (GeneLab OSD-288) | Web dashboard | Drive file | spaceappschallenge.org/2025/find-a-team/spacegenes/?tab=project | VERIFIED + page |
| 2025 | Data | Resonant Exoplanets | A World Away: Hunting for Exoplanets with AI | Kepler/TESS/JWST pipeline: transit detection, physics validation, exact-math biosignature checks, auto reports | ML + web | YouTube + live (resonant-planet.vercel.app) | spaceappschallenge.org/2025/find-a-team/resonant-exoplanets/?tab=project | VERIFIED + page |
| 2025 | Technology | Twisters | Will It Rain On My Parade? | SkySense, local weather risk + safest time windows | Web + AI | Not checked | spaceappschallenge.org/2025/find-a-team/twisters/?tab=project | VERIFIED |
| 2025 | Galactic Impact | Astro Sweepers | Commercializing LEO | Debris compliance platform, "credit score" risk index per object | Web/data | Not checked | spaceappschallenge.org/2025/find-a-team/astro-sweepers-we-catch-what-space-leaves-behind/?tab=project | VERIFIED |
| 2025 | Mission Concept | PureFlow | Habitat Layout Creator | 3D habitat design tested against space weather | Web 3D | Not checked | spaceappschallenge.org/2025/find-a-team/pureflow2/?tab=project | VERIFIED |
| 2025 | Most Inspirational | Photonics Odyssey | Commercializing LEO | Sovereign phased-array satellite internet for India | Concept | Not checked | spaceappschallenge.org/2025/find-a-team/photonic-force/?tab=project | VERIFIED |
| 2025 | Storytelling | HerCode Space | Stellar Stories: Space Weather | Illustrated kids story "A Solar Tale" | Story/art | Not checked | spaceappschallenge.org/2025/find-a-team/hercode-space/?tab=project | VERIFIED |
| 2025 | Global Connection | Gaia+LEO | Commercializing LEO | Optimization model for orbital + ground data centers | Modeling | Not checked | spaceappschallenge.org/2025/find-a-team/gaialeo/?tab=project | VERIFIED |
| 2025 | Art & Technology | Zumorroda-X | NASA Farm Navigators | Farmer mini games | Game | Not checked | spaceappschallenge.org/2025/find-a-team/zumorroda-x/ | VERIFIED |
| 2025 | Local Impact | QUEÑARIS | BloomWatch | Reforestation: microbes, satellite data, drones, AI | Hybrid hardware + AI | Not checked | spaceappschallenge.org/2025/find-a-team/watana-project/?tab=project | VERIFIED |
| 2024 | Science | WMPGang | Orrery Web App for NEOs | SkyShield 3D orrery, 1,669 NEOs + meteoroid streams, risk filters | Web 3D, no ML | Live app (simonvse.com/projects/neo-orrery/app/) | spaceappschallenge.org/nasa-space-apps-2024/find-a-team/wmpgang/?tab=project | VERIFIED |
| 2024 | Data | GaamaRamma | EO Data for Agriculture | Waterwise, farm water management | Web app | Not checked | spaceappschallenge.org/nasa-space-apps-2024/find-a-team/gaamaramma/?tab=project | VERIFIED |
| 2024 | Technology | 42 QuakeHeroes | Seismic Detection Across the Solar System | Deep net (U-Net per secondary source) finds quake onsets in Apollo/InSight data | ML | Not checked | spaceappschallenge.org/nasa-space-apps-2024/find-a-team/42-quakeheroes/?tab=project | VERIFIED |
| 2024 | Galactic Impact | NVS-knot | EO Data for Agriculture | 2plant, planting risk from soil moisture | Web app | Not checked | spaceappschallenge.org/nasa-space-apps-2024/find-a-team/nvs-knot/?tab=project | VERIFIED |
| 2024 | Mission Concept | AsturExplorers | Landsat Reflectance Data | Landsat Connect, track passes + notifications | Web app | Not checked | spaceappschallenge.org/nasa-space-apps-2024/find-a-team/asturexplorers/?tab=project | VERIFIED |
| 2024 | Most Inspirational | Innovisionaries | SDGs in the Classroom | Eco-Metropolis city-building game | Game | Not checked | spaceappschallenge.org/nasa-space-apps-2024/find-a-team/innovisionaries/?tab=project | VERIFIED |
| 2024 | Storytelling | TerraTales | Tell Us a Climate Story! | Climate stories for 3 regions + AI forecast + game | Web + AI + game | Not checked | spaceappschallenge.org/nasa-space-apps-2024/find-a-team/terratales/?tab=project | VERIFIED |
| 2024 | Global Connection | Asteroid Destroyer | Navigator for HWO | Speculo, 3D web map of which exoplanets HWO can characterize | Web 3D + ML | Live app per README | spaceappschallenge.org/nasa-space-apps-2024/find-a-team/asteroid-destroyer/?tab=project | VERIFIED |
| 2024 | Art & Technology | Connected Earth Museum | Imagine our Connected Earth | Virtual museum with AI host, time-series galleries | Web 3D + AI | Not checked | spaceappschallenge.org/nasa-space-apps-2024/find-a-team/connected-earth-museum/?tab=project | VERIFIED |
| 2024 | Local Impact | Team I.O. | Community Mapping | G.R.O.W. wildfire GIS made readable | Web/GIS | Not checked | spaceappschallenge.org/nasa-space-apps-2024/find-a-team/team-io/?tab=project | VERIFIED |
| 2023 | Science | LunarTech Ensemble | Make a Moonquake Map 2.0! | Website + immersive game for Apollo seismic data | Web + game | Not checked | spaceappschallenge.org/2023/find-a-team/lunartech-ensemble/?tab=project | VERIFIED |
| 2023 | Data | Storm Prophet | Develop the Oracle of DSCOVR | LSTM geomagnetic storm prediction | ML | Not checked | spaceappschallenge.org/2023/find-a-team/storm-prophet/?tab=project | VERIFIED |
| 2023 | Technology | Spacebee | Make a Moonquake Map 2.0! | Moonquake site: locations, types, ALSEP plots | Web | Not checked | spaceappschallenge.org/2023/find-a-team/spacebee/?tab=project | VERIFIED |
| 2023 | Galactic Impact | Greetings from Earth!! | Ocean Gardens | Ocean data visualization site | Web viz | Not checked | spaceappschallenge.org/2023/find-a-team/greetings-from-earth1/?tab=project | VERIFIED |
| 2023 | Mission Concept | ASTROGENESIS | Planetary Tourism Office | Personal itineraries to planets and moons | Web | Not checked | spaceappschallenge.org/2023/find-a-team/astrogenesis/?tab=project | VERIFIED |
| 2023 | Most Inspirational | Space Quest Maidens | Eclipses: Perspective is Everything | ECLIPSE: Celestial Shadows kids tool | Edu app | Not checked | spaceappschallenge.org/2023/find-a-team/space-quest-maidens-donzelas-da-missao-espacial/?tab=project | VERIFIED |
| 2023 | Storytelling | TeamVoyagers | Everything Starts with Water | Water-cycle web game | Game | Not checked | spaceappschallenge.org/2023/find-a-team/team-voyagers/?tab=project | VERIFIED |
| 2023 | Global Connection | Arcobaleno | Immersed in the Sounds of Space | Sonification of 2D/3D NASA images for blind users | Audio/web | Not checked | spaceappschallenge.org/2023/find-a-team/arcobaleno/?tab=project | VERIFIED |
| 2023 | Art & Technology | Oogway Comics | Habitable Exoplanets | Comic book about a data-based exoplanet | Comic | Not checked | spaceappschallenge.org/2023/find-a-team/oogway-comics/?tab=project | VERIFIED |
| 2023 | Local Impact | $quality_over_quantity | Biodiversity Hotspot w/ Imaging Spectroscopy | Method to prioritize hotspots | Method/analysis | Not checked | spaceappschallenge.org/2023/find-a-team/quality_over_quantity/?tab=project | VERIFIED |

Relevant astro finalists that did not win (VERIFIED on finalist lists):
- 2025 Exoplanet AI: ECI Centauri, GRIT-X Awa, NUPS, The Newtonians (plus winner Resonant). Embiggen Your Eyes (huge NASA image zoom): Vitruvian 6, The new Saraquatys. Meteor Madness: Meteor Rizzlers, TechNova.
- 2024: Exosky!: LazyVarenyky (only Exosky finalist). Orrery: aCentauri, CosmoArchitects, OrbitSpace, PhDs (plus winner WMPGang). HWO: Dark Mode. Chronicles of Exoplanet Exploration: 5 teams. JWST music: Saraquatys in G Major.
- 2023: Habitable Exoplanets: Spacezians. DSCOVR: (L)TI, TAITATUMU.
- Lists: spaceappschallenge.org/2025/awards/global-finalists/, /nasa-space-apps-2024/awards/global-finalists/, /2023/awards/global-finalists/

### (c) Deep dives

1. Resonant Exoplanets (2025 Data, page VERIFIED). Full pipeline: fetch Kepler/TESS/JWST, transit detection, physics validation, then exact-math chemistry to tell real biosignatures (O2 + CH4) from false positives; web UI with plots and auto-generated reports. Validity is the pitch ("reduces false positives"). Working tool with live Vercel link and YouTube demo.
2. GRIT-X Awa (2025 finalist, page VERIFIED). Stacked XGBoost/LightGBM/CatBoost classifier on Kepler/TESS with web UI, YouTube + Canva slides. Solid and working, but it is the standard approach. Inference: a common solution reaches finalist, a distinct science angle wins.
3. NUPS ExoHunt (2025 finalist, page VERIFIED). Citizen-science platform for amateur follow-up observations with AI help. Demo was Google Slides plus GitHub, no video seen. Strong citizen-science angle but did not win.
4. Vitruvian 6 Cosmo Scope and The new Saraquatys Eyes to the Sky (2025 Embiggen finalists, pages VERIFIED). Closest analog to a SPHEREx image viewer. Cosmo Scope: React/Three.js/MapLibre, GIBS/IIIF/PDS data, timeline slider, shared annotations, live Railway link + YouTube. Eyes to the Sky: Hubble/JWST images + music, identify-objects game across eras, live web.app + YouTube. Both gamified, both polished, neither won.
5. WMPGang SkyShield (2024 Science, Western news VERIFIED). Four physics grad students, no web experience, about 30 hours. 5 of 40 finalists built orreries; they won by adding the "overlooked" meteoroid threat using the meteoroid model NASA uses in mission planning, and showing all 1,669 NEOs at once with risk filters. A professor called it an "appealing package that's easy to use". They used ChatGPT for debugging and templates (allowed for code).
6. Asteroid Destroyer Speculo (2024 Global Connection, GitHub README via search, UNVERIFIED page). 3D web map of which exoplanets HWO could characterize, filters, live demo. Framed for global audience.
7. 42 QuakeHeroes (2024 Technology, NASA text VERIFIED, project tab gated). Deep net on decomposed signals to find quake onset in noisy Apollo/InSight data. Answered the exact NASA question (send back only useful data).
8. SpaceGenes+ (2025 Science, page VERIFIED). A dashboard, made by one person, won Best Use of Science because it surfaced a specific finding (non-additive TP53/ATM responses) from one named NASA dataset.

### (d) Patterns

Evidence-based (from the lists above):
- Working software dominates: about 24/30 winners are functioning apps, mostly web. Pure concepts (Photonics Odyssey), stories (HerCode) and comics (Oogway) won only Inspirational, Storytelling or Art & Tech.
- ML/AI named in 8/30 winner blurbs (Resonant, Twisters, QUEÑARIS, 42 QuakeHeroes, TerraTales, Asteroid Destroyer, Connected Earth Museum, Storm Prophet).
- Story, game or art elements in about 10/30.
- Astro/planetary/heliophysics challenges won Science (2023, 2024), Data (2023, 2025) and Technology (2023, 2024).
- Several finalists per challenge: winners differ from peers by one extra science layer (WMPGang meteoroids; Resonant false-positive checks).
- A dashboard is not disqualifying when it answers a precise science question (SpaceGenes+).
- 2025 pages I opened all had a demo video (YouTube) and most had a live link.

Inference (not proven):
- Generic ML classifiers and generic gamified explorers in astro challenges reached finalist but lost to more scientifically rigorous entries.
- "Validity" (explaining false positives, error handling, using NASA's own models) seems to be what separates Science/Data winners.
- No evidence found that "regular dashboards" lose as a category; the losing pattern looks more like "same as the other 4 finalists".

### (e) What this means for a SPHEREx project

- Expect several finalist-level SPHEREx viewers; a time slider over images is the baseline, not the differentiator (inference from orrery and Embiggen cases).
- Science/Data awards went to teams that showed why a detection is real (validation, false-positive handling) using real mission data and NASA-grade models.
- A working, deployed link plus a short YouTube demo is the norm among finalists and winners seen.
- Small teams can win: SpaceGenes+ was one person, WMPGang had no web experience.
- Story or art layers alone won only soft awards; in astro challenges they were finalists, not winners, in 2025.
- Rules note: WMPGang used ChatGPT for code help; the solution idea itself must come from the team.


---


# Part 4

## Agent 4 - Cleveland, OH Local Event (read-only study, Sat Nov 14 2026, checked ~12:20 PM Arizona)

### (a) Bottom line
1. Most important deadline: project submit by **Sun Nov 15, 11:59 PM Eastern = 9:59 PM Arizona** (event time zone is US/Eastern; EST is UTC-5, Arizona UTC-7, so 2 hours earlier). No earlier local deadline is set on the event page (its submissionDeadline field is empty).
2. Cleveland 2026 is **fully virtual** (Discord + Google Meet). No venue, no NASA Glenn host is named for 2026. Remote members are fine by design.
3. Posted schedule is only: Sat Nov 14 12:30 Kick Off (Google Meet), 13:00 Hacking (Eastern = 10:30 AM and 11:00 AM Arizona, both already past). No judging time, no live pitch, no awards posted.
4. Team SpaceX is listed on the Cleveland OH Teams tab (1 of 10 teams, the only one on Planet X and SPHEREx). Members tab: Dovlet Gurbanov (Team Owner) and Rahman Bazarov. Per-person accepted vs waitlisted status is not visible (browser was not logged in).
5. Global Nominees are announced Dec 3 2026. The guide does not say how many nominees each Local Event gets; Local Judges are picked by the Local Lead.

### (b) Event facts
| Item | Value | Link | Verified? |
|-|-|-|-|
| Event | Cleveland, OH (not Cleveland, MS, which is a separate event) | https://www.spaceappschallenge.org/2026/local-events/cleveland-oh/ | VERIFIED |
| Format | Virtual, "hosted entirely online"; venue "Online", Discord https://discord.gg/nKNhpxdxH | same | VERIFIED |
| Host org | Not named on 2026 page. Local Lead username bxbi442, email bxbi442@gmail.com. Same username in 2025 was named "Bobi Sofronijoski" (email bobi@internationalspacealliance.com) | 2026 page; https://www.spaceappschallenge.org/2025/local-events/cleveland-oh/ | VERIFIED (that bxbi442 = Bobi in 2026 is UNVERIFIED) |
| Time zone | US/Eastern (page data field "timezone") | 2026 page | VERIFIED |
| Schedule | Sat Nov 14: 12:30 Kick Off (https://meet.google.com/ndm-mkag-pni), 13:00 Hacking. Nothing for Sunday. Livestream URL "Not Set" | 2026 page, Schedule tab | VERIFIED |
| Local deadline | No local deadline set (field empty); global rule = Sun Nov 15 11:59 PM local event time | 2026 page data; https://www.spaceappschallenge.org/resources/judging-awards-guide/ | VERIFIED |
| Local judging time/format | Not posted | 2026 page | VERIFIED (absent) |
| Local awards / judges / mentors | Not posted for 2026 | 2026 page | VERIFIED (absent) |
| Announcements | None (alert field empty) | 2026 page | VERIFIED |
| Registration | 48 registered, virtual limit 200, waitlist 0, "Accepting Participants" | 2026 page data | VERIFIED |
| Socials | instagram.com/nasaspaceappscleveland, facebook.com/NASASpaceAppsCleveland (Facebook did not load) | 2026 page | VERIFIED links, content not read |

### (c) Team page status
- About tab: team bio (Dovlet Kent State, Rahman ASU) and challenge text. Local Event: Cleveland, OH, United States. Challenge: Planet X and SPHEREx. VERIFIED - https://www.spaceappschallenge.org/2026/find-a-team/team-spacex2/?tab=details
- Project tab: "Check back later to see this project take flight." = not submitted yet. VERIFIED
- Members tab: Dovlet Gurbanov (Team Owner, United States), Rahman Bazarov (United States). VERIFIED
- Event Teams tab shows "Team SpaceX - Seeking Members". VERIFIED
- Accepted vs waitlisted per member: not visible to a logged-out reader. UNVERIFIED.

### (d) Likely judges and what they care about
- 2025 Cleveland (virtual, same Local Lead username): judges Martina Dimoska, Bobi Sofronijoski, Arjun Srihari; 13 mentors, mostly software/data professionals by name. 2025 page also said official-challenge teams are eligible for local awards and global nomination, freestyle projects are local-only. VERIFIED - 2025 page.
- 2023: NASA Glenn hosted Cleveland (5th time), 50 participants, 13 teams; winner Team Vulcan, NASA Glenn interns, ML fire detection from Landsat. VERIFIED (search excerpt) - https://www.nasa.gov/general/glenn-in-the-community
- 2024: Cleveland teamed with NASA Glenn, hybrid, Local Lead Martina Dimoska; judge Bob Sopko named; NASA Glenn GVIS Lab interns won first place. VERIFIED (third-party blog excerpt) - https://sosassociates.com/blog/2024-10-19-nasa-international-space-apps-challenge-cleveland-2024
- Martina Dimoska: founder of International Space Alliance, analog astronaut, organized Cleveland at NASA Glenn. VERIFIED (excerpt) - https://greatercle.com/blog/gcp-news/from-north-macedonia-to-nasa-martina-dimoska-s-mission-to-make-space-for-everyone
- 2026 judges: not posted. Glenn involvement in 2025-2026: no mention on either page. Likely judges are the Local Lead's team, similar to 2025. UNVERIFIED.
- Glenn specialties (context only, SPHEREx is astrophysics, not a Glenn area): propulsion, power, communications, materials for extreme environments, icing, cryogenics. VERIFIED (excerpt) - https://www.nasa.gov/doing-business-with-glenn
- Official criteria at every level, each 1-5: Impact, Creativity, Validity, Relevance (NASA data as core), Presentation. Demo = max 7 slides or 30-second video, English. VERIFIED - judging guide.

### (e) Urgent action items (facts only)
- Submit before Sun Nov 15 9:59 PM Arizona (11:59 PM Eastern). Teams cannot add members after submission closes.
- Confirm in each member's logged-in view that both are registered for Cleveland, OH and not waitlisted; the guide makes this a hard eligibility rule for Global Judging.
- Ask the Local Lead (bxbi442@gmail.com or Discord) whether there is a live or recorded local pitch and when local judging happens; nothing is posted.
- Demo must be 7 slides max or a 30-second video, in English.
- Kickoff (10:30 AM Arizona) has already passed; recording, if any, would be on Discord/Meet (unknown).

### (f) Open questions
- How many Global Nominees Cleveland can send (field empty; guide silent).
- Who the 2026 judges are and whether NASA Glenn staff take part.
- Any local awards for 2026.
- Whether a live pitch on Sunday or Monday is expected.
- Each member's accepted vs waitlisted status.


---


# Part 5

## Agent 5 - Citizen science users (Backyard Worlds, Zooniverse, Rogue Worlds)
Research date: Sat Nov 14 2026. Labels: VERIFIED (full) = page opened and read; VERIFIED (excerpt) = source text read in search excerpt; UNVERIFIED = inferred or not read.

### (a) Bottom line
1. Discovery is a short loop, not a single viewer: spot motion in a flipbook, check SIMBAD/VizieR/Gaia, re-blink in WiseView, get coordinates, submit the "Think You've Got One" form, then the science team does telescope follow-up.
2. The biggest breakthroughs came from power users building their own tools (WiseView, a neural net), and the weirdest object ("The Accident") was found because a human looked at something the algorithm did NOT flag.
3. A small core does most of the work: 359 "advanced participants" vs ~83,000 registered users, Gini above 0.8.
4. Volunteer frustrations are concrete and visual: bad frames, loop "jump", fixed image size, no click-to-coordinate, markers that flicker.
5. Rogue Worlds (Faherty, AMNH) has no public interface, timeline or tool details yet beyond the Oct 28 2026 NASA listing. Another Space Apps entrant already polled Backyard Worlds volunteers on Nov 1 and got a "is this a bot?" reply.

### (b) How volunteers discover (step list)
1. Watch a flipbook of unWISE difference images; look for "movers" (fast) or "dipoles" (slow, negative next to positive). Kuchner et al. 2017, https://iopscience.iop.org/article/10.3847/2041-8213/aa7200/meta (2017-05-24) - VERIFIED (excerpt)
2. Rule out artifacts using the Field Guide: ghosts, diffraction spikes, latents, missing/partial frames. Cool Neighbors Talk sidebar, https://www.zooniverse.org/projects/coolneighbors/backyard-worlds-cool-neighbors/talk/5228/4168839 (seen 2026-11-14) - VERIFIED (full)
3. Check SIMBAD with a 1 arcmin radius; if nothing with total proper motion >100 mas/yr, tag #notinsimbad. Blog, https://blog.backyardworlds.org/2017/03/01/getting-started-with-simbad (2017-03-01) - VERIFIED (excerpt). Also VizieR across ~16,780 tables, https://blog.backyardworlds.org/2017/02/18/an-introduction-to-vizier (2017-02-18) - VERIFIED (excerpt). Cool Neighbors also treats anything with a Gaia parallax/proper motion as already known, https://www.zooniverse.org/projects/coolneighbors/backyard-worlds-cool-neighbors/about/faq (undated) - VERIFIED (excerpt)
4. Re-blink in WiseView (byw.tools/wiseview): FOV, W1/W2, speed, stretch, sliding window, difference imaging, shift-and-add, Gaia DR3 overlay, "Synthetic Object", PanSTARRS side cutout. Now operated by AMNH. http://byw.tools/wiseview (seen 2026-11-14) - VERIFIED (excerpt); https://blog.backyardworlds.org/2017/09/13/wiseview (2017-09-13) - VERIFIED (excerpt). Legacy Survey Sky Viewer for "quick big picture" (same blog).
5. Get exact coordinates from the IRSA Finder Chart; post notes on Talk using tags (#insimbad, #notingaia, #submitted, #artifact). Volunteer checklist, https://www.zooniverse.org/projects/marckuchner/backyard-worlds-planet-9/talk/693/902133 (2019-02-25) - VERIFIED (excerpt)
6. Submit "Think You've Got One" form -> goes to a spreadsheet; duplicates add you as co-discoverer; good ones go to a follow-up list, team discusses in chat, sometimes invites the volunteer. Moderator, https://www.zooniverse.org/projects/marckuchner/backyard-worlds-planet-9/talk/693/1188537 (2019-11-27) - VERIFIED (excerpt)
7. Follow-up: spectra / Spitzer photometry; 75 of 95 cold candidates motion-confirmed with WISE+Spitzer astrometry. https://iopscience.iop.org/article/10.3847/1538-4357/aba633 (2020-08-20) - VERIFIED (excerpt)

Famous finds and how:
- First BYW brown dwarf: Rosa Castro spotted it in flipbooks, "When an object is different, it simply stands out"; 4 volunteers co-authors. https://www.nasa.gov/feature/goddard/2017/nasa-funded-citizen-science-project-discovers-new-brown-dwarf (2017-07-17) - VERIFIED (excerpt)
- "The Accident" (WISEA J1534-1043): Caselden's own program removed stationary sources and highlighted brown-dwarf-like movers; he saw this one next to a candidate and it "hadn't been highlighted by the program because it did not match the program's profile." https://www.jpl.nasa.gov/images/pia24578-an-accidental-discovery/ (2021-08-31) - VERIFIED (excerpt)
- W1935 (methane emission, possible aurora, JWST): discovered by Caselden. https://science.nasa.gov/missions/webb/nasas-webb-finds-signs-of-possible-aurorae-on-isolated-brown-dwarf (2024-01-09) - VERIFIED (excerpt)
- WISE J0830+2837 (one of coldest): Caselden + Guillaume Colin. https://science.nasa.gov/people/dan-caselden/ (2019-10-24) - VERIFIED (excerpt)
- White dwarf LSPM J0207+3331: volunteer queried AllWISE infrared excess + Gaia DR2 parallax, found an outlier at 44 pc, checked motion in WiseView. https://blog.backyardworlds.org/category/results-and-discoveries (2019-07-15) - VERIFIED (excerpt)
- WiseView adoption "precipitated the rise in the rate of discovery," Sky and Telescope on Caselden's AAS Chambliss award. https://skyandtelescope.org/astronomy-news/citizen-scientist-wins-prestigious-aas-award (2024-01-25) - VERIFIED (excerpt)

### (c) User needs and frustrations
| Need | Evidence | Link | Date | Verified? |
|-|-|-|-|-|
| Drop bad frames | "We need a \"don't show this frame in the flip book\" button." | https://www.zooniverse.org/talk/739/190296 | 2017-02-23 | VERIFIED (excerpt) |
| Click-to-coordinates / jump to SIMBAD | "find coords of marker tool center ... or even have a button got to marker tool coords on Simbad" | https://www.zooniverse.org/talk/14/189204 | 2017-02-22 | VERIFIED (excerpt) |
| Bounce (forward-back) loop | "the repeating one-way loop has a distracting jump at the end ... offer a bouncing loop" ; researcher: Zooniverse does not support it | https://www.zooniverse.org/projects/coolneighbors/backyard-worlds-cool-neighbors/talk/5228/2975979 | 2023-06-27 | VERIFIED (full) |
| Resize images only | "I find it really hard to see movement because they are so big" ; uses classifier "to decide if it's worth opening wiseview" | same thread | 2023-06-30 | VERIFIED (full) |
| Reliable markers | Binaries: markers "flickering and vanishing ... making it impossible for me to work"; cause: drawing task not marking every frame | https://www.zooniverse.org/projects/coolneighbors/backyard-worlds-binaries/talk/7367/4042988 | 2026-06-16 to 2026-09-13 | VERIFIED (excerpt) |
| Use SPHEREx spectra for follow-up | Volunteer asks if SPHEREx low-res spectra could serve as follow-up "without the need to have observation proposals approved" | https://www.zooniverse.org/projects/coolneighbors/backyard-worlds-cool-neighbors/talk/5229/4160637 | 2026-10-22 | VERIFIED (excerpt) |
| Trust, no survey spam | Reply to a Space Apps team's 5-question poll: "please reply to make sure this is not a bot ... we saw similar type of a list of questions on other astronomy projects recently" | https://www.zooniverse.org/projects/coolneighbors/backyard-worlds-cool-neighbors/talk/5228/4168839 | 2026-11-02 | VERIFIED (full) |
| Weird objects outside the model | The Accident missed by algorithm; Kirkpatrick: "we need to think about how to look for them" | https://neowise.ipac.caltech.edu/news/neowise20210831/ | 2021-08-31 | VERIFIED (excerpt) |
| Noisy data, artifacts | Images "contain instrumental artifacts and are noisy" | https://en.wikipedia.org/wiki/Backyard_Worlds | accessed 2026-11-14 | VERIFIED (excerpt), secondary |

### (d) Other platforms and what worked
- Cool Neighbors (ML pre-selection, SMDET 3D-conv + LSTM on 13 unWISE epochs): median classification 6.0 s vs 22.0 s on Planet 9 (~3x faster); 423 vs 88 mean classifications per user; ~4,000 users, only ~1,000 overlap with P9. Survey of advanced group: 49.1% no effect, 39.6% more excited, 11.3% less excited by ML. https://theoryandpractice.citizenscienceassociation.org/articles/10.5334/cstp.737 (2024-01-11) - VERIFIED (full)
- Kilonova Seekers (GOTO, real-time): ~2,000 volunteers, 643,124 classifications, 20 first discoveries, report to TNS in as little as 3 h 20 min, 17,682-subject gold training set. https://academic.oup.com/mnras/article/533/2/2113/7735340 (2024-08-21) - VERIFIED (excerpt)
- Active Asteroids (DECam cutouts of known minor planets): 10,700+ volunteers, 9M classifications, 30+ discoveries; AI assistant TailNet found 2008 GB140 activity first. https://assets.pubpub.org/37jnduno/a6e3d78d-b807-49e2-8c60-69b243fa31d9.html (undated, after 2024) and https://iopscience.iop.org/article/10.3847/2515-5172/ad2b67/ampdf (2024-02-16) - VERIFIED (excerpt)
- Hubble Asteroid Hunter: 11,400 volunteers labeled >1,000 trails, used to train Google AutoML; 1,701 trails total, 1,031 unmatched to known objects; AutoML classified the archive in 10 hours vs "1 year" for volunteers. https://esahubble.org/news/heic2207 (2022-05-06), IVOA slides (2023-05-09) - VERIFIED (excerpt)
- Planet Hunters NGTS: 20,883 volunteers, 7.29M classifications, 5 candidates. https://blog.planethunters.org/ (2026-04-10) - VERIFIED (excerpt)
- Pattern (PNAS): human+machine beats either alone; must protect serendipity. https://www.pnas.org/doi/10.1073/pnas.1807190116 (2019-02-05) - VERIFIED (excerpt)

Users and motivation:
- Backyard Worlds combined: 175,000+ participants, 167+ countries, 10M classifications. https://science.nasa.gov/get-involved/citizen-science/backyard-worlds-volunteers-complete-ten-million-classifications-in-an-epic-search-for-new-objects-among-the-nearest-stars/ (2023-11-16) - VERIFIED (excerpt)
- Coauthorship is a key reward: 20 volunteers from 10 countries coauthored one paper; Les Hamlet: "its publication will definitely be the highlight." https://www.jpl.nasa.gov/news/citizen-scientists-discover-dozens-of-new-cosmic-neighbors-in-nasa-data (2020-08-18) - VERIFIED (excerpt)
- Zooniverse survey: 91% "contribute to progress", 84% subject interest; ages spread evenly; ~15% retired; ~half employed; ~60/40 gender. https://blog.zooniverse.org/2015/03/05/who-are-the-zooniverse-community-we-asked-them (2015-03-05) - VERIFIED (excerpt), old data
- NASA says more volunteers are using "super intelligence (SI)" to build their own data tools and write papers. https://science.nasa.gov/get-involved/citizen-science/nasa-selects-19-new-citizen-science-proposals-in-2026/ (2026-10-28) - VERIFIED (excerpt)
- Rogue Worlds: title "Activating volunteers to uncover the hidden population of super Jupiters with SPHEREx"; target young clusters; new projects "will come online as research teams prepare their platforms and data." Same NASA link and https://zot.news/article/nasa-selects-19-citizen-science-proposals-rogue-planets-ikktd (2026-10-28) - VERIFIED (excerpt). Platform (Zooniverse or not), interface, timeline: UNVERIFIED / not found.

### (e) What this means for choosing a project (facts, not an idea)
- Real users switch between 4-6 tools per candidate (flipbook, SIMBAD, VizieR, Gaia, WiseView, Finder Chart, form). Judges reading "Validity" will recognize whether a tool fits that loop.
- The highest-value users are a few hundred power users who already build tools; the mass audience does quick yes/no. A project should be clear which group it serves.
- ML pre-selection measurably raised engagement (~3x speed, 2-5x per-user output) without turning off advanced volunteers, but the most famous find was outside the ML profile. Serendipity is a stated value in the literature.
- SPHEREx spectra as "free follow-up" is something a volunteer raised unprompted (Oct 22 2026), and young-cluster free-floating planets are the stated Rogue Worlds target.
- Volunteers notice and distrust survey-style outreach from Space Apps teams; at least one other team (John_Luna) targets the same challenge with blink + subtraction + SED ideas, which makes a plain flipbook ordinary.

### (f) Gaps
- No Rogue Worlds interface, platform or schedule found.
- Did not read the Backyard Worlds advanced Google Group (members-only) or a full Planet 9 "feature requests" board.
- No SPHEREx-specific volunteer pain points yet (DR1 too new); WiseView limits beyond the threads above not documented.
- Comet Hunters results not checked. Demographics are Zooniverse-wide from 2015, not Backyard Worlds-specific.


---


# Part 6

## Agent 6 - Outside view (public, amateurs, press, tech crowd)
Checked Sat Nov 14 2026. VERIFIED = I read the text myself (full page, or the search excerpt where marked "excerpt"). UNVERIFIED = seen only as a title or listing.

### (a) Bottom line
1. Planet X / Nine is a real, open question for the press ("we don't know if either of these planets exists" - SciAm, Nov 6 2026), but to the public it is mixed up with Nibiru, Pluto jokes and conspiracy subs. A 2025 IRAS-AKARI candidate went viral again in Oct 2026. Mike Brown says it is "100 percent NOT Planet Nine".
2. On Reddit, SPHEREx pretty pictures do well (1,199 upvotes) and the science does not (brown dwarf post: 16 points, 0 comments). Top comments show people misread the all-sky map ("Why is it largely in a plane?", 71 points).
3. Volunteers are already being asked about "blink + subtraction" SPHEREx tools by at least one other Space Apps team (Nov 1 2026). A moderator suspected the list of questions came from a bot, and said similar lists had shown up "on other astronomy projects recently". So that idea is already common and the community is wary.
4. AI in citizen science: the accepted pattern is the hybrid model (AI pre-filters, humans find surprises). The 2026 worries are AI slop and fake data (NYT Oct 16, Nature E&E Jul 13). The "Super Intelligence" rename (EO 14434) was widely mocked as hype.
5. Unmet wants seen: "where is it in the sky right now" in plain terms, explorable zoom viewers people can share finds from, referee-style sanity checks for amateur candidates, access for blind and low-vision users, and tools that keep working when NASA services go down.

### (b) Opinions table
| Topic | What people say | Example quote | Link | Date | Verified? |
|-|-|-|-|-|-|
| Planet Nine, press | Open question. The candidate is likely a false positive, or a different planet | "The bottom line is: we don't know if either of these planets exists, yea or nay." | https://www.scientificamerican.com/article/have-astronomers-spotted-planet-nine/ | 2026-11-06 | VERIFIED (full) |
| Planet Nine, Brown | IRAS-AKARI candidate orbit tilted ~120 deg vs the predicted 15-20 deg. Batygin calls it "Planet 8.5" | "Whether it is real or not, it is 100 percent NOT Planet Nine" | https://www.astronomy.com/science/have-astronomers-found-planet-nine/ | 2025-05-13 | VERIFIED (excerpt) |
| Viral revival | The 2025 paper "enjoyed something of a renaissance" through BBC Sky at Night and social media | "We may have found the first direct evidence of a ninth major planet" (headline) | https://www.skyatnightmagazine.com/news/planet-9-iras-akari-survey-evidence | 2026-10-05 | VERIFIED (excerpt) |
| Skeptic (sednoid) | Ammonite's orbit lowers P9 odds | "lowers the likelihood of the Planet Nine hypothesis" - Yukun Huang | https://thedebrief.org/a-massive-hidden-planet-may-be-lurking-beyond-neptune-this-caltech-scientist-thinks-planet-nine-may-soon-be-confirmed | 2026-06-05 | VERIFIED (excerpt) |
| Amateur skeptic | The ETNO clustering is observation bias. Post title "New study completely debunks Planet 9" | "These 4 points totally debunk Planet 9." | https://community.lsst.org/t/new-study-completely-debunks-planet-9/12085 | 2026-06-08 | VERIFIED (excerpt). Amateur claim, not peer-reviewed |
| Rubin / discovery mood | A new dwarf planet candidate (2026 ED138) shows "amazing things left to be found" | "there could easily be a Mars-sized object out there" - Matthew Holman | https://www.nytimes.com/2026/10/27/science/space/new-dwarf-planet-beyond-pluto.html | 2026-10-27 | VERIFIED (excerpt) |
| Public on Planet X | The term gets confused with Nibiru right away | "...and definitely not for Nibiru in the snake oil sense." (25 pts) | https://old.reddit.com/r/askastronomy/comments/1p2x8yl/ | ~Dec 2025 (123 pts, 83 comments) | VERIFIED |
| SPHEREx map, public | Excited, but confused by the projection and what is shown | "Why is it largely in a plane? Like a really big galaxy?" (71 pts). Another: "this picture isnt just our galaxy. It is the known universe." | https://old.reddit.com/r/spaceporn/comments/1pt32nx/ | ~Jan 2026 (1,199 pts) | VERIFIED |
| SPHEREx science, public | Low engagement on science posts. One 2026 post title calls it a telescope "You May Not Have Heard Of" | r/Astronomy brown dwarf post: 16 pts, 0 comments. r/nasa "Niftiest Space Telescope You May Not Have Heard Of": 70 pts | https://old.reddit.com/r/Astronomy/comments/1x1846k/ | ~Oct 2026 | VERIFIED (listing counts) |
| 3I/ATLAS fringe | SPHEREx 3I/ATLAS images are shared in UFO and "cover-up" subs | Post titles such as "3I/ATLAS: The Complete Intelligence File. Every Anomaly. Every Cover-Up." | https://old.reddit.com/r/probes/comments/1rer6af/ | ~Mar 2026 | UNVERIFIED (title only) |
| Volunteers and Space Apps teams | Another team asked BYW volunteers about blink vs subtraction, pain points and 102-band display. A volunteer suspected it was a bot | "please reply to make sure this is not a bot asking a list of questions... we saw similar type of a list of questions on other astronomy projects recently" (LukeM714) | https://www.zooniverse.org/projects/coolneighbors/backyard-worlds-cool-neighbors/talk/5228/4168839 | 2026-11-01/02 | VERIFIED (Talk API) |
| AI in citizen science | Hybrid model praised. AI pre-filtering gave about 3x the classifications | "there's still the human element in discovering things that you didn't even realize you were looking for" - Aaron Meisner | https://news.medill.northwestern.edu/chicago/in-the-zooniverse-ai-cant-take-the-citizen-out-of-citizen-science | 2025-10-07 | VERIFIED (excerpt) |
| AI slop | Platforms are adding checks against fake AI submissions | "Citizen Science Groups Grapple With the Rise of A.I. Slop" (headline) | https://www.nytimes.com/2026/10/16/science/citizen-science-ai-slop.html | 2026-10-16 | VERIFIED (headline and snippet only) |
| SI rename | Experts call it hype and misleading | "I doubt 'SI' will stick, in part because it exaggerates the current capacities of AI" - Simon Coghlan | https://www.bbc.com/news/articles/cqy4z9pv4w0po | 2026-09-23 | VERIFIED (excerpt) |
| SI rename | Rename may increase fear | "Rebranding it to superintelligence is unlikely to reassure them." - Thomas Haigh | https://politifact.com/article/2026/oct/07/trump-ai-super-intelligence | 2026-10-07 | VERIFIED (excerpt) |
| Tech crowd, viewers | Love zoomable, shareable viewers. Users post coordinates of what they find | "Even one zoom-in and I find something interesting." | https://news.ycombinator.com/item?id=44356890 | 2025-06-23 (579 pts, 166 comments) | VERIFIED |
| Tech crowd, "where is it?" | Data exists, but ordinary users cannot get a sky position from it | "Ephemeris listing, if anyone knows how to get RA/Dec from it" | https://news.ycombinator.com/item?id=50266046 | 2026-10-28 | VERIFIED |
| Amateurs, vetting | Amateurs who mine public surveys want false-positive critique | "I'm looking for a sanity check / referee-style critique" | https://www.cloudynights.com/forums/topic/990361 | 2026-01-15 | VERIFIED (excerpt) |
| Amateurs, reliability | NASA sky-survey services are down for some users | "HIPS and NASA sky surveys are not responding in NINA" | https://www.cloudynights.com/forums/topic/1014997 | 2026-11-10 | VERIFIED (excerpt). The IRSA page also showed "10/28/2026: Some object lookup services are unavailable" |
| Amateur tool gripes | Aladin is powerful but the docs are hard to use. Users cannot easily blink their own image against SDSS | "Is there a way to blink my fits image with Aladin's SDSS images?" | https://www.cloudynights.com/forums/topic/696478-using-aladin-v10 | 2020-03-02 | VERIFIED (excerpt, old) |

### (c) What excites people
- The look and the scale: the 102-color whole-sky map is the hit (1,199 and 434 upvotes on r/spaceporn).
- "Things left to find": the new dwarf planet candidate, Planet Nine headlines, and stories like "12-year-old finds asteroid" (1,170 pts on r/space).
- Strange-but-real facts: a brown dwarf "as cold as a refrigerator" got a 1,118-pt TIL post. Press liked the line "They're kind of goth" and models "coming up short" (Cosmic Herald, ZME, Oct 2026).
- Ordinary people making discoveries: Backyard Worlds volunteers found 3,006 L/T dwarf candidates (AJ, May 2026).
- 3I/ATLAS chemistry (CO2 coma, organics). It also draws strong interest from conspiracy subs.

### (d) What they are skeptical of
- Single-detection planet claims ("two points do not a planet make"). Possible false positives include variable stars and flaring black holes (SciAm).
- The Planet Nine clustering itself (observation bias, Ammonite).
- Generic AI: slop, fabricated data, black-box results. The EAS 2026 session asks whether results are "driven by real astrophysical signals or by hidden biases".
- The "Super Intelligence" wording: called "hype" (Purtilo) and "misleading" (Coghlan), and compared to "Gulf of America" (Kovacevich, quoted in The Independent).
- Bot-like outreach to volunteer communities (Zooniverse, Nov 2026).

### (e) Unmet wants (as stated or implied)
- A plain-language "where is it in my sky now" from a catalog name (HN Oct 2026).
- A Google-Earth-style zoomable sky that is easy to share (HN liked skyviewer.app). Someone wished for a "super nice public mobile app".
- Help with the projection and orientation of all-sky maps (Reddit confusion).
- Referee-style vetting help for amateur candidates (Cloudy Nights).
- Blinking your own image against survey images (old Cloudy Nights request).
- Access for blind and low-vision users through sonification. A study of 3,184 participants reported learning gains and trust gains (Frontiers 2024).
- Tools that keep working when NASA services are down (NINA, IRSA outage notes).

### (f) What this means for choosing a project
- A plain "blink + subtract SPHEREx viewer" is already being built by other teams and is familiar to volunteers. Judges will likely see several. A non-ordinary entry needs a different angle on the same data.
- Planet X sells headlines but brings Nibiru baggage and skeptics. Framing that shows uncertainty openly (what is real, what is a false positive) fits where the press is now.
- The public's real gap is understanding: map projection, "what am I looking at", "where is it". Communicating what the data means is unmet, not only displaying it.
- If AI is used, people trust the hybrid "machine filters, human discovers" story. "AI finds planets" alone draws slop and hype objections, made sharper by the SI rename.
- Volunteer communities are sensitive to bots and extraction. Anything that touches them should give credit and be clearly human.

### (g) Gaps
- Reddit's .json and old.reddit were blocked for WebFetch and curl. Reading old.reddit through the browser worked. r/Astronomy_Software and r/citizenscience were not searched in depth.
- I found no Hacker News thread on SPHEREx with real discussion in 2026, and no Ars Technica or New Scientist SPHEREx pieces. The "mantis shrimp" framing was not found in public reactions.
- I did not check whether SPHEREx depth (5-sigma about 19.5 AB, 6.2-arcsec pixels) can constrain Planet Nine.
- I could only see the NYT AI-slop article's headline and a snippet (paywall). The SI rename reaction found is general, not specific to astronomy.


---


# Part 7

## Agent 7 - What builders, judges and local leads say about winning Space Apps

VERIFIED = I read the page text myself. UNVERIFIED = search snippet only, or second-hand.

### (a) Bottom line
1. The 2025 funnel was brutal: 11,511 projects, then 1,294 Global Nominees, then 45 Global Finalists (plus 23 Honorable Mentions), then 10 winners. Roughly 1 in 26 nominees became a finalist.
2. Scientist judges punish "just an app that shows NASA data". They want real computation, a validity check, and a clear answer to "doesn't this already exist?"
3. The official rubric gives a 5 for Creativity only to "a groundbreaking approach that has never been attempted before". Relevance 3 means NASA data is "supplementary", meaning the method would still work without it.
4. Presentation is judged from the demo first, and judges stop at 30 seconds or 7 slides. Builders who got close say they wish they had frozen the build earlier to work on the pitch.
5. Winning rarely changes careers straight away. The documented outcomes are a NASA scientist chat (2025), sponsor funding or incorporation for a few teams, and use as a credential.

### (b) Tips table
| Tip | # sources | Best quote | Links (date) | Verified? |
|-|-|-|-|-|
| Go past displaying data and do real science or maths, then show it is valid | 4 | Space-scientist judges said "it was just an app, that we were just obtaining raw data and not really doing real math with it" | Meera Vinod, Medium (event Apr 2016, posted Sep 2018) medium.com/@meerarevathy.99/my-first-ever-hackathon-the-nasa-space-apps-challenge-619f3efebddd ; 2025 Judging Guidelines PDF spaceapps-v2-staging.s3.amazonaws.com/media/documents/Final_Space_Apps_2025_Judging_Guidelines_for_web.pdf ; Mountain View local lead on Resonant Exoplanets: "physics-first AI engine... impressed NASA's global judges" facebook.com/groups/spacehipsters/posts/25512238575061018 (Nov 26 2025) ; Minerva Blue Skies "collaborated with researchers and integrated real-time contrail prediction data" minerva.edu/blog/2024-nasa-space-apps-challenge-winners (Dec 18 2024) | Vinod and PDF VERIFIED; FB and Minerva UNVERIFIED |
| Avoid the obvious solution; originality is what stands out | 3 | "think outside the box and avoid obvious solutions... your project will compete with thousands of others" (my translation from the Arabic track) | Bruno Freitas, 2023 Global Winner, youtube.com/watch?v=SeriamoGlnw (Oct 1 2024) ; 2025 rubric (Creativity 5 = "never been attempted before") ; 2016 Mission Report: NASA judges found the best projects "less linear" assets.spaceappschallenge.org/media/documents/SpaceApps2016_MissionReport.pdf | Video and PDF VERIFIED; 2016 report UNVERIFIED |
| Have an answer to "this already exists" | 3 | Judges "pointed out that complex weather tracking gear was currently available... we couldn't come up with a convincing response" | Vinod (above) ; 2025 rubric Creativity 1 = "difficult to distinguish from prior work" ; Science Buddies judge tips: "How does your approach... differ from people's previous approaches?" sciencebuddies.org (Jun 2012) | First two VERIFIED; Science Buddies UNVERIFIED |
| Presentation and story count as much as the build | 5 | "remember to pay equal attention to the final criterion: presentation" | Official guides 2020-2022, e.g. spaceapps-prod.s3.amazonaws.com/media/documents/Space_Apps_2022_Judging_and_Awards_Guide.pdf (Sep 2022) ; Katherine Soto, local winner 2024: "a less polished MVP would have allowed us to focus more on the pitch" kateincoding.medium.com (2024) ; Minerva winner-turned-mentor: pitch "is where everything comes together" (Nov 13 2024) ; Sydney local lead site spaceappssydney.org ; Dublin judge praised a "great deck" blog.ncirl.ie (Nov 2025) | Soto and NCI VERIFIED; others UNVERIFIED |
| Freeze the build early, keep time for the demo, document as you go | 4 | "we cut down tasks to make sure the development wrapped up by 3 p.m." | Soto (above) ; Freitas (above) ; Vinod ("perfecting... each stage... rarely works") ; Akinremi, Global Nominee 2021, "document your project as you're building" medium.com/@akinremibunmi111 (Nov 28 2021) | Soto, Freitas, Vinod VERIFIED; Akinremi UNVERIFIED |
| Pick a challenge that fits your skills and data you can actually open | 5 | "Make sure you can get the data... skipping it hurts on Saturday" | HackAthlone (Oct 13 2026) hackathlone.com/blogs/how-to-choose-a-space-apps-challenge ; Freitas ; Soto ; Minerva 2023 local winner (Nov 21 2023) ; 2016 Mission Report (Scintilla) | HackAthlone, Freitas, Soto VERIFIED; others UNVERIFIED |
| Build for scientists and the public, and show it scales | 1 (3 judge comments) | "a creative, practical approach to benefit both scientific and public community... demonstration of the potential scalability... is interesting" | Dublin local judges' comments on 2025 Global Nominees, blog.ncirl.ie/nasa-space-apps-challenge-projects-that-launched | VERIFIED |
| A local or human angle helps but is not enough | 2 | "A local angle won't win on its own, but it makes your problem real" | HackAthlone (above) ; 2016 Mission Report ("social or humanitarian component... rise to the top") | HackAthlone VERIFIED; report UNVERIFIED |

### (c) Judge red flags and common mistakes
- **Automatic score of 1, no further review** (2025 guidelines, VERIFIED): not mainly in English, does not answer the chosen challenge, demo over 7 slides or 30 seconds, links not open or behind a password, no NASA data, AI use not declared, AI-made content with NASA logos, flags or mission identifiers. AI images and video need a visible watermark.
- Judges stop watching at 30 seconds or at slide 7 (2022 Submission Guide, UNVERIFIED snippet). The 2024 guide's 30-second script: 0:00 names, 0:02 challenge, 0:05 title and tagline, 0:10 how it works plus the NASA data, 0:20-0:30 future (scribd copy, UNVERIFIED).
- NASA data that only plays a supporting role caps Relevance at about 3 (rubric, VERIFIED).
- Wireframes or mockups with no working core (Vinod, VERIFIED).
- Starting work before Nov 14 is against the rules (GitHub nasa/spaceapps discussion #1938, Nov 11 2026, UNVERIFIED).
- Devpost judge Karen (generic, not Space Apps): "surprising to see how many submissions did not fulfill the basic requirements" (info.devpost.com/blog/hackathon-judging-tips, UNVERIFIED).
- Complaint: one participant said "a basic AI powered one page weather webapp won the top place in our region" over a more complex build. This shows local judging varies (facebook.com/groups/coding.event.bd/posts/1079256561776578, 2026, UNVERIFIED).
- In live local judging, a laptop failure took 30+ minutes (Akinremi 2021, UNVERIFIED). Have a backup.

### (d) What happened after winning
- 2025 Global Winners got "one-on-one virtual conversations with NASA scientists" (DevStory, 2025 Global Finalist team, Feb 26 2026, VERIFIED page, secondary source). The 2026 prize is not published.
- Earlier Winners' Trip: possibly watching a launch, but winners and guests paid their own travel and visas, and NASA screening applied (legacy FAQ 2022, UNVERIFIED).
- Scintilla (2016 Best Use of Data): a sponsor (Supplyframe) paid a stipend for 4 months of prototype work. Canaria incorporated a company (2017 Mission Report, UNVERIFIED).
- FireWay (Ukraine): media coverage and investor talks. Also: "We cannot patent what we have done on the hackathon... Everything... is already public" (spacetech.global, Jul 7 2021, UNVERIFIED).
- Andrew Denio (2016 Best Mission Concept) later joined NASA Marshall in IT. Space Apps "didn't directly lead" to the job, but he discussed it in his interview (nasa.gov, Sep 20 2019, VERIFIED).
- SongSAT (global winner) kept building, using feedback from visually impaired users (same NASA article, VERIFIED).
- A Hacker News immigration attorney said repeated Space Apps wins could support an O-1 or EB-1A case "without knowing more" (news.ycombinator.com/item?id=11973819, Jun 2016, UNVERIFIED, not legal advice).

### (e) What this means for a SPHEREx project
- Expect the scientist question "is this just an image viewer?" Judges reward a computed result plus proof it works, for example checked against known ground truth. Showing pictures over time is not enough.
- Prepare a one-line answer on prior art: what existing SPHEREx and IRSA tools or moving-object searches already do, and what is new here. Check this live before pitching. I did not verify which tools exist.
- SPHEREx data must carry the method (Relevance 5). Name and link each dataset on the project page.
- The 30-second video is the first filter. Lead with the result, not the setup. Keep every link public and test it logged out.
- Planet X and SPHEREx is tagged Advanced only (HackAthlone, VERIFIED). That may mean fewer teams, but this is my inference, not data.
- Declare any AI use, watermark AI visuals, and keep NASA logos out of generated art.

### (f) Gaps
- I found no personal post from a NASA SME or executive judge on global judging. All judge comments here are local.
- Reddit threads (old.reddit and .json) returned empty. I did not browse LinkedIn. Community opinion is thin and mostly comes from snippets.
- I read the 2025 judging guidelines, not the 2026 guide published Nov 13 2026. Re-check the minimum rules there.
- I found no past Space Apps project built on SPHEREx data.


---


# Part 8

## Agent 8 - X/Twitter and YouTube (read-only, checked Sat Nov 14 2026)

### (a) Bottom line
1. The "blink + time slider" idea is already taken many times over. At least 6 public Planet X entries (Bangladesh, Egypt x2, Red-Shift, Schwarzschildren, OSCAR) all pitch blinking SPHEREx frames like Tombaugh 1930.
2. The strongest rival, Team Oblivion "SPHEREx Explorer", already ships: IRSA live search, blink, its own mover search, JPL check (0.8 arcsec match on asteroid 7 Iris), CatWISE brown-dwarf overlays, "where SPHEREx was" per frame, a spot-the-mover game, Bangla, and a cited-sources assistant.
3. Also taken: 3I/ATLAS as the hero target (SkyBlink), an "AI model that flags movers" plus spectra on click (Sky Time Machine), and a band selector plus tracking dashboard (TRACE-X).
4. Official rules (verified): 30 s video or 7 slides max, or no global award. Scores 1-5 on Impact, Creativity, Validity, Relevance, Presentation. Judges weigh "originality, intent, and execution" in AI-assisted work, and AI use must be labeled.
5. The SPHEREx team says repeat coverage is about every 6 months at the equator but much more often near the ecliptic poles. They say SPHEREx is "not really designed" for transients but can set a "baseline", and that most science is done by "the public mining through the data". SPHEREx DR1 went live at IRSA on Nov 13.

### (b) Live 2026 activity
| Who | What they build or say | Link | Time | Verified? |
|-|-|-|-|-|
| @willy_wonka_28 | "OSCAR: a data visualization tool for the SPHEREx satellite". Blinking "on a loop to spot anomalies... OSCAR is the modern version" of the Pluto method | x.com/willy_wonka_28/status/2121661530429165890 and /2121665287841776052 | Nov 14 17:48 and 18:03 UTC | VERIFIED (text read) |
| Team Oblivion (Bangladesh) | SPHEREx Explorer: blink, mover search, JPL check, CatWISE2020 movers, Gaia via SIMBAD, DSS2/2MASS/AllWISE side by side, game, Bangla, cited-answer assistant, ElevenLabs narration | youtube.com/watch?v=BDLzgZvxyYs (239 s), lhi7lI8fvHg (30 s), app spherex-explorer.vercel.app | Nov 13 2026 (earlier cut n4JViL7Wlvo, Oct 7) | VERIFIED (transcript + description) |
| Phantom Signal (Cairo) | SkyBlink: telescope-eyepiece UI, 3I/ATLAS target, time slider, blink, guided stories, IRSA cutouts, Aladin Lite | youtube.com/watch?v=2gWA6gkJPqo (85 s) | Nov 7 | VERIFIED |
| Ahmed Wael | "SPHEREx Sky Time Machine": coordinates to video, "AI model that flags movers", spectra on click, Flask/Astropy/React | youtube.com/watch?v=bmkcEWLj-jI | Nov 7 | VERIFIED (description) |
| Red-Shift / TRACE-X | Blink comparator with crossfade, 102-band selector, object tracking dashboard, spatial tiles, image registration | youtube.com/watch?v=YJgG2smIl2U (Sep 30), NC_445RK4Pg (Nov 13) | Sep 30 and Nov 13 | VERIFIED (transcript) |
| Schwarzschildren | Planet X entry, no transcript | youtube.com/watch?v=YdL1f9uXbAM | Oct 10 | UNVERIFIED content |
| @NASA_IRSA | "SPHEREx Data Release 1 (DR1) is now available at IRSA... all-sky spectral cube covering 102 spectral channels from 0.75 to 5.0 um". Also an IRSA Viewer HiPS how-to video | x.com/NASA_IRSA/status/2121321763342819736 and /2121322110425629093 | Nov 13 19:18 UTC | VERIFIED |
| @NASAUniverse | "create a time-lapse tool for this data that helps users explore how the sky changes" | x.com/NASAUniverse/status/2120953278854823989 | Nov 12 | VERIFIED |
| @SpaceApps | "Build a time-lapse sky viewer for the SPHEREx mission". Statements live Oct 28 (14 challenges). Global Offers live Nov 13 | x.com/SpaceApps/status/2112574568581751152, /2115481217965371893 | Oct 20 to Nov 14 | VERIFIED |

Note: several "2026" Planet X videos are dated Sep 30 to Oct 10, before the Oct 28 statement release. I can't explain this, but the ideas are public either way.

### (c) Winning demo breakdowns
**42 QuakeHeroes, 2024 (30 s)** - youtube.com/watch?v=thxLntBLF1I, Oct 6 2024. Winner status VERIFIED only by a teammate's video title "nosso projeto vencedor do NASA Space Apps 2024" (G4Y7l9MSH_g).
- 0-4 s: name and team.
- 4-8 s: challenge.
- 8-13 s: problem ("transmitting relevant data wastes energy").
- 13-23 s: method (empirical modes into an encoder-decoder network).
- 23-28 s: result ("identify seismic events even in the presence of noise").
- 28-31 s: tagline "together we can explore the unknown".
- Why it works: one problem, one method, one result. It is a talking head, with no polish.

**WaterWise, 2024 Best Use of Data (31 s)** - youtube.com/watch?v=Wg-gE3kYaas, Oct 6 2024. Award VERIFIED only by the uploader's title.
- 0-4 s: name and one-line value.
- 4-12 s: dashboard at a glance.
- 12-23 s: live workflow (map a field, get 7-day water needs).
- 23-28 s: AI helper.
- 28-31 s: tagline.
- Why it works: a pure screen-recorded user journey that shows the product working.

**Team Oblivion 2026 (competitor, not a winner; 239 s plus a 30 s cut)** - BDLzgZvxyYs.
- 0:19: SPHEREx in 102 colors.
- 0:37: team.
- 1:05: Tombaugh 1930.
- 1:36: "The method is simple. The scale isn't."
- 2:03: demo search.
- 2:16: blink, mover found, JPL confirms.
- 2:38: honesty about color, where SPHEREx was, game, Bangla.
- 3:27: "We have more data than ever before. Now we need more people looking at it."
- Their 30 s cut (lhi7lI8fvHg) squeezes all of this into a voice-over list of features.

**Global-winner advice (official channel)** - SeriamoGlnw, Oct 1 2024, Bruno Freitas, 2023 Galactic Impact. VERIFIED quotes:
- [01:03-01:11] "by far, my best advice is to think outside the box and avoid the obvious."
- [01:14-01:22] "having original ideas and exploring unusual approaches are the best way to stand out."
- Credits immersive interaction [01:26-01:34].

### (d) Official 2026 video takeaways
"Project Submission and Judging & Awards", CV7AYfMRyMM, Nov 13 2026, 13 min. VERIFIED (English auto captions).
- [02:56-03:09] "Slide presentations have a seven slide limit including title and intro slides. And video presentations must be 30 seconds or less."
- [03:30-03:42] the 30 s / 7-slide limit and public access are required to be eligible for a global award.
- [04:30-04:53] the questions judges ask: what it does, benefits, "What is the intended impact?", "How is your project creative?", and energy, accessibility or cost.
- [05:22-05:58] AI use must be labeled (watermark on images and video, note AI audio and code). "Judges will consider originality, intent, and execution when reviewing SI assisted work."
- [10:56-11:09] each category is scored 1-5.
- [12:09-12:22] dates: global nominees Dec 3, finalists Dec 17, winners Jan 26 2027.
- Spoken demos in other languages need English subtitles. No people under 18 may appear.
- I found no 2026 Planet X SME bootcamp video and no "how to make a demo" video on YouTube.

### (e) SPHEREx team talk takeaways
JPL public talk, Jamie Bock, XdnIAmDwkhc, Feb 22 2024. VERIFIED.
- [09:42-10:02] "this data comes out to the public uh on a rapid time scale... most of the science is actually done by the public mining through the data on their own."
- [09:12-09:24] solar-system science means "studying the spectra of comets and asteroids".
- [46:11-46:34] "looking for transient events and we're not really designed to do that, but we can help... we can establish a baseline and then if transients are discovered... we can come back and see in our next survey what happened".
- [46:44-46:59] near the poles "we actually cross multiple times", while near the equator it is "more like every 6 months".
- [47:07-47:16] long-term behavior such as "star systems that are going through a bombardment phase".

Brian Keating interview with Jamie Bock, uHSQW_BBYAc, Nov 21 2025. VERIFIED.
- [10:10-10:17] data released "within two months of collection".
- [51:42-51:55] three legacy programs, including "properties of solar system objects".
- [57:45-57:58] for 3I/ATLAS "because it's moving we wouldn't get a complete spectrum. So we added some additional fields".

### (f) What this means for choosing a project
- The baseline features are already crowded and public: blink, time slider, JPL check, CatWISE/Gaia overlays, a game, an AI chatbot and 3I/ATLAS. Matching them scores as "ordinary" under Creativity.
- Bock's points open angles the rivals mostly ignore: multi-visit polar fields, "what happened next" checks against a baseline, a moving object's spectrum that changes per band, and long-term change. The team should judge these themselves.
- Validity is where rivals over-claim. Oblivion's "honest about colour" point shows judges reward handling SPHEREx's band-per-frame quirk, and a project that names its limits will read as credible.
- The 30 s demo must be one problem, one moment of discovery and one result, as in the QuakeHeroes and WaterWise shapes. A feature list in voice-over reads as weak.
- Label any AI use, and avoid NASA logos in generated assets.

### (g) Gaps
- I did not find demo videos for Resonant Exoplanets (2025), WMPGang/SkyShield (2024) or Storm Prophet (2023). Only a 96-min Ukrainian story video exists for Storm Prophet (ts65sguADv8), and I did not read it. WMPGang's 2024 Best Use of Science award is VERIFIED via @csa_asc and @uwogazette.
- No 2026 SME or bootcamp video for Planet X, and no SPHEREx team posts on X about Space Apps beyond @NASAUniverse.
- I did not check @NASA, @NASAJPL or @IPAC_Caltech timelines one by one (one combined search). X search may miss non-English or hashtag-less posts.
- I did not read the official judging criteria text (the Judging and Awards guide page).


---


# Part 9

## Agent 9 - What NASA working staff say (below top leadership)
Research date: Sat Nov 14 2026. Read-only. VERIFIED = I read the quoted text on the linked page or in a search excerpt of it. UNVERIFIED = secondhand or not opened.

### (a) Bottom line
1. The IRSA archive staff and their own user panel (March 2026) say the problem is not data access but usability: tools are "clunkier than competitors", Firefly is powerful but "daunting", docs are "solid, though complex", and newcomers (students) need onboarding.
2. The panel explicitly asked for better multi-survey, multi-band time-domain (light-curve) interfaces. SPHEREx solar-system scientists say moving-object data needs "careful, consistent motion corrections" before it is useful.
3. NASA's AI people are cautious in a specific way: human in the loop, "trust but verify", traceable and validatable outputs. A black-box result will be distrusted.
4. Open-source culture is strong, but maintainers are now defensive: astroquery limits PRs from new contributors because of LLM-generated PRs. Outside tools get adopted when they plug into the existing stack (astropy, pyvo, Firefly, notebooks, Fornax) rather than replace it.
5. The workforce is badly cut (22% of civil servants gone, Goddard -34%, JPL -550 in Oct 2025). Staff morale is grim, so tools that save scarce expert time get the most interest.

### (b) People table
| Name | Role (date seen) | Quote or paraphrase | Link | Date | Status |
|-|-|-|-|-|-|
| Adam Ginsburg (chair) + IRSA User Panel | U. Florida, IRSA User Panel chair; astroquery co-maintainer (Nov 14 2026) | "several of the IRSA interfaces were clunkier than competitors"; "Firefly is an incredibly powerful tool, but users are often daunted by its complexity"; "we recommend improving data access interfaces for light-curve data ... better support multi-survey, multi-band datasets"; asks for training "focused at young students" and "classroom use of Fornax" | https://irsa.ipac.caltech.edu/docs/user_panel/IRSA_UP_2026.pdf | Meetings Feb 27 and Mar 6 2026 | VERIFIED |
| Same panel | as above | Praised IRSA's LLM documentation front end, especially "ensuring that the LLM frontend returns trustworthy, validatable answers" | same | 2026 | VERIFIED |
| Vandana Desai | IRSA Science Lead, IPAC Head of Science Staff, IRSA Fornax lead (Mar 2026 bio) | Mission is to "empower the global astronomical community with the tools required to preserve and extend the scientific legacy of NASA's mission data"; giving AAS 248 talk "Building User Support for Fornax: Community Engagement for Cloud-Based Astrophysics" | https://assets.science.nasa.gov/content/dam/science/astro/programs/physics-of-the-cosmos/fornax/documents/Fornax-Key-Team-Members_2026-03-26.pdf ; https://www.ipac.caltech.edu/page/aas248 | Mar and Jun 2026 | VERIFIED |
| IRSA Data Explorer team (unnamed staff) | SPHEREx Data Explorer known-issues page (updated Nov 2026) | Long spectrophotometry jobs "may be lost"; "Duplicate source names causes chaos"; no parameter checking for multi-object photometry; email notices fail; "IRSA Workspace doesn't work" | https://irsa.ipac.caltech.edu/docs/known_issues/spherexbugslist.html | Nov 2026 | VERIFIED |
| IRSA online help (staff-written) | SPHEREx Data Explorer help (Nov 2026) | Users trip over the LVF design: "All 6 bands are obtained at the same time but not of the same target"; "QR2 and QR3 data should not be mixed!"; DR1 released 12 Nov 2026 | https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/overview.html | Nov 2026 | VERIFIED |
| Brigitta Sipocz | Research Software Engineer, Caltech/IPAC-IRSA; astroquery maintainer (Nov 2026) | astroquery README: "we opted in enforcing a PR limit to exitsing contributors due to the recent uptake of LLM generated PRs"; new contributors should contact maintainers on astropy Slack first | https://github.com/astropy/astroquery | read Nov 14 2026 | VERIFIED |
| Gabriela Torrini, Andreas Faisst (SSDC), Troy Raen, Brigitta Sipocz, Jaladh Singhal (IRSA) | Authors of SPHEREx Source Discovery Tool notebook | IRSA already ships a tool that does "a simple image subtraction to find red sources" and extracts spectra interactively (Firefly + bokeh); photometry functions "adapted from Zafar Rustamkulov" | https://caltech-ipac.github.io/irsa-tutorials/spherex-source-discovery-tool-demo | 2026 | VERIFIED |
| Carey Lisse | SPHEREx solar system science lead, JHU/APL (LPSC 2026) | Every pointing contains "hundreds of moving solar system objects"; "Much work is required in order to convert the millions of individual SPHEREx LVF sky images taken over time into calibrated spectra with observational systematics removed"; earlier slide: "SPHEREx Data will require Careful, Consistent Motion Corrections to be Scientifically Useful!" | https://www.hou.usra.edu/meetings/lpsc2026/pdf/1833.pdf ; https://www.hou.usra.edu/meetings/sbagjuly2024/presentations/Friday/1505_Lisse.pdf | Jan 2026; Jul 2024 | VERIFIED (excerpt) |
| Kevin Murphy | SMD Chief Science Data Officer and Acting Chief Data and AI Officer (May 2026) | "we don't really have AI making decisions for us at this agency at this time"; human in the loop "especially for high consequence decisions"; NASA will never publish AI imagery that "could be misinterpreted as actual mission imagery" | https://www.nasa.gov/podcasts/houston-we-have-a-podcast/ai-at-nasa | Rec. May 5 2026 | VERIFIED |
| Kevin Murphy | same (Oct 2026) | "You can't have super intelligence or artificial intelligence without ... a really good data ecosystem"; ~200 PB public science data | https://www.meritalk.com/articles/nasa-moves-to-treat-data-software-as-strategic-assets-for-ai | Oct 9 2026 | VERIFIED (excerpt) |
| Rahul Ramachandran, Kaylin Bugbee | IMPACT / MSFC data science (2025-2026) | Agentic AI risks "plausible but incorrect results, automation bias"; outputs should cite validated datasets; "Opaque 'black-box' systems are insufficient"; Bugbee slide: "trust but verify", "Avoid unquestioning acceptance of AI-generated outputs" | https://agupubs.onlinelibrary.wiley.com/doi/abs/10.1029/2025EA004662 ; https://ntrs.nasa.gov/api/citations/20250002694/downloads/APS%20LLM%20Presentation.pdf | Mar 2026; 2025 | VERIFIED (excerpt) |
| Steve Crawford | Program executive, Open Science, OCSDO (Oct 2024) | Open-source tools "are integral to our missions ... used by our researchers, every day"; SMD policy: "as open as possible, as restricted as necessary, always secure" | https://www.nasa.gov/news-release/nasa-funds-open-source-software-underpinning-scientific-innovation ; https://lwn.net/Articles/923223 | 2024; 2023 | VERIFIED (excerpt) |
| Yoseline Angel Lopez | Goddard assistant research scientist, ex-Space Apps winner (Jul 2025) | Her 2021 winning prototype was adopted by Colombia's Ministry of Agriculture; Space Apps gave "validation from NASA scientists and industry experts" | https://www.nasa.gov/directorates/stmd/prizes-challenges-crowdsourcing-program/registration-opens-for-2025-nasa-international-space-apps-challenge/ | Jul 2025 | VERIFIED (excerpt) |
| Anonymous JPL staff (Reddit via Eos) | JPL employees (Oct 2025) | "Today was very somber on lab. It felt like everyone [was] grieving" | https://eos.org/research-and-developments/jpl-workforce-decimated | Oct 14 2025 | VERIFIED (secondhand Reddit) |
| Anonymous Goddard engineers; Barbara Thompson (ex-founder, Center for HelioAnalytics) | NPR (Sep 2026) | "We can't do the work because we don't have our $6 million antenna chamber anymore"; told to "pack as if you are never going to build another propulsion system again"; ~60% of Goddard engineers surveyed plan to leave | https://www.npr.org/2026/09/15/nx-s1-5964919/nasa-employee-relocations-equipment-impacts-missions | Sep 15 2026 | VERIFIED |

### (c) How NASA actually works and adopts tools
- Archives build on a shared stack: IVOA standards, Firefly, pyvo, astroquery, Jupyter notebooks with CI/CD, and now Fornax (cloud JupyterLab next to the data, beta now, "Open to all at full opening at the end of 2026, including community/educational/amateur"). Source: IRSA UP 2026; IVOA Interop Jun 2026 Fornax slides (https://wiki.ivoa.net/internal/IVOA/InterOpJune2026CSPSP/2026-06-Interop-Fornax-plenary.pdf). VERIFIED (excerpt).
- Division of labor in Fornax: HEASARC does client libraries ("mods to astropy, PyVO"), IRSA does notebooks and user support, MAST does cloud cutout services. A tool that plugs into one of these slots has a clear owner. Source: Fornax org chart Aug 24 2026. VERIFIED (excerpt).
- astroquery historically grew by outside contributors writing modules, with two maintainers carrying the load (AJ 2019). Now gated against LLM PRs (README). Openscapes hackday (Aug 2026) discussed "GitHub Actions test suites to triage and evaluate AI contributions". VERIFIED.
- Mission hackweeks feed results into official tutorials: PACE hackweek content is "incorporated into NASA's Ocean Ecology Lab Help Hub" (Oceanography, Jun 2026). VERIFIED (excerpt).
- AI is adopted only with SME review: Science Discovery Engine uses "human-in-the-loop" with SMEs labeling and validating (science.data.nasa.gov, May 2025). VERIFIED (excerpt).
- Cloud is the answer to volume: SPHEREx on AWS (nasa-irsa-spherex bucket), HATS Parquet catalogs praised by panel. VERIFIED.

### (d) Pain points
- Usability and onboarding: clunky interfaces, Firefly complexity, complex docs, students not reached (IRSA UP 2026). Earlier 2024 Archives Review said the same: Firefly UIs "difficult for new users to handle" (https://science.nasa.gov/wp-content/uploads/2024/10/nasa-aar2024-final-tagged.pdf). VERIFIED.
- Time-domain gap: multi-survey, multi-band light-curve access is weak (IRSA UP 2026). VERIFIED.
- SPHEREx-specific traps: LVF means bands of one target are not simultaneous; QR2/QR3/DR1 versions must not be mixed; long jobs get lost; moving objects need motion and rotation corrections (IRSA help, bug list, Lisse). VERIFIED.
- Panel asked IRSA for usage stats and helpdesk traffic summaries, meaning IRSA itself lacks a clear public picture of what users struggle with. VERIFIED.
- AI trust: hallucination, automation bias, lack of traceability (Ramachandran, Bugbee, Murphy). VERIFIED.
- Staff loss: GAO says 25 of 36 major projects felt workforce loss; Goddard lost 34% (SpaceNews Jul 23 2026, https://spacenews.com/nasa-programs-feel-effects-of-workforce-reductions). JPL cut ~550 (11%) Oct 2025, 4th round since 2024. FY2027 request is 23% lower (NPR). VERIFIED.

### (e) What this means for choosing a project (criteria only, not an idea)
- Judges from the archive side will value something that removes a known SPHEREx trap (non-simultaneous bands, version mixing, motion corrections) over a generic image viewer, since IRSA already ships viewers and a source-discovery notebook.
- Anything using AI should show its evidence (which images, which epochs, which version) and keep a human decision step. Black-box claims run against stated NASA practice.
- Building on the existing stack (IRSA APIs, pyvo/astroquery, Firefly, HATS, Fornax notebooks) makes the result look adoptable; the panel's "young students" and "classroom" requests point to a real unserved audience.
- Time-domain, multi-band views are an explicitly named gap by the users who advise IRSA.
- Given staff cuts, framing around saving expert time (triage, fewer helpdesk questions) matches how staff talk.

### (f) Gaps
- No public LinkedIn posts or Reddit AMAs from IRSA/SPHEREx staff found or opened (did not browse LinkedIn per rules).
- Did not open the Planet X and SPHEREx challenge page body (fetch returned only a third-party notice), so the challenge author/SME name is unknown.
- No IRSA helpdesk statistics are public (the panel itself asked for them).
- Eric Rice (SPHEREx Mission Ops Manager, JPL) Cosmic Radio podcast Oct 1 2026 and Rachel Akeson's AAS 248 SPHEREx data talk not listened to. UNVERIFIED content.
- No 2026 TOPS / Open Science 101 numbers retrieved; TOPS status after budget cuts unknown.


---


# Part 10

## Agent 10 - What NASA wants from Space Apps, and what SMEs say about Planet X and SPHEREx
Read-only research, Sat Nov 14 2026. Nothing posted, liked or joined.

### (a) Bottom line
1. NASA describes Space Apps as a "public gateway to NASA science" that puts open data in public hands (Open Government Initiative). It does not describe it as a product pipeline. The metrics it reports are about reach: participants, teams, events, countries, projects, SMEs, Navigators.
2. For 2026, NASA's own article says the astrophysics challenges are about "improving public access to mission data, designing tools that help visualize changes in the sky over time, and supporting broader engagement".
3. Space Apps Connect is GitHub Discussions (github.com/nasa/spaceapps/discussions). It is public and I could read it. The one SME answer on this challenge plus a likely challenge-team member (dancaselden) both say: real multi-epoch SPHEREx data is required, use small cutouts, and synthetic data is only OK for demos if clearly labeled.
4. The challenge is clearly modeled on WiseView and Backyard Worlds (citizen science). The GitHub user "dancaselden" writes "we've used wiseview", and Dan Caselden co-built WiseView. Inference only: the challenge authors probably sit in the Backyard Worlds / citizen science group.
5. Cases where NASA really adopted a project are rare and old (NYSpaceTag 2015). The usual follow-ons are: a trip for winners (launch or Goddard celebration), startups, and funding from outside NASA.

### (b) Program goals table
| Goal or metric | Exact wording or number | Source | Status |
|-|-|-|-|
| Purpose | "a public gateway to NASA science... promote transparency, participation, and global collaboration as part of the Open Government Initiative" | https://www.spaceappschallenge.org/about/ | VERIFIED (read Nov 14 2026) |
| Mission line | "answer the questions that benefit humanity, drive exploration, and exemplify community-driven, gold-standard science" | same | VERIFIED |
| Outcomes claimed | "Participants have gone on to form companies inspired by their projects, develop professional careers via employment opportunities or skill development, and network" | same | VERIFIED |
| Metrics tracked (2025) | 114,094 registered, 18,860 teams, 551 events, 167 countries, 11,511 projects, 14 agency partners, 124 SMEs, 78 Navigators. Cumulative: 487K+ registrations, 3400+ events, 190+ countries | https://www.spaceappschallenge.org/about/results-and-metrics/ | VERIFIED |
| Organizational home | "In 2017... it moved under the NASA Earth Science Division" | same | VERIFIED |
| 2026 focus areas | Moon, deeper solar system, "expanding understanding of the universe" | https://science.nasa.gov/universe/nasa-welcomes-all-ages-experience-levels-for-space-apps-challenge (Oct 15 2026) | VERIFIED |
| 2026 astrophysics intent | "improving public access to mission data, designing tools that help visualize changes in the sky over time, and supporting broader engagement with the scientific products" | same | VERIFIED |
| SMD leader quote 2026 | Nicky Fox (SMD Associate Administrator): "At NASA, science is for everyone..." | same | VERIFIED |
| ESD leader quote | Karen St. Germain (ESD Director): "puts NASA's free and open data into the hands of explorers around the world... real-world applications of agency data" | https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-announces-2025-international-space-apps-challenge-global-winners/ (Dec 18 2025) | VERIFIED |
| Named HQ program executive for 2026 | Not found. The 2026 Meet the Team page lists only first names of the GO Team (Allison through Shawn). The older legacy page lists "Sarah", Booz Allen Lead Associate at ESD, as "lead for Space Apps programming" (likely Sarah Hemmings, quoted in the FY19-20 Open Innovation report) | https://www.spaceappschallenge.org/meet-the-team/ ; https://legacy.spaceappschallenge.org/about/meet-team ; https://www.nasa.gov/wp-content/uploads/2022/01/fy1920openinnovationreport-final.pdf | VERIFIED that it is not listed. Identity of the 2026 lead UNVERIFIED |

### (c) Adoption and follow-on cases
- NYSpaceTag (2015): "currently working with NASA's Open Data team to apply the team's algorithm to data.nasa.gov... NASA plans to offer it to other federal agencies." From the 2015 Mission Report, https://assets.spaceappschallenge.org/media/documents/SpaceApps2015_Mission_Report.pdf. VERIFIED from the search excerpt. Whether it was ever deployed is UNVERIFIED.
- Winner trips: the "Jimmy in the Box" winner was told "we are looking forward to hosting the team at a future mission launch" (https://legacy.spaceappschallenge.org/blog/webb-space-telescope-sparks-innovation, Mar 2022). The 2025 Winners Celebration was held at Goddard, with Lystrup, St. Germain and Fox present, and winners met the SMEs "who authored many of the challenges" (https://www.spaceappschallenge.org/blog/the-nasa-space-apps-2025-winners-celebration). VERIFIED (excerpts).
- Non-NASA follow-on: L.I.V.E. Glacier got an ESA EO Entrepreneurship scholarship (up to EUR 15,000). Scintilla got a sponsor stipend (Supplyframe). Canaria incorporated (2017 Mission Report, https://assets.spaceappschallenge.org/media/documents/SpaceApps2017_MissionReport.pdf). VERIFIED (excerpt).
- NASA SBIR grants, citizen science funding, or a NASA hire tied directly to a Space Apps project: I found no example. UNVERIFIED / not found.

### (d) SME and Connect posts on this challenge
Connect URL: https://github.com/nasa/spaceapps/discussions (public, read Nov 14 2026).
- #2165 "Using a single timestamp vs. simulated time-series data" (label: SME answered). https://github.com/nasa/spaceapps/discussions/2165 VERIFIED
  - Prateek-SME: "A single real observation can demonstrate the initial visualization, but it cannot independently demonstrate how the sky changes over time. It would be best to retrieve small cutouts of one sky region from a few different observation dates."
  - dancaselden (no role label. His "we" suggests the challenge team, UNVERIFIED): "I think we can safely say multi-epoch visualization is required b/c we're looking to visualize changes to the sky over time like the motion of nearby objects. We've used wiseview to do this with WISE imagery". "I think it would be best to use real data but from small portions of sky". "hosting it in e.g., AWS gets expensive". "I could imagine, f/e, adding synthetic faint, high proper motion objects to real data for demo purposes". He points back to the five test targets.
  - Johnna0GO-Team: "to be eligible for a Global Award, you must use at least one NASA data or resource... list all data, resources, and tools".
  - Lightovic (collaborator, not an SME): DR1 = Surveys 1-2 and QR3 = Surveys 3-4 are "the current releases recommended for new work" (citing IRSA docs, Nov 12 2026). Use the SPHEREx Data Explorer with a Timing constraint.
- #1847 IRSA cutouts and epochs by band. https://github.com/nasa/spaceapps/discussions/1847 VERIFIED. Navigators, not SMEs, say to match epochs by wavelength before blinking, because of the linear variable filters (the WCS-WAVE extension). Whether a pre-built dataset will exist "still needs confirmation".
- #2183 data access outage. https://github.com/nasa/spaceapps/discussions/2183 VERIFIED. jayrosen-design: IRSA TAP returns "502 Proxy Error", but SIA works. The example query returned "about 330 SPHEREx DR1 images from 42 different observation days". GO Team tagged the SMEs.
- #2123 GO Team tips (Madison-GO-Team). https://github.com/nasa/spaceapps/discussions/2123 VERIFIED. AI tools are allowed but must be disclosed ("Super Intelligence (SI)"). "Our judges will consider originality, intent, and execution in the context of SI-assisted work." A 2025 winner adds: "be clear about what your prototype actually demonstrates versus what you plan to develop."
- Challenge author: not named on the page. Clues: the page links backyardworlds.org, uses WiseView as "a model or as inspiration", and dancaselden posts in the thread. Dan Caselden co-built WiseView (https://science.nasa.gov/people/dan-caselden). Backyard Worlds is led by Marc Kuchner, SMD Citizen Science Officer (https://science.nasa.gov/people/marc-jason-kuchner/). The author is UNVERIFIED. Side note: Adam Schneider of ASU used WiseView to confirm WISE 1810 (JPL, Jul 2020, https://www.jpl.nasa.gov/news/two-bizarre-brown-dwarfs-found-with-citizen-scientists-help). He is a possible local expert contact. Whether he is still at ASU is UNVERIFIED.

### (e) What this means for choosing a project
- The SME and the likely-author post both say real SPHEREx data from at least two epochs is a hard floor. A project built only on a single epoch or only on synthetic data goes against the only official answer.
- NASA's stated aim for this challenge is public access and citizen discovery (WiseView, Backyard Worlds). Ideas that help the public make real discoveries fit what NASA says it wants.
- The authors' own words hint at what they care about: cheap hosting (AWS cost), staying easy to update as releases arrive (DR1, QR3), and handling the 102 bands and the LVF wavelength quirk well.
- Judges weigh "originality, intent, and execution" for AI-assisted work, so a clear statement of what the demo really shows will count.
- Realistic upside after the event is a celebration trip and visibility with the SMEs. Adoption by NASA is rare, so pick for idea strength and fit, not for an expected handoff to NASA.

### (f) Gaps
- No 2026 NASA HQ program executive or program scientist found by name.
- No GAO or OIG report on Space Apps found (not searched deeply).
- 2026 webinars and bootcamps were not reviewed (out of time).
- Challenge author and dancaselden's role are not confirmed.
- I only read the threads that came up in a "SPHEREx" search on Connect. Newer SME posts may appear during the event.


---


# Part 11

## Agent 11 - Challenge science in plain language, and SPHEREx vs WISE

Labels: VERIFIED = I read the number in the linked source. UNVERIFIED = from memory, a secondary source, or my own arithmetic (noted as "computed").

### (a) Bottom line (5 lines)
1. A single SPHEREx frame is not a color picture: each of the 6 detectors sees a rainbow strip, so one star is measured at 6 wavelengths per frame, and a full 102-channel spectrum takes about 1-2 weeks of repointing. Any "flip-book" must compare like with like (same channel or a per-detector co-add), or brightness flicker will be fake.
2. Motion per 6 months is under 1 pixel for every test target (Barnard's ~0.85 px, WISE 0855 ~0.66 px, Eps Indi B ~0.38 px, the two variables ~0). It becomes obvious only over the full mission or when tied to 15 years of WISE images.
3. The real new power is the spectrum: every moving dot comes with a 0.75-5 micron spectrum, so you can tell a brown dwarf (water/methane dips) from a star or an asteroid (reflected sunlight) or a comet (CO2 gas glow at 4.26 microns).
4. Planet Nine itself is almost certainly too faint for SPHEREx (predicted V ~22, SPHEREx limit ~19.5 AB per channel), and at ~500 AU it would jump ~7 arcmin between 6-month visits, not creep. The realistic "Planet X"-type finds are cold nearby brown dwarfs.
5. Bright test targets (Barnard's Star, R Dra, likely RW Aur) are far above SPHEREx saturation, so flags and artifacts are part of what the tool must show honestly.

### (b) Plain primer
- **Arcsecond (")**: 1/3600 of a degree. SPHEREx pixel = 6.15" ([Expsupp Table 2](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp.pdf), VERIFIED).
- **Magnitude**: brightness scale, bigger = fainter, 5 mag = 100x. "AB" and "Vega" are two zero points; near-IR Vega mags convert to AB by adding ~0.9 (J), ~1.4 (H), ~1.85 (Ks), ~3.34 (WISE W2) (UNVERIFIED, standard 2MASS/WISE offsets from memory).
- **Planet X / Planet Nine**: "Planet X" is the old name for any unseen planet beyond Neptune. "Planet Nine" is the current hypothesis that a ~6.6 Earth-mass planet at ~500 AU explains clustered orbits of distant icy bodies; predicted V ~22.0 ([Brown et al 2024, PS1 search](https://iopscience.iop.org/article/10.3847/1538-3881/ad24e9), VERIFIED). WISE already ruled out a Saturn-size body to 10,000 AU and Jupiter-size to 26,000 AU ([NASA 2014](https://www.nasa.gov/news-release/nasas-wise-survey-finds-thousands-of-new-stars-but-no-planet-x), VERIFIED). A small cold Planet Nine mostly reflects sunlight at 2.5-5 microns, so WISE could only have seen Neptune itself out to ~70 AU ([Brown & Batygin 2016](https://iopscience.iop.org/article/10.3847/2041-8205/824/2/L23), VERIFIED).
- **Brown dwarf**: a "failed star" too light to fuse hydrogen, so it cools forever. Types by temperature: L (~2,500 K) to T (methane appears) to Y (coldest, down to ~250 K) ([SPHEREx BD sequence paper](https://iopscience.iop.org/article/10.3847/1538-4357/ae9d66), VERIFIED range L0-Y4, 2500-250 K). They are dim in visible light and brightest in infrared, which is why WISE and SPHEREx find them.
- **Proper motion**: a nearby object's real drift across the sky, in "/yr. **Parallax**: a yearly back-and-forth wobble because Earth orbits the Sun; amplitude in arcsec = 1/distance in parsecs. Close objects have both large, so "fast mover" usually means "very close".
- **Asteroids/comets in SPHEREx**: they move noticeably between exposures minutes to days apart. Asteroids show reflected sunlight; comets can show gas glow, e.g. SPHEREx saw a CO2 coma around interstellar comet 3I/ATLAS reaching at least 348,000 km ([SPHEREx news](https://spherex.caltech.edu/news/3i-atlas-co2-coma), VERIFIED) and methanol/cyanide/methane in Dec 2025 ([NASA](https://science.nasa.gov/blogs/spherex/2026/02/04/nasas-spherex-mission-tracks-brightening-of-interstellar-comet), VERIFIED). The pipeline predicts known solar-system object positions per frame (tool "kete") into an ancillary file ([pipeline paper](https://iopscience.iop.org/article/10.3847/1538-4365/ae8843/pdf), VERIFIED).
- **Variable stars**: stars whose brightness changes. R Draconis is a Mira (pulsating red giant), V 6.7-13.2, period 246.12 d ([AAVSO VSX](https://vsx.aavso.org/index.php?view=detail.top&oid=13673&image=poss2ukstu_red), VERIFIED). RW Aurigae is a young (~3 Myr) T Tauri binary that has had repeated ~2 mag dimmings since 2010, likely dust from its disk crossing our line of sight ([Rodriguez et al 2018](https://arxiv.org/html/1804.09190v2), VERIFIED); dimmings reached dV ~5 mag ([2018 multi-band photometry paper](https://arxiv.org/html/1811.00449v1), VERIFIED). Why chosen (my inference, UNVERIFIED): R Dra is regular and sits ~9 deg from the north ecliptic pole (computed), where SPHEREx revisits often, so it tests a light curve; RW Aur tests irregular, color-dependent dimming.

### (c) How SPHEREx takes data
- **Linear variable filter (LVF)**: a filter whose passband wavelength changes smoothly along one axis of the detector. So one frame = 6 detectors x a rainbow gradient; each star lands on one wavelength per detector. The spacecraft steps in small slews (17') so the same star lands on the next channel ([pipeline paper](https://iopscience.iop.org/article/10.3847/1538-4365/ae8843), VERIFIED). Full 102 channels for one object take ~1-2 weeks ([Bock et al 2026](https://iopscience.iop.org/article/10.3847/1538-4357/ae2be2), VERIFIED).
- **Six arrays** (2 focal planes split by a dichroic; Expsupp Table 2, VERIFIED): B1 0.744-1.116 um R=39; B2 1.099-1.651 R=41; B3 1.636-2.421 R=41; B4 2.423-3.822 R=35; B5 3.809-4.420 R=112; B6 4.412-5.002 R=128. R = wavelength / smallest resolvable wavelength step. 17 channels per array (102/6, computed).
- **Exposure** 113.58 s; field 2 x (3.5 x 11.3 deg) (Expsupp, VERIFIED). PSF FWHM 3.6-5.5" by band in the simulator ([Sky Simulator](https://iopscience.iop.org/article/10.3847/1538-4365/ae04cc), VERIFIED) but one real band-2 header shows 7.5" ([IRSA tutorial](https://caltech-ipac.github.io/irsa-tutorials/spherex-intro/), VERIFIED).
- **Depth**: 5-sigma 19.5-19.9 AB (0.75-3.8 um) and 17.8-18.8 AB (3.8-5 um) per channel after all 4 sky passes (Bock et al 2026, VERIFIED). One pass is roughly 0.75 mag shallower (computed, UNVERIFIED). Saturation starts ~11.3-11.7 AB (B1-B4), ~9.8-10.2 AB (B5-B6) ([Expsupp QR v1.1](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp_QR_v1.1.pdf), VERIFIED); sources brighter than ~6 AB saturate in under 2 samples ([SPHEREx 2024 overview](https://arxiv.org/html/2404.11017v1), VERIFIED).
- **Survey**: whole sky every ~6 months; surveys 1/2 have opposite filter orientation, surveys 3/4 shifted half a channel; deep fields (~100 sq deg each) near the ecliptic poles (Bock et al 2026; [Expsupp QR](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp_QR.pdf), VERIFIED).
- **Spectral image** = one calibrated detector frame (MJy/sr) with FLAGS, VARIANCE, ZODI, PSF and a WCS-WAVE table giving wavelength per pixel. Flags include NONLINEAR (saturation-related), PERSIST, GHOST, CROSSTALK, BLOOM, SOURCE (IRSA tutorial, VERIFIED). Note: no "moving object" flag in the pixel mask (VERIFIED from flag list).
- **All-sky cube** = 102 full-sky mosaics, one per channel, with flux, variance, coverage, flags ([pipeline paper](https://arxiv.org/html/2511.15823v2), VERIFIED).

### (d) Test targets
6-month shift = proper motion / 2, compared with a 6.15" pixel (computed). Parallax can add up to ~2x parallax between opposite-season visits (computed, UNVERIFIED).

| Target | Type | Proper motion | 6-month shift vs pixel | Expected visibility in SPHEREx | Spectral notes | Source |
|-|-|-|-|-|-|-|
| Barnard's Star | M4 red dwarf, 1.83 pc | 10.39"/yr; parallax 547 mas | ~5.2" = 0.85 px (+ up to ~1.1" parallax) | Shift visible in a blink; 2-yr total ~3.4 px. Ks 4.52 Vega = ~6.4 AB, so heavily saturated, expect NONLINEAR/ghost flags | M-dwarf water bands; photometry unreliable | [Exoplanet Archive](https://exoplanetarchive.ipac.caltech.edu/overview/Barnards%20star) VERIFIED; AB conversion UNVERIFIED |
| WISE 0855-0714 | Y4 brown dwarf, ~250 K, 2.28 pc | 8.15"/yr; parallax 439 mas | ~4.1" = 0.66 px (+ up to ~0.9") | Invisible below ~4 um (J 25.0, H 23.8 Vega); only in B5-B6 (W2 14.02 Vega = ~17.4 AB, near the 17.8-18.8 AB limit), so faint, best in co-adds | 4-5 um shaped by water; JWST found CH4, H2O, NH3, CO, no confirmed water-ice clouds | [Wikipedia summary](https://en.wikipedia.org/wiki/WISE_0855%E2%88%920714), [Luhman & Esplin 2016](https://iopscience.iop.org/article/10.3847/0004-6256/152/3/78/meta) VERIFIED; S/N estimate UNVERIFIED |
| Eps Indi Ba/Bb | T1-1.5 + T6 brown dwarf pair, 3.7 pc | ~4.68"/yr (+3982, -2467 mas/yr); parallax 271 mas | ~2.3" = 0.38 px | Pair 0.73" apart, so one blended dot. Combined J ~11.8, K ~11.3 Vega: bright, high S/N, below saturation. Primary star 402" away may add ghosts | Composite T-dwarf spectrum: methane + water dips; strong 4 um peak | [Wikipedia](https://en.wikipedia.org/wiki/Epsilon_Indi), [McCaughrean 2004](https://arxiv.org/html/astro-ph/0309256v2), [King et al 2010](http://www.astro.ex.ac.uk/people/rob/Publications/epsindib.pdf), [2022 dynamical-mass paper](https://iopscience.iop.org/article/10.3847/1538-3881/ac66d2) VERIFIED |
| RW Aurigae | Young T Tauri binary (1.45" apart), 164 pc | ~28 mas/yr | ~0.002 px, no motion | Brightness change, not motion; likely nonlinear in B1-B4 (K ~7 Vega, UNVERIFIED) | Disk dust and gas; dimming depth differs by wavelength | [Wikipedia](https://en.wikipedia.org/wiki/RW_Aurigae), Rodriguez 2018 VERIFIED |
| R Draconis | Mira, M5e-M9eIII, 246 d | ~22 mas/yr | ~0.002 px, no motion | Brightness change; IRC +70136 entry implies K brighter than ~3 (UNVERIFIED), so deeply saturated; many polar revisits | Cool giant: water, CO bands | [AAVSO VSX](https://vsx.aavso.org/index.php?view=detail.top&oid=13673&image=poss2ukstu_red) VERIFIED |

### (e) SPHEREx vs WISE/NEOWISE

| Aspect | WISE/NEOWISE | SPHEREx | Net |
|-|-|-|-|
| Colors | W1 3.4, W2 4.6 um after 2010 cryo (2 bands) | 102 channels 0.75-5 um | SPHEREx much better |
| Pixel | 2.75" ([NEOWISE](https://irsa.ipac.caltech.edu/data/WISE/docs/release/NEOWISE/), VERIFIED) | 6.15" | WISE ~2.2x finer |
| Baseline | Jan 2010 - Aug 1 2024, 21.3 sky passes, 12+ exposures per pass (NEOWISE, VERIFIED) | May 2025 - ~mid 2027, 4 passes (Bock 2026) | WISE far longer |
| Depth | CatWISE2020 90% complete W1 17.7, W2 17.5 Vega ([CatWISE2020](https://iopscience.iop.org/article/10.3847/1538-4365/abd805), VERIFIED) | ~19.5-19.9 AB per narrow channel | Similar order; WISE deeper at 4.6 um broadband (UNVERIFIED comparison) |
| Motion precision | CatWISE ~20 mas/yr at W1 15 (VERIFIED) | Not yet published for SPHEREx | Unknown |
| Track record | Backyard Worlds volunteers found >3,000 new brown dwarfs, doubling the known count ([NASA May 2026](https://science.nasa.gov/get-involved/citizen-science/nasa-volunteers-double-known-population-of-brown-dwarfs), VERIFIED) | Spectra for thousands of nearby brown dwarfs (BD sequence paper, VERIFIED) | Complementary |

What becomes possible (described, not proposed): confirm a mover is a brown dwarf from its spectrum instead of only two colors; estimate its type and temperature; tell asteroids (sunlight-like spectrum) from comets (CO2 4.26 um, CO 4.7 um, water near 3 um) from stars; tie SPHEREx positions to 2010-2024 WISE positions for a 15-year lever arm (Eps Indi B moves ~75" = ~12 SPHEREx px from 2010 to 2026, computed); watch brown dwarf and young-star brightness change per wavelength.

### (f) Genuinely open science questions
1. Does Planet Nine exist at all? Searches (ZTF, PS1, parallax-based) find nothing so far ([ZTF](https://iopscience.iop.org/article/10.3847/1538-3881/ac32dd), [2025 parallax-based search](https://arxiv.org/html/2504.05473v2), VERIFIED).
2. How many cold Y dwarfs and free-floating planetary-mass objects sit within ~10 pc? Census still incomplete (inference from the 2026 doubling, UNVERIFIED).
3. Atmosphere models still fail at the L/T transition, the 4 um window and CO/CO2 features (BD sequence paper, VERIFIED).
4. Brown dwarf weather and variability between SPHEREx epochs is only starting to be studied (Huang et al 2026 cited in [SUDA](https://iopscience.iop.org/article/10.3847/1538-4357/ae9082), VERIFIED mention).
5. Methods problem (inference, UNVERIFIED): measuring sub-pixel motion when each epoch is a different wavelength with a different PSF, and linking unknown movers across sparse 6-month gaps.
6. What causes RW Aur's repeated dimming (disk warps, tidal stream, dust lifted by winds)? Still debated (Rodriguez 2018, VERIFIED that it is debated across papers).

### (g) What this means for choosing a project
- Any image sequence must handle the "every frame is a different color" fact; this is the main scientific trap of the challenge.
- Motion of the test targets is small per epoch, so long-baseline context (WISE or multi-pass co-adds) decides whether motion is visible at all.
- Spectra are the scientific edge over WiseView; the judges' "extra kudos" points there.
- Bright targets will be saturated and flagged; showing flags is part of being scientifically honest.
- Planet Nine detection is out of reach for SPHEREx; the credible discovery space is brown dwarfs, comets and asteroids, and variability.


---


# Part 12

## Agent 12 - What professional astronomers say they wish existed (SPHEREx / Planet X area)
Researched Sat Nov 14 2026. Read-only. VERIFIED = I read the wording myself in the source or its abstract/excerpt. UNVERIFIED = secondhand or the date/author could not be checked.

### (a) Bottom line
1. The loudest wish, "spectra for thousands of Backyard Worlds candidates", is now mostly solved: Gagne et al. 2026 (SPIFF/MOCAdb) typed 6,003 ultracool dwarfs from SPHEREx, including 1,937 of the 3,006 Backyard Worlds candidates. A tool that only "classifies brown dwarf spectra" repeats existing work.
2. Still open and stated in several papers: the coldest objects (Y dwarfs) are missing, especially in the crowded Galactic plane, and the team says pixel-level deep learning on archival data is promising (SMDET-1, Jul 2026).
3. Still open for SPHEREx itself: artifacts (ghosts, crosstalk, satellites, persistence) and moving-object spectra, where rotation and distance change across the multi-day spectral sampling. The pipeline team lists these as future work.
4. Leftovers nobody has a public workflow for: SPIFF flagged 865 "possibly peculiar", 250 subdwarf and 2,668 young candidates "for future investigation", and ~1,069 Backyard Worlds candidates that did not get enough SPHEREx channels.
5. The AI and citizen science report (CCC, Feb 2026, which Kuchner promoted) asks for explainable AI for non-experts, uncertainty visualization, human-AI teaming for anomaly detection, and real-time feedback to volunteers.

### (b) Wish list (strongest / most often stated first)
| # | Wish / unsolved problem | Who | Quote or paraphrase | Link | Date | Already solved by? | Verified? |
|-|-|-|-|-|-|-|-|
| 1 | Spectroscopic confirmation of thousands of motion-selected candidates | Schneider et al. (Backyard Worlds) | "Follow-up spectroscopic observations will be necessary to confirm spectral types and further characterize the sources" | arxiv.org/abs/2604.01323 | Apr 1 2026 | Mostly: SPIFF / MOCAdb (Gagne et al.) confirmed 3,953 L0-Y1, 1,937 from Backyard Worlds; it "opens the doors to efficient confirmation" | VERIFIED |
| 2 | Coldest brown dwarfs (<600 K, Y dwarfs) still incomplete; Galactic plane under-counted | Kirkpatrick et al. 20 pc census | "still incomplete beyond 15 pc, and the completeness volume shrinks to 11 pc at 450 K"; plane Y dwarf underdensity "is now significantly worse" | iopscience.iop.org/article/10.3847/1538-4365/ad24e2 | Apr 9 2024 | Partly: SMDET deep learning (row 3), CatWISE, Backyard Worlds | VERIFIED |
| 3 | Search crowded archival fields with pixel-level ML for moving objects | Meisner, Caselden, Kirkpatrick et al. | SMDET-1 "illustrates the importance of continued searches for nearby brown dwarfs within archival datasets like WISE and Spitzer, as well as the potential of pixel-level deep learning to discover astronomical moving objects that challenge traditional data analysis approaches" | arxiv.org/abs/2608.00046 | Jul 24 2026 | Partly: SMDET on unWISE only; no SPHEREx equivalent found | VERIFIED |
| 4 | Follow-up of flagged oddballs | Gagne, Faherty, Kuchner et al. (SPIFF) | 2,668 young, 250 subdwarf and 865 "possibly otherwise peculiar" flagged "for future investigation" | arxiv.org/abs/2604.22012 | Apr-May 2026 | No public triage or review workflow found | VERIFIED |
| 5 | Atmosphere models fail; need data to fix them | Rustamkulov et al.; Kirkpatrick quote | "understanding of their nature is limited by model systematics rather than observational uncertainty"; Kirkpatrick: "we have thousands more that we are in the process of analyzing" | iopscience.iop.org/article/10.3847/1538-4357/ae9d66 ; nasa.gov SPHEREx brown dwarf release | Sep 28 / Oct 8 2026 | No (theory problem); SUDA also finds ~1.05 dex log g offset | VERIFIED |
| 6 | Better artifact handling in SPHEREx images | SPHEREx pipeline paper (ApJS); bestiary paper; Fazar persistence paper | Future work: "Improved transient flagging ... Earth-orbiting satellites and extended cosmic rays"; better masking of "frame edge ghosts", "electrical crosstalk", "optical ghosts", moon glow; in-flight persistence deferred to a follow-up paper | iopscience.iop.org/article/10.3847/1538-4365/ae8843 ; arxiv.org/html/2608.09862v2 ; arxiv.org/html/2608.21639v1 | Aug 2026 | Partly: pipeline flags (BLOOM, SNOWBALL, persistence masks) | VERIFIED (pipeline paper author list not checked) |
| 7 | Moving-object spectra: correct for rotation and changing distance over days | Bock et al. mission paper; LPSC 2026 abstract; Ariel paper | "care must be taken to account for the effects of rotation and changing distance"; "Work is ongoing to improve the systematics removal"; calibration "challenging, as the observations are not simultaneous for all wavelengths" | arxiv.org/html/2511.02985v1 ; hou.usra.edu/meetings/lpsc2026/pdf/1833.pdf ; arxiv.org/html/2610.35825v1 | Nov 2025 - Oct 2026 | Partly: SOLO lightcurves for ~10^3 asteroids | VERIFIED |
| 8 | Spectra of extended moving objects (comets) | IRSA 3I/ATLAS page; Lisse et al. | IRSA does "not recommend using the SPHEREx Spectrophotometry Tool, which is designed for point-like or nearly point-like sources"; Lisse used manual aperture/annulus photometry | irsa.ipac.caltech.edu/data/SPHEREx/docs/comet3iatlas/ ; iopscience.iop.org/article/10.3847/2515-5172/ae3f95 | Jan 2026 | No public tool found | VERIFIED |
| 9 | Planet Nine IRAS-AKARI candidate needs a third position | Phan, Goto; Brown (Science) | Goto: "The two detections from IRAS and AKARI alone are insufficient to determine the orbit"; Brown computed ~120 deg tilt, so not his Planet Nine | astronomy.com/science/have-astronomers-found-planet-nine/ ; science.org article | May 2025; Nov 2026 coverage | No; DECam / Rubin follow-up proposed | VERIFIED (quotes via press) |
| 10 | Science team hand-checks every volunteer submission | Schneider et al. | TYGO form "has over 102,000 individual submissions. Each ... individually inspected by members of the science team" | arxiv.org/html/2604.01323v1 | Apr 2026 | No automated pre-check found | VERIFIED |
| 11 | Volunteers cannot check if a candidate was already submitted | Backyard Worlds Talk thread 694 | Q: "is there a list of earlier submissions I can check before posting a candidate?" A: "Not that I know of." | zooniverse.org/projects/marckuchner/backyard-worlds-planet-9/talk/694 | 2026 (exact date not seen) | Partly: Schneider 2026 table as stopgap | UNVERIFIED (poster and date not checked) |
| 12 | Rubin solar system data hard to reach; community workaround "unsustainable" | Rubin Users Committee 2026A | Data "not currently served through any alert broker, nor is it accessible on the RSP"; SSSC community database "is unsustainable as data rates increase" | community.lsst.org/t/users-committee-report-2026a-april-27/12064 | Apr 27 2026 | Partly: PPDB coming; citizen-built MVP linking unlinked alerts to MPC orbits (Sibilev, Jul 2026) | VERIFIED |

Also noted (not a wish, but a prior-art risk): "Spaxel" (kanishkkacholia.com/projects/spaxel) already builds SPHEREx cubes, click-pixel spectra, Gaia cross-match with proper motion and "search by spectral feature" with a brown dwarf preset. Date and whether it is a Space Apps entry: UNVERIFIED. IRSA's Spectral Cube Cutout tool was scheduled for Nov 2026 (Bock et al. Table 5).

### (c) The "AI and citizen science" report
Identified as: CCC (Computing Community Consortium, NSF-backed) "Grand Challenges for the Convergence of Computational and Citizen Science Research", released Feb 23 2026 (revised Jun 30 2026), 46 experts, workshop Apr 8-9 2025. Lead authors include Lucy Fortson (Zooniverse). Kuchner posted the May 20 2026 webinar on Bluesky ("I have a 5-minute cameo"). VERIFIED.
Key points (from the Key Recommendations brief, read directly):
- Human-AI teaming frameworks, including LLMs, for "task assignment, anomaly detection, and data collection or labeling of large datasets".
- "Develop explainable AI for non-expert users": new UI and data visualization so AI decisions are "transparent and interpretable to the general public".
- Toolkits that explain AI behavior "including uncertainty visualization, explainable model outputs, and citizen-led model critique workflows".
- "Real-time feedback systems": adaptive, multilingual, just-in-time feedback during data collection and analysis.
- Interoperable, AI-ready FAIR data, provenance capture across human actions and model versions, trust metrics.
- Kuchner at the webinar (CRN, Jun 2 2026): volunteers now build their own AI tools; "With AI/ML, anyone can be a scientist, or pretend to be one. That makes educating and guiding the public via real citizen science even more important".

### (d) What this means for choosing a project
- Plain "classify brown dwarf spectra" or "click a pixel, see a spectrum with Gaia overlay" is already done (SPIFF/MOCAdb, Spaxel, IRSA tools). Judges who know the field will see it as repeat work.
- The gaps scientists state themselves are: Y dwarfs hidden in crowded Galactic plane fields, the ~1,000 candidates and 865 "peculiar" objects left without triage, artifact confusion (ghosts, persistence, satellites), and moving-object spectra distorted by time-sampling.
- Citizen-science gaps with written backing: science-team review load (102,000 hand-checked submissions), no duplicate-check for volunteers, and the CCC call for explainable, uncertainty-aware AI that volunteers can question.
- Planet Nine angle: the field wants third-epoch confirmation of slow movers (IRAS-AKARI candidate). This is linked to, but different from, the SPHEREx brief (SPHEREx sees 0.75-5 um, the candidate was found in far-IR).
- Strongest evidence = rows 1-3 and 6-7 (several papers each). Rows 10-12 rest on one source each.

### (e) Gaps
- Did not read full conclusions of Bock, Akeson or Korngut 2026, or the full Lisse papers; used abstracts and excerpts.
- Not found: Astro2020 decadal wording, NASA citizen science strategy text, Zooniverse ML roadmap, IVOA spectral cube visualization needs, Euclid/Roman/Rubin + SPHEREx combination wishes, Rubin brown dwarf science needs.
- Rogue Worlds (Faherty) and free-floating planet wishes were skipped as already known.
- Talk thread 694 poster and date not checked.


---


# Part 13

## Agent 13 - Planet X and SPHEREx competition map (read-only, Nov 14 2026)

### (a) Bottom line
1. The Planet X and SPHEREx challenge has **1,380 registered teams** (Space Apps API totalCount; the default Teams tab shows 891 because it filters to "Looking For Members"). Only **114 teams have filled in project text**, 80 of them marked submitted. About 17 of the 114 are off-topic or empty (they never mention SPHEREx).
2. The "regular" project is: enter RA/Dec or pick a preset (Barnard's Star, WISE 0855, Epsilon Indi B, 3I/ATLAS), pull IRSA cutouts, then blink or time-lapse them, with a band selector, a Gaia/WISE overlay and an AI or chatbot layer on top. In keyword hits across the 114: movers 67, blink 47, 102-band 47, AI/ML 39, WISE 40, timeline 40, brown dwarf 39, subtraction 36, citizen/volunteer 44, presets 32, Gaia 31.
3. A strong minority is already science-grade: LVF-aware matched-wavelength pairs (9 teams), JPL/known-asteroid ID (22), injection-recovery or validation (about 10), parallax-aware motion fits (8), provenance or reproducible dossiers (14).
4. Features almost nobody covers: shift-and-stack along a motion vector (0 teams), precovery (0), searching along hypothetical Planet X orbits (0), spectrum change per epoch for a moving object (about 1), spectral classification of movers (about 1 weak), MPC ADES export (1), weekly-release auto-ingest or alerts (2), satellite-streak handling (1 plus 1 GitHub repo), polar deep-field focus (4), real data sonification (about 4).
5. Existing non-hackathon tools already do blink, difference imaging, shift-and-add and synthetic-object injection (WiseView, WISE only), share links and blink via the URL (Legacy Viewer), and orbit-based precovery on SPHEREx (IRSA MOST since June 2026). None of them do SPHEREx time-domain blinking.

Method note: team data came from the same GraphQL API that feeds the site's Project tab (api.spaceappschallenge.org, read-only query, 1,380 records). Feature counts are regex keyword hits on name + summary + details + solution text. They are approximate (I removed obvious false positives where I checked context, noted in the matrix). The full 114-row table is in agent13-all-114-teams.md in the same folder.

### (b) Team list (30 most relevant of the 114; full list in agent13-all-114-teams.md)
| Team | Approach | Link | Verified? |
| --- | --- | --- | --- |
| Team Oblivion | SPHEREx Explorer: bilingual, blink/compare, LVF-aware wavelength matching, JPL SBIdent + Horizons, AllWISE/2MASS/DSS ~75-yr comparison, game, 3D | https://www.spaceappschallenge.org/2026/find-a-team/team-oblivion/?tab=project ; https://github.com/minhaz-42/spherex-explorer | VERIFIED (project text via site API) |
| AEC | SkyShift: RA/Dec time-lapse, fits motion from SPHEREx alone, checks vs Gaia/AllWISE, shareable link | https://www.spaceappschallenge.org/2026/find-a-team/aec/?tab=project ; https://skyshift-seven.vercel.app | VERIFIED (project text via site API) |
| SkyShift Cyprus | SkyShift time machine: candidate labels, reproducible dossier (HTML/PDF/FITS ZIP), CSV/JSON/MPC ADES export, URL query + embed, accessibility | https://www.spaceappschallenge.org/2026/find-a-team/skyshift-cyprus/?tab=project ; https://samuelakosaonyejekwe.github.io/skyshift-spherex/ | VERIFIED (project text via site API) |
| Nakshatra Chronos | "Tries to prove itself wrong": only fair (same array, matched colour) pairs, 3 independent change methods, injection test 29/120 recovered | https://www.spaceappschallenge.org/2026/find-a-team/spherex-chronos/?tab=project ; https://github.com/PRITIDIPADAS/nakshatra-chronus | VERIFIED (project text via site API) |
| Specula | Full pipeline on 1,401 images (99 GB) of 5 fields; NEP used as false-alarm control; built for weekly releases | https://www.spaceappschallenge.org/2026/find-a-team/specula/?tab=project ; https://specula-nasa.vercel.app | VERIFIED (project text via site API) |
| Vanilla Sphere | Blink comparator; recovers known asteroids in 3 test fields; Epsilon Indi B 4.68"/yr vs Gaia; 0.75-5 um spectrum in plain sentences | https://www.spaceappschallenge.org/2026/find-a-team/vanilla-sphere/?tab=project ; https://vanillasphere.com | VERIFIED (project text via site API) |
| Chronocosmos | SPHEREx Time Machine: movie of every visit + 2MASS (2000) and WISE (2010) for 26-yr baseline, predicted future path | https://www.spaceappschallenge.org/2026/find-a-team/chronocosmos/?tab=project ; https://github.com/hd189b/SPHEREx-Open-Sky-Observatory | VERIFIED (project text via site API) |
| Red-Shift | Trace-X: photutils pipeline, 72 sources x every exposure = 8,640 spectrum points, crossfade blink, 102-band selector | https://www.spaceappschallenge.org/2026/find-a-team/red-shift/?tab=project ; https://github.com/Ashhajj0/SPHEREX-And-PLANETX | VERIFIED (project text via site API) |
| Phantom Signal | SkyBlink: telescope eyepiece UI, 3I/ATLAS, Aladin Lite | https://www.spaceappschallenge.org/2026/find-a-team/phantom-signal/?tab=project ; https://skyblink.vercel.app/ | VERIFIED (project text via site API) |
| 8 BIT | PrismBlink OS: GPU temporal difference imaging, LVF-aware, Gaia DR3 + WISE/NEOWISE baseline, methane/water/CO templates (draft) | https://www.spaceappschallenge.org/2026/find-a-team/dhi/?tab=project | VERIFIED (project text via site API) |
| AstroFreak | PlanetHunter: stationary vs linear vs parallax motion models; synthetic movers injected into real backgrounds (draft) | https://www.spaceappschallenge.org/2026/find-a-team/astrofreak/?tab=project ; https://planethunter.streamlit.app/ | VERIFIED (project text via site API) |
| Forough | ParallaxStack: parallax-aware alignment + multi-temporal stacking | https://www.spaceappschallenge.org/2026/find-a-team/forough/?tab=project ; https://github.com/wfrghh-code/ParallaxStack- | VERIFIED (project text via site API) |
| Skill-Issue | SPHEREx Blink: brown dwarf methane dip at 3.3 um, honest ~1"/yr precision | https://www.spaceappschallenge.org/2026/find-a-team/skill-issue2/?tab=project ; https://spherexblink.vercel.app | VERIFIED (project text via site API) |
| New York Style Cellphone | Wanderer: uses IRSA MOST lists, then measures movers (draft) | https://www.spaceappschallenge.org/2026/find-a-team/new-york-style-cellphone/?tab=project ; https://spherex-wanderer.vercel.app | VERIFIED (project text via site API) |
| Wanderer | Wanderer: See the SPHEREx Sky Move (asteroids, comets, fast stars, 3I/ATLAS) | https://www.spaceappschallenge.org/2026/find-a-team/wanderer/?tab=project ; https://wanderer.stellar-trace.tech | VERIFIED (project text via site API) |
| Schwarzschildren | ORBIT-LENS: high-proper-motion search, Gaia/2MASS TAP, WCAG flicker cap 3 Hz, Web Audio sonification | https://www.spaceappschallenge.org/2026/find-a-team/schwarzschildren/?tab=project ; https://nsac-2026.vercel.app/ | VERIFIED (project text via site API) |
| Selenites | Ashesha: follow comet 3I/ATLAS, sound for low-vision users, guided narration (draft) | https://www.spaceappschallenge.org/2026/find-a-team/selenites/?tab=project | VERIFIED (project text via site API) |
| Pleiades7 | Cosmic Detective: story-driven multiplayer citizen science, training missions then open portal | https://www.spaceappschallenge.org/2026/find-a-team/pleadies/?tab=project ; https://github.com/YeadMuhammad/Cosmic-Detective | VERIFIED (project text via site API) |
| Team Sparks | Cosmic Hunt: 3D browser game, Ask-AI box, NASA sounds | https://www.spaceappschallenge.org/2026/find-a-team/team-sparks1/?tab=project ; https://github.com/topu-10j/Cosmic-Hunt | VERIFIED (project text via site API) |
| SphereX | Sky Detective: story-driven web game, Three.js, offline (draft) | https://www.spaceappschallenge.org/2026/find-a-team/spherex/?tab=project ; https://cemyurtlak.github.io/spherex-gokyuzu-dedektifi/ | VERIFIED (project text via site API) |
| Nebula Nexus | NOVOCHAR (Bangla name): NEP two epochs, SHA-256 provenance | https://www.spaceappschallenge.org/2026/find-a-team/team-voyager4/?tab=project ; https://github.com/muhammadmuhtasim/novochar | VERIFIED (project text via site API) |
| The Summit Society | Luma Sphere: stand inside the 102-band all-sky map, proper-motion correction, time-lapse planned | https://www.spaceappschallenge.org/2026/find-a-team/the-summit-society/?tab=project ; https://github.com/3ch0less/spaceappsproject.git | VERIFIED (project text via site API) |
| 24voltt | COSMIC COMMONS: 3D atlas, research lab, spectral explorer, blink comparator, anomaly engine, offline cache | https://www.spaceappschallenge.org/2026/find-a-team/24voltt/?tab=project ; https://cosmic-work.vercel.app/explore | VERIFIED (project text via site API) |
| A-JINX | Chrono & Spatial: difference maps, statistical change detection, IRSA + JPL | https://www.spaceappschallenge.org/2026/find-a-team/a-jinx/?tab=project ; https://github.com/ProgrammerJibon/NasaAppChallenge2026ChronoSpatial | VERIFIED (project text via site API) |
| RAM_Shortman | Temporal Subtraction & Anomaly Engine | https://www.spaceappschallenge.org/2026/find-a-team/ram_shortman/?tab=project ; https://github.com/faiyazkon/spherex_challenge.git | VERIFIED (project text via site API) |
| II-MAX | SPHEREx Time-Domain Explorer: AI-assisted citizen science (draft) | https://www.spaceappschallenge.org/2026/find-a-team/ii-max/?tab=project ; https://github.com/II-Max/Planet-X-and-SPHEREx | VERIFIED (project text via site API) |
| Dunkle Materie | SPHEREx Spotter: Planet 9 and brown dwarfs, HEALPix tiling (design only) | https://www.spaceappschallenge.org/2026/find-a-team/dunkle-materie/?tab=project ; https://drive.google.com/file/d/1LkiAcF57KkNtZr6Um9M9RAUhdRjAKZcI/view?usp=drivesdk | VERIFIED (project text via site API) |
| FROM NILE TO STARS | BlinkSphere: spectrum sonification for visually impaired users | https://www.spaceappschallenge.org/2026/find-a-team/spectrum-explorers/?tab=project ; https://blinksphere.vercel.app/ | VERIFIED (project text via site API) |
| Kepler-22 | SkyBlink: Arabic + English, captions, sound (pixels simulated, stated) | https://www.spaceappschallenge.org/2026/find-a-team/kepler-22/?tab=project ; https://joamir10.github.io/nasa26/ | VERIFIED (project text via site API) |
| 1401 | planetXplorer: RA/Dec + FOV, aligned image timeline | https://www.spaceappschallenge.org/2026/find-a-team/1401/?tab=project ; https://planet-x-plorer.vercel.app/ | VERIFIED (project text via site API) |

The other teams already known from the X/YouTube scan: Ahmed Wael "Sky Time Machine" and OSCAR (@willy_wonka_28) were not matched by name in the API data. "Null Point" (SPHEREx sky time machine, short sky videos) and "Anvild" (SkyBlink) may be related. UNVERIFIED link between them.

### (c) Existing tools (non-hackathon)
| Tool | What it does (relevant to this challenge) | Link | Verified? |
| --- | --- | --- | --- |
| WiseView (AMNH, Backyard Worlds) | WISE/NEOWISE only. Blink with interval control, sliding time window, W1/W2/W1+W2, difference imaging, shift and add, synthetic object injection, Gaia DR3 overlay, separate scan directions, skip epochs | http://byw.tools/wiseview | VERIFIED (control list read) |
| Legacy Survey Viewer | Space bar flips between layers (blink), &blink= URL param, "Link Here" permalink, &mark/&poly annotations, JPEG/FITS cutout URLs, "Discuss This Object" forum link | https://www.legacysurvey.org/svtips | VERIFIED |
| IRSA SPHEREx Data Explorer (Firefly) | Position, multi-object, timing and spectral constraint search; HiPS coverage map with all-sky and deep-field MOC; image, table and plot panes; catalog overlays (IRSA catalogs, TAP, NED, upload); Spectrophotometry tab. Docs say "other functionality will come in time" | https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/overview.html | VERIFIED (docs) |
| IRSA MOST | Computes an orbit for a named or MPC object (or manual elements), finds SPHEREx/WISE/ZTF/2MASS images on its predicted path, orbit plot, precovery. SPHEREx support since June 2026 | https://irsa.ipac.caltech.edu/applications/MOST ; https://caltech-ipac.github.io/irsa-tutorials/most-queries/ | VERIFIED |
| IRSA Spectrophotometry Tool | Forced-photometry spectrum at a position using the pipeline algorithm | https://irsa.ipac.caltech.edu/Missions/spherex.html | VERIFIED (description) |
| IRSA Source Discovery Tool | Python package plus notebook: finds sources without priors, simple image subtraction to find red sources, Firefly/bokeh plots, extracts spectra of selected sources | https://caltech-ipac.github.io/irsa-tutorials/spherex-source-discovery-tool-demo | VERIFIED (tutorial) |
| IRSA Mosaic and Cutout tools | Custom multi-band mosaics (May 2026), LVF cutouts without resampling; spectral cube cutout planned Jan 2027 | https://spherex.caltech.edu/page/data-tools | VERIFIED |
| SPHEREx DR1 HiPS cube (Aladin Lite/Desktop) | All-sky DR1 cube with 102 frames (one per band and channel), viewable in Aladin. It is a static co-add, not time-resolved | https://caltech-ipac.github.io/irsa-tutorials/spherex-hipscube/ | VERIFIED (tutorial) |
| ESASky | HiPS all-sky viewer. SPHEREx HiPS presence not confirmed; caveats page says HiPS are for visualization only | https://www.cosmos.esa.int/web/esdc/esasky-caveats | UNVERIFIED for SPHEREx |
| Backyard Worlds (Zooniverse) | Volunteer blink classification of WISE flipbooks, uses WiseView | https://www.zooniverse.org/projects/marckuchner/backyard-worlds-planet-9 | UNVERIFIED this session (known from prior context) |
| Community code on GitHub | SPIFF (spectrophotometry extraction, jgagneastro), spherextract (optimal point-source spectra), SPHEREx_pipeline (source decontamination plus SPIFF spectra), spherex-cutoutdb (cutouts plus PSF photometry), banados/spherex-tools. These are libraries with no time-domain UI | https://github.com/jgagneastro/SPIFF ; https://github.com/freddavies/spherextract ; https://github.com/andrijazupic/SPHEREx_pipeline ; https://github.com/yayasaikou1/spherex-cutoutdb | VERIFIED (search listing) |

GitHub: "spherex created:>2025-01-01" returns **429 repos**. The 50 newest are almost all Space Apps 2026 entries updated within minutes, with blink, time machine and SkyShift clones. Ones that differ: aquila147/Tombaugh ("what's moving above you", sky overhead your location), ayoubna99/spherex-skyshift (shows satellites crossing the data), JILZXY/SpectraHive-backend (Spanish citizen-science micro-tasks), Snikerso/spherex-explorer (OpenAI Agents SDK copilot, cockpit UI), Pentexa/SpectraX (FastAPI that samples the DR1 spectral cube and tracks DR1/QR3/DR2), Lordphoenix1223/SIEVE-public (SPHEREx plus Gaia evidence snapshot). Search: https://github.com/search?q=spherex+created%3A%3E2025-01-01&type=repositories . VERIFIED (listing only, READMEs not opened).

### (d) Feature matrix
Y = stated or seen. y? = likely but unverified. - = not found. The team columns are keyword-based from project text. "Teams with keyword" counts hits across all 114 project texts.

| Feature | Teams with keyword (of 114) | WiseView | Legacy Viewer | IRSA SPHEREx Data Explorer | MOST | Spectrophotometry Tool | Source Discovery Tool | SPHEREx HiPS cube (Aladin) | Backyard Worlds | Team Oblivion | AEC | SkyShift Cyprus | Nakshatra Chronos | Specula | Vanilla Sphere | Chronocosmos | Red-Shift | Phantom Signal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Blink | 47 | Y | Y | - | - | - | - | - | y? | Y | Y | Y | Y | - | Y | Y | - | Y |
| Time slider / timeline / time-lapse | 40 | Y | - | Y (time filter) | - | - | - | - | y? | Y | Y | - | Y | - | Y | Y | - | Y |
| Difference / subtraction | 36 | Y | - | - | - | - | Y | - | - | Y (known) | - | Y | - | - | Y | - | - | - |
| Co-add / stacking | 23 | Y | - | - | - | - | - | Y (DR1 cube) | - | - | Y | Y | - | - | - | - | - | - |
| Shift-and-stack along a motion vector | 0 | Y (shift and add) | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| 102-band / wavelength selector | 47 | W1/W2 only | - | Y (spectral constraints) | - | - | - | Y (102 frames) | - | - | Y | Y | Y | - | - | - | Y | - |
| Spectrum on click | 7 | - | - | Y (spectrophotometry tab) | - | Y | Y | - | - | - | - | Y | - | - | - | - | - | - |
| Spectrum per epoch / spectral change over time | 1 | - | - | - | - | y? | - | - | - | - | - | - | - | - | - | - | - | - |
| Matched-wavelength (LVF-aware) epoch pairs | 9 | n/a | n/a | - | - | - | - | - | n/a | Y | - | - | Y | - | Y | - | - | - |
| Mover detection | 67 | - | - | - | Y (known orbits) | - | - | - | human | Y | Y | Y | Y | Y | Y | Y | - | Y |
| ML / AI flagging | 39 | - | - | - | - | - | - | - | - | Y | Y | - | - | Y | Y | Y | Y | Y |
| Gaia cross-match / overlay | 31 | Y | y? | Y (via TAP/catalogs) | - | - | - | y? | - | - | Y | Y | Y | - | Y | - | Y | - |
| CatWISE / AllWISE / WISE | 40 | Y (data) | y? (unWISE) | Y (IRSA catalogs) | Y (WISE images) | - | - | - | Y | Y | Y | Y | - | - | Y | Y | Y | - |
| SIMBAD | 6 | - | - | y? (NED yes) | - | - | - | y? (Aladin) | - | Y | Y | - | - | - | - | - | - | - |
| JPL / known-asteroid ID | 22 | - | - | - | Y | - | - | - | - | Y | - | Y | Y | Y | Y | - | - | - |
| Predicted path / ephemeris | 4 | - | - | - | Y (orbit plot) | - | - | - | - | Y | - | - | - | - | - | Y | - | - |
| Contamination / artifact flags shown | 37 | scan-direction split | - | y? (mask planes) | - | y? | - | - | - | - | Y | Y | Y | - | Y | Y | Y | - |
| URL query / embeds / share link | 17 | y? | Y (Link Here, &blink) | - | Y (program interface) | - | - | Y (Aladin URL) | - | - | Y | Y | - | - | Y | Y | - | - |
| Game / gamification | 15 | - | - | - | - | - | - | - | y? | Y | - | - | - | - | - | - | - | - |
| Multilingual | 18 | - | - | - | - | - | - | - | y? | Y | Y | Y | Y | - | Y | - | - | - |
| Chatbot / LLM assistant | 23 | - | - | - | - | - | - | - | - | Y | Y | - | - | Y | Y | Y | Y | Y |
| Narration / story / guided tour | 19 | - | - | - | - | - | - | - | y? (tutorial) | - | - | - | Y | - | - | - | - | - |
| Sonification / audio | 12 hits, about 4 true data sonification | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| Accessibility (screen reader, low vision, flicker cap) | 6 | - | - | - | - | - | - | - | - | - | - | Y | - | - | - | - | - | - |
| Mobile / responsive | 21 | - (Chrome desktop) | y? | - | - | - | - | y? | y? | - | Y | - | - | - | - | - | - | - |
| Volunteer workflow / submission | 44 | - | Y (Discuss This Object) | - | - | - | - | - | Y | - | Y | Y | Y | - | Y | Y | - | - |
| Multiplayer / collaborative | 6 | - | - | - | - | - | - | - | y? (Talk) | - | - | - | - | - | - | - | - | - |
| Ground truth / injection-recovery | 10 | Y (Synthetic Object) | - | - | - | - | - | - | y? | - | - | - | Y | - | Y | - | - | - |
| Uncertainty display (error bars) | 8 | - | - | y? (plots) | - | Y (flux errors) | - | - | - | - | Y | - | Y | - | - | - | Y | - |
| Polar / deep-field focus | 4 | - | - | Y (deep-field MOC) | - | - | - | - | - | Y | - | - | - | Y | - | - | - | - |
| WISE + SPHEREx long baseline | 7 | WISE only | - | - | Y (both archives) | - | - | - | WISE only | Y | - | - | - | - | - | Y | - | - |
| Spectral classification of movers | 1 | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| Anomaly / transient detection | 28 | - | - | - | - | - | y? (red sources) | - | - | - | - | - | Y | - | - | - | - | - |
| Parallax-aware motion fit | 8 | - | - | - | - | - | - | - | - | - | - | Y | - | - | Y | - | - | - |
| MPC ADES export | 3 hits, 1 true (SkyShift Cyprus) | - | - | - | - | - | - | - | - | - | - | Y | - | - | - | - | - | - |
| Weekly-release auto ingest / alerts | 2 | - | - | - | - | - | - | - | - | - | - | - | - | Y | - | - | - | - |
| Precovery | 0 | - | - | - | Y | - | - | - | - | - | - | - | - | - | - | - | - | - |
| Search along hypothetical (Planet X) orbits | 0 | - | - | - | manual orbit input only | - | - | - | - | - | - | - | - | - | - | - | - | - |
| Satellite-streak handling | 1 hit (plus GitHub ayoubna99/spherex-skyshift) | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| Provenance / reproducible dossier | 14 | - | Y (URL state) | - | - | - | - | - | - | Y | - | Y | - | - | - | - | Y | - |
| 3D / VR view | 18 | - | - | - | - | - | - | - | - | Y (known) | - | - | - | Y | - | - | - | - |

### (e) Uncovered or nearly uncovered features (teams plus tools)
- **Shift-and-stack along a motion vector on SPHEREx**: 0 teams. Only WiseView does it, on WISE.
- **Search along hypothetical or predicted Planet X / Planet Nine orbits**: 0 teams. MOST takes manual orbital elements, one orbit at a time.
- **Precovery on SPHEREx in a public UI**: 0 teams. MOST does it as an expert tool.
- **Spectrum per epoch / spectral change of the same object over time**: about 1 weak team mention, and no tool.
- **Spectral classification of moving objects (asteroid taxonomy, ices)**: about 1 weak mention. 7 teams mention ice bands, but for static sources.
- **MPC ADES export of a candidate**: 1 team (SkyShift Cyprus).
- **Weekly-release auto-ingest or alerts**: 2 teams (Specula, Skill-Issue).
- **Satellite-streak identification**: 1 team plus 1 GitHub repo.
- **Polar deep-field (NEP/SEP daily cadence) as the main focus**: 4 teams (Nebula Nexus, Specula as a control field, Oblivion and ASTERIA as options).
- **Real data sonification and accessibility**: about 4 true sonification teams and 6 accessibility mentions.
- **Multiplayer or collaborative review**: 6 mentions, mostly games.
- **Uncertainty shown to the user (error bars)**: 8.

### (f) Gaps (coverage facts only, no idea proposed)
- Most teams stop at "show and blink". Teams that go further mostly add an LLM chatbot or a game layer. Both are common now (23 chatbot, 15 game), so they count as "regular".
- The validation story is rare: injection-recovery numbers show up in only about 3 teams (AstroFreak, Nakshatra Chronos, Vanilla Sphere). False-alarm control fields in 1 (Specula).
- SPHEREx's own trait (each epoch sees a different wavelength through the LVF) is handled by about 9 teams as a nuisance to correct. None says they use it to build a per-epoch spectrum of a mover.
- The output step after discovery (report, ADES, follow-up handoff, volunteer consensus) is thin. 44 teams use the word "citizen", but only 1 exports ADES and none describes a reviewed consensus queue.
- Long-baseline WISE plus SPHEREx combination: 7 teams. Oblivion and Chronocosmos already do it with 2MASS/DSS too, so it is no longer unique.
- Limits of this report: keyword tags are approximate. The 1,266 teams with no project text yet could still submit before the deadline. Teams found earlier (Ahmed Wael, OSCAR) were not matched by name. ESASky and Backyard Worlds rows are UNVERIFIED.


---


# Part 14

## Agent 14 - Other surveys and missions for moving and changing objects (checked Nov 14 2026)

V = VERIFIED (I read it on the source page or abstract today). U = UNVERIFIED (secondary source, or general knowledge I did not re-check).

### (a) Bottom line
1. Rubin has been running LSST since Jun 29 2026. It already finds asteroids and TNOs (2026 ED138) and sends 7 full-stream brokers up to ~7M alerts a night. Optical, southern sky, faint: it owns "faint movers in reflected light".
2. Infrared all-sky motion over time has been NEOWISE/WISE (2009-2024, 21 sky passes, ended Aug 2024). NEO Surveyor does not launch before Sep 2027. So right now SPHEREx is the only working all-sky infrared survey that revisits the sky.
3. What SPHEREx has that nobody else does: a 102-channel 0.75-5 um spectrum for every source, which shows methane, water and CO2. That can confirm what a cold object is, not just that it moves.
4. Weak points: 6.2" pixels (WISE was 2.75"), about 1 full spectrum every 6 months, and heavy crowding near the galactic plane. It is poor at finding new faint movers by itself.
5. Scientists already pair SPHEREx with Gaia (proper motions), WISE/CatWISE (motion selection) and JWST (follow-up). The published brown dwarf tool SPIFF exists because IRSA's tool does not handle fast movers.

### (b) Survey table
| Survey | Status Nov 2026 | Movers / variables | Public data / tools | Link | Verified? |
|-|-|-|-|-|-|
| Rubin LSST | LSST started Jun 29 2026; alerts public since Feb 24 2026 | ~7M alerts/night; Solar System Pipeline (heliolinx linking, Sorcha ephemerides, MPC submit, code X05). >11,000 new asteroids and >80,000 known bodies detected by Apr 2026 | Alerts world-public through brokers; solar system data public at MPC; Asteroid Institute subset ls.st/ast; dashboard sbx.dirac.dev/station/X05 | https://rubinobservatory.org/for-scientists/data-products/recent-data-releases ; https://rtn-011.lsst.io/RTN-011.pdf (rev Oct 29 2026) | V |
| Rubin solar system access gap | Users Committee Apr 27 2026 | Solar system data "not currently served through any alert broker, nor accessible on the RSP"; MPC metadata missing | - | https://community.lsst.org/t/users-committee-report-2026a-april-27/12064 | V (as of Apr 2026, may have changed) |
| Alert brokers: ALeRCE, AMPEL, ANTARES, Babamul, Fink, Lasair, Pitt-Google (+SNAPS, POI downstream) | Running on Rubin alerts since Feb 2026 | Cross-match, light-curve features, ML classes. Fink has SSO tables (SSoFT), new-SSO candidates, anomaly detection, "Fink AI" model upload (Oct 8 2026) | Fink REST API (sso, ssocand, ssoft, anomaly) | https://rubinobservatory.org/for-scientists/data-products/alerts-and-brokers ; https://api.ztf.fink-portal.org/ ; https://fink-broker.org/news | V |
| Rubin and brown dwarfs | Early-data study (arXiv 2604.08387) | LSST-only brown dwarf selection "too inefficient"; needs proper motions or infrared data | - | https://arxiv.org/html/2604.08387v1 | V |
| Rubin and Planet Nine | No published result | Batygin (Jun 2026): Rubin gives "a direct test of all lines of evidence". ED138 paper: the galactic plane needs crowded-field catalogs or trial-orbit image search | - | https://spacedaily.com/t-rubin-direct-test-planet-nine-2026/ (Aug 28 2026) ; https://arxiv.org/html/2610.38693v1 | quote U (secondary); ED138 text V |
| NEOWISE | Ended Aug 1 2024; final release Nov 14 2024 | 21.3 sky passes, 6 months apart; ~44,600 solar system objects; 199B detections | IRSA catalogs, coadder, time-series tool | https://irsa.ipac.caltech.edu/data/WISE/docs/release/NEOWISE/ | V |
| NEO Surveyor | Launch no earlier than Sep 2027 (official commitment by Jun 2028) | Infrared NEO hunter | none yet | https://science.nasa.gov/mission/neo-surveyor/ | V |
| Gaia DR4 | Scheduled Dec 2 2026; archive offline Nov 25-Dec 2 | Epoch astrometry for ~2.8B sources (62 TB); 436,551 SSOs with epoch spectra | Gaia archive TAP/DataLink; 12 sample sources released Jun 29 2026 | https://www.cosmos.esa.int/web/gaia/release ; https://www.cosmos.esa.int/web/gaia/dr4 | V |
| Euclid | Q1 Mar 2025; Q2 Jun 24 2026; DR1-Foundation Nov 12 2026 (~1,900 deg2); full DR1 mid-2027 | Q1: 5,306 new ultracool dwarf candidates in the deep fields; solar system objects detected | ESA/IRSA archives | https://www.cosmos.esa.int/en/web/euclid/dr1-timeline ; https://www.aanda.org/articles/aa/full_html/2026/07/aa56980-25/aa56980-25.html | V |
| Roman | Launched Aug 30 2026; science commissioning from Oct 22 | Not an all-sky mover survey; deep infrared fields | not yet | https://www.nasa.gov/news-release/nasas-dark-universe-seeking-nancy-grace-roman-space-telescope-launches | V (commissioning detail from azmth.space, U) |
| ZTF | ZTF-3 runs Jan 2025-Dec 31 2026; DR24 Jan 22 2026, DR25 Jan 20 2027 | Northern sky every ~2 days; ML pipelines; alerts to brokers | Public alerts, light curves, images (60-day window) | https://www.ztf.caltech.edu/ztf-public-releases.html | V |
| Catalina | Running | 726 NEAs in 2026 so far | MPC | https://catalina.lpl.arizona.edu/ | V |
| Pan-STARRS, ATLAS | Assumed running | NEO discovery; ATLAS all-sky ~daily | MPC; PS1 DR2 at MAST | - | U (not re-checked) |
| SPHEREx | DR1 Nov 12 2026 (reprocessed spectral images + all-sky 102-channel cube); QR3 since Sep 2026 | Each pointing has hundreds of moving solar system objects; ~1e5 asteroids expected; 3I/ATLAS imaged | IRSA SIA/TAP, cutouts, AWS, Moving Object Search Tool (MOST) | https://spherex.caltech.edu/news/spherex-data-release-1-dr1-is-now-available-at-irsa ; https://irsa.ipac.caltech.edu/Missions/spherex.html | V |

### (c) Production methods
- MPC: central clearing house for all mover astrometry; Rubin sends here (V, Rubin page above). JPL Horizons / Small-Body API and SkyBoT (IMCCE) give positions of known bodies for a given field and time (U, standard tools, not re-checked).
- IRSA MOST: takes an orbit and returns the SPHEREx images that covered the predicted positions (V, IRSA SPHEREx page).
- HelioLinC (Holman 2018): heliocentric transform and cluster, O(N log N); heliolinx runs inside Rubin (V): https://iopscience.iop.org/article/10.3847/1538-3881/aad69a
- THOR (Moeyens 2021): links without same-night tracklets, open source; 97% recovery on ZTF (V): https://iopscience.iop.org/article/10.3847/1538-3881/ac042b
- Spherical-orbit TNO linking on detections, tested on DES with LSST-like cadence (PSJ, Sep 30 2026) (V): https://iopscience.iop.org/article/10.3847/PSJ/aea3f4/pdf
- Shift-and-stack: KBMOD on GPUs (New Horizons Subaru survey found 239 TNOs down to r~26.5; ML was needed to cut false positives) (V): https://iopscience.iop.org/article/10.3847/PSJ/ad6f9e ; catalog-based shift-and-stack 4-200x faster (V): https://iopscience.iop.org/article/10.3847/1538-3881/ae0e1a/pdf ; TESS shift-stack Planet Nine search (V): https://iopscience.iop.org/article/10.3847/PSJ/abc42c
- Planet Nine parallax search between nights, 98 deg2, nothing found to r~21.3 (V): https://arxiv.org/html/2504.05473v2
- ML real/bogus: ResNet ensembles on KBMOD stamps cut human vetting ~10x and more (V): https://arxiv.org/pdf/2405.06148 ; ZTF and broker ML classifiers (V, ZTF site).

### (d) SPHEREx strengths vs weaknesses
| Strength | Weakness |
|-|-|
| 102 channels, 0.75-5 um, R~35-130, every pixel on the sky (V, Bock 2026 ApJ https://iopscience.iop.org/article/10.3847/1538-4357/ae2be2) | 6.2" pixels vs WISE 2.75"; crowding blocked a Y dwarf check (V, SMDET-1 https://arxiv.org/html/2608.00046v2) |
| 2.5-5 um mostly blocked from the ground (methane, CO, CO2, water) (V, NASA Oct 8 2026) | About 1 full spectrum per 6 months; a full 102-channel spectrum takes 1-2 weeks to build up (V, Bock 2026) |
| Brown dwarfs: 6,003 ultracool dwarfs in QR2, 945 new, more than doubles those with spectra (V, https://iopscience.iop.org/article/10.3847/1538-4357/ae8aed) | Shallow: ~14.5 mag Vega at 4-5 um after 1 year, worse in crowded fields (V, SMDET-1) |
| Deep fields at the ecliptic poles get hundreds of visits (V, ApJ ae9d66) | Only 3-4 epochs per object in the 2-year prime mission (V, LPSC 2026 #1833) |
| Sun-synchronous orbit like NEOWISE, so the 6-month cadence matches the WISE archive (V, LPSC #1833) | IRSA's spectrophotometry tool takes no batch input and does not follow proper motion (V, SPIFF paper) |

### (e) Combinations named by scientists
- SPHEREx + Gaia: proper motions and luminosities; the 10,000 low-mass star atlas uses Gaia astrometry to correct for motion (V, Bock 2026).
- SPHEREx + WISE/CatWISE/2MASS: SPHEREx gives spectra of WISE-selected sources and the faintest WISE sources at S/N >= 3 (V, https://arxiv.org/html/1805.05489v2); SPIFF picked candidates using CatWISE, UKIDSS, UHS, Gaia, PS1 motions and Backyard Worlds (V).
- SPHEREx + JWST: "SPHEREx goes wide while JWST goes deep" (V, https://spherex.caltech.edu/page/synergies-with-other-missions).
- SPHEREx + LSST, Euclid, Gaia, Roman, NEO Surveyor for solar system work (V, LPSC 2026 #1833, listed only, no method).
- SPHEREx + Rubin for brown dwarfs: not found in a paper. The Rubin study says infrared data is needed, which points that way (inference, U).

### (f) What this means for choosing a project
- Finding faint movers by blinking SPHEREx images alone is weak ground: Rubin (optical, deep) and the 11-year NEOWISE archive (sharper infrared) already cover it better.
- What nobody covers yet: an all-sky, spectrum-for-every-mover view. Brokers give light curves and classes, not 0.75-5 um spectra.
- Known tool gaps: no batch tool that follows fast movers in SPHEREx (SPIFF fills part of it), Rubin solar system data not in brokers (as of Apr 2026), and the galactic plane is hard for everyone.
- Timing: Gaia DR4 (Dec 2 2026), Euclid DR1-Foundation (Nov 12) and SPHEREx DR1 (Nov 12) are all brand new, so cross-mission work is fresh.
- Long baseline: WISE 2010 to SPHEREx 2025-2026 gives about 15 years for motion, but SPHEREx's large pixels limit precision.

### (g) Gaps
- No public statement found on SPHEREx being used to search for Planet Nine. The searches I ran returned nothing.
- "About 50 new Y dwarf candidates from SPHEREx" appears only on Wikipedia (List of Y-dwarfs); primary paper not checked (U).
- Pan-STARRS and ATLAS 2026 status, and SkyBoT/Horizons, were not re-checked.
- Whether Rubin solar system data reached the brokers after Apr 2026 is unknown.
- No ML specifics checked for ALeRCE, Lasair, AMPEL, Pitt-Google or Babamul beyond the Rubin broker page.
- I did not check whether SPHEREx DR1 includes a moving-object or SSO catalog. LPSC 2026 says a SPHEREx SSO photometric catalog is being built.


---


# Part 15

## Agent 15 - SPHEREx data: what it contains and what it makes possible

Checked Sat Nov 14 2026. VERIFIED = I read it in the doc or tested it live today. MEASURED = my own small SIA query or header request. INFERRED = my own arithmetic, not stated in any doc.

Sources: ES = Explanatory Supplement v2.1, 2026-11-10 (https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp.pdf). UG-P / UG-A / UG-R = Archive User Guide pages Data Products / Data Access / Data Releases (https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products, .../spherex-data-access, .../spherex-data-releases). SP = Spectrophotometry help (https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html).

### (a) Bottom line
1. Every position on the sky has a time series. Each image is one 113.6 s exposure with a UTC timestamp and a per-pixel wavelength map. At the ecliptic equator there are about 3 visit windows so far (May 2025, Dec 2025, May-Jun 2026), each about 1-10 days long. Near the ecliptic poles there are dozens to hundreds of visits.
2. The same pixel never repeats the same wavelength. The LVF filter means each frame samples a different wavelength at a given sky spot, so "same spot, same color, two epochs" has to be built on purpose.
3. The all-sky cube (102 channels, 12.9"/pix) is a Year-1 coadd with zodi removed. It has NO time axis. It works as a static reference or template, not as an epoch source.
4. From a browser, only AWS S3 (CORS *, byte ranges allowed) and the HiPS PNG tree (CORS *) can be called directly. SIA and the IBE cutout responses carry no CORS header, so a browser app needs a small proxy for them.
5. Forced-photometry spectra (Tractor) at fixed positions come back per exposure with an MJD and a data-release column. Positions are never refit, so a moving object needs its position supplied for every exposure.

### (b) What's in the data
| Item | Content | Status / source |
|-|-|-|
| Spectral image MEF | 1 file per detector per pointing, 6 detectors, about 65-70 MB, 2040x2040 | VERIFIED UG-P "Main Science Data Product"; ES 2.2 |
| HDU IMAGE | MJy/sr, zodi NOT subtracted | VERIFIED UG-P |
| HDU FLAGS | 32-bit bitmask (see below) | VERIFIED ES Table 16 |
| HDU VARIANCE | (MJy/sr)^2 per pixel | VERIFIED UG-P |
| HDU ZODI | modeled zodiacal light, not subtracted | VERIFIED UG-P; ES 3.2.11 |
| HDU EPSF (DR1/QR3) | 21x21 zones (det 3: 11x41), 33x33 px, 5x oversampled | VERIFIED UG-P; a live DR1 cutout had EPSF with 441 rows (MEASURED) |
| HDU WCS-WAVE | lookup table of pixel -> central wavelength + bandwidth. Fine for display; use the Spectral WCS files (CWAVE/CBAND per pixel) for science | VERIFIED ES 2.2; UG-P "Spectral WCS" |
| Bands | D1 0.75-1.09 R39; D2 1.10-1.62 R41; D3 1.63-2.41 R41; D4 2.42-3.82 R35; D5 3.83-4.41 R112; D6 4.42-5.00 R128 | VERIFIED UG-P; ES Table 2 |
| Pixel / PSF / astrometry | 6.15"/pix; PSF FWHM median about 8.7" (example header); astrometric RMS < 0.3" against Gaia | VERIFIED ES Table 2, Table A header, 4.2.2 |
| Timing | Exposure 113.58 s, frame 1.5349 s. Header has MJD-BEG/AVG/END. SIA gives t_min/t_max | VERIFIED ES Table 2, header table |
| Cadence | A target group is 17 pointings stepped one channel width apart. Up to 4 small slews per large slew, about 130 s apart (MEASURED); groups repeat over hours to days. Full-sky coverage twice per year. Surveys 3/4 are shifted 6' (half a channel) | VERIFIED ES 1.4, 2.2; cadence MEASURED |
| Epoch counts (DR1+QR3 wide, 0.001 deg circle) | (180,0): 340 files, about 57 per detector, 10 time clusters inside 3 seasons. M31: 362 files. NEP (270,+66.56): 671 files, 58 clusters. SEP (90,-66.56): 928 files, 80 clusters. Deep collections add 5,671 (DR1 deep at SEP) and 7,890 (QR3 deep at NEP) | MEASURED via SIA today |
| Flag bits | 0 TRANSIENT, 1 OVERFLOW, 2 SUR_ERROR, 6 NONFUNC, 7 DICHROIC, 9 MISSING_DATA, 10 HOT, 11 COLD, 12 FULLSAMPLE (info only), 14 PHANMISS, 15 NONLINEAR, 17 PERSIST, 19 OUTLIER, 20 CROSSTALK, 21 SOURCE (known source), 22 GHOST, 23 GHOST_FPA (unused), 24 GHOST_EXT (in development), 25 STREAK (satellite), 26 BLOOM, 27 SNOWBALL, 28 HALO, 29 SATELLITE_HALO | VERIFIED ES Table 16; SP flag table |
| Source mask input | Built from a Reference Catalog plus the known Solar System object catalog | VERIFIED ES 3.2.9 |
| All-sky cube | 12,288 HEALPix order-5 tiles of about 1.8 deg, 512x512 at 12.9"/pix, 102 channels. HDUs: IMAGE, NHITS, FLAGS, SPECTRAL_CHANNELS, WCS-WAVE. Zodi subtracted; built from about 1.2M DR1 images; channels 51/52 are blank | VERIFIED UG-P; ES 2.5 |
| Calibration and extras | gain, dark, ePSF, SIP, solid-angle map, spectral channels, nonfunc, crosstalk, He/aurora/shuttle-glow templates, zodi scaling, QR2->QR3 flux corrections | VERIFIED UG-P |

### (c) Services and access
| Service | What it returns | Time info? | Browser-callable? | Link |
|-|-|-|-|-|
| SIA2 (spherex_dr1, _dr1_deep, _dr1_cube, spherex_qr3, _qr3_deep) | ObsCore rows: access_url, cloud_access (S3 key), t_min/t_max (MJD), em_min/em_max (detector-wide), s_region polygon, obs_id. Filters: POS, BAND, TIME, UPLOAD (many positions), MAXREC. Jobs over 5 min are cancelled | Yes | No: no CORS header (MEASURED) | https://irsa.ipac.caltech.edu/ibe/sia.html |
| TAP (spherex.artifact, spherex.plane) | Cutout URLs sorted by time_bounds_lower for a point | Yes | not tested | Source Discovery notebook, section 12.1 |
| IBE cutout | `<access_url>?center=ra,dec&size=` returns the MEF with all 6 HDUs. EPSF is uncut, so even a 20-px cutout is about 3.9 MB (MEASURED). One request per image; "all epochs" means one request per SIA row | Yes, header MJD | No: no CORS (MEASURED) | https://irsa.ipac.caltech.edu/ibe/cutouts.html |
| AWS S3 `nasa-irsa-spherex` (us-east-1), prefixes dr1/ qr3/ qr2/ | Full files and calibrations, anonymous, no egress fee. CORS `*`, GET/HEAD, Range header allowed (206 MEASURED) | Yes (headers) | Yes | https://irsa.ipac.caltech.edu/cloud_access/ |
| HiPS cube | PNG, 102 frames, order 0-5, 0-40 MJy/sr asinh stretch, display only | No | Yes, CORS * (MEASURED) | https://irsa.ipac.caltech.edu/data/hips/SPHEREx/spherex_allsky_cube |
| Cube FITS tiles | Npix{N}_cube.fits, about 300 MB each | No | Through S3 yes | hipscube notebook |
| Spectrophotometry Tool (GUI) | Per exposure: wavelength, flux, flux_err (uJy), lambda_width, flags, fit_ql, flux_bkg, lvf_id, det_id, deep_flg, mjd, data_collection, x/y image. At most 20 sources per run; runtime about 1.67 s x images + 50 s | Yes (mjd) | GUI only | SP "Outputs", "Tips" |
| MOST | Orbit -> SPHEREx images covering the predicted position; catalog "spherex", 2025-03-11 to now | Yes | GUI / astroquery | https://irsa.ipac.caltech.edu/applications/MOST/ (VERIFIED in page source) |
| Source Discovery Tool | Python: SExtractor on a difference of two detectors, then aperture-photometry spectrum from all cutouts | Uses MJD | Python only | spherex-source-discovery-tool-demo |
| 3I/ATLAS | VOTable of every exposure with predicted comet_ra/comet_dec, plus download scripts (Aug + Dec 2025) | Yes | static file | https://irsa.ipac.caltech.edu/data/SPHEREx/docs/comet3iatlas/index.html |
| SPLICES | Ice-source target catalog | n/a | not checked | Missions page |

### (d) Analyses the data supports vs does not support
Supported (documented or directly implied):
- Spectrum at any position from about 100+ exposures (Spectrophotometry Tool, Source Discovery notebook), plus a quick 102-channel spectrum from the cube (hipscube notebook). VERIFIED.
- Per-epoch photometry, because every measurement carries an MJD. That means time-varying spectra or variability at partial wavelength coverage per epoch. VERIFIED (SP outputs). A full 0.75-5 um spectrum takes a full target group (about 17 pointings over days), which is INFERRED from ES 1.4.
- Spectra of moving objects with an ephemeris, shown by the 3I/ATLAS table (Aug and Dec 2025) and MOST "spherex". VERIFIED. ES 1.1 targets ">=100,000 asteroid and comet spectra".
- Image differencing. Cross-detector differencing is demonstrated in the Source Discovery notebook. Epoch-to-epoch differencing works if you match wavelength through CWAVE and reproject. INFERRED; no doc tutorial.
- Gaia cross-match: the pipeline astrometry already uses Gaia with proper motions. VERIFIED ES 3.2.8. WISE/NEOWISE single-exposure frames sit on S3 in us-west-2 with MOST support. VERIFIED cloud_access page.
- PSF-fit photometry with the ePSF. VERIFIED UG-P, spherex-psf tutorial.

Limits (my arithmetic, INFERRED): over about 130 s, 6.15" pixels pick up motion only above about 3"/min. Over a 1-10 day visit window, motion of a few arcsec/day is measurable against <0.3" astrometry. Between seasons the gap is about 6 months.

Not supported or not provided:
- No time axis in the cube or the HiPS. VERIFIED.
- No released source catalog of SPHEREx detections, and no moving-object catalog, in DR1. VERIFIED by absence in the UG-P product list.
- No server-side difference images and no server-side stacking along a motion vector. Not found in docs.
- The Spectrophotometry Tool does not refit positions and is for point-like sources; the docs advise against using it on 3I/ATLAS. VERIFIED SP, 3I page.

### (e) Caveats
- QR2 vs QR3: "advise caution" when combining them; use DR1+QR3. Flux-correction files exist. QR2 is no longer searchable and can be downloaded until Feb 2027. VERIFIED ES 2.1, UG-A.
- The PSF header error affects QR1/QR2 only (up to +/-5% photometry); not DR1/QR3. VERIFIED ES 2.2. The UG cutout section still describes the QR2 121-plane PSF, but DR1 cutouts carry EPSF. MEASURED.
- LVF entanglement: emission lines cause stripes and moire patterns in coadds that do not average down. The 1.083 um He airglow varies with time. VERIFIED ES 2.5.2, 3.4.10.
- Zodi is not subtracted in images but is subtracted in the cube. Zodi changes with season, which matters for epoch differences. VERIFIED.
- Artifacts: ghosts (frame-edge, linear, beam-splitter, 8 deg), Moon stray light, cosmic-ray snowballs/glow, crosstalk, satellite streaks (faint ones may be unflagged), and diffuse optical transients in about 1% of exposures. A list of anomaly images exists. VERIFIED ES 2.3.
- Known asteroids may carry the SOURCE flag through the masking catalog. INFERRED from ES 3.2.9.
- Cutout axes follow detector orientation, not north-up, and include SIP distortion. VERIFIED cutouts doc.
- IRSA has scheduled downtime every other Tuesday morning Pacific. VERIFIED SP Tips.

### (f) What this means for choosing a project
- The time dimension lives only in single exposures (SIA t_min, header MJD, photometry mjd), not in the cube.
- "Blink" at a fixed wavelength needs a per-pixel CWAVE lookup, because the same sky spot changes wavelength from frame to frame. This is built into the data, not a bug.
- Pole regions have far richer time sampling than the equator. Coverage depth differs by roughly 2-30x.
- A pure static web app can read S3 (with byte ranges) and HiPS directly. SIA, TAP and cutouts need a server or proxy.
- Ready-made per-exposure spectra and ephemeris-driven image lists (MOST, the 3I table) already exist. Gaia astrometry and NEOWISE frames are first-class companions.
- Remaining gaps are documented as missing: no epoch-resolved maps, no detection catalog, no motion-aware stacking.

### (g) Gaps
- The IBE directory listings (/ibe/data/spherex/dr1/level2/) returned 404 to my scripted requests, while file URLs worked. UNVERIFIED whether listings work in a browser.
- I did not test TAP CORS, MOST's programmatic SPHEREx output columns, the SPLICES contents, or rate limits (no documented limits found beyond the SIA 5-minute cap and the 20-source tool cap).
- I did not explain why the exact pole points returned only D2/D5 in the wide collections.
- I did not read the Spectral Calibrations page or the mosaic/intro/cutouts notebooks in full.


---


# Part 16

## Agent 16 - SPHEREx quantitative science check (Nov 14 2026)

V = VERIFIED (I pulled the number from the source in this session). U = UNVERIFIED (estimate, general knowledge, or not re-checked). SIMBAD/VizieR (CDS) returned 404 all session and IRSA TAP timed out, so astrometry comes from the Gaia DR3 archive TAP (gea.esac.esa.int) and photometry from the Gaia-archive 2MASS/AllWISE crossmatch plus papers.

### (a) Bottom line
1. Over 6-18 months, only Barnard's Star (0.85/1.69/2.54 px), WISE 0855 (0.66/1.33/1.99 px) and Eps Indi B (0.38/0.76/1.14 px) move enough to see. RW Aur and R Dra move less than 0.01 px, so they are effectively fixed and only their brightness changes.
2. WISE 0855 only shows up at 3.9-5 micron (about 17.4 AB). It cannot be seen at all at 0.75-3.8 micron (J about 25.9 AB). Rustamkulov et al. 2026 say the same: "Only flux redward of 3.9 um is detected reliably."
3. Barnard's Star (K about 6.4 AB), R Dra (about 3-5 AB) and RW Aur (about 8.6-9.3 AB) are all brighter than where SPHEREx goes nonlinear (about 11.3-11.7 AB in bands 1-4, 9.75-10.2 AB in bands 5-6). Their photometry may be flagged or distorted.
4. Each exposure covers one narrow wavelength at the source position, so images of the same spot from different epochs are usually at different wavelengths. A brown dwarf can look like it "vanished" just because the wavelength changed.
5. Asteroids and comets are easy movers within one pass. TNOs and Planet Nine are not practical: Planet Nine is V about 22 and jumps arcminutes between passes.

### (b) Target table
Pixel = 6.15" (Explanatory Supplement table 2, V; the brief says 6.2"). Shift = |PM| x t, divided by 6.15. AB = Vega + 0.913 (J), 1.391 (H), 1.863 (Ks), 2.699 (W1), 3.339 (W2) (STScI Roman-000825; WISE Expl. Supp., V).

| Target | PM (pmRA*, pmDec) mas/yr | Parallax / dist | Mags (Vega -> AB) | Shift 6/12/18 mo | Detectable? | Risks | Spectral features visible? |
|-|-|-|-|-|-|-|-|
| Barnard's Star (Gaia DR3 4472832130942575872; RA 269.4485, Dec +4.7394 at ep. 2016) | -801.6, +10362.4; total 10393 (V, Gaia DR3) | 546.98 mas / 1.828 pc (V) | J 5.244, H 4.834, Ks 4.524 (V, NASA Exoplanet Archive) -> 6.16/6.22/6.39 AB | 5.20"/0.85 px; 10.39"/1.69 px; 15.59"/2.54 px | Yes, very bright | Saturated or nonlinear by about 5 mag in bands 1-3 (U whether the up-the-ramp read rescues it). Shift per 6 months is under 1 px | M4 star; water bands yes, but saturation may corrupt the spectrum |
| Eps Indi Ba+Bb (Gaia DR3 6412596012146801152; RA 331.0765, Dec -56.7938) | +3982.0, -2466.8; total 4684 (V, Gaia; RUWE 4.3, binary photocenter) | 270.7 mas / 3.69 pc (V, Gaia; A gives 274.8 mas) | Combined 2MASS J 11.908, H 11.306, Ks 11.208; W1 10.718, W2 9.492 (V) -> 12.82/12.70/13.07/13.42/12.83 AB | 2.34"/0.38 px; 4.68"/0.76 px; 7.03"/1.14 px | Yes, high S/N (brighter than the 50-sigma level of about 14.6-14.9 AB, Expl. Supp. QR table 17, V) | Ba-Bb separation 0.732" (McCaughrean 2004, V; about 0.6-0.66" now, U) = 0.12 px, so NOT resolved, one blended source. A is 402.5" (65 px) away (computed from Gaia positions), so resolved, but A (J about 3.8 AB) is heavily saturated, so ghosts or wings are possible (U). A and B share the same PM, so both move together | Blended T1+T6. Ba dominates J/H/K (Bb is fainter by 0.94/1.76/2.18 mag, V). CH4, H2O, CO, CO2 bands are visible at R about 40-130 |
| WISE 0855-0714 (RA 133.795, Dec -7.245, J2000) | -8123.7, +673.2; total 8151.5 (Kirkpatrick 2021 via Wikipedia, U; Luhman & Esplin 2016 give -8118, +680, V) | 439.0 mas / 2.28 pc (V, Rustamkulov table 1 gives 2.28 pc) | J 25.0, H 23.83, W1 17.82, W2 14.02, [4.5] 13.89 (V, Luhman & Esplin 2016; Luhman 2014) -> J 25.9, H 25.2, W1 20.5, W2 17.36 AB | 4.08"/0.66 px; 8.15"/1.33 px; 12.23"/1.99 px | Only at 3.9-5 micron. Band 5-6 5-sigma depth 17.8-18.8 AB after 4 visits (Korngut et al. 2026, V) gives S/N about 7.5-19 per channel (5 x 10^(0.4 x (depth - 17.36))); a single pass is about half that (U) | Invisible in bands 1-4. Single-channel images are low S/N. In 2014 it was blended with two background sources (Luhman 2014, V); it has moved about 100" since then (U) | Only the 4-5 micron peak, the CO/CO2 region. Radius fits scatter 3-4x (Rustamkulov fig. 12, V) |
| RW Aur A+B (Gaia DR3 156430822114424576 / ...817820015232; RA 76.956, Dec +30.401) | A: +2.6, -27.4; total 27.5 (V) | 6.41 mas / 156 pc (V) | Combined J 8.378, H 7.621, Ks 7.02, W1 6.246, W2 5.228 (V) -> 9.29/9.01/8.88/8.95/8.57 AB | 0.014"/0.002 px; 0.028"/0.004 px; 0.041"/0.007 px | Yes, but above the nonlinearity limit by about 1.2-2.6 mag | A-B separation 1.49" (from Gaia positions) = 0.24 px, so blended. Ecliptic latitude 7.5 deg, so the fewest visits | Dimming events of 2-3 mag in V, lasting about 40-830 days (Rodriguez 2018, V). In the IR, W1 barely changes but 4.6 micron gets brighter during dimmings; 0.5-1 mag scatter (Koutoulaki 2019, V). In 2025 it was more stable and slightly faint (Lux 2024, V) |
| R Dra (Gaia DR3 1648328016354496384; RA 248.167, Dec +66.755) | -20.6, +6.1 (V) | 1.25 mas / about 800 pc (V, low precision) | J 3.863, H 3.125, Ks 2.438 (2MASS, D quality); W1 0.39 / W2 0.13 (saturated, "U" quality) (V) -> about 3-5 AB | 0.011"/0.002 px; 0.022"/0.004 px; 0.032"/0.005 px | Yes, but saturated by about 6-8 mag | Ecliptic latitude 81.4 deg, about 8.6 deg from the NEP, so likely many visits (U on the exact cadence) | Mira, P = 246.12 d, V 6.7-13.2 (AAVSO VSX, V). NIR amplitude is much smaller, about 1 mag in K (U). 6-month sampling steps the phase by 183/246 = 0.74 cycle |

Ecliptic latitudes come from the standard conversion I computed. Barnard 28.2 deg also matches the NASA Exoplanet Archive (V).

### (c) Brown dwarf spectra notes
- SPHEREx R: bands 1-3 about 39-41, band 4 about 35, band 5 about 112, band 6 about 128 (Expl. Supp. table 2, V). Water and methane bands are broad (about 0.1-0.5 micron) and resolved easily at R about 40. CO2 at 4.3 micron and CO at 4.6 micron are resolved at R about 120.
- Rustamkulov et al. 2026, ApJ 1009, 185 (arXiv 2607.00543; NASA release Oct 8 2026), V: they present 37 spectra from L0 to Y4 and say "thousands" have been measured. The spectra are dominated by H2O and CH4 up to the 4.2 micron window, with CO2 and CO beyond it. The paper also reports a new weak CH4 emission at 3.3 micron in a T7 dwarf. The CO and CO2 indices drop sharply from T6 to T7 (about 1000-700 K). None of the model grids fits well (reduced chi-squared of 10 or more for most). The data prefer the weak-mixing Elf Owl models (kzz = 10^4). Their method used proper-motion-corrected positions and the IRSA Spectrophotometry Tool (forced photometry), and dropped points more than 4 sigma off a running median. Eps Indi B is not in their sequence. WISE 0855 is the Y4 point.
- Eps Indi Ba (T1) has weak CH4 and strong H2O, plus CO at 4.6. Bb (T6) has strong CH4 at 1.6/2.2/3.3, CO2 strongest around T5-T6 (Rustamkulov, V), and CO. SPHEREx can only see the blend.
- Variability caveat: one 0.75-5 micron spectrum is built up over about 2 weeks of exposures in each epoch (LPSC 2024/2026 SPHEREx SSO abstracts, V). If the source changes during that time (RW Aur on 10-30 day scales, V; Miras), the spectrum mixes in time.

### (d) Movers detectable vs not
| Category | Rate | Brightness vs SPHEREx | Verdict |
|-|-|-|-|
| Nearby high-PM brown dwarfs and stars | 1-10"/yr gives 0.1-1.7 px/yr | T dwarfs within about 20 pc are often 13-17 AB at 4 micron (U) | Detectable across passes if PM is at least about 1"/yr and S/N is high. Centroid precision is about 0.1 px if FWHM is about 1-2 px and S/N about 20 (U; the PSF file FWHM_v28 is on the SPHEREx GitHub) |
| Parallax | WISE 0855: 2 x 0.439 = 0.88" (0.14 px) swing between opposite sides of the year vs 4.08" PM per 6 months, about 22%. Barnard: 1.09" vs 5.20" | - | SPHEREx always looks about 90 deg from the Sun, which is near the maximum parallax factor (U). The parallax adds a small wobble on top of the PM, under 0.2 px, so it is real but barely measurable |
| Main-belt asteroids | about 30"/hr gives about 0.95" (0.15 px) in one 113.58 s exposure (V for the exposure time; U for the rate) | About 100,000 with useful flux, about 10,000 with good spectra (Ivezic 2022 via Korngut 2026, V) | Not streaked in a single frame, but the position changes between exposures in the same pass. The pipeline only does forced photometry on known orbits, not discovery (Ivezic 2021, V) |
| Fast NEOs | Arcmin/min near Earth (U) | varies | Can streak |
| Comets | - | 3I/ATLAS imaged in dust, H2O, CO2, CO (LPSC 2026, V) | Yes |
| TNOs and dwarf planets | Parallax-dominated, arcsec/hr (U) | Most are V > 20 (U). Pluto, Eris, Makemake and Haumea are brighter (U) | Only the brightest few |
| Planet Nine | 0.1"/hr x (700 AU/d) parallax; 10-25' between 6-month epochs (Cowan 2016; AKARI 2025, V) | V = 22.0 (+1.1/-1.4) (Brown et al. 2024, V); 22 < V < 25 (Brown & Batygin 2016, V); optimistic W1 = 16.1 Vega = 18.8 AB (Fortney 2016, V) | Below the 19.5-19.9 AB depth except in the most optimistic IR model, and it lands somewhere else each pass. Not practical |

### (e) What this means for choosing a project (facts only, no idea proposed)
- For PM, only 3 of the 5 official targets show motion, and by just 0.4-2.5 px over the full data span (about 3 passes since May 1 2025, V). Seeing it needs sub-pixel centroiding or very wide blinks, not just viewing the images.
- RW Aur and R Dra test brightness changes, not motion. Both are saturated, so their numbers may be flagged.
- Wavelength matters as much as time: an epoch-to-epoch comparison has to match or combine channels. WISE 0855 needs 3.9-5 micron.
- Eps Indi Ba/Bb appear as one unresolved point, so they cannot be split at 6.15".
- SPHEREx revisits polar fields much more often than ecliptic ones: R Dra (81 deg) vs RW Aur (7.5 deg).
- Planet Nine and TNO discovery is out of reach. Known asteroids are plentiful but already handled by forced photometry.

### (f) Gaps
- CDS (SIMBAD/VizieR) was down and IRSA TAP timed out, so I did not re-verify Barnard W1/W2, the WISE 0855 CatWISE PM, or the Kirkpatrick 2021 values (taken from Wikipedia and the Y Dwarf Compendium).
- I did not get exact per-channel depth numbers, the PSF FWHM, or the real visit counts for each target (those need the IRSA SPHEREx coverage tool).
- Nonlinearity limits are pre-launch values (QR supplement table 17). How the pipeline handles saturation or recovers bright stars is unverified.
- The current Eps Indi Ba-Bb separation, the R Dra K amplitude, and the current RW Aur state in Nov 2026 were not checked.


---


# Part 17

## Agent 17 - SPHEREx gotchas: fake movers, fake variability, fake spectra

Sources read in full or in part: Explanatory Supplement v2.1, 2026-11-10 (ES) https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp.pdf ; Fazar et al. bestiary, SPIE 2026, arXiv 2608.09862v2 (BEST); Dowell persistence paper, JATIS 11 011208, arXiv 2608.21639 (PERS); anomaly list page https://spherex.caltech.edu/page/anomalyimages (ANOM); Lisse et al. LPSC 2026 abstract 1833 (LPSC); SOLO paper arXiv 2602.08037 (SOLO); WISE / unWISE / Backyard Worlds pages listed in (c).
VERIFIED = I read it in that source. UNVERIFIED = my inference from verified facts, not stated by the source.

### (a) Bottom line
1. The biggest fake-mover risk is anything fixed in detector pixels (persistence, crosstalk copies, frame-edge ghosts): the survey steps the sky one LVF channel per exposure and flips roll 180 deg between Survey 1 and 2, so a detector-fixed artifact lands at a new sky spot each time (UNVERIFIED inference; geometry VERIFIED ES 1.4).
2. Persistence is never zero: about 2% of pixels flagged at any time in simulation, and every pixel has an unflagged 0.01 e-/s floor (VERIFIED PERS sec 5-6).
3. Single-exposure junk (snowballs, diffuse optical transients ~1%, faint satellite streaks) is common and partly unflagged, so "seen in 1-2 frames only" should be treated as artifact by default (VERIFIED ES 2.3; rule borrowed from Backyard Worlds FAQ).
4. Fake variability mainly comes from wavelength mismatch: the same sky spot is seen at a different wavelength in each exposure, and Surveys 3-4 are shifted half a channel (VERIFIED ES 1.4).
5. Fake spectral features come from He 1.083 um leaks (0.84, 1.25, 1.49 um), other airglow lines, shuttle glow (~2.9, ~4.5 um), cosmic-ray glow gradients, dichroic edge pixels, and asteroid rotation during the ~2-week spectral build (VERIFIED ES 2.3, 2.4; SOLO; LPSC).

### (b) Artifact table

| Artifact | Looks like | Fakes | Flagged? | How often | How to recognize | Source | Verified? |
|-|-|-|-|-|-|-|-|
| Persistence (latent) | Decayed copy of a bright star at the same detector pixels in later exposures | Motion (copy moves on sky as pointing steps), variability | PERSIST if model predicts >0.1 e-/s (PSTHRESH); conservative model with "early release" | ~2% of pixels at all times (sim); one heavy saturation stays above 0.1 e-/s ~200 min, ~100 images; DQA rejects image if >20% flagged | Same detector x,y as a bright/saturated source in the previous exposure; pipeline itself cross-correlates with the previous exposure | PERS sec 3, 5, 6; ES 3.2.4, 3.2.12 | VERIFIED (motion mimic UNVERIFIED) |
| Persistence floor | Low smooth excess, unflagged | Variability in faint/low-background fields | No (below threshold) | 100% of pixels >0.01 e-/s in sim; zodi adds >=0.002 e-/s | Not separable per pixel; treat faint-level trends with caution | PERS sec 5 | VERIFIED |
| Charge bloom + extended bloom glow | Big circular NaN core, transient rings; glow tens-hundreds px away, horizontal/vertical "rays" like diffraction spikes, wedge "shadows" | Fake extended sources, spikes | BLOOM; bigger source mask for brightest stars; planets like Saturn may be under-masked | Every source that triggers OVERFLOW | Rays align with readout rows/columns, not with optics | BEST sec 3, 3.1 | VERIFIED |
| Crosstalk type 1 | Negative copy 32 rows above bright star | Negative half of a fake dipole | CROSSTALK where predicted >0.3 e-/s (R7); not in QR2 | Bands 1-3 only, strongest Band 1 | Exactly 32 px in slow-read direction | BEST 5.1; ES 2.3, 3.4.10 | VERIFIED |
| Crosstalk type 2 | Positive "donut" copies at multiples of 64 px horizontally | Fake faint companions; copies swap side when roll flips | CROSSTALK | Coupling ~1e-3; SWIR ~10x MWIR | Multiples of 64 px along fast read from a mag 6-9 star | BEST 5.2 | VERIFIED (side swap UNVERIFIED) |
| Crosstalk type 3 | Bright smear along next-read row | Fake streak | Whole row flagged | Bands 4-6, coupling can exceed 1 | Source at channel edge, row 32 away | BEST 5.3 | VERIFIED |
| Snowball / energetic CR + halo | Low-flux core, ragged ring, halo of unflagged excess | One-frame "transient" | SNOWBALL, HALO (from 2025W51 / v6.5; earlier QR2 unmasked) | More in MWIR, detector 6 worst; halos avg ~800 (SWIR) / ~4000 (MWIR) px per image; ~2% of non-SAA images re-observed for CR storms | Low flux at center, same SUR_ERROR state in core and ring, appears once | BEST 4, 7; ES 3.4.10 | VERIFIED |
| Cosmic-ray-induced glow | Faint diffuse glow, rim on Bands 4-6 edges | Spectral slope (more emission long-wavelength side, Bands 1-2) | No flag mentioned | Worse when transient fraction high | Correlates with N_TRANSIENT in header | ES 2.3 | VERIFIED |
| Frame-edge ghost | Triangle from source just off detector | Repeats in several exposures at left/right edge, can look like a persistent object | Masked for mAB <=11 | Any edge | Near frame edge, bright star just outside | ES 2.3, 3.2.9 | VERIFIED |
| Linear, beam-splitter (~10') and 8 deg ghosts; Moon stray light | Lines, disks, diffuse glow, edge glow | Fake extended features | GHOST/GHOST_EXT for DBS; 8 deg and Moon via anomaly list only | "Fraction of exposures" | Bright star off-field; anomaly codes 2, 10 | ES 2.3; ANOM | VERIFIED |
| Diffuse optical transients | Diffuse bands/glows | One-frame events | Anomaly list code 1 only; list "known to be incomplete", CSV dated 2025-08-10 | ~1% of exposures | Ephemeral, diffuse | ES 2.3; ANOM | VERIFIED |
| Satellite streaks | Lines, bright ones with halo | Fake fast mover | TRANSIENT, SATELLITE_HALO, STREAK (ZTF-style line fit); near-noise ones unflagged; incomplete in QR2 | "Many images" | Straight, crosses whole frame in one exposure | ES 2.3, 3.2.10, 3.4.10 | VERIFIED |
| He 1.083 um airglow | Horizontal band, few to 30x zodi | Spectrum: leak features at 0.84 (B1), 1.25 and 1.49 um (B2); variability | Not flagged; in variance layer; per-image fit HE_AG_AMPL etc. in header | All Band 1-2 images, varies with orbit | Use HE_AG_* keywords | ES 2.3, header table | VERIFIED |
| Aurora, other lines, shuttle glow | Line emission; glow at ~2.9 um (B4), ~4.5 um (B5-6) | Fake emission features | No; shuttle glow template exists | Aurora near poles, solar activity | Lines at 0.78, 0.84, 0.93, 1.13, 1.81, 2.63, 2.75, 4.03, 4.64 um | ES 2.3 | VERIFIED |
| Dichroic edge pixels | Low throughput rows (long end B3, short end B4) | Noisy/biased flux | DICHROIC (<50% throughput); cube ch 51-52 empty | Every image | Flag | ES 2.4, 2.5.2 | VERIFIED |
| Wrong source-mask size | Mask too small/large | Residual halo looks like variability | SOURCE size from catalog mag | Where catalog mag is wrong | Compare mask to image | ES 2.4 | VERIFIED |
| Astrometry/distortion | Field corners off | Whole-field shift = fake motion | FINAST; archive requires FINAST=0 | Corner distortion ~13-15 px (~80-90"); RMS <0.3" when good; partial fits = couple-px corner offsets | All stars shift together | ES 3.2.8, 3.2.12, 4.2.2 | VERIFIED |
| PSF varies by zone, undersampling | PSF median FWHM ~8.7" (example header) on 6.15" pixels; 21x21 zones (11x41 det 3) | Centroid jitter between epochs at different zones/wavelengths | n/a; no sub-pixel response map yet | Every image | Use per-zone ePSF | ES 3.3, 4.1.2, header | VERIFIED (centroid bias UNVERIFIED) |
| Forced photometry at fixed positions | Flux loss if position wrong | Fake fading of a mover with bad ephemeris | n/a | - | Tractor does not float positions; supply all nearby sources | ES 3.3 | VERIFIED (mover effect UNVERIFIED) |
| Asteroid rotation / phase change | Flux changes across the 1-2 week build | Fake spectral features | n/a | Rotation amplitudes several-tens of %; Ophelia ~1.5 mag | Team corrects with SOLO ground lightcurves | SOLO sec 1; LPSC Fig 5 | VERIFIED |
| LEO parallax | Near objects offset by spacecraft position | Fake motion for NEOs | n/a | - | Header has geocentric X_SC/Y_SC/Z_SC, velocities | ES header table | VERIFIED keywords; size UNVERIFIED |

### (c) WISE / Backyard Worlds lessons that transfer
- Most common false movers were stars partially subtracted by variability or small alignment errors, then cosmic rays, ghosts, latents (Kuchner et al. 2017, https://iopscience.iop.org/article/10.3847/2041-8213/aa7200/pdf, sec 2). VERIFIED.
- "Dipoles everywhere" means a pointing problem; real movers move differently from the rest; something seen in only 2 frames is most likely a ghost (BYW FAQ, https://www.zooniverse.org/projects/marckuchner/backyard-worlds-planet-9/about/faq). VERIFIED.
- Ghosts "hop back and forth, or even change color" (BYW Research page). VERIFIED. Directly relevant since SPHEREx shows a new wavelength each frame.
- WISE ghosts sit at a fixed offset from the parent star and are flagged purely by position (WISE expsup sec 4.4g). VERIFIED. SPHEREx DBS ghost masks use the same idea (ES 3.2.9).
- Latents land at the same detector pixels, so they are offset on the sky along the scan; unWISE masks latents separately per scan direction and for first and second order (Meisner et al. 2019, arXiv 1909.05444, mask bits 13-20). Near the ecliptic poles changing scan angle turns latents into arcs; bright asteroids also leave latents (WISE All-Sky expsup sec 2.3c). VERIFIED. Transfer: SPHEREx PA 0 vs 180 and deep fields at the poles are the analogs (UNVERIFIED).
- Faint candidates in flipbooks are only a start; volunteers confirm in WiseView / Finder Chart, and latents still fool people (BYW Talk thread, 2026-10-21). VERIFIED.
- unWISE avoided time-dependent artifacts by using the redundancy of extra visits (Meisner 2017, AJ 153 38, sec 5). VERIFIED.

### (d) Best-practice checklist (assembled from sources; no single official time-domain checklist found)
1. Drop or mask pixels with PERSIST, CROSSTALK, GHOST/GHOST_EXT, SNOWBALL, HALO, BLOOM, STREAK, SATELLITE_HALO, OUTLIER, DICHROIC, SOURCE as needed (ES 3.2.x). VERIFIED flags exist.
2. Do not trust QR2 images before 2025W51 for snowball/halo/bloom, or QR2 for crosstalk/streaks (ES 3.4.10). VERIFIED.
3. Check the anomaly CSV, knowing it is incomplete (ANOM). VERIFIED.
4. Use only FINAST=0 images; watch corners (ES 3.2.8). VERIFIED.
5. For a candidate, check the previous exposures for a bright source at the same detector x,y (persistence), and offsets of 32 rows / 64 columns from bright stars (crosstalk) (PERS; BEST). VERIFIED as mechanisms.
6. Use header HE_AG_* and N_TRANSIENT / L2.N_* counts to down-weight airglow-heavy or CR-storm images (ES header). VERIFIED keywords; use as filter is UNVERIFIED practice.
7. Match known asteroids with IRSA MOST (SPHEREx support added June 2026, https://caltech-ipac.github.io/irsa-tutorials/most-queries). VERIFIED.
8. For asteroid spectra, correct rotation/phase with ground lightcurves (SOLO; LPSC). VERIFIED.
9. Compare same-wavelength epochs before calling variability (UNVERIFIED practice, follows from ES 1.4).

### (e) What this means for choosing a project
- Any idea that flags movers automatically needs a detector-coordinate artifact check, or false alarms will dominate (UNVERIFIED judgment).
- Ideas that compare brightness across epochs must handle the wavelength mismatch first; raw frame-to-frame flux change is not variability.
- A known-asteroid sanity layer (MOST / ephemeris) is available and cheap.
- Spectral claims about moving objects need rotation correction; without it, features are not trustworthy.
- Use DR1 / R7-processed images, not early QR2, to avoid unmasked artifacts.
- Human-review flipbook lessons from Backyard Worlds (3+ frames, moves unlike the field) transfer well.

### (f) Gaps
- In-flight persistence paper (Fazar et al., in prep) not out; flight decay times unknown (BEST sec 6).
- No numbers found for centroid shift vs wavelength or pixel phase in SPHEREx.
- No SPHEREx or IRSA official time-domain checklist found.
- Backyard Worlds Field Guide itself (JS page) not read; categories taken from FAQ, Research page and Kuchner 2017.
- Size of LEO parallax for typical NEOs not computed.
- Anomaly CSV may be stale (file dated 2025-08-10).


---


# Part 18

## Agent 18 - Viewer and web tech for multi-epoch, multi-wavelength SPHEREx display
Checked Sat Nov 14 2026. VERIFIED = I read the page/repo today. UNVERIFIED = from search snippet only or my own background knowledge.

### (a) Bottom line
1. No off-the-shelf web viewer does WiseView-style time blinking of SPHEREx frames. Aladin Lite v3 (GPL-3) and Firefly (IRSA's own) are the strongest sky canvases; time animation has to be built on top (swap layers on a timer).
2. The IRSA SPHEREx HiPS cube has 102 wavelength layers from a DR1 coadd, not time layers. So a HiPS gives spectral browsing, but per-epoch blinking needs per-frame cutouts.
3. Cutouts are detector-oriented with SIP distortion. Something has to resample them to a common north-up grid: server-side astropy/reproject is the safe path; in-browser is possible (Aladin Lite v3 WCS FITS upload, Pyodide astropy) but SIP handling in the browser is unverified.
4. HCI research backs blink (superimposed, alternating) over side-by-side for spotting small changes, but static small multiples beat animation for trend analysis. Both have a role.
5. The strongest visible rival (minhaz-42/spherex-explorer) already ships FastAPI + React + Vite on Vercel with blink, difference, spectrum, light curve, JPL known objects, mover search, embed and a GIF export. That is the baseline to beat.

### (b) Options table
| Tool | Does well | Limits | License | Link | Verified? |
|-|-|-|-|-|-|
| Aladin Lite v3 | WebGL2, HiPS (JPEG/PNG/FITS tiles), overlay image layers, catalogs incl. Gaia HiPS catalogs with JS filter, MOC display, many projections, colormaps and asinh stretch, "upload your own FITS with WCS (beta)", ~500-600 kB | No time axis or animation API; FITS loading is beta; SIP support not confirmed; GPL-3 copyleft if you modify and redistribute | GPL-3 | https://aladin.cds.unistra.fr/AladinLite/doc/API , https://github.com/cds-astro/aladin-lite | VERIFIED (docs) |
| ipyaladin | Aladin Lite in Jupyter/JupyterLite via anywidget; Astropy tables, regions | Notebook only, not a public web app | BSD-3 | https://pypi.org/project/ipyaladin/ (0.8.1, Sep 16 2026) | VERIFIED |
| Firefly / firefly.js | IRSA's framework (React); FITS viewer, HiPS, tables, spectra charts, brushing and linking, DS9 regions, TAP/SIA search, Python client; used by the SPHEREx Data Explorer and the HiPS cube tutorial | Needs a Firefly server (Docker ipac/firefly) for FITS work; heavy | BSD-3 (UNVERIFIED) | https://github.com/Caltech-IPAC/firefly , https://caltech-ipac.github.io/irsa-tutorials/spherex-hipscube/ | VERIFIED features, license UNVERIFIED |
| JS9 | DS9-like FITS display in browser, WebAssembly, regions, blink/sync images, ReprojectData, pyjs9 | Last release v3.9.0 Dec 13 2024; creator's "final release" was 3.8; maintenance risk | MIT | https://github.com/ericmandel/js9 | VERIFIED |
| fitsjs / fitsjs-ng | Read FITS images, cubes, tables in JS; fitsjs-ng is a TypeScript rewrite with read/write | Reader only; no WCS or display | MIT (fitsjs) | https://github.com/astrojs/fitsjs , https://www.npmjs.com/package/fitsjs-ng | VERIFIED |
| OpenSeadragon | Deep-zoom tiled images, fast, plugins | No sky coordinates or WCS | BSD-3 ("New BSD"), v6.1.1 | https://openseadragon.github.io/ | VERIFIED |
| Leaflet (Legacy Survey Viewer stack) | Map-style tile viewer, URL state, overlays | Needs your own tile server and WCS math | BSD-2 (UNVERIFIED) | https://github.com/legacysurvey/imagine | VERIFIED as LS stack |
| WWT WebGL engine / pywwt | Full sky engine, HiPS, tours, research app | No SPHEREx time series support found | MIT (engine), BSD-3 (pywwt) | https://github.com/WorldWideTelescope/wwt-webgl-engine | VERIFIED |
| CARTA | Large-cube viewer (spectral profiles, moment maps); React frontend + C++ backend | Needs its own backend server; radio-cube focus | GPL-3 | https://cartavis.org/ , PASP paper Feb 17 2026 | VERIFIED |
| Stellarium Web Engine | Planetarium renderer, HiPS, Gaia stars | Public-outreach sky, not science images | AGPL-3 | https://github.com/Stellarium/stellarium-web-engine | VERIFIED |
| ESASky | Multi-mission sky explorer | Not tested for embedding or SPHEREx | UNVERIFIED | https://sky.esa.int | UNVERIFIED |

### (c) Browser vs server processing
- Reprojection to north-up: astropy reproject does interpolation, adaptive (DeForest 2004) and exact (Montage-like), and HEALPix/HiPS output (https://github.com/astropy/reproject, VERIFIED). Running it on a server is the safe route for SIP-distorted cutouts.
- Pyodide 314.0.7 ships astropy 7.2.0, numpy, pandas, opencv, bokeh; Astropy 8.1 now publishes WebAssembly wheels (https://pyodide.org/en/stable/usage/packages-in-pyodide.html, https://docs.astropy.org/en/latest/whatsnew/8.1.html, VERIFIED). reproject was not visible in the Pyodide list I saw - UNVERIFIED. Download cost of Pyodide plus astropy is tens of MB (UNVERIFIED size).
- A middle path: the server computes a resampling map once per frame (or the JS side applies the WCS + SIP polynomial), and the GPU does the resampling in a fragment shader. Feasible in principle, UNVERIFIED in an existing library.
- WebGL/WebGPU blink, difference, stretch (asinh, zscale) and shift-and-add on a stack of small (e.g. 64-256 px) aligned float textures is cheap in principle; WiseView does stretch server-side with astropy AsinhStretch and matplotlib colormaps (https://blog.backyardworlds.org/2017/09/13/wiseview, Sep 13 2017, VERIFIED).
- GPU shift-and-stack precedent: KBMOD (BSD-2) searches over 10^10 trajectories in 10-15 4Kx4K images in under a minute on a consumer GPU, and sums precomputed likelihood images instead of shifting pixels; limit about 100 4Kx4K images in GPU memory (https://github.com/dirac-institute/kbmod, AJ 2019 and 2021 papers, VERIFIED). This is the reference for any "shift and add" feature.
- Space-time coverage: IVOA MOC 2.0 (Jul 27 2022) defines STMOC; mocpy (Rust core) does space-time intersections in milliseconds; Aladin Lite v3 displays MOCs (https://www.ivoa.net/documents/MOC/20220727/REC-moc-2.0-20220727.html, VERIFIED). Useful for "which epochs cover this spot".
- SPHEREx HiPS cube: 102 frames in wavelength order, frames 50 and 51 blank (dichroic), data URL hips_20261026 (https://caltech-ipac.github.io/irsa-tutorials/spherex-hipscube/, VERIFIED). No time dimension.
- Caveat from rival docs: two visits of the same spot usually see different wavelengths (linear variable filter), so a naive difference image can show spectrum, not change (minhaz-42 README, VERIFIED).

### (d) Plotting and linking
- uPlot: Canvas 2D, ~50 kB, 166k points in 25 ms, MIT (https://github.com/leeoniya/uPlot, VERIFIED). Good for light curves and spectra.
- Plotly.js (MIT), Bokeh (BSD-3, also in Pyodide), Vega/Vega-Lite (BSD-3), D3 (ISC): licenses UNVERIFIED today. Plotly and Vega give heatmaps for spectro-temporal waterfalls (time on one axis, wavelength on the other, color = flux).
- Click-pixel-to-spectrum linking is built into Firefly (brushing and linking across images, tables, charts, VERIFIED). With Aladin Lite, linking is custom JS on click events (UNVERIFIED API name).
- Datacube viewers for reference: CARTA spectral profiles, Firefly HiPS-cube layer selector.

### (e) Visualization research
- Rensink, O'Regan, Clark 1997 "To See or Not to See": with a blank flicker, changes took 17.1 alternations (10.9 s) for marginal items; without the blank, 1.4 alternations (0.9 s). Lesson: blink must have no gap or reflow between frames (https://www2.psych.ubc.ca/~rensink/publications/download/PsychSci97-RR.pdf, VERIFIED).
- "Shuffling your way out of change blindness" (PMC4690818): alternating superimposed images found changes about 6 s faster than side-by-side; benefit fades when images are misaligned by large shifts (VERIFIED). Supports accurate registration before blinking.
- Gleicher et al. 2011 "Visual Comparison for Information Visualization": juxtaposition, superposition, explicit encoding (e.g. difference); blink is a superposition design (https://graphics.cs.wisc.edu/Papers/2011/GAWJHR11/paper.pdf, VERIFIED).
- Ondov et al. 2018 "Face to Face" (IEEE TVCG Jan 2019): animated transitions and superposition beat standard small multiples for finding the biggest mover (https://hcil.umd.edu/visualcomparison, VERIFIED).
- Robertson et al. 2008 "Effectiveness of Animation in Trend Visualization": animation least effective for analysis; small multiples more accurate (https://ieeexplore.ieee.org/document/4658146, VERIFIED abstract).
- "Comparative Layouts Revisited" (arXiv 2009.00192): animation good for small differences, weak for large ones; staged animation helps (VERIFIED).
- Multi-dimensional display ideas from general practice (UNVERIFIED as studied for SPHEREx): false-color RGB from three wavelength bins, small-multiples grid (time x wavelength), space-time cube, per-source spectral glyphs, waterfall heatmaps.

### (f) Reference architecture sketch (neutral)
Browser (React/Vite or plain JS) -> sky canvas (Aladin Lite or Leaflet/OpenSeadragon or raw WebGL) + chart (uPlot/Plotly) + URL state (?ra=&dec=&fov=&epochs=).
-> API proxy (FastAPI on Lambda/Vercel/VM in us-east-1) calls IRSA SIA2/TAP and cutouts (no CORS), caches results.
-> Data path option A: server fetches cutout MEF, reprojects to north-up with astropy/reproject, applies FLAGS, returns float PNG/FITS or JSON.
-> Option B: browser reads FITS bytes from S3 with Range requests (CORS *), and does WCS + GPU resample.
-> Overlays: Gaia/CatWISE via CDS HiPS catalogs (browser) or LSDB/HATS (Gaia DR3 at s3://stpubdata/gaia/gaia_dr3/public/hats, server) (https://docs.lsdb.io/en/stable/getting-started.html, VERIFIED).
-> Precomputed demo targets as static files for a reliable demo.

### (g) Gaps
- "Nakshatra Chronos" and "Specula" repos not found in this pass.
- Aladin Lite v3 SIP support and exact time-animation pattern not tested.
- reproject under Pyodide not confirmed; WebGPU astro libraries not searched.
- Firefly, Plotly, Bokeh, Vega, D3 licenses not re-read today.
- ESASky embed API not checked.


---


# Part 19

## Agent 19 - Automatic detection and characterization of moving/changing objects (SPHEREx lens)
Research date: Sat Nov 14 2026. Read-only. VERIFIED = I saw the paper/repo page in this session. UNVERIFIED = from general knowledge, not re-checked today.

### (a) Bottom line
1. The SPHEREx Solar System Object Catalog uses forced photometry at positions predicted by kete for known objects. I found no published blind search for unknown movers in SPHEREx, and no SPHEREx difference-image product (VERIFIED, pipeline paper + EPSC2024 abstract).
2. Spectral typing of known fast movers in SPHEREx is already done: the SPIFF library (Gagne et al., Apr 2026) gives spectra for 6,003 ultracool dwarfs, 947 of them new, with automated typing. "Spectra of known brown dwarfs" is not new any more. Using spectra to discover them is still open.
3. Pixel-level temporal deep learning for movers is now an established line of work (SMDET on unWISE, W-Net 3D U-Net on TESS, YOSO motion filter on DECam, all 2026). None has been applied to SPHEREx, and none handles a wavelength that changes per exposure (the LVF).
4. Generative "predict the expected sky, flag the residual" models exist, but only outside optical/IR survey moving-object work: ConvLSTM next-frame on Fermi gamma-ray maps (2026), conditional video diffusion on satellite video (2023). On SPHEREx I found zero diffusion or video-model applications.
5. The highest-novelty gap is a spectral-temporal joint model that uses the LVF wavelength sequence as signal. Example: an object whose per-exposure fluxes do not fit one stationary SED, or a wavelength-conditioned expected-sky model. I found no paper on this (gap, not proof of absence).

### (b) Methods table (sorted by novelty for SPHEREx)
| Method | Category | What it does | Applied to SPHEREx? | Novelty for SPHEREx | Team-skill fit | Link | Date | Verified? |
|-|-|-|-|-|-|-|-|-|
| LVF-wavelength-aware SED-consistency test (is the per-exposure flux sequence consistent with one static source?) | Spectral-temporal | Uses the fact that each visit samples a different wavelength; a mover or variable breaks the smooth-SED fit | No paper found | High - only SPHEREx has this sampling; it turns an instrument quirk into a detection feature | Medium-high (probabilistic modeling) | none found | - | Gap (searched, not found) |
| Generative "expected sky" via next-frame / video prediction (ConvLSTM) | Generative/temporal | Learns normal sky evolution, residual = anomaly score | No (Fermi-LAT only) | High - no IR imaging-survey moving-object use found; would need wavelength conditioning | Very high | https://arxiv.org/html/2605.22112 | 2026 | VERIFIED |
| Conditional video diffusion for anomaly (frame prediction) | Generative/temporal | Diffusion predicts future frames; mismatch = anomaly | No (Earth-observation satellite video) | High - none in astronomy found | Very high | https://arxiv.org/html/2306.05376v1 | 2023 | VERIFIED |
| SMDET (3D conv + ConvLSTM segmentation) | ML temporal | Segments faint, fast movers in unWISE image time series; trained on injected fakes | No (unWISE) | High if ported - SPHEREx is a deeper 0.75-5 um time series, same 6" scale as WISE | Very high | https://iopscience.iop.org/article/10.3847/1538-3881/ae593c ; https://arxiv.org/html/2608.00046v2 | Apr 2026 / Aug 2026 | VERIFIED |
| W-Net (stacked 3D U-Nets) trajectory-agnostic | ML temporal | Filters background and flags mover pixels in TESS cubes; rotation augmentation removes the speed/direction prior | No | High - same cube logic, no velocity grid | Very high | https://iopscience.iop.org/article/10.3847/1538-3881/ae6cfc | Jun 2026 | VERIFIED |
| YOSO (Gaussian motion filter + DL) | Classical+ML | Pixel motion filter instead of a discrete velocity grid; low false positives; 11 new TNOs | No | High - competitor field has 0 shift-and-stack | Medium | https://iopscience.iop.org/article/10.3847/1538-3881/ae6cf4 | Jun 2026 | VERIFIED |
| KBMOD GPU shift-and-stack | Classical | Max-likelihood search over velocity grid on difference images | No | High - none found on SPHEREx; LVF means each frame has a different wavelength, so the stack must be SED-weighted | Medium | https://github.com/dirac-institute/kbmod | active | VERIFIED |
| Normalizing-flow spectral outlier (Mendis) | ML anomaly | Likelihood of a spectrum under a learned density; low likelihood = interesting | No | Medium-high - would fit 102-channel spectra; uncertainty built in | High | https://arxiv.org/html/2207.02785v1 | 2022 | VERIFIED |
| Diffusion spectral prior / posterior sampling (POSTELLAR, spec-DDPM) | Generative | Score-based prior for denoising or for posterior sampling of spectra, with uncertainty | No | Medium-high - could reconstruct sparse, rotation-affected SPHEREx asteroid spectra | Very high | https://arxiv.org/html/2609.05599v1 ; https://iopscience.iop.org/article/10.1088/1674-4527/adf711 | Sep 2026 / Sep 2025 | VERIFIED |
| Diffusion denoise/deconvolve images (BGRem, DPS deconvolution) | Generative | Removes background or deconvolves; +7% true sources (BGRem, MeerLICHT) | No | Medium - helps detection, but priors can invent features (the DPS paper warns about this) | Very high | https://arxiv.org/html/2510.04718v3 ; https://arxiv.org/html/2411.19158v2 | 2025 | VERIFIED |
| Astronomaly / Protege active anomaly + human loop | ML anomaly | Isolation forest on learned features, then active learning from human scores; 1,635 of top 2,000 interesting | No | Medium-high - matches the CCC human-AI ask | High | https://github.com/MichelleLochner/astronomaly ; https://iopscience.iop.org/article/10.3847/1538-3881/ada14c | 2021 / Feb 2025 | VERIFIED |
| scarlet2 multi-epoch forward scene model | Generative (physical) | Jointly fits static host + variable/transient component across epochs and bands | No | Medium - natural fit to LVF per-exposure modeling | Medium-high | https://arxiv.org/html/2409.15427v2 | 2024 | VERIFIED |
| Multimodal contrastive (AstroCLIP, AION-1, AstroM3) | Foundation | Shared embedding of images, spectra, light curves | Partly: SPHEREx + DESI contrastive star-galaxy (Jul 2026) | Medium - exists for galaxies; nothing for movers | High | https://academic.oup.com/mnras/article/531/4/4990/7697182 ; https://arxiv.org/html/2510.17960 ; https://arxiv.org/html/2607.20797 | 2024-2026 | VERIFIED |
| SpectraFM / AstroPT / Multimodal Universe | Foundation | Transformer pretrain on spectra (any range) or images; MMU = 100 TB training set | No (no SPHEREx subset in MMU list) | Medium - fine-tune target, not a discovery method | High | https://arxiv.org/html/2411.04750 ; https://github.com/Smith42/astroPT ; https://github.com/MultimodalUniverse/MultimodalUniverse | 2024-2025 | VERIFIED |
| THOR / HelioLinC / heliolinx | Classical linking | Links detections into orbits without (THOR) or with tracklets; HelioLinC3D runs in Rubin | No | Medium - SPHEREx passes give intra-pass tracklets; nobody has linked unknown SPHEREx detections | Low-medium | https://github.com/moeyensj/thor ; https://github.com/heliolinx/heliolinx | 2021 / 2018+ | VERIFIED |
| ZOGY proper image subtraction | Classical | Optimal difference image + significance map | No SPHEREx epoch differences (IRSA demo only subtracts two detectors for colour) | Medium - needs same-wavelength pairs, rare with LVF | Low | https://github.com/pmvreeswijk/ZOGY | 2016 | VERIFIED |
| Alard-Lupton / HOTPANTS | Classical | Kernel-matched subtraction | No | Medium-low | Low | https://github.com/acbecker/hotpants | 1998+ | UNVERIFIED |
| Proper motion + parallax fitting (CatWISE2020) | Classical | Per-source motion fit in epoch coadds; 20-100 mas/yr precision | No SPHEREx motion catalog found | Medium - SPHEREx 2 yr baseline is short; mostly a ground-truth source | Low | https://iopscience.iop.org/article/10.3847/1538-4365/abd805 | 2021 | VERIFIED |
| CNN real/bogus (braai, active+semi-supervised RB) | ML vetting | Classifies difference-image cutouts as real or artifact | No | Low-medium - standard; 39 of 114 teams already do AI flagging | High | https://academic.oup.com/mnras/article/489/3/3582/5554758 ; https://www.aanda.org/articles/aa/full_html/2025/01/aa48581-23/aa48581-23.html | 2019 / 2025 | VERIFIED |
| Hubble Asteroid Hunter (volunteer labels -> AutoML) | ML + citizen | 1,701 new trails, 61% unmatched to MPC | No | Low-medium as a method; strong precedent | Medium | https://www.aanda.org/articles/aa/full_html/2022/05/aa42998-21/aa42998-21.html | 2022 | VERIFIED |
| SPIFF template typing of fast-moving UCDs | Spectral | Moving-source extraction + 0.75-5 um templates + auto typing | YES | Low now (done); the extraction tool is reusable | Medium | https://arxiv.org/abs/2604.22012 | Apr 2026 | VERIFIED |
| WISE dipole detection | Classical | Movers show +/- dipoles in epoch differences | No | Low-medium | Low | not found today | - | UNVERIFIED |

### (c) Generative/diffusion in astronomy notes
- Images: diffusion is used for denoising (BGRem), Bayesian deconvolution (DPS), and radio sky reconstruction (A&A 2024, https://www.aanda.org/articles/aa/full_html/2024/03/aa47948-23/aa47948-23.html, VERIFIED). All are single-epoch. None is time-domain or about moving objects.
- Spectra: spec-DDPM denoising, POSTELLAR diffusion priors, and photometry-to-spectrum diffusion (https://arxiv.org/html/2211.05556v1, 2022, VERIFIED). None on SPHEREx.
- Time-domain anomaly: the closest astronomy example is ConvLSTM next-frame prediction on Fermi maps (residual = anomaly). Muthukrishna et al. 2022 use autoregressive light-curve prediction error as an anomaly score (https://academic.oup.com/mnras/article/517/1/393/6705438, VERIFIED). WGAN latent-space anomalies on HSC (https://arxiv.org/pdf/2012.08082, VERIFIED).
- Simulators for training: AstroSkyFlow (2026) simulates time-domain sky frames with asteroids from the JPL API (https://arxiv.org/html/2606.02140, VERIFIED). This kind of tool is useful for injection.
- SPHEREx-specific ML found: SPHEREx+DESI contrastive star-galaxy separation, and ML continuum fitting in the Ices pipeline (https://iopscience.iop.org/article/10.3847/1538-4357/ae53e0, Apr 2026, VERIFIED). I found no diffusion, video, or foundation-model work on SPHEREx time series.
- Risk to name: generative priors can hallucinate sources. The DPS deconvolution paper quantifies "prior-driven features". Any generative detector needs calibrated false-alarm control.

### (d) Validation methods
- Injection-recovery: SMDET is trained and tested on synthetic movers injected into real unWISE frames. KBMOD and YOSO report recovery of known objects (YOSO found 45 of 73 known plus 11 new). Report completeness vs magnitude and rate of motion. VERIFIED (sources above).
- Known-object ground truth: kete predicts every known asteroid in each SPHEREx frame (https://arxiv.org/pdf/2509.04666, VERIFIED). The pipeline already writes an ancillary SSO parquet file per image (VERIFIED). JPL Horizons/SBDB serves as an independent check.
- Stellar movers ground truth: Gaia DR3 and CatWISE2020 proper motions, and the SPIFF/MOCA list of 6,003 UCDs (https://mocadb.ca/) as positive labels. VERIFIED.
- False-alarm control: run on empty or scrambled-time cubes (shuffled epoch order) and on low-ecliptic vs high-ecliptic fields. Report false positives per square degree. The THOR purity metric (97.7-100% on ZTF) is a benchmark. Partly VERIFIED (THOR numbers); the scrambling protocol is standard practice, UNVERIFIED for a specific paper.
- Spectral validation: compare the recovered asteroid spectrum with a C/S-type template. Correct for rotation using SOLO light curves (171 Ophelia example, LPSC 2026). VERIFIED.
- Metrics: completeness, purity, false positives per field, astrometric residual, and calibration of uncertainty (expected vs observed error).

### (e) What this means for choosing a project (method ranking only)
- The biggest open area is methods that treat the LVF wavelength sequence as information instead of a nuisance. No prior work turned up, and no competitor addresses it.
- Temporal or generative pixel models (SMDET, W-Net, next-frame prediction) are proven elsewhere, unused on SPHEREx, and the closest match to the team's skills. Scientific value depends on wavelength conditioning plus injection-recovery.
- Blind discovery of unknown SSOs in SPHEREx is open, because the official SSOC uses forced photometry on known objects only. Known objects (kete) still give free labels.
- Plain CNN real/bogus flagging and spectral typing of known brown dwarfs are crowded or already published. They are low novelty on their own.
- Uncertainty and human-in-the-loop parts (flows, Astronomaly-style active learning) add value that matches the CCC 2026 asks, and work as a layer on top of any detector.

### (f) Gaps
- I did not verify that "SPHEREx difference imaging" is absent from every non-refereed source. The search covered the pipeline paper, explanatory supplement and IRSA tutorials only.
- WISE dipole method: no primary source found today.
- HOTPANTS link not re-checked.
- I did not read the full SMDET method paper's metrics (completeness numbers).
- I did not check AAS 249 (Jan 2027) abstracts or the newest arXiv (Oct-Nov 2026) for SPHEREx ML on moving objects.
- Spectral signatures for comet vs asteroid vs brown dwarf were covered only at a high level: CO2 4.26 um and H2O 2.7 um coma lines in 3I/ATLAS; H2O, CH4, CO, CO2 bands in UCDs; 2.7 um hydration and >3.3 um thermal emission in asteroids. All VERIFIED from the SPHEREx papers above, but no quantitative separability study was found.


---


# Part 20

## Agent 20 - Cross-match catalogs and services: "what is this mover?" (Sat Nov 14 2026)

Tests run ~19:55-20:05 UTC Nov 14 2026 with curl from one machine. MEASURED = my own test today. VERIFIED = read in a source today. UNVERIFIED = from background knowledge or the brief, not re-read today.

### (a) Bottom line
1. Gaia DR3 TAP works today (MEASURED: Barnard's Star returned in 2.8 s, pmdec 10362 mas/yr, ref_epoch 2016.0). SIMBAD and VizieR are still down (MEASURED: CDS "Page unavailable" 404 on SIMBAD TAP, SIMBAD home, VizieR home; VizieR TAP timed out at 30 s).
2. Asteroid ID: SkyBoT cone search works and sends `Access-Control-Allow-Origin: *` (MEASURED, 8 s). JPL Horizons API works (MEASURED, 0.3 s). JPL sb_ident doc page loads, but two real 0.2 deg field queries timed out at 45 s and 100 s (MEASURED).
3. The SPHEREx pipeline already computes known solar-system object positions per frame with kete and stores them in an "ancillary parquet file" (VERIFIED, pipeline paper). I could not find that parquet in a small public S3 listing (only FITS files seen), so public availability is UNVERIFIED.
4. Browser-direct access is limited: only SkyBoT and the IRSA S3 buckets (`nasa-irsa-spherex`, `nasa-irsa-wise`) returned CORS headers. Gaia TAP, IRSA TAP, Horizons, sb_ident and data.lsdb.io sent none (MEASURED). A browser app needs a small proxy or backend.
5. LSDB hosts HATS Gaia DR3 (1,811,709,771 rows, with pm and ruwe), Gaia epoch photometry, 2MASS, AllWISE, NEOWISE, Legacy Surveys DR10.1, ZTF DR14-22, VSX monthly snapshots to 2026-10 and Rubin alerts (MEASURED directory listing). This is the fastest bulk "is it known" path.

### (b) Catalog / service table

| Name | Contents | Depth / epoch | Access | Browser CORS? | Status today | Link | Verified? |
|-|-|-|-|-|-|-|-|
| Gaia DR3 gaia_source | 1.81B sources, ra, dec, pmra, pmdec, parallax, ruwe, G/BP/RP | G~21; ref_epoch 2016.0 | TAP sync/async, astroquery.gaia | No (OPTIONS 403) | Up, 2.8 s | gea.esac.esa.int/tap-server/tap | MEASURED |
| Gaia DR4 | epoch astrometry, more | due Dec 2 2026; archive offline Nov 25 - Dec 2 | same | - | Not out | - | UNVERIFIED (brief) |
| CatWISE2020 | 1.89B W1/W2 sources, pmra/pmdec | W1~17; positions at MJD 57170 (2015.405) | IRSA TAP `catwise_2020`, VizieR II/365 | No | IRSA TAP schema up; cone query timed out at 60 s | irsa.ipac.caltech.edu/data/WISE/CatWISE/gator_docs/catwise_colDescriptions.html | MEASURED + VERIFIED epoch |
| AllWISE | W1-W4, pm (poor) | epoch ~2010.5 | IRSA TAP, S3 `wise/allwise/catalogs/p3as_psd/`, LSDB HATS | S3 yes | S3 up | nasa-irsa-wise.s3.us-west-2.amazonaws.com | MEASURED |
| NEOWISE single exposure | per-epoch W1/W2 detections 2013-2024 | time series | IRSA TAP, S3 `wise/neowiser/catalogs/`, LSDB `wise/neowise` | S3 yes | Up (listing) | same | MEASURED (listing) |
| unWISE | W1/W2 deep coadds and catalog | deeper than AllWISE | legacysurvey.org, IRSA | - | not tested | unwise.me | UNVERIFIED |
| 2MASS | JHK, epoch ~1998-2001 (per-source date) | Ks~14.3 | IRSA TAP, LSDB `two_mass` | - | LSDB up | data.lsdb.io/hats/two_mass | MEASURED (listing) |
| UKIDSS/UHS/VHS | deep J/K, gives a second epoch | K~18 | WSA/VSA, VizieR | - | VizieR down | - | UNVERIFIED |
| Pan-STARRS DR2 | grizy, own pm in some tables | i~23 | MAST CasJobs/API | - | not tested | catalogs.mast.stsci.edu | UNVERIFIED |
| Legacy Surveys DR10 | grz(i) Tractor; pm only copied from Gaia for matched stars | r~23-24 | NOIRLab Data Lab, LSDB `legacysurvey_dr10.1` | - | LSDB up | data.lsdb.io/hats/legacysurvey_dr10.1 | MEASURED listing, pm detail UNVERIFIED |
| Kirkpatrick 2024 20 pc census | stars + brown dwarfs within 20 pc | astrometry with epochs/refs | CSV (2.3 MB) at Exoplanet Archive | - | page indexed | exoplanetarchive.ipac.caltech.edu/docs/20pcCensus.html | VERIFIED |
| UltracoolSheet v2 | 3,890 (4,076 with companions) UCDs, pm, plx, CatWISE, Gaia DR3 | M6 and later | CSV on Zenodo, Google Sheet | Zenodo - | Jul 3 2025 version | zenodo.org/records/15802304 | VERIFIED |
| Backyard Worlds candidates | 3,006 candidates | - | arXiv 2604.01323 tables | - | - | arxiv.org/abs/2604.01323 | UNVERIFIED (brief) |
| MOCAdb / SPIFF | 6,003 UCDs typed with SPHEREx | - | MOCAdb SQL | - | - | - | UNVERIFIED (brief) |
| SIMBAD TAP | names, types, pm, bibliography | all literature | TAP, astroquery | - | DOWN (404) | simbad.cds.unistra.fr | MEASURED |
| VizieR / TAPVizieR / CDS XMatch | all published tables | - | TAP, XMatch | - | DOWN (404 / timeout) | vizier.cds.unistra.fr | MEASURED |
| SkyBoT | known SSOs in a cone at an epoch, with motion arcsec/h | MPC-based, V mag | REST GET, JSON | Yes (*) | Up, 8 s | ssp.imcce.fr/webservices/skybot/ | MEASURED |
| JPL sb_ident | SSOs in a FOV for an observer and time | asteroids/comets | REST | No | Doc up; queries timed out | ssd-api.jpl.nasa.gov/doc/sb_ident.html | MEASURED |
| JPL Horizons API | ephemeris for one named body | - | REST JSON | No | Up, 0.3 s | ssd.jpl.nasa.gov/api/horizons.api | MEASURED |
| IRSA MOST | which archive images contain a given orbit, incl. SPHEREx | - | web form, API | - | Up (page 200) | irsa.ipac.caltech.edu/applications/MOST/ | MEASURED |
| kete | n-body propagation of full MPC catalog, FOV checks, thermal/optical mags; Python with Rust core, BSD-3 | - | pip / GitHub | n/a | repo indexed | github.com/Caltech-IPAC/kete | VERIFIED |
| SPHEREx L2 FITS + SSO parquet | 6 HDUs (IMAGE, FLAGS, VARIANCE, ZODI, PSF, WCS-WAVE); per-frame kete SSO list | QR3 weeks 2026W20+ seen | S3 `nasa-irsa-spherex` (dr1, qr2, qr3), IRSA TAP `spherex.*` (obscore etc.) | S3 yes | Up | caltech-ipac.github.io/spherex-archive-documentation | MEASURED + VERIFIED; parquet public? UNVERIFIED |
| AAVSO VSX | variable star index | all types | API; LSDB monthly HATS | - | aavso.org API gave Cloudflare 403 to curl; LSDB copies up to 2026-10 | data.lsdb.io/hats/vsx | MEASURED |
| Gaia DR3 variability | vari_summary and class tables, epoch photometry | G | Gaia TAP; LSDB `gaia_dr3_epoch_phot` | No | TAP up | - | MEASURED (TAP), table names UNVERIFIED |
| ZTF light curves | DR14-DR22 | r~20.5 | IRSA API; LSDB HATS | - | LSDB up | data.lsdb.io/hats/ztf_dr22 | MEASURED (listing) |
| ATLAS variables | ~4.7M variables | o/c ~18 | MAST HLSP, VizieR | - | not tested | - | UNVERIFIED |
| MPC | orbits, observations | - | MPC APIs | Reflected Origin on a 404 path | not confirmed | minorplanetcenter.net | MEASURED (partial) |

### (c) Known-vs-unknown logic used in practice
- Backyard Worlds Cool Neighbors: a mover is "already known" if it is in SIMBAD, or in Gaia with a parallax and proper motion; a Gaia source without astrometry can still be submitted, and Gaia detection implies a warmer, lower-priority object (VERIFIED, Zooniverse FAQ). Brief adds: 1 arcmin SIMBAD radius, PM>100 mas/yr, VizieR checks (UNVERIFIED today).
- ZTF/Fink: ZTF tags each alert with the nearest MPC object within 30 arcsec (astcheck on a daily ephemeris). Fink keeps only matches under 5 arcsec, requires the MPC object to be closer than the nearest Pan-STARRS source, and ndethist<=2. "New SSO candidate" = no MPC match, 1-2 detections within 30 min, not within 5 arcsec of a Pan-STARRS star-like source (sgscore1<0.76) (VERIFIED, Fink 2022 note and A&A 2023).
- Rubin: associates to known MPC SSOs with a 1 arcsec radius before sending alerts (VERIFIED, Fink/LSST docs).
- SPHEREx pipeline: kete predicts known SSO positions per frame (ancillary parquet), and a source mask flags pixels hit by known catalog sources; an outlier step flags transients (VERIFIED, pipeline paper ApJS 2026).
- Generic order that follows from these: (1) mask known SSOs at the frame time, (2) propagate Gaia/CatWISE positions with pm to the SPHEREx epoch and match, (3) check name catalogs (SIMBAD, UltracoolSheet, 20 pc), (4) check variability catalogs for flux changes, (5) only then label "unknown".

### (d) Pitfalls
- Epochs differ: Gaia 2016.0, CatWISE 2015.405, AllWISE ~2010.5, 2MASS ~2000. A 1 arcsec/yr star moves ~10 arcsec from 2016 to 2026, larger than a SPHEREx 6.2 arcsec pixel (pixel size UNVERIFIED today).
- Gaia misses very red, cold brown dwarfs (late T and Y), so "not in Gaia" is weak evidence of new (VERIFIED in spirit by BYW FAQ).
- SPHEREx pixels are large, so blends of a mover with a background star are common; match radius must scale with PSF and pm uncertainty.
- CatWISE pm has known issues for blends and bright stars, and ~20 mas/yr precision at W1~15 (brief, UNVERIFIED).
- Very high-pm objects can fail catalog cross-IDs between surveys (counted as two sources).
- Asteroid services differ in speed: sb_ident timed out twice today; SkyBoT was 8 s per cone.
- SIMBAD/VizieR outage today removes the main "is it published" check.

### (e) What this means for choosing a project
- Any idea that labels movers can rely on Gaia TAP, SkyBoT, Horizons, IRSA S3 and LSDB today; SIMBAD/VizieR cannot be assumed up during the build.
- A pure browser app will hit CORS walls on Gaia, IRSA TAP and JPL; plan a thin backend or pre-built cache.
- Known-asteroid labeling may already be solved inside the SPHEREx pipeline (kete parquet); check whether it is public before building it again.
- Bulk cross-match via LSDB HATS is fast and avoids TAP rate limits; per-object TAP is fine for small demos.
- Gaia DR4 lands Dec 2 with an archive outage Nov 25 - Dec 2, which can affect any demo date in that window.

### (f) Gaps
- Not tested: Pan-STARRS MAST, NOIRLab Data Lab, UKIDSS/VHS, MPC API, ATLAS, MOCAdb, ZTF IRSA API.
- Rate limits not measured for any service.
- CatWISE IRSA TAP cone timed out; not retried async.
- Public availability of SPHEREx SSO parquet not confirmed.
- License text not re-read; Gaia, IRSA and CDS data are free to use with citation (UNVERIFIED wording); kete is BSD-3 (VERIFIED).


---


# Part 21

## Agent 21 - Accessibility, sonification, multi-sensory (research only, Nov 14 2026)

### (a) Bottom line
1. Sound can carry real signal, but only when the signal is strong: in the Astronify test (192 people), listeners found SNR 30-100 transits 85-100% of the time and were at guessing level at SNR 3-5. Plots beat sound at medium SNR.
2. Pairing sound with visuals works better than sound alone. Diaz-Merced's thesis found audio helped only once a moving cursor line was synced to the sound.
3. Public sonification is proven for engagement, not for detection: Chandra's Frontiers 2024 study (3,184 people) found learning gains, but they were SELF-REPORTED. Webb, Chandra and Eclipse Soundscapes all used blind consultants as co-designers.
4. I found no published sonification of moving objects across an image time series (asteroid "by ear") and no SPHEREx sonification. This is an open gap, not proof that it does not work.
5. Any blink tool must stay under WCAG 2.3.1 (no more than 3 flashes in any 1 second, plus a separate red-flash limit) and must not depend on colour alone. Space Apps 2025 had 114,094 people in 167 countries, and mobile is 84% of internet connections, so low-bandwidth design matters.

### (b) Sonification techniques
| Technique | Mapping | Evidence people can detect signals | Example | Link | Verified? |
|-|-|-|-|-|-|
| Pitch = brightness (light curve) | flux to pitch, time to time | 192 people: 85-100% at SNR 30-100, guessing level at SNR 3-5; experts 2-3x better with plots at SNR 7-10; training needed (MNRAS, Sep 2022) | Astronify (STScI/MAST) | https://academic.oup.com/mnras/article/516/4/5674/6698731 | VERIFIED |
| Pitch vs duration vs both (transits) | brightness to pitch, duration, or both | Above chance by ear, but plots did better and astronomers beat non-astronomers. Sound made people say "yes" more often, plots made them cautious (AJ, Mar 2024) | lab study | https://iopscience.iop.org/article/10.3847/1538-3881/ad2943 | VERIFIED |
| Audio plus a synced cursor | sound with a sweeping visual line | Sound alone gave no benefit. Sound plus a synced line helped scientists find events hidden in noise (PhD thesis, Dec 2014) | xSonify, Diaz-Merced | https://theses.gla.ac.uk/5804 | VERIFIED |
| Spectral audification | spectrum played directly as a sound wave | 58 listeners' ratings matched the measured SNR, line width and flux ratios. The order clips were heard changed the ratings (RASTI 2023) | STRAUSS, galaxy spectra and datacubes | https://arxiv.org/html/2306.10126v1 | VERIFIED |
| Spectrum scan | wavelength to pitch (longer = lower), light blocked to volume, water features to a droplet sound | No detection test; outreach only (Aug 2022) | Webb WASP-96 b | https://science.nasa.gov/asset/webb/exoplanet-wasp-96-b-sonification-niriss-transmission-spectrum | VERIFIED |
| Image scan | cursor sweeps the image, brightness to pitch, object type to instrument (marimba, cymbal for spiky stars) | Self-reported learning gains, n=3,184 (Frontiers, Mar 2024) | Chandra "A Universe of Sound", Stephan's Quintet | https://www.frontiersin.org/journals/communication/articles/10.3389/fcomm.2024.1288896/full ; https://www.nasa.gov/missions/chandra/cosmic-harmonies-sonifications-from-nasa-telescopes | VERIFIED |
| Spatial or pan mapping | position to stereo or 3D audio, object to instrument | Strong positive feedback from blind audiences (survey, not a detection test) | Audio Universe planetarium show (STRAUSS) | https://www.astroscu.unam.mx/rmaa/RMxAC..57/PDF/RMxAC..57_jtrayford-X.pdf | VERIFIED (feedback only) |
| Familiar sounds (skeuomorphic) | water = vapour, sand = dust, cracking ice = asteroid collisions | Report says spatial mapping worked well for movement over time; no numbers (UNOOSA report, May 2023) | various | https://www.unoosa.org/documents/pdf/Space4PersonswithDisabilites/UNOOSA_Special_Report_on_Sonification_2023.pdf | VERIFIED (claim only) |
| User-adjustable pitch, volume and timbre | the user tunes the mapping | User-centred tests; no accuracy numbers (JOSS, Jan 2024) | sonoUno | https://joss.theoj.org/papers/10.21105/joss.05819.pdf | VERIFIED |
| Sonification plus chatbot (citizen-science task) | meteor echoes to audio, voice dialogue | 57 visually impaired students: 90.4% agreement with experts, 79.7% detection, quick gains after the first try (ACM TACCESS, Jun 2026) | meteor-echo task | https://dl.acm.org/doi/10.1145/3812854 | VERIFIED |
| Discovery by ear | light curves and periods | Variable star UCAC4 459-09273 found by blind students (RASTI preprint, Dec 2024). Diaz-Merced reports finding periods by sound (interview, 2019) | StarSound and others | https://arxiv.org/pdf/2412.00185 ; https://fm4.orf.at/stories/2987076 | VERIFIED (secondary) |

Field size: about 100 sound-based astronomy projects (Nature Astronomy, Aug 2022, https://www.nature.com/articles/s41550-022-01721-z, VERIFIED). Data Sonification Archive: 119 astronomy examples as of Apr 2023 (https://sonification.design/, VERIFIED via UNOOSA). The Perseus black hole audio got 173M plays on Twitter (UNOOSA, VERIFIED). Kilonova sonification: not checked (UNVERIFIED).

### (c) Accessibility requirements for blink and change tools
- WCAG 2.3.1 (Level A): nothing may flash more than 3 times in any 1-second period unless it stays below the general-flash and red-flash thresholds. This applies to the whole page (https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html, VERIFIED). Exactly 3 Hz is the upper limit, so a cap below 3 Hz or a user-controlled toggle is safer. False-colour reds fall under the separate red-flash rule (my reading, UNVERIFIED for a specific product).
- NASA web: Section 508 and WCAG 2.0 AA, under NPR 2800.2A; manual accessibility testing is mandated (https://www.nasa.gov/general/accessibility/, Jul 2023; https://nodis3.gsfc.nasa.gov/OPD_Docs/NID_2800_147_.pdf, extended to Sep 2026, VERIFIED).
- Colour: use viridis or cividis and avoid jet; use shapes and line styles; describe by shape, not colour; a palette is colour-blind-proof if each colour has its own lightness (CTAO guide, Mar 2025, https://www.ctao.org/wp-content/uploads/ColourBlindFriendlyPractices_v2_032025.pdf; Crameri 2024, https://currentprotocols.onlinelibrary.wiley.com/doi/10.1002/cpz1.1126, VERIFIED).
- Tactile: Tactile Universe has free 3D galaxy files (https://tactileuniverse.org/, VERIFIED). Chandra offers 3D prints, braille posters and audio descriptions (https://chandra.si.edu/tactile, VERIFIED). NASA Moon Trek exports 3D-print files (NISE Net, VERIFIED).
- Screen-reader data tables and haptics: no astronomy-specific study found (gap).

### (d) Recognized multi-sensory projects
- Arcobaleno (Brazil), Space Apps 2023 Global Connection: sonified 2D and 3D NASA images for blind users (https://science.nasa.gov/directorates/smd/2023-nasa-international-space-apps-challenge-announces-10-global-winners/, Jan 2024, VERIFIED).
- Earth, Wind and Flare (Boston), 2022 Art and Technology: IoT device mapping space-weather data to light and sound (https://legacy.spaceappschallenge.org/blog/2022-global-winners, Jan 2023, VERIFIED).
- Other Art and Technology winners: 2023 Oogway Comics (comic book), 2024 Connected Earth Museum (virtual museum with time series), 2025 Zumorroda-X (mini games). 2025 Most Inspirational: Photonics Odyssey; 2025 Global Connection: Gaia+LEO (https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-announces-2025-international-space-apps-challenge-global-winners/, Dec 2025, VERIFIED). Since 2023, sound-based work has won once out of 3 years in these categories.
- Eclipse Soundscapes (NASA SciAct): co-designed with the National Federation of the Blind, three participation roles, 3,425 apprentices, 3,373 observers, about 390 kits with braille and bump dots, English and Spanish (BAAS, Nov 2025, https://baas.aas.org/pub/2025n6i002, VERIFIED).
- LightSound (IAU OAD): a cheap Arduino device that turns light into sound, 900 made (https://astro4dev.org/the-lightsound-project-accessibility-for-the-blind/, VERIFIED).
- Webb sonifications, made with blind consultant Christine Malec (https://science.nasa.gov/mission/webb/sonifications, VERIFIED). The NASA+ documentary "Listen to the Universe" (blindnewworld, Apr 2024, VERIFIED).
- Zooniverse: neurodiversity working group (2025-26) with 91 recommended features (https://blog.zooniverse.org/2025/06/18/neurodiversity-call-2025, https://theoryandpractice.citizenscienceassociation.org/en/articles/10.5334/cstp.1004, VERIFIED). I found no Zooniverse blind-volunteer study (gap).

### (e) Global reach notes
- Space Apps 2025: 114,094 registrants, 18,860 teams, 167 countries (https://spaceappschallenge.org/about/results-and-metrics, VERIFIED).
- Mobile is 84% of internet connections and the main way people get online in low- and middle-income countries. 3.1B people are covered but offline, and a cheap phone costs 44% of monthly income for the poorest 20% in these countries (GSMA, Sep 2025 and Sep 2026, https://www.gsma.com/newsroom/press-release/gsma-warns-of-emerging-global-ai-divide-as-three-billion-people-remain-offline-and-smartphone-component-costs-soar, VERIFIED). India, Nigeria, Pakistan and Egypt have large usage gaps (VERIFIED).
- Eclipse Soundscapes lessons: printable or offline instructions for no-signal areas, plain-language text and multi-format content (BAAS 2024, VERIFIED). Audio files are small compared with image stacks (general point, UNVERIFIED).

### (f) What this means for choosing a project
- Evidence favours sound as a second channel next to visuals (synced cursor) or for strong signals, not as a standalone detector of faint objects.
- Claims should be scoped carefully: the 3,184-person result is self-reported learning, and detection studies show limits at low SNR.
- Webb's WASP-96 b and STRAUSS spectral audification show that spectra can be sonified. Sound for a moving object across epochs looks unexplored in published work.
- Rival teams already cover the WCAG flicker cap, so it is baseline hygiene, not a point of difference.
- Recognized accessibility projects co-designed with blind users (NFB, Malec). Judges may weigh named user involvement more than features alone.

### (g) Gaps
- Not found: any study of asteroid or moving-object detection by ear in image sequences; any SPHEREx sonification.
- Not checked: kilonova sonification, Zooniverse screen-reader support, haptic astronomy studies, the Sonification World Chart.
- Not found: the Space Apps 2026 winners (probably not announced yet) and country-level participant counts.
- The AJ 2024 and RASTI 2023 author lists were not recorded.


---


# Appendix: all 114 rival teams with project text (from agent 13)

## All 114 Planet X teams with project text (auto-extracted from Space Apps API, Nov 14 2026)

Tags are keyword hits, approximate.

| Team | Project and first sentence [keyword tags] | Link | Verified |
| --- | --- | --- | --- |
| 1401 | planetXplorer: planetXplorer is a web tool for exploring how the sky changes over time using SPHEREx data. [timeline, movers, citizen] | https://www.spaceappschallenge.org/2026/find-a-team/1401/?tab=project ; https://planet-x-plorer.vercel.app/ | VERIFIED (API text) submitted |
| 1_tesseract | Project 1_tesseract: SPHEREx Cosmic Detective is an interactive astronomical data exploration and visualization platform developed for the NA [timeline, diff, stack, Gaia, WISE, validation, Aladin/HiPS] | https://www.spaceappschallenge.org/2026/find-a-team/1_tesseract/?tab=project ; https://spherex-cosmic-detective.onrender.com/ | VERIFIED (API text) submitted |
| 24voltt | Cosmic-commons: COSMIC COMMONS is a web‑based astronomical exploration platform that combines a 3‑D sky atlas, a research lab, a spectra [blink, timeline, stack, bands, movers, flags, citizen, anomaly] | https://www.spaceappschallenge.org/2026/find-a-team/24voltt/?tab=project ; https://cosmic-work.vercel.app/explore | VERIFIED (API text) submitted |
| 8 BIT | SPHEREx PrismBlink OS - Interactive Infrared Discovery Engine: SPHEREx PrismBlink OS is a cloud-native, GPU-accelerated web platform that transforms complex SPHEREx infrared survey da [blink, diff, stack, bands, movers, Gaia, WISE, flags] | https://www.spaceappschallenge.org/2026/find-a-team/dhi/?tab=project | VERIFIED (API text) draft |
| Adex | Exoplanet Lab: SpectraTerra Protocol is an interactive web-based platform that transforms astronomical data from NASA’s SPHEREx mission [AI/ML, Aladin/HiPS] | https://www.spaceappschallenge.org/2026/find-a-team/adex/?tab=project | VERIFIED (API text) draft |
| AEC | SkyShift: Blink the Infrared Sky, Measure What Moves: In 1930, Pluto was found by blinking two photographs of the sky. [blink, timeline, stack, bands, movers, AI/ML, Gaia, WISE] | https://www.spaceappschallenge.org/2026/find-a-team/aec/?tab=project ; https://skyshift-seven.vercel.app | VERIFIED (API text) submitted |
| A-JINX | Chrono & Spatial - SPHEREx Sky Change Explorer: Chrono & Spatial is an interactive astronomical platform that transforms real NASA SPHEREx infrared observations into a  [blink, timeline, diff, bands, movers, JPL, citizen, anomaly] | https://www.spaceappschallenge.org/2026/find-a-team/a-jinx/?tab=project ; https://github.com/ProgrammerJibon/NasaAppChallenge2026ChronoSpatial | VERIFIED (API text) submitted |
| Ak researcher | Finding cosmic needle in space: It's represent a scalable, robust and mathematically valid solution for mining all sky infrared survey by transforming t [movers, AI/ML, anomaly] | https://www.spaceappschallenge.org/2026/find-a-team/ak-researcher/?tab=project ; https://drive.google.com/file/d/12hZEsqSDsHyZTGPnjOr3lwinhuHOk0o3/view?usp=drivesdk | VERIFIED (API text) submitted |
| Aliens are Real | Project Alines are Real: game about aliens [game] | https://www.spaceappschallenge.org/2026/find-a-team/alines-are-real/?tab=project ; https://paider.itch.io/aliens-are-real?zarsrc=30&utm_source=zalo&utm_medium=zalo&utm_campaign=zalo | VERIFIED (API text) submitted |
| Altivon Builders | SPHEREx Planet X: SPHEREx Planet X is an astronomical data analysis platform that transforms real NASA SPHEREx infrared observations into  [bands, AI/ML, WISE, flags, multi-lang, chatbot, citizen] | https://www.spaceappschallenge.org/2026/find-a-team/altivon-builders/?tab=project ; https://spherex-planet-x-1.onrender.com/ | VERIFIED (API text) draft |
| Anvild | Skyblink: We built SkyBlink: a high-performance, zero-install, open-source web application and astronomical data pipeline engineer [blink, diff, bands, citizen, anomaly] | https://www.spaceappschallenge.org/2026/find-a-team/anvild/?tab=project ; https://anvild-nasa-space-apps-production.up.railway.app | VERIFIED (API text) submitted |
| archive 07 | SPHEREx Cosmic Explorer: We built an interactive web platform featuring a cinematic flyover of the 2025 SPHEREx all-sky map, dynamic wavelength c [bands, JPL, multi-lang, story] | https://www.spaceappschallenge.org/2026/find-a-team/archive-07/?tab=project ; https://nasa-ct4m.onrender.com/ | VERIFIED (API text) submitted |
| ASTERIA - Watch The Sky Move | ASTERIA: Astronomical SPHEREx Time-series Extraction & Rapid Image Analysis: ASTERIA is an interactive astronomical dashboard designed to make NASA’s SPHEREx all-sky survey data accessible, compara [timeline, bands, movers, AI/ML, Gaia, flags, multi-lang, chatbot] | https://www.spaceappschallenge.org/2026/find-a-team/quantal-universe/?tab=project ; https://github.com/Quantal-Universe/ASTERIA | VERIFIED (API text) draft |
| ASTRAVIA | Project SPHERESCAPE: SPHERESCAPE - Beyond What the Eyes Can See is a web-based astronomy exploration project inspired by NASA’s SPHEREx missi [timeline] | https://www.spaceappschallenge.org/2026/find-a-team/astravia/?tab=project ; https://github.com/anandjyotsna1711-cmd/SPHERESCAPE | VERIFIED (API text) submitted |
| Astro Analyst | Project Astro Analyst: An interactive web-based platform has been created for the purposes of conducting temporal analysis on and monitoring an [citizen, anomaly] | https://www.spaceappschallenge.org/2026/find-a-team/astro-analyst2/?tab=project ; https://github.com/priyanshianand44/SPHEREx-Mission-Sky-Change-Explorer | VERIFIED (API text) submitted |
| AstroFreak | Project PlanetHunter: Exploring Changes in the Universe: PlanetHunter is an interactive, public-facing astronomical exploration platform that transforms real NASA SPHEREx observ [timeline, diff, movers, AI/ML, WISE, citizen, validation] | https://www.spaceappschallenge.org/2026/find-a-team/astrofreak/?tab=project ; https://planethunter.streamlit.app/ | VERIFIED (API text) draft |
| BEYOND X | Project BEYOND X: BEYOND X is an interactive discovery platform that transforms real NASA SPHEREx observations into a cinematic and access [movers, AI/ML, multi-lang, story, anomaly, 3D] | https://www.spaceappschallenge.org/2026/find-a-team/beyond-x/?tab=project ; https://drive.google.com/drive/folders/11bwAIq0FX2YmNM0ZeViIe2tw9ma14XFA?usp=sharing | VERIFIED (API text) submitted |
| Bright Sparks | SPHEREx Blink: SPHEREx Blink is an interactive astronomical data visualisation platform designed to help users explore and understand m [blink, stack, movers, Gaia] | https://www.spaceappschallenge.org/2026/find-a-team/bright-spark/?tab=project ; https://louischiew11-sketch.github.io/SPHEREx-Blink/ | VERIFIED (API text) draft |
| Bugs Bunny | Project Bugs Bunny: Planet X and SPHEREx is an innovative, public-facing web tool designed to make astronomical discovery accessible to ever [timeline, stack, bands, movers, WISE, citizen, Aladin/HiPS] | https://www.spaceappschallenge.org/2026/find-a-team/bugs-bunny/?tab=project ; https://docs.google.com/presentation/d/19xo9B8XkIk3G6uPQRl00xUUKDdP4ix_W/edit?usp=sharing&ouid=101549053482464511064&rtpof=true&sd=true | VERIFIED (API text) submitted |
| Chronocosmos | SPHEREx Time Machine: SPHEREx Time Machine is a web tool that lets anyone travel through time in NASA infrared images. [blink, timeline, movers, AI/ML, WISE, flags, chatbot, citizen] | https://www.spaceappschallenge.org/2026/find-a-team/chronocosmos/?tab=project ; https://github.com/hd189b/SPHEREx-Open-Sky-Observatory | VERIFIED (API text) submitted |
| Colaris | Project Colaris: Planet Hunter is a public website that lets anyone see the sky change in real images from NASA's SPHEREx telescope. [blink, timeline, diff, movers, JPL, game] | https://www.spaceappschallenge.org/2026/find-a-team/colaris/?tab=project ; https://slashsly5-rgb.github.io/planet-hunter/ | VERIFIED (API text) submitted |
| Colossus. | OrbitWatch.: OrbitWatch is an accessible, zero-install citizen science web application developed for the NASA Space Apps Challenge to [blink, timeline, diff, movers, AI/ML, JPL, flags, game] | https://www.spaceappschallenge.org/2026/find-a-team/colossus/?tab=project ; https://drive.google.com/drive/folders/1f9fHRvN4-BbCxIXXB5OSXCaWW21p31kk?usp=sharing | VERIFIED (API text) submitted |
| Compass Crew | Project SPHEREx Time Machine: SPHEREx Time Machine is an interactive website where users can view and visualize astronomical discoveries accessible to [movers, anomaly] | https://www.spaceappschallenge.org/2026/find-a-team/compass-crew/?tab=project ; https://spherex-skywatcher.base44.app/ | VERIFIED (API text) submitted |
| coolest physicists | Project coolest physicists: we should write a high level summary of our amazing project here questions to consider: what did we develope? how did we [] | https://www.spaceappschallenge.org/2026/find-a-team/coolest-physicists/?tab=project | VERIFIED (API text) draft |
| CosmicLens | Project Cosmic Lens: Cosmic Lens is an open-source, interactive web platform and scientific pipeline developed to explore multi-epoch NASA SP [blink, diff, bands, movers, Gaia, WISE, JPL, flags] | https://www.spaceappschallenge.org/2026/find-a-team/cosmiclens/?tab=project ; https://github.com/MSH2006/Cosmic-Lens.git | VERIFIED (API text) submitted |
| Cosmo Class | Cosmo Class: COSMO CLASS - Planet X Hunter: Explore 102 SPHEREx bands, blink-compare sky surveys to find a moving dot, filter 12 to 4 [blink, timeline, bands, movers, AI/ML, Gaia, game, chatbot] | https://www.spaceappschallenge.org/2026/find-a-team/cosmo-class/?tab=project ; https://cosmoclass.netlify.app/ | VERIFIED (API text) draft |
| cupcakkemas gang | spherex-blink: We developed a public web tools that help users discover moving object objects in the sky using real NASA SPHEREx infrar [blink, timeline, movers, WISE, citizen] | https://www.spaceappschallenge.org/2026/find-a-team/cupcakkemas-gang/?tab=project | VERIFIED (API text) draft |
| DAPS - Deep Space Archiving and Positioning System | Project DAPS - Deep Space Archiving and Positioning System: DAPS - Deep Space Archival and Positioning System DAPS is a project designed to explore how technology can make space ex [] | https://www.spaceappschallenge.org/2026/find-a-team/daps-deep-space-archiving-and-positioning-system/?tab=project | VERIFIED (API text) draft |
| Darkshadows Group | VIA / SPHEREx - Watch the Sky Change: VIA / SPHEREx is a public-facing explorer for real SPHEREx observations. [movers, AI/ML, flags, anomaly] | https://www.spaceappschallenge.org/2026/find-a-team/darkshadows-group/?tab=project ; https://www.youtube.com/watch?v=0UH2dHS_uZk | VERIFIED (API text) submitted |
| DEFAULT SKIN | Orion: A Physics based accurate 3d stimulation that allows children and researchers to explore the solar system using an intera [game, 3D] | https://www.spaceappschallenge.org/2026/find-a-team/cortisol4life/?tab=project ; https://drive.google.com/drive/folders/1dkY3TlISXN8pd3VZu_eKenkMQqXr1tAb?usp=drive_link | VERIFIED (API text) draft |
| Deneb | SEDNA - Explore the unseen: SEDNA is a public web tool: type a sky position or a name and watch NASA SPHEREx images of that patch change over time. [blink, Gaia, WISE, JPL, citizen] | https://www.spaceappschallenge.org/2026/find-a-team/deneb/?tab=project ; https://www.sednaspace.earth | VERIFIED (API text) draft |
| Dunkle Materie | SPHEREx Spotter: SPHEREx Spotter is a theoretical web app design that helps users find Planet 9 and brown dwarfs. [diff, AI/ML, flags, citizen, Aladin/HiPS] | https://www.spaceappschallenge.org/2026/find-a-team/dunkle-materie/?tab=project ; https://drive.google.com/file/d/1LkiAcF57KkNtZr6Um9M9RAUhdRjAKZcI/view?usp=drivesdk | VERIFIED (API text) submitted |
| Earth Intruders | BlinkSky by Earth Intruders: NASA's SPHEREx telescope photographs the whole sky again and again in 102 colours of infrared light. [blink, diff, stack, bands, movers, Gaia, WISE, JPL] | https://www.spaceappschallenge.org/2026/find-a-team/earth-intruders/?tab=project ; https://skibidimama106-lang.github.io/BlinkSky/ | VERIFIED (API text) submitted |
| ElNasaالحلوه | Cosmic Tracker: Cosmic Tracker is an interactive web platform built for the NASA SPHEREx Challenge to bridge the gap between complex ast [AI/ML, Gaia, WISE, game, story, 3D] | https://www.spaceappschallenge.org/2026/find-a-team/elnasalhlwh/?tab=project ; https://web-production-b5e6374a.up.railway.app/?ra=133&dec=-56&size=0.05 | VERIFIED (API text) submitted |
| eStars | Wikiverse: Wikiverse es una herramienta web de uso público para el análisis del espacio. [] | https://www.spaceappschallenge.org/2026/find-a-team/estars/?tab=project | VERIFIED (API text) draft |
| EVS | Infrapix: Our project is a web-based platform that transforms raw astronomical data from NASA’s SPHEREx mission into visual images [movers] | https://www.spaceappschallenge.org/2026/find-a-team/evs/?tab=project | VERIFIED (API text) draft |
| ExoSky | SPHEREx TimeScope: SPHEREx TimeScope is a web-based tool that helps users explore NASA's SPHEREx infrared observations, view FITS images an [AI/ML, chatbot] | https://www.spaceappschallenge.org/2026/find-a-team/terranex-agriai/?tab=project ; https://github.com/subanaash/spherex-timescope | VERIFIED (API text) submitted |
| FLYING MINNIE | FLYING MINNIE: SPHEREx Sky Change is a free, public web tool for watching the sky evolve in SPHEREx data. [diff, stack, bands, movers, Gaia, WISE, flags] | https://www.spaceappschallenge.org/2026/find-a-team/flying-minnie/?tab=project | VERIFIED (API text) draft |
| Forough | Project ForoughParallaxStack: Dynamic Parallax-Aware Alignment and Multi-Temporal Stacking for SPHEREx Moving Object DetectionShort: SPHEREx maps the entire sky every six months in 102 near-infrared bands, producing an enormous volume of data. [diff, stack, bands, movers, WISE, citizen, anomaly] | https://www.spaceappschallenge.org/2026/find-a-team/forough/?tab=project ; https://github.com/wfrghh-code/ParallaxStack- | VERIFIED (API text) submitted |
| FROM NILE TO STARS | BlinkSphere: NASA’s SPHEREx telescope generates thousands of sky images every six months across 102 infrared wavebands, yet utilizing [blink, timeline, bands, AI/ML, flags, multi-lang, sound, citizen] | https://www.spaceappschallenge.org/2026/find-a-team/spectrum-explorers/?tab=project ; https://blinksphere.vercel.app/ | VERIFIED (API text) submitted |
| General Relativity & cosmology | Project General Relativity & cosmology: Water from ocean and river & nuclear radiated water & sewage water are taken with pipes to a deep hole/ steel chamber. [movers, JPL, sound] | https://www.spaceappschallenge.org/2026/find-a-team/general-relativity-cosmology/?tab=project ; https://drive.google.com/file/d/1xS-5SVswAUJpbfCu1PnyG_V0Ev1js_Zj/view?usp=drivesdk | VERIFIED (API text) submitted |
| GGTron | All stars: We have developed a web application that allows humans to easily observe the hidden patterns in the SphereX mission's ob [] | https://www.spaceappschallenge.org/2026/find-a-team/ggtron/?tab=project | VERIFIED (API text) draft |
| II-MAX | PXS-Solution: # SPHEREx Time-Domain Explorer: Making the Invisible Visible SPHEREx Time-Domain Explorer is an AI-assisted citizen scie [blink, diff, bands, movers, AI/ML, Gaia, WISE, flags] | https://www.spaceappschallenge.org/2026/find-a-team/ii-max/?tab=project ; https://github.com/II-Max/Planet-X-and-SPHEREx | VERIFIED (API text) draft |
| InfraNex | InfraNex's SPHEREx Explorer: A New Perspective on the Unknown: SPHEREx Explorer is an interactive six-page astrophysics web platform developed for the 2026 NASA Space Apps Challenge. [blink, timeline, diff, bands, movers, AI/ML, Gaia, WISE] | https://www.spaceappschallenge.org/2026/find-a-team/infranex/?tab=project | VERIFIED (API text) draft |
| ⁠InfraQ Stargazers | AegisEarth: An interactive sky viewer for NASA’s SPHEREx mission data. Choose sky coordinates and a field of view, then play infrared observations in date order to explore motion and changes in brightness.: AegisEarth, developed by InfraQ Stargazers, is an interactive astronomy platform that makes NASA’s SPHEREx observations  [movers, JPL, citizen] | https://www.spaceappschallenge.org/2026/find-a-team/infraq-stargazers/?tab=project ; https://github.com/Ahiraf/AegisEarth | VERIFIED (API text) submitted |
| Kaizoku sentai gokaiger | COSMIC COMPASS: COSMIC COMPASS is an interactive astronomical exploration platform designed to make SPHEREx infrared observations access [diff, bands] | https://www.spaceappschallenge.org/2026/find-a-team/kaizoku-sentai-gokaiger/?tab=project ; https://drive.google.com/drive/folders/1x4CMzdqLxavMIccmkwaTMPJhE9fqdbKI | VERIFIED (API text) submitted |
| Kanphit o99 | Project Kanphit o99: SPHEREx Sky Time-Lapse: see the sky move. [timeline, diff, bands, movers, Gaia, WISE, flags] | https://www.spaceappschallenge.org/2026/find-a-team/kanphit-o99/?tab=project ; https://statuesque-swan-a0bd30.netlify.app/#wise | VERIFIED (API text) submitted |
| Kayseri Mafyası | ExoPulse: Citizen-Centric Exoplanet & Habitability Analytics Dashboard: The search for extrasolar planets has entered a golden age, with NASA missions like Kepler and TESS generating unprecede [stack, AI/ML, flags, game, citizen, anomaly] | https://www.spaceappschallenge.org/2026/find-a-team/kayseri-mafyasi/?tab=project ; https://voluble-sable-6bfb3b.netlify.app/ | VERIFIED (API text) submitted |
| Kepler-22 | Project Kepler-22: We built SkyBlink, a web tool that helps anyone spot moving objects in the sky, the way astronomers found Pluto How it w [blink, diff, stack, movers, Gaia, WISE, multi-lang, sound] | https://www.spaceappschallenge.org/2026/find-a-team/kepler-22/?tab=project ; https://joamir10.github.io/nasa26/ | VERIFIED (API text) submitted |
| Khan Space | Project Space detectives: Project Space Detectives developed a transparent, six-step scientific classification protocol called "STAR OR PLANET?" t [movers, Gaia, Aladin/HiPS] | https://www.spaceappschallenge.org/2026/find-a-team/spacemonsters/?tab=project ; https://quiet-moonbeam-8bde17.netlify.app/#classifier | VERIFIED (API text) draft |
| Krypton | orbital eye: ORBITAL EYE is an interactive astronomical data exploration platform that transforms SPHEREx space telescope observation [movers, WISE] | https://www.spaceappschallenge.org/2026/find-a-team/krypton3/?tab=project ; https://github.com/saberx45/SphereXNasa.git | VERIFIED (API text) submitted |
| Lone Esdee | SPHEREx Sky Viewer: SPHEREx Sky Viewer is a small web tool for seeing how the sky changes between two weeks of SPHEREx observations. [blink, movers, flags] | https://www.spaceappschallenge.org/2026/find-a-team/lone-esdee/?tab=project ; https://spherex-cutout-jirogsnxg7fvm2gtm6hp48.streamlit.app/ | VERIFIED (API text) submitted |
| MarsBZU | SKYTRACE: SKYTRACE is an interactive web platform that transforms real NASA SPHEREx infrared observations into an engaging, time-b [blink, JPL, story, Aladin/HiPS] | https://www.spaceappschallenge.org/2026/find-a-team/marsbzu/?tab=project ; https://skytrace-puce.vercel.app | VERIFIED (API text) draft |
| Mission Chi Lăng Andromeda-7 | Project Mission Chi Lăng Andromeda-7: We have developed a website that displays images from NASA’s SPHEREx mission, making them easily accessible to everyone. [timeline, bands, Aladin/HiPS] | https://www.spaceappschallenge.org/2026/find-a-team/mission-chi-lang-andromeda-7/?tab=project ; https://mission7.tiiny.site/ | VERIFIED (API text) submitted |
| Nakshatra Chronos | Nakshatra CHRONOS: an observatory that asks what changed in the SPHEREx sky & tries to prove itself wrong: You can’t blink SPHEREx. [blink, timeline, bands, movers, Gaia, JPL, flags, multi-lang] | https://www.spaceappschallenge.org/2026/find-a-team/spherex-chronos/?tab=project ; https://github.com/PRITIDIPADAS/nakshatra-chronus | VERIFIED (API text) submitted |
| nasainmyheart | Project ExoSky: Constellations from Distant Worlds: ExoSky: Constellations from Distant Worlds is an interactive web platform developed for the Imagine an Exoplanet challen [multi-lang, story] | https://www.spaceappschallenge.org/2026/find-a-team/nasainmyheart/?tab=project ; https://canva.link/c57vvsmzalggeqx | VERIFIED (API text) submitted |
| Nasa winner | Project Nasa winner: Our team is called "Nasa Winner." We have developed a website that provides information about stars and tracks the paths [] | https://www.spaceappschallenge.org/2026/find-a-team/nasa-winner/?tab=project ; https://bison-3dtn36.my.canva.site/spherex-timelapse-summarize | VERIFIED (API text) submitted |
| Nebula Nexus | NOVOCHAR: Novochar (নভোচার, "spacefarer") is a full-stack, browser-based astronomy platform built around NASA's SPHEREx mission, o [blink, timeline, stack, bands, movers, 3D] | https://www.spaceappschallenge.org/2026/find-a-team/team-voyager4/?tab=project ; https://github.com/muhammadmuhtasim/novochar | VERIFIED (API text) submitted |
| Neutr*n | Waveshift:  [] | https://www.spaceappschallenge.org/2026/find-a-team/1-world3/?tab=project ; https://waveshift-4billion.vercel.app | VERIFIED (API text) draft |
| New York Style Cellphone | Wanderer: Wanderer is a web tool that measures moving objects in NASA's SPHEREx all-sky survey. [diff, movers, Gaia, JPL, flags, citizen, anomaly, Aladin/HiPS] | https://www.spaceappschallenge.org/2026/find-a-team/new-york-style-cellphone/?tab=project ; https://spherex-wanderer.vercel.app | VERIFIED (API text) draft |
| Nexora_A | Project Nexora_A: SpectraShift is a space-data exploration platform designed to help researchers, students, and curious individuals invest [bands, Gaia, anomaly] | https://www.spaceappschallenge.org/2026/find-a-team/nexora_a/?tab=project ; https://github.com/rafincs3023-cyber/SpectraShift | VERIFIED (API text) submitted |
| Nexus Carazo | Project Nexus Carazo: SPHERE is an interactive web-based platform inspired by NASA’s Planet X and SPHEREx challenge. [bands] | https://www.spaceappschallenge.org/2026/find-a-team/nexus-carazo/?tab=project ; https://nexus-carazo.vercel.app/ | VERIFIED (API text) submitted |
| no one | spherex-skyflow: Space exploration yields vast amounts of telemetry, scientific data, and historical milestones, yet translating these co [timeline, stack, movers, multi-lang, story, 3D, Aladin/HiPS] | https://www.spaceappschallenge.org/2026/find-a-team/no-one/?tab=project ; https://adorable-unicorn-53b1ec.netlify.app | VERIFIED (API text) submitted |
| Nova Rover Systems | Project Nova Rover Systems: **Planet X and SPHEREx** is an interactive web platform designed to make NASA’s massive infrared space archives accessib [timeline, diff, bands, movers, AI/ML, WISE, flags, story] | https://www.spaceappschallenge.org/2026/find-a-team/nova-rover-systems/?tab=project ; https://nova-rover-sys.web.app/ | VERIFIED (API text) submitted |
| Nova stella | Project Nova stella: Stella Astro Viewer is a browser-based infrared astronomical workbench built for the NASA Space Apps Challenge to make r [blink, timeline, diff, bands, movers, Gaia, WISE, flags] | https://www.spaceappschallenge.org/2026/find-a-team/nova-stella/?tab=project ; https://stella-eta-sepia.vercel.app | VERIFIED (API text) submitted |
| NovaTerra | Project NovaTerra: The NOVATERRA team's project aims to transform the vast and complex astronomical data collected by NASA's SPHEREx missio [blink, bands, movers, AI/ML, Gaia, WISE, JPL, citizen] | https://www.spaceappschallenge.org/2026/find-a-team/novaterra1/?tab=project ; https://mackshttrick.site/%E2%9F%A6%20N%C3%98V%CE%9BT%CE%9ERR%CE%9B%20%E2%AB%B7%20SPH%CE%9ER%CE%9EX%20%E2%AB%B8%20%E2%9F%A7/index.php#tab%3Dearth | VERIFIED (API text) draft |
| Nuetral Nebulas | Project Nuetral Nebulas: Beyond Known: Exploring the Search for Planet X Beyond Known is an interactive astronomy website that explores one of th [bands] | https://www.spaceappschallenge.org/2026/find-a-team/nuetral-nebulas/?tab=project ; https://speck-stream-14199517.figma.site/ | VERIFIED (API text) draft |
| Null Point | SPHEREx sky time machine: SPHEREx Sky Time Machine is a free website that turns NASA’s SPHEREx infrared survey into short videos of the sky. [bands, movers, AI/ML, Gaia, WISE, flags, chatbot, citizen] | https://www.spaceappschallenge.org/2026/find-a-team/null-point/?tab=project ; https://github.com/Ahmed-Wael-01/SPHEREx-sky-time-machine | VERIFIED (API text) submitted |
| NXT CO. | SPHEREx Sky Shift Visualizer: SPHEREx Sky Shift Visualizer is a web tool that shows how objects in the sky appear to move between NASA SPHEREx survey  [blink, timeline, bands, movers, WISE, citizen] | https://www.spaceappschallenge.org/2026/find-a-team/nxt-co/?tab=project ; https://spherexskyshiftvisualizer.netlify.app/ | VERIFIED (API text) submitted |
| Old Terminal | Old Terminal: # HELIOS-X: AI-Powered Astronomical Exploration & Scientific Investigation The universe is full of unanswered questions. [movers, AI/ML, Gaia, WISE, chatbot, citizen] | https://www.spaceappschallenge.org/2026/find-a-team/old-terminal/?tab=project ; https://github.com/Musfiq-003/HELIOS-X.git | VERIFIED (API text) submitted |
| OORT ODESSEY | BEYOND 30 AU:OORT ODESSEY: BEYOND 30 AU:OORT ODESSEY is an interactive space-exploration concept that combines NASA’s SPHEREx infrared sky observat [diff, bands, AI/ML, JPL, flags, citizen, anomaly] | https://www.spaceappschallenge.org/2026/find-a-team/beyond-30-auoort-odessey/?tab=project ; https://drive.google.com/file/d/1bfHVzDl7XQIGoXYmnK6UOErMCyjSnJx_/view?usp=drivesdk | VERIFIED (API text) submitted |
| Phantom Signal | SkyBlink: SkyBlink turns raw SPHEREx infrared sky data into a telescope-style web tool that anyone can use. [blink, timeline, movers, AI/ML, chatbot] | https://www.spaceappschallenge.org/2026/find-a-team/phantom-signal/?tab=project ; https://skyblink.vercel.app/ | VERIFIED (API text) submitted |
| PinkiePie from the Ozz | Project PinkiePie from the Ozz: We developed an open-source, web-based platform that turns multi-epoch FITS sky images from NASA's SPHEREx mission into  [blink, timeline, diff, bands, movers, WISE, flags, citizen] | https://www.spaceappschallenge.org/2026/find-a-team/pinkiepie-from-the-ozz/?tab=project ; https://github.com/duongvukhang/PinkiePieFromTheOzz-Nasa-challenge- | VERIFIED (API text) submitted |
| Planet hunter | Project Planet hunter: To solve the challenge of spotting moving objects among billions of static stars in massive sky surveys like SPHEREx and [movers, AI/ML, flags, citizen, validation, anomaly] | https://www.spaceappschallenge.org/2026/find-a-team/planet-hunter5/?tab=project ; https://youtube.com/shorts/Sxk9_T84QN8?si=ottq0ei46DUArzLB | VERIFIED (API text) submitted |
| Pleiades7 | Cosmic Detective: Cosmic Detective transforms complex astronomical datasets into an accessible, story-driven multiplayer citizen-science e [blink, diff, bands, WISE, game, story, sound, citizen] | https://www.spaceappschallenge.org/2026/find-a-team/pleadies/?tab=project ; https://github.com/YeadMuhammad/Cosmic-Detective | VERIFIED (API text) submitted |
| Prime Autobots | Prime Sky: Our application is an astronomy tool that provides users with information on how they can study and observe objects in t [timeline, AI/ML, chatbot] | https://www.spaceappschallenge.org/2026/find-a-team/prime-autobots/?tab=project | VERIFIED (API text) draft |
| Quantum SphereX | Project COSMOSX by Quantum sphereX: Cosmos 1 is a public-facing astronomy explorer for the NASA Space Apps Challenge, built by Adharv Kodali and Reyansh Van [blink, timeline, movers, AI/ML, WISE, story, 3D] | https://www.spaceappschallenge.org/2026/find-a-team/quantum-spherex/?tab=project ; https://quantum-spherex-sky.eldergodchaosharbrin.chatgpt.site/ | VERIFIED (API text) submitted |
| RAKS_THE SEAWEED BRAINS | Project RAKS_THE SEAWEED BRAINS: Our project develops a way for the public to access Planet X and SPHEREx probe data easily through our own libraries. [] | https://www.spaceappschallenge.org/2026/find-a-team/raks_the-seaweed-brains/?tab=project ; https://github.com/starlordtomatoes/spherex-tools | VERIFIED (API text) draft |
| RAM_Shortman | Project SPHEREx Temporal Subtraction & Anomaly Engine: The SPHEREx Temporal Subtraction & Anomaly Engine is a web tool that helps astronomers and curious people find moving or [blink, diff, stack, movers, anomaly] | https://www.spaceappschallenge.org/2026/find-a-team/ram_shortman/?tab=project ; https://github.com/faiyazkon/spherex_challenge.git | VERIFIED (API text) submitted |
| Red-Shift | Trace-X: Project Red-Shift is SPHEREx Explorer, a web platform that makes SPHEREx infrared spectral data accessible to researcher [bands, AI/ML, Gaia, WISE, flags, chatbot] | https://www.spaceappschallenge.org/2026/find-a-team/red-shift/?tab=project ; https://github.com/Ashhajj0/SPHEREX-And-PLANETX | VERIFIED (API text) submitted |
| RT's | Space exploration: Project Title: Advancing Space Exploration: Technologies, Discoveries, and Societal Impact Prepared by: Team RT's ​Execu [] | https://www.spaceappschallenge.org/2026/find-a-team/rts3/?tab=project ; https://youtu.be/e79KFkrtCV0?si=JYJUYsVZyO-gZaoX | VERIFIED (API text) submitted |
| Sarawak Astronauts | StarXplorer: We are developing a public web tool that turns NASA SPHEREx data into sky time-lapses for everyone. [blink, timeline, diff, bands, movers, AI/ML, WISE, game] | https://www.spaceappschallenge.org/2026/find-a-team/sarawak-astronauts/?tab=project ; https://google.com | VERIFIED (API text) submitted |
| SATEv2 | Project SATEv2: space [] | https://www.spaceappschallenge.org/2026/find-a-team/satev2/?tab=project ; https://www.spaceappschallenge.org/ | VERIFIED (API text) submitted |
| Schwarzschildren | Orbit Lens: ORBIT-LENS is an interactive, multi-epoch infrared sky explorer and time-series blink comparator engineered to uncover h [blink, timeline, diff, bands, movers, Gaia, WISE, flags] | https://www.spaceappschallenge.org/2026/find-a-team/schwarzschildren/?tab=project ; https://nsac-2026.vercel.app/ | VERIFIED (API text) submitted |
| Selenites | Ashesha: Follow a Comet Through SPHEREx: No one will ever visit another star. [bands, sound] | https://www.spaceappschallenge.org/2026/find-a-team/selenites/?tab=project | VERIFIED (API text) draft |
| Silent Vector | Blinkfield: Blinkfield - Project Summary Blinkfield is a public web tool built for the 2026 NASA Space Apps Challenge. [blink, diff, stack, bands, movers, Gaia, WISE, flags] | https://www.spaceappschallenge.org/2026/find-a-team/silent-vector/?tab=project ; https://github.com/CyberwarriorAtt/Blinkfield | VERIFIED (API text) submitted |
| Skill-Issue | Project Skill-Issue: **SPHEREx Blink** Every six months, SPHEREx photographs the entire sky in infrared. [blink, diff, stack, bands, movers, Gaia, WISE, flags] | https://www.spaceappschallenge.org/2026/find-a-team/skill-issue2/?tab=project ; https://spherexblink.vercel.app | VERIFIED (API text) submitted |
| SkyShift Cyprus | SkyShift: A Time Machine for the SPHEREx Sky: SkyShift is a free web app that turns NASA's SPHEREx all-sky survey into a time machine anyone can use. [blink, diff, stack, bands, movers, Gaia, WISE, JPL] | https://www.spaceappschallenge.org/2026/find-a-team/skyshift-cyprus/?tab=project ; https://samuelakosaonyejekwe.github.io/skyshift-spherex/ | VERIFIED (API text) submitted |
| SkyShift Murcia | SkyShift: SkyShift is a free public web tool that lets anyone explore NASA's SPHEREx infrared sky and see how it changes over time [timeline, stack, movers, WISE, story, citizen] | https://www.spaceappschallenge.org/2026/find-a-team/skyshift-murcia/?tab=project ; https://skyshift-roan.vercel.app | VERIFIED (API text) draft |
| Space Roger | FIMU - FITS Intelligence & Mapping Utility: FIMU (FITS Intelligence & Mapping Utility) is an AI-assisted astronomical intelligence platform designed to simplify the [bands, AI/ML, anomaly] | https://www.spaceappschallenge.org/2026/find-a-team/space-roger/?tab=project ; https://fimuuu.streamlit.app/ | VERIFIED (API text) submitted |
| Space_VI | NODIXHI: NODIXHI is an interactive web tool for exploring the sky and comparing infrared observations. [blink, movers] | https://www.spaceappschallenge.org/2026/find-a-team/space_vi/?tab=project | VERIFIED (API text) draft |
| Specula | Specula: Specula is a full pipeline, from NASA's archive to an interactive website, that hunts for moving objects in real photos  [movers, AI/ML, JPL, chatbot, 3D] | https://www.spaceappschallenge.org/2026/find-a-team/specula/?tab=project ; https://specula-nasa.vercel.app | VERIFIED (API text) submitted |
| SphereX | SPHEREx: Sky Detective: SPHEREx: Sky Detective is a free, story-driven web game that answers the challenge's call for a public tool that makes i [blink, bands, movers, game, multi-lang, chatbot, story, sound] | https://www.spaceappschallenge.org/2026/find-a-team/spherex/?tab=project ; https://cemyurtlak.github.io/spherex-gokyuzu-dedektifi/ | VERIFIED (API text) draft |
| StellarCipher | StellarCipher: StellarCipher is an interactive web-based tool developed for the NASA Space Apps Challenge 2026, addressing the Planet X [] | https://www.spaceappschallenge.org/2026/find-a-team/stellarcipher/?tab=project ; https://stellarcipher-9z2dgmawtwfnssevncnxvm.streamlit.app/ | VERIFIED (API text) submitted |
| StellarLuna | NovaScope: Navigate the Stars, Discover the Universe: NovaScope is an interactive web-based stars navigations based planetarium viewing concept that targeting students, educa [timeline] | https://www.spaceappschallenge.org/2026/find-a-team/stellarluna/?tab=project ; https://www.spaceappschallenge.org/ | VERIFIED (API text) submitted |
| Team KingKortobboBimur | Spy the Sky: We are developing an interactive sky exploration platform that uses NASA's SPHEREx data to help users investigate the ch [timeline, movers, anomaly, Aladin/HiPS] | https://www.spaceappschallenge.org/2026/find-a-team/team-kingkortobbobimur/?tab=project ; https://github.com/chowdhury-shovon/SPHEREx-Sky-Explorer | VERIFIED (API text) submitted |
| Team Oblivion | Project Team Oblivion: **SPHEREx Explorer** is a free, bilingual web application that makes NASA's SPHEREx infrared sky survey accessible to ev [blink, timeline, movers, AI/ML, WISE, JPL, game, multi-lang] | https://www.spaceappschallenge.org/2026/find-a-team/team-oblivion/?tab=project ; https://github.com/minhaz-42/spherex-explorer | VERIFIED (API text) submitted |
| Team OP | AstroBlink: AstroBlink is a free, no-login web tool that plays NASA SPHEREx infrared sky images as a short film. [blink, diff, stack, bands, movers, WISE, flags, multi-lang] | https://www.spaceappschallenge.org/2026/find-a-team/team-op/?tab=project ; https://astroblink.fatinshadab123.workers.dev | VERIFIED (API text) submitted |
| Team Sparks | Cosmic Hunt: Cosmic Hunt is a free, browser-based 3D space exploration game designed to make real infrared astronomy accessible and f [bands, AI/ML, game, multi-lang, chatbot, sound, 3D] | https://www.spaceappschallenge.org/2026/find-a-team/team-sparks1/?tab=project ; https://github.com/topu-10j/Cosmic-Hunt | VERIFIED (API text) submitted |
| The Motion Mappers | Project The Motion Mappers: The Motion Mappers is an interactive astronomy project designed to help users explore SPHEREx observations and investiga [movers] | https://www.spaceappschallenge.org/2026/find-a-team/the-motion-mappers/?tab=project ; https://spherex.myaddr.dev/ | VERIFIED (API text) submitted |
| The Summit Society | Project The Summit Society: Luma Sphere is a web app for the NASA Space Apps Challenge 2026 challenge “Planet X and SPHEREx.” It lets you stand insi [blink, timeline, bands, movers] | https://www.spaceappschallenge.org/2026/find-a-team/the-summit-society/?tab=project ; https://github.com/3ch0less/spaceappsproject.git | VERIFIED (API text) submitted |
| Three Heads of AI | Skyshift: See things move in the sky. [blink, diff, movers, AI/ML, Gaia, JPL, flags, chatbot] | https://www.spaceappschallenge.org/2026/find-a-team/root23/?tab=project ; https://skyshift-weld.vercel.app | VERIFIED (API text) draft |
| T.Nasa | Project T.Nasa: T-AstraOps is a full-stack mission control and telemetry platform designed to bridge the gap between raw aerospace datas [stack] | https://www.spaceappschallenge.org/2026/find-a-team/tnasa/?tab=project | VERIFIED (API text) draft |
| to the end of the world | Project to the end of the world: Skytime is a web tool for looking at the same patch of sky in several SPHEREx infrared images. [blink, timeline, diff, movers, AI/ML, WISE, flags] | https://www.spaceappschallenge.org/2026/find-a-team/to-the-end-of-the-world/?tab=project ; https://skytime-vercel-flat.vercel.app/ | VERIFIED (API text) submitted |
| Türksat 1A | Beyond The Known Universe: Drawing inspiration from current and compelling space research, such as NASA's SPHEREx mission and the search for "Plane [] | https://www.spaceappschallenge.org/2026/find-a-team/turksat-1a/?tab=project ; https://metalkafadiyojen.github.io/BeyondTheKnownUniverse/ | VERIFIED (API text) submitted |
| Unstoppable space warriors | Project Unstoppable space warriors: Project Summary SPHEREx Sky Explorer is an interactive web-based platform inspired by NASA's SPHEREx mission. [stack, AI/ML, Gaia, JPL, chatbot, story] | https://www.spaceappschallenge.org/2026/find-a-team/unstoppable-space-warriors/?tab=project ; https://nasaspherexweb.my.canva.site/ | VERIFIED (API text) submitted |
| Vanilla Sphere | Vanilla Sphere: Vanilla Sphere turns NASA's SPHEREx all-sky survey into a blink comparator that runs in any browser. [blink, timeline, diff, movers, AI/ML, Gaia, WISE, JPL] | https://www.spaceappschallenge.org/2026/find-a-team/vanilla-sphere/?tab=project ; https://vanillasphere.com | VERIFIED (API text) submitted |
| vortex ai nxt gen | Project vortex ai nxt gen: SPHEREx Analysis of 3I/ATLAS Our project uses NASA's SPHEREx mission data to study the interstellar object 3I/ATLAS. [AI/ML] | https://www.spaceappschallenge.org/2026/find-a-team/vortex-ai-nxt-gen/?tab=project ; https://25a31a04g7.github.io/spherex-project/?utm_source=chatgpt.com#calibration | VERIFIED (API text) submitted |
| Wanderer | Wanderer: See the SPHEREx Sky Move: Since 2025, NASA's SPHEREx mission has mapped the entire sky every six months in 102 colours of near-infrared light. [blink, timeline, diff, bands, movers, JPL, flags, citizen] | https://www.spaceappschallenge.org/2026/find-a-team/wanderer/?tab=project ; https://wanderer.stellar-trace.tech | VERIFIED (API text) submitted |
| Whispers of Motion | Whispers of Motion: Watching the Infrared Sky Move with SPHEREx: NASA's SPHEREx telescope maps the entire sky in 102 infrared bands, imaging over a billion stars. [blink, diff, stack, bands, movers, AI/ML, JPL, flags] | https://www.spaceappschallenge.org/2026/find-a-team/whispers-of-motion/?tab=project ; https://github.com/SSJemey/whispers-of-motion | VERIFIED (API text) submitted |
| X | SkyShift-X: The sky looks still-until you press play. [blink, timeline, diff, stack, WISE, flags, multi-lang, story] | https://www.spaceappschallenge.org/2026/find-a-team/x255/?tab=project ; https://skyshift-x.vercel.app/#%2F | VERIFIED (API text) submitted |
| XeNovate | XeNovate: Planet X - Exploring the Changing Universe Planet X is an interactive, public-facing web platform designed to make NASA' [movers] | https://www.spaceappschallenge.org/2026/find-a-team/xenovate/?tab=project ; https://joyful-rabanadas-c947b2.netlify.app | VERIFIED (API text) submitted |
| YLMA Space | SphereX Explorer: Our project revolves around the Planet X and SphereX challenge, where we have built a website using SphereX to show a ma [blink, chatbot, Aladin/HiPS] | https://www.spaceappschallenge.org/2026/find-a-team/ylma-spacetm/?tab=project | VERIFIED (API text) draft |
| Zgrench | Project SphereX Explorer: I developed SPHEREx Explorer as a solo participant to make NASA’s infrared sky observations easier to explore. [timeline, 3D] | https://www.spaceappschallenge.org/2026/find-a-team/zgrench/?tab=project | VERIFIED (API text) draft |