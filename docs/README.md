# Project docs: start here

Everything we've planned for the NASA Space Apps 2026 build (Planet X / SPHEREx track) is in this folder, in reading order. **Nothing here is built yet.** These are plans, reviewed on 2026-11-15: both are cleared to build (CEO + eng review), with two small open follow-ups on the base plan (see Status).

**What we're building**
1. **SPHEREx Sky Time Machine (base, 2D).** A static website where you pick a sky target and watch SPHEREx images of it play like a flipbook.
2. **3D Object Explorer (add-on).** Object pages with a rotatable 3D model, the SPHEREx history of the object, its predicted path, and a "what it's made of" panel.

The 3D add-on is the **first thing cut** if time runs short.

## Read in this order

| # | File | What it is | Read it if… | Length |
|---|------|------------|-------------|--------|
| 1 | [plans/01-base-2d-sky-time-machine.md](plans/01-base-2d-sky-time-machine.md) | **Base plan.** Problem, approach, hour-by-hour plan for 2 people, build phases, UI spec, data contract, plus the full CEO / design / DX / eng review record | Always. Read the top part, through "NOT in scope". The review record below it is reference. | long (~1,000 lines) |
| 2 | [plans/02-base-2d-scope-summary.md](plans/02-base-2d-scope-summary.md) | One-page scope decisions for the base plan: what was accepted and what was deferred | You want the base scope at a glance | 1 page |
| 3 | [plans/03-base-2d-qa-test-plan.md](plans/03-base-2d-qa-test-plan.md) | QA checklist for the 2D site: pages, interactions, edge cases | You test the 2D site | 1 page |
| 4 | [plans/04-3d-object-explorer.md](plans/04-3d-object-explorer.md) | **3D add-on plan.** Architecture, data contract (`object.json`), error handling, design spec (§13), build schedule (§14), tasks T1-T17 (§15), plus the CEO, design and eng review records and decision ledger | You work on 3D, or need to know what it changes | long (~1,000 lines) |
| 5 | [plans/05-3d-scope-summary.md](plans/05-3d-scope-summary.md) | One-page scope decisions for the 3D add-on | You want the 3D scope at a glance | 1 page |
| 6 | [plans/06-3d-qa-test-plan.md](plans/06-3d-qa-test-plan.md) | QA checklist for the 3D object pages | You test the 3D pages | 1 page |
| – | [../TODOS.md](../TODOS.md) | Everything deliberately postponed, with reasons (live mode, 5 base-plan features, 2 base-plan review follow-ups) | Before proposing "new" features | short |

**Research and data background** (in the repo root, not moved, because code references them):
- [../Planet_X_SPHEREx_Resources_Report.md](../Planet_X_SPHEREx_Resources_Report.md): every data source tested live (IRSA SIA2, cutouts, S3, MOST, Gaia), what works, CORS limits, and the required NASA acknowledgement text.
- [../SpaceX-SPHEREx-research-pack.md](../SpaceX-SPHEREx-research-pack.md): the broader research pack (large).
- Existing code: `spherex_try.py` (search, cutouts, north-up stacking, motion stack) and `fake_mover_filter.py` (real-vs-artifact mover filter).

## Status

| Plan | CEO review | Design review | Eng review | DX review |
|---|---|---|---|---|
| Base 2D | cleared | **issues open** (2/10 → 5/10: no shared design tokens) | cleared | **issues open** (4.5/10 → 7/10: setup time not measured) |
| 3D add-on | cleared | cleared (2/10 → 8/10) | cleared | not run |

Both base-plan open items are follow-ups, not blockers. They're listed in [../TODOS.md](../TODOS.md). The 3D plan's shared `web/css/tokens.css` (04 §13.1) covers most of the base design gap, because both pages use it.

Every review decision is recorded in the plans with the question asked and the answer given. Look for the "Decision" tables, the "Decision ledger", and the "GSTACK REVIEW REPORT" at the end of each long plan.

## Don't miss these

1. **3D shapes are AI-generated, never from SPHEREx.** SPHEREx pixels (6.15″) are far too big to see any asteroid's shape. Every 3D model carries the "AI impression · real size" chip. Everything else on the page is real data and labelled so. (04 §1)
2. **Hours 0-4 matter for 3D.** The data person writes and starts three offline scripts early: `export_objects.py facts`, `track_export.py` and `gen_mesh.py`. They need IRSA to be up and need a **fal.ai account with `FAL_KEY`**, which one of us has to create. (04 §14)
3. **Timebox is tight.** The 3D tasks total about 19 human-hours (about 3.5 h of Claude Code time), so they fit only if Claude Code writes most of the code. The cut order is in 04 §14.
4. **The S/N numbers quoted in the demo are protected by a test.** WISE 0855: 13.5 stacked, 14.0 motion-following. `publish.sh` refuses to publish if that test didn't run, which needs the local `spherex_cache/` (1.6 GB, not in git). (04, decision R4)
5. **The two plans disagree on test tooling.** The base plan (01) specifies `pytest` and a `node` test (`web/test/tan.test.mjs`), but neither is installed. The 3D plan (04) uses stdlib `unittest` and an in-browser test page. Pick one approach before writing tests.
6. **No visual mockups exist yet.** The designer tool needs `GEMINI_API_KEY` or `OPENAI_API_KEY`. The design is specified in text (01 "UI spec", 04 §13).
7. **Housekeeping:** `main` has a stray `.DS_Store` commit (0aa203e). Remove it and add `.DS_Store` to `.gitignore`.

## Where these files came from

Files 01, 02, 03, 05 and 06 were copied on 2026-11-15 from Dovlet's local review-tool folder (`~/.gstack/projects/d-gurbano-nasa-space-x/`), which isn't in git. **The copies in this folder are now the shared version: edit them here.** If someone reruns a review tool locally, copy its updated output back into `docs/plans/` so we don't end up with two versions.
