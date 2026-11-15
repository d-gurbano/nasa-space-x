"""A8 (AI training data) - build per-patch SPHEREx time series for "Expected Sky".

Steps (all resumable):
  python code/A8/build_patches.py index      # SIA2 frame lists per cluster -> data/08-ai-training/index/
  python code/A8/build_patches.py select     # stratified frame selection -> index/frames_selected.parquet
  python code/A8/build_patches.py fetch [max_minutes] [threads]   # S3 range reads -> raw/<cluster>/<frame>.npz
  python code/A8/build_patches.py consolidate  # raw per-frame -> patches/<patch>.npz + index/patch_epochs.parquet

Geometry: each cluster = 3x3 sky patches on a common north-up TAN grid (6.15"/px), patch centres 64 px apart.
For each frame we read ONE full-width row block (IMAGE, VARIANCE, ZODI, FLAGS rows, the ePSF zone rows,
WCS-WAVE) that covers all patches of the cluster, then cut a 96x96 native-pixel cutout per patch and also
resample it to a 64x64 north-up grid shared by all epochs of that patch.
Reader is the pilot HTTPS range reader (code/A0/rewind.py), extended to row blocks.
"""
from __future__ import annotations
import sys, os, io, json, time, shutil, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np, pandas as pd
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import astropy.units as u
from scipy.ndimage import map_coordinates

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(ROOT, 'code/A0'))
import rewind as R  # noqa: E402

OUT = os.path.join(ROOT, 'data/08-ai-training')
RAW = os.path.join(OUT, 'raw')
# Dataset version: v1 (frozen first training set) uses index/ and patches/; v2 (larger, built later from all
# raw frames) uses index/v2/ and patches_v2/. Select with env A8_VERSION=v2. Fetch/select always use index/.
VERSION = os.environ.get('A8_VERSION', 'v1')
IDX_BASE = os.path.join(OUT, 'index')
IDX = IDX_BASE if VERSION == 'v1' else os.path.join(IDX_BASE, VERSION)
PAT = os.path.join(OUT, 'patches' if VERSION == 'v1' else f'patches_{VERSION}')
FRAMELIST = os.environ.get('A8_FRAMELIST')   # optional text file of frame_ids to consolidate (v1 freeze)
PIX = 6.15            # arcsec/px (ES Table 2)
NP_AL = 64            # aligned patch size (px)
NP_NAT = 96           # native cutout size (px), covers a rotated 64x64 grid + margin
SPACING = 64          # patch centre spacing (aligned px)
GRID = 3              # 3x3 patches per cluster
ZSTEP = 16            # ZODI row sampling step (smooth model, interpolated)


def ecl2eq(lam, beta):
    c = SkyCoord(lon=lam * u.deg, lat=beta * u.deg, frame='barycentrictrueecliptic')
    e = c.icrs
    return float(e.ra.deg), float(e.dec.deg)


# role: pole (deep fields, many epochs) / ecliptic / midlat (controls, fewer epochs)
CLUSTERS = [
    dict(name='NEP-A', ra=270.0, dec=66.56, role='pole', n=240),
    dict(name='NEP-B', ra=268.8, dec=66.05, role='pole', n=120, parent='NEP-A'),
    dict(name='NEP-C', ra=271.3, dec=67.05, role='pole', n=120, parent='NEP-A'),
    dict(name='NEP-D', ra=268.7, dec=67.10, role='pole', n=60, parent='NEP-A'),
    dict(name='SEP-A', ra=90.0, dec=-66.56, role='pole', n=180),
    dict(name='SEP-B', ra=91.3, dec=-66.05, role='pole', n=60, parent='SEP-A'),
]
for nm, lam, beta, role in [('ECL-1', 180.0, 0.0, 'ecliptic'), ('ECL-2', 45.0, 0.0, 'ecliptic'),
                            ('MID-1', 160.0, 40.0, 'midlat'), ('MID-2', 300.0, -40.0, 'midlat')]:
    ra, dec = ecl2eq(lam, beta)
    CLUSTERS.append(dict(name=nm, ra=round(ra, 4), dec=round(dec, 4), role=role, n=(60 if role == 'ecliptic' else 48), elon=lam, elat=beta))
COLLS = ['spherex_qr3_deep', 'spherex_dr1_deep', 'spherex_qr3', 'spherex_dr1']


def poly_contains(s_region, ra, dec):
    """Point-in-polygon on a tangent plane centred on (ra, dec) for an ObsCore 'POLYGON ICRS ...' string."""
    v = np.array(s_region.split()[2:], float).reshape(-1, 2)
    r0, d0 = np.radians(ra), np.radians(dec)
    r, d = np.radians(v[:, 0]), np.radians(v[:, 1])
    cosc = np.sin(d0) * np.sin(d) + np.cos(d0) * np.cos(d) * np.cos(r - r0)
    x = np.cos(d) * np.sin(r - r0) / cosc
    y = (np.cos(d0) * np.sin(d) - np.sin(d0) * np.cos(d) * np.cos(r - r0)) / cosc
    from matplotlib.path import Path
    return bool(Path(np.c_[x, y]).contains_point((0.0, 0.0)))


def cluster_wcs(c):
    w = WCS(naxis=2)
    w.wcs.ctype = ['RA---TAN', 'DEC--TAN']
    w.wcs.crval = [c['ra'], c['dec']]
    w.wcs.crpix = [1, 1]   # 0-based pixel (0,0) = cluster centre
    w.wcs.cdelt = [-PIX / 3600, PIX / 3600]
    return w


def patch_list(c):
    """Patch centres and aligned-grid world coordinates for one cluster."""
    w = cluster_wcs(c)
    out = []
    h = (NP_AL - 1) / 2
    for j in range(GRID):
        for i in range(GRID):
            px, py = (i - 1) * SPACING, (j - 1) * SPACING
            ra, dec = w.all_pix2world([[px, py]], 0)[0]
            yy, xx = np.mgrid[0:NP_AL, 0:NP_AL]
            gra, gdec = w.all_pix2world(xx - h + px, yy - h + py, 0)
            out.append(dict(patch=f"{c['name']}_{j}{i}", cluster=c['name'], ra=float(ra), dec=float(dec),
                            gra=gra, gdec=gdec))
    return out


# ------------------------------------------------------------------ index + select
def cmd_index():
    os.makedirs(IDX, exist_ok=True)
    rows = []
    for c in CLUSTERS:
        for coll in COLLS:
            f = os.path.join(IDX_BASE, f"sia_{c['name']}_{coll}.parquet")
            if os.path.exists(f):
                df = pd.read_parquet(f)
            elif c.get('parent'):
                # neighbour cluster: frames of the parent query whose footprint polygon contains this centre
                # (saves heavy SIA2 deep queries; frames covering the neighbour but not the parent are not listed)
                dp = pd.read_parquet(os.path.join(IDX_BASE, f"sia_{c['parent']}_{coll}.parquet"))
                df = dp[[poly_contains(r, c['ra'], c['dec']) for r in dp.s_region]].reset_index(drop=True)
                df.to_parquet(f)
            else:
                # deep collections at the poles exceed 20000 rows: split by time
                parts = []
                wins = [(60700, 60900), (60900, 61050), (61050, 61200), (61200, 61400)] if 'deep' in coll and c['role'] == 'pole' else [None]
                for wdw in wins:
                    for k in range(4):
                        try:
                            parts.append(R.sia2_query(c['ra'], c['dec'], coll, radius_deg=0.001, time_mjd=wdw, maxrec=30000))
                            break
                        except Exception as e:
                            print('retry', c['name'], coll, wdw, e, flush=True)
                            time.sleep(5 * (k + 1))
                    time.sleep(1)
                df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
                df.to_parquet(f)
            print(c['name'], coll, len(df), flush=True)
            if len(df):
                d = df[['obs_id', 'energy_bandpassname', 't_min', 'cloud_access', 'em_min', 'em_max', 'obs_collection']].copy()
                d['collection'] = coll
                d['cluster'] = c['name']
                rows.append(d)
    allf = pd.concat(rows, ignore_index=True)
    allf['key'] = allf.cloud_access.map(lambda s: json.loads(s)['aws']['key'])
    allf['det'] = allf.energy_bandpassname.str[-1].astype(int)
    allf['release'] = allf.key.str.split('/').str[0]
    allf = allf.drop(columns=['cloud_access']).drop_duplicates(['cluster', 'key'])
    allf.to_parquet(os.path.join(IDX_BASE, 'frames_available.parquet'))
    print(allf.groupby(['cluster', 'collection']).size())


def cmd_select(mult=1.0, out_name='frames_selected.parquet'):
    allf = pd.read_parquet(os.path.join(IDX_BASE, 'frames_available.parquet'))
    # one exposure can appear in two releases (QR vs DR reprocessing): keep the newest release per obs_id+det
    allf = allf.sort_values('release').drop_duplicates(['cluster', 'obs_id', 'det'], keep='last')
    sel = []
    for c in CLUSTERS:
        d = allf[allf.cluster == c['name']].sort_values('t_min')
        dets = sorted(d.det.unique())
        per = int(np.ceil(c['n'] * mult / max(len(dets), 1)))
        for det in dets:
            dd = d[d.det == det]
            if len(dd) <= per:
                sel.append(dd)
            else:  # evenly spaced in time order (covers the whole baseline, all wavelengths over time)
                ii = np.unique(np.linspace(0, len(dd) - 1, per).round().astype(int))
                sel.append(dd.iloc[ii])
    s = pd.concat(sel, ignore_index=True)
    s['frame_id'] = s.key.map(lambda k: os.path.basename(k).replace('.fits', ''))
    # keep frames already fetched in an earlier (larger) selection
    allf['frame_id'] = allf.key.map(lambda k: os.path.basename(k).replace('.fits', ''))
    have = {(c, f[:-4]) for c in os.listdir(RAW) if os.path.isdir(os.path.join(RAW, c))
            for f in os.listdir(os.path.join(RAW, c)) if f.endswith('.npz') and not f.endswith('.tmp.npz')} if os.path.isdir(RAW) else set()
    extra = allf[[(c, f) in have for c, f in zip(allf.cluster, allf.frame_id)]]
    s = pd.concat([s, extra], ignore_index=True).drop_duplicates(['cluster', 'frame_id'])
    s.to_parquet(os.path.join(IDX_BASE, out_name))
    print(s.groupby(['cluster', 'det']).size().unstack(fill_value=0))
    print('total frames', len(s))


# ------------------------------------------------------------------ fetch
def wave_grid(wave_row, xs, ys):
    """Per-pixel central wavelength and bandwidth (um) from WCS-WAVE, full-frame 0-based coords."""
    X = np.asarray(wave_row['X']).ravel().astype(float)
    Y = np.asarray(wave_row['Y']).ravel().astype(float)
    V = np.asarray(wave_row['VALUES']).reshape(len(Y), len(X), 2)
    fx = np.interp(xs + 1.0, X, np.arange(len(X)))
    fy = np.interp(ys + 1.0, Y, np.arange(len(Y)))
    lam = map_coordinates(V[:, :, 0], [fy, fx], order=1)
    bw = map_coordinates(V[:, :, 1], [fy, fx], order=1)
    return lam.astype(np.float32), bw.astype(np.float32)


HDR_KEYS = ['DETECTOR', 'OBSID', 'EXPIDN', 'MJD-BEG', 'MJD-AVG', 'MJD-END', 'XPOSURE', 'TELAPSE',
            'X_SC', 'Y_SC', 'Z_SC', 'VX_SC', 'VY_SC', 'VZ_SC', 'XYZ_SC_SYSTEM', 'SPS_FLAGS', 'SPS_TARGET',
            'SPS_ELON', 'SPS_ELAT', 'SPS_EPA', 'L1DQAFLG', 'L2DQAFLG', 'FINAST', 'OMEGA_MEDIAN', 'OMEGA_STDDEV',
            'PSF_FWHM', 'PXSRCMSK', 'L2 N_PERSIST', 'L2 N_OUTLIER', 'L2 SATSTRKS', 'NON_SURVEY', 'CRVAL1', 'CRVAL2',
            'PC1_1', 'PC1_2', 'PC2_1', 'PC2_2', 'HE_AG_AMPL', 'AURORA_CORR']


def fetch_frame(fr, plist):
    uri = 'ibe/data/spherex/' + fr.key
    url, lay, stats = R.l2_layout(uri)
    hdr = lay['IMAGE'][0]
    prim = lay['PRIMARY'][0]
    w = R._celestial_wcs(hdr)
    NX = hdr['NAXIS1']
    hn = NP_NAT // 2
    cen = w.all_world2pix([[p['ra'], p['dec']] for p in plist], 0)
    ok = [(hn <= x < 2040 - hn) and (hn <= y < 2040 - hn) for x, y in cen]
    if not any(ok):
        return None, dict(reason='no patch on detector')
    xi = np.round(cen[:, 0]).astype(int)
    yi = np.round(cen[:, 1]).astype(int)
    use = np.where(ok)[0]
    Y0 = int(min(yi[use]) - hn)
    Y1 = int(max(yi[use]) - hn + NP_NAT)
    X0 = int(min(xi[use]) - hn)
    X1 = int(max(xi[use]) - hn + NP_NAT)

    def rows(name):
        h, _, dloc, _ = lay[name]
        raw = R._range(url, dloc + Y0 * NX * 4, (Y1 - Y0) * NX * 4)
        stats['bytes'] += len(raw)
        stats['requests'] += 1
        return np.frombuffer(raw, dtype='>f4').reshape(Y1 - Y0, NX)[:, X0:X1].astype(np.float32)
    img, var = rows('IMAGE'), rows('VARIANCE')
    # ZODI is a smooth model: read every ZSTEP-th full row and interpolate linearly in y
    # (tested: max error 0.08% of zodi = 0.5% of the pixel noise, MEASURED on an NEP D4 frame)
    zh, _, zloc, _ = lay['ZODI']
    yc = np.unique(np.r_[np.arange(Y0, Y1, ZSTEP), Y1 - 1])
    zr = []
    for yy_ in yc:
        raw = R._range(url, zloc + int(yy_) * NX * 4, NX * 4)
        stats['bytes'] += len(raw); stats['requests'] += 1
        zr.append(np.frombuffer(raw, dtype='>f4')[X0:X1].astype(np.float32))
    zr = np.array(zr)
    yfull = np.arange(Y0, Y1)
    zod = np.empty((Y1 - Y0, X1 - X0), np.float32)
    for j in range(X1 - X0):
        zod[:, j] = np.interp(yfull, yc, zr[:, j])
    flg = R._read_flags_rows(url, lay['FLAGS'], Y0, Y1, stats)[:, X0:X1].astype(np.int32)
    # ePSF: zone grid from row 0, then the contiguous block of zone rows overlapping the block
    eh, eoff, edat, elen = lay['EPSF']
    rowlen = eh['NAXIS1']
    dt = R._epsf_dtype(eh)
    rec0 = np.frombuffer(R._range(url, edat, rowlen), dtype=dt)[0]
    xw, yw = float(rec0['XWIDTH']), float(rec0['YWIDTH'])
    nzx, nzy = int(round(2040 / xw)), int(round(2040 / yw))
    # only the zones touched by the patch cutouts: one contiguous read per zone row
    zset = set()
    for k in use:
        ys_, xs_ = np.mgrid[yi[k] - hn:yi[k] - hn + NP_NAT, xi[k] - hn:xi[k] - hn + NP_NAT]
        zset |= set(np.unique(np.minimum(ys_ // yw, nzy - 1) * nzx + np.minimum(xs_ // xw, nzx - 1)).astype(int).tolist())
    parts, zids = [], []
    for iyz in sorted({q // nzx for q in zset}):
        xs_z = [q % nzx for q in zset if q // nzx == iyz]
        za, zb = iyz * nzx + min(xs_z), iyz * nzx + max(xs_z) + 1
        parts.append(np.frombuffer(R._range(url, edat + za * rowlen, (zb - za) * rowlen), dtype=dt))
        zids += list(range(za, zb))
        stats['bytes'] += (zb - za) * rowlen; stats['requests'] += 1
    ezr = np.concatenate(parts)
    stats['bytes'] += rowlen; stats['requests'] += 1
    whh, woff, wdat, wlen = lay['WCS-WAVE']
    rawW = R._range(url, woff, (wdat - woff) + wlen)
    stats['requests'] += 1
    stats['bytes'] += len(rawW)
    wave = fits.open(io.BytesIO(fits.PrimaryHDU().header.tostring().encode() + rawW))[1].data[0]
    # per-pixel zone index map (full-frame zone number = iy*nzx+ix) for the block
    yy, xx = np.mgrid[Y0:Y1, X0:X1]
    zmap = (np.minimum(yy // yw, nzy - 1) * nzx + np.minimum(xx // xw, nzx - 1)).astype(np.int16)
    lam, bw = wave_grid(wave, xx.ravel().astype(float), yy.ravel().astype(float))
    lam, bw = lam.reshape(yy.shape), bw.reshape(yy.shape)
    out = {}
    pmeta = []
    for k in use:
        p = plist[k]
        sx, sy = xi[k] - hn - X0, yi[k] - hn - Y0
        sl = (slice(sy, sy + NP_NAT), slice(sx, sx + NP_NAT))
        tag = p['patch']
        out[f'{tag}/img'] = img[sl]
        out[f'{tag}/var'] = var[sl]
        out[f'{tag}/zodi'] = zod[sl]
        out[f'{tag}/flags'] = flg[sl]
        out[f'{tag}/lam'] = lam[sl]
        out[f'{tag}/bw'] = bw[sl].astype(np.float16)
        out[f'{tag}/zone'] = zmap[sl]
        # aligned 64x64 north-up grid: world -> this frame's pixels -> sample the native cutout
        gx, gy = w.all_world2pix(p['gra'].ravel(), p['gdec'].ravel(), 0)
        cx, cy = gx - (xi[k] - hn), gy - (yi[k] - hn)
        co = [cy, cx]
        sh = p['gra'].shape
        out[f'{tag}/al_img'] = map_coordinates(img[sl], co, order=1, cval=np.nan).reshape(sh).astype(np.float32)
        out[f'{tag}/al_var'] = map_coordinates(var[sl], co, order=1, cval=np.nan).reshape(sh).astype(np.float32)
        out[f'{tag}/al_zodi'] = map_coordinates(zod[sl], co, order=1, cval=np.nan).reshape(sh).astype(np.float32)
        out[f'{tag}/al_lam'] = map_coordinates(lam[sl], co, order=1, cval=np.nan).reshape(sh).astype(np.float32)
        out[f'{tag}/al_flags'] = flg[sl][np.clip(np.round(cy).astype(int), 0, NP_NAT - 1),
                                        np.clip(np.round(cx).astype(int), 0, NP_NAT - 1)].reshape(sh).astype(np.int32)
        out[f'{tag}/al_x'] = cx.reshape(sh).astype(np.float32)   # native-cutout coords of each aligned pixel
        out[f'{tag}/al_y'] = cy.reshape(sh).astype(np.float32)
        pmeta.append(dict(patch=tag, x0_full=int(xi[k] - hn), y0_full=int(yi[k] - hn),
                          xc_full=float(cen[k, 0]), yc_full=float(cen[k, 1]),
                          lam_center_um=float(lam[sl][hn, hn]), bw_center_um=float(bw[sl][hn, hn]),
                          zone_center=int(zmap[sl][hn, hn]), zodi_median=float(np.nanmedian(zod[sl]))))
    out['epsf_zone_index'] = np.array(zids, dtype=np.int16)
    out['epsf'] = np.asarray(ezr['EPSF'], np.float32).reshape(-1, 33, 33)
    out['epsf_cwave'] = np.asarray(ezr['CWAVE'], np.float32)
    out['epsf_cband'] = np.asarray(ezr['CBAND'], np.float32)
    out['epsf_xcenter'] = np.asarray(ezr['XCENTER'], np.float32)
    out['epsf_ycenter'] = np.asarray(ezr['YCENTER'], np.float32)
    out['epsf_neff'] = np.asarray(ezr['NEFF_MEAN'], np.float32)
    wcs_hdr = w.to_header(relax=True).tostring()
    meta = {k: (hdr.get(k) if not isinstance(hdr.get(k), bool) else int(hdr.get(k))) for k in HDR_KEYS}
    meta.update(frame_id=fr.frame_id, key=fr.key, cluster=fr.cluster, collection=fr.collection, release=fr.release,
                det=int(fr.det), pipeline_version=prim.get('VERSION'), n_patches=len(use),
                bytes_read=stats['bytes'], requests=stats['requests'], block=(Y0, Y1, X0, X1))
    out['meta_json'] = np.frombuffer(json.dumps(dict(frame=meta, patches=pmeta), default=str).encode(), dtype=np.uint8)
    out['wcs_header'] = np.frombuffer(wcs_hdr.encode(), dtype=np.uint8)
    out['image_header'] = np.frombuffer(hdr.tostring().encode(), dtype=np.uint8)
    return out, meta


STOP = os.path.join(OUT, 'STOP_FETCH')    # touch this file to stop a running fetch cleanly
BUDGET_GB = 30.0                            # fetch stops when data/08-ai-training reaches this (leaves ~15 GB of the 45 GB budget for consolidated v2 patches + baselines)


def folder_gb():
    t = 0
    for dp, dn, fn in os.walk(OUT):
        for f in fn:
            try:
                t += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    return t / 1e9


def disk_free_gb():
    st = shutil.disk_usage(ROOT)
    return st.free / 1e9


def cmd_fetch(max_minutes=60.0, threads=8, sel='frames_selected.parquet'):
    s = pd.read_parquet(os.path.join(IDX_BASE, sel))
    plists = {c['name']: patch_list(c) for c in CLUSTERS}
    todo = []
    for fr in s.itertuples():
        f = os.path.join(RAW, fr.cluster, fr.frame_id + '.npz')
        if not os.path.exists(f) and not os.path.exists(f + '.skip'):
            todo.append(fr)
    # interleave clusters so a time stop leaves every cluster partially filled
    todo.sort(key=lambda r: (hash(r.frame_id) % 1000))
    print('todo', len(todo), 'free GB', round(disk_free_gb(), 1), flush=True)
    t0 = time.time()
    lock = threading.Lock()
    done = [0, 0, 0]

    used = [folder_gb()]
    print('folder GB', round(used[0], 2), 'budget', BUDGET_GB, flush=True)

    def work(fr):
        if time.time() - t0 > max_minutes * 60:
            return 'time'
        if os.path.exists(STOP):
            return 'stop'
        if disk_free_gb() < 21:
            return 'disk'
        if used[0] + done[2] * 0.45 / 1e9 > BUDGET_GB:   # stored ~0.45 x bytes read (+ derived products)
            return 'budget'
        os.makedirs(os.path.join(RAW, fr.cluster), exist_ok=True)
        f = os.path.join(RAW, fr.cluster, fr.frame_id + '.npz')
        if os.path.exists(f):
            return 'exists'
        for k in range(3):
            try:
                out, meta = fetch_frame(fr, plists[fr.cluster])
                break
            except Exception as e:
                err = repr(e)
                time.sleep(3 * (k + 1))
        else:
            with open(f + '.err', 'w') as fh:
                fh.write(err)
            return 'err'
        if out is None:
            open(f + '.skip', 'w').write(meta['reason'])
            return 'skip'
        np.savez(f + '.tmp.npz', **out)
        os.replace(f + '.tmp.npz', f)
        with lock:
            done[2] += meta['bytes_read']
        return 'ok'
    with ThreadPoolExecutor(threads) as ex:
        futs = [ex.submit(work, fr) for fr in todo]
        n = 0
        stat = {}
        for fu in as_completed(futs):
            r = fu.result()
            stat[r] = stat.get(r, 0) + 1
            n += 1
            if n % 25 == 0:
                el = time.time() - t0
                print(f'{n}/{len(todo)} {stat} {el/60:.1f} min, {done[2]/1e6:.0f} MB read, {done[2]/1e6/el:.2f} MB/s, free {disk_free_gb():.1f} GB', flush=True)
    print('final', stat, f'{(time.time()-t0)/60:.1f} min', flush=True)


# ------------------------------------------------------------------ consolidate
def cmd_consolidate():
    """raw per-frame npz -> one npz per patch (epochs sorted by MJD-AVG) + Parquet indexes. Per cluster to bound RAM."""
    os.makedirs(PAT, exist_ok=True)
    os.makedirs(IDX, exist_ok=True)
    keep = set(open(FRAMELIST).read().split()) if FRAMELIST else None
    frames, pe = [], []
    for c in CLUSTERS:
        d = os.path.join(RAW, c['name'])
        if not os.path.isdir(d):
            continue
        store = {}
        for fn in sorted(os.listdir(d)):
            if not fn.endswith('.npz') or fn.endswith('.tmp.npz'):
                continue
            if keep is not None and fn[:-4] not in keep:
                continue
            try:
                z = np.load(os.path.join(d, fn))
                m = json.loads(bytes(z['meta_json']).decode())
            except Exception as e:
                print('bad', fn, e)
                continue
            fm = m['frame']
            fm['wcs_header'] = bytes(z['wcs_header']).decode()
            # first fetch code read ZODI rows exactly (15 requests per frame); later code samples every ZSTEP rows
            fm['zodi_exact'] = bool(int(fm.get('requests', 99)) <= 16)
            frames.append(fm)
            zi = z['epsf_zone_index']
            ep_all, cw_all = z['epsf'], z['epsf_cwave']
            for p in m['patches']:
                tag = p['patch']
                rec = {**p, 'frame_id': fm['frame_id'], 'cluster': fm['cluster'], 'det': fm['det'],
                       'mjd_avg': fm['MJD-AVG'], 'release': fm['release'], 'collection': fm['collection']}
                zones = np.unique(z[f'{tag}/zone'])
                rec['zones'] = ','.join(map(str, zones))
                arrs = {k.split('/', 1)[1]: z[k] for k in z.files if k.startswith(tag + '/')}
                eps = {int(q): ep_all[np.where(zi == q)[0][0]] for q in zones}
                cws = {int(q): float(cw_all[np.where(zi == q)[0][0]]) for q in zones}
                store.setdefault(tag, []).append((rec, arrs, eps, cws))
        for tag, lst in store.items():
            lst.sort(key=lambda t: t[0]['mjd_avg'])
            recs = [t[0] for t in lst]
            arrs = {k: np.stack([t[1][k] for t in lst]) for k in lst[0][1]}
            nz = max(len(t[2]) for t in lst)
            ep = np.zeros((len(lst), nz, 33, 33), np.float32)
            epz = np.full((len(lst), nz), -1, np.int16)
            epw = np.full((len(lst), nz), np.nan, np.float32)
            for i, t in enumerate(lst):
                for j, (q, a) in enumerate(sorted(t[2].items())):
                    ep[i, j], epz[i, j], epw[i, j] = a, q, t[3][q]
            arrs.update(epsf=ep, epsf_zone=epz, epsf_cwave=epw,
                        mjd_avg=np.array([r['mjd_avg'] for r in recs]),
                        det=np.array([r['det'] for r in recs], np.int8),
                        x0_full=np.array([r['x0_full'] for r in recs], np.int16),
                        y0_full=np.array([r['y0_full'] for r in recs], np.int16),
                        frame_id=np.array([r['frame_id'] for r in recs]))
            np.savez_compressed(os.path.join(PAT, tag + '.npz'), **arrs)
            for i, r in enumerate(recs):
                r['epoch_index'] = i
                pe.append(r)
        print(c['name'], 'patches', len(store), 'patch-epochs', sum(len(v) for v in store.values()), flush=True)
        del store
    fr = pd.DataFrame(frames)
    fr['block'] = fr['block'].astype(str)
    for col in fr.columns:
        if fr[col].dtype == object and col not in ('wcs_header',):
            fr[col] = fr[col].astype(str)
    fr.to_parquet(os.path.join(IDX, 'frames.parquet'))
    pdf = pd.DataFrame(pe)
    pdf.to_parquet(os.path.join(IDX, 'patch_epochs.parquet'))
    print('frames', len(fr), 'patch-epochs', len(pdf), 'patches', pdf.patch.nunique())


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'index':
        cmd_index()
    elif cmd == 'select':
        cmd_select()
    elif cmd == 'select_v2':
        cmd_select(float(sys.argv[2]), 'frames_selected_v2.parquet')
    elif cmd == 'fetch':
        cmd_fetch(float(sys.argv[2]) if len(sys.argv) > 2 else 60, int(sys.argv[3]) if len(sys.argv) > 3 else 8,
                  sys.argv[4] if len(sys.argv) > 4 else 'frames_selected.parquet')
    elif cmd == 'consolidate':
        cmd_consolidate()
