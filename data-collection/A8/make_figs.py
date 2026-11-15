"""A8 - preview figures and dataset statistics.
  python code/A8/make_figs.py   -> data/08-ai-training/figs/*.png, tables/dataset_stats.json
"""
import os, sys, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(ROOT, 'code/A8'))
import build_patches as B  # noqa: E402
import splits_baselines as SB  # noqa: E402

FIG = os.path.join(B.OUT, 'figs' if B.VERSION == 'v1' else f'figs_{B.VERSION}')
TAB = SB.TAB


def show(ax, a, title, lo=1, hi=99.5):
    v = a[np.isfinite(a)]
    if v.size == 0:
        ax.set_axis_off(); return
    vmin, vmax = np.percentile(v, [lo, hi])
    ax.imshow(a, origin='lower', cmap='gray', vmin=vmin, vmax=vmax)
    ax.set_title(title, fontsize=7)
    ax.set_xticks([]); ax.set_yticks([])


def patch_panel(patch, km, n=6):
    z = np.load(os.path.join(B.PAT, patch + '.npz'))
    sr = np.load(os.path.join(SB.BL, patch + '_staticref.npz'))
    a = z['al_img'] - z['al_zodi']
    have = np.where(np.isfinite(sr['ref']).mean((1, 2)) > 0.5)[0]
    ee = have[np.linspace(0, len(have) - 1, min(n, len(have))).astype(int)] if len(have) else np.arange(min(n, len(a)))
    fig, axs = plt.subplots(3, len(ee), figsize=(2 * len(ee), 6.3))
    axs = np.atleast_2d(axs).reshape(3, -1)
    for k, e in enumerate(ee):
        lam = float(z['al_lam'][e][32, 32])
        show(axs[0, k], a[e], f"D{z['det'][e]} {lam:.2f}um\nMJD {z['mjd_avg'][e]:.2f}")
        show(axs[1, k], sr['ref'][e], 'static ref')
        r = a[e] - sr['ref'][e]
        s = np.sqrt(z['al_var'][e])
        show(axs[2, k], r / s, 'resid / sigma', 2, 98)
        g = km[(km.patch == patch) & (km.frame_id == z['frame_id'][e]) & km.in_aligned]
        for q in g.itertuples():
            for row in range(3):
                axs[row, k].plot(q.x_al, q.y_al, 'o', mfc='none', mec='r', ms=9)
    fig.suptitle(f'{patch}: aligned 64x64 (6.15"/px, north up), image-zodi, static-sky reference, residual; red = known mover (kete)', fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, f'{patch}_timeseries.png'), dpi=110)
    plt.close(fig)


def main():
    os.makedirs(FIG, exist_ok=True)
    pe = pd.read_parquet(os.path.join(B.IDX, 'patch_epochs_split.parquet'))
    km = pd.read_parquet(os.path.join(B.IDX, 'known_movers.parquet'))
    for patch in ['NEP-A_11', 'SEP-A_11', 'ECL-1_11', 'NEP-D_11']:
        if os.path.exists(os.path.join(B.PAT, patch + '.npz')):
            patch_panel(patch, km)
    # epochs per patch and wavelength coverage
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.6))
    pe.groupby('patch').size().sort_values().plot.bar(ax=axs[0], fontsize=4)
    axs[0].set_ylabel('epochs per patch')
    for d in range(1, 7):
        s = pe[pe.det == d]
        axs[1].scatter(s.mjd_avg, s.lam_center_um, s=2, label=f'D{d}')
    axs[1].set_xlabel('MJD-AVG'); axs[1].set_ylabel('wavelength at patch centre (um)'); axs[1].legend(fontsize=6, markerscale=4)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'coverage.png'), dpi=110); plt.close(fig)
    st = dict(patch_epochs=int(len(pe)), patches=int(pe.patch.nunique()), frames=int(pe.frame_id.nunique()),
              by_split=pe.split.value_counts().to_dict(), by_cluster=pe.cluster.value_counts().to_dict(),
              by_det=pe.det.value_counts().sort_index().to_dict(),
              epochs_per_patch=pe.groupby('patch').size().describe().round(1).to_dict(),
              mjd_range=[float(pe.mjd_avg.min()), float(pe.mjd_avg.max())],
              releases=pe.release.value_counts().to_dict(),
              known_mover_rows=int(len(km)), known_mover_rows_in_aligned=int(km.in_aligned.sum()),
              known_objects=int(km.desig.nunique()),
              patch_epochs_with_known_mover=int((pe.get('n_known_aligned', pd.Series(0)) > 0).sum()))
    json.dump(st, open(os.path.join(TAB, 'dataset_stats.json'), 'w'), indent=1, default=str)
    print(json.dumps(st, indent=1, default=str))


if __name__ == '__main__':
    main()
