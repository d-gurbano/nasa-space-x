# Rewind website

The 3D website for Rewind (NASA Space Apps 2026, team SpaceX): a live solar system with real asteroid
orbits, a time slider, the SPHEREx "flash" when an older photo of a new object exists, and an object panel
with the photos, checks, uncertainty cloud and discovery story.

Vite + three.js + plain TypeScript. Node 22.

## Run

```bash
cd web
npm install && xattr -dr com.apple.quarantine node_modules   # macOS
npm run sync-data        # copy engine output (MAIN/data/site) into public/data
npm run dev              # local dev server
npm run build            # typecheck + static build into web/dist (relative paths)
npm run preview -- --port 4317 --host 127.0.0.1
npm test                 # Vitest: Kepler solver, dates, data loading, ranking, MPC format
```

Data: the site reads `public/data/index.json` (real engine output, see `../docs/DATA-CONTRACT.md`) and falls
back to `public/data-sample/` (a generated fixture with real orbits and made-up results, all marked
`"sample": true`; rebuild it with `npm run sample`). Each file falls back separately, and anything from the
sample shows a "Sample data" chip.

## Useful URLs

- `/?demo=1`: scripted 25-second camera and time path for screen recording (no UI chrome).
- `/?fps=1`: frame-rate meter.
- `/?flash=<slug>`: choose the object for the guided rewind and the demo (otherwise picked automatically:
  FOUND before HINT, highest null-scaled S/N, never a known object).
- `#/object/<slug>`, `#/sky`, `#/games`, `#/targets`, `#/blind-test`, `#/methods`, `#/about` (old `#/detectives`, `#/stars`, `#/benchmark`, `#/scientists` redirect).

## Deploy to GitHub Pages

`scripts/deploy-gh-pages.sh` (in the repo root) builds the site and force-pushes `web/dist` as a single
commit to the `gh-pages` branch of the repo you give it:

```bash
scripts/deploy-gh-pages.sh git@github.com:OWNER/REPO.git          # branch defaults to gh-pages
scripts/deploy-gh-pages.sh git@github.com:OWNER/REPO.git my-pages # or another branch
```

It syncs engine data first, runs the typecheck, tests and build, adds `.nojekyll`, and pushes from a
temporary folder, so your working tree is untouched. Then turn on Pages for that branch in the repo
settings. The build uses relative paths, so it works under `https://OWNER.github.io/REPO/`.
It publishes everything in `web/dist`, including the synced real data, so check that the data may be public
before running it. (It has not been run by the website job.)
