"""A1 - build clean tables and ranked target lists from the raw pulls.
Run after fetch_sbdb.py, fetch_live.py, fetch_disc_obs.py.  python code/A1/build_targets.py
All brightness / sky-uncertainty numbers here are ESTIMATED (two-body screen, see ephem.py) unless noted.
"""
import gzip, json, re, glob, pathlib, time
import numpy as np, pandas as pd
from astropy.time import Time
import ephem

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/01-targets"; C = D / "clean"; R = D / "raw"; OUT = D / "lists"; OUT.mkdir(exist_ok=True)
NOW = Time("2026-11-15T00:00:00", scale="utc").jd  # snapshot date
SPHX0 = Time("2025-05-01").jd  # SPHEREx survey start (VERIFIED: survey began May 1 2025)
SPHX_EL = (83.0, 115.0)  # MEASURED: 5th-95th percentile solar elongation of 14,972 SPHEREx frame-object rows in the Y1 MOST tables
LETTERS = "ABCDEFGHJKLMNOPQRSTUVWXY"


def jd(s):
    try:
        return Time(str(s).replace(" ", "-", 2) if re.match(r"^\d{4} \d\d \d", str(s)) else s).jd
    except Exception:
        return np.nan


def obs80_jd(s):
    m = re.match(r"(\d{4}) (\d\d) (\d\d\.?\d*)", str(s))
    if not m: return np.nan
    y, mo, d = int(m.group(1)), int(m.group(2)), float(m.group(3))
    return Time(f"{y}-{mo:02d}-01").jd + d - 1


def desig_halfmonth_jd(pdes):
    """Start JD of the half-month of a provisional designation like '2025 GA' or '2014 AA12' or comet '2025 K1'."""
    m = re.match(r"^(\d{4}) ([A-HJ-Y])", str(pdes))
    if not m: return np.nan
    y, L = int(m.group(1)), m.group(2)
    k = LETTERS.index(L); mon = k // 2 + 1; day = 1 if k % 2 == 0 else 16
    return Time(f"{y}-{mon:02d}-{day:02d}").jd


def prov_from_fullname(fn):
    m = re.search(r"\((\d{4} [A-Z]{2}\d*)\)", str(fn))
    if m: return m.group(1)
    m = re.match(r"^\s*\(?(\d{4} [A-Z]{2}\d*)\)?", str(fn))
    return m.group(1) if m else None


def comet_des(fn):
    m = re.match(r"^([CPDXAI]/-?\d{4} [A-Z]+\d*(-[A-Z]+)?)", str(fn))
    if m: return m.group(1)
    m = re.match(r"^(\d+[PDI](-[A-Z]+)?)", str(fn))
    return m.group(1) if m else str(fn)


def group_of(row):
    if str(row.get("kind", "")).startswith("c"): return "comet"
    if row.get("neo") == "Y": return "NEO"
    return {"MBA": "MBA", "IMB": "MBA", "OMB": "MBA", "MCA": "Mars-crosser", "TJN": "Trojan", "TNO": "TNO", "CEN": "Centaur",
            "HYA": "Hyperbolic"}.get(row.get("class"), str(row.get("class")))


def tag(df):
    df["group"] = [group_of(r) for r in df[["kind", "neo", "class"]].to_dict("records")]
    df["designation"] = np.where(df["group"] == "comet", df["full_name"].map(comet_des), df["pdes"])
    return df


def save(df, name, doc):
    df.to_csv(OUT / f"{name}.csv", index=False)
    df.to_parquet(OUT / f"{name}.parquet", index=False)
    DOCS[name] = doc
    print(name, len(df))


DOCS = {}
t0 = time.time()

# ---------------------------------------------------------------- base tables
neo = tag(pd.read_parquet(C / "sbdb_neo_all.parquet"))
com = tag(pd.read_parquet(C / "sbdb_comet_all.parquet"))
new = pd.concat([pd.read_parquet(C / f) for f in ["sbdb_new_firstobs_since_2025-04-01.parquet", "sbdb_new_desig_2025G_to_2025Y.parquet",
                                                  "sbdb_new_desig_2026.parquet"]])
com["prov"] = com["full_name"].str.extract(r"^[CPDXAI]/(\d{4} [A-Z]+\d*)")[0]
com_new = com[(com["prov"].map(desig_halfmonth_jd) >= Time("2025-04-01").jd) | (com["first_obs"] >= "2025-04-01")]
new = tag(pd.concat([new, com_new.drop(columns=["prov"], errors="ignore")]).drop_duplicates("spkid"))
new["desig_halfmonth_start_jd"] = [desig_halfmonth_jd(p if g != "comet" else str(fn).split("/")[-1])
                                   for p, g, fn in zip(new["pdes"], new["group"], new["full_name"])]

# discovery observations (MPC obs80 asterisk)
disc = pd.read_csv(C / "discovery_obs.csv", dtype=str) if (C / "discovery_obs.csv").exists() else pd.DataFrame(columns=["desig"])
disc = disc.drop_duplicates("desig")
new = new.merge(disc.rename(columns={"desig": "designation"}), on="designation", how="left")
new["disc_jd"] = new["disc_date_utc"].map(obs80_jd)
new["first_obs_jd"] = new["first_obs"].map(jd)
new["mpc_first_obs_jd"] = new["first_obs_utc"].map(obs80_jd) if "first_obs_utc" in new else np.nan
# best discovery date: MPC discovery asterisk > designation half-month start > SBDB first_obs
new["disc_date_best_jd"] = new["disc_jd"].fillna(new["desig_halfmonth_start_jd"]).fillna(new["first_obs_jd"])
new["disc_date_source"] = np.where(new["disc_jd"].notna(), "MPC_obs80_asterisk",
                                   np.where(new["desig_halfmonth_start_jd"].notna(), "designation_halfmonth_start", "sbdb_first_obs"))
new["disc_date_best"] = Time(new["disc_date_best_jd"].fillna(2451545.0).to_numpy(), format="jd").iso
new.loc[new["disc_date_best_jd"].isna(), "disc_date_best"] = ""
new["disc_date_best"] = new["disc_date_best"].str[:10]
# earliest known ground observation (min of SBDB first_obs and MPC first obs)
new["earliest_obs_jd"] = np.fmin(new["first_obs_jd"], new["mpc_first_obs_jd"])
new = new[new["disc_date_best_jd"] >= Time("2025-04-01").jd - 0.5].copy()
new.to_parquet(C / "new_objects_since_2025-04-01.parquet", index=False)
new.drop(columns=[c for c in new.columns if c.startswith("sigma_") or c in ("A1", "A2", "A3", "DT")]).to_csv(C / "new_objects_since_2025-04-01.csv", index=False)
DOCS["clean/new_objects_since_2025-04-01"] = ("All objects (any class) whose discovery/designation date is on/after 2025-04-01: union of SBDB "
                                              "first_obs>=2025-04-01, provisional designations 2025 G-Y and 2026, and comets designated 2025 G+/2026. "
                                              "disc_* columns from MPC obs80 discovery asterisk (only NEOs H<24, PHAs and comets were pulled).")
print("new objects", len(new), new.group.value_counts().to_dict())

# ---------------------------------------------------------------- (a) SPHEREx precovery candidates
pa = new[(new["disc_date_best_jd"] >= Time("2025-06-01").jd)].copy()
end = (pa["earliest_obs_jd"].fillna(pa["disc_date_best_jd"]) - 0.5).to_numpy()
scr = ephem.screen(pa, SPHX0, end, step=1.0, elong=SPHX_EL, vlim_stack=21.0)
for k, v in scr.items(): pa["pre_" + k] = v
scr2 = ephem.screen(pa, SPHX0, (pa["disc_date_best_jd"] - 0.5).to_numpy(), step=2.0, elong=SPHX_EL, vlim_stack=21.0)
pa["predisc_best_mag_to_discdate"] = scr2["best_mag"]; pa["predisc_days_lt21_to_discdate"] = scr2["days_mag_lt_lim"]
# brightest point at least 7 days before the earliest ground observation (real arc gain)
scr7 = ephem.screen(pa, SPHX0, end - 7.0, step=1.0, elong=SPHX_EL, vlim_stack=21.0)
pa["lead7_best_mag"] = scr7["best_mag"]; pa["lead7_days_mag_lt_lim"] = scr7["days_mag_lt_lim"]
pa["lead7_best_date"] = [Time(j, format="jd").iso[:10] if np.isfinite(j) else "" for j in scr7["best_jd"]]
pa["lead7_best_delta"] = scr7["best_delta"]
pa["lead7_best_AB_est"] = pa["lead7_best_mag"] - 0.3
# thermal (SPHEREx D6 ~4.6 um) for asteroids: W2 Vega -> AB (+3.339); D6 single-frame depth AB 17.0 vs 19.0 for D1-D3 (Y1/V4),
# so the reflected-equivalent AB is thermal_AB + 2.0. ESTIMATED (NEATM-lite, pV 0.14, eta 1.4).
pa["lead7_thermal_AB_est"] = scr7["best_w2"] + 3.339
pa["lead7_eff_AB_est"] = np.fmin(pa["lead7_best_AB_est"], pa["lead7_thermal_AB_est"] + 2.0)
pa["pre_window_days"] = np.clip(end - SPHX0, 0, None)
pa["pre_best_AB_est"] = pa["pre_best_mag"] - 0.3  # UNVERIFIED solar-like colour V-0.3
pa["pre_single_snr_est"] = 5 * 10 ** (-0.4 * (pa["pre_best_AB_est"] - 19.0))  # baseline D1-D3 5-sigma AB 19.0 (VERIFIED in Y1 from V4)
pa["pre_best_date"] = [Time(j, format="jd").iso[:10] if np.isfinite(j) else "" for j in pa["pre_best_jd"]]
pa["sky_sigma1_arcsec_at_best_proxy"] = ephem.sky_sigma_arcsec(pa, pa["pre_best_jd"].fillna(NOW).to_numpy())
pa["lead_days_at_best"] = pa["earliest_obs_jd"] - pa["pre_best_jd"]
pa["fast_mover_risk"] = pa["pre_best_delta"] < 0.05  # trailing / parallax risk in ~112 s SPHEREx exposures (ESTIMATED threshold)
pa["tier"] = np.select([pa["lead7_eff_AB_est"] <= 19.5, pa["lead7_eff_AB_est"] <= 21.0, pa["lead7_eff_AB_est"] <= 22.5], ["A_single", "B_stack", "C_deep_stack"], "D_too_faint")
pa.loc[pa["lead7_best_mag"].isna(), "tier"] = "X_no_window_7d"
y1 = {"2026 KC3", "2026 PW6", "2026 MM", "2026 JS1", "C/2025 W2", "C/2026 B2", "C/2026 H2", "P/2026 V1", "P/2026 C2", "C/2026 P4", "C/2025 X1",
      "C/2026 S1", "P/2026 R1", "P/2025 Y2", "C/2026 L1"}
pa["y1_stack_candidate"] = pa["designation"].isin(y1)
grp_w = pa["group"].map({"comet": 0.0, "NEO": 0.3}).fillna(1.0)  # prefer comets, then NEOs (Y1 yield); MBAs last
pa["rank_score"] = (pa["lead7_eff_AB_est"].fillna(99) + grp_w - 0.3 * np.log10(1 + pa["lead7_days_mag_lt_lim"])
                    + 0.5 * pa["fast_mover_risk"] - 0.5 * pa["y1_stack_candidate"])
pa = pa.sort_values("rank_score")
pa["shortlist_reason"] = np.where(pa["tier"].isin(["A_single", "B_stack"]) & ~pa["fast_mover_risk"] & pa["group"].isin(["NEO", "comet"]), "tier_A_or_B",
                                  np.where(pa["y1_stack_candidate"], "Y1_stack_candidate", ""))
cols_a = ["designation", "full_name", "group", "class", "neo", "pha", "H", "M1", "K1", "q", "e", "i", "a", "condition_code", "data_arc", "n_obs_used",
          "first_obs", "last_obs", "disc_date_best", "disc_date_source", "disc_station", "disc_mag", "disc_band", "first_station", "n_stations",
          "pre_window_days", "pre_best_mag", "pre_best_AB_est", "pre_single_snr_est", "pre_best_date", "pre_best_r", "pre_best_delta", "pre_best_elong",
          "pre_days_in_elong", "pre_days_mag_lt_lim", "pre_best_w2", "lead_days_at_best", "fast_mover_risk",
          "lead7_best_mag", "lead7_best_AB_est", "lead7_thermal_AB_est", "lead7_eff_AB_est", "lead7_best_date", "lead7_best_delta", "lead7_days_mag_lt_lim", "predisc_best_mag_to_discdate", "predisc_days_lt21_to_discdate",
          "sky_sigma1_arcsec_at_best_proxy", "y1_stack_candidate", "tier", "shortlist_reason", "rank_score", "spkid"]
save(pa[cols_a], "a_spherex_precovery_candidates",
     "Objects discovered on/after 2025-06-01. Window = SPHEREx survey start 2025-05-01 to 0.5 d before the EARLIEST known ground observation. "
     "pre_best_mag = brightest predicted V (asteroids, H-G) or total mag (comets, M1/K1) while solar elongation 83-115 deg (range MEASURED from Y1 MOST frames; geometry ESTIMATED, geocentric two-body). "
     "lead7_* = same but only up to 7 d before the earliest ground observation (real arc gain); lead7_eff_AB_est = min(reflected AB, thermal D6 AB + 2.0); tier and rank use lead7_eff. fast_mover_risk = Delta<0.05 au at best. "
     "pre_best_AB_est = V-0.3; pre_single_snr_est vs 5-sigma AB 19.0. tier (on lead7 AB) A<=19.5, B<=21, C<=22.5. pre_days_mag_lt_lim = days with mag<21 in "
     "window (stack potential). rank_score = AB + group weight (comet 0, NEO 0.3, other 1.0) - 0.3 log10(1+days<21); lower is better. "
     "Comet magnitudes use SBDB M1/K1 (K1=10 if missing) and are often too bright (Y1). Thermal (D5/D6) flux not included.")

# ---------------------------------------------------------------- (b) lost / poorly constrained recovery candidates
crit = []
for l in open(R / "mpc/Soft00CritList.txt"):
    if len(l) > 170:
        crit.append({"crit_readable": l[166:194].strip(), "crit_opps": l[123:126].strip(), "crit_arc": l[127:136].strip(), "crit_last_ref": l[107:116].strip()})
crit = pd.DataFrame(crit)
crit["crit_key"] = crit["crit_readable"].str.replace(r"^\((\d+)\).*", r"\1", regex=True).str.strip("()")
nea_ext = pd.DataFrame(json.load(gzip.open(R / "mpc/nea_extended.json.gz")))
nea_ext["key"] = nea_ext["Number"].fillna("").str.strip("()")
nea_ext.loc[nea_ext["key"] == "", "key"] = nea_ext["Principal_desig"]
nea_ext = nea_ext[["key", "Num_opps", "Last_obs", "U", "Arc_years"]].rename(columns={"Num_opps": "mpc_num_opps", "Last_obs": "mpc_last_obs", "U": "mpc_U", "Arc_years": "mpc_arc"})

sentry = pd.DataFrame(json.load(open(sorted(glob.glob(str(R / "sentry/sentry_summary_*.json")))[-1]))["data"])
sentry_des = set(sentry["des"])

lostN = neo[(pd.to_numeric(neo["condition_code"], errors="coerce") >= 5) | (neo["data_arc"] <= 30)].copy()
lostC = com[(com["prefix"] == "D") | (pd.to_numeric(com["condition_code"], errors="coerce") >= 7)].copy()
u5 = tag(pd.read_parquet(C / "sbdb_uncertain_U5plus_all.parquet"))
lostM = u5[(u5["group"] != "NEO") & (u5["H"] <= 16.0)].copy()
lost = pd.concat([lostN, lostC, lostM]).drop_duplicates("spkid")
lost["key"] = np.where(lost["pdes"].astype(str).str.match(r"^\d+$"), lost["pdes"], lost["pdes"])
lost = lost.merge(nea_ext, on="key", how="left")
lost["mpc_critical_list"] = lost["key"].isin(set(crit["crit_key"])) | lost["full_name"].map(prov_from_fullname).isin(set(crit["crit_readable"]))
lost["sentry"] = lost["pdes"].isin(sentry_des)
lost["last_obs_jd"] = lost["last_obs"].map(jd)
lost["years_since_last_obs"] = (NOW - lost["last_obs_jd"]) / 365.25
lost["single_opposition_proxy"] = (lost["data_arc"] <= 120) | (lost["mpc_num_opps"] == 1)
lost["lost_flag"] = np.select([(pd.to_numeric(lost["condition_code"], errors="coerce") >= 7) & (lost["years_since_last_obs"] > 2),
                               (pd.to_numeric(lost["condition_code"], errors="coerce") >= 5) & (lost["years_since_last_obs"] > 1)],
                              ["likely_lost", "poorly_constrained_unrecovered"], "poorly_constrained")
lost.loc[lost["prefix"] == "D", "lost_flag"] = "D_comet_lost_or_defunct"
scr = ephem.screen(lost, SPHX0, NOW, step=3.0, elong=SPHX_EL, vlim_stack=21.0)
for k, v in scr.items(): lost["sphx_" + k] = v
# SPHEREx-visible window AFTER the last observation only (true recovery, not precovery)
post_start = np.fmax(lost["last_obs_jd"].fillna(SPHX0).to_numpy() + 0.5, SPHX0)
scrp = ephem.screen(lost, post_start, NOW, step=3.0, elong=SPHX_EL, vlim_stack=21.0)
for k, v in scrp.items(): lost["post_" + k] = v
lost["post_window_days"] = np.clip(NOW - post_start, 0, None)
lost["sphx_best_date"] = [Time(j, format="jd").iso[:10] if np.isfinite(j) else "" for j in lost["sphx_best_jd"]]
lost["post_best_date"] = [Time(j, format="jd").iso[:10] if np.isfinite(j) else "" for j in lost["post_best_jd"]]
lost["sky_sigma1_arcsec_now_proxy"] = ephem.sky_sigma_arcsec(lost, NOW)
lost["sky_sigma3_deg_now_proxy"] = (3 * lost["sky_sigma1_arcsec_now_proxy"] / 3600).clip(upper=180.0)  # capped: linear proxy saturates
lost["sky_sigma1_arcsec_at_sphx_best_proxy"] = ephem.sky_sigma_arcsec(lost, lost["sphx_best_jd"].fillna(NOW).to_numpy())
lost["sky_sigma1_deg_at_sphx_best_proxy"] = lost["sky_sigma1_arcsec_at_sphx_best_proxy"] / 3600
lost["sky_sigma3_deg_at_post_best_proxy"] = np.minimum(3 * ephem.sky_sigma_arcsec(lost, lost["post_best_jd"].fillna(NOW).to_numpy()) / 3600, 180.0)
lost["sphx_best_AB_est"] = lost["sphx_best_mag"] - 0.3
lost["post_best_AB_est"] = lost["post_best_mag"] - 0.3
lost["sphx_after_last_obs"] = lost["post_best_mag"].notna()  # some SPHEREx-geometry window exists after the last observation
lost["fast_mover_risk"] = lost["post_best_delta"].fillna(lost["sphx_best_delta"]) < 0.02
lost["searchable_1deg"] = lost["sky_sigma3_deg_at_post_best_proxy"] < 1.0
# lost tiers (our definitions):
#  L1 truly lost: last observation >= 1 yr ago AND 3-sigma sky uncertainty now >= 0.5 deg (or unknown, e.g. old D/ comets)
#  L2 poorly constrained recent: seen within the last year, U>=5 or arc <=30 d
#  L3 old but findable: last obs >= 1 yr ago but 3-sigma now < 0.5 deg (not lost, just unobserved)
old1 = lost["years_since_last_obs"].fillna(99) >= 1.0
big = lost["sky_sigma3_deg_now_proxy"].fillna(999) >= 0.5
lost["lost_tier"] = np.select([old1 & big, ~old1, old1 & ~big], ["L1_truly_lost", "L2_recent_poorly_constrained", "L3_old_but_findable"], "")
pen_post = np.log10(np.clip(3600 * lost["sky_sigma3_deg_at_post_best_proxy"].fillna(180) / 6.15, 1, None))  # log10 3-sigma in SPHEREx px
pen_any = np.log10(np.clip(3 * lost["sky_sigma1_arcsec_at_sphx_best_proxy"].fillna(6.5e5) / 6.15, 1, None))
haz = 1.0 * (lost["pha"] == "Y") + 1.0 * lost["sentry"] + 0.5 * (lost["group"] == "NEO")
# rank within each tier: L1/L3 on the post-last-obs window (recovery); L2 on the whole SPHEREx era (arc extension)
lost["rank_score"] = np.where(lost["lost_tier"] == "L2_recent_poorly_constrained",
                              lost["sphx_best_AB_est"].fillna(99) + 0.5 * pen_any - haz + 1.0 * lost["fast_mover_risk"],
                              lost["post_best_AB_est"].fillna(99) + 0.25 * pen_post - haz + 1.0 * lost["fast_mover_risk"])
lost["tier_rank"] = lost.groupby("lost_tier")["rank_score"].rank(method="first").astype(int)
lost = lost.sort_values(["lost_tier", "rank_score"])
cols_b = ["designation", "full_name", "group", "class", "neo", "pha", "sentry", "mpc_critical_list", "H", "M1", "q", "e", "i", "a", "moid",
          "condition_code", "mpc_U", "data_arc", "n_obs_used", "first_obs", "last_obs", "years_since_last_obs", "mpc_num_opps", "mpc_arc",
          "single_opposition_proxy", "lost_flag", "sphx_best_mag", "sphx_best_AB_est", "sphx_best_date", "sphx_best_r", "sphx_best_delta", "sphx_best_elong",
          "sphx_days_in_elong", "sphx_days_mag_lt_lim", "sphx_best_w2", "lost_tier", "tier_rank", "post_window_days", "post_best_mag", "post_best_AB_est",
          "post_best_date", "post_best_r", "post_best_delta", "post_best_elong", "post_days_in_elong", "post_days_mag_lt_lim", "sky_sigma3_deg_now_proxy",
          "sky_sigma3_deg_at_post_best_proxy", "sky_sigma1_arcsec_now_proxy", "sky_sigma1_arcsec_at_sphx_best_proxy",
          "sky_sigma1_deg_at_sphx_best_proxy", "searchable_1deg", "sphx_after_last_obs", "fast_mover_risk", "sigma_a", "sigma_e", "sigma_ma", "sigma_tp", "rms", "rank_score", "spkid"]
cols_b = [c for c in cols_b if c in lost.columns]
save(lost[cols_b], "b_lost_recovery_candidates",
     "Poorly constrained objects: all NEOs with SBDB condition code U>=5 or data arc <=30 d; comets with prefix D or U>=7; non-NEOs with U>=5 and H<=16. "
     "lost_flag: likely_lost = U>=7 and last obs >2 yr ago; poorly_constrained_unrecovered = U>=5 and last obs >1 yr ago (our definitions, ESTIMATED). "
     "sphx_* = brightest predicted mag on the NOMINAL orbit 2025-05-01..2026-11-15 at solar elongation 83-115 deg (ESTIMATED; for lost objects the "
     "true position can be far off). sky_sigma1_* = crude 1-sigma along-track proxy from sigma_ma and sigma_a (COMPUTED, ignores correlations). "
     "mpc_critical_list = in MPC Soft00CritList. sphx_after_last_obs = predicted best SPHEREx moment is after the last observation (true recovery). "
     "searchable_1deg = 3-sigma proxy at the post-window best moment < 1 deg. hazard = 1 PHA + 1 Sentry + 0.5 NEO; fast_mover (Delta<0.02 au) +1; lower rank_score is better.")

l1base = (lost["lost_tier"] == "L1_truly_lost") & lost["sphx_after_last_obs"] & (lost["prefix"] != "D")
l1haz = l1base & (lost["sentry"] | (lost["pha"] == "Y")) & (lost["post_best_mag"] < 22.5)
L1 = lost[l1base & ((lost["post_best_mag"] < 21.5) | l1haz)].copy()
L1["shortlist_reason"] = np.where(L1["post_best_mag"] < 21.5, "L1_post_mag_lt_21.5", "L1_sentry_or_PHA_post_mag_lt_22.5_deep_stack")
L2 = lost[(lost["lost_tier"] == "L2_recent_poorly_constrained") & lost["sphx_after_last_obs"] & lost["searchable_1deg"] & (lost["post_best_mag"] < 21)
          & (lost["group"] != "comet")]
L3 = lost[(lost["lost_tier"] == "L3_old_but_findable") & lost["sphx_after_last_obs"] & (lost["post_best_mag"] < 21)]
L3 = L3.assign(shortlist_reason="L3_post_mag_lt_21"); L2 = L2.assign(shortlist_reason="L2_post_mag_lt_21_and_3sigma_lt_1deg")
sl = pd.concat([L1, L3, L2])
save(sl[cols_b + ["shortlist_reason"]], "b_lost_recovery_shortlist", "Shortlist, ordered L1 then L3 then L2, each by rank_score. L1 truly lost (last obs >=1 yr, 3-sigma now >=0.5 deg) "
     "with a SPHEREx-geometry window after the last observation and predicted post-window mag < 21.5 on the nominal orbit (or < 22.5 if Sentry or PHA, deep-stack case) (no search-area cut: the "
     "search region is part of the challenge; see sky_sigma3_deg_at_post_best_proxy). L3 old-but-findable with post-window mag < 21. L2 recent "
     "poorly constrained non-comets with post-window mag < 21 and 3-sigma < 1 deg. D/ comets excluded (defunct).")
sa = pa[pa["shortlist_reason"] != ""]
save(sa[cols_a], "a_spherex_precovery_shortlist", "Subset of a_spherex_precovery_candidates: NEOs and comets in tier A or B (lead7_eff_AB <= 21), "
     "not fast movers, plus every Y1 stack-only candidate (shortlist_reason). Same columns.")

# ---------------------------------------------------------------- (c) NEOWISE-era practice cases
num = []
with gzip.open(R / "mpc/NumberedMPs.txt.gz", "rt", errors="replace") as f:
    for l in f:
        m = re.match(r"^\s*\((\d+)\)", l)
        if m and len(l) > 52:
            num.append((m.group(1), l[41:51].strip(), l[51:52] == "*", l[53:78].strip(), l[78:].strip()))
num = pd.DataFrame(num, columns=["number", "mpc_disc_date", "mpc_disc_star", "mpc_disc_site", "mpc_discoverer"])
num.to_parquet(C / "mpc_numbered_discovery_circumstances.parquet", index=False)
DOCS["clean/mpc_numbered_discovery_circumstances"] = "Parsed MPC NumberedMPs.txt: number, discovery date, site name, discoverer for every numbered minor planet."
pc = pd.concat([neo, com[com["q"] < 5]]).drop_duplicates("spkid").copy()
pc["prov"] = np.where(pc["group"] == "comet", pc["full_name"].str.extract(r"^[CPDXAI]/(\d{4} [A-Z]+\d*)")[0], pc["full_name"].map(prov_from_fullname))
pc["prov_jd"] = pc["prov"].map(desig_halfmonth_jd)
pc["number"] = pc["pdes"].where(pc["pdes"].astype(str).str.match(r"^\d+$"))
pc = pc.merge(num, on="number", how="left")
pc["mpc_disc_jd"] = pc["mpc_disc_date"].map(lambda s: jd(str(s).replace(" ", "-")) if isinstance(s, str) and len(s) == 10 else np.nan)
pc["disc_jd"] = pc["mpc_disc_jd"].fillna(pc["prov_jd"])
pc["disc_date_source"] = np.where(pc["mpc_disc_jd"].notna(), "MPC_NumberedMPs", np.where(pc["prov_jd"].notna(), "designation_halfmonth_start", ""))
pc = pc[(pc["disc_jd"] >= Time("2010-02-01").jd) & (pc["disc_jd"] < Time("2024-09-01").jd)].copy()
pc["first_obs_jd"] = pc["first_obs"].map(jd)
pc["earliest_known_obs"] = pc["first_obs"]
pc["already_precovered"] = pc["first_obs_jd"] < pc["disc_jd"] - 5
pc["precovery_gain_days"] = np.clip(pc["disc_jd"] - pc["first_obs_jd"], 0, None)
W1, W1e, W2s, W2e = Time("2010-01-07").jd, Time("2011-02-01").jd, Time("2013-12-13").jd, Time("2024-08-08").jd
endp = pc["disc_jd"].to_numpy() - 0.5
res = []
for (s, e_) in [(W1, W1e), (W2s, W2e)]:
    res.append(ephem.screen(pc, s, np.minimum(endp, e_), step=2.0, elong=(88.0, 115.0), vlim_stack=21.0, w2lim=15.5))
for k in res[0]:
    pc["wise_" + k] = res[0][k]; pc["neowise_" + k] = res[1][k]
pc["best_w2_est"] = np.fmin(pc["wise_best_w2"], pc["neowise_best_w2"])
pc["best_w2_jd"] = np.where(pc["wise_best_w2"] <= pc["neowise_best_w2"].fillna(99), pc["wise_best_w2_jd"], pc["neowise_best_w2_jd"])
pc["best_w2_date"] = [Time(j, format="jd").iso[:10] if np.isfinite(j) else "" for j in pc["best_w2_jd"]]
pc["best_V_predisc_est"] = np.fmin(pc["wise_best_mag"], pc["neowise_best_mag"])
pc["days_w2_lt_15p5_predisc"] = pc["wise_days_w2_lt_lim"] + pc["neowise_days_w2_lt_lim"]
pc["disc_date_best"] = [Time(j, format="jd").iso[:10] for j in pc["disc_jd"]]
pc["neowise_discovery"] = pc["mpc_disc_site"].fillna("").str.contains("WISE", case=False)
# comets: no thermal model; rank on total mag (W2 ~ Vtotal - 1 is a placeholder, ESTIMATED)
key = np.where(pc["group"] == "comet", pc["best_V_predisc_est"] - 4.0, pc["best_w2_est"])
pc["years_best_before_disc"] = (pc["disc_jd"] - pc["best_w2_jd"]) / 365.25
pc["fast_mover_risk"] = np.fmin(pc["wise_best_delta"], pc["neowise_best_delta"]) < 0.02
pc["rank_score"] = (pd.Series(key, index=pc.index).fillna(99) - 0.3 * np.log10(1 + pc["days_w2_lt_15p5_predisc"]) + 1.0 * pc["fast_mover_risk"]
                    + 0.5 * (pc["years_best_before_disc"] > 2))  # two-body reliability drops over years
pc = pc.sort_values("rank_score")
cols_c = ["designation", "full_name", "group", "class", "pha", "H", "M1", "q", "e", "i", "a", "condition_code", "n_obs_used", "disc_date_best",
          "disc_date_source", "mpc_disc_site", "mpc_discoverer", "neowise_discovery", "earliest_known_obs", "last_obs", "already_precovered",
          "precovery_gain_days", "best_w2_est", "best_w2_date", "years_best_before_disc", "fast_mover_risk", "days_w2_lt_15p5_predisc", "best_V_predisc_est", "wise_best_w2", "neowise_best_w2",
          "wise_best_mag", "neowise_best_mag", "neowise_best_r", "neowise_best_delta", "neowise_days_in_elong", "rank_score", "spkid"]
save(pc[cols_c], "c_neowise_practice_cases",
     "NEOs and comets (q<5 au) discovered 2010-02-01..2024-08-31 (date from MPC NumberedMPs if numbered, else designation half-month start). "
     "Windows: WISE 2010-01-07..2011-02-01 and NEOWISE-R 2013-12-13..2024-08-08, ending 0.5 d before discovery. best_w2_est = brightest NEATM-lite "
     "W2 (Vega) thermal estimate (pV 0.14, eta 1.4; ESTIMATED, ~1 mag) at solar elongation 88-115 deg; days_w2_lt_15p5 = pre-discovery days brighter "
     "than W2 15.5. earliest_known_obs = SBDB first_obs; already_precovered = first_obs more than 5 d before discovery (answer key exists). "
     "Comet rank uses total mag minus 4 as a placeholder (no thermal model). rank_score = W2 - 0.3 log10(1+days) + 1 fast_mover(Delta<0.02) + 0.5 if best >2 yr before discovery (two-body drift); lower is better.")

# ---------------------------------------------------------------- special lists
pha = neo[neo["pha"] == "Y"].copy(); pha["sentry"] = pha["pdes"].isin(sentry_des)
save(pha, "special_phas", "All PHAs in SBDB (pha=Y) with full orbit, uncertainty and arc fields; sentry = on the Sentry risk list.")
sentry.to_csv(OUT / "special_sentry_summary.csv", index=False); DOCS["special_sentry_summary"] = "JPL Sentry summary (all objects with possible impacts), raw API fields."
sv = sentry.merge(neo[["pdes", "condition_code", "data_arc", "first_obs", "last_obs", "n_obs_used", "H", "q", "e", "i", "a", "moid"]], left_on="des", right_on="pdes", how="left")
for c in ["ip", "ps_cum", "ps_max", "h", "diameter"]: sv[c] = pd.to_numeric(sv[c], errors="coerce")
sv["years_since_last_obs"] = (NOW - sv["last_obs_jd"].astype(float)) / 365.25
save(sv.sort_values("ps_cum", ascending=False), "special_sentry_with_orbits", "Sentry summary joined to SBDB orbit quality; sorted by cumulative Palermo scale.")
isd = []
for p in sorted(glob.glob(str(R / "special/interstellar_*.json"))):
    j = json.load(open(p)); o = j.get("object", {}); orb = j.get("orbit", {})
    el = {e["name"]: e["value"] for e in orb.get("elements", [])}
    isd.append({"designation": o.get("des"), "full_name": o.get("fullname"), "first_obs": orb.get("first_obs"), "last_obs": orb.get("last_obs"),
                "n_obs_used": orb.get("n_obs_used"), "condition_code": orb.get("condition_code"), "e": el.get("e"), "q": el.get("q"), "i": el.get("i"),
                "tp": el.get("tp"), "discovery": json.dumps(j.get("discovery", {}))[:500]})
save(pd.DataFrame(isd), "special_interstellar", "1I/2I/3I SBDB records (full JSON with covariance in raw/special/).")
aa = com[(com["t_jup"] > 3.08) & (com["a"] < 5.2) & (com["a"] > 0)].copy()
aa["active_asteroid_type"] = np.where(aa["q"] < 1.3, "NEO-orbit comet with Tj>3.08", "main-belt comet / active asteroid (Tj>3.08, a<5.2)")
save(aa, "special_active_asteroids_from_sbdb",
     "Comets in SBDB with asteroid-like orbits (Tisserand T_J>3.08 and a<5.2 au; Jewitt 2012 criterion), i.e. main-belt comets and other active "
     "asteroids that carry comet designations. Active asteroids known only by asteroid designation (e.g. 3200 Phaethon, 6478 Gault, 596 Scheila) "
     "are added by hand in special_active_asteroids_known.csv.")
known_aa = ["3200", "6478", "596", "493", "62412", "101955", "2201", "1", "7968", "118401", "300163", "3552", "162173", "4015", "60558", "2060",
            "174P", "133P", "176P", "238P", "259P", "288P", "311P", "313P", "324P", "331P", "354P", "358P", "426P", "427P", "432P", "433P", "435P", "456P", "457P", "483P"]
pd.DataFrame({"designation": known_aa}).to_csv(OUT / "special_active_asteroids_known.csv", index=False)
DOCS["special_active_asteroids_known"] = "Hand list of well-known active asteroids by designation (literature: Jewitt 2012, Hsieh 2017, Chandler et al. 2024); B1 should resolve each in SBDB."
rc = com[(com["tp"].between(NOW - 365, NOW + 365)) & ((com["M1"] < 13) | (com["first_obs"] >= "2025-04-01"))].copy()
rc["tp_cal"] = rc["tp_cal"].astype(str)
save(rc.sort_values("M1"), "special_active_comets_near_perihelion",
     "Comets with perihelion within +-1 yr of 2026-11-15 and M1<13 (intrinsically bright = high activity proxy) or new since 2025-04; sorted by M1.")

# ---------------------------------------------------------------- live tables
sc = json.load(open(sorted(glob.glob(str(R / "scout/scout_list_*.json")))[-1]))
scdf = pd.DataFrame(sc["data"])
save(scdf, "live_scout", f"JPL Scout list snapshot (signature {sc.get('signature')}). unc = 1-sigma plane-of-sky uncertainty (arcmin); uncP1 = same +1 day; "
                         "scores are percent. Per-object detail JSON in raw/scout/detail/.")
nc = pd.DataFrame(json.load(open(sorted(glob.glob(str(R / "neocp/neocp_*.json")))[-1])))
save(nc, "live_neocp", "MPC NEO Confirmation Page snapshot (neocp.json): temp designation, score, discovery date, RA/Dec, V, nObs, arc, H, days not seen.")
cads = []
for p in sorted(glob.glob(str(R / "cad/cad_2025-2027_*.json"))):
    j = json.load(open(p)); cads.append(pd.DataFrame(j.get("data", []), columns=j.get("fields")))
cad = pd.concat(cads)
for c in ["dist", "dist_min", "dist_max", "v_rel", "v_inf", "h", "diameter"]: cad[c] = pd.to_numeric(cad[c], errors="coerce")
cad["dist_ld"] = cad["dist"] * 389.17
cad["fullname"] = cad["fullname"].str.strip()
save(cad.sort_values("cd"), "live_cad_2025_2027", "CNEOS close approaches to Earth 2025-01-01..2027-12-31 within 0.2 au (NEO asteroids + comets). dist in au, dist_ld lunar distances.")

json.dump(DOCS, open(OUT / "column_docs.json", "w"), indent=1)
print("done in", round(time.time() - t0), "s")
