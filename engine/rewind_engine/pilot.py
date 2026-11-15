"""Import shim: reuse the pilot reader/photometry (code/A0/rewind.py) and the A2 position and
orbit-fit engines (code/A2) from this repo, pointing their data paths at MAIN (read-only) and
the kete cache at our private WORK copy."""
import os
import sys
import warnings

from astropy.io.fits.verify import VerifyWarning
from astropy.wcs import FITSFixedWarning

warnings.simplefilter("ignore", VerifyWarning)
warnings.simplefilter("ignore", FITSFixedWarning)

from . import config as C

os.environ["KETE_CACHE_DIR"] = C.KETE_CACHE
for sub in ("code/A0", "code/A2"):
    p = os.path.join(C.WORKTREE, sub)
    if p not in sys.path:
        sys.path.insert(0, p)

import rewind as R  # noqa: E402,F401  (pilot functions: read_stamp_http, forced_phot, ...)


def positions():
    import positions as P
    P.ORB = C.ORBITS
    P.SPHEREX_VEC = C.SPHEREX_VEC
    return P


def orbitfit():
    positions()
    import orbitfit as OF
    return OF
