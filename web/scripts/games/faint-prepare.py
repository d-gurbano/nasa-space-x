"""Too faint?: one small list of every searched object with the numbers the game shows.

All values come from web/public/data/index.json and objects/<slug>/object.json.
pred_ab is the predicted AB magnitude in the stack: the pipeline writes the measured magnitude
ab = pred - 2.5 log10(amp), with amp = measured flux / predicted flux, so pred = ab + 2.5 log10(amp).
Objects with no positive measured flux (amp <= 0) have no stored prediction and are left out.

Run: python3 web/scripts/games/faint-prepare.py
"""
import json
import math
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "public/data"
OUT = DATA / "games/faint/objects.json"

rows = []
for o in json.loads((DATA / "index.json").read_text())["objects"]:
    if o["verdict"] not in ("FOUND", "HINT", "TOO_FAINT"):
        continue
    p = json.loads((DATA / o["page"]).read_text())
    st = (p.get("spherex") or {}).get("stack") or {}
    ab, amp, snr = st.get("ab_mag"), st.get("flux_fraction_of_predicted"), st.get("snr")
    if ab is None or not amp or amp <= 0 or snr is None:
        continue
    inj = (p.get("checks") or {}).get("injection") or {}
    rows.append({
        "slug": o["slug"], "name": o["name"], "kind": o["kind"], "verdict": o["verdict"],
        "pred_ab": round(ab + 2.5 * math.log10(amp), 1),
        "n_frames": st.get("n_frames"), "snr": snr,
        "limit_ab": inj.get("limit_ab_mag"),
    })
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"objects": rows}, separators=(",", ":")))
from collections import Counter
print(len(rows), Counter(r["verdict"] for r in rows), OUT.stat().st_size)
