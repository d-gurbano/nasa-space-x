"""A1 - per-object MPC observation pull (get-obs API allows 1 designation per call) to read the
discovery observation (obs80 column 13 '*'), discovery station, date and magnitude, and first/last observation.
Input: data/01-targets/tmp/discobs_targets.txt (one designation per line). Resumable.
Output: raw/mpc_obs/obs80_<batch>.txt (all obs, concatenated, '#OBJ <desig>' header lines)
        clean/discovery_obs.csv
Usage: python code/A1/fetch_disc_obs.py [max_n]
"""
import sys, time, json, csv, pathlib, requests
from common import D, UA

URL = "https://data.minorplanetcenter.net/api/get-obs"
targets = [l.strip() for l in open(D / "tmp/discobs_targets.txt") if l.strip()]
maxn = int(sys.argv[1]) if len(sys.argv) > 1 else len(targets)
out_csv = D / "clean/discovery_obs.csv"
done = set()
if out_csv.exists():
    done = {r["desig"] for r in csv.DictReader(open(out_csv))}
obsdir = D / "raw/mpc_obs"; obsdir.mkdir(parents=True, exist_ok=True)
obsfile = open(obsdir / "obs80_new_objects.txt", "a")
new = not out_csv.exists()
fo = open(out_csv, "a", newline="")
w = csv.writer(fo)
if new:
    w.writerow(["desig", "n_obs_mpc", "disc_date_utc", "disc_station", "disc_mag", "disc_band", "first_obs_utc", "first_station",
                "last_obs_utc", "n_stations", "status"])


def parse_date(line):
    # obs80 cols 16-32: YYYY MM DD.ddddd
    s = line[15:32]
    return s.strip()


n = 0
for t in targets:
    if t in done:
        continue
    if n >= maxn:
        break
    n += 1
    status, lines = "ok", []
    for k in range(5):
        try:
            r = requests.get(URL, json={"desigs": [t], "output_format": ["OBS80"]}, timeout=120, headers=UA)
            if r.status_code == 200:
                d = r.json()
                rec = d[0] if isinstance(d, list) else d
                lines = rec.get("OBS80", "").splitlines() if isinstance(rec, dict) else []
                break
            status = f"http{r.status_code}"
            if r.status_code in (400, 404, 501):
                break
        except Exception as ex:  # noqa
            status = "err"
        time.sleep(3 * 2 ** k)
    opt = [l for l in lines if len(l) >= 80 and l[14] not in "srvRV"]  # skip 2nd lines of satellite/roving/radar
    disc = [l for l in opt if l[12] == "*"]
    if not lines:
        w.writerow([t, 0, "", "", "", "", "", "", "", 0, status if status != "ok" else "noobs"])
    else:
        obsfile.write(f"#OBJ {t}\n" + "\n".join(lines) + "\n")
        dl = disc[0] if disc else None
        srt = sorted(opt, key=parse_date)
        w.writerow([t, len(opt), parse_date(dl) if dl else "", dl[77:80] if dl else "", dl[65:70].strip() if dl else "", dl[70] if dl else "",
                    parse_date(srt[0]) if srt else "", srt[0][77:80] if srt else "", parse_date(srt[-1]) if srt else "",
                    len({l[77:80] for l in opt}), status if disc else "no_disc_asterisk"])
    fo.flush(); obsfile.flush()
    if n % 50 == 0:
        print(n, t, flush=True)
    time.sleep(0.7)
print("done", n)
