import json
import os

from rewind_engine import merge_kaggle as MK


def _entry(slug, verdict, snr):
    return dict(slug=slug, name=slug, kind="neo", verdict=verdict, verdict_text="", discovered=None, first_spherex_hint=None,
                best_snr=snr, n_frames=10, thumb=None, page=f"objects/{slug}/object.json")


def test_merge_adds_new_and_compares_existing(tmp_path):
    site, kag, out = tmp_path / "site", tmp_path / "kaggle", tmp_path / "out"
    (site / "objects" / "a").mkdir(parents=True)
    json.dump(dict(schema="rewind-site-v1", objects=[_entry("a", "FOUND", 7.0)], flash_events=[{"slug": "a", "mjd": 2.0}],
                   headline_stats=dict(frames_read=10), extra_field=1), open(site / "index.json", "w"))
    run = kag / "rewind-c2-engine-all-a"
    for slug, v in (("a", "HINT"), ("b", "TOO_FAINT")):
        os.makedirs(run / "work" / "objects" / slug)
        os.makedirs(run / "site" / "objects" / slug)
        json.dump(dict(entry=_entry(slug, v, 1.0), flashes=[{"slug": slug, "mjd": 1.0}], n_read=5),
                  open(run / "work" / "objects" / slug / "entry.json", "w"))
    s = MK.merge(str(site), str(kag), str(out), orbits=False)
    assert s["added_slugs"] == ["b"] and s["already_in_site"] == 1 and s["crosscheck_same_verdict"] == 0
    idx = json.load(open(out / "index.json"))
    assert [e["slug"] for e in idx["objects"]] == ["a", "b"]
    assert idx["objects"][0]["verdict"] == "FOUND"  # the site's own result is kept
    assert idx["headline_stats"]["frames_read"] == 15 and idx["extra_field"] == 1
    assert [f["slug"] for f in idx["flash_events"]] == ["b", "a"]  # sorted by mjd
    assert (out / "objects" / "b").is_dir()
    cc = json.load(open(out / "kaggle_crosscheck.json"))["crosscheck"]
    assert cc[0]["mac_verdict"] == "FOUND" and cc[0]["kaggle_verdict"] == "HINT"
