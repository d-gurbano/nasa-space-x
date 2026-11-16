# Rewind data contract (engine writes, website reads) - v1

The engine writes the website data to one folder outside git:
  SITE_DATA = /Users/rahmanbazarov/Data/programming/SpaceApps2026-Rewind/data/site/
The website reads the same files from `public/data/` (a sync script copies SITE_DATA there). Until real data exists, the website uses `public/data-sample/` in the SAME format, with every sample marked "sample": true.

All JSON is UTF-8. Times are given as MJD (UTC) plus ISO strings. Positions in 3D are heliocentric ecliptic J2000, in AU. Angles are in degrees. Image paths are relative to the JSON file that names them.

## 1. site/index.json
{
  "schema": "rewind-site-v1", "generated": "<ISO>", "sample": false,
  "headline_stats": {"objects_searched": N, "found": N, "hints": N, "too_faint": N, "frames_read": N},
  "benchmark": "benchmark.json",
  "objects": [ {
     "slug": "c2026s1", "name": "C/2026 S1", "kind": "comet|neo|mba|lost|famous",
     "verdict": "FOUND|HINT|TOO_FAINT|NO_PHOTOS|PENDING",
     "verdict_text": "one plain sentence",
     "discovered": {"mjd": 61299.0, "iso": "2026-09-16", "by": "survey or person", "site": "observatory"},
     "first_spherex_hint": {"mjd": ..., "iso": ..., "days_before_discovery": 6} | null,
     "best_snr": 11.1, "n_frames": 128,
     "thumb": "objects/c2026s1/thumb.png",
     "page": "objects/c2026s1/object.json"
  } ],
  "flash_events": [ {"slug": "c2026s1", "mjd": ..., "iso": ..., "photo": "objects/c2026s1/flash_01.png",
                     "spherex_xyz_au": [x,y,z], "object_xyz_au": [x,y,z], "label": "SPHEREx photo, 6 days before discovery"} ]
}

## 2. site/orbits.json  (dots for the 3D scene)
{
  "schema": "rewind-orbits-v1", "epoch_mjd": <common epoch>, "fields": ["a","e","i","node","peri","M","H","flag"],
  "flag_bits": {"1": "neo", "2": "pha", "4": "new_since_2025", "8": "comet", "16": "in_rewind"},
  "rows": [[a,e,i,node,peri,M,H,flag], ...]
}
The file holds every NEO, every comet with an orbit, every object found since 2025-04-01 and a random sample of main-belt asteroids: about 60,000 to 120,000 rows, rounded to stay under about 8 MB. orbits.bin has the same rows as Float32 (same column order, row-major), and orbits.bin.json gives the row count and fields, so the website can load it fast.

## 3. site/planets.json
Keplerian elements for Mercury to Neptune (JPL "approximate positions of the planets" table with rates), plus Earth. SPHEREx itself follows Earth (low Earth orbit), so the website draws SPHEREx at Earth's position.

## 4. site/objects/<slug>/object.json
{
  "schema": "rewind-object-v1", "slug", "name", "kind", "verdict", "verdict_text", "sample": false,
  "story": {"discovered_iso", "by", "site", "plain": "<short plain-language story>", "sources": [urls]},
  "facts": {"H": .., "diameter_km": ..|null, "albedo": ..|null, "class": ..|null, "neo": bool, "pha": bool, "sentry": bool, "moid_au": ..|null, "next_close_approach": {"iso", "dist_ld"}|null},
  "orbit": {"epoch_mjd", "a","e","i","node","peri","M","q","Q","period_yr"},
  "cloud": {"dates_mjd": [...], "before": [[[x,y,z] x N clones] per date], "after": same | null,
            "before_sigma_km_at": {"iso", "km"}, "after_sigma_km_at": {"iso", "km"} | null,
            "note": "after = with the Rewind positions added; null if nothing measured"},
  "spherex": {
     "frames": [{"key", "mjd", "iso", "detector", "wavelength_um", "pred_ra", "pred_dec", "sigma_px",
                 "flux_ujy", "flux_err", "snr", "flags", "used": bool, "png": "frames/f000.png"}],
     "days": [{"iso", "n_frames", "snr", "png": "days/d0.png"}],
     "stack": {"png": "stack.png", "png_median": "stack_median.png", "snr": .., "ab_mag": .., "n_frames": ..},
     "spherex_xyz_au_at_frames": [[x,y,z], ...]
  },
  "checks": {
     "null_paths": {"n": 24, "snr_mean": .., "snr_std": .., "n_exceeding": 0},
     "time_shift": {"shifts_days": [...], "snr": [...]},
     "per_day_positive": "6 of 6",
     "static_sky_subtracted": {"snr": ..},
     "injection": {"limit_ab_mag": .., "recovered_fraction_at_object_mag": ..},
     "orbit_fit": {"rms_arcsec_before": .., "rms_arcsec_after": .., "new_points": N} | null,
     "trail_px": .., "clone_search": {"n_clones": .., "false_alarm_rate": ..} | null,
     "real_or_fake_score": .. | null
  },
  "composition": {"points": [{"um", "value", "err"}], "templates": [{"name", "um": [...], "value": [...]}],
                  "best_match": "S" | null, "label": "rough match"},
  "quiz": {"image": "quiz.png", "answer_xy": [x, y], "answer_text": "..."},
  "shape_model": {"glb": "...", "source": "NASA ...", "credit": "..."} | null,
  "credits": ["NASA/IPAC IRSA SPHEREx QR3/DR1", "..."]
}

## 5. site/benchmark.json  ("pretend it is new" test)
{"cases": [{"name", "hidden_until_iso", "truth": "seen|not seen", "rewind_verdict", "snr", "pos_err_arcsec"}],
 "summary": {"n": .., "found": .., "missed": .., "false_alarms": .., "plain": "Rewind found X of Y known cases"}}

## 6. site/stars/<slug>/manifest.json  (5 challenge targets: barnard, wise0855, epsindib, rwaur, rdra)
{"slug", "name", "ra", "dec", "pm": {...}, "seasons": [{"iso", "png"}], "frames": [{"iso", "mjd", "wavelength_um", "png", "pred_xy": [x, y]}],
 "stack": {"png", "snr"}, "motion_caption": "Moves 10.4 arcsec per year, about 1.7 pixels per year", "note": "..."}

## 7. site/detectives/rounds.json
{"rounds": [{"id", "images": ["a.png", ...], "truth": "real|planted|known|empty", "answer_xy": [x,y] | null, "explain": "..."}]}
Planted fakes are labelled as planted after the user answers.

PNG rules: north up, east left; one shared brightness stretch per object; at most 512 px; nearest-neighbour upscaling so pixels stay honest.
