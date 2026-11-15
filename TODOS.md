# TODOS

## Live any-coordinate mode (deferred from the 24h build)
- **What:** FastAPI `/api/field?ra&dec` that runs the export pipeline for any sky position and writes the same manifest/object.json files the static site reads.
- **Why:** Lets anyone explore any patch of sky, not just the featured targets.
- **Pros:** Biggest reach jump; the file contracts already support it.
- **Cons:** Needs a hosted backend, IRSA reliability handling, rate limits.
- **Context:** Deferred by /plan-ceo-review on 2026-11-15 (decision D8) to free 4-5 hours for the 3D Object Explorer (`docs/plans/04-3d-object-explorer.md`). Full spec is Phase 4 of the base design doc (`docs/plans/01-base-2d-sky-time-machine.md`).
- **Effort:** human L / CC+gstack M
- **Priority:** P2
- **Depends on:** base 2D site shipped; `export_web.py` importable.

## Deferred from the base 2D plan (Sky Time Machine)
Approved deferrals from the base plan's review (`docs/plans/01-base-2d-sky-time-machine.md`, "NOT in scope", 2026-11-15). The plan said "deferred to TODOS.md", but no TODOS.md existed then, so they are recorded here.

### Spot the Mover (citizen-science voting game)
- **What:** visitors vote on pre-screened mover candidates.
- **Why deferred:** needs accounts and storage; does not fit the 24h budget.
- **Priority:** P3

### On-click spectrum from the HiPS cube
- **What:** click any sky position in the player to see its spectrum from the SPHEREx all-sky cube.
- **Why deferred:** 24h budget. The 3D plan's per-object spectrum (`docs/plans/04-3d-object-explorer.md` §13.6) covers featured objects only.
- **Priority:** P3

### Gaia / CatWISE catalogue overlay
- **What:** draw catalogue stars, moved to each frame's date, over the frames.
- **Why deferred:** CDS and IRSA Gator send no CORS headers, so this needs the backend (see live mode above).
- **Priority:** P3

### Animated GIF / video export of a field
- **What:** download the blink as a GIF or video.
- **Why deferred:** needs a new client-side dependency.
- **Priority:** P3

### Embed mode (`?embed=1`)
- **What:** a chrome-less player for embedding in other pages.
- **Why deferred:** 24h budget.
- **Priority:** P3

## Open follow-ups from the base 2D plan's reviews
From the base plan's review report (`docs/plans/01-base-2d-sky-time-machine.md`, "GSTACK REVIEW REPORT"), which says these were carried "in TODOS.md".

### Design system for the 2D player (design review: issues open, 5/10)
- **What:** shared design tokens (type, colour, spacing) for the 2D player.
- **Status:** mostly covered by the 3D plan's `web/css/tokens.css`, which both pages share (`docs/plans/04-3d-object-explorer.md` §13.1). Check that the player uses it, then close this.
- **Priority:** P2

### Measure teammate setup time (DX review: issues open, 7/10)
- **What:** time a fresh clone to the `?t=sample` fixture playing; target under 5 minutes.
- **Why:** the DX review set the target but never measured it.
- **Priority:** P3
