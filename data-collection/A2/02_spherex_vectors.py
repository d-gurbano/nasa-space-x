"""A2: download SPHEREx (-163182) geocentric J2000 equatorial state vectors from JPL Horizons
(source: concatenated Space-Track TLEs, per Horizons header), 5-min step, mission start to +30 d.
Output: data/02-orbits/horizons/spherex_vectors_geo_5min.parquet (JD TDB, x,y,z km, vx,vy,vz km/s)."""
import requests, time, io, pandas as pd, numpy as np, os, datetime as dt
out = os.path.join(os.path.dirname(__file__), '../../data/02-orbits/horizons')
os.makedirs(out, exist_ok=True)
start = dt.date(2025, 3, 13); stop = dt.date(2026, 12, 13)
frames = []
d = start
while d < stop:
    e = min(d + dt.timedelta(days=50), stop)
    p = dict(format='text', COMMAND="'-163182'", EPHEM_TYPE='VECTORS', CENTER="'500@399'", REF_PLANE='FRAME',
             REF_SYSTEM='ICRF', START_TIME=f"'{d} 00:00'", STOP_TIME=f"'{e} 00:00'", STEP_SIZE="'5 m'",
             VEC_TABLE='2', CSV_FORMAT='YES', OUT_UNITS='KM-S', VEC_LABELS='NO', TIME_TYPE='TDB')
    for k in range(5):
        try:
            r = requests.get('https://ssd.jpl.nasa.gov/api/horizons.api', params=p, timeout=300)
            if r.status_code == 200 and '$$SOE' in r.text: break
        except Exception as ex: print('retry', ex)
        time.sleep(10 * (k + 1))
    t = r.text; body = t[t.find('$$SOE') + 5:t.find('$$EOE')]
    lines=[l for l in body.strip().splitlines() if l.count(',')>=7]
    df = pd.read_csv(io.StringIO('\n'.join(lines)), header=None).iloc[:, [0, 2, 3, 4, 5, 6, 7]]
    df.columns = ['jd_tdb', 'x', 'y', 'z', 'vx', 'vy', 'vz']
    frames.append(df); print(d, e, len(df), flush=True)
    d = e; time.sleep(3)
v = pd.concat(frames).drop_duplicates('jd_tdb').sort_values('jd_tdb').reset_index(drop=True)
v.to_parquet(os.path.join(out, 'spherex_vectors_geo_5min.parquet'))
with open(os.path.join(out, 'spherex_horizons_header.txt'), 'w') as f: f.write(t[:t.find('$$SOE')])
print('rows', len(v), v.jd_tdb.min(), v.jd_tdb.max())
