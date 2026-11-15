import json

import numpy as np
import pandas as pd

from rewind_engine import site_static as S


def _dist(name, mjd):
    return float(np.linalg.norm(S.planet_xyz(name, mjd)))


def test_earth_perihelion_2026():
    assert abs(_dist("Earth", 61043.0) - 0.9833) < 0.002  # 2026-01-03


def test_planet_distances_plausible():
    for mjd in (60000.0, 61000.0, 62000.0):
        assert 1.38 < _dist("Mars", mjd) < 1.67
        assert 4.95 < _dist("Jupiter", mjd) < 5.46
        assert 0.30 < _dist("Mercury", mjd) < 0.47


def test_earth_in_ecliptic_and_moving_prograde():
    p0, p1 = S.planet_xyz("Earth", 61000.0), S.planet_xyz("Earth", 61001.0)
    assert abs(p0[2]) < 1e-4
    assert np.cross(p0, p1)[2] > 0


def test_mean_motion_and_propagation():
    assert abs(S.mean_motion(1.0) - 0.98561) < 1e-4
    M = S.propagate_M([350.0, 10.0], [1.0, 0.5], [61190.0, 61200.0], 61200.0 + 0.0, e=[0.1, 0.2])
    assert np.allclose(M, [0.0, 10.0])
    Mh = S.propagate_M(0.0, 1.0, 60000.0, 61200.0, e=1.5)  # hyperbolic: not wrapped
    assert float(Mh) == 1200.0


def test_flag_bits():
    f = S.flag_bits(q=[0.5, 2.0, 1.0, 3.0], pha=[True, False, False, False], new=[False, True, False, False],
                    comet=[False, False, True, False], rewind=[False, False, False, True])
    assert list(f) == [1 | 2, 4, 1 | 8, 16]


def test_build_orbits_selection():
    mk = lambda keys, a, q, comet: pd.DataFrame({"key": keys, "a": a, "e": 0.1, "i": 1.0, "node": 2.0,
                                                  "peri": 3.0, "M": 4.0, "H": 15.0, "q": q, "pha": False,
                                                  "comet": comet})
    mpc = mk(["1", "2", "3", "2025 AB", "433"], [2.5, 2.6, 2.7, 2.8, 1.46], [2.2, 2.3, 2.4, 2.5, 1.13], False)
    com = mk(["1P"], [17.8], [0.59], True)
    new = pd.DataFrame({"pdes": ["2025 AB"], "full_name": ["(2025 AB)"], "kind": ["au"], "a": [2.8], "e": [0.1],
                        "i": [1.0], "om": [2.0], "w": [3.0], "ma": [4.0], "epoch": [2461200.5], "H": [18.0],
                        "M1": [np.nan], "q": [2.5], "tp": [np.nan], "pha": ["N"]})
    df = S.build_orbits(mpc, com, new, mba_sample=1, rewind_desigs=["433"], pha_keys=["433"]).set_index("key")
    assert df.loc["433", "flag"] == 1 | 2 | 16
    assert df.loc["1P", "flag"] == 1 | 8
    assert df.loc["2025 AB", "flag"] == 4
    assert len(df) == 4  # 3 required + 1 sampled main-belt row


def test_comet_frame_hyperbolic():
    c = S.comet_frame(["C/X"], [2.0], [1.2], [10.0], [20.0], [30.0], [S.EPOCH_MJD], [8.0])
    assert abs(c.a.iloc[0] + 10.0) < 1e-9 and c.M.iloc[0] == 0.0


def test_motion_caption():
    assert S.motion_caption(-801.551, 10362.394) == "Moves 10.4 arcsec per year, about 1.7 pixels per year"


def test_north_up_east_left():
    w, n = S.out_wcs(180.0, 10.0)
    xy_e = S.png_xy(w, n, 1, 180.0 + 20 / 3600 / np.cos(np.radians(10)), 10.0)
    xy_n = S.png_xy(w, n, 1, 180.0, 10.0 + 20 / 3600)
    c = n / 2
    assert xy_e[0] < c and abs(xy_e[1] - c) < 1   # east is left
    assert xy_n[1] < c and abs(xy_n[0] - c) < 1   # north is up


def test_planets_json(tmp_path):
    S.write_planets(str(tmp_path))
    d = json.load(open(tmp_path / "planets.json"))
    assert [p["name"] for p in d["planets"]][:4] == ["Mercury", "Venus", "Earth", "Mars"]
    assert "Earth" in d["spherex"]
