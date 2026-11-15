"""A2: JPL Horizons daily ephemerides AS SEEN FROM SPHEREx (500@-163182) for each candidate,
2025-03-14 to 2026-11-14, with RA/Dec 3-sigma uncertainty (quantity 36), V/T-mag, r, delta.
Out: data/02-orbits/horizons/ephem_spherex/<des>.csv  (one Horizons call per object, paced 2 s)."""
import requests, os, io, time, pandas as pd
root = os.path.join(os.path.dirname(__file__), '../../data/02-orbits'); od = f'{root}/horizons/ephem_spherex'; os.makedirs(od, exist_ok=True)
c = pd.read_csv(f'{root}/candidates_Y1.csv'); names = ['99942', '2024 YR4', '433', '3200', '1566'] + list(c.designation)
log = []
for n in names:
    fn = f"{od}/{n.replace('/', '_').replace(' ', '_')}.csv"
    if os.path.exists(fn): continue
    cmd = f"DES={n};CAP;NOFRAG" if '/' in n else (f"DES={n};" if ' ' in n else f"{n};")
    p = dict(format='text', COMMAND=f"'{cmd}'", EPHEM_TYPE='OBSERVER', CENTER="'500@-163182'", START_TIME="'2025-03-14'",
             STOP_TIME="'2026-11-14'", STEP_SIZE="'1 d'", QUANTITIES="'1,9,19,20,23,36'", CSV_FORMAT='YES', EXTRA_PREC='YES',
             ANG_FORMAT='DEG', CAL_FORMAT='BOTH', OBJ_DATA='NO', TIME_TYPE='UT')
    t = ''
    for k in range(4):
        try:
            r = requests.get('https://ssd.jpl.nasa.gov/api/horizons.api', params=p, timeout=180); t = r.text
            if '$$SOE' in t or 'No matches' in t or 'Cannot' in t: break
        except Exception as e: print('retry', n, e)
        time.sleep(8 * (k + 1))
    if '$$SOE' not in t:
        log.append(dict(designation=n, status='fail', note=t[-300:].replace('\n', ' '))); print(n, 'FAIL'); continue
    hdr = [h.strip() for h in t[:t.find('$$SOE')].strip().splitlines()[-2].split(',')]
    hdr = [h if h else f'_b{j}' for j, h in enumerate(hdr)]
    df = pd.read_csv(io.StringIO(t[t.find('$$SOE') + 5:t.find('$$EOE')]), header=None, names=hdr, index_col=False)
    df = df[[x for x in df.columns if not x.startswith('_b')]]
    df.to_csv(fn, index=False); log.append(dict(designation=n, status='ok', rows=len(df))); print(n, len(df), flush=True)
    time.sleep(2)
pd.DataFrame(log).to_csv(f'{od}/_log.csv', index=False)
