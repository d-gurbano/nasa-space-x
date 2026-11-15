"""A1 - fast vectorized two-body ephemeris screen (ESTIMATED quality, for ranking only).
Heliocentric two-body Kepler propagation from SBDB osculating elements (q, e, i, om, w, tp, ecliptic J2000),
Earth from astropy builtin ephemeris, geocentric observer (SPHEREx/NEOWISE are in LEO; parallax ignored).
Gives V (asteroids, H-G) or total T-mag (comets, M1/K1), r, Delta, phase, solar elongation, and a rough
NEATM-lite W2 thermal magnitude. NOT for pointing; B1 must use kete/Horizons for real predictions.
"""
import numpy as np
from astropy.time import Time
from astropy.coordinates import get_body_barycentric
import astropy.units as u

K = 0.01720209895  # Gauss constant, rad/day
OBL = np.deg2rad(23.4392911)


def earth_helio_ecl(jd):
    t = Time(jd, format="jd", scale="tdb")
    e = get_body_barycentric("earth", t).xyz.to(u.au).value
    s = get_body_barycentric("sun", t).xyz.to(u.au).value
    x, y, z = e - s
    # equatorial -> ecliptic
    return np.stack([x, y * np.cos(OBL) + z * np.sin(OBL), -y * np.sin(OBL) + z * np.cos(OBL)], axis=-1)  # (T,3)


def _rotmat(i, om, w):
    i, om, w = np.deg2rad(i), np.deg2rad(om), np.deg2rad(w)
    co, so, ci, si, cw, sw = np.cos(om), np.sin(om), np.cos(i), np.sin(i), np.cos(w), np.sin(w)
    P = np.stack([co * cw - so * sw * ci, so * cw + co * sw * ci, sw * si], -1)
    Q = np.stack([-co * sw - so * cw * ci, -so * sw + co * cw * ci, cw * si], -1)
    return P, Q


def helio_pos(q, e, i, om, w, tp, jd):
    """q,e,i,om,w,tp: arrays (N,). jd: scalar. Returns (N,3) au."""
    e = np.where(np.abs(e - 1) < 1e-5, np.where(e < 1, 1 - 1e-5, 1 + 1e-5), e)
    a = q / (1 - e)
    dt = jd - tp
    xs = np.empty_like(q); ys = np.empty_like(q)
    el = e < 1
    if el.any():
        ae, ee = a[el], e[el]
        M = K * dt[el] / ae ** 1.5
        M = np.mod(M + np.pi, 2 * np.pi) - np.pi
        E = np.where(ee > 0.8, np.pi * np.sign(M), M)
        for _ in range(30):
            E = E - (E - ee * np.sin(E) - M) / (1 - ee * np.cos(E))
        xs[el] = ae * (np.cos(E) - ee)
        ys[el] = ae * np.sqrt(1 - ee ** 2) * np.sin(E)
    hy = ~el
    if hy.any():
        ah, eh = -a[hy], e[hy]
        N = K * dt[hy] / ah ** 1.5
        F = np.arcsinh(N / eh)
        for _ in range(50):
            F = F - (eh * np.sinh(F) - F - N) / (eh * np.cosh(F) - 1)
        xs[hy] = ah * (eh - np.cosh(F))
        ys[hy] = ah * np.sqrt(eh ** 2 - 1) * np.sinh(F)
    P, Q = _rotmat(i, om, w)
    return xs[:, None] * P + ys[:, None] * Q


def hg_phase(alpha, G=0.15):
    t = np.tan(alpha / 2)
    p1 = np.exp(-3.33 * t ** 0.63); p2 = np.exp(-1.87 * t ** 1.22)
    return -2.5 * np.log10((1 - G) * p1 + G * p2)


def w2_thermal_mag(H, r, d, alpha, pv=0.14, eta=1.4, eps=0.9):
    """Very rough NEATM-lite: disk of diameter D at an effective temperature. ESTIMATED to ~1 mag."""
    D_km = 1329.0 / np.sqrt(pv) * 10 ** (-H / 5)
    A = 0.39 * pv  # bond albedo, q=0.39 (G=0.15)
    Tss = (1361.0 * (1 - A) / (eta * eps * 5.670374e-8)) ** 0.25 / np.sqrt(r)
    Teff = 0.85 * Tss
    lam = 4.6e-6
    h, c, kb = 6.62607e-34, 2.99792e8, 1.380649e-23
    B = 2 * h * c ** 2 / lam ** 5 / np.expm1(np.clip(h * c / (lam * kb * Teff), 1e-6, 700))  # W m-2 m-1 sr-1
    omega = np.pi * (D_km * 1e3 / 2) ** 2 / (d * 1.495978707e11) ** 2
    Fl = eps * B * omega * 10 ** (-0.4 * 0.01 * np.rad2deg(alpha))  # W m-2 m-1
    Fnu = Fl * lam ** 2 / c / 1e-26  # Jy
    return -2.5 * np.log10(np.clip(Fnu, 1e-30, None) / 171.787)  # W2 Vega


def screen(df, jd_start, jd_end, step=2.0, elong=(91.5, 120.0), vlim_stack=21.0, w2lim=15.0, chunk=20000):
    """For each row, over [jd_start, jd_end_row) (jd_end may be array), find the brightest predicted mag
    while solar elongation is inside `elong`. Returns dict of arrays."""
    n = len(df)
    jd_end = np.broadcast_to(np.asarray(jd_end, float), (n,)).copy()
    jd_st = np.broadcast_to(np.asarray(jd_start, float), (n,)).copy()  # per-object start allowed
    jd_st = np.where(np.isfinite(jd_st), jd_st, np.nanmin(jd_st))
    grid = np.arange(np.nanmin(jd_st), np.nanmax(jd_end) + step, step)
    E = earth_helio_ecl(grid)
    q = df["q"].to_numpy(float); e = df["e"].to_numpy(float)
    i = df["i"].to_numpy(float); om = df["om"].to_numpy(float); w = df["w"].to_numpy(float)
    tp = df["tp"].to_numpy(float)
    H = df["H"].to_numpy(float) if "H" in df else np.full(n, np.nan)
    G = df["G"].to_numpy(float) if "G" in df else np.full(n, np.nan)
    G = np.where(np.isfinite(G), G, 0.15)
    M1 = df["M1"].to_numpy(float) if "M1" in df else np.full(n, np.nan)
    K1 = df["K1"].to_numpy(float) if "K1" in df else np.full(n, np.nan)
    K1 = np.where(np.isfinite(K1), K1, 10.0)
    is_comet = ~np.isfinite(H) & np.isfinite(M1)
    best = np.full(n, np.inf); best_jd = np.full(n, np.nan); best_r = np.full(n, np.nan); best_d = np.full(n, np.nan)
    best_el = np.full(n, np.nan); ndays = np.zeros(n); nvis = np.zeros(n)
    bw2 = np.full(n, np.inf); bw2_jd = np.full(n, np.nan); nw2 = np.zeros(n)
    ok = np.isfinite(q) & np.isfinite(e) & np.isfinite(tp) & (np.isfinite(H) | np.isfinite(M1))
    for k, jd in enumerate(grid):
        act = ok & (jd < jd_end) & (jd >= jd_st)
        if not act.any():
            continue
        idx = np.where(act)[0]
        rv = helio_pos(q[idx], e[idx], i[idx], om[idx], w[idx], tp[idx], jd)
        gv = rv - E[k]
        r = np.linalg.norm(rv, axis=1); d = np.linalg.norm(gv, axis=1)
        cos_el = np.sum(-E[k] * gv, axis=1) / (np.linalg.norm(E[k]) * d)
        el = np.rad2deg(np.arccos(np.clip(cos_el, -1, 1)))
        cos_a = np.sum(rv * gv, axis=1) / (r * d)
        alpha = np.arccos(np.clip(cos_a, -1, 1))
        mag = np.where(is_comet[idx], M1[idx] + 5 * np.log10(d) + K1[idx] * np.log10(r),
                       H[idx] + 5 * np.log10(r * d) + hg_phase(alpha, G[idx]))
        inside = (el >= elong[0]) & (el <= elong[1])
        nvis[idx] += inside * step
        m = np.where(inside, mag, np.inf)
        upd = m < best[idx]
        j = idx[upd]
        best[j] = m[upd]; best_jd[j] = jd; best_r[j] = r[upd]; best_d[j] = d[upd]; best_el[j] = el[upd]
        ndays[idx] += (m < vlim_stack) * step
        w2 = np.where(inside & ~is_comet[idx], w2_thermal_mag(H[idx], r, d, alpha), np.inf)
        u2 = w2 < bw2[idx]
        j2 = idx[u2]; bw2[j2] = w2[u2]; bw2_jd[j2] = jd
        nw2[idx] += (w2 < w2lim) * step
    best[~np.isfinite(best)] = np.nan; bw2[~np.isfinite(bw2)] = np.nan
    return dict(best_mag=best, best_jd=best_jd, best_r=best_r, best_delta=best_d, best_elong=best_el,
                days_in_elong=nvis, days_mag_lt_lim=ndays, best_w2=bw2, best_w2_jd=bw2_jd, days_w2_lt_lim=nw2)


def sky_sigma_arcsec(df, jd):
    """Crude 1-sigma along-track sky uncertainty proxy (arcsec) at jd from SBDB sigma_ma and sigma_a
    (ignores correlations and close approaches): sigma_M(t)^2 = sigma_ma^2 + (1.5 n sigma_a / a * dt)^2,
    converted with r/Delta ~ 1 (so it is a mean-anomaly angle, roughly the sky angle for Delta ~ r). COMPUTED proxy."""
    a = df["a"].to_numpy(float); sa = df["sigma_a"].to_numpy(float); sm = df["sigma_ma"].to_numpy(float)
    n = np.rad2deg(K / np.abs(a) ** 1.5)  # deg/day
    ep = df["epoch"].to_numpy(float)
    dt = np.asarray(jd, float) - ep
    sM = np.sqrt(np.nan_to_num(sm) ** 2 + (1.5 * n * np.nan_to_num(sa) / np.abs(a) * dt) ** 2)
    sM = np.where(np.isfinite(sm) | np.isfinite(sa), sM, np.nan)
    return sM * 3600.0
