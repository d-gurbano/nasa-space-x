"""Paths and constants for the Rewind engine."""
import os

WORKTREE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MAIN = os.environ.get("REWIND_MAIN", "/Users/rahmanbazarov/Data/programming/SpaceApps2026-Rewind")
DATA = os.path.join(MAIN, "data")
WORK = os.environ.get("REWIND_WORK", os.path.join(DATA, "results", "c2-engine"))  # caches, stamps, tables
SITE = os.path.join(DATA, "site")
ORBITS = os.path.join(DATA, "02-orbits")
TARGETS = os.path.join(DATA, "01-targets")
KETE_CACHE = os.path.join(WORK, "kete-cache")  # private copy, MAIN stays read-only
SPHEREX_VEC = os.path.join(ORBITS, "horizons", "spherex_vectors_geo_5min.parquet")

PIX_ARCSEC = 6.15            # SPHEREx pixel scale (VERIFIED, pilot)
MJD_AVG_OFFSET_S = 57.56     # MJD-AVG = MJD-BEG + 57.56 s (MEASURED, pilot)
EXPTIME_S = 113.58           # XPOSURE
MAX_FRAMES = 300
MIN_FREE_GB = 20


def ensure_dirs():
    for d in (WORK, SITE, os.path.join(WORK, "objects"), KETE_CACHE):
        os.makedirs(d, exist_ok=True)
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "8")
