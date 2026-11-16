"""Step 5: one verdict per object from the measured checks, with one plain sentence.

FOUND     : cleaned (static-sky subtracted) stack S/N >= 5 after null scaling, no null path reaches it,
            time-shift peak at 0, >= 2 days positive, injection says detectable, orbit fit stays good.
HINT      : some of those checks pass (but not all).
TOO_FAINT : injection says the object was below the limit, and nothing significant is seen.
NO_PHOTOS : SPHEREx never imaged it in the searched window.
Known (famous) objects use the same tests, but FOUND there means "SPHEREx saw it", never a precovery."""
from __future__ import annotations

import numpy as np

SNR_FOUND = 5.0
SNR_HINT = 3.0


def checks_passed(m: dict, orbit_fit: dict | None, cleaned: bool):
    c = dict(
        snr=bool(np.isfinite(m.get("snr_scaled", np.nan)) and m["snr_scaled"] >= SNR_FOUND),
        cleaned=bool(cleaned),
        nulls=bool(m.get("null_exceed", 99) == 0 and m.get("null_n", 0) >= 12),
        time_shift=bool(m.get("shift_peak_at_zero")),
        days=bool(m.get("days_positive", 0) >= 2),
        detectable=bool(np.isfinite(m.get("recovered_at_pred", np.nan)) and m["recovered_at_pred"] >= 0.5),
        orbit=bool(orbit_fit is not None and orbit_fit.get("ok")),
        sign_test=_sign_ok(m),
        not_one_day=bool(np.isfinite(m.get("snr_without_best_day", np.nan)) and m["snr_without_best_day"] >= SNR_HINT),
    )
    return c


def _sign_ok(m):
    """More frames positive on the target path than on every null path, and >= 3 sigma above the null mean."""
    fp = m.get("frac_positive") or {}
    t, mu, sd, mx = (fp.get(k, np.nan) for k in ("target", "null_mean", "null_std", "null_max"))
    if m.get("median_frame_snr", 0) >= 5 and t >= 0.9:  # seen in single photos: the sign test is moot (its wings reach the nulls)
        return True
    if not all(np.isfinite(x) for x in (t, mu, sd, mx)):
        return False
    return bool(t > mx and (t - mu) / max(sd, 1e-6) >= 3)


PLAIN = dict(snr="stack S/N below 5", nulls="a null trajectory reached the same S/N", time_shift="S/N does not peak at zero "
             "time shift", days="positive on fewer than 2 nights", detectable="predicted magnitude below the injection-recovery limit",
             cleaned="no usable static-sky reference", orbit="new positions inconsistent with the orbit",
             sign_test="sign test failed (too few positive single images)", not_one_day="signal depends on a single night")


def decide(obj, res: dict | None, orbit_fit: dict | None = None, clone: dict | None = None):
    """Returns (verdict, sentence, checks_passed dict)."""
    name = obj.name
    if res is None or res.get("n_frames_measured", 0) == 0:
        if res is not None and res.get("pending"):
            return "PENDING", f"The SPHEREx images of {name} are still being processed.", {}
        if res is not None and res.get("most_error"):
            return "NO_PHOTOS", (f"No SPHEREx image list for {name}: the IRSA MOST service could not compute its "
                                 f"ephemeris, so it was not searched."), {}
        return "NO_PHOTOS", f"No SPHEREx image covers the predicted position of {name} in the searched window.", {}
    m = res["main"]
    c = checks_passed(m, orbit_fit, res.get("cleaned", False))
    if not m.get("n") and res.get("n_qa_dropped", 0) > 0:  # nothing left to stack: say so instead of "too faint"
        return "TOO_FAINT", (f"SPHEREx imaged {name} {res['n_frames_measured']} times, but every image was rejected "
                             f"because bright stars lie next to the predicted path, so no constraint is possible."), c
    known = obj.role == "known"
    snr = m.get("snr_scaled", np.nan)
    lim_ok = c["detectable"]
    n_core = sum(c[k] for k in ("snr", "nulls", "time_shift", "days"))
    if clone and clone.get("significant"):
        n_core += 1
    if all(c[k] for k in ("snr", "nulls", "time_shift", "days", "detectable", "cleaned", "sign_test", "not_one_day")) and (c["orbit"] or known):
        v = "FOUND"
        if known:
            s = (f"SPHEREx detected {name} (control object, not a precovery): null-calibrated S/N {snr:.1f} in the "
                 f"static-sky-subtracted stack of {m['n']} images, and every check passes.")
        else:
            pos = [d for d in m.get("days", []) if d.get("snr", 0) >= 2]
            when = ""
            if pos and isinstance(getattr(obj, "disc_iso", None), str):
                from .frames import iso_to_mjd
                dd = sorted(int(iso_to_mjd(obj.disc_iso) - d["day"]) for d in pos)
                when = f" taken {dd[0]}-{dd[-1]} days before its discovery" if dd[0] != dd[-1] else f" taken {dd[0]} days before its discovery"
            single = "" if m.get("median_frame_snr", 0) >= 5 else " (below the noise in every single image; detected only in the stack)"
            s = (f"Rewind detected {name} in SPHEREx images{when}: null-calibrated S/N {snr:.1f} in the static-sky-subtracted "
                 f"stack of {m['n']} images{single}, positive on {m['days_positive']} separate nights, and the orbit refit with "
                 f"the new positions stays consistent.")
    elif res.get("qa_fraction", 0) >= 0.3 and res.get("snr_before_qa", 0) >= SNR_FOUND and not snr >= SNR_HINT:
        v = "HINT"
        s = (f"A signal is present at the predicted position of {name} (S/N {res['snr_before_qa']:.1f}), but {res['qa_fraction']:.0%} "
             f"of the images are affected by bright stars next to the path (bad fits, halo flags). Without them nothing "
             f"significant remains, so this is a HINT, not a detection.")
    elif snr >= SNR_HINT or n_core >= 2 and snr >= 2:
        v = "HINT"
        miss = [PLAIN[k] for k in ("snr", "nulls", "time_shift", "days", "detectable", "cleaned", "sign_test", "not_one_day",
                                   "orbit") if not c[k] and not (k == "orbit" and known)]
        s = (f"A signal is present at the predicted position of {name} (S/N {snr:.1f}), but not every check passes "
             f"({'; '.join(miss)}), so this is a HINT, not a detection.")
        if res.get("qa_fraction", 0) >= 0.3:
            s += f" {res['qa_fraction']:.0%} of the images were rejected because bright stars lie next to the path."
    elif not lim_ok:
        lim = m.get("limit_mag")
        s = f"{name} was below the SPHEREx detection limit at this position" + (f": injection-recovery puts the local 50% limit at about AB {lim:.1f}." if lim and np.isfinite(lim) else ".")
        v = "TOO_FAINT"
    else:
        v = "TOO_FAINT"
        if getattr(obj, "kind", "") == "comet":
            s = (f"No significant signal at the predicted position of {name}. A point source at its predicted total "
                 f"magnitude would have been recovered, but comet magnitude predictions are uncertain (outbursts, extended coma), "
                 f"so it was probably fainter or more diffuse than predicted.")
        else:
            s = (f"No significant signal at the predicted position of {name}, although a source at the predicted magnitude "
                 f"would have been recovered: it was fainter than predicted, or off the predicted path.")
    if res.get("crowded") and v != "FOUND":
        s += " The images lie in a crowded Galactic field, where faint sources are harder to separate from stars."
    return v, s, c
