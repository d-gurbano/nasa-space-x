"""Measure objects as soon as their downloads finish and rebuild site/index.json after each batch.
An object is ready when a fetch log shows its references finished ('<slug> refs: 0 to read', 'n/n', or
'refs failed <slug>'), or it has no frames at all."""
from __future__ import annotations

import glob
import os
import re
import time

from . import config as C
from . import fetch as FE


def _done_from_logs():
    done = set()
    for p in glob.glob(os.path.join(FE.FETCH_DIR, "fetch*.log")):
        for line in open(p, errors="replace"):
            m = re.search(r"\] (\S+) refs: (\d+)/(\d+) ", line)
            if m and m.group(2) == m.group(3):
                done.add(m.group(1))
            m = re.search(r"\] (\S+) refs: 0 to read", line)
            if m:
                done.add(m.group(1))
            m = re.match(r"refs failed (\S+)", line)
            if m:
                done.add(m.group(1))
    return done


def _no_frames(slug):
    p = os.path.join(C.WORK, "objects", slug, "frames.csv")
    return os.path.exists(p) and os.path.getsize(p) < 5


def run(objs, every_s=300):
    from . import report, site
    measured = {}
    while True:
        ready = _done_from_logs()
        batch = [o for o in objs.itertuples() if (o.slug in ready or _no_frames(o.slug)) and o.slug not in measured]
        for o in batch:
            try:
                report.run_object(o)
            except Exception as e:  # noqa
                print(f"{o.slug}: measure failed: {e}", flush=True)
            measured[o.slug] = time.time()
        if batch:
            idx = site.rebuild_index()
            print(f"[{time.strftime('%H:%M:%S')}] index rebuilt: {len(idx['objects'])} objects", flush=True)
        if len(measured) == len(objs):
            print("all objects measured", flush=True)
            return
        time.sleep(every_s)
