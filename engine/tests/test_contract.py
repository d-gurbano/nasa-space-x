"""Check the written website files against docs/DATA-CONTRACT.md (skipped if the site is not built)."""
import json
import os

import pytest

from rewind_engine import config as C

INDEX = os.path.join(C.SITE, "index.json")
pytestmark = pytest.mark.skipif(not os.path.exists(INDEX), reason="site not built")

VERDICTS = {"FOUND", "HINT", "TOO_FAINT", "NO_PHOTOS", "PENDING"}
KINDS = {"comet", "neo", "mba", "lost", "famous"}


def _idx():
    return json.load(open(INDEX))


def test_index_shape():
    idx = _idx()
    assert idx["schema"] == "rewind-site-v1" and idx["sample"] is False
    for k in ("objects_searched", "found", "hints", "too_faint", "frames_read"):
        assert k in idx["headline_stats"]
    for o in idx["objects"]:
        assert {"slug", "name", "kind", "verdict", "verdict_text", "discovered", "first_spherex_hint", "best_snr",
                "n_frames", "thumb", "page"} <= set(o)
        assert o["verdict"] in VERDICTS and o["kind"] in KINDS
        assert os.path.exists(os.path.join(C.SITE, o["page"]))
        if o["thumb"]:
            assert os.path.exists(os.path.join(C.SITE, o["thumb"]))
    for f in idx["flash_events"]:
        assert {"slug", "mjd", "iso", "photo", "spherex_xyz_au", "object_xyz_au", "label"} <= set(f)
        assert os.path.exists(os.path.join(C.SITE, f["photo"]))


def test_object_pages():
    for o in _idx()["objects"]:
        p = os.path.join(C.SITE, o["page"])
        page = json.load(open(p))
        assert page["schema"] == "rewind-object-v1"
        for k in ("slug", "name", "kind", "verdict", "verdict_text", "story", "facts", "orbit", "cloud", "spherex", "checks",
                  "composition", "quiz", "shape_model", "credits"):
            assert k in page, (o["slug"], k)
        d = os.path.dirname(p)
        for fr in page["spherex"]["frames"]:
            assert {"key", "mjd", "iso", "detector", "wavelength_um", "pred_ra", "pred_dec", "sigma_px", "flux_ujy", "flux_err",
                    "snr", "flags", "used", "png"} <= set(fr)
            if fr["png"]:
                assert os.path.exists(os.path.join(d, fr["png"]))
        if page["cloud"]:
            c = page["cloud"]
            assert len(c["dates_mjd"]) == len(c["before"]) == 40
            assert all(len(x[0]) == 3 for x in c["before"])


def test_static_files():
    for f in ("orbits.json", "orbits.bin", "orbits.bin.json", "planets.json"):
        assert os.path.exists(os.path.join(C.SITE, f))
    for s in ("barnard", "wise0855", "epsindib", "rwaur", "rdra"):
        assert os.path.exists(os.path.join(C.SITE, "stars", s, "manifest.json"))
    r = json.load(open(os.path.join(C.SITE, "detectives", "rounds.json")))
    assert all(x["truth"] in ("real", "planted", "known", "empty") for x in r["rounds"])
